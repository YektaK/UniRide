
import os, sys, json, time
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ws, "ls"))
import fast_ls
from fast_ls import FastLS
import ils_fast as IF
from landscape_demo import load
OPT = {"lin318": 42029, "pr439": 107217, "rat783": 8806, "pr1002": 259045}
BUD = {"lin318": 20, "pr439": 30, "rat783": 60, "pr1002": 60}
orig_bc = fast_ls.build_candidates

def cands_from_lists(dm, lists):
    n = len(dm); W = max(len(l) for l in lists)
    nbo = np.zeros((n, W), np.int32)
    for i, l in enumerate(lists):
        l = sorted(set(l) - {i}, key=lambda j: dm[i, j]); l = l + [l[-1]] * (W - len(l)); nbo[i] = l
    return nbo, nbo.copy()   # symmetric instance: in-list = out-list

def phase1(dm, tlim, seed):
    rng = np.random.default_rng(seed); ls = FastLS(dm, K=10, use_or3=False); n = len(dm); t0 = time.time(); res = []
    while time.time() - t0 < tlim:
        t, c, _ = ls.optimize(rng.permutation(n).astype(np.int32)); res.append((c, t.copy()))
    res.sort(key=lambda x: x[0]); return res

def run(name, arm, seed):
    xy, dm = load(name); n = len(dm); B = BUD[name]; t0 = time.time(); info = {}
    if arm in ("K10", "K5"):
        fast_ls.build_candidates = orig_bc
        r = IF.ils_fast(dm, B, seed, K=10 if arm == "K10" else 5)
    else:
        P1 = phase1(dm, 0.1 * B, seed); elite = P1[:max(5, len(P1) // 3)]
        lists = [set() for _ in range(n)]
        for c, t in elite:
            for a, b in zip(t, np.roll(t, -1)): lists[a].add(int(b)); lists[b].add(int(a))
        info = dict(m1=len(P1), elite=len(elite), mean_deg=float(np.mean([len(l) for l in lists])), p1_best=float(elite[0][0]))
        if arm == "P1+K10": fast_ls.build_candidates = orig_bc; K = 10
        else:
            if arm == "U+3NN":
                order = np.argsort(dm + np.eye(n) * 1e18, axis=1)[:, :3]
                for i in range(n): lists[i] |= set(order[i].tolist())
            nbo, nbi = cands_from_lists(dm, [list(l) for l in lists]); K = nbo.shape[1]
            fast_ls.build_candidates = lambda d, K=10, _a=nbo, _b=nbi: (_a, _b)
        r = IF.ils_fast(dm, B - (time.time() - t0), seed, K=K, init_tour=elite[0][1])
        fast_ls.build_candidates = orig_bc
    return dict(inst=name, arm=arm, seed=seed, cost=float(r["cost"]), gap=100 * (r["cost"] / OPT[name] - 1), kicks=int(r.get("kicks", -1)),
                wall=time.time() - t0, **info)

if __name__ == "__main__":
    out, wid, nw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    done = set()
    if os.path.exists(out):
        for l in open(out): d = json.loads(l); done.add((d["inst"], d["arm"], d["seed"]))
    jobs = [(nm, arm, s) for nm in OPT for s in range(5) for arm in ["K10", "K5", "P1+K10", "U", "U+3NN"]]
    for k, j in enumerate(jobs):
        if k % nw != wid or j in done: continue
        r = run(*j); open(out, "a").write(json.dumps(r) + "\n"); print(r, flush=True)
