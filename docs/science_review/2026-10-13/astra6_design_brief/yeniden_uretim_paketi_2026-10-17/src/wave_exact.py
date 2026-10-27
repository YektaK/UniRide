
"""Exact wave solver for UniRide anchored waves (pickup / dropoff).

Route enumeration by subset dynamic programming + set partitioning (CP-SAT).
Pickup route D -> v1 .. vk -> D: the longest ride is v1's, i.e. the path
length v1 -> ... -> D.  We build routes backwards from the depot: state
(S, f) = shortest path that starts at f, visits all of S and ends at D.
Every suffix of a feasible pickup route is itself a feasible state (its
rides are unchanged), so pruning states whose value exceeds R is exact even
on non-metric matrices.  Drop-off is the same problem on the transposed
matrix with the visiting order reversed.  The tour cap T is checked only on
complete routes (c(D, f) + value), never used for pruning.
"""
import numpy as np
from numba import njit

BIG = np.int32(1 << 29)

@njit(cache=True)
def _subset_dp(C, depot, swmask, cap_sw, cap_so, R):
    n = C.shape[0] - 1
    M = 1 << n
    val = np.full((M, n), BIG, dtype=np.int32)
    nxt = np.full((M, n), -1, dtype=np.int8)
    nsw = np.zeros(M, dtype=np.int8)
    nso = np.zeros(M, dtype=np.int8)
    for m in range(1, M):
        low = m & (-m)
        b = 0
        while (1 << b) != low:
            b += 1
        prev = m ^ low
        if (swmask >> b) & 1:
            nsw[m] = nsw[prev] + 1; nso[m] = nso[prev]
        else:
            nsw[m] = nsw[prev]; nso[m] = nso[prev] + 1
    for i in range(n):
        m = 1 << i
        if nsw[m] <= cap_sw and nso[m] <= cap_so and C[i, depot] <= R:
            val[m, i] = C[i, depot]
    for m in range(1, M):
        for f in range(n):
            v = val[m, f]
            if v >= BIG:
                continue
            for u in range(n):
                if (m >> u) & 1:
                    continue
                m2 = m | (1 << u)
                if nsw[m2] > cap_sw or nso[m2] > cap_so:
                    continue
                w = C[u, f] + v
                if w <= R and w < val[m2, u]:
                    val[m2, u] = w
                    nxt[m2, u] = f
    return val, nxt

@njit(cache=True)
def _columns(val, C, depot, T):
    M, n = val.shape
    cnt = 0
    for m in range(1, M):
        best = BIG
        for f in range(n):
            if val[m, f] < BIG:
                t = C[depot, f] + val[m, f]
                if t < best:
                    best = t
        if best <= T:
            cnt += 1
    masks = np.empty(cnt, dtype=np.int64)
    costs = np.empty(cnt, dtype=np.int32)
    firsts = np.empty(cnt, dtype=np.int8)
    k = 0
    for m in range(1, M):
        best = BIG; bf = -1
        for f in range(n):
            if val[m, f] < BIG:
                t = C[depot, f] + val[m, f]
                if t < best:
                    best = t; bf = f
        if best <= T:
            masks[k] = m; costs[k] = best; firsts[k] = bf; k += 1
    return masks, costs, firsts

def _sequence(nxt, mask, first):
    seq = [int(first)]; m = int(mask); f = int(first)
    while bin(m).count("1") > 1:
        g = int(nxt[m, f]); m ^= (1 << f); f = g; seq.append(f)
    return seq

def enumerate_routes(C, depot, is_sw, cap_sw, cap_so, R, T, direction):
    """C: (n+1)x(n+1) int matrix over occurrences, depot index = n.
    Returns masks, costs, sequences-builder."""
    Cw = np.ascontiguousarray(C.T if direction == "dropoff" else C, dtype=np.int32)
    swmask = 0
    for i, s in enumerate(is_sw):
        if s: swmask |= (1 << i)
    val, nxt = _subset_dp(Cw, depot, swmask, cap_sw, cap_so, R)
    masks, costs, firsts = _columns(val, Cw, depot, T)
    def seq_of(k):
        s = _sequence(nxt, masks[k], firsts[k])
        return s[::-1] if direction == "dropoff" else s
    return masks, costs, seq_of

def solve_partition(masks, costs, n, weight=10000, time_limit=120.0, workers=4, extra_lb=None):
    from ortools.sat.python import cp_model
    md = cp_model.CpModel()
    x = [md.NewBoolVar("") for _ in range(len(masks))]
    rows = [[] for _ in range(n)]
    for k, m in enumerate(masks):
        mm = int(m); i = 0
        while mm:
            if mm & 1: rows[i].append(x[k])
            mm >>= 1; i += 1
    for i in range(n):
        md.AddExactlyOne(rows[i])
    md.Minimize(sum((weight + int(c)) * x[k] for k, c in enumerate(costs)))
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_workers = workers
    st = s.Solve(md)
    chosen = [k for k in range(len(masks)) if s.Value(x[k])] if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else []
    return s.StatusName(st), chosen, s.ObjectiveValue() if chosen else None, s.BestObjectiveBound()
