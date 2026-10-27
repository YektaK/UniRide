
"""ESN-SP v3 = v2 + (a) location-aware neighbourhoods (occurrences at the
same stop count as one neighbour) and (b) route merging: the final routes of
k GA-Split runs (repo engine, default configuration) are added to the column
pool before set partitioning. With an optimally solved SP the result is never
lexicographically worse than the best merged GA run."""
import time, itertools
import numpy as np
import esn_sp as v2

def solve_wave_v3(C, is_sw, R, T, direction, loc_ids, ga_routes_list, cap_sw=4, cap_so=5, g=10, u_max=18,
                  time_budget=120.0, sp_time=60.0):
    n = len(is_sw); depot = n; t0 = time.time()
    tel = dict(pool_seed=0, ga_columns=0, unions_tried=0, unions_improved=0, passes=0, sp_status=[])
    pool = {}
    def put(gm, c, seq):
        if gm not in pool or c < pool[gm][0]: pool[gm] = (c, seq)
    locs = sorted(set(loc_ids)); occ_of = {l: [i for i in range(n) if loc_ids[i] == l] for l in locs}
    rep = {l: occ_of[l][0] for l in locs}
    for l in locs:
        order = sorted(locs, key=lambda m: (C[rep[l], rep[m]] + C[rep[m], rep[l]], m))
        nb = []
        for m in order:
            if len(nb) + len(occ_of[m]) > g: continue
            nb += occ_of[m]
            if len(nb) >= g: break
        for gm, v in v2._enum_subset(C, depot, is_sw, sorted(nb), cap_sw, cap_so, R, T, direction).items(): put(gm, *v)
    tel["pool_seed"] = len(pool)
    for routes in ga_routes_list:
        for r in routes:
            gm = 0
            for v in r: gm |= (1 << v)
            d = int(C[n, r[0]] + sum(C[a, b] for a, b in zip(r, r[1:])) + C[r[-1], n])
            put(gm, d, list(r)); tel["ga_columns"] += 1
    key = lambda s: (len(s), sum(v[0] for v in s.values()))
    inc = None
    for routes in ga_routes_list:          # best merged GA run = incumbent (feasible by certificate upstream)
        cand = {}
        for r in routes:
            gm = 0
            for v in r: gm |= (1 << v)
            cand[gm] = pool[gm]
        if inc is None or key(cand) < key(inc): inc = cand
    chosen, st = v2._sp(pool, list(range(n)), sp_time); tel["sp_status"].append(st)
    sol = {m: pool[m] for m in chosen} if chosen is not None else None
    tel["sp_initial"] = key(sol) if sol else None; tel["ga_incumbent"] = key(inc) if inc else None
    if sol is None or (inc is not None and key(inc) < key(sol)): sol = dict(inc)
    tel["initial"] = key(sol); tried = set(); improved = True
    sym = C[:n, :n].astype(np.int64) + C[:n, :n].T
    while improved and time.time() - t0 < time_budget:
        improved = False; tel["passes"] += 1
        routes = list(sol.keys())
        dist = lambda a, b: float(sym[np.ix_(v2._members(a), v2._members(b))].min())
        groups = sorted(itertools.combinations(routes, 2), key=lambda p: dist(*p))
        groups += sorted(itertools.combinations(routes, 3), key=lambda p: dist(p[0], p[1]) + dist(p[1], p[2]) + dist(p[0], p[2]))
        for grp in groups:
            if time.time() - t0 > time_budget: break
            if any(m not in sol for m in grp): continue
            u = 0
            for m in grp: u |= m
            mem = v2._members(u)
            if len(mem) > u_max or u in tried: continue
            tried.add(u); tel["unions_tried"] += 1
            local = v2._enum_subset(C, depot, is_sw, mem, cap_sw, cap_so, R, T, direction)
            ch, st = v2._sp(local, mem, sp_time)
            if ch is None: continue
            new = (len(ch), sum(local[m][0] for m in ch)); old = (len(grp), sum(sol[m][0] for m in grp))
            if new < old:
                for m in grp: del sol[m]
                for m in ch: sol[m] = local[m]
                tel["unions_improved"] += 1; improved = True
    tel["final"] = key(sol); tel["time_s"] = round(time.time() - t0, 3)
    return ([v[1] for v in sol.values()], [v[0] for v in sol.values()]), tel
