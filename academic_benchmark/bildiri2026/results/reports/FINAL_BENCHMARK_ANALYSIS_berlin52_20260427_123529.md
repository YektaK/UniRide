# Final Benchmark Analysis - berlin52

Generated at: 2026-04-27 12:35:29

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_093256.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_093256.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | 3-opt | 23 | 7672.000 | 7935.233 | 108.213 | 2176.4 | 1.72 |
| 2 | 3-opt | 19 | 7542.000 | 7944.133 | 153.060 | 1189.7 | 0.00 |
| 3 | 3-opt | 20 | 7657.000 | 7951.733 | 133.495 | 2254.1 | 1.52 |
| 4 | 3-opt | 22 | 7542.000 | 7974.600 | 139.552 | 2309.1 | 0.00 |
| 5 | Or-opt | 24 | 7673.000 | 8024.800 | 219.320 | 2980.1 | 1.74 |
| 6 | Or-opt | 29 | 7714.000 | 8029.667 | 197.044 | 2460.5 | 2.28 |
| 7 | Or-opt | 30 | 7673.000 | 8031.433 | 150.822 | 2251.1 | 1.74 |
| 8 | Or-opt | 28 | 7714.000 | 8061.100 | 177.108 | 3015.0 | 2.28 |
| 9 | Or-opt | 26 | 7542.000 | 8063.933 | 233.800 | 2608.8 | 0.00 |
| 10 | Or-opt | 25 | 7714.000 | 8087.567 | 192.579 | 2566.7 | 2.28 |
| 11 | Or-opt | 27 | 7542.000 | 8088.433 | 235.105 | 2786.7 | 0.00 |
| 12 | Or-opt | 31 | 7640.000 | 8115.733 | 255.954 | 2956.6 | 1.30 |
| 13 | 3-opt | 21 | 7758.000 | 8209.500 | 218.744 | 2453.6 | 2.86 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 3-opt | 1189.7 | 7944.133 |
| 2 | 3-opt | 2176.4 | 7935.233 |
| 3 | Or-opt | 2251.1 | 8031.433 |
| 4 | 3-opt | 2254.1 | 7951.733 |
| 5 | 3-opt | 2309.1 | 7974.600 |
| 6 | 3-opt | 2453.6 | 8209.500 |
| 7 | Or-opt | 2460.5 | 8029.667 |
| 8 | Or-opt | 2566.7 | 8087.567 |
| 9 | Or-opt | 2608.8 | 8063.933 |
| 10 | Or-opt | 2786.7 | 8088.433 |
| 11 | Or-opt | 2956.6 | 8115.733 |
| 12 | Or-opt | 2980.1 | 8024.800 |
| 13 | Or-opt | 3015.0 | 8061.100 |

## ANOVA (duration across algorithms)

F(1, 388) = 8.2114, eta^2 = 0.0207

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 3-opt | Or-opt | 30 | -133.000 | 23 | 7 | 87.000 | -2.993 | 0.002765 | 0.002765 | yes |

## Auto Comments

1. Best average quality: 3-opt (mean=7935.233, best=7672.000).
2. Fastest algorithm: 3-opt (mean time=1189.7 ms).
3. Same algorithm leads in both quality and speed for this problem.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: berlin52}
  \label{tab:results_berlin52}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    3-opt & 7672.00 & 7935.23 & 108.21 & 2176.4 & 1.72 \\
    3-opt & 7542.00 & 7944.13 & 153.06 & 1189.7 & 0.00 \\
    3-opt & 7657.00 & 7951.73 & 133.49 & 2254.1 & 1.52 \\
    3-opt & 7542.00 & 7974.60 & 139.55 & 2309.1 & 0.00 \\
    Or-opt & 7673.00 & 8024.80 & 219.32 & 2980.1 & 1.74 \\
    Or-opt & 7714.00 & 8029.67 & 197.04 & 2460.5 & 2.28 \\
    Or-opt & 7673.00 & 8031.43 & 150.82 & 2251.1 & 1.74 \\
    Or-opt & 7714.00 & 8061.10 & 177.11 & 3015.0 & 2.28 \\
    Or-opt & 7542.00 & 8063.93 & 233.80 & 2608.8 & 0.00 \\
    Or-opt & 7714.00 & 8087.57 & 192.58 & 2566.7 & 2.28 \\
    Or-opt & 7542.00 & 8088.43 & 235.11 & 2786.7 & 0.00 \\
    Or-opt & 7640.00 & 8115.73 & 255.95 & 2956.6 & 1.30 \\
    3-opt & 7758.00 & 8209.50 & 218.74 & 2453.6 & 2.86 \\
    \hline
  \end{tabular}
\end{table}
```
