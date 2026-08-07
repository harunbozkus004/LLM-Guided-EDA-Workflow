# Cumulative success by attempt

- % of episodes that ended successfully within k attempts (success and attempts used <= k), mean ± SD over runs.
- k = 1 can be lower than first-attempt success in the main results: an attempt 1 that passed the validator but was rejected by the agent's self-check did not end the episode, so it counts at a later k if a repair also passed, and never if the episode ended failed (see 'Correct attempt 1 rejected' in the main results).

| Configuration | k=1 | k=2 | k=3 | k=4 |
|---|---|---|---|---|
| A_baseline | 4.0 ± 0.0 | - | - | - |
| B_rag | 32.7 ± 3.1 | - | - | - |
| C_feedback | 4.0 ± 2.0 | 10.0 ± 2.0 | 11.3 ± 1.2 | 13.3 ± 2.3 |
| D_full | 30.0 ± 0.0 | 42.7 ± 4.2 | 44.0 ± 4.0 | 48.0 ± 6.0 |
| E_vector_only | 23.3 ± 5.8 | 36.7 ± 6.4 | 44.0 ± 5.3 | 46.0 ± 4.0 |
| F_single_repair | 28.0 ± 5.3 | 43.3 ± 1.2 | - | - |
| G_targeted_repair | 30.0 ± 0.0 | 43.3 ± 4.6 | 47.3 ± 3.1 | 53.3 ± 5.0 |
