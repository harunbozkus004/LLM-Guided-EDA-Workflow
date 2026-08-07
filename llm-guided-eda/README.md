# LLM-Guided EDA Workflow

Can retrieval-augmented generation (RAG), tool-execution feedback and iterative error
correction make an LLM reliable at real ASIC physical-design scripting?

This repository contains a reproducible research prototype that answers that question
with experiments on a real EDA tool:

* **A 50-task benchmark** of OpenROAD Tcl scripting tasks (floorplanning, placement,
  timing, CTS, routing, inspection, optimization). Every task has an independent
  validator, a reference solution, and positive/negative control scripts.
* **An LLM agent** that writes Tcl, runs it in a sandboxed OpenROAD session, reads the
  result, diagnoses failures and repairs its script.
* **A version-matched knowledge base** of OpenROAD/OpenSTA documentation with hybrid
  (BM25 + vector) retrieval.
* **Six experimental configurations** (an ablation study) × 3 runs, plus statistical
  analysis.

Results and the write-up are in [`paper/research_report.md`](paper/research_report.md).

## Architecture

```
natural-language task ──► planner / prompt builder ──► LLM ──► Tcl script
        ▲                       ▲                                  │
        │                 RAG retriever                            ▼
        │           (BM25 + FAISS, RRF fusion,          sandboxed OpenROAD execution
        │            version-matched docs)            (fresh snapshot per attempt)
        │                                                          │
        │                                      structured result + design-state probe
        │                                                          │
        └──── repair prompt ◄── error classifier ◄── agent self-check (verifier)
                                                                    │
                                     hidden benchmark validator (scoring only)
```

* `openroad/`: execution harness ([executor.py](openroad/executor.py)), sandbox
  ([sandbox.py](openroad/sandbox.py)), design-state probe ([tcl/probe.tcl](openroad/tcl/probe.tcl)),
  log parsing and the error taxonomy ([log_parser.py](openroad/log_parser.py)).
* `benchmark/`: starting-state snapshots ([states.py](benchmark/states.py)), the 50 tasks
  ([tasks.json](benchmark/tasks.json)), 8 dev tasks ([dev_tasks.json](benchmark/dev_tasks.json)),
  validators, reference scripts and controls, plus [verify_benchmark.py](benchmark/verify_benchmark.py).
* `rag/` + `knowledge_base/`: ingestion, chunking, embeddings, FAISS, BM25, hybrid retrieval,
  and a retrieval evaluation.
* `agent/`: LLM clients, prompts, generator, verifier, error classifier/corrector, state
  manager, orchestrator.
* `experiments/`: experiment runner and per-configuration wrappers; results in `experiments/results/`.
* `analysis/`: metrics, paired statistics, error analysis, plots, report tables.
* `paper/`: research report, figures and tables.

## Experimental configurations

| Config | Retrieval | Execution feedback + iterative correction | Max executions |
|---|---|---|---|
| A_baseline | none | no | 1 |
| B_rag | hybrid | no | 1 |
| C_feedback | none | yes | 4 |
| D_full | hybrid | yes | 4 |
| E_vector_only | vector only | yes | 4 |
| F_single_repair | hybrid | yes (one repair) | 2 |
| G_targeted_repair (follow-up) | hybrid + exact syntax card of the failing command in each repair | yes | 4 |

All six configurations are run on all 50 tasks, 3 times each (900 episodes). An earlier attempt at
`F_single_repair` was stopped after 35 episodes; those records are kept in
`experiments/results/main/_dropped/`, excluded from all results, and F was rerun from scratch.

`G_targeted_repair` was added afterwards as a follow-up
([agent/targeted_retrieval.py](agent/targeted_retrieval.py)). It reuses D's first-attempt
generations, so D and G differ only in what happens after a failed first attempt (150 episodes).

All 1,050 episodes were run between June 11 and August 2, 2026.

All configurations use the same model, prompts (except for the documentation and feedback
sections), design context, starting snapshots, timeouts and validators.

## Methodological safeguards

* **Independent validators.** Scoring uses ground truth only: the harness probe of the actual
  database after the script, the output files, and trusted Tcl queries on the final
  database (with the original SDC reloaded, so relaxing constraints can't fake success).
  The LLM's own claims are never used. The validators are hidden from the agent, which
  decides when to stop using only its own self-check.
* **Validated validators.** Each task has a reference solution, alternative valid solutions
  (must pass), and plausible wrong solutions, including fabricated reports (must fail). Task
  drafting and an adversarial review of each category were done, and the
  final validators were verified by running every control script; 649/649 controls behave as
  expected (`python -m benchmark.verify_benchmark --split all`).
* **No test-set leakage.** Reference scripts are excluded from the knowledge base. Prompts and
  harness behavior were only checked on the 8 dev tasks.
* **Rollback.** Every attempt runs the complete script from the immutable starting snapshot.
* **Pinned versions.** The OpenROAD binary, the documentation (same commit), the LLM weights,
  the llama.cpp build and the embedding model are all pinned (see below). Every LLM call records
  the model, sampling settings and per-call seed.

## Environment (pinned)

| Component | Version |
|---|---|
| OpenROAD | 2.0-10927-g0922eecb9 (commit 0922eecb9, 2023-11-06; litex-hub conda build, x86_64 under Rosetta on Apple Silicon) |
| OpenSTA / ORFS docs | commits in [third_party/VERSIONS.txt](third_party/VERSIONS.txt) (fetched by `scripts/fetch_sources.sh`) |
| Platform / design | Nangate45 (OpenROAD test platform), `gcd` |
| LLM | Qwen3.6-35B-A3B, Q4_K_M GGUF (Apache-2.0), ggml-org revision 7878dc9a, non-thinking mode |
| LLM server | llama.cpp b11829, 4 slots × 32k context, local only (127.0.0.1) |
| Embeddings | BAAI/bge-small-en-v1.5 (revision 5c38ec7c) |
| Python | 3.11 (`requirements.lock.txt`) |

The LLM is a free, local open-weights model. The Anthropic API (`provider: anthropic`) and any
OpenAI-compatible endpoint (`provider: openai_compatible`) are also supported through
`config/model_config.yaml`.

## Setup (macOS, Apple Silicon)

Everything is installed under `.tools/` inside the repository. Nothing is written to the
home directory or the system.

```bash
bash scripts/setup_env.sh        # micromamba, OpenROAD, Python 3.11 + requirements
bash scripts/fetch_sources.sh    # version-matched OpenROAD/OpenSTA/ORFS docs and test platform
.tools/envs/py/bin/python -m benchmark.states build      # 8 starting-state snapshots
.tools/envs/py/bin/python -m rag.build_index             # knowledge base + indexes
bash scripts/setup_llm.sh        # llama.cpp + model weights (~20 GB, checksummed)
```

`Dockerfile` / `docker-compose.yml` describe an equivalent Linux environment. They were not
executed on the development Mac, which has no Docker.

## Running

```bash
scripts/llm_server.sh run        # local LLM server (separate terminal)
.tools/envs/py/bin/python -m benchmark.verify_benchmark --split all           # controls
.tools/envs/py/bin/python -m pytest tests -q                                   # unit/integration tests
.tools/envs/py/bin/python -m experiments.run_experiment --config A_baseline B_rag C_feedback D_full E_vector_only F_single_repair G_targeted_repair --runs 1 2 3 --experiment-id main
.tools/envs/py/bin/python -m analysis.make_report --experiment main --out-dir paper
```

The experiment runner is resumable: re-running the same command skips finished episodes.

## Safety

LLM-generated Tcl runs under two layers. First, a static policy rejects `exec`, sockets,
`load`, `interp`, `cd`, `package`, `rename`, harness tampering, `..` and `~` paths. Second,
a macOS Seatbelt profile denies network and process execution, confines writes to the run
directory, and blocks reads of the home directory outside the repository. Each execution
also has a wall-clock timeout and a memory watchdog.

## Results (6 configurations × 50 tasks × 3 runs, plus follow-up G: 1,050 episodes)

| Configuration | Completion % (mean ± SD, 3 runs) | Final-script execution failure % |
|---|---:|---:|
| A_baseline (single shot) | 4.0 ± 0.0 | 94.0 |
| B_rag (single shot + hybrid RAG) | 32.7 ± 3.1 | 57.3 |
| C_feedback (4 attempts, no RAG) | 13.3 ± 2.3 | 72.7 |
| D_full (4 attempts + hybrid RAG) | 48.0 ± 6.0 | 20.7 |
| E_vector_only (4 attempts + vector RAG) | 46.0 ± 4.0 | 24.7 |
| F_single_repair (2 attempts + hybrid RAG) | 43.3 ± 1.2 | 40.0 |
| G_targeted_repair (D + syntax cards on repair, follow-up) | **53.3 ± 5.0** | 20.7 |

The full agent beats the baseline by +44 pp (paired bootstrap 95% CI [32.7, 55.3]). Hybrid vs.
vector-only retrieval (-2.0 pp, CI [-10.0, 5.3]) and four attempts vs. one repair (-4.7 pp,
CI [-12.7, 2.7]) are not significantly different. Failed executions *per episode* did not fall
(0.94 baseline vs. 1.45 full agent) because the agent retries; only the failure rate of the final
script fell. Adding the exact syntax card of the failing command to each repair prompt (G) raised
completion from 48.0% to 53.3% (+5.3 pp, 95% CI [0.7, 10.7], McNemar p = 0.039; not significant
on the stricter majority-vote test). These numbers are for one local model and one design; see
[`paper/research_report.md`](paper/research_report.md) for the full analysis and limitations.
Generated tables are in `paper/tables/` and figures in `paper/figures/`.
