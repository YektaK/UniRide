# Final Benchmark Analysis - kroA100

Generated at: 2026-04-25 21:51:59

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030540.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030540.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 8 | 21292.000 | 21629.100 | 163.256 | 2535.1 | 0.05 |
| 2 | 2-opt | 7 | 21282.000 | 21667.433 | 173.359 | 2170.3 | 0.00 |
| 3 | PSO | 9 | 21421.000 | 21699.600 | 148.390 | 2548.2 | 0.65 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 2170.3 | 21667.433 |
| 2 | GA | 2535.1 | 21629.100 |
| 3 | PSO | 2548.2 | 21699.600 |

## ANOVA (duration across algorithms)

F(2, 87) = 1.4241, eta^2 = 0.0317

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| GA | PSO | 30 | -47.500 | 20 | 10 | 128.000 | -2.149 | 0.031603 | 0.094810 | no |
| 2-opt | GA | 30 | 26.000 | 13 | 17 | 188.500 | -0.905 | 0.365462 | 0.730923 | no |
| 2-opt | PSO | 30 | -35.500 | 16 | 14 | 196.500 | -0.740 | 0.459021 | 0.730923 | no |

## Auto Comments

1. Best average quality: GA (mean=21629.100, best=21292.000).
2. Fastest algorithm: 2-opt (mean time=2170.3 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show no significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: kroA100}
  \label{tab:results_kroa100}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    GA & 21292.00 & 21629.10 & 163.26 & 2535.1 & 0.05 \\
    2-opt & 21282.00 & 21667.43 & 173.36 & 2170.3 & 0.00 \\
    PSO & 21421.00 & 21699.60 & 148.39 & 2548.2 & 0.65 \\
    \hline
  \end{tabular}
\end{table}
```
