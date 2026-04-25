# Final Benchmark Analysis - st70

Generated at: 2026-04-25 21:52:00

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030656.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030656.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 14 | 677.000 | 684.033 | 3.643 | 2262.9 | 0.30 |
| 2 | PSO | 15 | 675.000 | 684.567 | 5.211 | 1963.4 | 0.00 |
| 3 | 2-opt | 13 | 676.000 | 692.100 | 8.010 | 1550.1 | 0.15 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 1550.1 | 692.100 |
| 2 | PSO | 1963.4 | 684.567 |
| 3 | GA | 2262.9 | 684.033 |

## ANOVA (duration across algorithms)

F(2, 87) = 17.5126, eta^2 = 0.2870

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 30 | 7.000 | 3 | 27 | 28.000 | -4.206 | 0.000026 | 0.000078 | yes |
| 2-opt | PSO | 27 | 9.000 | 4 | 23 | 41.000 | -3.556 | 0.000377 | 0.000754 | yes |
| GA | PSO | 28 | 1.000 | 13 | 15 | 181.000 | -0.501 | 0.616391 | 0.616391 | no |

## Auto Comments

1. Best average quality: GA (mean=684.033, best=677.000).
2. Fastest algorithm: 2-opt (mean time=1550.1 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: st70}
  \label{tab:results_st70}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    GA & 677.00 & 684.03 & 3.64 & 2262.9 & 0.30 \\
    PSO & 675.00 & 684.57 & 5.21 & 1963.4 & 0.00 \\
    2-opt & 676.00 & 692.10 & 8.01 & 1550.1 & 0.15 \\
    \hline
  \end{tabular}
\end{table}
```
