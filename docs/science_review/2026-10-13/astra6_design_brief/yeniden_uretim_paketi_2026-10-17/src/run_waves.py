
import os, sys, json, glob, re, time
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ws)
ROOT = os.environ.get("UNIRIDE_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 6))
sys.path.insert(0, ROOT)
import wave_exact
from uniride_core.algorithms import feasibility_certificate as FC
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csc_matrix

CAP_SW, CAP_SO, T_CAP, WEIGHT = 4, 5, 150, 10000

def loc_of(o): return o.split(":")[-1].split("~")[0]

def load_waves(D):
    waves = []
    for f in sorted(glob.glob(os.path.join(D, "*_repeat1.response.json"))):
        date, R = re.search(r"(\d{4}-\d{2}-\d{2})_R(\d+)_", os.path.basename(f)).groups()
        rj = json.load(open(f, encoding="utf-8"))
        for j in rj["jobs"]:
            occ = [s for r in j["result"]["routes"] for s in r["student_ids"]]
            waves.append(dict(date=date, R=int(R), job=j["id"], direction=j["direction"], anchor=j["anchorMinutes"],
                              occ=occ, ga_routes=len(j["result"]["routes"]), ga_dur=j["result"]["total_duration_minutes"],
                              ga_route_durs=[r["total_duration_minutes"] for r in j["result"]["routes"]]))
    return waves

def load_matrix(D, date):
    mj = json.load(open(glob.glob(os.path.join(D, f"{date}_R60*.matrix.json"))[0], encoding="utf-8"))
    codes = sorted({a["origin_code"] for a in mj["arcs"]} | {a["destination_code"] for a in mj["arcs"]})
    idx = {c: i for i, c in enumerate(codes)}
    M = np.zeros((len(codes), len(codes)), dtype=np.int64)
    for a in mj["arcs"]: M[idx[a["origin_code"]], idx[a["destination_code"]]] = a["duration_minutes"]
    return M, idx, mj["sha256"]

def highs_sp(masks, costs, n, time_limit):
    ri, cj = [], []
    for k, m in enumerate(masks):
        mm = int(m); i = 0
        while mm:
            if mm & 1: ri.append(i); cj.append(k)
            mm >>= 1; i += 1
    A = csc_matrix((np.ones(len(ri)), (ri, cj)), shape=(n, len(masks)))
    r = milp(WEIGHT + np.asarray(costs, float), constraints=LinearConstraint(A, 1, 1),
             integrality=np.ones(len(masks)), bounds=Bounds(0, 1), options={"time_limit": time_limit, "mip_rel_gap": 0})
    chosen = [k for k in range(len(masks)) if r.x is not None and r.x[k] > 0.5]
    return ("OPTIMAL" if r.status == 0 else f"HIGHS_{r.status}"), chosen

def main(D, out, wid, nw, tl):
    waves = load_waves(D)
    mats = {d: load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
    done = set()
    if os.path.exists(out):
        for l in open(out, encoding="utf-8"): done.add(json.loads(l)["job_key"])
    order = sorted(range(len(waves)), key=lambda i: -len(waves[i]["occ"]))
    for rank, i in enumerate(order):
        if rank % nw != wid: continue
        w = waves[i]; key = f'{w["job"]}|R{w["R"]}'
        if key in done: continue
        M, idx, sha = mats[w["date"]]
        locs = [idx[loc_of(o)] for o in w["occ"]] + [idx["D.Kampus"]]
        C = M[np.ix_(locs, locs)].astype(np.int32); n = len(w["occ"])
        is_sw = [loc_of(o).startswith("Sw") for o in w["occ"]]
        t0 = time.time()
        masks, costs, seq_of = wave_exact.enumerate_routes(C, n, is_sw, CAP_SW, CAP_SO, w["R"], T_CAP, w["direction"])
        t1 = time.time()
        status, chosen = highs_sp(masks, costs, n, tl); solver = "highs"
        if status != "OPTIMAL":
            status, chosen, _, _ = wave_exact.solve_partition(masks, costs, n, time_limit=tl); solver = "cpsat"
        t2 = time.time()
        routes = [seq_of(c) for c in chosen]
        durs = [int(C[n, r[0]] + sum(C[a, b] for a, b in zip(r, r[1:])) + C[r[-1], n]) for r in routes]
        assert durs == [int(costs[c]) for c in chosen]
        dem = [(1, 0) if s else (0, 1) for s in is_sw] + [(0, 0)]
        Cf = C.astype(float)
        viol = (FC.check_occurrence_coverage(routes, n + 1, n) + FC.check_depot_closure(routes, n, n + 1)
                + FC.check_capacity_vectors(routes, dem, [CAP_SW, CAP_SO]) + FC.check_duration(routes, Cf, n, T_CAP)
                + FC.check_ride_time(routes, Cf, n, w["R"], w["direction"]))
        nsw = sum(is_sw)
        rec = dict(job_key=key, date=w["date"], R=w["R"], job=w["job"], direction=w["direction"], anchor=w["anchor"], n=n,
                   n_sw=nsw, lseat=max(-(-nsw // CAP_SW), -(-(n - nsw) // CAP_SO)), n_columns=int(len(masks)),
                   status=status, solver=solver, ex_routes=len(routes), ex_dur=int(sum(durs)), ex_route_durs=durs,
                   ex_routes_occ=[[w["occ"][v] for v in r] for r in routes], ga_routes=w["ga_routes"], ga_dur=w["ga_dur"],
                   ga_route_durs=w["ga_route_durs"], cert_violations=len(viol), t_enum=round(t1 - t0, 3),
                   t_sp=round(t2 - t1, 3), matrix_sha=sha)
        with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
        print(key, n, status, solver, len(routes), sum(durs), w["ga_routes"], w["ga_dur"], round(t2 - t0, 1), flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
