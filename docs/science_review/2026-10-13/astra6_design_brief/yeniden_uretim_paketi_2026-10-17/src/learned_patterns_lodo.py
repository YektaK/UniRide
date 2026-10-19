"""Öğrenilmiş rota örüntüleri — UniRide LODO deneyleri (Claude Science, 2026-10-15).
Bu dosya çekirdekte çalıştırılan fonksiyonların birebir kopyasıdır (inspect.getsource ile dışa aktarıldı).
Sürücü akışı (çekirdekte yapılan):
  1) W = dalga listesi: run_waves.load_waves(D) + wave_exact_4sw5so.jsonl optimum rotaları (key: job|R).
  2) Her test günü için: eğitim satırları (iç içe LODO ile FREQ özellikleri), test satırları; fit_models -> score_wave.
  3) eval_target / prec_acc / recall_at_k; savings_construct (CW vs öğrenilmiş); MUTUAL-RANK taban çizgisi.
  4) prune_exp.py (yay adayı budama + kolon süzgeci), run_esn_learned.py (ESN-SP v3 vs v3L), tsp_learned_cands.py (TSP aday listesi).
Bağımlılıklar: numpy, pandas, scikit-learn (HistGradientBoostingClassifier, LogisticRegression), uniride_core.algorithms.feasibility_certificate.
"""
import itertools
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, average_precision_score
CAP_SW, CAP_SO, TCAP = 4, 5, 150
ARC_F = ["c_ij", "c_ji", "d0_i", "d0_j", "d0_i-d0_j", "detour", "rank_out", "rank_in", "R_slack", "same_loc", "sw_i", "sw_j", "R", "n", "pickup"]
FREQ_F = ["f_same", "f_succ", "f_before", "log_co"]
# NOT: eval_target/prec_acc/recall_at_k global SC ve days sözlüklerini kullanır; check_solution FC (feasibility_certificate) modülünü kullanır.

def wave_labels(w):
    n = w["n"]; same = np.zeros((n, n), bool); succ = np.zeros((n, n), bool); before = np.zeros((n, n), bool)
    for rt in w["routes"]:
        for a in range(len(rt)):
            for b in range(len(rt)):
                if a != b: same[rt[a], rt[b]] = True
                if a < b: before[rt[a], rt[b]] = True
        for a, b in zip(rt, rt[1:]): succ[a, b] = True
    return same, succ, before


def campus_dist(w):
    C, n = w["C"], w["n"]
    return C[:n, n].astype(float) if w["direction"] == "pickup" else C[n, :n].astype(float)


def arc_features(w):
    """ordered pairs i!=j in travel orientation"""
    C, n = w["C"].astype(float), w["n"]; d0 = campus_dist(w); pk = w["direction"] == "pickup"
    Cn = C[:n, :n]
    rank_out = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=1), axis=1)  # rank of j for i
    rank_in = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=0), axis=0)
    rows = []
    for i in range(n):
        for j in range(n):
            if i == j: continue
            cij, cji = Cn[i, j], Cn[j, i]
            # radial: pickup i->j->campus, dropoff campus->i->j
            detour = (cij + d0[j] - d0[i]) if pk else (d0[i] + cij - d0[j])
            ride_ij = (cij + d0[j]) if pk else (d0[i] + cij)   # ride of the end passenger served first/last
            rows.append([cij, cji, d0[i], d0[j], d0[i] - d0[j], detour, rank_out[i, j] / n, rank_in[i, j] / n,
                         w["R"] - ride_ij, float(w["locs"][i] == w["locs"][j]), float(w["is_sw"][i]), float(w["is_sw"][j]),
                         w["R"], n, float(pk)])
    return np.array(rows)


def pairs_index(n): return [(i, j) for i in range(n) for j in range(n) if i != j]


def freq_tables(ws_):
    co, same, succ, before = Counter(), Counter(), Counter(), Counter()
    for w in ws_:
        S, A, B = wave_labels(w); L = w["locs"]; n = w["n"]
        for i in range(n):
            for j in range(n):
                if i == j: continue
                k = (w["direction"], L[i], L[j]); co[k] += 1; same[k] += S[i, j]; succ[k] += A[i, j]; before[k] += B[i, j]
    return co, same, succ, before


def freq_feats(w, tabs, alpha=2.0, priors=(0.3, 0.1, 0.5)):
    co, same, succ, before = tabs; L = w["locs"]; out = []
    for i, j in pairs_index(w["n"]):
        k = (w["direction"], L[i], L[j]); c = co.get(k, 0)
        out.append([(same.get(k, 0) + alpha * priors[0]) / (c + alpha), (succ.get(k, 0) + alpha * priors[1]) / (c + alpha),
                    (before.get(k, 0) + alpha * priors[2]) / (c + alpha), np.log1p(c)])
    return np.array(out)


def build_rows(w, tabs):
    X = arc_features(w); F = freq_feats(w, tabs); S, A, B = wave_labels(w)
    P = pairs_index(w["n"]); y = np.array([[S[i, j], A[i, j], B[i, j]] for i, j in P], float)
    return X, F, y, P


def fit_models(tr, target):
    X = np.vstack([t[1] for t in tr]); F = np.vstack([t[2] for t in tr]); y = np.concatenate([t[3][:, target] for t in tr])
    XF = np.hstack([X, F]); mask = slice(None)
    if target == 2:  # precedence only among same-route pairs
        m = np.concatenate([t[3][:, 0] for t in tr]) > 0; X, XF, y = X[m], XF[m], y[m]
    mods = {}
    mods["LR-geo"] = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)).fit(X, y)
    mods["GBM-geo"] = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=0).fit(X, y)
    mods["LR-hyb"] = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)).fit(XF, y)
    mods["GBM-hyb"] = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=0).fit(XF, y)
    return mods


def score_wave(mods, X, F, target):
    XF = np.hstack([X, F]); out = {}
    for k, m in mods.items(): out[k] = m.predict_proba(XF if "hyb" in k else X)[:, 1]
    fi = ARC_F.index
    if target == 0: out["GEO"] = -np.minimum(X[:, fi("c_ij")], X[:, fi("c_ji")]); out["FREQ"] = F[:, 0]
    if target == 1: out["GEO"] = -X[:, fi("c_ij")]; out["FREQ"] = F[:, 1]
    if target == 2:
        out["RADIAL"] = np.where(X[:, fi("pickup")] > 0, X[:, fi("d0_i-d0_j")], -X[:, fi("d0_i-d0_j")]); out["FREQ"] = F[:, 2]
    return out


def eval_target(target, nmin=2):
    res = {}
    for d in days:
        for w, P, sc, y in SC[(d, target)]:
            if w["n"] < nmin: continue
            for mname, s in sc.items():
                res.setdefault(mname, []).append((y[:, target], s, y[:, 0], w, P))
    out = {}
    for mname, L in res.items():
        yy = np.concatenate([a for a, *_ in L]); ss = np.concatenate([b for _, b, *_ in L])
        if target < 2:
            out[mname] = dict(AUC=roc_auc_score(yy, ss), AP=average_precision_score(yy, ss), base=yy.mean())
        else:
            # pairwise precedence accuracy among same-route pairs: compare s(i,j) vs s(j,i)
            corr = tot = 0
            for yb, s, ysame, w, P in L:
                pi = {p: k for k, p in enumerate(P)}
                for (i, j), k in pi.items():
                    if i < j and ysame[k] > 0:
                        pred = s[k] > s[pi[(j, i)]]; corr += (pred == (yb[k] > 0)); tot += 1
            out[mname] = dict(acc=corr / tot, n_pairs=tot)
    return out


def prec_acc(nmin):
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


def recall_at_k(nmin, ks=(1, 2, 3, 4, 5)):
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


def route_eval(w, rt):
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
    """score[i,j]: merge priority for arc i->j (higher first); tail(A)=i, head(B)=j"""
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
    R_ = [best_order(w, r) for r in routes.values()] if reseq else list(routes.values())
    return R_


def check_solution(w, R_):
    n = w["n"]; Cf = w["C"].astype(float)
    dem = [(1, 0) if s else (0, 1) for s in w["is_sw"]] + [(0, 0)]
    viol = (FC.check_occurrence_coverage(R_, n + 1, n) + FC.check_depot_closure(R_, n, n + 1) + FC.check_capacity_vectors(R_, dem, [CAP_SW, CAP_SO])
            + FC.check_duration(R_, Cf, n, TCAP) + FC.check_ride_time(R_, Cf, n, w["R"], w["direction"]))
    return len(viol)


def arc_features_T(C, n, d0, R, is_sw, locs, pk):
    Cn = C[:n, :n].astype(float)
    ro = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=1), axis=1); ri = np.argsort(np.argsort(Cn + np.eye(n) * 1e9, axis=0), axis=0)
    I, J = np.where(~np.eye(n, dtype=bool))
    cij, cji = Cn[I, J], Cn[J, I]
    detour = (cij + d0[J] - d0[I]) if pk else (d0[I] + cij - d0[J])
    ride = (cij + d0[J]) if pk else (d0[I] + cij)
    sl = np.array([locs[i] == locs[j] for i, j in zip(I, J)], float); sw = np.array(is_sw, float)
    X = np.column_stack([cij, cji, d0[I], d0[J], d0[I] - d0[J], detour, np.minimum(ro[I, J], 15), np.minimum(ri[I, J], 15), R - ride, sl, sw[I], sw[J],
                         np.full(len(I), R), np.full(len(I), float(pk))])
    return X, I, J


def wave_XT(w):
    return arc_features_T(w["C"], w["n"], campus_dist(w), w["R"], w["is_sw"], w["locs"], w["direction"] == "pickup")


def toy_landscape(xy, moves):
    nc = len(xy); dm = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
    def canon(t):
        t = list(t); i = t.index(0); t = t[i:] + t[:i]
        if t[1] > t[-1]: t = [t[0]] + t[1:][::-1]
        return tuple(t)
    tours = sorted({canon((0,) + p) for p in itertools.permutations(range(1, nc))}); index = {t: k for k, t in enumerate(tours)}
    cost = np.array([sum(dm[t[i], t[(i + 1) % nc]] for i in range(nc)) for t in tours])
    out = {}
    for mv in moves:
        nb_best = np.empty(len(tours)); nb_arg = np.empty(len(tours), int)
        for k, t in enumerate(tours):
            best, arg = np.inf, -1
            for i in range(nc):
                for j in range(i + 1, nc):
                    s_ = list(t)
                    if mv == "2-opt": s_[i:j + 1] = s_[i:j + 1][::-1]
                    elif mv == "swap": s_[i], s_[j] = s_[j], s_[i]
                    elif mv == "insert":
                        c = s_.pop(i); s_.insert(j, c)
                    c2 = canon(s_); kk = index[c2]
                    if kk != k and cost[kk] < best: best, arg = cost[kk], kk
            nb_best[k], nb_arg[k] = best, arg
        lo_ = nb_best >= cost - 1e-9
        g = int(np.argmin(cost))
        def desc(k):
            while not lo_[k]: k = nb_arg[k]
            return k
        bas = np.array([desc(k) for k in range(len(tours))])
        out[mv] = dict(n_lo=int(lo_.sum()), glob_basin=float(np.mean(bas == g)), lo_mean_exc=float(np.mean(cost[lo_] / cost[g] - 1)))
    return out
