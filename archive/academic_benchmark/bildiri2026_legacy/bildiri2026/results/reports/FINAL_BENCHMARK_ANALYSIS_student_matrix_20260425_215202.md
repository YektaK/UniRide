# Final Benchmark Analysis - student_matrix

Generated at: 2026-04-25 21:52:02

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_090056.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_090056.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 17 | 314.000 | 314.167 | 0.648 | 2199.2 | - |
| 2 | PSO | 18 | 314.000 | 314.567 | 0.898 | 2117.0 | - |
| 3 | 2-opt | 16 | 314.000 | 316.167 | 1.931 | 3129.3 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | PSO | 2117.0 | 314.567 |
| 2 | GA | 2199.2 | 314.167 |
| 3 | 2-opt | 3129.3 | 316.167 |

## ANOVA (duration across algorithms)

F(2, 87) = 20.3424, eta^2 = 0.3186

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 20 | 3.000 | 1 | 19 | 11.000 | -3.509 | 0.000449 | 0.001348 | yes |
| 2-opt | PSO | 22 | 2.000 | 3 | 19 | 23.000 | -3.360 | 0.000779 | 0.001558 | yes |
| GA | PSO | 11 | -2.000 | 9 | 2 | 17.000 | -1.423 | 0.154860 | 0.154860 | no |

## Auto Comments

1. Best average quality: GA (mean=314.167, best=314.000).
2. Fastest algorithm: PSO (mean time=2117.0 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: student\_matrix}
  \label{tab:results_student_matrix}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    GA & 314.00 & 314.17 & 0.65 & 2199.2 & - \\
    PSO & 314.00 & 314.57 & 0.90 & 2117.0 & - \\
    2-opt & 314.00 & 316.17 & 1.93 & 3129.3 & - \\
    \hline
  \end{tabular}
\end{table}
```
