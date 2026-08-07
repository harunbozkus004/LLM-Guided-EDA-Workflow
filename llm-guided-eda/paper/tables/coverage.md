# Data coverage

- Expected design: 50 tasks (source: metadata) x 3 runs (source: metadata); configurations from metadata.
- Malformed lines skipped: 0; records parsed after dropping unknown fields: 0; records of another split dropped: 0.
- Harness errors are episodes aborted by an exception in the experiment harness; they count as failures unless the report was built with --exclude-harness-errors (then they are missing episodes).

| Configuration | Expected | Recorded | Coverage % | Missing | Runs | Tasks | Harness errors | Duplicates dropped | Inconsistent records |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| B_rag | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| C_feedback | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| D_full | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| E_vector_only | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| F_single_repair | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
| G_targeted_repair | 150 | 150 | 100.0 | 0 | 1, 2, 3 | 50 | 0 | 0 | 0 |
