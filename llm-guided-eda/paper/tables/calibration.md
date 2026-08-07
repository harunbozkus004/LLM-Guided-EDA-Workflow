# Agent self-verification calibration

- Agent self-verification vs the hidden validator (feedback configurations). Episode level: agent_declared_success vs episode success; attempt level: agent_verdict_ok vs that attempt's validator verdict. Positive = success. Precision = TP/(TP+FP); recall = TP/(TP+FN); false-success rate = FP/(FP+TN), the share of validator failures the agent declared successful.

| Configuration | Level | Scored | No verdict | TP | FP | FN | TN | Precision % | Recall % | False-success % | Accuracy % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C_feedback | episode | 150 | 0 | 20 | 14 | 0 | 116 | 58.8 | 100.0 | 10.8 | 90.7 |
| C_feedback | attempt | 543 | 0 | 20 | 14 | 0 | 509 | 58.8 | 100.0 | 2.7 | 97.4 |
| D_full | episode | 150 | 0 | 70 | 38 | 2 | 40 | 64.8 | 97.2 | 48.7 | 73.3 |
| D_full | attempt | 364 | 0 | 70 | 38 | 5 | 251 | 64.8 | 93.3 | 13.1 | 88.2 |
| E_vector_only | episode | 150 | 0 | 69 | 37 | 0 | 44 | 65.1 | 100.0 | 45.7 | 75.3 |
| E_vector_only | attempt | 385 | 0 | 69 | 37 | 5 | 274 | 65.1 | 93.2 | 11.9 | 89.1 |
| F_single_repair | episode | 150 | 0 | 65 | 21 | 0 | 64 | 75.6 | 100.0 | 24.7 | 86.0 |
| F_single_repair | attempt | 249 | 0 | 65 | 21 | 3 | 160 | 75.6 | 95.6 | 11.6 | 90.4 |
| G_targeted_repair | episode | 150 | 0 | 80 | 32 | 0 | 38 | 71.4 | 100.0 | 45.7 | 78.7 |
| G_targeted_repair | attempt | 360 | 0 | 80 | 32 | 4 | 244 | 71.4 | 95.2 | 11.6 | 90.0 |
