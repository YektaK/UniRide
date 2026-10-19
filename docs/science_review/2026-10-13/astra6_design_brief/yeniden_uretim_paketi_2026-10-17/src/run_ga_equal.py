
import os, sys, json, time
ws = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ws)
import run_esn, run_waves
D, esn_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
waves = run_waves.load_waves(D)
mats = {d: run_waves.load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
inst = {f'{w["job"]}|R{w["R"]}': w for w in run_esn.scale_instances(waves)}
cfg = json.load(open(os.path.join(D, "run_manifest.json"), encoding="utf-8"))["ga_effective_configuration"]
done = set()
if os.path.exists(out): done = {json.loads(l)["key"] for l in open(out, encoding="utf-8")}
while True:
    esn = [json.loads(l) for l in open(esn_path, encoding="utf-8")]
    todo = [r for r in esn if r["key"] not in done]
    if not todo:
        if len(esn) >= len(inst): break
        time.sleep(60); continue
    for r in todo:
        w = inst[r["key"]]; C, is_sw = run_esn.build(w, mats)
        t0 = time.time(); best = None; runs = []; seed = 100
        while time.time() - t0 < r["esn_time"]:
            rt, du, dt = run_esn.ga(w, C, is_sw, seed, cfg)
            v = run_esn.certify(rt, C, is_sw, w["R"], w["direction"])
            k = (v > 0, len(rt), sum(du)); runs.append(dict(seed=seed, routes=len(rt), dur=int(sum(du)), viol=v, time=round(dt, 2)))
            if best is None or k < best: best = k
            seed += 1
        rec = dict(key=r["key"], n=r["n"], esn_time=r["esn_time"], ga_eq_time=round(time.time() - t0, 2), ga_eq_runs=len(runs),
                   ga_eq_best_routes=best[1], ga_eq_best_dur=best[2], ga_eq_best_feasible=not best[0], runs=runs)
        with open(out, "a", encoding="utf-8") as fh: fh.write(json.dumps(rec) + "\n")
        done.add(r["key"]); print(r["key"], r["n"], best, len(runs), flush=True)
