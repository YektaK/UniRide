
"""ESN-SP v2: Exact Sub-Neighbourhood enumeration + Set Partitioning, with an
exact route-union LNS.

UniRide anchored wave: two capacity pools (Sw/So), tour cap T, direction-
specific ride cap R, directed non-metric matrix.
1. Seed pool: for every passenger, all feasible routes inside its g-nearest
   neighbourhood (exact subset DP of wave_exact).
2. Initial solution: lexicographic set partitioning over the seed pool
   (HiGHS; stage 1 min #routes, stage 2 min minutes).
3. Route-union LNS: for each pair / triple of incumbent routes (closest
   first) whose union has <= u_max passengers, enumerate ALL feasible routes
   of the union and solve the local set partitioning exactly; replace the
   routes if the local optimum is lexicographically better. A full pass with
   no improvement, or the time budget, stops the search.
Exact when g >= n. Telemetry counts unions tried / improved.
"""
import time, itertools
import numpy as np
import wave_exact
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import csc_matrix, vstack

def _enum_subset(C, depot, is_sw, nodes, cap_sw, cap_so, R, T, direction):
    nodes = list(nodes); sub = nodes + [depot]
    Cs = np.ascontiguousarray(C[np.ix_(sub, sub)], dtype=np.int32)
    masks, costs, seq_of = wave_exact.enumerate_routes(Cs, len(nodes), [is_sw[v] for v in nodes], cap_sw, cap_so, R, T, direction)
    out = {}
    for k in range(len(masks)):
        m = int(masks[k]); gm = 0; i = 0
        while m:
            if m & 1: gm |= (1 << nodes[i])
            m >>= 1; i += 1
        c = int(costs[k])
        if gm not in out or c < out[gm][0]: out[gm] = (c, k)
    return {gm: (c, [nodes[v] for v in seq_of(k)]) for gm, (c, k) in out.items()}

def _sp(pool, items, time_limit):
    """items: list of passenger indices covered exactly once; pool: {mask: (cost, seq)}"""
    keys = list(pool.keys()); pos = {v: i for i, v in enumerate(items)}
    ri, cj = [], []
    for k, m in enumerate(keys):
        mm = m; i = 0
        while mm:
            if mm & 1: ri.append(pos[i]); cj.append(k)
            mm >>= 1; i += 1
    nc = len(keys); nr = len(items)
    A = csc_matrix((np.ones(len(ri)), (ri, cj)), shape=(nr, nc))
    r1 = milp(np.ones(nc), constraints=LinearConstraint(A, 1, 1), integrality=np.ones(nc), bounds=Bounds(0, 1),
              options={"time_limit": time_limit})
    if r1.x is None: return None, f"s1={r1.status}"
    K = int(round(r1.fun))
    A2 = vstack([A, csc_matrix(np.ones((1, nc)))]).tocsc()
    cst = np.array([pool[m][0] for m in keys], float)
    r2 = milp(cst, constraints=LinearConstraint(A2, np.r_[np.ones(nr), K], np.r_[np.ones(nr), K]),
              integrality=np.ones(nc), bounds=Bounds(0, 1), options={"time_limit": time_limit, "mip_rel_gap": 0})
    x = r2.x if r2.x is not None else r1.x
    return [keys[k] for k in range(nc) if x[k] > 0.5], f"s1={r1.status},s2={r2.status}"

def _members(m):
    out = []; i = 0
    while m:
        if m & 1: out.append(i)
        m >>= 1; i += 1
    return out

def solve_wave(C, is_sw, R, T, direction, cap_sw=4, cap_so=5, g=10, u_max=16, time_budget=60.0, sp_time=60.0):
    n = len(is_sw); depot = n; t0 = time.time()
    tel = dict(pool_seed=0, unions_tried=0, unions_improved=0, passes=0, sp_status=[])
    pool = {}
    sym = C[:n, :n].astype(np.int64) + C[:n, :n].T
    for i in range(n):
        nb = [i] + [int(j) for j in np.argsort(sym[i], kind="stable") if j != i][:max(0, g - 1)]
        for gm, v in _enum_subset(C, depot, is_sw, sorted(nb), cap_sw, cap_so, R, T, direction).items():
            if gm not in pool or v[0] < pool[gm][0]: pool[gm] = v
    tel["pool_seed"] = len(pool)
    chosen, st = _sp(pool, list(range(n)), sp_time); tel["sp_status"].append(st)
    if chosen is None: return None, tel
    sol = {m: pool[m] for m in chosen}
    def key(s): return (len(s), sum(v[0] for v in s.values()))
    tel["initial"] = key(sol)
    tried = set()
    improved = True
    while improved and time.time() - t0 < time_budget:
        improved = False; tel["passes"] += 1
        routes = list(sol.keys())
        def dist(a, b): return float(sym[np.ix_(_members(a), _members(b))].min())
        groups = sorted(itertools.combinations(routes, 2), key=lambda p: dist(*p))
        groups += sorted(itertools.combinations(routes, 3), key=lambda p: dist(p[0], p[1]) + dist(p[1], p[2]) + dist(p[0], p[2]))
        for grp in groups:
            if time.time() - t0 > time_budget: break
            if any(m not in sol for m in grp): continue
            u = 0
            for m in grp: u |= m
            mem = _members(u)
            if len(mem) > u_max or u in tried: continue
            tried.add(u); tel["unions_tried"] += 1
            local = _enum_subset(C, depot, is_sw, mem, cap_sw, cap_so, R, T, direction)
            ch, st = _sp(local, mem, sp_time)
            if ch is None: continue
            new = (len(ch), sum(local[m][0] for m in ch)); old = (len(grp), sum(sol[m][0] for m in grp))
            if new < old:
                for m in grp: del sol[m]
                for m in ch: sol[m] = local[m]
                tel["unions_improved"] += 1; improved = True
    tel["final"] = key(sol); tel["time_s"] = round(time.time() - t0, 3)
    return ([v[1] for v in sol.values()], [v[0] for v in sol.values()]), tel
