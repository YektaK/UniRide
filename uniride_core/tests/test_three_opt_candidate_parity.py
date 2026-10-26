"""MT6-01 (audit M25): the canonical 3-opt candidate generator is a pure speed-up.

The production generator must yield exactly the candidate sequence of the
historical implementation (same cut triples, same candidates, same rotation,
same order).  The historical implementation is frozen below as a private test
fixture (verbatim copy of ``three_opt.py`` at WIP 7e189c05, functions renamed
with an ``_old`` prefix); it is never imported by production code.

Deterministic call-count tests (no timings) pin the speed-up mechanism.
"""

from __future__ import annotations

from itertools import combinations, permutations, product
import random

import pytest

import uniride_core.algorithms.objective_budget as objective_budget_module
import uniride_core.algorithms.three_opt as three_opt_module
from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    improve_three_opt_budgeted,
)
from uniride_core.algorithms.three_opt import (
    closed_tour_cost,
    generate_three_opt_candidates,
    improve_three_opt,
    iter_three_opt_cuts,
)


# ---------------------------------------------------------------------------
# Frozen reference implementation (historical generator, verbatim semantics)
# ---------------------------------------------------------------------------


def _old_iter_three_opt_cuts(n, window=None):
    if n < 6:
        return
    if window is not None and window < 2:
        raise ValueError("3-opt window must be at least 2")
    for i, j, k in combinations(range(n), 3):
        if j - i < 2 or k - j < 2 or n - k + i < 2:
            continue
        if window is not None and (j - i > window or k - j > window):
            continue
        yield i, j, k


def _old_rotate_to_anchor(route, anchor):
    idx = route.index(anchor)
    return list(route[idx:]) + list(route[:idx])


def _old_directed_cycle_key(route):
    values = tuple(route)
    return min(values[idx:] + values[:idx] for idx in range(len(values)))


def _old_symmetric_cycle_key(route):
    values = tuple(route)
    reverse = tuple(reversed(values))
    rotations = [values[idx:] + values[:idx] for idx in range(len(values))]
    rotations.extend(reverse[idx:] + reverse[:idx] for idx in range(len(reverse)))
    return min(rotations)


def _old_undirected_edges(route):
    return frozenset(
        frozenset((node, route[(idx + 1) % len(route)]))
        for idx, node in enumerate(route)
    )


def _old_generate_three_opt_candidates(route, i, j, k, *, directed):
    route_list = list(route)
    n = len(route_list)
    if len(set(route_list)) != n:
        raise ValueError("3-opt route must contain unique nodes")
    if not (0 <= i < j < k < n):
        raise ValueError("3-opt cut indices must satisfy 0 <= i < j < k < n")
    if j - i < 2 or k - j < 2 or n - k + i < 2:
        raise ValueError("3-opt cut edges must be non-adjacent")

    segments = [
        route_list[i + 1:j + 1],
        route_list[j + 1:k + 1],
        route_list[k + 1:] + route_list[:i + 1],
    ]
    anchor = route_list[0]

    if directed:
        original_key = _old_directed_cycle_key(route_list)
        candidates = {}
        for order in permutations(range(3)):
            candidate = [node for segment_idx in order for node in segments[segment_idx]]
            key = _old_directed_cycle_key(candidate)
            if key != original_key:
                candidates.setdefault(key, _old_rotate_to_anchor(candidate, anchor))
        return [candidates[key] for key in sorted(candidates)]

    original_key = _old_symmetric_cycle_key(route_list)
    original_edges = _old_undirected_edges(route_list)
    candidates = {}
    for order in permutations(range(3)):
        for reversed_flags in product((False, True), repeat=3):
            candidate = []
            for segment_idx, reverse_segment in zip(order, reversed_flags):
                segment = segments[segment_idx]
                candidate.extend(reversed(segment) if reverse_segment else segment)
            key = _old_symmetric_cycle_key(candidate)
            if key != original_key:
                candidates.setdefault(key, _old_rotate_to_anchor(candidate, anchor))

    ordered = list(candidates.values())
    ordered.sort(
        key=lambda candidate: (
            len(original_edges - _old_undirected_edges(candidate)),
            tuple(candidate),
        )
    )
    return ordered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WINDOWS = (None, 2, 3, 12)


def _routes(n, seed, extra=2):
    """Identity plus seeded random permutations (the anchor is route[0])."""
    rng = random.Random(seed * 1000 + n)
    out = [list(range(n))]
    for _ in range(extra):
        perm = list(range(n))
        rng.shuffle(perm)
        out.append(perm)
    return out


def _random_matrix(n, seed, *, symmetric, integer):
    rng = random.Random(seed)
    matrix = [[0.0] * n for _ in range(n)]
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            if symmetric and b < a:
                matrix[a][b] = matrix[b][a]
                continue
            matrix[a][b] = float(rng.randint(1, 99)) if integer else rng.random() * 100.0
    return matrix


# ---------------------------------------------------------------------------
# Red tests: the speed-up mechanism (deterministic call counts)
# ---------------------------------------------------------------------------


def test_candidate_generation_does_not_build_cycle_keys_per_arrangement(monkeypatch):
    calls = {"sym": 0, "dir": 0}

    def counting_sym(route):
        calls["sym"] += 1
        return _old_symmetric_cycle_key(route)

    def counting_dir(route):
        calls["dir"] += 1
        return _old_directed_cycle_key(route)

    # raising=False: the helpers are removed from production by the fix.
    monkeypatch.setattr(three_opt_module, "_symmetric_cycle_key", counting_sym, raising=False)
    monkeypatch.setattr(three_opt_module, "_directed_cycle_key", counting_dir, raising=False)

    route = list(range(12))
    sym = generate_three_opt_candidates(route, 1, 4, 8, directed=False)
    dirc = generate_three_opt_candidates(route, 1, 4, 8, directed=True)

    assert len(sym) == 7 and len(dirc) == 1
    assert calls == {"sym": 0, "dir": 0}


def test_windowed_cut_enumeration_does_not_scan_all_triples(monkeypatch):
    def forbidden_combinations(*args, **kwargs):
        raise AssertionError("windowed cut enumeration must not scan C(n, 3) triples")

    monkeypatch.setattr(three_opt_module, "combinations", forbidden_combinations, raising=False)

    cuts = list(iter_three_opt_cuts(40, 5))
    assert cuts  # produced without the full triple scan
    assert all(2 <= j - i <= 5 and 2 <= k - j <= 5 for i, j, k in cuts)


# ---------------------------------------------------------------------------
# Parity: cut enumeration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("window", (None, 2, 3, 4, 7, 12, 30))
def test_cut_enumeration_parity_exhaustive_n(window):
    checked = 0
    for n in range(0, 41):
        assert list(iter_three_opt_cuts(n, window)) == list(_old_iter_three_opt_cuts(n, window))
        checked += 1
    assert checked == 41


@pytest.mark.parametrize("n", (60, 100))
def test_cut_enumeration_parity_large_n(n):
    for window in (None, 12) if n == 60 else (12,):
        new = list(iter_three_opt_cuts(n, window))
        assert new == list(_old_iter_three_opt_cuts(n, window))
        assert new


def test_cut_enumeration_rejects_small_window_like_before():
    for window in (0, 1, -3):
        with pytest.raises(ValueError):
            list(iter_three_opt_cuts(10, window))
        with pytest.raises(ValueError):
            list(_old_iter_three_opt_cuts(10, window))
    assert list(iter_three_opt_cuts(5, 12)) == []
    assert list(iter_three_opt_cuts(5, 1)) == []  # n < 6 returns before window check


@pytest.mark.parametrize("window", (12.0, 12.5, "12", 2.0))
def test_cut_enumeration_rejects_non_integer_window_with_value_error(window):
    # MT6-01 polish: the range-based enumeration would raise a bare TypeError for 12.0;
    # the window is validated explicitly instead (the historical code, which only
    # compared the window, tolerated floats; the study profiles pass integers).
    with pytest.raises(ValueError, match="integer"):
        list(iter_three_opt_cuts(10, window))
    with pytest.raises(ValueError, match="integer"):
        improve_three_opt(list(range(10)), _random_matrix(10, 1, symmetric=True, integer=True), window=window)
    with pytest.raises(ValueError, match="integer"):
        improve_three_opt_budgeted(
            list(range(10)), _random_matrix(10, 1, symmetric=True, integer=True),
            ObjectiveEvaluationBudget(None), max_iterations=1, window=window,
        )


def test_cut_enumeration_accepts_integer_like_windows():
    import numpy as np

    expected = list(iter_three_opt_cuts(10, 12))
    assert list(iter_three_opt_cuts(10, np.int64(12))) == expected
    assert list(iter_three_opt_cuts(10, None)) == list(iter_three_opt_cuts(10))


# ---------------------------------------------------------------------------
# Parity: candidate sequence (also proves M25-d: no admitted cut loses a candidate)
# ---------------------------------------------------------------------------

PARITY_COUNTS = {"triples": 0, "candidates": 0}


@pytest.mark.parametrize("window", WINDOWS)
@pytest.mark.parametrize("n", range(6, 17))
def test_candidate_parity_exhaustive_small_n(n, window):
    for route in _routes(n, seed=n):
        for i, j, k in _old_iter_three_opt_cuts(n, window):
            for directed in (False, True):
                old = _old_generate_three_opt_candidates(route, i, j, k, directed=directed)
                new = generate_three_opt_candidates(route, i, j, k, directed=directed)
                assert new == old, (n, window, route, (i, j, k), directed)
                # M25-d: every admitted cut keeps all 7 (symmetric) / 1 (directed).
                assert len(old) == (1 if directed else 7)
                PARITY_COUNTS["triples"] += 1
                PARITY_COUNTS["candidates"] += len(new)


@pytest.mark.parametrize("window", (None, 12))
@pytest.mark.parametrize("n", (20, 24, 30))
def test_candidate_parity_medium_n_strided(n, window):
    for route in _routes(n, seed=n, extra=1):
        cuts = list(_old_iter_three_opt_cuts(n, window))
        for idx, (i, j, k) in enumerate(cuts):
            if idx % 3:
                continue
            for directed in (False, True):
                assert generate_three_opt_candidates(
                    route, i, j, k, directed=directed
                ) == _old_generate_three_opt_candidates(route, i, j, k, directed=directed)


def test_candidate_parity_n60_window_12_strided():
    n = 60
    for route in _routes(n, seed=60, extra=1):
        cuts = list(_old_iter_three_opt_cuts(n, 12))
        for idx, (i, j, k) in enumerate(cuts):
            if idx % 6:
                continue
            for directed in (False, True):
                assert generate_three_opt_candidates(
                    route, i, j, k, directed=directed
                ) == _old_generate_three_opt_candidates(route, i, j, k, directed=directed)


@pytest.mark.parametrize("symmetric", (True, False))
@pytest.mark.parametrize("integer", (True, False))
@pytest.mark.parametrize("n", (8, 13, 30))
def test_candidate_costs_and_deltas_parity(n, symmetric, integer):
    matrix = _random_matrix(n, seed=n * 7 + symmetric * 2 + integer, symmetric=symmetric, integer=integer)
    directed = not symmetric
    for route in _routes(n, seed=n, extra=1):
        base_cost = closed_tour_cost(route, matrix)
        for idx, (i, j, k) in enumerate(_old_iter_three_opt_cuts(n, 12)):
            if idx % 4:
                continue
            old = _old_generate_three_opt_candidates(route, i, j, k, directed=directed)
            new = generate_three_opt_candidates(route, i, j, k, directed=directed)
            assert [closed_tour_cost(c, matrix) for c in new] == [closed_tour_cost(c, matrix) for c in old]
            assert [closed_tour_cost(c, matrix) - base_cost for c in new] == [
                closed_tour_cost(c, matrix) - base_cost for c in old
            ]


def test_candidates_input_validation_unchanged():
    with pytest.raises(ValueError):
        generate_three_opt_candidates([0, 1, 2, 3, 4, 4], 0, 2, 4, directed=False)
    with pytest.raises(ValueError):
        generate_three_opt_candidates(list(range(8)), 3, 2, 5, directed=False)
    with pytest.raises(ValueError):
        generate_three_opt_candidates(list(range(8)), 0, 1, 5, directed=True)
    with pytest.raises(ValueError):
        generate_three_opt_candidates(list(range(8)), 0, 3, 7, directed=False)


def test_parity_case_counts_are_nontrivial():
    # Runs after the exhaustive parametrised tests in file order.
    assert PARITY_COUNTS["triples"] > 5000
    assert PARITY_COUNTS["candidates"] > 5000


# ---------------------------------------------------------------------------
# Full-run parity of the controllers against the frozen generator
# ---------------------------------------------------------------------------


def _patch_frozen_generator(monkeypatch):
    for module in (three_opt_module, objective_budget_module):
        monkeypatch.setattr(module, "iter_three_opt_cuts", _old_iter_three_opt_cuts)
        monkeypatch.setattr(module, "generate_three_opt_candidates", _old_generate_three_opt_candidates)


def _ft53_like_matrix():
    return _random_matrix(53, seed=5353, symmetric=False, integer=True)


CASES = {
    "sym30": lambda: _random_matrix(30, seed=3001, symmetric=True, integer=True),
    "sym30_float": lambda: _random_matrix(30, seed=3002, symmetric=True, integer=False),
    "asym30": lambda: _random_matrix(30, seed=3003, symmetric=False, integer=True),
    "asym30_float": lambda: _random_matrix(30, seed=3004, symmetric=False, integer=False),
    "ft53_like": _ft53_like_matrix,
}


def _start_route(n, seed):
    route = list(range(n))
    random.Random(seed).shuffle(route)
    return route


def _run_plain(matrix, first_improvement, window, max_iterations=2):
    res = improve_three_opt(
        _start_route(len(matrix), 99),
        matrix,
        max_iterations=max_iterations,
        first_improvement=first_improvement,
        window=window,
    )
    return (res.route, res.cost, res.iterations, res.evaluations, res.mode)


def _run_budgeted(matrix, first_improvement, window, limit, max_iterations=2):
    budget = ObjectiveEvaluationBudget(limit)
    res = improve_three_opt_budgeted(
        _start_route(len(matrix), 99),
        matrix,
        budget,
        max_iterations=max_iterations,
        first_improvement=first_improvement,
        window=window,
    )
    return (
        res.route,
        res.cost,
        res.iterations,
        res.evaluations,
        res.budget_exhausted,
        res.mode,
        res.termination_reason,
        budget.used,
    )


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("first_improvement", (False, True))
@pytest.mark.parametrize("window", (12, None))
def test_improve_three_opt_full_run_parity(monkeypatch, case, first_improvement, window):
    matrix = CASES[case]()
    if window is None and (len(matrix) > 30 or not first_improvement):
        pytest.skip("window=None with the frozen generator is slow; best-improvement is covered by window=12")
    new = _run_plain(matrix, first_improvement, window)
    _patch_frozen_generator(monkeypatch)
    assert _run_plain(matrix, first_improvement, window) == new
    assert new[3] > 0  # evaluations really happened


@pytest.mark.parametrize("case", sorted(CASES))
@pytest.mark.parametrize("first_improvement", (False, True))
@pytest.mark.parametrize("limit", (None, 25))  # not binding / binding
def test_budgeted_three_opt_full_run_parity(monkeypatch, case, first_improvement, limit):
    matrix = CASES[case]()
    new = _run_budgeted(matrix, first_improvement, 12, limit)
    _patch_frozen_generator(monkeypatch)
    assert _run_budgeted(matrix, first_improvement, 12, limit) == new
    if limit is not None and not first_improvement:  # best improvement scans 25+ candidates: budget binds
        assert new[4] is True and new[6] == "evaluation_budget_exhausted" and new[7] == limit


# Convergence parity (MT6-01 polish): no iteration cap, window=None, small n.  The tests
# above cap max_iterations at 2 and skip best-improvement with window=None; here the
# search runs to its local optimum (the frozen generator is fast enough for n <= 12).
CONVERGENCE_CASES = {
    f"{kind}{n}": (lambda n=n, symmetric=symmetric, integer=integer: _random_matrix(
        n, seed=7000 + n, symmetric=symmetric, integer=integer))
    for n in (7, 9, 12)
    for kind, symmetric, integer in (("sym", True, True), ("symf", True, False), ("asym", False, True))
}


@pytest.mark.parametrize("case", sorted(CONVERGENCE_CASES))
@pytest.mark.parametrize("first_improvement", (False, True))
def test_three_opt_converges_to_the_same_local_optimum_window_none(monkeypatch, case, first_improvement):
    matrix = CONVERGENCE_CASES[case]()
    plain = _run_plain(matrix, first_improvement, None, max_iterations=500)
    budgeted = _run_budgeted(matrix, first_improvement, None, None, max_iterations=500)
    _patch_frozen_generator(monkeypatch)
    assert _run_plain(matrix, first_improvement, None, max_iterations=500) == plain
    assert _run_budgeted(matrix, first_improvement, None, None, max_iterations=500) == budgeted
    # converged: the last pass found nothing, so the run ended before the 500 cap
    assert plain[2] < 500 and budgeted[2] < 500
    assert budgeted[6] == "no_improving_move"
    assert plain[3] > 0


# ---------------------------------------------------------------------------
# M25-e: the Numba-module wrappers must not feed NumPy arrays to the Python engine
# ---------------------------------------------------------------------------


def _spy_on_three_opt_matrix(monkeypatch):
    import uniride_core.algorithms.local_search_numba as lsn

    seen = []
    real = lsn.improve_three_opt

    def spy(route, matrix, **kwargs):
        seen.append(matrix)
        return real(route, matrix, **kwargs)

    monkeypatch.setattr(lsn, "improve_three_opt", spy)
    return lsn, seen


def _assert_plain_float_lists(matrix):
    assert isinstance(matrix, list)
    assert all(isinstance(row, list) for row in matrix)
    assert all(type(value) is float for row in matrix for value in row)


def test_improve_route_numba_passes_plain_list_matrix_to_python_engine(monkeypatch):
    import numpy as np

    lsn, seen = _spy_on_three_opt_matrix(monkeypatch)
    matrix = np.array(_random_matrix(14, seed=1414, symmetric=True, integer=True))
    route = np.array(_start_route(14, 5), dtype=np.int64)

    improved, cost = lsn.improve_route_numba(route, matrix, "three_opt", 3)

    expected = improve_three_opt(route.tolist(), matrix.tolist(), max_iterations=3)
    assert improved.tolist() == expected.route and cost == expected.cost
    assert len(seen) == 1
    _assert_plain_float_lists(seen[0])


def test_three_opt_local_search_class_passes_plain_list_matrix(monkeypatch):
    import numpy as np

    lsn, seen = _spy_on_three_opt_matrix(monkeypatch)
    n = 12
    matrix = np.array(_random_matrix(n, seed=1212, symmetric=False, integer=True))
    names = [f"L{idx}" for idx in range(n)]

    def duration_func(route):
        index = {name: idx for idx, name in enumerate(names)}
        return float(sum(matrix[index[a]][index[b]] for a, b in zip(route, route[1:] + route[:1])))

    duration_func._np_dist_matrix = matrix
    duration_func._np_unique_locs = names
    start = [names[idx] for idx in _start_route(n, 3)]

    improved, duration = lsn.ThreeOptLocalSearch(max_iterations=3).improve(start, duration_func)

    assert sorted(improved) == sorted(names)
    assert duration == duration_func(improved)
    assert len(seen) == 1
    _assert_plain_float_lists(seen[0])
