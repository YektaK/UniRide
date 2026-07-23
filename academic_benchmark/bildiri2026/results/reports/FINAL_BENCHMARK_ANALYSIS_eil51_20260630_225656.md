# Final Benchmark Analysis - eil51

Generated at: 2026-06-30 22:56:56

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260630_225508.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260630_225508.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | GA | 49 | 427.000 | 432.967 | 2.371 | 1524.1 | 0.23 |
| 2 | PSO | 50 | 427.000 | 433.100 | 2.820 | 1206.9 | 0.23 |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | PSO | 1206.9 | 433.100 |
| 2 | GA | 1524.1 | 432.967 |

## ANOVA (duration across algorithms)

F(1, 58) = 0.0393, eta^2 = 0.0007

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| GA | PSO | 28 | 1.000 | 13 | 15 | 192.000 | -0.250 | 0.802212 | 0.802212 | no |

## Auto Comments

1. Best average quality: GA (mean=432.967, best=427.000).
2. Fastest algorithm: PSO (mean time=1206.9 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show no significant differences after Holm correction.

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
    GA & 427.00 & 432.97 & 2.37 & 1524.1 & 0.23 \\
    PSO & 427.00 & 433.10 & 2.82 & 1206.9 & 0.23 \\
    \hline
  \end{tabular}
\end{table}
```
