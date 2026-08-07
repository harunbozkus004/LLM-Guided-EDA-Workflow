# Statistical comparisons (follow-up contrasts)

- Δ = mean completion of b minus a over the tasks recorded for both (per-task success averaged over runs); 95% CI: percentile paired bootstrap over tasks (10,000 replicates, seed 20261106).
- McNemar: exact two-sided test on discordant pairs; 'runs' pairs (task, run) by run index, 'majority' pairs per-task majority outcomes (solved in more than half of the runs). a-only / b-only = pairs solved only by a / only by b.
- Wilcoxon signed-rank on per-task success rates, zero_method='pratt' (zero differences ranked, then dropped), asymptotic normal approximation with tie correction; p = 1 when every difference is zero.
- Follow-up contrasts were added after the planned analysis and form their own Holm family (one contrast: adjusted p = unadjusted p); the planned contrasts are unaffected.

| Contrast (a vs b) | Effect | Tasks | a % | b % | Δ b−a (pp) [95% CI] | McNemar runs: a-only/b-only | p runs (Holm) | McNemar majority: a-only/b-only | p majority (Holm) | Wilcoxon p (Holm) | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D_full vs G_targeted_repair | targeted syntax cards on repair | 50 | 48.0 | 53.3 | 5.3 [0.7, 10.7] | 2/10 | 0.039 (0.039) | 1/3 | 0.625 (0.625) | 0.033 (0.033) |  |
