# Token usage and cost

- Per task = mean over all episodes. Per solved task = total over all episodes (failed ones included) divided by the number of successful episodes. Tokens = input + output + cache read + cache write. Costs are those recorded by the agent (list prices in config/model_config.yaml).

| Configuration | LLM calls/task | Input tok/task | Output tok/task | Cache-read tok/task | Cache-write tok/task | Cost/task (USD) | Cost/solved task (USD) | Tokens/solved task | Total cost (USD) |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 1.00 | 897 | 2411 | 221 | 0 | 0.0000 | 0.0000 | 88222 | 0.00 |
| B_rag | 1.00 | 2661 | 1244 | 339 | 0 | 0.0000 | 0.0000 | 12991 | 0.00 |
| C_feedback | 3.62 | 2529 | 9258 | 17758 | 0 | 0.0000 | 0.0000 | 221590 | 0.00 |
| D_full | 2.43 | 4239 | 3564 | 12393 | 0 | 0.0000 | 0.0000 | 42075 | 0.00 |
| E_vector_only | 2.57 | 5042 | 3753 | 11900 | 0 | 0.0000 | 0.0000 | 44988 | 0.00 |
| F_single_repair | 1.66 | 3135 | 1955 | 4009 | 0 | 0.0000 | 0.0000 | 20997 | 0.00 |
| G_targeted_repair | 2.40 | 6341 | 3709 | 10031 | 0 | 0.0000 | 0.0000 | 37653 | 0.00 |
