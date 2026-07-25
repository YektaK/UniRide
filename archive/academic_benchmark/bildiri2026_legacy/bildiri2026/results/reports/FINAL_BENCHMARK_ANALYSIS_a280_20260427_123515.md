# Final Benchmark Analysis - a280

Generated at: 2026-04-27 12:35:15

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_093256.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_093256.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | 3-opt | 22 | 13956.000 | 15851.600 | 812.845 | 8349.7 | 441.14 |
| 2 | 3-opt | 20 | 15085.000 | 16124.767 | 537.936 | 10639.3 | 484.92 |
| 3 | 3-opt | 21 | 14384.000 | 17023.100 | 1358.934 | 3445.4 | 457.74 |
| 4 | 3-opt | 19 | 20305.000 | 21354.700 | 713.969 | 4245.2 | 687.32 |
| 5 | 3-opt | 23 | 20211.000 | 21402.500 | 657.135 | 3974.4 | 683.68 |
| 6 | Or-opt | 27 | 22021.000 | 23203.367 | 627.507 | 3042.1 | 753.86 |
| 7 | Or-opt | 25 | 21201.000 | 23274.967 | 658.831 | 3026.3 | 722.06 |
| 8 | Or-opt | 31 | 21828.000 | 23275.433 | 629.623 | 2692.5 | 746.37 |
| 9 | Or-opt | 28 | 22108.000 | 23329.667 | 609.445 | 3571.9 | 757.23 |
| 10 | Or-opt | 24 | 22479.000 | 23447.533 | 527.320 | 2866.6 | 771.62 |
| 11 | Or-opt | 30 | 21878.000 | 23453.067 | 786.341 | 21386.1 | 748.31 |
| 12 | Or-opt | 29 | 22780.000 | 23492.800 | 393.680 | 2932.3 | 783.29 |
| 13 | Or-opt | 26 | 22059.000 | 23498.867 | 597.131 | 2441.3 | 755.33 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | Or-opt | 2441.3 | 23498.867 |
| 2 | Or-opt | 2692.5 | 23275.433 |
| 3 | Or-opt | 2866.6 | 23447.533 |
| 4 | Or-opt | 2932.3 | 23492.800 |
| 5 | Or-opt | 3026.3 | 23274.967 |
| 6 | Or-opt | 3042.1 | 23203.367 |
| 7 | 3-opt | 3445.4 | 17023.100 |
| 8 | Or-opt | 3571.9 | 23329.667 |
| 9 | 3-opt | 3974.4 | 21402.500 |
| 10 | 3-opt | 4245.2 | 21354.700 |
| 11 | 3-opt | 8349.7 | 15851.600 |
| 12 | 3-opt | 10639.3 | 16124.767 |
| 13 | Or-opt | 21386.1 | 23453.067 |

## ANOVA (duration across algorithms)

F(1, 388) = 793.8103, eta^2 = 0.6717

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 3-opt | Or-opt | 30 | -1760.500 | 30 | 0 | 0.000 | -4.782 | 0.000002 | 0.000002 | yes |

## Auto Comments

1. Best average quality: 3-opt (mean=15851.600, best=13956.000).
2. Fastest algorithm: Or-opt (mean time=2441.3 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: a280}
  \label{tab:results_a280}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    3-opt & 13956.00 & 15851.60 & 812.84 & 8349.7 & 441.14 \\
    3-opt & 15085.00 & 16124.77 & 537.94 & 10639.3 & 484.92 \\
    3-opt & 14384.00 & 17023.10 & 1358.93 & 3445.4 & 457.74 \\
    3-opt & 20305.00 & 21354.70 & 713.97 & 4245.2 & 687.32 \\
    3-opt & 20211.00 & 21402.50 & 657.13 & 3974.4 & 683.68 \\
    Or-opt & 22021.00 & 23203.37 & 627.51 & 3042.1 & 753.86 \\
    Or-opt & 21201.00 & 23274.97 & 658.83 & 3026.3 & 722.06 \\
    Or-opt & 21828.00 & 23275.43 & 629.62 & 2692.5 & 746.37 \\
    Or-opt & 22108.00 & 23329.67 & 609.44 & 3571.9 & 757.23 \\
    Or-opt & 22479.00 & 23447.53 & 527.32 & 2866.6 & 771.62 \\
    Or-opt & 21878.00 & 23453.07 & 786.34 & 21386.1 & 748.31 \\
    Or-opt & 22780.00 & 23492.80 & 393.68 & 2932.3 & 783.29 \\
    Or-opt & 22059.00 & 23498.87 & 597.13 & 2441.3 & 755.33 \\
    \hline
  \end{tabular}
\end{table}
```
