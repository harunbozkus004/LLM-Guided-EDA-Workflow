# Error transitions (attempt 1 -> final)

- Episodes of multi-attempt configurations whose attempt 1 failed the validator, by the attempt-1 outcome. Recovered = the final attempt passed. The full attempt-1 -> final outcome matrix is in error_transitions.csv.

| Configuration | Attempt-1 outcome | Episodes | Recovered | Recovery % | Same failure at end | Mean attempts |
|---|---|---|---|---|---|---|
| C_feedback | validation_failure | 6 | 2 | 33.3 | 3 | 1.83 |
| C_feedback | invalid_command | 96 | 7 | 7.3 | 63 | 3.85 |
| C_feedback | invalid_argument | 33 | 5 | 15.2 | 6 | 3.67 |
| C_feedback | missing_file | 1 | 0 | 0.0 | 1 | 4.00 |
| C_feedback | tool_error | 8 | 0 | 0.0 | 2 | 3.88 |
| D_full | validation_failure | 15 | 0 | 0.0 | 13 | 1.93 |
| D_full | invalid_command | 29 | 10 | 34.5 | 3 | 2.93 |
| D_full | invalid_argument | 28 | 10 | 35.7 | 0 | 3.29 |
| D_full | runtime_failure | 1 | 0 | 0.0 | 0 | 2.00 |
| D_full | unsafe_command | 6 | 0 | 0.0 | 0 | 3.50 |
| D_full | tool_error | 24 | 5 | 20.8 | 3 | 3.42 |
| E_vector_only | validation_failure | 11 | 0 | 0.0 | 10 | 1.55 |
| E_vector_only | invalid_command | 46 | 23 | 50.0 | 4 | 2.98 |
| E_vector_only | invalid_argument | 33 | 6 | 18.2 | 5 | 3.45 |
| E_vector_only | missing_file | 1 | 0 | 0.0 | 0 | 4.00 |
| E_vector_only | incorrect_design_context | 1 | 1 | 100.0 | 0 | 2.00 |
| E_vector_only | unsafe_command | 2 | 0 | 0.0 | 0 | 3.00 |
| E_vector_only | tool_error | 18 | 4 | 22.2 | 1 | 3.22 |
| F_single_repair | validation_failure | 16 | 0 | 0.0 | 14 | 1.44 |
| F_single_repair | invalid_command | 43 | 13 | 30.2 | 9 | 2.00 |
| F_single_repair | invalid_argument | 23 | 5 | 21.7 | 4 | 2.00 |
| F_single_repair | missing_file | 1 | 1 | 100.0 | 0 | 2.00 |
| F_single_repair | runtime_failure | 1 | 0 | 0.0 | 0 | 2.00 |
| F_single_repair | unsafe_command | 2 | 0 | 0.0 | 0 | 2.00 |
| F_single_repair | tool_error | 19 | 4 | 21.1 | 11 | 2.00 |
| G_targeted_repair | validation_failure | 15 | 1 | 6.7 | 12 | 1.93 |
| G_targeted_repair | invalid_command | 29 | 13 | 44.8 | 1 | 2.90 |
| G_targeted_repair | invalid_argument | 28 | 10 | 35.7 | 3 | 3.32 |
| G_targeted_repair | runtime_failure | 1 | 0 | 0.0 | 0 | 2.00 |
| G_targeted_repair | unsafe_command | 6 | 1 | 16.7 | 0 | 3.00 |
| G_targeted_repair | tool_error | 24 | 8 | 33.3 | 5 | 3.38 |
