"""Tests of the RAG subsystem: chunking invariants, BM25 tokenizer, RRF, retriever round trip,
and sanity checks on the real knowledge base (skipped when it has not been built)."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from common.paths import KB_DIR, THIRD_PARTY
from rag.bm25_retriever import BM25Index, stem, tokenize
from rag.document_chunker import Chunk, chunk_document, chunk_documents, chunk_id
from rag.document_loader import (DOC_TYPES, Document, clean_markdown, count_commands,
                                 load_command_cards, read_versions)
from rag.embeddings import model_files_present
from rag.hybrid_retriever import RetrievedChunk, Retriever, format_context, rrf_fuse

TARGET, OVERLAP = 600, 80
HAVE_MODEL = model_files_present()
HAVE_KB = (KB_DIR / "manifest.json").exists() and (KB_DIR / "embeddings" / "chunks.faiss").exists()
needs_model = pytest.mark.skipif(not HAVE_MODEL, reason="embedding model not cached in .tools/cache")
needs_kb = pytest.mark.skipif(not (HAVE_MODEL and HAVE_KB), reason="run python -m rag.build_index first")


def words(text: str) -> int:
    """Whitespace token counter: deterministic stand-in for the model tokenizer."""
    return len(text.split())


def _sentences(n: int, tag: str) -> str:
    return " ".join(f"Sentence {i} of {tag} explains placement density and routing layers." for i in range(n))


def _code(lines: int, name: str) -> str:
    body = "\n".join(f"set_cmd_{name} -opt_{i} value_{i}" for i in range(lines))
    return f"```tcl\n{body}\n```"


def md_doc(text: str, source: str = "OpenROAD/src/xyz/README.md") -> Document:
    return Document(text=text, source=source, url=f"https://example.invalid/{source}", doc_type="readme",
                    tool="xyz", title="Tool")


# --------------------------------------------------------------------------- chunking

def test_chunk_size_and_overlap_invariants():
    paras = "\n\n".join(_sentences(6, f"paragraph {p}") for p in range(30))      # ~1800 words
    doc = md_doc(f"# Tool\n\n## Commands\n\n### Long Section\n\n{paras}\n")
    chunks = chunk_document(doc, words, TARGET, OVERLAP)
    assert len(chunks) >= 3
    assert all(c.n_tokens <= TARGET for c in chunks)
    assert {c.section for c in chunks} == {"Tool > Commands > Long Section"}
    for prev, nxt in zip(chunks, chunks[1:]):
        # the next chunk starts with a non-empty suffix of the previous one, at most OVERLAP tokens
        shared = max(k for k in range(0, len(nxt.text.split()) + 1)
                     if k == 0 or prev.text.split()[-k:] == nxt.text.split()[:k])
        assert 0 < shared <= OVERLAP
    assert chunks[1].text.split()[0] == "Sentence"          # overlap is cut on sentence boundaries


def test_short_code_blocks_are_never_split():
    blocks = [_code(n, f"b{n}") for n in (40, 120, 150, 90, 160)]                # 160-640 words each
    body = "\n\n".join(f"{_sentences(5, f'intro {i}')}\n\n{b}" for i, b in enumerate(blocks))
    chunks = chunk_document(md_doc(f"# Tool\n\n## Usage\n\n{body}\n"), words, TARGET, OVERLAP)
    assert len(chunks) > 1
    for block in blocks:
        if words(block) <= TARGET:
            assert any(block in c.text for c in chunks), "a code block that fits was split"
    for c in chunks:
        assert c.text.count("```") % 2 == 0
        assert c.n_tokens <= TARGET


def test_long_code_block_is_split_and_referenced():
    chunks = chunk_document(md_doc(f"# Tool\n\n## Script\n\n{_code(500, 'big')}\n"), words, TARGET, OVERLAP)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.text.startswith("```tcl") and c.text.rstrip().endswith("```")
        assert c.n_tokens <= TARGET


def test_heading_path_merge_and_embed_text():
    text = ("# Detailed Placement\n\nIntro.\n\n## Commands\n\n### Check Placement\n\n"
            "The `check_placement` command checks legality.\n\n```tcl\ncheck_placement [-verbose]\n```\n\n"
            "#### Options\n\n| Switch | Description |\n| --- | --- |\n| `-verbose` | Verbose. |\n\n"
            "```shell\n# not a heading inside a code block\n```\n\n"
            "### Filler Placement\n\nThe `filler_placement` command fills gaps.\n\n"
            "```tcl\nfiller_placement FILL*\n```\n")
    # 40-word budget: "Commands" (51 words) is too big, each command section (<= 40) is one chunk
    chunks = chunk_document(md_doc(text), words, 40, 10)
    assert [c.section for c in chunks] == ["Detailed Placement > Commands > Check Placement",
                                           "Detailed Placement > Commands > Filler Placement"]
    sections = [c.section for c in chunks]
    assert "Detailed Placement > Commands > Check Placement" in sections
    cp = chunks[sections.index("Detailed Placement > Commands > Check Placement")]
    assert "#### Options" in cp.text and "check_placement [-verbose]" in cp.text   # subsection merged
    assert not any("not a heading" in s for s in sections)
    assert cp.embed_text().startswith("OpenROAD/src/xyz/README.md > Detailed Placement > Commands > "
                                      "Check Placement\n")
    assert cp.url.endswith("#check-placement")
    assert cp.id == chunk_id(cp.source, cp.section, cp.text)


def test_syntax_cards_are_atomic_and_exact():
    cards = load_command_cards(THIRD_PARTY / "OpenROAD/src/gpl/src/replace.tcl", read_versions())
    gp = next(c for c in cards if c.section == "global_placement")
    assert gp.doc_type == "command_syntax" and gp.atomic
    assert "[-density target_density]" in gp.text and "-skip_io" in gp.text
    assert re.search(r"#L\d+-L\d+$", gp.url) and "0922eecb9" in gp.url
    tiny = chunk_document(gp, words, target_tokens=20, overlap_tokens=5)
    assert len(tiny) == 1 and tiny[0].text == gp.text.strip("\n")


def test_tcl_script_sections_and_line_permalinks():
    script = ("read_lef tech.lef\nread_def design.def\n\n" + "#" * 40 + "\n# Global placement\n"
              "global_placement -density 0.6\n\n" + "#" * 40 + "\n# Detailed placement\n"
              "detailed_placement\ncheck_placement\n")
    doc = Document(text=script, source="OpenROAD/test/x.tcl", url="u", doc_type="flow_script",
                   tool="flow", title="x.tcl", fmt="script", line_map=list(range(1, 12)))
    whole = chunk_document(doc, words, TARGET, OVERLAP)
    assert len(whole) == 1 and "#" * 40 not in whole[0].text        # decorative rules dropped
    assert "# Global placement" in whole[0].text and whole[0].url == "u#L1-L11"
    parts = chunk_document(doc, words, target_tokens=8, overlap_tokens=2)
    assert [c.section for c in parts] == ["x.tcl", "Global placement", "Detailed placement"]


def test_markdown_cleaning_keeps_code_and_placeholders():
    md = ("# T\n\n[![badge](https://x/b.svg)](https://x)\n\n<img src=\"a.png\" width=3>\n\n"
          "See [the guide](https://x/guide) for `<file>` usage.\n\n```{note}\nNotes here.\n```\n\n"
          "```tcl\nread_def <file>  ;# <tag> kept\n```\n")
    out = clean_markdown(md)
    assert "badge" not in out and "<img" not in out and "https://x/guide" not in out
    assert "See the guide for `<file>` usage." in out
    assert "Note:" in out and "Notes here." in out
    assert "read_def <file>  ;# <tag> kept" in out


def test_html_loader(tmp_path: Path):
    from rag.document_loader import load_html

    page = tmp_path / "OpenROAD" / "docs" / "page.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html><body><nav>menu</nav><h1>Guide</h1><p>Use <b>pdngen</b> after "
                    "<a href='x'>tapcell</a>.</p><h2>Example</h2><pre>pdngen\ncheck_placement</pre>"
                    "<h2>License</h2><p>BSD</p></body></html>")
    (tmp_path / "VERSIONS.txt").write_text("OpenROAD abc123\n")
    doc = load_html(page, "guide", read_versions(tmp_path), tmp_path)
    assert doc.title == "Guide" and doc.source == "OpenROAD/docs/page.html"
    assert doc.url.endswith("/blob/abc123/docs/page.html")
    assert "Use pdngen after tapcell." in doc.text and "```\npdngen\ncheck_placement\n```" in doc.text
    assert "menu" not in doc.text and "BSD" not in doc.text            # nav and License dropped
    whole = chunk_document(doc, words, TARGET, OVERLAP)
    assert [c.section for c in whole] == ["Guide"] and "## Example" in whole[0].text
    assert "Guide > Example" in [c.section for c in chunk_document(doc, words, 6, 2)]


def test_trivial_command_count():
    assert count_commands("source helpers.tcl\nset x 1\nread_lef a.lef\n# c\nputs hi\n") == 1
    assert count_commands("read_lef a\nread_def b \\\n  -floorplan_initialize\nglobal_placement\n") == 3


def test_duplicate_chunks_dropped_and_truncation():
    a = md_doc("# A\n\nsame text here\n", "OpenROAD/src/a/README.md")
    b = md_doc("# B\n\nsame text here\n", "OpenROAD/src/b/README.md")
    chunks, stats = chunk_documents([a, b], words)
    assert len(chunks) == 1 and stats["duplicates_dropped"] == 1


# --------------------------------------------------------------------------- BM25 tokenizer

def test_tokenizer_keeps_identifiers_options_and_subtokens():
    toks = tokenize("global_placement -density 0.7 -routability_driven")
    for t in ("global_placement", "global", "placement", "-density", "densiti", "0.7",
              "-routability_driven", "routability_driven", "driven"):
        assert t in toks, t
    ns = tokenize("sta::report_checks -group_count 5")
    for t in ("sta::report_checks", "report_checks", "sta", "report", "check", "-group_count",
              "group_count", "group", "count", "5"):
        assert t in ns, t


def test_tokenizer_lowercases_stems_and_drops_stopwords():
    assert tokenize("How do I legalize the placement?") == ["legal", "placement"]
    assert tokenize("legalizing") == tokenize("legalization") == tokenize("Legalized") == ["legal"]
    assert tokenize("SET_WIRE_RC") == ["set_wire_rc", "set", "wire", "rc"]
    assert stem("violations") == stem("violating") == "violat"
    assert stem("caresses") == "caress" and stem("relational") == "relat"   # Porter reference cases


def test_bm25_ranks_exact_option_match_first(tmp_path: Path):
    docs = ["global_placement -density target_density sets the placement density",
            "detailed_placement legalizes cells after global placement",
            "report_checks -group_count path_count reports paths per group"]
    index = BM25Index.build(docs)
    assert index.search("-group_count", 3)[0][0] == 2
    assert index.search("legalize placement", 1)[0][0] == 1
    index.save(tmp_path)
    again = BM25Index.load(tmp_path)
    assert again.corpus_tokens == index.corpus_tokens
    assert np.allclose(again.scores("placement density"), index.scores("placement density"))
    assert index.search("zzzz unknown", 3) == []


# --------------------------------------------------------------------------- RRF / context formatting

def test_rrf_math_on_toy_example():
    fused = dict(rrf_fuse([["a", "b", "c"], ["c", "a", "d"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert fused["b"] == pytest.approx(1 / 62)
    assert fused["c"] == pytest.approx(1 / 63 + 1 / 61)
    assert fused["d"] == pytest.approx(1 / 63)
    assert [x for x, _ in rrf_fuse([["a", "b", "c"], ["c", "a", "d"]], k=60)] == ["a", "c", "b", "d"]
    assert [x for x, _ in rrf_fuse([["x"], ["y"]], k=60)] == ["x", "y"]   # tie -> earlier list
    assert [x for x, _ in rrf_fuse([["p", "q"], []], k=1)] == ["p", "q"]


def _rc(i: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(id=str(i), text=text, source=f"s{i}.md", section=f"Sec {i}", url="u",
                          doc_type="readme", score=1.0, rank=i)


def test_format_context_numbering_and_cut_on_chunk_boundaries():
    chunks = [_rc(1, "a" * 100), _rc(2, "b" * 100), _rc(3, "c" * 100)]
    full = format_context(chunks, max_chars=10_000)
    assert full.startswith("[1] s1.md > Sec 1\n" + "a" * 100 + "\n\n[2] s2.md > Sec 2\n")
    cut = format_context(chunks, max_chars=260)
    assert "[2]" in cut and "[3]" not in cut and len(cut) <= 260
    assert format_context(chunks, max_chars=50) == ("[1] s1.md > Sec 1\n" + "a" * 100)[:50]
    assert format_context([], 100) == ""


# --------------------------------------------------------------------------- retriever round trip

def _tiny_chunks() -> list[Chunk]:
    rows = [
        ("OpenROAD/src/dpl/README.md", "Detailed Placement > Commands > Detailed Placement", "readme",
         "The detailed_placement command legalizes instances to rows and sites after global placement."),
        ("OpenROAD/src/dpl/README.md", "Detailed Placement > Commands > Detailed Placement", "readme",
         "Option -max_displacement limits how far detailed_placement moves an instance."),
        ("OpenROAD/src/gpl/README.md", "RePlAce > Commands", "readme",
         "global_placement -density target_density sets the target placement density of the global placer."),
        ("OpenSTA/tcl/Search.tcl", "report_checks", "command_syntax",
         "report_checks [-group_count path_count] [-path_delay min|max] [-format full|end]"),
        ("OpenROAD/src/pdn/README.md", "PDNGEN > Commands > Add Stripe", "readme",
         "add_pdn_stripe -layer metal4 -width 0.48 -pitch 56.0 adds power straps to the grid."),
        ("OpenROAD/src/dpl/test/simple01.tcl", "simple01.tcl", "example",
         "read_lef Nangate45.lef\nread_def simple01.def\ndetailed_placement\ncheck_placement"),
    ]
    return [Chunk(id=chunk_id(s, sec, t), text=t, source=s, section=sec, url=f"https://x/{s}",
                  doc_type=dt, tool=s.split("/")[2] if "/src/" in s else "sta", title="T",
                  n_tokens=words(t)) for s, sec, dt, t in rows]


@pytest.fixture(scope="module")
def tiny_kb(tmp_path_factory) -> Path:
    from rag.build_index import write_index

    kb = tmp_path_factory.mktemp("kb")
    write_index(_tiny_chunks(), kb)
    return kb


@needs_model
def test_retriever_round_trip_on_tiny_index(tiny_kb: Path):
    manifest = json.loads((tiny_kb / "manifest.json").read_text())
    assert manifest["chunks"]["total"] == 6 and manifest["embedding"]["dim"] == 384
    for name in ("documentation/chunks.jsonl", "examples/chunks.jsonl"):
        assert (tiny_kb / name).exists()
    for mode in ("hybrid", "vector", "bm25"):
        r = Retriever.load(mode, kb_dir=tiny_kb)
        assert r.retrieve("", k=3) == [] and r.retrieve("anything", k=0) == []
        hits = r.retrieve("legalize the placement with detailed placement", k=6)
        assert hits and all(isinstance(h, RetrievedChunk) for h in hits)
        assert [h.rank for h in hits] == list(range(1, len(hits) + 1))
        assert "detailed_placement" in hits[0].text, mode
        keys = [(h.source, h.section) for h in hits]
        assert len(keys) == len(set(keys)), "same source+section returned twice"
        top = r.retrieve("report_checks -group_count", k=2)
        assert top[0].source == "OpenSTA/tcl/Search.tcl", mode
    with pytest.raises(ValueError):
        Retriever.load("tfidf", kb_dir=tiny_kb)


@needs_model
def test_retriever_is_thread_safe(tiny_kb: Path):
    r = Retriever.load("hybrid", kb_dir=tiny_kb)
    queries = ["power straps on metal4", "report paths per group", "global placement density",
               "legalize cells", "check placement"] * 8
    sequential = [[h.id for h in r.retrieve(q)] for q in queries]
    with ThreadPoolExecutor(max_workers=8) as pool:
        parallel = list(pool.map(lambda q: [h.id for h in r.retrieve(q)], queries))
    assert parallel == sequential


# --------------------------------------------------------------------------- real knowledge base

@pytest.fixture(scope="module")
def kb_chunks() -> list[dict]:
    return [json.loads(line) for name in ("documentation", "examples")
            for line in open(KB_DIR / name / "chunks.jsonl")]


@needs_kb
def test_real_kb_metadata_and_invariants(kb_chunks: list[dict]):
    manifest = json.loads((KB_DIR / "manifest.json").read_text())
    assert manifest["chunks"]["total"] == len(kb_chunks)
    assert len({c["id"] for c in kb_chunks}) == len(kb_chunks)
    versions = read_versions()
    for c in kb_chunks:
        assert c["doc_type"] in DOC_TYPES
        assert c["source"].split("/")[0] in versions          # third_party sources only
        assert versions[c["source"].split("/")[0]] in c["url"]
        assert c["text"].strip() and c["tool"]
        assert c["id"] == chunk_id(c["source"], c["section"], c["text"])
        if c["doc_type"] != "command_syntax":
            assert c["n_tokens"] <= manifest["chunking"]["target_tokens"]
    for name, info in manifest["files"].items():
        if name.endswith("chunks.jsonl"):
            from rag.build_index import sha256_file
            assert sha256_file(KB_DIR / name) == info["sha256"]


@needs_kb
def test_real_kb_token_counts_use_model_tokenizer(kb_chunks: list[dict]):
    from rag.embeddings import get_token_counter

    count = get_token_counter()
    for c in kb_chunks[::97]:
        assert c["n_tokens"] == count(c["text"])


@needs_kb
def test_faiss_matches_brute_force_search():
    r = Retriever.load("vector")
    vectors = np.load(KB_DIR / "embeddings" / "embeddings.npy")
    for q in ("clock tree synthesis buffers", "insert filler cells", "write SPEF"):
        qv = r.kb._embedder.embed_query(q)
        faiss_rows = [row for row, _ in r.kb._vectors.search(qv, 10)]
        brute = list(np.argsort(-(vectors @ qv), kind="stable")[:10])
        assert faiss_rows[:5] == brute[:5]


@needs_kb
def test_sanity_global_placement_density():
    hybrid = Retriever.load("hybrid").retrieve("global placement target density", k=6)
    assert any(h.source.startswith("OpenROAD/src/gpl/") for h in hybrid[:3])      # README or syntax card
    assert any(h.source.endswith("src/gpl/README.md") for h in hybrid)
    bm25 = Retriever.load("bm25").retrieve("global placement target density", k=3)
    assert any(h.source.endswith("src/gpl/README.md") for h in bm25)


@needs_kb
def test_sanity_report_checks_group_count():
    hits = Retriever.load("hybrid").retrieve("report_checks group count option", k=6)
    assert any(h.source in ("OpenSTA/doc/OpenSTA.pdf", "OpenSTA/tcl/Search.tcl")
               and "report_checks" in h.section for h in hits)
    assert any("-group_count" in h.text for h in hits)


@needs_kb
def test_sanity_legalization_and_context_budget():
    r = Retriever.load("hybrid")
    hits = r.retrieve("detailed_placement legalize cells after global placement", k=6)
    assert any(h.source.startswith("OpenROAD/src/dpl/") for h in hits[:3])
    ctx = format_context(hits, max_chars=14000)
    assert ctx.startswith("[1] ") and len(ctx) <= 14000
