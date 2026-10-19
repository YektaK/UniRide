
import os, sys, json, time, pickle
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
import wave_exact
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csc_matrix
BIG = 30000

def sp2(masks, costs, n, tl=float(os.environ.get('SP_TL', '120'))):
    if len(masks) == 0: return None
    ri, cj = [], []
    for k, m in enumerate(masks):
        mm = int(m); i = 0
        while mm:
            if mm & 1: ri.append(i); cj.append(k)
            mm >>= 1; i += 1
    A = csc_matrix((np.ones(len(ri)), (ri, cj)), shape=(n, len(masks)))
    o = dict(time_limit=tl, mip_rel_gap=0)
    r1 = milp(np.ones(len(masks)), constraints=LinearConstraint(A, 1, 1), integrality=np.ones(len(masks)), bounds=Bounds(0, 1), options=o)
    if r1.x is None: return None
    K = int(round(r1.fun))
    A2 = csc_matrix(np.vstack([A.toarray(), np.ones((1, len(masks)))]))
    lo = np.r_[np.ones(n), K]; hi = np.r_[np.ones(n), K]
    r2 = milp(np.asarray(costs, float), constraints=LinearConstraint(A2, lo, hi), integrality=np.ones(len(masks)), bounds=Bounds(0, 1), options=o)
    if r2.x is None: return dict(routes=K, dur=None, status=(r1.status, r2.status))
    return dict(routes=K, dur=int(round(r2.fun)), status=(int(r1.status), int(r2.status)))

def cand_mask(S, k):
    n = S.shape[0]; A = np.zeros((n, n), bool)
    for i in range(n):
        o = np.argsort(-S[i]); A[i, [j for j in o[:k] if j != i]] = True
    for j in range(n):
        o = np.argsort(-S[:, j]); A[[i for i in o[:k] if i != j], j] = True
    np.fill_diagonal(A, False); return A

def run(p, method, k):
    n = p["n"]; C = p["C"].copy()
    A = cand_mask(p["succ"][method], k)
    sub = C[:n, :n].copy(); sub[~A & ~np.eye(n, dtype=bool)] = BIG; C[:n, :n] = sub
    t0 = time.time()
    masks, costs, _ = wave_exact.enumerate_routes(C, n, p["is_sw"], 4, 5, p["R"], 150, p["direction"])
    t1 = time.time(); r = sp2(masks, costs, n); t2 = time.time()
    return dict(n_arcs=int(A.sum()), n_cols=int(len(masks)), t_enum=t1 - t0, t_sp=t2 - t1, **(r or dict(routes=None, dur=None, status=None)))

def run_filter(p, method, theta, full):
    n = p["n"]; masks, costs = full; S = p["same"][method]; P = (S + S.T) / 2 if np.isfinite(S).all() else S
    Pm = np.where(np.isfinite(S), S, 0); Pm = np.minimum(Pm, Pm.T)
    keep = []
    for k, m in enumerate(masks):
        mm = int(m); mem = [i for i in range(n) if mm >> i & 1]
        ok = all(Pm[a, b] >= theta for x, a in enumerate(mem) for b in mem[x + 1:])
        if ok: keep.append(k)
    t0 = time.time(); r = sp2([masks[k] for k in keep], [costs[k] for k in keep], n); t1 = time.time()
    return dict(n_cols=len(keep), t_sp=t1 - t0, **(r or dict(routes=None, dur=None, status=None)))

if __name__ == "__main__":
    out, wid, nw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    P = pickle.load(open(os.path.join(ws, "results", "prune_in.pkl"), "rb"))
    done = set()
    if os.path.exists(out):
        for l in open(out): done.add(json.loads(l)["tag"])
    order = sorted(range(len(P)), key=lambda i: -P[i]["n"])
    for rank, i in enumerate(order):
        if rank % nw != wid: continue
        p = P[i]; n = p["n"]
        tag = p["key"] + "|FULL"
        if tag not in done:
            t0 = time.time(); masks, costs, _ = wave_exact.enumerate_routes(p["C"], n, p["is_sw"], 4, 5, p["R"], 150, p["direction"])
            t1 = time.time(); r = sp2(masks, costs, n); t2 = time.time()
            rec = dict(tag=tag, key=p["key"], n=n, mode="full", method="FULL", k=None, n_cols=int(len(masks)), t_enum=t1 - t0, t_sp=t2 - t1, **r,
                       opt_routes=p["opt_routes"], opt_dur=p["opt_dur"])
            open(out, "a").write(json.dumps(rec) + "\n"); print(tag, r, flush=True)
        else:
            masks, costs, _ = wave_exact.enumerate_routes(p["C"], n, p["is_sw"], 4, 5, p["R"], 150, p["direction"])
        for method in ["GEO", "DETOUR", "FREQ", "LR-geo", "GBM-geo", "GBM-hyb"]:
            for k in [2, 3, 4, 5, 6, 8]:
                tag = f'{p["key"]}|arc|{method}|{k}'
                if tag in done or k >= n - 1: continue
                r = run(p, method, k)
                open(out, "a").write(json.dumps(dict(tag=tag, key=p["key"], n=n, mode="arc", method=method, k=k, opt_routes=p["opt_routes"], opt_dur=p["opt_dur"], **r)) + "\n")
        for method in ["GEO", "DETOUR", "FREQ", "LR-geo", "GBM-geo"]:
            for theta in ([0.01, 0.03, 0.1, 0.2] if method not in ("GEO", "DETOUR") else []):
                tag = f'{p["key"]}|col|{method}|{theta}'
                if tag in done: continue
                r = run_filter(p, method, theta, (masks, costs))
                open(out, "a").write(json.dumps(dict(tag=tag, key=p["key"], n=n, mode="col", method=method, k=theta, opt_routes=p["opt_routes"], opt_dur=p["opt_dur"], **r)) + "\n")
        print("done", p["key"], flush=True)
