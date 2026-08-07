# Error types

- Outcome = 'success', the executor error type, or 'validation_failure' (script ran cleanly but the validator failed). Cells: count (%).

## Attempt 1 outcome (% of episodes)

| Outcome | A_baseline | B_rag | C_feedback | D_full | E_vector_only | F_single_repair | G_targeted_repair |
|---|---|---|---|---|---|---|---|
| success | 6 (4.0%) | 49 (32.7%) | 6 (4.0%) | 47 (31.3%) | 38 (25.3%) | 45 (30.0%) | 47 (31.3%) |
| validation_failure | 3 (2.0%) | 15 (10.0%) | 6 (4.0%) | 15 (10.0%) | 11 (7.3%) | 16 (10.7%) | 15 (10.0%) |
| invalid_command | 91 (60.7%) | 36 (24.0%) | 96 (64.0%) | 29 (19.3%) | 46 (30.7%) | 43 (28.7%) | 29 (19.3%) |
| invalid_argument | 40 (26.7%) | 22 (14.7%) | 33 (22.0%) | 28 (18.7%) | 33 (22.0%) | 23 (15.3%) | 28 (18.7%) |
| tcl_syntax | 1 (0.7%) | 0 | 0 | 0 | 0 | 0 | 0 |
| missing_prerequisite | 1 (0.7%) | 0 | 0 | 0 | 0 | 0 | 0 |
| missing_file | 1 (0.7%) | 0 | 1 (0.7%) | 0 | 1 (0.7%) | 1 (0.7%) | 0 |
| incorrect_design_context | 0 | 1 (0.7%) | 0 | 0 | 1 (0.7%) | 0 | 0 |
| runtime_failure | 0 | 0 | 0 | 1 (0.7%) | 0 | 1 (0.7%) | 1 (0.7%) |
| unsafe_command | 1 (0.7%) | 2 (1.3%) | 0 | 6 (4.0%) | 2 (1.3%) | 2 (1.3%) | 6 (4.0%) |
| tool_error | 6 (4.0%) | 25 (16.7%) | 8 (5.3%) | 24 (16.0%) | 18 (12.0%) | 19 (12.7%) | 24 (16.0%) |
| total | 150 | 150 | 150 | 150 | 150 | 150 | 150 |

## Final outcome (% of episodes)

| Outcome | A_baseline | B_rag | C_feedback | D_full | E_vector_only | F_single_repair | G_targeted_repair |
|---|---|---|---|---|---|---|---|
| success | 6 (4.0%) | 49 (32.7%) | 20 (13.3%) | 72 (48.0%) | 69 (46.0%) | 65 (43.3%) | 80 (53.3%) |
| validation_failure | 3 (2.0%) | 15 (10.0%) | 21 (14.0%) | 47 (31.3%) | 44 (29.3%) | 25 (16.7%) | 39 (26.0%) |
| invalid_command | 91 (60.7%) | 36 (24.0%) | 75 (50.0%) | 8 (5.3%) | 12 (8.0%) | 18 (12.0%) | 6 (4.0%) |
| invalid_argument | 40 (26.7%) | 22 (14.7%) | 17 (11.3%) | 7 (4.7%) | 11 (7.3%) | 12 (8.0%) | 8 (5.3%) |
| tcl_syntax | 1 (0.7%) | 0 | 1 (0.7%) | 1 (0.7%) | 2 (1.3%) | 0 | 1 (0.7%) |
| missing_prerequisite | 1 (0.7%) | 0 | 0 | 0 | 0 | 0 | 0 |
| missing_file | 1 (0.7%) | 0 | 1 (0.7%) | 0 | 0 | 0 | 0 |
| incorrect_design_context | 0 | 1 (0.7%) | 0 | 3 (2.0%) | 2 (1.3%) | 2 (1.3%) | 3 (2.0%) |
| runtime_failure | 0 | 0 | 0 | 2 (1.3%) | 1 (0.7%) | 1 (0.7%) | 2 (1.3%) |
| unsafe_command | 1 (0.7%) | 2 (1.3%) | 1 (0.7%) | 1 (0.7%) | 0 | 1 (0.7%) | 1 (0.7%) |
| tool_error | 6 (4.0%) | 25 (16.7%) | 14 (9.3%) | 9 (6.0%) | 9 (6.0%) | 26 (17.3%) | 10 (6.7%) |
| total | 150 | 150 | 150 | 150 | 150 | 150 | 150 |

## All failed executions (% of failed executions)

| Outcome | A_baseline | B_rag | C_feedback | D_full | E_vector_only | F_single_repair | G_targeted_repair |
|---|---|---|---|---|---|---|---|
| invalid_command | 91 (64.5%) | 36 (41.9%) | 322 (65.3%) | 61 (28.0%) | 91 (36.3%) | 61 (40.9%) | 58 (27.2%) |
| invalid_argument | 40 (28.4%) | 22 (25.6%) | 106 (21.5%) | 62 (28.4%) | 86 (34.3%) | 35 (23.5%) | 60 (28.2%) |
| tcl_syntax | 1 (0.7%) | 0 | 6 (1.2%) | 1 (0.5%) | 3 (1.2%) | 0 | 3 (1.4%) |
| missing_prerequisite | 1 (0.7%) | 0 | 0 | 1 (0.5%) | 0 | 0 | 0 |
| missing_file | 1 (0.7%) | 0 | 2 (0.4%) | 2 (0.9%) | 3 (1.2%) | 1 (0.7%) | 2 (0.9%) |
| incorrect_design_context | 0 | 1 (1.2%) | 0 | 7 (3.2%) | 7 (2.8%) | 2 (1.3%) | 6 (2.8%) |
| runtime_failure | 0 | 0 | 0 | 4 (1.8%) | 2 (0.8%) | 2 (1.3%) | 4 (1.9%) |
| unsafe_command | 1 (0.7%) | 2 (2.3%) | 4 (0.8%) | 9 (4.1%) | 2 (0.8%) | 3 (2.0%) | 9 (4.2%) |
| tool_error | 6 (4.3%) | 25 (29.1%) | 53 (10.8%) | 71 (32.6%) | 57 (22.7%) | 45 (30.2%) | 71 (33.3%) |
| total | 141 | 86 | 493 | 218 | 251 | 149 | 213 |
