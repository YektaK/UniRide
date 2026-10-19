
"""Joint typed day model (heterogeneous fleet, P6/P7): large 4Sw/5So and sedan
0Sw/4So, cooldown 10. Each chosen route is assigned to one type; per-type
peak concurrency = per-type fleet. For fixed L large vehicles, minimise the
sedan count S, then total route minutes. Columns are complete per type, so an
infeasible model means no routing of the day exists with L large vehicles."""
import os, sys, json, time
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
ROOT = r"C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"; sys.path.insert(0, ROOT)
import run_waves, wave_exact
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix, vstack, csr_matrix
COOL = 10
TYPES = {"large": (4, 5), "sedan": (0, 4)}

def columns(D, date, R, T=150):
    waves = [w for w in run_waves.load_waves(D) if w["date"] == date and w["R"] == R]
    M, idx, sha = run_waves.load_matrix(D, date)
    cols = []
    for wi, w in enumerate(waves):
        locs = [idx[run_waves.loc_of(o)] for o in w["occ"]] + [idx["D.Kampus"]]
        C = M[np.ix_(locs, locs)].astype(np.int32); n = len(w["occ"])
        is_sw = [run_waves.loc_of(o).startswith("Sw") for o in w["occ"]]
        a = w["anchor"]
        for tname, (csw, cso) in TYPES.items():
            masks, costs, seq_of = wave_exact.enumerate_routes(C, n, is_sw, csw, cso, R, T, w["direction"])
            for k in range(len(masks)):
                d = int(costs[k]); s, e = (a - d, a + COOL) if w["direction"] == "pickup" else (a, a + d + COOL)
                cols.append(dict(w=wi, mask=int(masks[k]), d=d, s=s, e=e, type=tname, occ=[w["occ"][v] for v in seq_of(k)]))
    return waves, cols

def build(waves, cols):
    nc = len(cols); S_idx = nc; nv = nc + 1
    rows, ci, va, lo, hi, kinds = [], [], [], [], [], []
    r = 0
    for wi, w in enumerate(waves):
        for i in range(len(w["occ"])):
            for j, c in enumerate(cols):
                if c["w"] == wi and (c["mask"] >> i) & 1: rows.append(r); ci.append(j); va.append(1.0)
            lo.append(1); hi.append(1); kinds.append("part"); r += 1
    pts = sorted({c["s"] for c in cols})
    for tname in TYPES:
        for t in pts:
            cover = [j for j, c in enumerate(cols) if c["type"] == tname and c["s"] <= t < c["e"]]
            if not cover: continue
            for j in cover: rows.append(r); ci.append(j); va.append(1.0)
            if tname == "sedan": rows.append(r); ci.append(S_idx); va.append(-1.0)
            lo.append(-np.inf); hi.append(0.0); kinds.append(tname); r += 1
    A = coo_matrix((va, (rows, ci)), shape=(r, nv)).tocsr()
    return A, np.array(lo, float), np.array(hi, float), kinds, nv

def solve(waves, cols, L, tl=900):
    A, lo, hi, kinds, nv = build(waves, cols)
    hi2 = hi.copy(); hi2[[k == "large" for k in kinds]] = L
    integ = np.ones(nv); bnd = Bounds(np.zeros(nv), np.r_[np.ones(nv - 1), 50])
    c1 = np.zeros(nv); c1[-1] = 1
    t0 = time.time()
    s1 = milp(c1, constraints=LinearConstraint(A, lo, hi2), integrality=integ, bounds=bnd, options={"time_limit": tl})
    out = dict(L=L, s1=int(s1.status), S=None if s1.x is None else int(round(s1.fun)))
    if s1.status != 0:
        out["time_s"] = round(time.time() - t0, 1); return out, None
    S = out["S"]
    c2 = np.r_[[c["d"] for c in cols], 0.0]
    bnd2 = Bounds(np.zeros(nv), np.r_[np.ones(nv - 1), S])
    s2 = milp(c2, constraints=LinearConstraint(A, lo, hi2), integrality=integ, bounds=bnd2, options={"time_limit": tl, "mip_rel_gap": 0})
    out.update(s2=int(s2.status), minutes=None if s2.x is None else int(round(s2.fun)), time_s=round(time.time() - t0, 1), n_cols=len(cols))
    chosen = [j for j in range(len(cols)) if s2.x is not None and s2.x[j] > 0.5]
    plan = [dict(job=waves[cols[j]["w"]]["job"], direction=waves[cols[j]["w"]]["direction"], anchor=waves[cols[j]["w"]]["anchor"],
                 type=cols[j]["type"], dur=cols[j]["d"], occ=cols[j]["occ"]) for j in chosen]
    out["large_routes"] = sum(p["type"] == "large" for p in plan); out["sedan_routes"] = sum(p["type"] == "sedan" for p in plan)
    return out, plan

if __name__ == "__main__":
    D, out_path = sys.argv[1], sys.argv[2]
    done = set()
    if os.path.exists(out_path):
        done = {(json.loads(l)["date"], json.loads(l)["R"], json.loads(l)["L"]) for l in open(out_path, encoding="utf-8")}
    cells = [(d_, R_) for d_ in ["2026-10-07", "2026-10-06", "2026-10-08", "2026-10-09", "2026-10-05"] for R_ in [50, 60, 70, 90]]
    cells = [c for c in cells if c != ("2026-10-05", 90)] + [("2026-10-05", 90)]
    for date, R in cells:
        if all((date, R, L) in done for L in (1, 2, 3)): continue
        waves, cols = columns(D, date, R)
        for L in (1, 2, 3):
            if (date, R, L) in done: continue
            res, plan = solve(waves, cols, L)
            with open(out_path, "a", encoding="utf-8") as fh: fh.write(json.dumps(dict(date=date, R=R, **res, plan=plan)) + "\n")
            print(date, R, res, flush=True)
