# Final Benchmark Analysis - eil51

Generated at: 2026-04-25 21:51:58

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030507.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030507.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 5 | 430.000 | 433.100 | 2.155 | 1881.0 | 0.94 |
| 2 | PSO | 6 | 428.000 | 433.500 | 2.177 | 1826.3 | 0.47 |
| 3 | 2-opt | 4 | 428.000 | 439.433 | 5.117 | 1398.8 | 0.47 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 2-opt | 1398.8 | 439.433 |
| 2 | PSO | 1826.3 | 433.500 |
| 3 | GA | 1881.0 | 433.100 |

## ANOVA (duration across algorithms)

F(2, 87) = 31.8272, eta^2 = 0.4225

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 2-opt | GA | 29 | 7.000 | 4 | 25 | 23.000 | -4.206 | 0.000026 | 0.000078 | yes |
| 2-opt | PSO | 29 | 6.000 | 4 | 25 | 30.000 | -4.054 | 0.000050 | 0.000101 | yes |
| GA | PSO | 28 | -1.000 | 17 | 11 | 166.500 | -0.831 | 0.405885 | 0.405885 | no |

## Auto Comments

1. Best average quality: GA (mean=433.100, best=430.000).
2. Fastest algorithm: 2-opt (mean time=1398.8 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: eil51}
  \label{tab:results_eil51}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    GA & 430.00 & 433.10 & 2.16 & 1881.0 & 0.94 \\
    PSO & 428.00 & 433.50 & 2.18 & 1826.3 & 0.47 \\
    2-opt & 428.00 & 439.43 & 5.12 & 1398.8 & 0.47 \\
    \hline
  \end{tabular}
\end{table}
```
