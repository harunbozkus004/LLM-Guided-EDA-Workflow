"""Rebuild the knowledge base from scratch: ``python -m rag.build_index``.

Pipeline: load the pinned third_party sources -> heading-aware chunks ->
knowledge_base/{documentation,examples}/chunks.jsonl -> bge embeddings (FAISS
IndexFlatIP) + BM25 token index in knowledge_base/embeddings/ ->
knowledge_base/manifest.json. Everything except the build timestamp and timings
is deterministic for a given machine and library versions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from common.paths import KB_DIR, THIRD_PARTY
from rag.document_chunker import CHUNKER_VERSION, OVERLAP_TOKENS, TARGET_TOKENS, Chunk, chunk_documents
from rag.document_loader import GITHUB, Document, load_corpus

DOCUMENTATION_TYPES = ("readme", "guide", "command_syntax", "reference_pdf")
EXAMPLE_TYPES = ("example", "flow_script")
MAX_CHUNKS_PER_DOC = {"example": 6}     # very long test scripts (pad ring data) keep their first chunks
MAX_COMMANDS_PER_CHUNK = 25
# Core OpenROAD commands defined in src/OpenRoad.tcl, which is outside the pinned sparse checkout.
CORE_COMMANDS = ("read_lef", "read_def", "write_def", "read_db", "write_db", "set_thread_count",
                 "read_guides", "write_cdl")
# Command names without an underscore that are not also ordinary English words.
SINGLE_WORD_COMMANDS = ("tapcell", "pdngen")
CORPUS_SPEC = {
    "OpenROAD": ["README.md", "docs/**/*.md (contributor-process and link-only pages skipped)",
                 "src/<tool>/README.md", "src/<tool>/src/*.tcl -> command syntax cards",
                 "src/<tool>/test/*.tcl -> examples (near-duplicates and < 3 commands skipped)",
                 "test/*.tcl flow scripts (regression infrastructure skipped)"],
    "OpenSTA": ["README.md", "doc/OpenSTA.pdf -> one entry per section / command / variable",
                "tcl/*.tcl and */*.tcl -> command syntax cards", "examples/*.tcl -> examples"],
    "OpenROAD-flow-scripts": ["README.md", "docs/user/*.md", "docs/tutorials/*.md",
                              "flow/scripts/*.tcl (Yosys/KLayout scripts skipped)",
                              "flow/platforms/nangate45/*.tcl and config.mk"],
}
PREPROCESSING = [
    "markdown: images, badges, html tags/comments, mermaid diagrams and link targets removed; "
    "code blocks kept verbatim; License/Authors/References/Regression tests/FAQs sections dropped",
    "tcl: leading license headers and decorative '####' / '# ----' comment rules removed",
    "examples: 'source helpers.tcl' and diff_file lines removed; a one-line note marks "
    "make_result_file as a regression-test helper",
    "command syntax cards: exact define_cmd_args text, the proc's leading comments, and the "
    "keys/flags of its parse_key_args call",
    "OpenSTA.pdf: split by font (Helvetica-Bold headings, LiberationMono-Bold command names); "
    "table of contents and alphabetical index dropped",
    "tool READMEs (src/<tool>/README.md): the title in the heading path is extended with the tool "
    "namespace and the name given in docs/contrib/DeveloperGuide.md, e.g. 'RePlAce (gpl: RePlAce "
    "Global Placer)'",
    "chunks with identical text (whitespace-normalised) are kept once",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def known_commands(docs: list[Document]) -> set[str]:
    """Command names used to annotate chunks (single words such as 'source' are ambiguous in
    prose and only kept when listed in SINGLE_WORD_COMMANDS)."""
    names = set(CORE_COMMANDS)
    for d in docs:
        names.update(c for c in d.commands if "_" in c or c in SINGLE_WORD_COMMANDS)
    return names


def annotate_commands(chunks: list[Chunk], names: set[str]) -> None:
    """``chunk.commands`` = known command names mentioned in the chunk, in order of appearance."""
    if not names:
        return
    pattern = re.compile(r"(?<![\w:$-])(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True))
                         + r")(?![\w])")
    for c in chunks:
        found: list[str] = list(c.commands)
        for m in pattern.finditer(c.text):
            if m.group(1) not in found:
                found.append(m.group(1))
        c.commands = found[:MAX_COMMANDS_PER_CHUNK]


def _distribution(values: list[int]) -> dict:
    if not values:
        return {}
    s = sorted(values)
    return {"min": s[0], "median": statistics.median(s), "mean": round(statistics.mean(s), 1),
            "p95": s[min(len(s) - 1, int(0.95 * len(s)))], "max": s[-1]}


def write_index(chunks: list[Chunk], kb_dir: Path, embedder=None, manifest_extra: dict | None = None,
                show_progress: bool = False, count=None) -> dict:
    """Write chunk files, FAISS + BM25 indexes and manifest.json for ``chunks`` into ``kb_dir``.

    Chunks are indexed documentation first, then examples (the order of the chunk files)."""
    from rag.bm25_retriever import B, EPSILON, K1, TOKENIZER_VERSION, BM25Index
    from rag.embeddings import BATCH_SIZE, MAX_SEQ_LENGTH, QUERY_PREFIX, get_embedder, library_versions
    from rag.hybrid_retriever import EMBEDDINGS_DIR
    from rag.vector_store import VectorStore

    t0 = time.time()
    emb_dir = kb_dir / EMBEDDINGS_DIR
    groups = {"documentation": [c for c in chunks if c.doc_type not in EXAMPLE_TYPES],
              "examples": [c for c in chunks if c.doc_type in EXAMPLE_TYPES]}
    ordered = groups["documentation"] + groups["examples"]
    if len({c.id for c in ordered}) != len(ordered):
        raise ValueError("duplicate chunk ids")

    for stale in [kb_dir / g / "chunks.jsonl" for g in groups] + \
                 [emb_dir / n for n in ("chunks.faiss", "chunk_ids.json", "embeddings.npy",
                                        "bm25_vocab.json", "bm25_tokens.npy", "bm25_offsets.npy")]:
        stale.unlink(missing_ok=True)
    files: dict[str, dict] = {}
    for group, items in groups.items():
        path = kb_dir / group / "chunks.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for c in items:
                f.write(json.dumps(c.to_dict(), sort_keys=True, ensure_ascii=False) + "\n")
        files[f"{group}/chunks.jsonl"] = {"chunks": len(items), "sha256": sha256_file(path)}

    embedder = embedder or get_embedder()
    texts = [c.embed_text() for c in ordered]
    t_embed = time.time()
    vectors = embedder.embed_documents(texts, show_progress=show_progress)
    embed_seconds = time.time() - t_embed
    VectorStore.build(vectors, [c.id for c in ordered]).save(emb_dir, vectors)
    BM25Index.build(texts).save(emb_dir)
    for name in ("chunks.faiss", "chunk_ids.json", "embeddings.npy", "bm25_vocab.json",
                 "bm25_tokens.npy", "bm25_offsets.npy"):
        files[f"{EMBEDDINGS_DIR}/{name}"] = {"sha256": sha256_file(emb_dir / name)}

    manifest = {
        "build_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunks": {
            "total": len(ordered),
            "by_doc_type": dict(sorted(Counter(c.doc_type for c in ordered).items())),
            "by_tool": dict(sorted(Counter(c.tool for c in ordered).items())),
            "tokens": _distribution([c.n_tokens for c in ordered]),
        },
        "embedding": {
            "model": embedder.model_name, "revision": embedder.revision, "dim": embedder.dim,
            "normalized": True, "query_prefix": QUERY_PREFIX, "document_prefix": "",
            "max_seq_length": MAX_SEQ_LENGTH, "batch_size": BATCH_SIZE, "device": embedder.device,
            "embedded_text": "'<source> > <section>' line + chunk text",
        },
        "vector_store": {"type": "faiss.IndexFlatIP", "metric": "inner product of normalised vectors (cosine)",
                         "n_vectors": len(ordered)},
        "bm25": {"implementation": "rank_bm25.BM25Okapi", "k1": K1, "b": B, "epsilon": EPSILON,
                 "tokenizer_version": TOKENIZER_VERSION, "indexed_text": "same as embedded text"},
        "files": files,
        "timings_s": {"embedding": round(embed_seconds, 1), "write_index": round(time.time() - t0, 1)},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        **library_versions()},
    }
    if count is not None:
        manifest["chunks"]["over_model_window"] = sum(1 for t in texts if count(t) + 2 > MAX_SEQ_LENGTH)
    for key, value in (manifest_extra or {}).items():
        if isinstance(value, dict) and isinstance(manifest.get(key), dict):
            manifest[key].update(value)
        else:
            manifest[key] = value
    (kb_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def build_knowledge_base(kb_dir: Path = KB_DIR, root: Path = THIRD_PARTY,
                         target_tokens: int = TARGET_TOKENS, overlap_tokens: int = OVERLAP_TOKENS,
                         show_progress: bool = True) -> dict:
    from rag.embeddings import MODEL_NAME, get_embedder, get_token_counter

    t0 = time.time()
    docs, load_stats = load_corpus(root)
    count = get_token_counter()
    chunks, chunk_stats = chunk_documents(docs, count, target_tokens, overlap_tokens, MAX_CHUNKS_PER_DOC)
    annotate_commands(chunks, known_commands(docs))
    t_chunk = time.time() - t0

    embedder = get_embedder()
    versions = load_stats["versions"]
    extra = {
        "sources": {repo: {"commit": versions.get(repo), "repository": url,
                           "include": CORPUS_SPEC[repo]} for repo, url in GITHUB.items()},
        "corpus": {
            "root": "third_party/",
            "benchmark_content_included": False,
            "documents": {
                "total": len(docs),
                "by_doc_type": dict(sorted(Counter(d.doc_type for d in docs).items())),
                "by_tool": dict(sorted(Counter(d.tool for d in docs).items())),
                "source_files": len({d.source for d in docs}),
            },
            "skipped_files": load_stats["skipped"],
            "trivial_examples_skipped": len(load_stats["trivial_examples"]),
            "near_duplicate_examples_skipped": load_stats["duplicate_examples"],
            "pdf_unmatched_headings": load_stats.get("pdf_unmatched_headings", []),
            "preprocessing": PREPROCESSING,
        },
        "chunking": {
            "chunker_version": CHUNKER_VERSION, "target_tokens": target_tokens,
            "overlap_tokens": overlap_tokens, "tokenizer": f"{MODEL_NAME} (WordPiece, no special tokens)",
            "max_chunks_per_document": MAX_CHUNKS_PER_DOC,
            "truncated_documents": chunk_stats["truncated_documents"],
            "duplicate_chunks_dropped": chunk_stats["duplicates_dropped"],
            "atomic": "command syntax cards and code blocks <= target are never split",
        },
    }
    manifest = write_index(chunks, kb_dir, embedder, extra, show_progress, count)
    manifest["timings_s"]["load_and_chunk"] = round(t_chunk, 1)
    manifest["timings_s"]["total"] = round(time.time() - t0, 1)
    (kb_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kb-dir", type=Path, default=KB_DIR)
    ap.add_argument("--target-tokens", type=int, default=TARGET_TOKENS)
    ap.add_argument("--overlap-tokens", type=int, default=OVERLAP_TOKENS)
    args = ap.parse_args(argv)
    m = build_knowledge_base(args.kb_dir, target_tokens=args.target_tokens, overlap_tokens=args.overlap_tokens)
    print(json.dumps({"documents": m["corpus"]["documents"], "chunks": m["chunks"],
                      "timings_s": m["timings_s"]}, indent=2))


if __name__ == "__main__":
    main()
