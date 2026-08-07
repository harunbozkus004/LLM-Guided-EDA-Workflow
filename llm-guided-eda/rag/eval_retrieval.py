"""Retrieval evaluation: ``python -m rag.eval_retrieval``.

Runs the labeled questions of knowledge_base/retrieval_eval.json through the
vector, bm25 and hybrid retrievers and reports recall@1/3/6 (the fraction of
questions with at least one relevant chunk in the top k) and MRR@10. A chunk is
relevant when its source matches a labeled source file and its text or section
mentions a labeled command (see ``is_relevant``). Writes
knowledge_base/retrieval_eval_results.json and .md.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from common.paths import KB_DIR
from rag.hybrid_retriever import MODES, RetrievedChunk, Retriever

EVAL_FILE = KB_DIR / "retrieval_eval.json"
RESULTS_JSON = KB_DIR / "retrieval_eval_results.json"
RESULTS_MD = KB_DIR / "retrieval_eval_results.md"
NOTE = ("The questions were written before any retrieval result was seen. There is no separate "
        "development set: the same 40 questions were used to check three design changes (Porter "
        "stemming in BM25, per-ranker source+section deduplication before fusion, tool names in "
        "README titles), so the numbers are slightly optimistic. Relevance counts only the labeled "
        "primary documentation; usage examples are credited by command_hit@6 only.")
RECALL_AT = (1, 3, 6)
MRR_DEPTH = 10
EVAL_ORDER = ("vector", "bm25", "hybrid")


def load_eval_set(path: Path = EVAL_FILE) -> list[dict]:
    return json.loads(path.read_text())["questions"]


def source_matches(source: str, labeled: str) -> bool:
    """``labeled`` is a third_party-relative path, or a suffix of one on a '/' boundary."""
    return source == labeled or source.endswith("/" + labeled)


def mentions(text: str, command: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(command)}(?!\w)", text) is not None


def is_relevant(chunk: RetrievedChunk, item: dict) -> bool:
    if not any(source_matches(chunk.source, s) for s in item["sources"]):
        return False
    commands = item.get("commands") or []
    return not commands or any(mentions(chunk.section, c) or mentions(chunk.text, c) for c in commands)


def first_relevant_rank(chunks: list[RetrievedChunk], item: dict) -> int | None:
    return next((c.rank for c in chunks if is_relevant(c, item)), None)


def first_command_rank(chunks: list[RetrievedChunk], item: dict) -> int | None:
    """Rank of the first chunk from ANY source (docs, examples, flows) naming a labeled command."""
    return next((c.rank for c in chunks
                 if any(mentions(c.section, x) or mentions(c.text, x) for x in item.get("commands", []))),
                None)


def evaluate_mode(retriever: Retriever, items: list[dict], depth: int = MRR_DEPTH) -> dict:
    per_q = []
    t0 = time.time()
    for item in items:
        chunks = retriever.retrieve(item["question"], k=depth)
        rank = first_relevant_rank(chunks, item)
        per_q.append({"id": item["id"], "first_relevant_rank": rank,
                      "first_command_rank": first_command_rank(chunks, item),
                      "top": [f"{c.source} > {c.section}" for c in chunks[:6]]})
    n = len(items)
    ranks = [q["first_relevant_rank"] for q in per_q]
    metrics = {f"recall@{k}": sum(1 for r in ranks if r is not None and r <= k) / n for k in RECALL_AT}
    metrics[f"mrr@{depth}"] = sum(1.0 / r for r in ranks if r is not None) / n
    metrics["command_hit@6"] = sum(1 for q in per_q if (q["first_command_rank"] or 99) <= 6) / n
    metrics["mean_latency_ms"] = 1000 * (time.time() - t0) / n
    return {"metrics": metrics, "questions": per_q}


def evaluate(modes: tuple[str, ...] = EVAL_ORDER, kb_dir: Path | None = None,
             eval_file: Path = EVAL_FILE) -> dict:
    items = load_eval_set(eval_file)
    results: dict = {"n_questions": len(items), "modes": {}}
    for mode in modes:
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode}")
        retriever = Retriever.load(mode, kb_dir)
        retriever.retrieve("warm-up query", k=1)
        results["modes"][mode] = evaluate_mode(retriever, items)
    kb = Path(kb_dir or KB_DIR)
    manifest = json.loads((kb / "manifest.json").read_text()) if (kb / "manifest.json").exists() else {}
    results["config"] = {
        "top_k_semantic": retriever.top_k_semantic, "top_k_keyword": retriever.top_k_keyword,
        "rrf_k": retriever.rrf_k, "dedupe": "source+section", "max_examples": retriever.max_examples,
        "embedding_model": manifest.get("embedding", {}).get("model"),
        "embedding_revision": manifest.get("embedding", {}).get("revision"),
        "chunks": manifest.get("chunks", {}).get("total"),
        "index_built": manifest.get("build_timestamp"),
    }
    results["definitions"] = {
        "relevant": "chunk source matches a labeled source file AND the chunk text/section mentions "
                    "a labeled command (whole word)",
        "recall@k": "fraction of questions with >= 1 relevant chunk among the top k (hit rate)",
        f"mrr@{MRR_DEPTH}": f"mean reciprocal rank of the first relevant chunk in the top {MRR_DEPTH} "
                            "(0 when none)",
        "command_hit@6": "secondary: fraction of questions whose top 6 contain a chunk from ANY source "
                         "(documentation, example or flow script) naming a labeled command",
    }
    results["note"] = NOTE
    results["evaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return results


def to_markdown(results: dict, items: list[dict]) -> str:
    modes = list(results["modes"])
    cols = [f"recall@{k}" for k in RECALL_AT] + [f"mrr@{MRR_DEPTH}", "command_hit@6"]
    lines = ["# Retrieval evaluation", "",
             f"{results['n_questions']} labeled questions (knowledge_base/retrieval_eval.json); "
             f"index of {results['config']['chunks']} chunks built {results['config']['index_built']}, "
             f"embedding model {results['config']['embedding_model']}.", "",
             "| mode | " + " | ".join(cols) + " | mean latency (ms) |",
             "|---|" + "---:|" * (len(cols) + 1)]
    for m in modes:
        met = results["modes"][m]["metrics"]
        lines.append(f"| {m} | " + " | ".join(f"{met[c]:.3f}" for c in cols)
                     + f" | {met['mean_latency_ms']:.0f} |")
    cfg = results["config"]
    lines += ["", f"Hybrid = reciprocal rank fusion (k={cfg['rrf_k']}) of the top {cfg['top_k_semantic']} "
              f"vector and top {cfg['top_k_keyword']} BM25 hits. Every mode deduplicates chunks with the "
              "same source + section (each ranker's list holds distinct sections; hybrid fuses per "
              "section and shows the section's best chunk).", "",
              "Definitions: " + "; ".join(f"**{k}**: {v}" for k, v in results["definitions"].items()), "",
              f"Note: {results['note']}", "",
              "## Per question (rank of the first relevant chunk, '-' = not in top 10)", "",
              "| id | question | " + " | ".join(modes) + " |", "|---|---|" + "---:|" * len(modes)]
    ranks = {m: {q["id"]: q["first_relevant_rank"] for q in results["modes"][m]["questions"]} for m in modes}
    for item in items:
        cells = [str(ranks[m][item["id"]] or "-") for m in modes]
        lines.append(f"| {item['id']} | {item['question']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kb-dir", type=Path, default=None)
    ap.add_argument("--eval-file", type=Path, default=EVAL_FILE)
    ap.add_argument("--out-json", type=Path, default=RESULTS_JSON)
    ap.add_argument("--out-md", type=Path, default=RESULTS_MD)
    args = ap.parse_args(argv)
    results = evaluate(kb_dir=args.kb_dir, eval_file=args.eval_file)
    args.out_json.write_text(json.dumps(results, indent=2) + "\n")
    args.out_md.write_text(to_markdown(results, load_eval_set(args.eval_file)))
    for mode, r in results["modes"].items():
        print(mode.ljust(7), "  ".join(f"{k}={v:.3f}" for k, v in r["metrics"].items()))


if __name__ == "__main__":
    main()
