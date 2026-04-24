# Final Benchmark Analysis - student_matrix

Generated at: 2026-04-25 00:23:09

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_002216.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_002216.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 9 | 314.000 | 314.000 | 0.000 | 752.7 | - |
| 2 | PSO | 10 | 314.000 | 314.000 | 0.000 | 684.7 | - |
| 3 | 2-opt | 6 | 314.000 | 314.900 | 1.242 | 293.9 | - |
| 4 | 3-opt | 7 | 314.000 | 316.733 | 2.559 | 347.9 | - |
| 5 | Or-opt | 8 | 314.000 | 318.767 | 4.485 | 373.8 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 293.9 | 314.900 |
| 2 | 3-opt | 347.9 | 316.733 |
| 3 | Or-opt | 373.8 | 318.767 |
| 4 | PSO | 684.7 | 314.000 |
| 5 | GA | 752.7 | 314.000 |

## ANOVA (duration across algorithms)

F(4, 145) = 22.4567, eta^2 = 0.3825

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| GA | Or-opt | 21 | -7.000 | 21 | 0 | 0.000 | -4.015 | 0.000060 | 0.000596 | yes |
| Or-opt | PSO | 21 | 7.000 | 0 | 21 | 0.000 | -4.015 | 0.000060 | 0.000596 | yes |
| 3-opt | GA | 20 | 4.000 | 0 | 20 | 0.000 | -3.920 | 0.000089 | 0.000709 | yes |
| 3-opt | PSO | 20 | 4.000 | 0 | 20 | 0.000 | -3.920 | 0.000089 | 0.000709 | yes |
| 2-opt | Or-opt | 21 | -5.000 | 18 | 3 | 10.500 | -3.650 | 0.000263 | 0.001576 | yes |
| 2-opt | GA | 12 | 2.000 | 0 | 12 | 0.000 | -3.059 | 0.002218 | 0.011089 | yes |
| 2-opt | PSO | 12 | 2.000 | 0 | 12 | 0.000 | -3.059 | 0.002218 | 0.011089 | yes |
| 2-opt | 3-opt | 23 | -2.000 | 17 | 6 | 48.500 | -2.722 | 0.006486 | 0.019458 | yes |
| 3-opt | Or-opt | 24 | -1.000 | 15 | 9 | 93.000 | -1.629 | 0.103404 | 0.206808 | no |
| GA | PSO | 0 | 0.000 | 0 | 0 | 0.000 | 0.000 | 1.000000 | 1.000000 | no |

## Auto Comments

1. Best average quality: GA (mean=314.000, best=314.000).
2. Fastest algorithm: 2-opt (mean time=293.9 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 8 significant differences after Holm correction.
