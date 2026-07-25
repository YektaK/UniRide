# Final Benchmark Analysis - a280

Generated at: 2026-04-25 02:52:55

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_025127.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_025127.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | PSO | 3 | 2742.000 | 2779.000 | 21.741 | 16106.9 | 6.32 |
| 2 | GA | 2 | 2738.000 | 2791.300 | 23.281 | 15229.6 | 6.17 |
| 3 | 2-opt | 1 | 4889.000 | 5944.800 | 530.672 | 32426.4 | 89.57 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | GA | 15229.6 | 2791.300 |
| 2 | PSO | 16106.9 | 2779.000 |
| 3 | 2-opt | 32426.4 | 5944.800 |

## ANOVA (duration across algorithms)

F(2, 27) = 353.2391, eta^2 = 0.9632

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 10 | 3235.000 | 0 | 10 | 0.000 | -2.803 | 0.005062 | 0.015186 | yes |
| 2-opt | PSO | 10 | 3231.500 | 0 | 10 | 0.000 | -2.803 | 0.005062 | 0.015186 | yes |
| GA | PSO | 10 | 9.000 | 3 | 7 | 14.000 | -1.376 | 0.168807 | 0.168807 | no |

## Auto Comments

1. Best average quality: PSO (mean=2779.000, best=2742.000).
2. Fastest algorithm: GA (mean time=15229.6 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

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
    PSO & 2742.00 & 2779.00 & 21.74 & 16106.9 & 6.32 \\
    GA & 2738.00 & 2791.30 & 23.28 & 15229.6 & 6.17 \\
    2-opt & 4889.00 & 5944.80 & 530.67 & 32426.4 & 89.57 \\
    \hline
  \end{tabular}
\end{table}
```
