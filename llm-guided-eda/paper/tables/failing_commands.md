# Most common failing commands

- First word of the failing script line, over the 1282 of 1551 failed executions whose failing line is known (policy rejections and timeouts have none). Per-configuration columns count occurrences ('-' = not among that configuration's top commands).

| Rank | Command | All | Most common error | A_baseline | B_rag | C_feedback | D_full | E_vector_only | F_single_repair | G_targeted_repair |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `set` | 500 (39.0%) | invalid_argument | 42 | 33 | 132 | 81 | 82 | 62 | 68 |
| 2 | `In` | 66 (5.1%) | invalid_command | - | - | 66 | - | - | - | - |
| 3 | `mkdir` | 40 (3.1%) | invalid_command | - | 4 | - | 8 | 13 | 6 | 9 |
| 4 | `place_pins` | 40 (3.1%) | tool_error | - | 4 | 5 | 8 | 7 | 7 | 9 |
| 5 | `legalize_placement` | 28 (2.2%) | invalid_command | 3 | 2 | 7 | 4 | 4 | 4 | 4 |
| 6 | `The` | 27 (2.1%) | invalid_command | - | - | 10 | 8 | 6 | - | 3 |
| 7 | `define_corners` | 27 (2.1%) | tool_error | - | 3 | - | 6 | 6 | 5 | 7 |
| 8 | `place_opt` | 20 (1.6%) | invalid_command | 3 | - | 9 | 2 | - | - | 2 |
| 9 | `cts` | 18 (1.4%) | invalid_command | 7 | - | 11 | - | - | - | - |
| 10 | `report_timing` | 18 (1.4%) | invalid_command | 5 | - | 13 | - | - | - | - |
| 11 | `extract_parasitics` | 14 (1.1%) | invalid_argument | - | - | 10 | - | - | - | - |
| 12 | `write_verilog` | 13 (1.0%) | invalid_argument | - | - | - | 2 | - | 2 | 2 |
| 13 | `puts` | 12 (0.9%) | invalid_argument | 5 | - | - | - | 4 | - | - |
| 14 | `check_drc` | 11 (0.9%) | invalid_command | - | - | - | 3 | 3 | 2 | 3 |
| 15 | `extract_rc` | 11 (0.9%) | invalid_command | 4 | - | 5 | - | - | - | - |
