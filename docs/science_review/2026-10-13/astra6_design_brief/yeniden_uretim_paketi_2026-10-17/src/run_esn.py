
import os, sys, json, time, random
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
ROOT = os.environ.get("UNIRIDE_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 6)); sys.path.insert(0, ROOT)
import run_waves, esn_sp
from uniride_core.algorithms import feasibility_certificate as FC
from uniride_core.algorithms.ga_split_engine import solve_ga_split
from uniride_core.algorithms.string_split_decoder import Direction
CAP_SW, CAP_SO, T = 4, 5, 150

def build(w, mats):
    M, idx, _ = mats[w["date"]]
    locs = [idx[run_waves.loc_of(o)] for o in w["occ"]] + [idx["D.Kampus"]]
    C = M[np.ix_(locs, locs)].astype(np.int32)
    return C, [run_waves.loc_of(o).startswith("Sw") for o in w["occ"]]

def certify(routes, C, is_sw, R, direction):
    n = len(is_sw); dem = [(1, 0) if s else (0, 1) for s in is_sw] + [(0, 0)]; Cf = C.astype(float)
    return len(FC.check_occurrence_coverage(routes, n + 1, n) + FC.check_depot_closure(routes, n, n + 1)
               + FC.check_capacity_vectors(routes, dem, [CAP_SW, CAP_SO]) + FC.check_duration(routes, Cf, n, T)
               + FC.check_ride_time(routes, Cf, n, R, direction))

def dur_of(C, r, n): return int(C[n, r[0]] + sum(C[a, b] for a, b in zip(r, r[1:])) + C[r[-1], n])

def ga(w, C, is_sw, seed, cfg):
    n = len(is_sw); keys = list(w["occ"]); dep = "D.Kampus"; allk = keys + [dep]
    dm = {a: {b: float(C[i, j]) for j, b in enumerate(allk)} for i, a in enumerate(allk)}
    dem = {k: ((1, 0) if s else (0, 1)) for k, s in zip(keys, is_sw)}
    t0 = time.time()
    sol = solve_ga_split(keys, dep, dm, dem, CAP_SW, CAP_SO, T, cfg, random.Random(seed),
                         direction=Direction.PICKUP if w["direction"] == "pickup" else Direction.DROPOFF,
                         is_asymmetric=True, max_ride_time=w["R"])
    pos = {k: i for i, k in enumerate(keys)}
    routes = [[pos[x] for x in r] for r in sol.final_result["routes"]]
    return routes, [dur_of(C, r, n) for r in routes], time.time() - t0

def scale_instances(waves):
    out = []
    for date in sorted({w["date"] for w in waves}):
        ws90 = [w for w in waves if w["date"] == date and w["R"] == 90]
        pick = [o for w in ws90 if w["direction"] == "pickup" for o in w["occ"]]
        allo = [o for w in ws90 for o in w["occ"]]
        out.append(dict(date=date, R=90, job=f"{date}:S1_day_pickups", direction="pickup", anchor=0, occ=pick))
        out.append(dict(date=date, R=90, job=f"{date}:S2_day_all", direction="pickup", anchor=0, occ=allo))
        out.append(dict(date=date, R=90, job=f"{date}:S3_day_all_x2", direction="pickup", anchor=0,
                        occ=allo + [o + "#b" for o in allo]))
    return out

if __name__ == "__main__":
    mode, D, out = sys.argv[1], sys.argv[2], sys.argv[3]
    waves = run_waves.load_waves(D)
    mats = {d: run_waves.load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
    done = set()
    if os.path.exists(out): done = {json.loads(l)["key"] for l in open(out, encoding="utf-8")}
    cfg = json.load(open(os.path.join(D, "run_manifest.json"), encoding="utf-8"))["ga_effective_configuration"]
    if mode == "real":
        todo = waves
    else:
        todo = scale_instances(waves)
    for w in sorted(todo, key=lambda x: len(x["occ"])):
        key = f'{w["job"]}|R{w["R"]}'
        if key in done: continue
        C, is_sw = build(w, mats); n = len(is_sw)
        rec = dict(key=key, n=n, n_sw=int(sum(is_sw)), R=w["R"], direction=w["direction"],
                   lseat=max(-(-sum(is_sw) // CAP_SW), -(-(n - sum(is_sw)) // CAP_SO)))
        budget = 30.0 if mode == "real" else 120.0
        t0 = time.time(); sol, tel = esn_sp.solve_wave(C, is_sw, w["R"], T, w["direction"], g=10, u_max=16, time_budget=budget)
        rec["esn_time"] = round(time.time() - t0, 2)
        if sol is None:
            rec["esn_routes"] = None
        else:
            routes, durs = sol
            assert [dur_of(C, r, n) for r in routes] == durs
            rec.update(esn_routes=len(routes), esn_dur=int(sum(durs)), esn_viol=certify(routes, C, is_sw, w["R"], w["direction"]),
                       esn_tel={k: v for k, v in tel.items() if k != "sp_status"}, esn_sp_status=tel["sp_status"])
        if mode == "scale":
            rec["ga"] = []
            for seed in range(1, 6):
                r_, d_, dt = ga(w, C, is_sw, seed, cfg)
                rec["ga"].append(dict(seed=seed, routes=len(r_), dur=int(sum(d_)), time=round(dt, 2), viol=certify(r_, C, is_sw, w["R"], w["direction"])))
        with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
        print(key, n, rec.get("esn_routes"), rec.get("esn_dur"), rec["esn_time"], [ (g["routes"], g["dur"], g["time"]) for g in rec.get("ga", [])], flush=True)
