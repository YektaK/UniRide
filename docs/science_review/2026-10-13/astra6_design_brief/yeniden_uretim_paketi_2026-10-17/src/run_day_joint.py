
"""Joint day-level exact model: choose one route partition per wave and
minimise (1) peak concurrent busy vehicles K (= minimum homogeneous fleet for
interval jobs with cooldown), (2) total routes, (3) total route minutes.
Columns are all feasible routes from the exact wave enumeration."""
import os, sys, json, time
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
ROOT = os.environ.get("UNIRIDE_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 6)); sys.path.insert(0, ROOT)
import run_waves, wave_exact
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix
COOL = 10

def build_day(D, date, R, cap_sw=4, cap_so=5, T=150):
    waves = [w for w in run_waves.load_waves(D) if w["date"] == date and w["R"] == R]
    M, idx, sha = run_waves.load_matrix(D, date)
    cols = []   # (wave_idx, mask, dur, start, end_busy, seq)
    for wi, w in enumerate(waves):
        locs = [idx[run_waves.loc_of(o)] for o in w["occ"]] + [idx["D.Kampus"]]
        C = M[np.ix_(locs, locs)].astype(np.int32); n = len(w["occ"])
        is_sw = [run_waves.loc_of(o).startswith("Sw") for o in w["occ"]]
        masks, costs, seq_of = wave_exact.enumerate_routes(C, n, is_sw, cap_sw, cap_so, R, T, w["direction"])
        a = w["anchor"]
        for k in range(len(masks)):
            d = int(costs[k])
            s, e = (a - d, a + COOL) if w["direction"] == "pickup" else (a, a + d + COOL)
            cols.append((wi, int(masks[k]), d, s, e, k, seq_of))
    return waves, cols

def solve_day(waves, cols, time_limit=900):
    nc = len(cols); nv = nc + 1            # last var = K
    rows, cidx, vals, lo, hi = [], [], [], [], []
    r = 0
    for wi, w in enumerate(waves):         # partition rows
        n = len(w["occ"])
        for i in range(n):
            for j, c in enumerate(cols):
                if c[0] == wi and (c[1] >> i) & 1:
                    rows.append(r); cidx.append(j); vals.append(1.0)
            lo.append(1); hi.append(1); r += 1
    pts = sorted({c[3] for c in cols})     # max overlap of half-open intervals occurs at a start
    for t in pts:
        cover = [j for j, c in enumerate(cols) if c[3] <= t < c[4]]
        if len(cover) == 0: continue
        for j in cover: rows.append(r); cidx.append(j); vals.append(1.0)
        rows.append(r); cidx.append(nc); vals.append(-1.0); lo.append(-np.inf); hi.append(0); r += 1
    A = coo_matrix((vals, (rows, cidx)), shape=(r, nv)).tocsr()
    integ = np.ones(nv); bnd = Bounds(np.zeros(nv), np.r_[np.ones(nc), 100])
    out = {}
    t0 = time.time()
    c1 = np.zeros(nv); c1[-1] = 1
    s1 = milp(c1, constraints=LinearConstraint(A, lo, hi), integrality=integ, bounds=bnd, options={"time_limit": time_limit})
    out["K"] = None if s1.x is None else int(round(s1.fun)); out["s1"] = int(s1.status)
    if s1.status != 0: return out, None
    K = out["K"]; bnd2 = Bounds(np.zeros(nv), np.r_[np.ones(nc), K])
    c2 = np.r_[np.ones(nc), 0]
    s2 = milp(c2, constraints=LinearConstraint(A, lo, hi), integrality=integ, bounds=bnd2, options={"time_limit": time_limit})
    out["routes"] = None if s2.x is None else int(round(s2.fun)); out["s2"] = int(s2.status)
    if s2.status != 0: return out, None
    A3 = coo_matrix(np.vstack([A.toarray(), c2[None, :]])).tocsr()
    c3 = np.r_[[c[2] for c in cols], 0.0]
    s3 = milp(c3, constraints=LinearConstraint(A3, np.r_[lo, out["routes"]], np.r_[hi, out["routes"]]), integrality=integ,
              bounds=bnd2, options={"time_limit": time_limit, "mip_rel_gap": 0})
    out["minutes"] = None if s3.x is None else int(round(s3.fun)); out["s3"] = int(s3.status)
    out["time_s"] = round(time.time() - t0, 1); out["n_cols"] = nc; out["n_rows"] = r
    chosen = [j for j in range(nc) if s3.x is not None and s3.x[j] > 0.5]
    return out, chosen

if __name__ == "__main__":
    D, out_path = sys.argv[1], sys.argv[2]
    done = set()
    if os.path.exists(out_path):
        done = {(json.loads(l)["date"], json.loads(l)["R"]) for l in open(out_path, encoding="utf-8")}
    cells = [(d_, R_) for d_ in ["2026-10-07", "2026-10-05", "2026-10-06", "2026-10-08", "2026-10-09"] for R_ in [50, 60, 70, 90]]
    cells = [c for c in cells if c != ("2026-10-05", 90)] + [("2026-10-05", 90)]
    for date, R in cells:
            if (date, R) in done: continue
            waves, cols = build_day(D, date, R)
            res, chosen = solve_day(waves, cols)
            plan = []
            if chosen:
                for j in chosen:
                    wi, mask, d, s, e, k, seq_of = cols[j]
                    w = waves[wi]
                    plan.append(dict(job=w["job"], direction=w["direction"], anchor=w["anchor"], dur=d, start=s, end=e - COOL,
                                     occ=[w["occ"][v] for v in seq_of(k)]))
            rec = dict(date=date, R=R, **res, plan=plan)
            with open(out_path, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
            print(date, R, res, flush=True)
