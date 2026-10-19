
import os, sys, json, time, itertools
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ws, "ls"))
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(ws, "numba_cache"))
from fast_ls import FastLS, tour_cost
from ils_fast import ils_fast
import elkai

OPT = {"rd100": 7910, "pr136": 96772, "a280": 2579, "lin318": 42029, "pr439": 107217}

def load(name):
    xy, sec = [], False
    for line in open(os.path.join(ws, "ls", name + ".tsp"), encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("NODE_COORD_SECTION"): sec = True; continue
        if s.startswith("EOF"): break
        if sec and s:
            p = s.split(); xy.append((float(p[1]), float(p[2])))
    xy = np.array(xy); d = np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5); np.fill_diagonal(d, 0)
    return xy, d

def edges(t):
    t = np.asarray(t); a = t; b = np.roll(t, -1)
    return set(zip(np.minimum(a, b).tolist(), np.maximum(a, b).tolist()))

def run_instance(name, n_lo=1000, n_ils=100, ils_kicks=3000, seed=0):
    xy, dm = load(name); n = len(dm)
    t0 = time.time()
    m = elkai.DistanceMatrix(dm.astype(int).tolist()); tour = m.solve_tsp(runs=10)
    tour = tour[:-1] if len(tour) > n else tour
    c_opt = tour_cost(dm, np.array(tour, np.int32)); t_lkh = time.time() - t0
    E_opt = edges(tour)
    ls = FastLS(dm, K=10, use_or3=False)
    rng = np.random.default_rng(seed)
    recs = []
    for k in range(n_lo):
        t, c, _ = ls.optimize(rng.permutation(n).astype(np.int32))
        E = edges(t); recs.append(dict(kind="LS", cost=float(c), d_opt=n - len(E & E_opt), edges=sorted(E)))
    t_lo = time.time()
    for k in range(n_ils):
        r = ils_fast(dm, 0, seed=1000 + k, K=10, Lmax=50, use_or3=True, max_kicks=ils_kicks)
        E = edges(r["tour"]); recs.append(dict(kind="ILS", cost=float(r["cost"]), d_opt=n - len(E & E_opt), edges=sorted(E)))
    t_ils = time.time()
    # pairwise distances among LS optima (sample 300)
    LS = [r for r in recs if r["kind"] == "LS"]
    idx = rng.choice(len(LS), size=min(300, len(LS)), replace=False)
    sets = [set(map(tuple, LS[i]["edges"])) for i in idx]
    pd_ = [n - len(sets[a] & sets[b]) for a in range(len(sets)) for b in range(a + 1, len(sets))]
    # edge frequency over best 10% LS optima
    LSs = sorted(LS, key=lambda r: r["cost"]); top = LSs[:max(10, len(LSs) // 10)]
    freq = {}
    for r in top:
        for e in r["edges"]: freq[tuple(e)] = freq.get(tuple(e), 0) + 1
    calib = []
    for lo, hi in [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, .999), (.999, 1.01)]:
        es = [e for e, f in freq.items() if lo <= f / len(top) < hi]
        calib.append(dict(lo=lo, hi=hi, n_edges=len(es), frac_in_opt=(sum(e in E_opt for e in es) / len(es)) if es else None))
    # geometric baseline: k-th nearest neighbour edges
    order = np.argsort(dm + np.eye(n) * 1e18, axis=1)
    knn = []
    for k in range(5):
        es = {(min(i, int(order[i, k])), max(i, int(order[i, k]))) for i in range(n)}
        knn.append(dict(k=k + 1, n_edges=len(es), frac_in_opt=sum(e in E_opt for e in es) / len(es)))
    backbone = [e for e, f in freq.items() if f == len(top)]
    return dict(name=name, n=n, opt_known=OPT[name], opt_lkh=float(c_opt), t_lkh=t_lkh, t_lo=t_lo - t0 - t_lkh, t_ils=t_ils - t_lo,
                records=[{k: v for k, v in r.items() if k != "edges"} for r in recs], top_k=len(top),
                pairwise_LS_mean=float(np.mean(pd_)), pairwise_LS_sd=float(np.std(pd_)), calib=calib, knn=knn,
                backbone_n=len(backbone), backbone_in_opt=sum(e in E_opt for e in backbone),
                opt_tour=[int(x) for x in tour], xy=xy.tolist(),
                best_LS_tour_edges=LSs[0]["edges"], worst_LS_tour_edges=LSs[-1]["edges"],
                freq_top=[[int(a), int(b), f] for (a, b), f in freq.items()])

def toy(nc=8, seed=7):
    rng = np.random.default_rng(seed); xy = rng.uniform(0, 100, size=(nc, 2))
    dm = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
    def canon(t):
        t = list(t); i = t.index(0); t = t[i:] + t[:i]
        if t[1] > t[-1]: t = [t[0]] + t[1:][::-1]
        return tuple(t)
    tours = sorted({canon((0,) + p) for p in itertools.permutations(range(1, nc))})
    index = {t: k for k, t in enumerate(tours)}
    cost = np.array([sum(dm[t[i], t[(i + 1) % nc]] for i in range(nc)) for t in tours])
    nbrs = []
    for t in tours:
        nb = set()
        for i in range(1, nc):
            for j in range(i + 1, nc + 1):
                s = list(t); s[i:j] = s[i:j][::-1]; c = canon(s)
                if c != t: nb.add(index[c])
        nbrs.append(sorted(nb))
    is_lo = [all(cost[j] >= cost[k] - 1e-9 for j in nbrs[k]) for k in range(len(tours))]
    def descend(k):
        while True:
            j = min(nbrs[k], key=lambda x: cost[x])
            if cost[j] < cost[k] - 1e-9: k = j
            else: return k
    basin = [descend(k) for k in range(len(tours))]
    E = [edges(t) for t in tours]
    D = np.array([[nc - len(E[a] & E[b]) for b in range(len(tours))] for a in range(len(tours))], dtype=np.float32)
    # classical MDS
    n = len(D); J = np.eye(n, dtype=np.float32) - 1.0 / n
    Bm = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(Bm); idx = np.argsort(w)[::-1][:2]
    X = V[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    return dict(nc=nc, xy=xy.tolist(), n_tours=len(tours), cost=cost.tolist(), is_lo=is_lo, basin=basin, mds=X.tolist(),
                tours=[list(t) for t in tours], n_neighbors=len(nbrs[0]),
                d_to_opt=[float(D[k, int(np.argmin(cost))]) for k in range(len(tours))])

if __name__ == "__main__":
    out = sys.argv[1]
    res = dict(toy=toy())
    print("toy done", sum(res["toy"]["is_lo"]), flush=True)
    for name in ["rd100", "pr136", "a280", "lin318"]:
        res[name] = run_instance(name); r = res[name]
        print(name, "lkh", r["opt_lkh"], "known", r["opt_known"], "t", round(r["t_lkh"], 1), round(r["t_lo"], 1), round(r["t_ils"], 1), flush=True)
        json.dump(res, open(out, "w"))
