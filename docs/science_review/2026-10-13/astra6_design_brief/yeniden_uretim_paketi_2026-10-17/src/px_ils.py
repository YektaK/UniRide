"""px_ils.py -- PX-ILS prototype: simple GPX (symmetric) + small elite pool of ILS-fast trajectories.

GPX (Whitley et al. 2009, simple variant):
  * union graph of parents A, B; shared edges removed -> 'difference graph';
  * connected components of the difference graph (union-find);
  * shared paths through vertices outside all components are contracted to surrogate edges;
  * a component is FEASIBLE iff exactly 2 surrogate/shared edges cross its boundary; then both parents
    traverse it as one Hamiltonian path between the same two portals, so the parent with the
    shorter inside path can be chosen independently per component;
  * all other components (and all shared edges) are taken from the better parent (base).
  => child cost = cost(base) - sum of per-component gains  <=  min(cost A, cost B);
     every shared edge is kept.  The child is re-checked (Hamiltonian cycle, else base).
PX-ILS:
  m trajectories (ILSState) run ILS-fast epochs; after each epoch every trajectory i is
  recombined with a random partner j; the child gets a queue-LS from the portal cities and
  replaces the worse parent if it is strictly better than it and is not a clone of the better
  parent.  use_gpx=False gives the equal-time control (m independent ILS-fast trajectories).
"""
import time
import numpy as np
from numba import njit

from fast_ls import FastLS, ls_queue, tour_cost, _push_py, EPS
from ils_fast import ILSState, T_KICKS, T_IMPROVING, T_ACCEPTED


@njit(cache=True)
def _find(par, x):
    while par[x] != x:
        par[x] = par[par[x]]
        x = par[x]
    return x


@njit(cache=True)
def gpx_core(dm, ta, tb, child, touch, out):
    """out = [n_comp, n_feasible, n_switched, gain, child_cost, base_is_A, ok]"""
    n = ta.shape[0]
    sa = np.empty(n, np.int32); pa = np.empty(n, np.int32)
    sb = np.empty(n, np.int32); pb = np.empty(n, np.int32)
    for i in range(n):
        a = ta[i]; sa[a] = ta[(i + 1) % n]; pa[a] = ta[i - 1]
        b = tb[i]; sb[b] = tb[(i + 1) % n]; pb[b] = tb[i - 1]
    par = np.arange(n).astype(np.int32)
    indiff = np.zeros(n, np.uint8)
    for u in range(n):
        v = sa[u]
        if not (v == sb[u] or v == pb[u]):
            ru = _find(par, u); rv = _find(par, v)
            if ru != rv:
                par[ru] = rv
            indiff[u] = 1; indiff[v] = 1
        v = sb[u]
        if not (v == sa[u] or v == pa[u]):
            ru = _find(par, u); rv = _find(par, v)
            if ru != rv:
                par[ru] = rv
            indiff[u] = 1; indiff[v] = 1
    comp = np.full(n, -1, np.int32)
    rid = np.full(n, -1, np.int32)
    ncomp = 0
    for u in range(n):
        if indiff[u]:
            r = _find(par, u)
            if rid[r] < 0:
                rid[r] = ncomp
                ncomp += 1
            comp[u] = rid[r]
    cross = np.zeros(max(ncomp, 1), np.int64)
    ca = np.zeros(max(ncomp, 1)); cb = np.zeros(max(ncomp, 1))
    costA = 0.0; costB = 0.0
    for u in range(n):
        v = sa[u]
        costA += dm[u, v]
        if not (v == sb[u] or v == pb[u]):
            ca[comp[u]] += dm[u, v]
        v = sb[u]
        costB += dm[u, v]
        if not (v == sa[u] or v == pa[u]):
            cb[comp[u]] += dm[u, v]
    # boundary crossings on the contracted graph: a maximal path of shared edges through
    # vertices outside every component is a 'surrogate edge' (u ... w); it crosses the boundary
    # of comp[u] iff comp[w] != comp[u].  Counted from each end for that end's component.
    far = np.full(2 * n, -1, np.int32)   # far[2u+k]: component-vertex reached from u via its k-th A edge
    for u in range(n):
        if comp[u] < 0:
            continue
        for k in range(2):
            v = sa[u] if k == 0 else pa[u]
            if not (v == sb[u] or v == pb[u]):
                continue                    # A-only edge: internal to comp[u]
            prev = u; cur = v; steps = 0
            while comp[cur] < 0 and steps <= n:
                nx = sa[cur] if pa[cur] == prev else pa[cur]
                prev = cur; cur = nx; steps += 1
            far[2 * u + k] = cur
            if comp[cur] != comp[u]:
                cross[comp[u]] += 1
    base_is_A = costA <= costB
    src_other = np.zeros(max(ncomp, 1), np.uint8)
    nfeas = 0; nsw = 0; gain = 0.0
    for c in range(ncomp):
        if cross[c] == 2:
            nfeas += 1
            if base_is_A:
                if cb[c] < ca[c] - EPS:
                    src_other[c] = 1; nsw += 1; gain += ca[c] - cb[c]
            else:
                if ca[c] < cb[c] - EPS:
                    src_other[c] = 1; nsw += 1; gain += cb[c] - ca[c]
    base_cost = costA if base_is_A else costB
    out[0] = ncomp; out[1] = nfeas; out[2] = nsw; out[3] = gain; out[5] = 1.0 if base_is_A else 0.0
    touch[:] = 0
    if nsw == 0:
        if base_is_A:
            child[:] = ta
        else:
            child[:] = tb
        out[4] = base_cost; out[6] = 1.0
        return
    # portals of switched components
    for u in range(n):
        if comp[u] < 0 or not src_other[comp[u]]:
            continue
        for k in range(2):
            w = far[2 * u + k]
            if w >= 0 and comp[w] != comp[u]:
                touch[u] = 1
                touch[sa[u] if k == 0 else pa[u]] = 1
                touch[w] = 1
    visited = np.zeros(n, np.uint8)
    prev = -1; cur = 0; ok = True
    for k in range(n):
        if visited[cur]:
            ok = False
            break
        visited[cur] = 1
        child[k] = cur
        c = comp[cur]
        useA = base_is_A
        if c >= 0 and src_other[c]:
            useA = not useA
        if useA:
            n1 = sa[cur]; n2 = pa[cur]
        else:
            n1 = sb[cur]; n2 = pb[cur]
        nxt = n1 if n1 != prev else n2
        prev = cur; cur = nxt
    if ok and cur != child[0]:
        ok = False
    if not ok:
        if base_is_A:
            child[:] = ta
        else:
            child[:] = tb
        out[4] = base_cost; out[6] = 0.0; out[2] = 0; out[3] = 0.0
        touch[:] = 0
        return
    out[4] = base_cost - gain; out[6] = 1.0


@njit(cache=True)
def same_tour(t1, t2):
    n = t1.shape[0]
    p2 = np.empty(n, np.int32)
    for i in range(n):
        p2[t2[i]] = i
    for i in range(n):
        a = t1[i]; b = t1[(i + 1) % n]
        j = p2[a]
        if t2[(j + 1) % n] != b and t2[j - 1] != b:
            return False
    return True


@njit(cache=True)
def bp_distance(t1, t2):
    """Broken-pairs distance (undirected): number of edges of t1 not in t2."""
    n = t1.shape[0]
    p2 = np.empty(n, np.int32)
    for i in range(n):
        p2[t2[i]] = i
    d = 0
    for i in range(n):
        a = t1[i]; b = t1[(i + 1) % n]
        j = p2[a]
        if t2[(j + 1) % n] != b and t2[j - 1] != b:
            d += 1
    return d


def gpx(dm, A, B):
    n = len(A)
    child = np.empty(n, np.int32); touch = np.zeros(n, np.uint8); out = np.zeros(7)
    gpx_core(np.ascontiguousarray(dm, dtype=np.float64), np.asarray(A, np.int32), np.asarray(B, np.int32),
             child, touch, out)
    info = dict(n_comp=int(out[0]), n_feasible=int(out[1]), n_switched=int(out[2]), gain=float(out[3]),
                child_cost=float(out[4]), base_is_A=bool(out[5]), ok=bool(out[6]))
    return child, info, touch


def gpx_child(dm, A, B):
    c, info, _ = gpx(dm, A, B)
    return c, info


def px_ils(dm, time_limit, seed, m=8, K=10, Lmax=50, epoch_kicks=None, use_gpx=True, use_or3=None):
    t0 = time.perf_counter()
    dm = np.ascontiguousarray(np.asarray(dm, np.float64))
    n = dm.shape[0]
    ls = FastLS(dm, K=K, use_or3=use_or3)
    assert not ls.directed, "simple GPX implemented for symmetric instances only"
    rng = np.random.default_rng(seed)
    trajs = []
    for i in range(m):
        t, c, _ = ls.optimize(rng.permutation(n).astype(np.int32))
        trajs.append(ILSState(ls, t, c, seed * 1000 + i, Lmax))
    if epoch_kicks is None:
        epoch_kicks = max(100, n // 2)
    tel = dict(gpx_calls=0, gpx_with_feasible=0, gpx_switched=0, feasible_total=0, comps_total=0,
               switched_total=0, gpx_gain_total=0.0, child_strict_better_than_best_parent=0,
               ls_gain_after_gpx=0.0, replacements=0, clone_rejects=0, gpx_fail=0, epochs=0)
    best_cost = min(s.cs[1] for s in trajs)
    t_best = time.perf_counter() - t0
    done = False
    q, inq, qs = ls.q, ls.inq, ls.qs
    while not done:
        for st in trajs:
            if time.perf_counter() - t0 >= time_limit:
                done = True
                break
            # run the epoch in slices so that the time limit is respected
            left = epoch_kicks
            while left > 0 and time.perf_counter() - t0 < time_limit:
                k = min(left, 256)
                st.run(k)
                left -= k
        tel["epochs"] += 1
        if use_gpx and not done:
            for i in range(m):
                if time.perf_counter() - t0 >= time_limit:
                    break
                j = int(rng.integers(m - 1)); j = j + 1 if j >= i else j
                A, B = trajs[i], trajs[j]
                child, info, touch = gpx(dm, A.cur, B.cur)
                tel["gpx_calls"] += 1; tel["comps_total"] += info["n_comp"]
                tel["feasible_total"] += info["n_feasible"]
                if info["n_feasible"] > 0:
                    tel["gpx_with_feasible"] += 1
                if not info["ok"]:
                    tel["gpx_fail"] += 1
                if info["n_switched"] == 0:
                    continue
                tel["gpx_switched"] += 1; tel["switched_total"] += info["n_switched"]
                tel["gpx_gain_total"] += info["gain"]
                # queue LS from the portals
                pos = np.empty(n, np.int32); pos[child] = np.arange(n, dtype=np.int32)
                ls._reset_queue()
                for c in np.nonzero(touch)[0]:
                    _push_py(q, inq, qs, int(c))
                d = ls_queue(ls.dm, ls.nbo, ls.nbi, child, pos, q, inq, qs, ls.buf, ls.stats, ls.flags, 1 << 60)
                cc = info["child_cost"] + d
                tel["ls_gain_after_gpx"] += -d
                ci, cj = A.cs[0], B.cs[0]
                if cc < min(ci, cj) - EPS:
                    tel["child_strict_better_than_best_parent"] += 1
                worse, better = (A, B) if ci >= cj else (B, A)
                if cc < worse.cs[0] - EPS:
                    if same_tour(child, better.cur):
                        tel["clone_rejects"] += 1
                    else:
                        worse.set_current(child, cc)
                        tel["replacements"] += 1
        cb = min(s.cs[1] for s in trajs)
        if cb < best_cost - EPS:
            best_cost = cb; t_best = time.perf_counter() - t0
    bi = int(np.argmin([s.cs[1] for s in trajs]))
    best = trajs[bi].best.copy()
    pre = float(tour_cost(dm, best))
    best, _, _ = ls.optimize(best)
    elapsed = time.perf_counter() - t0
    kicks = int(sum(s.tel[T_KICKS] for s in trajs))
    # final diversity of current tours
    dists = [bp_distance(trajs[a].cur, trajs[b].cur) for a in range(m) for b in range(a + 1, m)]
    res = dict(tour=best, cost=float(tour_cost(dm, best)), cost_pre_polish=pre,
               cost_incremental=float(trajs[bi].cs[1]), elapsed=elapsed, t_best=t_best, kicks=kicks,
               kicks_per_s=kicks / max(elapsed, 1e-9),
               improving_kicks=int(sum(s.tel[T_IMPROVING] for s in trajs)),
               accepted_kicks=int(sum(s.tel[T_ACCEPTED] for s in trajs)),
               final_mean_bp_dist=float(np.mean(dists)) / n, m=m, epoch_kicks=epoch_kicks, use_gpx=use_gpx)
    res.update(tel)
    return res
