# Statistical comparisons (planned contrasts)

- Δ = mean completion of b minus a over the tasks recorded for both (per-task success averaged over runs); 95% CI: percentile paired bootstrap over tasks (10,000 replicates, seed 20261106).
- McNemar: exact two-sided test on discordant pairs; 'runs' pairs (task, run) by run index, 'majority' pairs per-task majority outcomes (solved in more than half of the runs). a-only / b-only = pairs solved only by a / only by b.
- Wilcoxon signed-rank on per-task success rates, zero_method='pratt' (zero differences ranked, then dropped), asymptotic normal approximation with tie correction; p = 1 when every difference is zero.
- Holm-Bonferroni adjustment within each test family across the planned contrasts with data.
- Cochran's Q over 6 configurations (A_baseline, B_rag, C_feedback, D_full, E_vector_only, F_single_repair) on per-task majority outcomes of 50 tasks recorded for all of them: Q = 65.77, df = 5, p < 0.001.

| Contrast (a vs b) | Effect | Tasks | a % | b % | Δ b−a (pp) [95% CI] | McNemar runs: a-only/b-only | p runs (Holm) | McNemar majority: a-only/b-only | p majority (Holm) | Wilcoxon p (Holm) | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline vs B_rag | retrieval, single shot | 50 | 4.0 | 32.7 | 28.7 [18.7, 38.7] | 3/46 | <0.001 (<0.001) | 0/16 | <0.001 (<0.001) | <0.001 (<0.001) |  |
| A_baseline vs C_feedback | feedback + repair, no retrieval | 50 | 4.0 | 13.3 | 9.3 [3.3, 16.7] | 1/15 | <0.001 (0.002) | 0/7 | 0.016 (0.062) | 0.017 (0.052) |  |
| B_rag vs D_full | feedback + repair, with retrieval | 50 | 32.7 | 48.0 | 15.3 [7.3, 24.0] | 9/32 | <0.001 (0.002) | 2/10 | 0.039 (0.116) | <0.001 (0.002) |  |
| A_baseline vs D_full | full system vs baseline | 50 | 4.0 | 48.0 | 44.0 [32.7, 55.3] | 0/66 | <0.001 (<0.001) | 0/24 | <0.001 (<0.001) | <0.001 (<0.001) |  |
| D_full vs E_vector_only | vector-only vs hybrid retrieval | 50 | 48.0 | 46.0 | -2.0 [-10.0, 5.3] | 17/14 | 0.720 (0.720) | 4/2 | 0.688 (0.906) | 0.623 (0.974) |  |
| D_full vs F_single_repair | 2 vs 4 attempts | 50 | 48.0 | 43.3 | -4.7 [-12.7, 2.7] | 18/11 | 0.265 (0.530) | 5/2 | 0.453 (0.906) | 0.487 (0.974) |  |
