
import os, sys, json, time, pickle
import numpy as np
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
import run_esn, run_waves, esn_sp_v3, esn_sp_v3L
D, out, wid, nw = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
TM = pickle.load(open(os.path.join(ws, "results", "transfer_models.pkl"), "rb"))
waves = run_waves.load_waves(D)
mats = {d: run_waves.load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
cfg = json.load(open(os.path.join(D, "run_manifest.json"), encoding="utf-8"))["ga_effective_configuration"]
done = set()
if os.path.exists(out): done = {json.loads(l)["key"] for l in open(out, encoding="utf-8")}

def feats(C, n, R, is_sw, locs):
    d0 = C[:n, n].astype(float); Cn = C[:n, :n].astype(float)
    ro = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=1), axis=1); ri = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=0), axis=0)
    I, J = np.where(~np.eye(n, dtype=bool)); cij, cji = Cn[I, J], Cn[J, I]
    detour = cij + d0[J] - d0[I]; ride = cij + d0[J]
    sl = np.array([locs[i] == locs[j] for i, j in zip(I, J)], float); sw = np.array(is_sw, float)
    X = np.column_stack([cij, cji, d0[I], d0[J], d0[I] - d0[J], detour, np.minimum(ro[I, J], 15), np.minimum(ri[I, J], 15), R - ride, sl, sw[I], sw[J],
                         np.full(len(I), R), np.ones(len(I))])
    return X, I, J

insts = sorted(run_esn.scale_instances(waves), key=lambda x: len(x["occ"]))
for k, w in enumerate(insts):
    if k % nw != wid: continue
    key = f'{w["job"]}|R{w["R"]}'
    if key in done: continue
    C, is_sw = run_esn.build(w, mats); n = len(is_sw)
    loc_ids = [run_waves.loc_of(o.split("#")[0]) for o in w["occ"]]
    X, I, J = feats(C, n, w["R"], is_sw, loc_ids)
    p = TM[w["date"]].predict_proba(X)[:, 1]
    P = np.zeros((n, n)); P[I, J] = p; P = (P + P.T) / 2
    for i in range(n):
        for j in range(n):
            if i != j and loc_ids[i] == loc_ids[j]: P[i, j] = 1.0
    t0 = time.time(); ga_sols = []; ga_meta = []
    for seed in (1, 2):
        r_, d_, dt = run_esn.ga(w, C, is_sw, seed, cfg); ga_sols.append(r_); ga_meta.append((len(r_), int(sum(d_)), round(dt, 2)))
    t_ga = time.time() - t0; B = max(30.0, 120.0 - t_ga)
    rec = dict(key=key, n=n, ga=ga_meta, budget=B)
    for arm in ("geo", "learned"):
        t1 = time.time()
        if arm == "geo": sol, tel = esn_sp_v3.solve_wave_v3(C, is_sw, w["R"], 150, w["direction"], loc_ids, ga_sols, time_budget=B)
        else: sol, tel = esn_sp_v3L.solve_wave_v3L(C, is_sw, w["R"], 150, w["direction"], loc_ids, ga_sols, P, time_budget=B)
        routes, durs = sol
        assert [run_esn.dur_of(C, r, n) for r in routes] == durs
        rec[arm] = dict(routes=len(routes), dur=int(sum(durs)), viol=run_esn.certify(routes, C, is_sw, w["R"], w["direction"]), t=round(time.time() - t1, 1),
                        initial=tel.get("initial"), pool_seed=tel.get("pool_seed"), unions_tried=tel.get("unions_tried"), unions_improved=tel.get("unions_improved"))
    with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
    print(key, n, ga_meta, rec["geo"], rec["learned"], flush=True)
