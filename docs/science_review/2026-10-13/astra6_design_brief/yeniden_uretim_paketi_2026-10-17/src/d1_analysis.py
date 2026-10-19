"""D1 analysis: merges logs/d1_<inst>.jsonl, recomputes the (deterministic) fast-LS variants from the
same start tours, and writes D1_results.csv (per start) + D1_summary.csv (per instance/part)."""
import json, random, os, sys
import numpy as np
import pandas as pd
from scipy import stats
from fast_ls import FastLS, tour_cost
from inst import load_tsp

rows = []
for inst in ["a280", "pr439", "pr1002"]:
    f = f"logs/d1_{inst}.jsonl"
    if not os.path.exists(f):
        continue
    dm, opt = load_tsp(inst); n = len(dm)
    ls10 = FastLS(dm, K=10, use_or3=True); ls10b = FastLS(dm, K=10, use_or3=False); ls20 = FastLS(dm, K=20, use_or3=True)
    for l in open(f):
        r = json.loads(l); r.pop("repo_tour", None)
        if r["part"] in ("ls_quality", "ls_quality_kicked"):
            start = np.random.default_rng(1000 + r["start"]).permutation(n).astype(np.int32)
            if r["part"] == "ls_quality_kicked":
                lo, _, _ = ls10.optimize(start)
                rng = random.Random(r["start"]); cur = lo.tolist()
                i, j, k = sorted(rng.sample(range(1, n), 3))
                start = np.asarray(cur[:i] + cur[j:k] + cur[i:j] + cur[k:], np.int32)
                assert tour_cost(dm, start) == r["start_cost"]
            ref = r["repo_conv_cost"] if r["part"] == "ls_quality" else r["repo_1call_cost"]
            r["repo_ref_cost"] = ref
            for lab, ls in [("fast_k10_or3", ls10), ("fast_k10_2o", ls10b), ("fast_k20_or3", ls20)]:
                t, c, _ = ls.optimize(start)
                r[lab + "_cost"] = c
                r[lab + "_vs_repo_pct"] = 100 * (c / ref - 1)
            assert r["fast_k10_or3_cost"] == r["fast_cost"], "fast LS not deterministic?"
            r["repo_ref_gap_pct"] = 100 * (ref / opt - 1)
        rows.append(r)
D = pd.DataFrame(rows)
D.to_csv("D1_results.csv", index=False, float_format="%.6g")

S = []
for (inst, part), g in D[D.part.isin(["ls_quality", "ls_quality_kicked"])].groupby(["inst", "part"]):
    for lab in ["fast_k10_or3", "fast_k10_2o", "fast_k20_or3"]:
        x = g[lab + "_vs_repo_pct"].values
        m = x.mean(); se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan
        h = stats.t.ppf(0.975, len(x) - 1) * se if len(x) > 1 else np.nan
        S.append(dict(inst=inst, part=part, variant=lab, n_starts=len(x), mean_diff_vs_repo_pct=m,
                      ci95_lo=m - h, ci95_hi=m + h, repo_mean_gap_to_opt_pct=g["repo_ref_gap_pct"].mean(),
                      repo_mean_ls_s=g["repo_1call_s"].mean() if part == "ls_quality_kicked" else g["repo_conv_s"].mean(),
                      fast_mean_ls_s=g["fast_s"].mean(),
                      within_0_5_point=bool(abs(m) <= 0.5),
                      within_0_5_ci=bool(len(x) > 1 and -0.5 <= m - h and m + h <= 0.5)))
# kicks per second
main = []
for f in ["results/main_w0.jsonl", "results/main_w1.jsonl", "results/main_w2.jsonl"]:
    if os.path.exists(f):
        main += [json.loads(l) for l in open(f)]
M = pd.DataFrame([{k: v for k, v in r.items() if k not in ("tour", "params")} for r in main]) if main else pd.DataFrame()
for inst in ["a280", "pr439", "pr1002"]:
    g = D[(D.inst == inst) & (D.part == "kicks_per_s")]
    if len(g):
        repo_kps = g["repo_kicks"].sum() / g["repo_s"].sum(); fast_kps = g["fast_kicks"].sum() / g["fast_s"].sum()
        src_r = f"kick loop from repo local optimum, {len(g)} starts x ~20 s"; src_f = f"ILS-fast {len(g)} starts x 5 s"
    else:
        gk = D[(D.inst == inst) & (D.part == "ls_quality_kicked")]
        if not len(gk):
            continue
        repo_kps = len(gk) / gk["repo_1call_s"].sum()
        src_r = f"{len(gk)} repo LS calls on kicked tours (1/mean time)"
        mm = M[(M.inst == inst) & (M.arm == "ils_fast")] if len(M) else []
        fast_kps = float(mm["kicks_per_s"].mean()) if len(mm) else np.nan
        src_f = f"main benchmark ILS-fast, {len(mm)} runs x 30 s"
    mm = M[(M.inst == inst) & (M.arm == "repo_ils")] if len(M) else []
    S.append(dict(inst=inst, part="kicks_per_s", variant="ILS-fast vs repo ILS", repo_kps=repo_kps, fast_kps=fast_kps,
                  speedup=fast_kps / repo_kps, criterion_50x=bool(fast_kps / repo_kps >= 50), repo_source=src_r,
                  fast_source=src_f,
                  main_bench_repo_iter_per_s=float((mm["iterations"] / mm["wall"]).mean()) if len(mm) else np.nan))
S = pd.DataFrame(S)
S.to_csv("D1_summary.csv", index=False, float_format="%.5g")
with pd.option_context("display.width", 250, "display.max_columns", 30):
    print(S.round(4).to_string(index=False))
