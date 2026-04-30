# Final Benchmark Analysis - d2103

Generated at: 2026-04-27 12:36:14

Source summary: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_093256.csv

Source progress: C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_093256.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
|------|-----------|---------|------|------|--------|------------|-------------|
| 1 | 3-opt | 22 | 2874663.000 | 2924105.433 | 21946.116 | 188216.3 | - |
| 2 | 3-opt | 20 | 2873434.000 | 2924466.233 | 20116.585 | 183837.1 | - |
| 3 | 3-opt | 21 | 2888003.000 | 2961829.867 | 31502.587 | 43287.0 | - |
| 4 | 3-opt | 23 | 2985097.000 | 3032748.633 | 19335.743 | 34451.7 | - |
| 5 | 3-opt | 19 | 2997039.000 | 3037515.400 | 21510.996 | 40679.2 | - |
| 6 | Or-opt | 24 | 3051320.000 | 3085788.867 | 17427.184 | 10838.8 | - |
| 7 | Or-opt | 28 | 3035615.000 | 3087720.700 | 20086.889 | 11229.3 | - |
| 8 | Or-opt | 29 | 3053842.000 | 3089932.533 | 19039.794 | 10032.2 | - |
| 9 | Or-opt | 31 | 3042694.000 | 3090647.800 | 22321.171 | 7369.7 | - |
| 10 | Or-opt | 30 | 3024989.000 | 3090657.300 | 24534.327 | 37204.0 | - |
| 11 | Or-opt | 25 | 3044551.000 | 3090892.300 | 21490.336 | 8478.5 | - |
| 12 | Or-opt | 26 | 3034348.000 | 3091187.033 | 20392.206 | 9523.6 | - |
| 13 | Or-opt | 27 | 3057933.000 | 3091436.733 | 18477.087 | 11062.1 | - |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
|------|-----------|------------|-------------|
| 1 | Or-opt | 7369.7 | 3090647.800 |
| 2 | Or-opt | 8478.5 | 3090892.300 |
| 3 | Or-opt | 9523.6 | 3091187.033 |
| 4 | Or-opt | 10032.2 | 3089932.533 |
| 5 | Or-opt | 10838.8 | 3085788.867 |
| 6 | Or-opt | 11062.1 | 3091436.733 |
| 7 | Or-opt | 11229.3 | 3087720.700 |
| 8 | 3-opt | 34451.7 | 3032748.633 |
| 9 | Or-opt | 37204.0 | 3090657.300 |
| 10 | 3-opt | 40679.2 | 3037515.400 |
| 11 | 3-opt | 43287.0 | 2961829.867 |
| 12 | 3-opt | 183837.1 | 2924466.233 |
| 13 | 3-opt | 188216.3 | 2924105.433 |

## ANOVA (duration across algorithms)

F(1, 388) = 834.3052, eta^2 = 0.6826

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A | B | n | median(A-B) | A better runs | B better runs | W | z | p | p_holm | sig(0.05) |
|---|---|---|-------------|---------------|---------------|---|---|---|--------|-----------|
| 3-opt | Or-opt | 30 | -55508.000 | 29 | 1 | 1.000 | -4.762 | 0.000002 | 0.000002 | yes |

## Auto Comments

1. Best average quality: 3-opt (mean=2924105.433, best=2874663.000).
2. Fastest algorithm: Or-opt (mean time=7369.7 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 1 significant differences after Holm correction.

## LaTeX Table (Academic Output)

```latex
\begin{table}[h]
  \centering
  \caption{Benchmark Results for Problem: d2103}
  \label{tab:results_d2103}
  \begin{tabular}{lccccc}
    \hline
    Algorithm & Best & Mean & Std.Dev & Time (ms) & Gap (\%) \\
    \hline
    3-opt & 2874663.00 & 2924105.43 & 21946.12 & 188216.3 & - \\
    3-opt & 2873434.00 & 2924466.23 & 20116.59 & 183837.1 & - \\
    3-opt & 2888003.00 & 2961829.87 & 31502.59 & 43287.0 & - \\
    3-opt & 2985097.00 & 3032748.63 & 19335.74 & 34451.7 & - \\
    3-opt & 2997039.00 & 3037515.40 & 21511.00 & 40679.2 & - \\
    Or-opt & 3051320.00 & 3085788.87 & 17427.18 & 10838.8 & - \\
    Or-opt & 3035615.00 & 3087720.70 & 20086.89 & 11229.3 & - \\
    Or-opt & 3053842.00 & 3089932.53 & 19039.79 & 10032.2 & - \\
    Or-opt & 3042694.00 & 3090647.80 & 22321.17 & 7369.7 & - \\
    Or-opt & 3024989.00 & 3090657.30 & 24534.33 & 37204.0 & - \\
    Or-opt & 3044551.00 & 3090892.30 & 21490.34 & 8478.5 & - \\
    Or-opt & 3034348.00 & 3091187.03 & 20392.21 & 9523.6 & - \\
    Or-opt & 3057933.00 & 3091436.73 & 18477.09 & 11062.1 & - \\
    \hline
  \end{tabular}
\end{table}
```
