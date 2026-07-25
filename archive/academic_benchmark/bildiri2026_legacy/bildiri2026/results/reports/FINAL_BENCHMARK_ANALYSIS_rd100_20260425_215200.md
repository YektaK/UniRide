# Final Benchmark Analysis - rd100

Generated at: 2026-04-25 21:52:00

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030618.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030618.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 11 | 8001.000 | 8139.933 | 89.955 | 2619.7 | - |
| 2 | PSO | 12 | 8022.000 | 8200.567 | 92.352 | 1748.0 | - |
| 3 | 2-opt | 10 | 8031.000 | 8265.900 | 120.597 | 2033.6 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | PSO | 1748.0 | 8200.567 |
| 2 | 2-opt | 2033.6 | 8265.900 |
| 3 | GA | 2619.7 | 8139.933 |

## ANOVA (duration across algorithms)

F(2, 87) = 11.4614, eta^2 = 0.2085

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 29 | 124.000 | 4 | 25 | 56.000 | -3.492 | 0.000479 | 0.001437 | yes |
| 2-opt | PSO | 30 | 50.500 | 12 | 18 | 138.500 | -1.933 | 0.053184 | 0.064854 | no |
| GA | PSO | 30 | -41.000 | 19 | 11 | 128.500 | -2.139 | 0.032427 | 0.064854 | no |

## Auto Comments

1. Best average quality: GA (mean=8139.933, best=8001.000).
2. Fastest algorithm: PSO (mean time=1748.0 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: rd100}
  \label{tab:results_rd100}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    GA & 8001.00 & 8139.93 & 89.96 & 2619.7 & - \\
    PSO & 8022.00 & 8200.57 & 92.35 & 1748.0 & - \\
    2-opt & 8031.00 & 8265.90 & 120.60 & 2033.6 & - \\
    \hline
  \end{tabular}
\end{table}
```
