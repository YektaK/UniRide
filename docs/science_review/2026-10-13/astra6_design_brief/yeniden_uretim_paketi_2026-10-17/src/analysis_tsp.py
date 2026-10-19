"""analysis.py results.jsonl prefix ref_arm other_arm[,other_arm...]
Writes <prefix>_summary.csv and <prefix>_wilcoxon.csv (paired by (inst, seed), Holm-corrected)."""
import sys, json
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


def holm(p):
    p = np.asarray(p, float); m = len(p); order = np.argsort(p); adj = np.empty(m); run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * p[i]); adj[i] = min(1.0, run)
    return adj


def main(path, prefix, ref, others, inst_order=None):
    rows = [json.loads(l) for l in open(path)]
    df = pd.DataFrame([{k: v for k, v in r.items() if k not in ("tour", "params")} for r in rows])
    assert df["valid"].all(), "invalid tour in results"
    order = inst_order or list(dict.fromkeys(df["inst"]))
    agg = dict(runs=("gap", "size"), mean_gap=("gap", "mean"), std_gap=("gap", "std"), min_gap=("gap", "min"),
               max_gap=("gap", "max"), n_opt=("is_opt", "sum"), mean_wall=("wall", "mean"), max_wall=("wall", "max"))
    if "iterations" in df:
        agg["mean_iter"] = ("iterations", "mean")
    s = df.groupby(["inst", "arm"]).agg(**agg).reset_index()
    s["inst"] = pd.Categorical(s["inst"], order, ordered=True)
    s = s.sort_values(["inst", "arm"])
    tot = df.groupby("arm").agg(runs=("gap", "size"), mean_gap=("gap", "mean"), n_opt=("is_opt", "sum"),
                                mean_wall=("wall", "mean")).reset_index()
    tot.insert(0, "inst", "ALL")
    s = pd.concat([s, tot], ignore_index=True)
    s.to_csv(prefix + "_summary.csv", index=False, float_format="%.4f")
    W = []
    piv = df.pivot_table(index=["inst", "seed"], columns="arm", values="gap")
    for o in others:
        sub = piv[[ref, o]].dropna()
        d = (sub[ref] - sub[o]).values
        nz = np.abs(d) > 1e-12
        wins, ties, losses = int((d < -1e-12).sum()), int((~nz).sum()), int((d > 1e-12).sum())
        if nz.sum() == 0:
            stat, p = np.nan, 1.0
        else:
            res = wilcoxon(sub[ref].values, sub[o].values, zero_method="wilcox", alternative="two-sided")
            stat, p = float(res.statistic), float(res.pvalue)
        W.append(dict(comparison=f"{ref} vs {o}", n_pairs=len(d), n_nonzero=int(nz.sum()), wins_ref=wins,
                      ties=ties, losses_ref=losses, mean_diff_gap_pct=float(d.mean()),
                      median_diff_gap_pct=float(np.median(d)), W=stat, p=p))
        for inst, g in sub.groupby(level=0):
            dd = (g[ref] - g[o]).values
            W.append(dict(comparison=f"{ref} vs {o} [{inst}]", n_pairs=len(dd),
                          n_nonzero=int((np.abs(dd) > 1e-12).sum()), wins_ref=int((dd < -1e-12).sum()),
                          ties=int((np.abs(dd) <= 1e-12).sum()), losses_ref=int((dd > 1e-12).sum()),
                          mean_diff_gap_pct=float(dd.mean()), median_diff_gap_pct=float(np.median(dd)),
                          W=np.nan, p=np.nan))
    W = pd.DataFrame(W)
    pooled = W["p"].notna()
    W.loc[pooled, "p_holm"] = holm(W.loc[pooled, "p"].values)
    W.to_csv(prefix + "_wilcoxon.csv", index=False, float_format="%.6g")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(s.round(4).to_string(index=False))
        print(W[pooled].round(6).to_string(index=False))
    return s, W


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(","))
