"""Gün düzeyi tablo: GA arşiv filosu, sıralı kesin plan, LB0 ve ortak modelin bağımsız doğrulaması.

Kaynak: 2026-10-14 oturumundaki çekirdek hücreleri (arşivlenmiş konuşma, mesaj 597 ve 601) birebir aktarıldı.
Kullanım: python gun_duzeyi.py <veri_klasoru> <dalga_jsonl> <gun_ortak_jsonl> <cikti_klasoru>
Üretilen: day_level_4sw5so.csv, weekly_fleet_4sw5so.csv
Durum (2026-10-17): yazıldı, henüz çalıştırılmadı (kod korumalı alanı açılamadı).
"""
import os, sys, json, glob, re, collections
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import run_waves
sys.path.insert(0, run_waves.ROOT)
from uniride_core.algorithms import feasibility_certificate as FC
COOL = 10


def min_vehicles(iv):
    ev = sorted([(s, 1) for s, e in iv] + [(e + COOL, -1) for s, e in iv], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d_ in ev:
        cur += d_; best = max(best, cur)
    return best


def main(D, wave_jsonl, day_jsonl, out_dir):
    waves_all = run_waves.load_waves(D)
    mats = {d: run_waves.load_matrix(D, d) for d in sorted({w["date"] for w in waves_all})}

    def verify_plan(date, R, plan):
        M_, idx_, _ = mats[date]
        waves = {w["job"]: w for w in waves_all if w["date"] == date and w["R"] == R}
        errs = 0; ivs = collections.defaultdict(list); by_job = collections.defaultdict(list)
        for p_ in plan:
            by_job[p_["job"]].append(p_)
        for job, w in waves.items():
            occ = w["occ"]; pos = {o: i for i, o in enumerate(occ)}; n = len(occ)
            locs = [idx_[run_waves.loc_of(o)] for o in occ] + [idx_["D.Kampus"]]
            C = M_[np.ix_(locs, locs)].astype(float)
            dem = [(1, 0) if run_waves.loc_of(o).startswith("Sw") else (0, 1) for o in occ] + [(0, 0)]
            ps = by_job[job]; routes = [[pos[o] for o in p_["occ"]] for p_ in ps]
            errs += len(FC.check_capacity_vectors(routes, dem, [4, 5]) + FC.check_duration(routes, C, n, 150)
                        + FC.check_ride_time(routes, C, n, R, w["direction"]) + FC.check_depot_closure(routes, n, n + 1))
            for p_, r in zip(ps, routes):
                d = int(C[n, r[0]] + sum(C[a, b] for a, b in zip(r, r[1:])) + C[r[-1], n])
                errs += (d != p_["dur"])
                ivs["all"].append((w["anchor"] - d, w["anchor"]) if w["direction"] == "pickup" else (w["anchor"], w["anchor"] + d))
            errs += len(FC.check_occurrence_coverage(routes, n + 1, n)) + (sum(len(r) for r in routes) != n)
        return errs, min_vehicles(ivs["all"])

    J = {(r["date"], r["R"]): r for r in (json.loads(l) for l in open(day_jsonl, encoding="utf-8"))}
    ex = pd.DataFrame([json.loads(l) for l in open(wave_jsonl, encoding="utf-8")]).drop_duplicates("job_key", keep="last")
    arch = []
    for f in sorted(glob.glob(os.path.join(D, "*_repeat1.response.json"))):
        date, R = re.search(r"(\d{4}-\d{2}-\d{2})_R(\d+)_", os.path.basename(f)).groups()
        rj = json.load(open(f, encoding="utf-8")); vs = rj["vehicleSummary"]
        arch.append(dict(date=date, R=int(R), ga_fleet=vs["minimumVehicles"], ga_routes=len(rj["routeIntervals"]),
                         ga_min=sum(x["endMinutes"] - x["startMinutes"] for x in rj["routeIntervals"])))
    rows = []
    for a in arch:
        g = ex[(ex.date == a["date"]) & (ex.R == a["R"])]
        iv = [(r.anchor - d, r.anchor) if r.direction == "pickup" else (r.anchor, r.anchor + d) for r in g.itertuples() for d in r.ex_route_durs]
        lb0 = 0
        for t in sorted({r.anchor + k for r in g.itertuples() for k in range(COOL)}):
            lb0 = max(lb0, int(sum(r.ex_routes for r in g.itertuples() if r.anchor <= t < r.anchor + COOL)))
        seq_fleet = min_vehicles(iv); jr = J[(a["date"], a["R"])]
        row = dict(**a, lb0=lb0, seq_fleet=seq_fleet, seq_routes=int(g.ex_routes.sum()), seq_min=int(g.ex_dur.sum()))
        if jr.get("s3") == 0:
            errs, fleet = verify_plan(a["date"], a["R"], jr["plan"])
            row.update(joint_K=jr["K"], joint_proof="joint MIP optimal", joint_routes=jr["routes"], joint_min=jr["minutes"],
                       verify_errs=errs, verify_fleet=fleet, joint_time_s=jr.get("time_s"))
        elif seq_fleet == lb0:
            why = "time limit" if jr.get("s1") == 1 else "status %s" % jr.get("s1")
            row.update(joint_K=seq_fleet, joint_proof="seq plan = LB0 (MIP %s)" % why,
                       joint_routes=None, joint_min=None, verify_errs=0, verify_fleet=seq_fleet, joint_time_s=None)
        else:
            row.update(joint_K=None, joint_proof="open", joint_routes=None, joint_min=None, verify_errs=None, verify_fleet=None, joint_time_s=None)
        rows.append(row)
    DAY = pd.DataFrame(rows)
    os.makedirs(out_dir, exist_ok=True)
    DAY.to_csv(os.path.join(out_dir, "day_level_4sw5so.csv"), index=False)
    bad = DAY[(DAY.verify_errs.fillna(0) != 0) | (DAY.verify_fleet != DAY.joint_K)]
    if len(bad):
        print("DOGRULAMA UYUSMAZLIGI:"); print(bad[["date", "R", "joint_K", "verify_fleet", "verify_errs", "joint_proof"]].to_string())
    assert (DAY.verify_errs.fillna(0) == 0).all() and (DAY.verify_fleet == DAY.joint_K).all()
    wk = DAY.groupby("R").agg(ga_fleet=("ga_fleet", "max"), seq_fleet=("seq_fleet", "max"), joint_fleet=("joint_K", "max"),
                              ga_min=("ga_min", "sum"), seq_min=("seq_min", "sum"))
    wk.to_csv(os.path.join(out_dir, "weekly_fleet_4sw5so.csv"))
    print(wk.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:5])
