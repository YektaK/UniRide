
import os, sys, json, time
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
import run_esn, run_waves, esn_sp_v3
D, out = sys.argv[1], sys.argv[2]; only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
waves = run_waves.load_waves(D)
mats = {d: run_waves.load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
cfg = json.load(open(os.path.join(D, "run_manifest.json"), encoding="utf-8"))["ga_effective_configuration"]
done = set()
if os.path.exists(out): done = {json.loads(l)["key"] for l in open(out, encoding="utf-8")}
insts = run_esn.scale_instances(waves)
for w in sorted(insts, key=lambda x: len(x["occ"])):
    key = f'{w["job"]}|R{w["R"]}'
    if key in done or (only and not any(o in key for o in only)): continue
    C, is_sw = run_esn.build(w, mats); n = len(is_sw)
    loc_ids = [run_waves.loc_of(o.split("#")[0]) for o in w["occ"]]
    t0 = time.time(); ga_sols = []; ga_meta = []
    for seed in (1, 2):
        r_, d_, dt = run_esn.ga(w, C, is_sw, seed, cfg); ga_sols.append(r_); ga_meta.append((len(r_), int(sum(d_)), round(dt, 2)))
    t_ga = time.time() - t0
    sol, tel = esn_sp_v3.solve_wave_v3(C, is_sw, w["R"], 150, w["direction"], loc_ids, ga_sols, time_budget=max(30.0, 120.0 - t_ga))
    routes, durs = sol
    assert [run_esn.dur_of(C, r, n) for r in routes] == durs
    rec = dict(key=key, n=n, v3_routes=len(routes), v3_dur=int(sum(durs)), v3_viol=run_esn.certify(routes, C, is_sw, w["R"], w["direction"]),
               v3_time=round(time.time() - t0, 2), ga_inside=ga_meta, tel={k: v for k, v in tel.items() if k != "sp_status"}, sp_status=tel["sp_status"])
    with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
    print(key, n, rec["v3_routes"], rec["v3_dur"], rec["v3_time"], ga_meta, tel.get("initial"), tel.get("final"), flush=True)
