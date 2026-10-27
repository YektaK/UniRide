"""Contract tests for fast_ls / ils_fast / px_ils (plain assert script; prints PASS/FAIL lines).
Run:  python test_contracts.py  > test_contracts_output.txt"""
import os, sys, time, itertools, traceback
sys.dont_write_bytecode = True
import numpy as np
from fast_ls import (FastLS, ls_queue, tour_cost, is_symmetric, _push_py, ST_REV, ST_2OPT, ST_OR, ST_OR3)
from ils_fast import ils_fast, warmup, kick_double_bridge, splitmix64
from inst import load_tsp, load_atsp

RESULTS = []


def check(name, cond, info=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (("  | " + info) if info else ""), flush=True)


def is_perm(t, n):
    return len(t) == n and np.array_equal(np.sort(np.asarray(t)), np.arange(n))


def dedges(t):
    t = np.asarray(t)
    return set(zip(t.tolist(), np.roll(t, -1).tolist()))


def uedges(t):
    return {(min(a, b), max(a, b)) for a, b in dedges(t)}


def rand_euc(n, seed):
    xy = np.random.RandomState(seed).rand(n, 2) * 1000
    dm = np.floor(np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1)) + 0.5)
    np.fill_diagonal(dm, 0)
    return dm


def rand_asym(n, seed):
    rs = np.random.RandomState(seed)
    dm = rand_euc(n, seed) + np.floor(rs.rand(n, n) * 300)
    np.fill_diagonal(dm, 0)
    return dm


def per_move_check(dm, label, K=10, seed=0, use_or3=None):
    """Run the queue LS one move at a time; check every move."""
    ls = FastLS(dm, K=K, use_or3=use_or3)
    n = ls.n
    t = np.random.default_rng(seed).permutation(n).astype(np.int32)
    p = np.empty(n, np.int32); p[t] = np.arange(n, dtype=np.int32)
    ls._reset_queue()
    for c in t:
        _push_py(ls.q, ls.inq, ls.qs, int(c))
    cost = tour_cost(dm, t)
    moves = bad_cost = bad_perm = bad_pos = 0
    max_new_dir = max_new_und = 0
    while True:
        before_d = dedges(t)
        before_u = uedges(t)
        d = ls_queue(ls.dm, ls.nbo, ls.nbi, t, p, ls.q, ls.inq, ls.qs, ls.buf, ls.stats, ls.flags, 1)
        if d == 0.0:
            break
        moves += 1
        cost += d
        if abs(cost - tour_cost(dm, t)) > 1e-6:
            bad_cost += 1
        if not is_perm(t, n):
            bad_perm += 1
        if not np.array_equal(t[p], np.arange(n)):
            bad_pos += 1
        max_new_dir = max(max_new_dir, len(dedges(t) - before_d))
        max_new_und = max(max_new_und, len(uedges(t) - before_u))
    return ls, t, dict(moves=moves, bad_cost=bad_cost, bad_perm=bad_perm, bad_pos=bad_pos,
                       max_new_dir=max_new_dir, max_new_und=max_new_und, rev=int(ls.stats[ST_REV]),
                       n2=int(ls.stats[ST_2OPT]), nor=int(ls.stats[ST_OR]), nor3=int(ls.stats[ST_OR3]))


def brute_2opt_improving(dm, t):
    n = len(t); cnt = 0
    for i in range(n - 1):
        a, b = t[i], t[i + 1]
        for j in range(i + 2, n if i > 0 else n - 1):
            c, d = t[j], t[(j + 1) % n]
            if dm[a, c] + dm[b, d] - dm[a, b] - dm[c, d] < -1e-7:
                cnt += 1
    return cnt


def brute_oropt_improving(dm, t, directed):
    n = len(t); cnt = 0
    for i in range(n):
        for L in (1, 2, 3):
            seg = [t[(i + k) % n] for k in range(L)]
            p, q = t[(i - 1) % n], t[(i + L) % n]
            g = dm[p, seg[0]] + dm[seg[-1], q] - dm[p, q]
            rest = [t[(i + L + k) % n] for k in range(n - L)]  # q ... p
            for k in range(len(rest) - 1):
                x, y = rest[k], rest[k + 1]
                if dm[x, seg[0]] + dm[seg[-1], y] - dm[x, y] - g < -1e-7:
                    cnt += 1
                if not directed and dm[x, seg[-1]] + dm[seg[0], y] - dm[x, y] - g < -1e-7:
                    cnt += 1
    return cnt


def main():
    t0 = time.time()
    warmup()
    sym_cases = [("rand_euc120", rand_euc(120, 1)), ("rd100", load_tsp("rd100")[0]),
                 ("a280", load_tsp("a280")[0])]
    asym_cases = [("ft53", load_atsp("ft53")[0]), ("rand_asym150", rand_asym(150, 2))]

    # C0 symmetric / directed detection
    check("C0 symmetry detection (sym->undirected, asym->directed)",
          all(not FastLS(d).directed for _, d in sym_cases) and all(FastLS(d).directed for _, d in asym_cases))

    # C1-C3 per-move checks  (symmetric cases also with the benchmark configuration use_or3=True)
    cases = [(l, d, None) for l, d in sym_cases + asym_cases] + [(l + "+or3", d, True) for l, d in sym_cases]
    for lab, dm, o3 in cases:
        ls, t, s = per_move_check(dm, lab, use_or3=o3)
        directed = ls.directed
        check(f"C1 tour validity after every move [{lab}]", s["bad_perm"] == 0 and s["bad_pos"] == 0,
              f"moves={s['moves']} (2opt={s['n2']}, or={s['nor']}, or3={s['nor3']})")
        check(f"C2 incremental cost == recomputed after every move [{lab}]", s["bad_cost"] == 0)
        if directed:
            check(f"C3 ATSP: no reversal applied (reversal counter == 0) [{lab}]", s["rev"] == 0, f"rev={s['rev']}")
            check(f"C3 ATSP: each move adds <= 3 new directed arcs (orientation kept) [{lab}]",
                  s["max_new_dir"] <= 3, f"max_new_dir={s['max_new_dir']}")
        else:
            check(f"C3' symmetric: each move changes <= 3 undirected edges [{lab}]", s["max_new_und"] <= 3,
                  f"max_new_und={s['max_new_und']}")

    # C3 kick: delta exact, 4 new directed arcs at most, no reversal
    for lab, dm in [("ft53", asym_cases[0][1]), ("rand_asym150", asym_cases[1][1]), ("a280", sym_cases[2][1])]:
        n = len(dm); ls = FastLS(dm)
        t = np.random.default_rng(3).permutation(n).astype(np.int32)
        p = np.empty(n, np.int32); p[t] = np.arange(n, dtype=np.int32)
        rng = np.array([splitmix64(5)], np.uint64); bad = 0; mx = 0
        for _ in range(300):
            c0 = tour_cost(dm, t); e0 = dedges(t); ls._reset_queue()
            dk = kick_double_bridge(ls.dm, t, p, rng, 50, ls.buf, ls.q, ls.inq, ls.qs)
            if abs(c0 + dk - tour_cost(dm, t)) > 1e-6 or not is_perm(t, n):
                bad += 1
            mx = max(mx, len(dedges(t) - e0))
        check(f"C3 kick: exact delta, valid, <= 4 new directed arcs [{lab}]", bad == 0 and mx <= 4, f"max_new_arcs={mx}")

    # C2/C3 over whole ILS runs
    for lab, dm in [("ft53", asym_cases[0][1]), ("rand_asym150", asym_cases[1][1]), ("rd100", sym_cases[1][1])]:
        r = ils_fast(dm, 10.0, 7, max_kicks=20000, Lmax=100, use_or3=True)
        ok = is_perm(r["tour"], len(dm)) and r["cost_pre_polish"] == r["cost_incremental"] \
            and abs(r["cost"] - tour_cost(dm, np.asarray(r["tour"], np.int32))) < 1e-9
        check(f"C2 ILS (20000 kicks): valid tour, incremental == recomputed [{lab}]", ok,
              f"cost={r['cost']:.0f} incr={r['cost_incremental']:.0f} kicks={r['kicks']}")
        if r["directed"]:
            check(f"C3 ILS on ATSP applies no reversal [{lab}]", r["reversals"] == 0, f"rev={r['reversals']}")

    # C4 determinism
    for lab, dm in [("a280", sym_cases[2][1]), ("ft53", asym_cases[0][1])]:
        r1 = ils_fast(dm, 10.0, 42, max_kicks=5000, Lmax=100, use_or3=True)
        r2 = ils_fast(dm, 10.0, 42, max_kicks=5000, Lmax=100, use_or3=True)
        r3 = ils_fast(dm, 10.0, 43, max_kicks=5000, Lmax=100, use_or3=True)
        check(f"C4 same seed -> same tour [{lab}]", np.array_equal(r1["tour"], r2["tour"]) and r1["cost"] == r2["cost"],
              f"seed42 cost={r1['cost']:.0f}/{r2['cost']:.0f}; seed43 differs={not np.array_equal(r1['tour'], r3['tour'])}")

    # C5 local optimum: no candidate move improves (dry-run full scan of all cities)
    for lab, dm, o3 in cases:
        ls = FastLS(dm, use_or3=o3)
        worst = 0
        for s in range(5):
            t, c, _ = ls.optimize(np.random.default_rng(100 + s).permutation(len(dm)))
            worst = max(worst, ls.n_improving(t))
        check(f"C5 local optimum: 0 improving candidate moves (5 starts, full scan) [{lab}]", worst == 0,
              f"max cities with improving move={worst}")
    # C5b completeness of neighbour-list 2-opt with K = n-1 (independent brute force)
    for lab, dm in [("rand_euc120", sym_cases[0][1]), ("rd100", sym_cases[1][1])]:
        n = len(dm); ls = FastLS(dm, K=n - 1)
        t, c, _ = ls.optimize(np.random.default_rng(9).permutation(n))
        b2 = brute_2opt_improving(dm, list(t)); bo = brute_oropt_improving(dm, list(t), False)
        check(f"C5b K=n-1: brute-force full 2-opt finds no improving move [{lab}]", b2 == 0,
              f"brute 2-opt improving={b2}; info: brute full Or-opt improving={bo}")
    for lab, dm in [("ft53", asym_cases[0][1])]:
        n = len(dm); ls = FastLS(dm, K=n - 1)
        t, c, _ = ls.optimize(np.random.default_rng(9).permutation(n))
        bo = brute_oropt_improving(dm, list(t), True)
        print(f"INFO K=n-1 ATSP [{lab}]: brute-force full directed Or-opt improving moves = {bo}")

    # C7 GPX contracts (if px_ils is available)
    try:
        import px_ils
    except ImportError:
        px_ils = None
    if px_ils is not None:
        for lab, dm in [("a280", sym_cases[2][1]), ("rand_euc120", sym_cases[0][1]), ("pr439", load_tsp("pr439")[0])]:
            n = len(dm); bad_valid = bad_le = bad_common = 0; nfeas = 0; ngain = 0
            for s in range(30):
                ra = ils_fast(dm, 10.0, 200 + s, max_kicks=300 + 50 * s)
                rb = ils_fast(dm, 10.0, 300 + s, max_kicks=300 + 30 * s)
                A = np.asarray(ra["tour"], np.int32); B = np.asarray(rb["tour"], np.int32)
                child, info = px_ils.gpx_child(dm, A, B)
                if not is_perm(child, n):
                    bad_valid += 1
                cc = tour_cost(dm, child)
                if cc > min(tour_cost(dm, A), tour_cost(dm, B)) + 1e-9:
                    bad_le += 1
                if not (uedges(A) & uedges(B)) <= uedges(child):
                    bad_common += 1
                if abs(cc - info["child_cost"]) > 1e-6:
                    bad_valid += 1
                nfeas += info["n_feasible"]; ngain += int(info["gain"] > 0)
            check(f"C7 GPX child valid, <= best parent, keeps 100% common edges (30 pairs) [{lab}]",
                  bad_valid == 0 and bad_le == 0 and bad_common == 0,
                  f"feasible comps total={nfeas}, pairs with strict gain={ngain}")
        # identical parents -> child == parent
        dm = sym_cases[2][1]; r = ils_fast(dm, 10.0, 1, max_kicks=500)
        A = np.asarray(r["tour"], np.int32)
        child, info = px_ils.gpx_child(dm, A, np.roll(A[::-1], 5))
        check("C7 GPX(T, rotate(reverse(T))) == T (no components)", uedges(child) == uedges(A) and info["n_comp"] == 0)

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\nSUMMARY: {len(RESULTS) - n_fail}/{len(RESULTS)} contracts passed, {n_fail} failed "
          f"({time.time() - t0:.1f} s)")
    return n_fail


if __name__ == "__main__":
    sys.exit(main())
