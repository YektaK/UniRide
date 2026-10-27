"""OPTIMAL olmayan dalga hücrelerini iki aşamalı HiGHS ile yeniden çözer (U1-not'taki işlemin betik hali).

Aşama 1: en az rota (küme bölümleme). Aşama 2: rota sayısı sabitken en az toplam dakika.
Kullanım: python resolve_two_stage.py <veri_klasoru> <dalga_jsonl> <cikti_jsonl> [sure_siniri_s=1800]
Çıktı: girdideki bütün kayıtlar; yeniden çözülenlerde status/solver/ex_* alanları güncellenir, solver="highs-2stage".
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import run_waves as RW, wave_exact
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csc_matrix, vstack, csr_matrix


def two_stage(masks, costs, n, tl):
    ri, cj = [], []
    for k, m in enumerate(masks):
        mm = int(m); i = 0
        while mm:
            if mm & 1: ri.append(i); cj.append(k)
            mm >>= 1; i += 1
    A = csc_matrix((np.ones(len(ri)), (ri, cj)), shape=(n, len(masks))); o = dict(time_limit=tl, mip_rel_gap=0)
    r1 = milp(np.ones(len(masks)), constraints=LinearConstraint(A, 1, 1), integrality=np.ones(len(masks)), bounds=Bounds(0, 1), options=o)
    if r1.status != 0: return f"S1_{r1.status}", None
    K = int(round(r1.fun))
    A2 = vstack([A, csr_matrix(np.ones((1, len(masks))))]).tocsc()
    r2 = milp(np.asarray(costs, float), constraints=LinearConstraint(A2, np.r_[np.ones(n), K], np.r_[np.ones(n), K]),
              integrality=np.ones(len(masks)), bounds=Bounds(0, 1), options=o)
    if r2.status != 0: return f"S2_{r2.status}", None
    return "OPTIMAL", [k for k in range(len(masks)) if r2.x[k] > 0.5]


def main(D, inp, out, tl=1800.0):
    recs = [json.loads(l) for l in open(inp, encoding="utf-8")]
    waves = {f'{w["job"]}|R{w["R"]}': w for w in RW.load_waves(D)}
    mats = {}
    for r in recs:
        if r["status"] == "OPTIMAL": continue
        w = waves[r["job_key"]]
        if w["date"] not in mats: mats[w["date"]] = RW.load_matrix(D, w["date"])
        M, idx, sha = mats[w["date"]]
        locs = [idx[RW.loc_of(o)] for o in w["occ"]] + [idx["D.Kampus"]]
        C = M[np.ix_(locs, locs)].astype(np.int32); n = len(w["occ"]); is_sw = [RW.loc_of(o).startswith("Sw") for o in w["occ"]]
        t0 = time.time()
        masks, costs, seq_of = wave_exact.enumerate_routes(C, n, is_sw, RW.CAP_SW, RW.CAP_SO, w["R"], RW.T_CAP, w["direction"])
        status, chosen = two_stage(masks, costs, n, tl)
        print(r["job_key"], status, round(time.time() - t0, 1), flush=True)
        if status == "OPTIMAL":
            routes = [seq_of(c) for c in chosen]
            durs = [int(C[n, q[0]] + sum(C[a, b] for a, b in zip(q, q[1:])) + C[q[-1], n]) for q in routes]
            r.update(status="OPTIMAL", solver="highs-2stage", ex_routes=len(routes), ex_dur=int(sum(durs)), ex_route_durs=durs,
                     ex_routes_occ=[[w["occ"][v] for v in q] for q in routes], t_sp=round(time.time() - t0, 3))
    with open(out, "w", encoding="utf-8") as fh:
        for r in recs: fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 1800.0)
