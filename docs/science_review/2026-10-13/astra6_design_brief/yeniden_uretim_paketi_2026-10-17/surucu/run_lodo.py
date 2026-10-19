"""Öğrenilmiş örüntü çalışmasının (CS4) yeniden kurulmuş sürücüsü.

Kaynak: 2026-10-15 oturumundaki çekirdek hücreleri (arşivlenmiş konuşma, mesaj 740-748, 804, 867-869) birebir
aktarıldı; yalnız global değişkenler fonksiyon parametresine ve dosya yolları komut satırına taşındı.
Üretilen: lodo_metrics.csv, recall_at_k.csv, construct_learned_vs_cw.csv, prune_in.pkl
Kullanım: python run_lodo.py <veri_klasoru> <wave_exact_jsonl> <cikti_klasoru>
Yeniden kurulmayanlar: lodo_auc_by_day.csv, forward_chaining_auc.csv, succ_feature_importance_fold1005.csv.
"""
import os, sys, json, itertools, pickle
from collections import Counter
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(os.path.dirname(HERE), "src"); sys.path.insert(0, SRC)
import run_waves as RW
from learned_patterns_lodo import (wave_labels, arc_features, pairs_index, freq_tables, freq_feats, fit_models, ARC_F)
from sklearn.metrics import roc_auc_score, average_precision_score
# Korumalı Windows ortamında joblib iş parçacığı havuzu adlandırılmış boru açamıyor (PermissionError). HistGBM'in
# özellik kutulaması backend="threading" ile sabit yazılmış; her özelliğin eşikleri bağımsız hesaplandığından
# tek işçiyle çalıştırmak sonucu değiştirmez.
import sklearn.ensemble._hist_gradient_boosting.binning as _hgb_binning
from sklearn.utils.parallel import Parallel as _SkParallel
class _TekIsciParallel(_SkParallel):
    def __init__(self, *a, **k):
        k["n_jobs"] = 1; k.pop("backend", None); super().__init__(*a, **k)
_hgb_binning.Parallel = _TekIsciParallel
sys.path.insert(0, RW.ROOT)
from uniride_core.algorithms import feasibility_certificate as FC
CAP_SW, CAP_SO, TCAP = 4, 5, 150


def build_W(D, recs):                                   # hücre 740
    waves = RW.load_waves(D)
    mats = {d: RW.load_matrix(D, d) for d in sorted({w["date"] for w in waves})}
    rec_by = {r["job_key"]: r for r in recs}; W = []
    for w in waves:
        key = f'{w["job"]}|R{w["R"]}'; r = rec_by[key]
        M, idx, sha = mats[w["date"]]
        locs = [RW.loc_of(o) for o in w["occ"]]
        li = [idx[l] for l in locs] + [idx["D.Kampus"]]
        C = M[np.ix_(li, li)].astype(np.int32)
        pos = {o: k for k, o in enumerate(w["occ"])}
        routes = [[pos[o] for o in rt] for rt in r["ex_routes_occ"]]
        assert sorted(sum(routes, [])) == list(range(len(locs)))
        durs = [int(C[len(locs), rt[0]] + sum(C[a, b] for a, b in zip(rt, rt[1:])) + C[rt[-1], len(locs)]) for rt in routes]
        assert sum(durs) == r["ex_dur"], key
        W.append(dict(key=key, date=w["date"], R=w["R"], job=w["job"], direction=w["direction"], n=len(locs), locs=locs,
                      is_sw=[l.startswith("Sw") for l in locs], C=C, routes=routes, opt_routes=len(routes), opt_dur=int(sum(durs)),
                      ga_routes=w["ga_routes"], ga_dur=w["ga_dur"]))
    return W


def build_rows(w, tabs):                                # hücre 742
    X = arc_features(w); F = freq_feats(w, tabs); S, A, B = wave_labels(w)
    P = pairs_index(w["n"]); y = np.array([[S[i, j], A[i, j], B[i, j]] for i, j in P], float)
    return X, F, y, P


def nested_lodo(W, days):                               # hücre 742: iç içe LODO
    data = {}
    for test_day in days:
        train_days = [d for d in days if d != test_day]
        tabs_full = freq_tables([w for w in W if w["date"] in train_days])
        tr, te = [], []
        for w in W:
            if w["n"] < 2: continue
            if w["date"] == test_day:
                te.append((w, *build_rows(w, tabs_full)))
            else:
                tabs_in = freq_tables([v for v in W if v["date"] in train_days and v["date"] != w["date"]])
                tr.append((w, *build_rows(w, tabs_in)))
        data[test_day] = (tr, te, tabs_full)
    return data


def score_wave(mods, X, F, target):                     # hücre 744
    XF = np.hstack([X, F]); out = {}
    for k, m in mods.items(): out[k] = m.predict_proba(XF if "hyb" in k else X)[:, 1]
    fi = ARC_F.index
    if target == 0: out["GEO"] = -np.minimum(X[:, fi("c_ij")], X[:, fi("c_ji")]); out["FREQ"] = F[:, 0]
    if target == 1: out["GEO"] = -X[:, fi("c_ij")]; out["FREQ"] = F[:, 1]
    if target == 2:
        out["RADIAL"] = np.where(X[:, fi("pickup")] > 0, X[:, fi("d0_i-d0_j")], -X[:, fi("d0_i-d0_j")]); out["FREQ"] = F[:, 2]
    return out


def eval_target(SC, days, target, nmin=2):              # hücre 744
    res = {}
    for d in days:
        for w, P, sc, y in SC[(d, target)]:
            if w["n"] < nmin: continue
            for mname, s in sc.items(): res.setdefault(mname, []).append((y[:, target], s, y[:, 0], w, P))
    out = {}
    for mname, L in res.items():
        yy = np.concatenate([a for a, *_ in L]); ss = np.concatenate([b for _, b, *_ in L])
        out[mname] = dict(AUC=roc_auc_score(yy, ss), AP=average_precision_score(yy, ss), base=yy.mean())
    return out


def prec_acc(SC, days, nmin):                           # hücre 746
    out = {}
    for d in days:
        for w, P, sc, y in SC[(d, 2)]:
            if w["n"] < nmin: continue
            pi = {p: k for k, p in enumerate(P)}
            for mname, s in sc.items():
                o = out.setdefault(mname, [0.0, 0])
                for (i, j), k in pi.items():
                    if i < j and y[k, 0] > 0:
                        a, b = s[k], s[pi[(j, i)]]
                        o[0] += 0.5 if a == b else float((a > b) == (y[k, 2] > 0)); o[1] += 1
    return {m: round(v[0] / v[1], 3) for m, v in out.items()}, next(iter(out.values()))[1]


def recall_at_k(SC, days, nmin, ks=(1, 2, 3, 4, 5)):    # hücre 746
    out = {}
    for d in days:
        for w, P, sc, y in SC[(d, 1)]:
            if w["n"] < nmin: continue
            n = w["n"]; pi = {p: k for k, p in enumerate(P)}
            succ = {rt[a]: rt[a + 1] for rt in w["routes"] for a in range(len(rt) - 1)}
            for mname, s in sc.items():
                o = out.setdefault(mname, np.zeros(len(ks) + 1))
                for i, j in succ.items():
                    cand = sorted([jj for jj in range(n) if jj != i], key=lambda jj: -s[pi[(i, jj)]])
                    r = cand.index(j) + 1
                    o[:-1] += [r <= k for k in ks]; o[-1] += 1
    return {m: [round(x, 3) for x in (v[:-1] / v[-1])] for m, v in out.items()}, next(iter(out.values()))[-1]


def route_eval(w, rt):                                  # hücre 804
    C, n = w["C"], w["n"]; path = sum(int(C[a, b]) for a, b in zip(rt, rt[1:]))
    dur = int(C[n, rt[0]]) + path + int(C[rt[-1], n])
    ride = (path + int(C[rt[-1], n])) if w["direction"] == "pickup" else (int(C[n, rt[0]]) + path)
    sw = sum(w["is_sw"][i] for i in rt); so = len(rt) - sw
    return dur, (dur <= TCAP and ride <= w["R"] and sw <= CAP_SW and so <= CAP_SO)


def best_order(w, rt):
    if len(rt) <= 1: return rt
    best, bd = rt, route_eval(w, rt)[0] if route_eval(w, rt)[1] else 10 ** 9
    if len(rt) > 8: return rt
    for p in itertools.permutations(rt):
        d, ok = route_eval(w, list(p))
        if ok and d < bd: best, bd = list(p), d
    return best


def savings_construct(w, score, reseq=False):
    n = w["n"]; routes = {i: [i] for i in range(n)}; rid = list(range(n))
    cand = sorted(((score[i, j], i, j) for i in range(n) for j in range(n) if i != j and np.isfinite(score[i, j])), reverse=True)
    for s, i, j in cand:
        a, b = rid[i], rid[j]
        if a == b or routes[a][-1] != i or routes[b][0] != j: continue
        new = routes[a] + routes[b]
        if route_eval(w, new)[1] or (reseq and route_eval(w, best_order(w, new))[1]):
            if reseq: new = best_order(w, new)
            routes[a] = new; del routes[b]
            for v in new: rid[v] = a
    return [best_order(w, r) for r in routes.values()] if reseq else list(routes.values())


def check_solution(w, R_):
    n = w["n"]; Cf = w["C"].astype(float)
    dem = [(1, 0) if s else (0, 1) for s in w["is_sw"]] + [(0, 0)]
    viol = (FC.check_occurrence_coverage(R_, n + 1, n) + FC.check_depot_closure(R_, n, n + 1) + FC.check_capacity_vectors(R_, dem, [CAP_SW, CAP_SO])
            + FC.check_duration(R_, Cf, n, TCAP) + FC.check_ride_time(R_, Cf, n, w["R"], w["direction"]))
    return len(viol)


def main(D, jsonl, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    recs = [json.loads(l) for l in open(jsonl, encoding="utf-8")]
    W = build_W(D, recs); days = sorted({w["date"] for w in W})
    print(len(W), "hücre", Counter(w["n"] for w in W), flush=True)
    data = nested_lodo(W, days)
    SC = {}
    for d in days:
        tr, te, _ = data[d]
        for target in (0, 1, 2):
            mods = fit_models(tr, target)
            SC[(d, target)] = [(t[0], t[4], score_wave(mods, t[1], t[2], target), t[3]) for t in te]
    print("modeller eğitildi", flush=True)
    fi = ARC_F.index                                     # hücre 746: DETOUR
    for (d, target), L in SC.items():
        for w, P, sc, y in L:
            X = arc_features(w); det = X[:, fi("detour")]; infeas = X[:, fi("R_slack")] < 0
            if target == 1: sc["DETOUR"] = np.where(infeas, -1e6, -det)
            if target == 0:
                pi = {p: k for k, p in enumerate(P)}; rev = np.array([pi[(j, i)] for i, j in P])
                best = np.minimum(np.where(infeas, 1e6, det), np.where(infeas[rev], 1e6, det[rev])); sc["DETOUR"] = -best
    prune_in = []                                        # hücre 748 (MUTUAL-RANK'tan önce)
    for d in days:
        m_same = {id(t[0]): t for t in SC[(d, 0)]}
        for w, P, sc, y in SC[(d, 1)]:
            if w["n"] < 6: continue
            n = w["n"]; _, _, sc0, _ = m_same[id(w)]
            def mat(s):
                M_ = np.full((n, n), -np.inf)
                for (i, j), k in zip(P, range(len(P))): M_[i, j] = s[k]
                return M_
            prune_in.append(dict(key=w["key"], date=d, n=n, R=w["R"], direction=w["direction"], C=w["C"], is_sw=w["is_sw"],
                                 opt_routes=w["opt_routes"], opt_dur=w["opt_dur"], ga_routes=w["ga_routes"], ga_dur=w["ga_dur"],
                                 succ={m: mat(s) for m, s in sc.items()},
                                 same={m: mat(s) for m, s in sc0.items() if m in ("GBM-geo", "LR-geo", "GBM-hyb", "FREQ", "GEO", "DETOUR")}))
    pickle.dump(prune_in, open(os.path.join(out_dir, "prune_in.pkl"), "wb"))
    rows = []                                            # hücre 804: öğrenilmiş tasarruf yapıcısı
    for d in days:
        for w, P, sc, y in SC[(d, 1)]:
            n = w["n"]
            if n < 2: continue
            C = w["C"].astype(float); sav = np.full((n, n), -np.inf)
            for i in range(n):
                for j in range(n):
                    if i != j: sav[i, j] = C[i, n] + C[n, j] - C[i, j]
            mats_ = {"CW-savings": sav}
            for mname in ["GBM-geo", "LR-geo", "FREQ", "GBM-hyb"]:
                M_ = np.full((n, n), -np.inf)
                for (i, j), v in zip(P, sc[mname]): M_[i, j] = v
                mats_["learned-" + mname] = M_
            for mname, M_ in mats_.items():
                for reseq in (False, True):
                    R_ = savings_construct(w, M_, reseq); durs = [route_eval(w, r)[0] for r in R_]
                    rows.append(dict(key=w["key"], day=d, n=n, method=mname, reseq=reseq, routes=len(R_), dur=sum(durs), viol=check_solution(w, R_),
                                     opt_routes=w["opt_routes"], opt_dur=w["opt_dur"], ga_routes=w["ga_routes"], ga_dur=w["ga_dur"]))
    CON = pd.DataFrame(rows); CON["d_routes"] = CON.routes - CON.opt_routes; CON["d_min"] = CON.dur - CON.opt_dur
    CON["exact"] = (CON.d_routes == 0) & (CON.d_min == 0); CON.to_csv(os.path.join(out_dir, "construct_learned_vs_cw.csv"), index=False)
    for (d, target), L_ in SC.items():                   # hücre 867: MUTUAL-RANK
        if target != 1: continue
        for w, P, sc, y in L_:
            X = arc_features(w); ro_, ri_ = X[:, fi("rank_out")], X[:, fi("rank_in")]; inf_ = X[:, fi("R_slack")] < 0
            sc["MUTUAL-RANK"] = np.where(inf_, -1e6, -(ro_ + ri_))
    rows = []                                            # hücre 869
    for t, nm in [(0, "ayni_rota"), (1, "ardil_yay")]:
        for nmin in (2, 6):
            for mname, v in eval_target(SC, days, t, nmin).items():
                rows.append(dict(hedef=nm, n_min=nmin, model=mname, AUC=v["AUC"], AP=v["AP"], taban_orani=v["base"]))
    for nmin in (2, 6):
        acc, npairs = prec_acc(SC, days, nmin)
        for mname, v in acc.items(): rows.append(dict(hedef="oncelik", n_min=nmin, model=mname, dogruluk=v, n_cift=npairs))
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, "lodo_metrics.csv"), index=False)
    rk, nsucc = recall_at_k(SC, days, 6)
    RK = pd.DataFrame([dict(model=m, **{f"recall@{k}": v[k - 1] for k in range(1, 6)}) for m, v in rk.items()]); RK["n_ardil"] = nsucc
    RK.to_csv(os.path.join(out_dir, "recall_at_k.csv"), index=False)
    print("bitti", flush=True)


if __name__ == "__main__":
    import joblib
    # Korumalı ortamda joblib iş parçacığı havuzu (adlandırılmış boru) açılamıyor; HistGBM özellik kutulaması
    # özellik başına bağımsız olduğundan sıralı arka uç sonucu değiştirmez.
    with joblib.parallel_config(backend="sequential"):
        main(sys.argv[1], sys.argv[2], sys.argv[3])
