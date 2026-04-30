# Final Benchmark Analysis - d1655

Generated at: 2026-04-27 12:35:46

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_093256.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_093256.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | 3-opt | 20 | 1881667.000 | 1911467.167 | 13179.471 | 25774.4 | - |
| 2 | 3-opt | 22 | 1888356.000 | 1912470.633 | 13648.266 | 24937.0 | - |
| 3 | 3-opt | 21 | 1909155.000 | 1938667.233 | 19682.126 | 24481.7 | - |
| 4 | 3-opt | 19 | 1967657.000 | 1999170.300 | 12910.635 | 4762.9 | - |
| 5 | 3-opt | 23 | 1961611.000 | 1999664.500 | 16442.912 | 4551.1 | - |
| 6 | Or-opt | 30 | 1990372.000 | 2036327.333 | 15703.557 | 5844.9 | - |
| 7 | Or-opt | 29 | 1997621.000 | 2036348.667 | 17614.260 | 6102.9 | - |
| 8 | Or-opt | 31 | 1987035.000 | 2037648.700 | 20798.493 | 5568.3 | - |
| 9 | Or-opt | 27 | 2016903.000 | 2037887.200 | 13310.121 | 6640.0 | - |
| 10 | Or-opt | 26 | 2003217.000 | 2038047.600 | 16007.663 | 6028.9 | - |
| 11 | Or-opt | 24 | 1992957.000 | 2038121.633 | 17590.378 | 7219.7 | - |
| 12 | Or-opt | 28 | 2010518.000 | 2038234.900 | 17284.703 | 5835.1 | - |
| 13 | Or-opt | 25 | 2008839.000 | 2038727.567 | 14893.226 | 8002.9 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | 3-opt | 4551.1 | 1999664.500 |
| 2 | 3-opt | 4762.9 | 1999170.300 |
| 3 | Or-opt | 5568.3 | 2037648.700 |
| 4 | Or-opt | 5835.1 | 2038234.900 |
| 5 | Or-opt | 5844.9 | 2036327.333 |
| 6 | Or-opt | 6028.9 | 2038047.600 |
| 7 | Or-opt | 6102.9 | 2036348.667 |
| 8 | Or-opt | 6640.0 | 2037887.200 |
| 9 | Or-opt | 7219.7 | 2038121.633 |
| 10 | Or-opt | 8002.9 | 2038727.567 |
| 11 | 3-opt | 24481.7 | 1938667.233 |
| 12 | 3-opt | 24937.0 | 1912470.633 |
| 13 | 3-opt | 25774.4 | 1911467.167 |

## ANOVA (duration across algorithms)

F(1, 388) = 776.4958, eta^2 = 0.6668

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 3-opt | Or-opt | 30 | -40871.000 | 28 | 2 | 10.000 | -4.576 | 0.000005 | 0.000005 | yes |

## Auto Comments

1. Best average quality: 3-opt (mean=1911467.167, best=1881667.000).
2. Fastest algorithm: 3-opt (mean time=4551.1 ms).
3. Same algorithm leads in both quality and speed for this problem.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: d1655}
  \label{tab:results_d1655}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    3-opt & 1881667.00 & 1911467.17 & 13179.47 & 25774.4 & - \\
    3-opt & 1888356.00 & 1912470.63 & 13648.27 & 24937.0 & - \\
    3-opt & 1909155.00 & 1938667.23 & 19682.13 & 24481.7 & - \\
    3-opt & 1967657.00 & 1999170.30 & 12910.64 & 4762.9 & - \\
    3-opt & 1961611.00 & 1999664.50 & 16442.91 & 4551.1 & - \\
    Or-opt & 1990372.00 & 2036327.33 & 15703.56 & 5844.9 & - \\
    Or-opt & 1997621.00 & 2036348.67 & 17614.26 & 6102.9 & - \\
    Or-opt & 1987035.00 & 2037648.70 & 20798.49 & 5568.3 & - \\
    Or-opt & 2016903.00 & 2037887.20 & 13310.12 & 6640.0 & - \\
    Or-opt & 2003217.00 & 2038047.60 & 16007.66 & 6028.9 & - \\
    Or-opt & 1992957.00 & 2038121.63 & 17590.38 & 7219.7 & - \\
    Or-opt & 2010518.00 & 2038234.90 & 17284.70 & 5835.1 & - \\
    Or-opt & 2008839.00 & 2038727.57 & 14893.23 & 8002.9 & - \\
    \hline
  \end{tabular}
\end{table}
```
