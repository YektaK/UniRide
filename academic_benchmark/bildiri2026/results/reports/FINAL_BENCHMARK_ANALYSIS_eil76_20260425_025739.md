# Final Benchmark Analysis - eil76

Generated at: 2026-04-25 02:57:39

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_025718.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_025718.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | PSO | 6 | 550.000 | 557.100 | 3.725 | 2526.8 | 2.23 |
| 2 | GA | 5 | 560.000 | 564.400 | 2.011 | 1954.2 | 4.09 |
| 3 | 2-opt | 4 | 558.000 | 568.200 | 5.160 | 1819.9 | 3.72 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 1819.9 | 568.200 |
| 2 | GA | 1954.2 | 564.400 |
| 3 | PSO | 2526.8 | 557.100 |

## ANOVA (duration across algorithms)

F(2, 27) = 21.4325, eta^2 = 0.6135

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | PSO | 10 | 10.500 | 0 | 10 | 0.000 | -2.803 | 0.005062 | 0.015186 | yes |
| GA | PSO | 10 | 7.500 | 0 | 10 | 0.000 | -2.803 | 0.005062 | 0.015186 | yes |
| 2-opt | GA | 8 | 5.500 | 1 | 7 | 5.500 | -1.750 | 0.080058 | 0.080058 | no |

## Auto Comments

1. Best average quality: PSO (mean=557.100, best=550.000).
2. Fastest algorithm: 2-opt (mean time=1819.9 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: eil76}
  \label{tab:results_eil76}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    PSO & 550.00 & 557.10 & 3.73 & 2526.8 & 2.23 \\
    GA & 560.00 & 564.40 & 2.01 & 1954.2 & 4.09 \\
    2-opt & 558.00 & 568.20 & 5.16 & 1819.9 & 3.72 \\
    \hline
  \end{tabular}
\end{table}
```
