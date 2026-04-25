# Final Benchmark Analysis - eil76

Generated at: 2026-04-25 00:16:58

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_000642.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_000642.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | PSO | 10 | 548.000 | 558.767 | 4.133 | 1700.2 | 1.86 |
| 2 | GA | 9 | 551.000 | 559.200 | 3.595 | 2034.8 | 2.42 |
| 3 | 2-opt | 6 | 551.000 | 559.833 | 5.093 | 636.8 | 2.42 |
| 4 | 3-opt | 7 | 551.000 | 562.500 | 5.782 | 580.7 | 2.42 |
| 5 | Or-opt | 8 | 563.000 | 580.700 | 11.975 | 1416.7 | 4.65 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 3-opt | 580.7 | 562.500 |
| 2 | 2-opt | 636.8 | 559.833 |
| 3 | Or-opt | 1416.7 | 580.700 |
| 4 | PSO | 1700.2 | 558.767 |
| 5 | GA | 2034.8 | 559.200 |

## ANOVA (duration across algorithms)

F(4, 145) = 56.1830, eta^2 = 0.6078

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| GA | Or-opt | 30 | -20.000 | 30 | 0 | 0.000 | -4.782 | 0.000002 | 0.000017 | yes |
| Or-opt | PSO | 30 | 21.000 | 1 | 29 | 1.000 | -4.762 | 0.000002 | 0.000017 | yes |
| 2-opt | Or-opt | 29 | -18.000 | 29 | 0 | 0.000 | -4.703 | 0.000003 | 0.000021 | yes |
| 3-opt | Or-opt | 29 | -17.000 | 27 | 2 | 4.500 | -4.606 | 0.000004 | 0.000029 | yes |
| 3-opt | PSO | 29 | 4.000 | 11 | 18 | 103.500 | -2.465 | 0.013700 | 0.082198 | no |
| 3-opt | GA | 26 | 4.000 | 8 | 18 | 86.500 | -2.260 | 0.023795 | 0.118976 | no |
| 2-opt | 3-opt | 27 | -4.000 | 18 | 9 | 114.000 | -1.802 | 0.071565 | 0.286260 | no |
| 2-opt | GA | 27 | -1.000 | 14 | 13 | 172.500 | -0.396 | 0.691801 | 1.000000 | no |
| 2-opt | PSO | 30 | 1.000 | 13 | 17 | 188.000 | -0.915 | 0.360039 | 1.000000 | no |
| GA | PSO | 26 | 0.000 | 13 | 13 | 171.500 | -0.102 | 0.919081 | 1.000000 | no |

## Auto Comments

1. Best average quality: PSO (mean=558.767, best=548.000).
2. Fastest algorithm: 3-opt (mean time=580.7 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 4 significant differences after Holm correction.
