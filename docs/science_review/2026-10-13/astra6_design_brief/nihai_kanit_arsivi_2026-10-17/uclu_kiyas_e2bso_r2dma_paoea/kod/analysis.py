import glob, json, itertools
import numpy as np, pandas as pd
from scipy import stats

rows = [json.loads(l) for p in glob.glob("results/bench_main_w*.jsonl") for l in open(p)]
df = pd.DataFrame(rows)
df["arm"] = df.apply(lambda r: r["alg"] + ("-noevo" if r.get("tag") == "noevo" else ""), axis=1)
ARMS = ["E2BSO", "R2DMA", "P-AOEA", "P-AOEA-noevo", "ILS", "GLS", "LKH"]
INST = ["eil101", "rd100", "lin105", "pr136", "pr152", "a280"]
df = df[df.arm.isin(ARMS)]
summ = (df.groupby(["inst", "arm"]).agg(n=("gap", "size"), gap_mean=("gap", "mean"), gap_sd=("gap", "std"),
        gap_best=("gap", "min"), opt_hits=("gap", lambda g: int((g < 1e-9).sum())), elapsed_mean=("elapsed", "mean"),
        iters_mean=("iterations", "mean")).reset_index())
summ.to_csv("results/bench_summary_by_instance.csv", index=False)
overall = (df.groupby("arm").agg(n=("gap", "size"), gap_mean=("gap", "mean"), gap_median=("gap", "median"),
           opt_hits=("gap", lambda g: int((g < 1e-9).sum())), elapsed_mean=("elapsed", "mean")).reindex(ARMS).reset_index())
overall.to_csv("results/bench_summary_overall.csv", index=False)

piv = df.pivot_table(index=["inst", "seed"], columns="arm", values="gap")
tests = []
for a, b in [("E2BSO", "ILS"), ("R2DMA", "ILS"), ("P-AOEA", "ILS"), ("P-AOEA", "P-AOEA-noevo"),
             ("E2BSO", "GLS"), ("P-AOEA", "GLS"), ("R2DMA", "GLS"), ("ILS", "GLS"),
             ("E2BSO", "LKH"), ("P-AOEA", "LKH"), ("R2DMA", "LKH"), ("E2BSO", "P-AOEA"), ("E2BSO", "R2DMA")]:
    sub = piv[[a, b]].dropna(); d = sub[a] - sub[b]
    if (d != 0).sum() == 0:
        p = 1.0
    else:
        p = stats.wilcoxon(sub[a], sub[b], zero_method="zsplit").pvalue
    tests.append(dict(a=a, b=b, n_pairs=len(sub), mean_diff=d.mean(), a_better=int((d < 0).sum()), ties=int((d == 0).sum()),
                      b_better=int((d > 0).sum()), wilcoxon_p=p))
tests = pd.DataFrame(tests)
# Holm correction
order = np.argsort(tests.wilcoxon_p.values); m = len(tests); adj = np.empty(m); run = 0
for k, i in enumerate(order):
    run = max(run, min(1, (m - k) * tests.wilcoxon_p.values[i])); adj[i] = run
tests["holm_p"] = adj
tests.to_csv("results/bench_wilcoxon.csv", index=False)
full = piv[ARMS].dropna()
fr = stats.friedmanchisquare(*[full[a] for a in ARMS])
ranks = full.rank(axis=1).mean().reindex(ARMS)
json.dump(dict(friedman_stat=fr.statistic, friedman_p=fr.pvalue, n_blocks=len(full), mean_ranks=ranks.to_dict()),
          open("results/bench_friedman.json", "w"), indent=1)
print(overall.round(3).to_string(index=False))
print(tests.round(4).to_string(index=False))
print("Friedman", fr, "\nmean ranks", ranks.round(2).to_dict())
