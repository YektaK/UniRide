"""ils_fast.py -- ILS on top of fast_ls (Phase 0 / O1+O2).

Kick       : segment-local double-bridge.  Three consecutive segments B,C,D (each 1..Lmax long)
             starting at a random position:  A B C D -> A D C B  (4 edges change, every segment
             keeps its orientation, so the kick is valid for ATSP as well).
LS restart : only the 8 endpoints of the changed edges are put back into the work queue
             (don't-look bits of all other cities stay set).
Acceptance : 'better or equal' with respect to the current tour (else revert).
Telemetry  : kicks, improving kicks, accepted kicks, new-best events, LS move counts.
"""
import time
import numpy as np
from numba import njit

from fast_ls import (FastLS, ls_queue, tour_cost, _push, EPS, NSTATS,
                     ST_2OPT, ST_OR, ST_OR3, ST_REV, ST_EVAL, ST_POPS)

# telemetry indices
T_KICKS, T_IMPROVING, T_ACCEPTED, T_NEWBEST, T_EQUAL = 0, 1, 2, 3, 4
NTEL = 6


def splitmix64(seed):
    z = (int(seed) * 0x9E3779B97F4A7C15 + 0x632BE59BD9B4E019) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    z = z ^ (z >> 31)
    return z if z != 0 else 0x1234567


@njit(cache=True, inline="always")
def _rnd(st, m):
    x = st[0]
    x ^= x >> np.uint64(12)
    x ^= x << np.uint64(25)
    x ^= x >> np.uint64(27)
    st[0] = x
    r = (x * np.uint64(2685821657736338717)) >> np.uint64(11)
    return np.int64(r % np.uint64(m))


@njit(cache=True)
def kick_double_bridge(dm, tour, pos, rng, Lmax, buf, q, inq, qs):
    n = tour.shape[0]
    lmax = min(Lmax, (n - 2) // 3)
    if lmax < 1:
        lmax = 1
    lb = 1 + _rnd(rng, lmax)
    lc = 1 + _rnd(rng, lmax)
    ld = 1 + _rnd(rng, lmax)
    W = lb + lc + ld
    p0 = _rnd(rng, n)
    s = (p0 + 1) % n
    a2 = tour[p0]
    b1 = tour[s]
    b2 = tour[(s + lb - 1) % n]
    c1 = tour[(s + lb) % n]
    c2 = tour[(s + lb + lc - 1) % n]
    d1 = tour[(s + lb + lc) % n]
    d2 = tour[(s + W - 1) % n]
    a1 = tour[(s + W) % n]
    delta = (dm[a2, d1] + dm[d2, c1] + dm[c2, b1] + dm[b2, a1]
             - dm[a2, b1] - dm[b2, c1] - dm[c2, d1] - dm[d2, a1])
    for k in range(W):
        buf[k] = tour[(s + k) % n]
    w = 0
    for k in range(lb + lc, W):          # D
        idx = (s + w) % n
        c = buf[k]
        tour[idx] = c
        pos[c] = idx
        w += 1
    for k in range(lb, lb + lc):         # C
        idx = (s + w) % n
        c = buf[k]
        tour[idx] = c
        pos[c] = idx
        w += 1
    for k in range(0, lb):               # B
        idx = (s + w) % n
        c = buf[k]
        tour[idx] = c
        pos[c] = idx
        w += 1
    _push(q, inq, qs, a2); _push(q, inq, qs, b1); _push(q, inq, qs, b2); _push(q, inq, qs, c1)
    _push(q, inq, qs, c2); _push(q, inq, qs, d1); _push(q, inq, qs, d2); _push(q, inq, qs, a1)
    return delta


@njit(cache=True)
def ils_batch(dm, nbo, nbi, flags, cur, cpos, work, wpos, best, q, inq, qs, buf, rng,
              Lmax, n_kicks, cs, tel, stats):
    """n_kicks ILS iterations.  cs = [current cost, best cost] (updated in place)."""
    big = np.int64(1) << np.int64(62)
    for _ in range(n_kicks):
        dk = kick_double_bridge(dm, work, wpos, rng, Lmax, buf, q, inq, qs)
        dl = ls_queue(dm, nbo, nbi, work, wpos, q, inq, qs, buf, stats, flags, big)
        newc = cs[0] + dk + dl
        tel[T_KICKS] += 1
        if newc < cs[0] - EPS:
            tel[T_IMPROVING] += 1
        if newc <= cs[0] + EPS:
            if newc >= cs[0] - EPS:
                tel[T_EQUAL] += 1
            tel[T_ACCEPTED] += 1
            cur[:] = work
            cpos[:] = wpos
            cs[0] = newc
            if newc < cs[1] - EPS:
                cs[1] = newc
                best[:] = work
                tel[T_NEWBEST] += 1
        else:
            work[:] = cur
            wpos[:] = cpos


class ILSState:
    """One ILS trajectory (used by ils_fast and by px_ils)."""

    def __init__(self, ls, tour, cost, seed, Lmax):
        n = ls.n
        self.ls = ls
        self.cur = np.ascontiguousarray(np.asarray(tour, np.int32).copy())
        self.cpos = np.empty(n, np.int32)
        self.cpos[self.cur] = np.arange(n, dtype=np.int32)
        self.work = self.cur.copy()
        self.wpos = self.cpos.copy()
        self.best = self.cur.copy()
        self.cs = np.array([cost, cost], np.float64)
        self.rng = np.array([splitmix64(seed)], np.uint64)
        self.tel = np.zeros(NTEL, np.int64)
        self.Lmax = int(Lmax)

    def run(self, n_kicks):
        ls = self.ls
        ls._reset_queue()
        ils_batch(ls.dm, ls.nbo, ls.nbi, ls.flags, self.cur, self.cpos, self.work, self.wpos,
                  self.best, ls.q, ls.inq, ls.qs, ls.buf, self.rng, self.Lmax, int(n_kicks),
                  self.cs, self.tel, ls.stats)

    def set_current(self, tour, cost):
        """Replace the current tour (e.g. by a recombination child)."""
        n = self.ls.n
        self.cur[:] = tour
        self.cpos[self.cur] = np.arange(n, dtype=np.int32)
        self.work[:] = self.cur
        self.wpos[:] = self.cpos
        self.cs[0] = cost
        if cost < self.cs[1] - EPS:
            self.cs[1] = cost
            self.best[:] = self.cur


def warmup():
    """Compile all kernels on a tiny symmetric and a tiny asymmetric instance."""
    rs = np.random.RandomState(0)
    xy = rs.rand(30, 2) * 100
    dm = np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5)
    ils_fast(dm, 0.05, 0, max_kicks=50)
    da = dm + np.floor(rs.rand(30, 30) * 10)
    np.fill_diagonal(da, 0)
    ils_fast(da, 0.05, 0, max_kicks=50)


def ils_fast(dm, time_limit, seed, K=10, Lmax=50, use_or3=None, max_kicks=None, init_tour=None,
             target=None):
    """Returns dict(tour, cost, elapsed, kicks, telemetry...).  Timer includes candidate build
    and initial LS.  With max_kicks set, the run is fully deterministic for a given seed."""
    t0 = time.perf_counter()
    dm = np.ascontiguousarray(np.asarray(dm, np.float64))
    n = dm.shape[0]
    ls = FastLS(dm, K=K, use_or3=use_or3)
    if init_tour is None:
        init_tour = np.random.default_rng(seed).permutation(n).astype(np.int32)
    t, c, _ = ls.optimize(init_tour)
    t_init = time.perf_counter() - t0
    st = ILSState(ls, t, c, seed, Lmax)
    batch = 32
    t_best = time.perf_counter() - t0
    while True:
        el = time.perf_counter() - t0
        if max_kicks is None and el >= time_limit:
            break
        if max_kicks is not None and st.tel[T_KICKS] >= max_kicks:
            break
        nk = batch if max_kicks is None else min(batch, max_kicks - st.tel[T_KICKS])
        prev_best = st.cs[1]
        tb = time.perf_counter()
        st.run(nk)
        dt = time.perf_counter() - tb
        if st.cs[1] < prev_best - EPS:
            t_best = time.perf_counter() - t0
        if max_kicks is None:  # aim at ~10 ms per batch
            if dt < 0.005:
                batch = min(batch * 2, 1 << 20)
            elif dt > 0.02 and batch > 1:
                batch = max(1, batch // 2)
        if target is not None and st.cs[1] <= target + EPS:
            break
    best = st.best.copy()
    pre_polish = float(tour_cost(dm, best))
    best, _, _ = ls.optimize(best)          # final verification sweep / polish
    elapsed = time.perf_counter() - t0
    recomputed = tour_cost(dm, best)
    tel = st.tel
    kicks = int(tel[T_KICKS])
    return dict(tour=best, cost=float(recomputed), cost_incremental=float(st.cs[1]),
                cost_pre_polish=pre_polish,
                elapsed=elapsed, t_init=t_init, t_best=t_best, kicks=kicks,
                kicks_per_s=kicks / max(elapsed - t_init, 1e-9),
                improving_kicks=int(tel[T_IMPROVING]), accepted_kicks=int(tel[T_ACCEPTED]),
                equal_accepted=int(tel[T_EQUAL]), new_best=int(tel[T_NEWBEST]),
                improving_rate=int(tel[T_IMPROVING]) / max(kicks, 1),
                accept_rate=int(tel[T_ACCEPTED]) / max(kicks, 1),
                ls_2opt=int(ls.stats[ST_2OPT]), ls_or=int(ls.stats[ST_OR]),
                ls_or3=int(ls.stats[ST_OR3]), reversals=int(ls.stats[ST_REV]),
                evals=int(ls.stats[ST_EVAL]), directed=bool(ls.directed), init_cost=float(c))
