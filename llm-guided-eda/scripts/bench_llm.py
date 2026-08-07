"""Calibrate the local LLM server (speed, output length, mode) on DEV tasks only.

Evaluation tasks are never used here. Results go to experiments/llm_calibration.json
and justify the generation settings recorded in config/model_config.yaml.

    python scripts/bench_llm.py --task DEV-EX-01 --concurrency 4 --repeats 4
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.paths  # noqa: E402,F401
from common.paths import EXPERIMENTS_DIR  # noqa: E402
from benchmark.design_context import design_context  # noqa: E402
from benchmark.task_loader import load_tasks  # noqa: E402

SYSTEM = (
    "You are an expert ASIC physical-design engineer who writes Tcl scripts for the OpenROAD tool.\n"
    "Write one complete Tcl script that accomplishes the task when it is sourced in that session.\n"
    "Return the complete script in a single fenced code block marked tcl."
)
MODES = {
    # Qwen3.6 model-card recommendations; presence_penalty 0 because code repeats identifiers.
    "non_thinking": {"enable_thinking": False, "temperature": 0.7, "top_p": 0.8},
    "thinking": {"enable_thinking": True, "temperature": 0.6, "top_p": 0.95},
}


def call(client, model: str, messages: list[dict], mode: str, seed: int, max_tokens: int) -> dict:
    m = MODES[mode]
    t0 = time.monotonic()
    r = client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=m["temperature"],
        top_p=m["top_p"], seed=seed, presence_penalty=0.0,
        extra_body={"top_k": 20, "min_p": 0.0, "chat_template_kwargs": {"enable_thinking": m["enable_thinking"]}},
    )
    d = r.to_dict()
    text = r.choices[0].message.content or ""
    return {
        "mode": mode, "seed": seed, "latency_s": round(time.monotonic() - t0, 2),
        "prompt_tokens": d["usage"]["prompt_tokens"], "completion_tokens": d["usage"]["completion_tokens"],
        "has_tcl_block": bool(re.search(r"```tcl", text, re.I)), "finish_reason": r.choices[0].finish_reason,
        "timings": d.get("timings", {}),
    }


def main() -> None:
    from openai import OpenAI

    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="DEV-EX-01")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    args = ap.parse_args()

    task = load_tasks("dev", [args.task])[0]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"TASK\n{task.instruction}\n\n{design_context(task.start_state)}\nWrite the Tcl script."}]
    client = OpenAI(base_url=args.base_url, api_key="local", timeout=900)
    model = client.models.list().data[0].id
    out = {"task": args.task, "model": model, "concurrency": args.concurrency, "modes": {}}
    for mode in MODES:
        t0 = time.monotonic()
        with ThreadPoolExecutor(args.concurrency) as pool:
            rows = list(pool.map(lambda s: call(client, model, messages, mode, s, args.max_tokens),
                                 range(1, args.repeats + 1)))
        wall = time.monotonic() - t0
        comp = [r["completion_tokens"] for r in rows]
        out["modes"][mode] = {
            "wall_s": round(wall, 1), "calls": len(rows), "mean_latency_s": round(sum(r["latency_s"] for r in rows) / len(rows), 1),
            "mean_completion_tokens": round(sum(comp) / len(comp)), "max_completion_tokens": max(comp),
            "aggregate_tokens_per_s": round(sum(comp) / wall, 1), "tcl_block_rate": sum(r["has_tcl_block"] for r in rows) / len(rows),
            "rows": rows,
        }
        print(f"{mode:13s} wall={wall:6.1f}s mean_latency={out['modes'][mode]['mean_latency_s']}s "
              f"mean_out={out['modes'][mode]['mean_completion_tokens']} tok aggregate={out['modes'][mode]['aggregate_tokens_per_s']} tok/s "
              f"tcl_block_rate={out['modes'][mode]['tcl_block_rate']}")
    (EXPERIMENTS_DIR / "llm_calibration.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
