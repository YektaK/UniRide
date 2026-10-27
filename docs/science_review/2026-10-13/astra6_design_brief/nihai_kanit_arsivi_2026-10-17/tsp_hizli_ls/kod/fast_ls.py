"""fast_ls.py -- Numba fast local search for TSP / ATSP (UniRide academic pipeline, Phase 0.1).

Representation : array tour[pos] + position index pos[city]  (int32).
Candidates     : K nearest neighbours.  Symmetric: one list.  Directed: out-list (i->j cheap)
                 and in-list (j->i cheap).
Work queue     : FIFO of 'active' cities (don't-look bits = not in queue).
Moves (exact integer-valued deltas, first improvement, partial-gain pruning):
  symmetric : 2-opt (shorter side reversed) + Or-opt (segment 1..3, both orientations)
              [+ optional or-3opt segment exchange]
  directed  : Or-opt (segment 1..3, orientation kept) + or-3opt segment exchange
              (A B C -> A C B, orientation kept).  No reversal is ever applied
              (stats[ST_REV] counts reversals; contract tests assert it stays 0).
Symmetric vs directed is detected from the matrix (np.array_equal(dm, dm.T)).
"""
import os
import numpy as np
from numba import njit

EPS = 1e-7
# stats indices
ST_2OPT, ST_OR, ST_OR3, ST_REV, ST_EVAL, ST_SWAPCOST, ST_POPS, ST_SWEEP = 0, 1, 2, 3, 4, 5, 6, 7
NSTATS = 8


# ----------------------------------------------------------------------------- helpers
@njit(cache=True, inline="always")
def _succ(tour, pos, n, c):
    p = pos[c] + 1
    if p == n:
        p = 0
    return tour[p]


@njit(cache=True, inline="always")
def _pred(tour, pos, n, c):
    p = pos[c] - 1
    if p < 0:
        p = n - 1
    return tour[p]


@njit(cache=True, inline="always")
def _rel(pos, n, x, a):
    """Steps from a forward to x  (0..n-1)."""
    r = pos[x] - pos[a]
    if r < 0:
        r += n
    return r


@njit(cache=True, inline="always")
def _push(q, inq, qs, c):
    # qs = [head, tail, count, cap]
    if inq[c] == 0:
        inq[c] = 1
        q[qs[1]] = c
        qs[1] += 1
        if qs[1] == qs[3]:
            qs[1] = 0
        qs[2] += 1


@njit(cache=True)
def _reverse(tour, pos, n, i, j, stats):
    """Reverse cyclic positions i..j (forward, inclusive); reverses the shorter side."""
    L = j - i
    if L < 0:
        L += n
    L += 1
    if 2 * L > n:
        ni = j + 1
        if ni == n:
            ni = 0
        nj = i - 1
        if nj < 0:
            nj = n - 1
        i = ni
        j = nj
        L = n - L
    stats[ST_REV] += 1
    for _ in range(L // 2):
        a = tour[i]
        b = tour[j]
        tour[i] = b
        pos[b] = i
        tour[j] = a
        pos[a] = j
        i += 1
        if i == n:
            i = 0
        j -= 1
        if j < 0:
            j = n - 1


@njit(cache=True)
def _swap_raw(tour, pos, n, s, la, lb, buf):
    """Adjacent blocks A=[s, s+la) and B=[s+la, s+la+lb) (cyclic) -> B A starting at s."""
    if la <= lb:
        for k in range(la):
            buf[k] = tour[(s + k) % n]
        for k in range(lb):
            idx = (s + k) % n
            c = tour[(s + la + k) % n]
            tour[idx] = c
            pos[c] = idx
        for k in range(la):
            idx = (s + lb + k) % n
            c = buf[k]
            tour[idx] = c
            pos[c] = idx
    else:
        for k in range(lb):
            buf[k] = tour[(s + la + k) % n]
        for k in range(la - 1, -1, -1):
            dst = (s + lb + k) % n
            c = tour[(s + k) % n]
            tour[dst] = c
            pos[c] = dst
        for k in range(lb):
            idx = (s + k) % n
            c = buf[k]
            tour[idx] = c
            pos[c] = idx


@njit(cache=True)
def _seg_exchange(tour, pos, n, x1, x2, x3, buf, stats):
    """Orientation-preserving 3-change.  Cyclic order x1 < x2 < x3.
    Removes (x1,y1),(x2,y2),(x3,y3); adds (x1,y2),(x3,y1),(x2,y3): x1 [y2..x3] [y1..x2] y3.
    Implemented as an adjacent block swap; the cheapest of the three equivalent swaps is used."""
    l1 = _rel(pos, n, x2, x1)          # block X = y1..x2
    l2 = _rel(pos, n, x3, x2)          # block Y = y2..x3
    l3 = n - l1 - l2                   # block Z = y3..x1
    s = pos[x1] + 1
    if s == n:
        s = 0
    if l1 + l2 <= l2 + l3 and l1 + l2 <= l3 + l1:
        _swap_raw(tour, pos, n, s, l1, l2, buf)
        stats[ST_SWAPCOST] += l1 + l2
    elif l2 + l3 <= l3 + l1:
        _swap_raw(tour, pos, n, (s + l1) % n, l2, l3, buf)
        stats[ST_SWAPCOST] += l2 + l3
    else:
        _swap_raw(tour, pos, n, (s + l1 + l2) % n, l3, l1, buf)
        stats[ST_SWAPCOST] += l3 + l1


# ----------------------------------------------------------------------------- moves
@njit(cache=True)
def _try_2opt(a, dm, nb, K, tour, pos, n, q, inq, qs, buf, stats, apply):
    for dirn in range(2):
        if dirn == 0:
            b = _succ(tour, pos, n, a)
        else:
            b = _pred(tour, pos, n, a)
        d_ab = dm[a, b]
        for k in range(K):
            c = nb[a, k]
            d_ac = dm[a, c]
            if d_ab - d_ac <= EPS:
                break
            if dirn == 0:
                d = _succ(tour, pos, n, c)
            else:
                d = _pred(tour, pos, n, c)
            if c == b or d == a:
                continue
            stats[ST_EVAL] += 1
            delta = d_ac + dm[b, d] - d_ab - dm[c, d]
            if delta < -EPS:
                if apply:
                    if dirn == 0:
                        _reverse(tour, pos, n, pos[b], pos[c], stats)
                    else:
                        _reverse(tour, pos, n, pos[a], pos[d], stats)
                    _push(q, inq, qs, a); _push(q, inq, qs, b)
                    _push(q, inq, qs, c); _push(q, inq, qs, d)
                    stats[ST_2OPT] += 1
                return delta
    return 0.0


@njit(cache=True)
def _apply_or(tour, pos, n, s1, s2, L, c, rev, buf, stats):
    """Move segment s1..s2 (forward, length L) between c and succ(c); reversed if rev."""
    p = _pred(tour, pos, n, s1)
    _seg_exchange(tour, pos, n, p, s2, c, buf, stats)
    if rev and L > 1:
        _reverse(tour, pos, n, pos[s1], pos[s2], stats)


@njit(cache=True)
def _try_or_sym(a, dm, nb, K, tour, pos, n, q, inq, qs, buf, stats, apply):
    for L in range(1, 4):
        if n < L + 4:
            break
        for end in range(2):
            if end == 0:
                s1 = a
                s2 = a
                for _ in range(L - 1):
                    s2 = _succ(tour, pos, n, s2)
            else:
                s2 = a
                s1 = a
                for _ in range(L - 1):
                    s1 = _pred(tour, pos, n, s1)
            if L == 1 and end == 1:
                continue
            p = _pred(tour, pos, n, s1)
            qn = _succ(tour, pos, n, s2)
            g = dm[p, s1] + dm[s2, qn] - dm[p, qn]
            if g <= EPS:
                continue
            for side in range(2):
                sx = s1 if side == 0 else s2
                so = s2 if side == 0 else s1
                for k in range(K):
                    x = nb[sx, k]
                    dx = dm[sx, x]
                    if dx >= g - EPS:
                        break
                    if _rel(pos, n, x, s1) < L:
                        continue
                    # (i) x [sx .. so] succ(x)
                    if x != p:
                        y = _succ(tour, pos, n, x)
                        stats[ST_EVAL] += 1
                        delta = -g + dx + dm[so, y] - dm[x, y]
                        if delta < -EPS:
                            if apply:
                                # orientation after x: sx..so ; side 0 -> s1..s2 (no rev)
                                _apply_or(tour, pos, n, s1, s2, L, x, side == 1, buf, stats)
                                _push(q, inq, qs, p); _push(q, inq, qs, qn); _push(q, inq, qs, s1)
                                _push(q, inq, qs, s2); _push(q, inq, qs, x); _push(q, inq, qs, y)
                                stats[ST_OR] += 1
                            return delta
                    # (ii) pred(x) [so .. sx] x
                    if x != qn:
                        w = _pred(tour, pos, n, x)
                        stats[ST_EVAL] += 1
                        delta = -g + dx + dm[w, so] - dm[w, x]
                        if delta < -EPS:
                            if apply:
                                # orientation after w: so..sx ; side 0 -> s2..s1 (rev)
                                _apply_or(tour, pos, n, s1, s2, L, w, side == 0, buf, stats)
                                _push(q, inq, qs, p); _push(q, inq, qs, qn); _push(q, inq, qs, s1)
                                _push(q, inq, qs, s2); _push(q, inq, qs, x); _push(q, inq, qs, w)
                                stats[ST_OR] += 1
                            return delta
    return 0.0


@njit(cache=True)
def _try_or_dir(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, apply):
    """Directed Or-opt: segment 1..3 containing a at one end, orientation kept."""
    for L in range(1, 4):
        if n < L + 4:
            break
        for end in range(2):
            if L == 1 and end == 1:
                continue
            if end == 0:
                s1 = a
                s2 = a
                for _ in range(L - 1):
                    s2 = _succ(tour, pos, n, s2)
            else:
                s2 = a
                s1 = a
                for _ in range(L - 1):
                    s1 = _pred(tour, pos, n, s1)
            p = _pred(tour, pos, n, s1)
            qn = _succ(tour, pos, n, s2)
            g = dm[p, s1] + dm[s2, qn] - dm[p, qn]
            if g <= EPS:
                continue
            # x -> s1 cheap (in-list of s1)
            for k in range(K):
                x = nbi[s1, k]
                dx = dm[x, s1]
                if dx >= g - EPS:
                    break
                if x == p or _rel(pos, n, x, s1) < L:
                    continue
                y = _succ(tour, pos, n, x)
                stats[ST_EVAL] += 1
                delta = -g + dx + dm[s2, y] - dm[x, y]
                if delta < -EPS:
                    if apply:
                        _apply_or(tour, pos, n, s1, s2, L, x, False, buf, stats)
                        _push(q, inq, qs, p); _push(q, inq, qs, qn); _push(q, inq, qs, s1)
                        _push(q, inq, qs, s2); _push(q, inq, qs, x); _push(q, inq, qs, y)
                        stats[ST_OR] += 1
                    return delta
            # s2 -> y cheap (out-list of s2)
            for k in range(K):
                y = nbo[s2, k]
                dy = dm[s2, y]
                if dy >= g - EPS:
                    break
                if y == qn or _rel(pos, n, y, s1) < L:
                    continue
                x = _pred(tour, pos, n, y)
                stats[ST_EVAL] += 1
                delta = -g + dm[x, s1] + dy - dm[x, y]
                if delta < -EPS:
                    if apply:
                        _apply_or(tour, pos, n, s1, s2, L, x, False, buf, stats)
                        _push(q, inq, qs, p); _push(q, inq, qs, qn); _push(q, inq, qs, s1)
                        _push(q, inq, qs, s2); _push(q, inq, qs, x); _push(q, inq, qs, y)
                        stats[ST_OR] += 1
                    return delta
    return 0.0


@njit(cache=True)
def _try_or3(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, apply):
    """Orientation-preserving segment exchange (or-3opt) with neighbour lists.
    Removed (x1,y1),(x2,y2),(x3,y3) ; added (x1,y2),(x3,y1),(x2,y3)."""
    if n < 6:
        return 0.0
    # forward: x1 = a
    x1 = a
    y1 = _succ(tour, pos, n, a)
    d11 = dm[x1, y1]
    for k in range(K):
        y2 = nbo[x1, k]
        g1 = d11 - dm[x1, y2]
        if g1 <= EPS:
            break
        if y2 == y1:
            continue
        x2 = _pred(tour, pos, n, y2)
        G = g1 + dm[x2, y2]
        r2 = _rel(pos, n, x2, x1)
        for k2 in range(K):
            x3 = nbi[y1, k2]
            g2 = G - dm[x3, y1]
            if g2 <= EPS:
                break
            if _rel(pos, n, x3, x1) <= r2:
                continue
            y3 = _succ(tour, pos, n, x3)
            stats[ST_EVAL] += 1
            delta = dm[x2, y3] - dm[x3, y3] - g2
            if delta < -EPS:
                if apply:
                    _seg_exchange(tour, pos, n, x1, x2, x3, buf, stats)
                    _push(q, inq, qs, x1); _push(q, inq, qs, y1); _push(q, inq, qs, x2)
                    _push(q, inq, qs, y2); _push(q, inq, qs, x3); _push(q, inq, qs, y3)
                    stats[ST_OR3] += 1
                return delta
    # backward (mirror): y3 = a
    y3 = a
    x3 = _pred(tour, pos, n, a)
    d33 = dm[x3, y3]
    for k in range(K):
        x2 = nbi[y3, k]
        g1 = d33 - dm[x2, y3]
        if g1 <= EPS:
            break
        if x2 == x3:
            continue
        y2 = _succ(tour, pos, n, x2)
        G = g1 + dm[x2, y2]
        r2 = _rel(pos, n, x2, y3)
        for k2 in range(K):
            x1 = nbi[y2, k2]
            g2 = G - dm[x1, y2]
            if g2 <= EPS:
                break
            if x1 == x2 or _rel(pos, n, x1, y3) >= r2:
                continue
            y1 = _succ(tour, pos, n, x1)
            stats[ST_EVAL] += 1
            delta = dm[x3, y1] - dm[x1, y1] - g2
            if delta < -EPS:
                if apply:
                    _seg_exchange(tour, pos, n, x1, x2, x3, buf, stats)
                    _push(q, inq, qs, x1); _push(q, inq, qs, y1); _push(q, inq, qs, x2)
                    _push(q, inq, qs, y2); _push(q, inq, qs, x3); _push(q, inq, qs, y3)
                    stats[ST_OR3] += 1
                return delta
    return 0.0


@njit(cache=True)
def _try_node(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, flags, apply):
    # flags = [directed, use_2opt, use_or, use_or3]
    if flags[0] == 0:
        if flags[1]:
            d = _try_2opt(a, dm, nbo, K, tour, pos, n, q, inq, qs, buf, stats, apply)
            if d < 0.0:
                return d
        if flags[2]:
            d = _try_or_sym(a, dm, nbo, K, tour, pos, n, q, inq, qs, buf, stats, apply)
            if d < 0.0:
                return d
    else:
        if flags[2]:
            d = _try_or_dir(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, apply)
            if d < 0.0:
                return d
    if flags[3]:
        d = _try_or3(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, apply)
        if d < 0.0:
            return d
    return 0.0


@njit(cache=True)
def ls_queue(dm, nbo, nbi, tour, pos, q, inq, qs, buf, stats, flags, max_moves):
    """Run LS until the active queue is empty (or max_moves).  Returns total delta (<=0)."""
    n = tour.shape[0]
    K = nbo.shape[1]
    total = 0.0
    moves = 0
    while qs[2] > 0 and moves < max_moves:
        a = q[qs[0]]
        qs[0] += 1
        if qs[0] == qs[3]:
            qs[0] = 0
        qs[2] -= 1
        inq[a] = 0
        stats[ST_POPS] += 1
        while moves < max_moves:
            d = _try_node(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, flags, True)
            if d < 0.0:
                total += d
                moves += 1
            else:
                break
    return total


@njit(cache=True)
def count_improving(dm, nbo, nbi, tour, pos, flags):
    """Dry-run full scan: number of cities at which some candidate move improves."""
    n = tour.shape[0]
    K = nbo.shape[1]
    q = np.zeros(n + 1, np.int32)
    inq = np.ones(n, np.uint8)  # 'already queued' -> pushes are no-ops
    qs = np.array([0, 0, 0, n + 1], np.int64)
    buf = np.zeros(n, np.int32)
    stats = np.zeros(NSTATS, np.int64)
    cnt = 0
    for a in range(n):
        if _try_node(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, flags, False) < 0.0:
            cnt += 1
    return cnt


@njit(cache=True)
def ls_full(dm, nbo, nbi, tour, pos, q, inq, qs, buf, stats, flags, max_moves):
    """Queue LS followed by verification sweeps: every city whose candidate neighbourhood still
    contains an improving move is re-activated, until a sweep finds none.  The result is a
    local optimum w.r.t. the full candidate neighbourhood (DLB alone does not guarantee it)."""
    n = tour.shape[0]
    K = nbo.shape[1]
    total = ls_queue(dm, nbo, nbi, tour, pos, q, inq, qs, buf, stats, flags, max_moves)
    while True:
        found = 0
        for a in range(n):
            if _try_node(a, dm, nbo, nbi, K, tour, pos, n, q, inq, qs, buf, stats, flags, False) < 0.0:
                _push(q, inq, qs, a)
                found += 1
        stats[ST_SWEEP] += 1
        if found == 0:
            break
        total += ls_queue(dm, nbo, nbi, tour, pos, q, inq, qs, buf, stats, flags, max_moves)
    return total


@njit(cache=True)
def tour_cost(dm, tour):
    n = tour.shape[0]
    s = 0.0
    for i in range(n - 1):
        s += dm[tour[i], tour[i + 1]]
    s += dm[tour[n - 1], tour[0]]
    return s


# ----------------------------------------------------------------------------- python API
def is_symmetric(dm):
    return bool(np.array_equal(dm, dm.T))


def build_candidates(dm, K=10):
    n = dm.shape[0]
    K = int(min(K, n - 1))
    D = np.array(dm, dtype=np.float64, copy=True)
    np.fill_diagonal(D, np.inf)
    nbo = np.ascontiguousarray(np.argsort(D, axis=1, kind="stable")[:, :K].astype(np.int32))
    nbi = np.ascontiguousarray(np.argsort(D.T, axis=1, kind="stable")[:, :K].astype(np.int32))
    return nbo, nbi


class FastLS:
    """Reusable LS engine bound to one distance matrix."""

    def __init__(self, dm, K=10, use_2opt=True, use_or=True, use_or3=None, directed=None):
        self.dm = np.ascontiguousarray(np.asarray(dm, dtype=np.float64))
        self.n = n = self.dm.shape[0]
        self.directed = (not is_symmetric(self.dm)) if directed is None else bool(directed)
        if use_or3 is None:
            use_or3 = self.directed
        self.flags = np.array([int(self.directed), int(use_2opt and not self.directed),
                               int(use_or), int(use_or3)], np.int64)
        self.K = K
        self.nbo, self.nbi = build_candidates(self.dm, K)
        self.q = np.zeros(n + 1, np.int32)
        self.inq = np.zeros(n, np.uint8)
        self.qs = np.array([0, 0, 0, n + 1], np.int64)
        self.buf = np.zeros(n, np.int32)
        self.stats = np.zeros(NSTATS, np.int64)

    def _reset_queue(self):
        self.inq[:] = 0
        self.qs[:3] = 0

    def optimize(self, tour, max_moves=1 << 60, order=None, sweep=True):
        """Full LS from a tour (all cities active).  Returns (tour, cost, pos).
        sweep=True adds verification sweeps (guaranteed candidate-neighbourhood local optimum)."""
        n = self.n
        t = np.ascontiguousarray(np.asarray(tour, dtype=np.int32).copy())
        p = np.empty(n, np.int32)
        p[t] = np.arange(n, dtype=np.int32)
        self._reset_queue()
        seq = t if order is None else np.asarray(order, np.int32)
        for c in seq:
            _push_py(self.q, self.inq, self.qs, int(c))
        c0 = tour_cost(self.dm, t)
        fn = ls_full if sweep else ls_queue
        d = fn(self.dm, self.nbo, self.nbi, t, p, self.q, self.inq, self.qs, self.buf,
               self.stats, self.flags, max_moves)
        return t, c0 + d, p

    def n_improving(self, tour):
        t = np.ascontiguousarray(np.asarray(tour, dtype=np.int32))
        p = np.empty(self.n, np.int32)
        p[t] = np.arange(self.n, dtype=np.int32)
        return int(count_improving(self.dm, self.nbo, self.nbi, t, p, self.flags))


def _push_py(q, inq, qs, c):
    if inq[c] == 0:
        inq[c] = 1
        q[qs[1]] = c
        qs[1] += 1
        if qs[1] == qs[3]:
            qs[1] = 0
        qs[2] += 1
