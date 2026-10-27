"""D1 decision experiment: fast_ls vs repo MultiLayerLS('moderate').
usage: python d1_experiment.py inst out.jsonl T_repo_kick T_fast_kick n_quality_starts n_kick_starts
(restartable: rows already present in out.jsonl are skipped)
(a) local-optimum quality from identical random start tours (5 starts):
    repo_1call = bench_common.ls_moderate (exactly what bench_common.ils uses per kick)
    repo_conv  = ls_moderate repeated until no further improvement
    fast       = FastLS.optimize (ILS-fast configuration) and fast_2o = 2-opt+Or-opt only
(b) kicks per second: ILS loop of each engine started from its own local optimum of start 0..2;
    repo kick = bench_common double-bridge (A C B D, global cuts) + ls_moderate, accept if not worse;
    fast kick = ILS-fast (segment-local double-bridge + queue LS).  Initial LS excluded."""
import os, sys, time, csv, random, json
sys.dont_write_bytecode = True
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.abspath("numba_cache"))
import numpy as np
import bench_common as bc
from fast_ls import FastLS, tour_cost
from ils_fast import ILSState, warmup, T_KICKS
from inst import load_tsp

CFG = dict(K=10, Lmax=int(os.environ.get("D1_LMAX", "100")), use_or3=os.environ.get("D1_OR3", "1") == "1")


def main():
    inst, out = sys.argv[1], sys.argv[2]
    T_repo, T_fast = float(sys.argv[3]), float(sys.argv[4])
    NQ, NK = int(sys.argv[5]), int(sys.argv[6])
    NKQ = int(sys.argv[7]) if len(sys.argv) > 7 else 3
    done = set()
    if os.path.exists(out):
        for l in open(out):
            r = json.loads(l); done.add((r["part"], r["start"]))
    fo = open(out, "a")
    warmup()
    xy = np.random.RandomState(0).rand(40, 2) * 100
    bc.ils(np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5), 0.3, 0)   # repo JIT warm-up
    dm, opt = load_tsp(inst)
    n = len(dm); dml = dm.tolist()
    rows = []
    t0 = time.perf_counter(); ls = FastLS(dm, K=CFG["K"], use_or3=CFG["use_or3"]); t_build = time.perf_counter() - t0
    ls2 = FastLS(dm, K=CFG["K"], use_or3=False)
    for s in range(NQ):
        if ("ls_quality", s) in done:
            continue
        start = np.random.default_rng(1000 + s).permutation(n).astype(np.int32)
        tt = time.perf_counter(); tr, cr = bc.ls_moderate(start.tolist(), dml, dm); dt_r = time.perf_counter() - tt
        cr = tour_cost(dm, np.asarray(tr, np.int32))
        tt = time.perf_counter(); tc, cc = list(tr), cr; ncall = 1
        while os.environ.get("D1_CONV", "1") == "1":
            t2, c2 = bc.ls_moderate(tc, dml, dm); ncall += 1
            c2 = tour_cost(dm, np.asarray(t2, np.int32))
            if c2 < cc - 1e-9:
                tc, cc = t2, c2
            else:
                break
        dt_conv = time.perf_counter() - tt + dt_r
        tt = time.perf_counter(); tf, cf, _ = ls.optimize(start); dt_f = time.perf_counter() - tt
        tt = time.perf_counter(); tf2, cf2, _ = ls2.optimize(start); dt_f2 = time.perf_counter() - tt
        rows.append(dict(inst=inst, n=n, part="ls_quality", start=s, start_cost=tour_cost(dm, start),
                         repo_1call_cost=cr, repo_1call_s=dt_r, repo_conv_cost=cc, repo_conv_calls=ncall, repo_conv_s=dt_conv,
                         fast_cost=cf, fast_s=dt_f, fast_2o_cost=cf2, fast_2o_s=dt_f2, fast_build_s=t_build,
                         fast_vs_repo1_pct=100 * (cf / cr - 1), fast_vs_repoconv_pct=100 * (cf / cc - 1),
                         fast2o_vs_repoconv_pct=100 * (cf2 / cc - 1), opt=opt, repo_tour=[int(x) for x in tr]))
        fo.write(json.dumps(rows[-1]) + "\n"); fo.flush()
    # (a2) same KICKED start tours: fast-LS local optimum of random start s + bench_common kick
    for s in range(NKQ):
        if ("ls_quality_kicked", s) in done:
            continue
        start = np.random.default_rng(1000 + s).permutation(n).astype(np.int32)
        lo, clo, _ = ls.optimize(start)
        rng = random.Random(s); cur = lo.tolist()
        i, j, k = sorted(rng.sample(range(1, n), 3))
        cand = cur[:i] + cur[j:k] + cur[i:j] + cur[k:]
        ck = tour_cost(dm, np.asarray(cand, np.int32))
        tt = time.perf_counter(); tr, cr = bc.ls_moderate(list(cand), dml, dm); dt_r = time.perf_counter() - tt
        cr = tour_cost(dm, np.asarray(tr, np.int32))
        tt = time.perf_counter(); tf, cf, _ = ls.optimize(np.asarray(cand, np.int32)); dt_f = time.perf_counter() - tt
        tt = time.perf_counter(); tf2, cf2, _ = ls2.optimize(np.asarray(cand, np.int32)); dt_f2 = time.perf_counter() - tt
        rows.append(dict(inst=inst, n=n, part="ls_quality_kicked", start=s, lo_cost=clo, start_cost=ck,
                         repo_1call_cost=cr, repo_1call_s=dt_r, fast_cost=cf, fast_s=dt_f, fast_2o_cost=cf2,
                         fast_2o_s=dt_f2, fast_vs_repo1_pct=100 * (cf / cr - 1), fast2o_vs_repo1_pct=100 * (cf2 / cr - 1),
                         repo_kps_from_kicked=1.0 / dt_r, opt=opt))
        fo.write(json.dumps(rows[-1]) + "\n"); fo.flush()
    # (b) kicks per second
    for s in range(NK):
        if ("kicks_per_s", s) in done:
            continue
        start = np.random.default_rng(1000 + s).permutation(n).astype(np.int32)
        rng = random.Random(s)
        prev = [json.loads(l) for l in open(out)] if os.path.exists(out) else []
        prev = [r for r in prev if r["part"] == "ls_quality" and r["start"] == s and "repo_tour" in r]
        if prev:
            cur = prev[0]["repo_tour"]; cc = tour_cost(dm, np.asarray(cur, np.int32))
        else:
            cur, cc = bc.ls_moderate(start.tolist(), dml, dm)
        it = 0; tt = time.perf_counter()
        while time.perf_counter() - tt < T_repo:
            it += 1
            i, j, k = sorted(rng.sample(range(1, n), 3))
            cand = cur[:i] + cur[j:k] + cur[i:j] + cur[k:]
            cand, c = bc.ls_moderate(cand, dml, dm)
            if c <= cc:
                cur, cc = cand, c
        el_r = time.perf_counter() - tt
        tf, cf, _ = ls.optimize(start)
        st = ILSState(ls, tf, cf, s, CFG["Lmax"])
        tt = time.perf_counter()
        while time.perf_counter() - tt < T_fast:
            st.run(256)
        el_f = time.perf_counter() - tt
        kf = int(st.tel[T_KICKS])
        rows.append(dict(inst=inst, n=n, part="kicks_per_s", start=s, repo_kicks=it, repo_s=el_r, repo_kps=it / el_r,
                         repo_final_cost=cc, fast_kicks=kf, fast_s=el_f, fast_kps=kf / el_f,
                         fast_final_cost=float(st.cs[1]), speedup=(kf / el_f) / max(it / el_r, 1e-12), opt=opt))
        fo.write(json.dumps(rows[-1]) + "\n"); fo.flush()


if __name__ == "__main__":
    main()
