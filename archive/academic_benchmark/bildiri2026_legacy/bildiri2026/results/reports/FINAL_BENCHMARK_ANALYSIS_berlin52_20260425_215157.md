# Final Benchmark Analysis - berlin52

Generated at: 2026-04-25 21:51:57

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030432.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030432.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 2 | 7542.000 | 7678.467 | 99.379 | 1698.8 | 0.00 |
| 2 | PSO | 3 | 7542.000 | 7719.600 | 89.781 | 1756.5 | 0.00 |
| 3 | 2-opt | 1 | 7596.000 | 7932.933 | 154.885 | 1556.7 | 0.72 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 1556.7 | 7932.933 |
| 2 | GA | 1698.8 | 7678.467 |
| 3 | PSO | 1756.5 | 7719.600 |

## ANOVA (duration across algorithms)

F(2, 87) = 40.0550, eta^2 = 0.4794

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 29 | 219.000 | 2 | 27 | 8.000 | -4.530 | 0.000006 | 0.000018 | yes |
| 2-opt | PSO | 30 | 222.500 | 4 | 26 | 24.000 | -4.288 | 0.000018 | 0.000036 | yes |
| GA | PSO | 30 | -32.000 | 19 | 11 | 156.500 | -1.563 | 0.118007 | 0.118007 | no |

## Auto Comments

1. Best average quality: GA (mean=7678.467, best=7542.000).
2. Fastest algorithm: 2-opt (mean time=1556.7 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

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
    GA & 7542.00 & 7678.47 & 99.38 & 1698.8 & 0.00 \\
    PSO & 7542.00 & 7719.60 & 89.78 & 1756.5 & 0.00 \\
    2-opt & 7596.00 & 7932.93 & 154.88 & 1556.7 & 0.72 \\
    \hline
  \end{tabular}
\end{table}
```
