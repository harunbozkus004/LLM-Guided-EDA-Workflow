# Main results

- Completion and first-attempt success: per-run rate (successes / episodes recorded in the run x 100); mean and sample SD (ddof=1) over runs.
- Recovery: episodes whose attempt 1 failed the validator but whose final attempt passed / episodes whose attempt 1 failed (pooled over runs; n/a for single-shot configurations).
- Failed exec./task: mean number of failed OpenROAD executions (error, timeout or policy rejection) per episode. Final exec. failure: % of episodes whose final script did not execute cleanly.
- Correct attempt 1 rejected: episodes whose attempt 1 passed the validator but failed the agent's own self-check, so the agent kept repairing; in parentheses, how many of them then ended failed. First-attempt success counts these episodes; cumulative success at k = 1 (episodes that ended after one attempt) does not.
- Exec. time: total OpenROAD execution time per episode; wall time: whole episode incl. LLM calls.

| Configuration | RAG | Feedback | Max attempts | Episodes | Completion % (mean ± SD) | Per run % | First-attempt % | Recovery % | Correct attempt 1 rejected (then lost) | Failed exec./task | Final exec. failure % | Attempts | Exec. time (s) | Wall time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | none | no | 1 | 150 | 4.0 ± 0.0 | 4.0 / 4.0 / 4.0 | 4.0 ± 0.0 | n/a | n/a | 0.94 | 94.0 | 1.00 | 0.4 | 113.7 |
| B_rag | hybrid | no | 1 | 150 | 32.7 ± 3.1 | 32.0 / 30.0 / 36.0 | 32.7 ± 3.1 | n/a | n/a | 0.57 | 57.3 | 1.00 | 0.6 | 77.8 |
| C_feedback | none | yes | 4 | 150 | 13.3 ± 2.3 | 16.0 / 12.0 / 12.0 | 4.0 ± 2.0 | 9.7 (14/144) | 0 (0) | 3.29 | 72.7 | 3.62 | 1.5 | 439.9 |
| D_full | hybrid | yes | 4 | 150 | 48.0 ± 6.0 | 54.0 / 48.0 / 42.0 | 31.3 ± 1.2 | 24.3 (25/103) | 2 (0) | 1.45 | 20.7 | 2.43 | 3.6 | 210.1 |
| E_vector_only | vector | yes | 4 | 150 | 46.0 ± 4.0 | 50.0 / 42.0 / 46.0 | 25.3 ± 5.8 | 30.4 (34/112) | 3 (3) | 1.67 | 24.7 | 2.57 | 1.6 | 217.7 |
| F_single_repair | hybrid | yes | 2 | 150 | 43.3 ± 1.2 | 44.0 / 44.0 / 42.0 | 30.0 ± 5.3 | 21.9 (23/105) | 3 (3) | 0.99 | 40.0 | 1.66 | 1.1 | 81.7 |
| G_targeted_repair | hybrid | yes | 4 | 150 | 53.3 ± 5.0 | 58.0 / 54.0 / 48.0 | 31.3 ± 1.2 | 32.0 (33/103) | 2 (0) | 1.42 | 20.7 | 2.40 | 3.9 | 167.0 |
