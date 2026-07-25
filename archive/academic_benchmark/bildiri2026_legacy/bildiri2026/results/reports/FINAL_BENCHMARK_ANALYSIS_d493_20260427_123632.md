# Final Benchmark Analysis - d493

Generated at: 2026-04-27 12:36:32

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_093256.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_093256.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | 3-opt | 22 | 231716.000 | 246085.200 | 5640.050 | 7724.0 | - |
| 2 | 3-opt | 20 | 232537.000 | 246716.900 | 6080.622 | 8516.8 | - |
| 3 | 3-opt | 21 | 233340.000 | 254677.900 | 10056.441 | 2308.9 | - |
| 4 | 3-opt | 23 | 293229.000 | 305787.933 | 6818.900 | 1838.4 | - |
| 5 | 3-opt | 19 | 287936.000 | 306128.433 | 7752.841 | 1902.5 | - |
| 6 | Or-opt | 31 | 355981.000 | 369576.467 | 6086.671 | 1664.3 | - |
| 7 | Or-opt | 24 | 356214.000 | 370106.133 | 5894.553 | 1836.0 | - |
| 8 | Or-opt | 26 | 355624.000 | 370284.533 | 6239.178 | 1915.9 | - |
| 9 | Or-opt | 25 | 359851.000 | 370346.500 | 5698.086 | 1805.5 | - |
| 10 | Or-opt | 29 | 355231.000 | 370509.500 | 7178.575 | 2031.2 | - |
| 11 | Or-opt | 30 | 352930.000 | 370873.100 | 6724.114 | 1912.8 | - |
| 12 | Or-opt | 28 | 356047.000 | 371500.233 | 8527.896 | 1757.1 | - |
| 13 | Or-opt | 27 | 364249.000 | 371821.200 | 4758.496 | 1601.1 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | Or-opt | 1601.1 | 371821.200 |
| 2 | Or-opt | 1664.3 | 369576.467 |
| 3 | Or-opt | 1757.1 | 371500.233 |
| 4 | Or-opt | 1805.5 | 370346.500 |
| 5 | Or-opt | 1836.0 | 370106.133 |
| 6 | 3-opt | 1838.4 | 305787.933 |
| 7 | 3-opt | 1902.5 | 306128.433 |
| 8 | Or-opt | 1912.8 | 370873.100 |
| 9 | Or-opt | 1915.9 | 370284.533 |
| 10 | Or-opt | 2031.2 | 370509.500 |
| 11 | 3-opt | 2308.9 | 254677.900 |
| 12 | 3-opt | 7724.0 | 246085.200 |
| 13 | 3-opt | 8516.8 | 246716.900 |

## ANOVA (duration across algorithms)

F(1, 388) = 2579.8461, eta^2 = 0.8693

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 3-opt | Or-opt | 30 | -63804.000 | 30 | 0 | 0.000 | -4.782 | 0.000002 | 0.000002 | yes |

## Auto Comments

1. Best average quality: 3-opt (mean=246085.200, best=231716.000).
2. Fastest algorithm: Or-opt (mean time=1601.1 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: d493}
  \label{tab:results_d493}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    3-opt & 231716.00 & 246085.20 & 5640.05 & 7724.0 & - \\
    3-opt & 232537.00 & 246716.90 & 6080.62 & 8516.8 & - \\
    3-opt & 233340.00 & 254677.90 & 10056.44 & 2308.9 & - \\
    3-opt & 293229.00 & 305787.93 & 6818.90 & 1838.4 & - \\
    3-opt & 287936.00 & 306128.43 & 7752.84 & 1902.5 & - \\
    Or-opt & 355981.00 & 369576.47 & 6086.67 & 1664.3 & - \\
    Or-opt & 356214.00 & 370106.13 & 5894.55 & 1836.0 & - \\
    Or-opt & 355624.00 & 370284.53 & 6239.18 & 1915.9 & - \\
    Or-opt & 359851.00 & 370346.50 & 5698.09 & 1805.5 & - \\
    Or-opt & 355231.00 & 370509.50 & 7178.57 & 2031.2 & - \\
    Or-opt & 352930.00 & 370873.10 & 6724.11 & 1912.8 & - \\
    Or-opt & 356047.00 & 371500.23 & 8527.90 & 1757.1 & - \\
    Or-opt & 364249.00 & 371821.20 & 4758.50 & 1601.1 & - \\
    \hline
  \end{tabular}
\end{table}
```
