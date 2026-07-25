Final Benchmark Analysis - Total

Final Benchmark Analysis - berlin52

Generated at: 2026-04-25 21:51:57

Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030432.csv

Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030432.csv

## Quality Ranking (lower mean is better)

| Rank | Algorithm | ModelID | Best     | Mean     | StdDev  | MeanTimeMS | Gap% (best) |
| ---- | --------- | ------- | -------- | -------- | ------- | ---------- | ----------- |
| 1    | GA        | 2       | 7542.000 | 7678.467 | 99.379  | 1698.8     | 0.00        |
| 2    | PSO       | 3       | 7542.000 | 7719.600 | 89.781  | 1756.5     | 0.00        |
| 3    | 2-opt     | 1       | 7596.000 | 7932.933 | 154.885 | 1556.7     | 0.72        |

## Speed Ranking (lower mean time is better)

| Rank | Algorithm | MeanTimeMS | MeanQuality |
| ---- | --------- | ---------- | ----------- |
| 1    | 2-opt     | 1556.7     | 7932.933    |
| 2    | GA        | 1698.8     | 7678.467    |
| 3    | PSO       | 1756.5     | 7719.600    |

## ANOVA (duration across algorithms)

F(2, 87) = 40.0550, eta^2 = 0.4794

Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.

## Pairwise Wilcoxon (paired by run_idx, Holm corrected)

| A     | B   | n   | median(A-B) | A better runs | B better runs | W       | z      | p        | p_holm   | sig(0.05) |
| ----- | --- | --- | ----------- | ------------- | ------------- | ------- | ------ | -------- | -------- | --------- |
| 2-opt | GA  | 29  | 219.000     | 2             | 27            | 8.000   | -4.530 | 0.000006 | 0.000018 | yes       |
| 2-opt | PSO | 30  | 222.500     | 4             | 26            | 24.000  | -4.288 | 0.000018 | 0.000036 | yes       |
| GA    | PSO | 30  | -32.000     | 19            | 11            | 156.500 | -1.563 | 0.118007 | 0.118007 | no        |

## Auto Comments

1. Best average quality: GA (mean=7678.467, best=7542.000).
2. Fastest algorithm: 2-opt (mean time=1556.7 ms).
3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
4. Pairwise tests show 2 significant differences after Holm correction.

## LaTeX Table (Academic Output)

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
    
    # Final Benchmark Analysis - eil51
    
    Generated at: 2026-04-25 21:51:58
    
    Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030507.csv
    
    Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030507.csv
    
    ## Quality Ranking (lower mean is better)
    
    | Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 1   | GA  | 5   | 430.000 | 433.100 | 2.155 | 1881.0 | 0.94 |
    | 2   | PSO | 6   | 428.000 | 433.500 | 2.177 | 1826.3 | 0.47 |
    | 3   | 2-opt | 4   | 428.000 | 439.433 | 5.117 | 1398.8 | 0.47 |
    
    ## Speed Ranking (lower mean time is better)
    
    | Rank | Algorithm | MeanTimeMS | MeanQuality |
    | --- | --- | --- | --- |
    | 1   | 2-opt | 1398.8 | 439.433 |
    | 2   | PSO | 1826.3 | 433.500 |
    | 3   | GA  | 1881.0 | 433.100 |
    
    ## ANOVA (duration across algorithms)
    
    F(2, 87) = 31.8272, eta^2 = 0.4225
    
    Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.
    
    ## Pairwise Wilcoxon (paired by run_idx, Holm corrected)
    
    | A   | B   | n   | median(A-B) | A better runs | B better runs | W   | z   | p   | p_holm | sig(0.05) |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | 2-opt | GA  | 29  | 7.000 | 4   | 25  | 23.000 | -4.206 | 0.000026 | 0.000078 | yes |
    | 2-opt | PSO | 29  | 6.000 | 4   | 25  | 30.000 | -4.054 | 0.000050 | 0.000101 | yes |
    | GA  | PSO | 28  | -1.000 | 17  | 11  | 166.500 | -0.831 | 0.405885 | 0.405885 | no  |
    
    ## Auto Comments
    
    1. Best average quality: GA (mean=433.100, best=430.000).
    2. Fastest algorithm: 2-opt (mean time=1398.8 ms).
    3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
    4. Pairwise tests show 2 significant differences after Holm correction.
    
    ## LaTeX Table (Academic Output)
    
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
    # Final Benchmark Analysis - kroA100
    
    Generated at: 2026-04-25 21:51:59
    
    Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030540.csv
    
    Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030540.csv
    
    ## Quality Ranking (lower mean is better)
    
    | Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 1   | GA  | 8   | 21292.000 | 21629.100 | 163.256 | 2535.1 | 0.05 |
    | 2   | 2-opt | 7   | 21282.000 | 21667.433 | 173.359 | 2170.3 | 0.00 |
    | 3   | PSO | 9   | 21421.000 | 21699.600 | 148.390 | 2548.2 | 0.65 |
    
    ## Speed Ranking (lower mean time is better)
    
    | Rank | Algorithm | MeanTimeMS | MeanQuality |
    | --- | --- | --- | --- |
    | 1   | 2-opt | 2170.3 | 21667.433 |
    | 2   | GA  | 2535.1 | 21629.100 |
    | 3   | PSO | 2548.2 | 21699.600 |
    
    ## ANOVA (duration across algorithms)
    
    F(2, 87) = 1.4241, eta^2 = 0.0317
    
    Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.
    
    ## Pairwise Wilcoxon (paired by run_idx, Holm corrected)
    
    | A   | B   | n   | median(A-B) | A better runs | B better runs | W   | z   | p   | p_holm | sig(0.05) |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | GA  | PSO | 30  | -47.500 | 20  | 10  | 128.000 | -2.149 | 0.031603 | 0.094810 | no  |
    | 2-opt | GA  | 30  | 26.000 | 13  | 17  | 188.500 | -0.905 | 0.365462 | 0.730923 | no  |
    | 2-opt | PSO | 30  | -35.500 | 16  | 14  | 196.500 | -0.740 | 0.459021 | 0.730923 | no  |
    
    ## Auto Comments
    
    1. Best average quality: GA (mean=21629.100, best=21292.000).
    2. Fastest algorithm: 2-opt (mean time=2170.3 ms).
    3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
    4. Pairwise tests show no significant differences after Holm correction.
    
    ## LaTeX Table (Academic Output)
    
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
        \end{table}# Final Benchmark Analysis - rd100
    
    Generated at: 2026-04-25 21:52:00
    
    Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030618.csv
    
    Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030618.csv
    
    ## Quality Ranking (lower mean is better)
    
    | Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 1   | GA  | 11  | 8001.000 | 8139.933 | 89.955 | 2619.7 | -   |
    | 2   | PSO | 12  | 8022.000 | 8200.567 | 92.352 | 1748.0 | -   |
    | 3   | 2-opt | 10  | 8031.000 | 8265.900 | 120.597 | 2033.6 | -   |
    
    ## Speed Ranking (lower mean time is better)
    
    | Rank | Algorithm | MeanTimeMS | MeanQuality |
    | --- | --- | --- | --- |
    | 1   | PSO | 1748.0 | 8200.567 |
    | 2   | 2-opt | 2033.6 | 8265.900 |
    | 3   | GA  | 2619.7 | 8139.933 |
    
    ## ANOVA (duration across algorithms)
    
    F(2, 87) = 11.4614, eta^2 = 0.2085
    
    Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.
    
    ## Pairwise Wilcoxon (paired by run_idx, Holm corrected)
    
    | A   | B   | n   | median(A-B) | A better runs | B better runs | W   | z   | p   | p_holm | sig(0.05) |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | 2-opt | GA  | 29  | 124.000 | 4   | 25  | 56.000 | -3.492 | 0.000479 | 0.001437 | yes |
    | 2-opt | PSO | 30  | 50.500 | 12  | 18  | 138.500 | -1.933 | 0.053184 | 0.064854 | no  |
    | GA  | PSO | 30  | -41.000 | 19  | 11  | 128.500 | -2.139 | 0.032427 | 0.064854 | no  |
    
    ## Auto Comments
    
    1. Best average quality: GA (mean=8139.933, best=8001.000).
    2. Fastest algorithm: PSO (mean time=1748.0 ms).
    3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
    4. Pairwise tests show 1 significant differences after Holm correction.
    
    ## LaTeX Table (Academic Output)
    
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
    # Final Benchmark Analysis - st70
    
    Generated at: 2026-04-25 21:52:00
    
    Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_030656.csv
    
    Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_030656.csv
    
    ## Quality Ranking (lower mean is better)
    
    | Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 1   | GA  | 14  | 677.000 | 684.033 | 3.643 | 2262.9 | 0.30 |
    | 2   | PSO | 15  | 675.000 | 684.567 | 5.211 | 1963.4 | 0.00 |
    | 3   | 2-opt | 13  | 676.000 | 692.100 | 8.010 | 1550.1 | 0.15 |
    
    ## Speed Ranking (lower mean time is better)
    
    | Rank | Algorithm | MeanTimeMS | MeanQuality |
    | --- | --- | --- | --- |
    | 1   | 2-opt | 1550.1 | 692.100 |
    | 2   | PSO | 1963.4 | 684.567 |
    | 3   | GA  | 2262.9 | 684.033 |
    
    ## ANOVA (duration across algorithms)
    
    F(2, 87) = 17.5126, eta^2 = 0.2870
    
    Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.
    
    ## Pairwise Wilcoxon (paired by run_idx, Holm corrected)
    
    | A   | B   | n   | median(A-B) | A better runs | B better runs | W   | z   | p   | p_holm | sig(0.05) |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | 2-opt | GA  | 30  | 7.000 | 3   | 27  | 28.000 | -4.206 | 0.000026 | 0.000078 | yes |
    | 2-opt | PSO | 27  | 9.000 | 4   | 23  | 41.000 | -3.556 | 0.000377 | 0.000754 | yes |
    | GA  | PSO | 28  | 1.000 | 13  | 15  | 181.000 | -0.501 | 0.616391 | 0.616391 | no  |
    
    ## Auto Comments
    
    1. Best average quality: GA (mean=684.033, best=677.000).
    2. Fastest algorithm: 2-opt (mean time=1550.1 ms).
    3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
    4. Pairwise tests show 2 significant differences after Holm correction.
    
    ## LaTeX Table (Academic Output)
    
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
    # Final Benchmark Analysis - student_matrix
    
    Generated at: 2026-04-25 21:52:02
    
    Source summary: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_summary_20260425_090056.csv
    
    Source progress: C:\Users\yekta\Masaüstü\AiCode\FirebaseUniRide\UniRide\academic_benchmark\bildiri2026\results\benchmark_progress_20260425_090056.csv
    
    ## Quality Ranking (lower mean is better)
    
    | Rank | Algorithm | ModelID | Best | Mean | StdDev | MeanTimeMS | Gap% (best) |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 1   | GA  | 17  | 314.000 | 314.167 | 0.648 | 2199.2 | -   |
    | 2   | PSO | 18  | 314.000 | 314.567 | 0.898 | 2117.0 | -   |
    | 3   | 2-opt | 16  | 314.000 | 316.167 | 1.931 | 3129.3 | -   |
    
    ## Speed Ranking (lower mean time is better)
    
    | Rank | Algorithm | MeanTimeMS | MeanQuality |
    | --- | --- | --- | --- |
    | 1   | PSO | 2117.0 | 314.567 |
    | 2   | GA  | 2199.2 | 314.167 |
    | 3   | 2-opt | 3129.3 | 316.167 |
    
    ## ANOVA (duration across algorithms)
    
    F(2, 87) = 20.3424, eta^2 = 0.3186
    
    Note: This script uses standard-library ANOVA summary (no scipy p-value). Use F and eta^2 for effect-size oriented reporting.
    
    ## Pairwise Wilcoxon (paired by run_idx, Holm corrected)
    
    | A   | B   | n   | median(A-B) | A better runs | B better runs | W   | z   | p   | p_holm | sig(0.05) |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | 2-opt | GA  | 20  | 3.000 | 1   | 19  | 11.000 | -3.509 | 0.000449 | 0.001348 | yes |
    | 2-opt | PSO | 22  | 2.000 | 3   | 19  | 23.000 | -3.360 | 0.000779 | 0.001558 | yes |
    | GA  | PSO | 11  | -2.000 | 9   | 2   | 17.000 | -1.423 | 0.154860 | 0.154860 | no  |
    
    ## Auto Comments
    
    1. Best average quality: GA (mean=314.167, best=314.000).
    2. Fastest algorithm: PSO (mean time=2117.0 ms).
    3. There is a quality-speed tradeoff: best quality and best speed belong to different algorithms.
    4. Pairwise tests show 2 significant differences after Holm correction.
    
    ## LaTeX Table (Academic Output)
    
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
