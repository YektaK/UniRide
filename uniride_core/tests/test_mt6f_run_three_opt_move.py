"""MT6F-04: the RUN-TSP "k2" move is a canonical 3-opt move on one random cut.

Contract under test (docs/superpowers/plans/2026-10-27-mt6-followup-sota-common-shims-l3-l10.md,
item MT6F-04, option b; CANONICAL_THREE_OPT_DESIGN.md):

* one admitted cut ``(i, j, k)`` is drawn with three ``rng.randint`` calls in the order
  i, j, k (admitted = ``j - i >= 2``, ``k - j >= 2``, ``n - k + i >= 2``, both forward
  separations at most ``window``);
* candidates are the identity plus the canonical neighbourhood of that cut (7 undirected
  reconnections on a symmetric matrix, the single ``S1 + S3 + S2`` reconnection on an
  asymmetric one), each costed once with ``closed_tour_cost``; the first minimum wins;
* ``n < 6`` returns the tour unchanged.

The reference enumerator below is written independently: it does not import the production
candidate generator (design, "Verification strategy").  It builds every arrangement of the
three segments (all orders, all reversal flags), reduces each to its cycle class, and keeps
one representative per class.
"""

from __future__ import annotations

import itertools
import random

import pytest

from uniride_core.algorithms.sota_tsp import run_tsp
from uniride_core.algorithms.sota_tsp.run_tsp import RUN_TSP, RUNConfig


# --------------------------------------------------------------------------- helpers


def _move(tour, matrix, rng, window=12):
    return run_tsp._apply_random_cut_three_opt(tour, matrix, rng, window)


def _cost(tour, matrix):
    n = len(tour)
    return sum(matrix[tour[x]][tour[(x + 1) % n]] for x in range(n))


def _matrix(n: int, seed: int, symmetric: bool):
    rng = random.Random(seed)
    m = [[0] * n for _ in range(n)]
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            if symmetric and b < a:
                m[a][b] = m[b][a]
            else:
                m[a][b] = rng.randint(1, 1000)
    return m


def _rotate_to(seq, anchor):
    idx = seq.index(anchor)
    return seq[idx:] + seq[:idx]


def _class_key(cycle, anchor, directed):
    fwd = tuple(_rotate_to(list(cycle), anchor))
    if directed:
        return fwd
    bwd = tuple(_rotate_to(list(reversed(cycle)), anchor))
    return min(fwd, bwd)


def _reference_classes(tour, i, j, k, directed):
    """Independent enumeration: {class key: representative} over every segment arrangement.

    Symmetric: all 3! orders x 2^3 reversal flags, classes taken up to rotation and
    reversal of the whole cycle.  Directed: segment orientation is preserved (no flag),
    classes taken up to rotation only.
    """
    segs = [tour[i + 1:j + 1], tour[j + 1:k + 1], tour[k + 1:] + tour[:i + 1]]
    anchor = tour[0]
    classes = {}
    for order in itertools.permutations(range(3)):
        for flags in itertools.product((False, True), repeat=3):
            if directed and any(flags):
                continue
            cycle = []
            for idx, flag in zip(order, flags):
                cycle.extend(reversed(segs[idx]) if flag else segs[idx])
            classes.setdefault(_class_key(cycle, anchor, directed), cycle)
    return classes


class _CutRng:
    """Fixes the cut: the n-th randint call returns the n-th target, clipped into [a, b]."""

    def __init__(self, cut):
        self.targets = list(cut)
        self.calls = 0

    def randint(self, a, b):
        target = self.targets[min(self.calls, len(self.targets) - 1)]
        self.calls += 1
        return min(max(target, a), b)


CUTS = {
    8: [(0, 2, 4), (1, 3, 6), (1, 4, 6), (2, 4, 6), (0, 3, 6)],
    12: [(0, 2, 4), (3, 6, 9), (1, 4, 10), (0, 5, 10), (2, 5, 8)],
}


def _admitted(n, i, j, k, window):
    return (
        0 <= i < j < k < n
        and j - i >= 2
        and k - j >= 2
        and n - k + i >= 2
        and j - i <= window
        and k - j <= window
    )


def test_test_cuts_are_admitted():
    for n, cuts in CUTS.items():
        for cut in cuts:
            assert _admitted(n, *cut, window=12), (n, cut)


@pytest.mark.parametrize("directed", [False, True])
def test_reference_enumerator_class_counts(directed):
    tour = list(range(10))
    classes = _reference_classes(tour, 1, 4, 7, directed)
    assert len(classes) == (2 if directed else 8)


# ---------------------------------------------------------------- best of the neighbourhood


@pytest.mark.parametrize("n", [8, 12])
@pytest.mark.parametrize("symmetric", [True, False])
def test_move_returns_identity_or_best_canonical_candidate(n, symmetric):
    directed = not symmetric
    non_identity_results = 0
    for seed in range(20):
        matrix = _matrix(n, seed, symmetric)
        tour = random.Random(1000 + seed).sample(range(n), n)
        for cut in CUTS[n]:
            original = list(tour)
            result = _move(tour, matrix, _CutRng(cut), 12)
            assert tour == original, "input tour must not be mutated"
            assert sorted(result) == list(range(n))

            classes = _reference_classes(tour, *cut, directed)
            identity_key = _class_key(tour, tour[0], directed)
            costs = {key: _cost(cyc, matrix) for key, cyc in classes.items()}
            best = min(costs.values())
            assert abs(_cost(result, matrix) - best) < 1e-9, (n, symmetric, seed, cut)
            if costs[identity_key] == best:
                assert result == tour, "ties keep the identity (first minimum)"
            else:
                assert _class_key(result, tour[0], directed) in {
                    key for key, value in costs.items() if value == best
                }
                non_identity_results += 1
    assert non_identity_results > 0, "the move never left the identity: the test is vacuous"


def test_directed_move_never_reverses_a_segment():
    n = 12
    matrix = _matrix(n, 3, symmetric=False)
    tour = list(range(n))
    for cut in CUTS[n]:
        result = _move(tour, matrix, _CutRng(cut), 12)
        # An orientation-preserving move keeps every directed arc of the input that is not
        # one of the three cut arcs; a reversed segment would flip them.
        arcs_in = {(tour[x], tour[(x + 1) % n]) for x in range(n)}
        arcs_out = {(result[x], result[(x + 1) % n]) for x in range(n)}
        assert len(arcs_in - arcs_out) in (0, 3), cut


# ------------------------------------------------------------------------- cost accounting


def _install_cost_spy(monkeypatch):
    """Count every tour costed by the move, whichever cost helper the module uses."""
    seen = []

    def spy(tour, matrix):
        seen.append(list(tour))
        return _cost(tour, matrix)

    monkeypatch.setattr(run_tsp, "_tour_cost", spy)
    monkeypatch.setattr(run_tsp, "closed_tour_cost", spy, raising=False)
    return seen


@pytest.mark.parametrize(("symmetric", "expected_calls"), [(True, 8), (False, 2)])
@pytest.mark.parametrize("n", [8, 12])
def test_each_distinct_candidate_is_costed_exactly_once(monkeypatch, n, symmetric, expected_calls):
    directed = not symmetric
    matrix = _matrix(n, 5, symmetric)
    tour = random.Random(77).sample(range(n), n)
    seen = _install_cost_spy(monkeypatch)

    _move(tour, matrix, _CutRng(CUTS[n][1]), 12)

    assert len(seen) == expected_calls
    keys = [_class_key(t, tour[0], directed) for t in seen]
    assert len(set(keys)) == len(keys), "a duplicate candidate was costed"


# ------------------------------------------------------------------------- small and window


@pytest.mark.parametrize("n", [0, 1, 3, 4, 5])
def test_below_six_nodes_returns_the_tour_unchanged(n):
    matrix = _matrix(max(n, 1), 1, True)
    tour = list(range(n))
    rng = _CutRng((0, 2, 4))
    result = _move(tour, matrix, rng, 12)
    assert result == tour
    assert result is not tour
    assert rng.calls == 0


@pytest.mark.parametrize("n", [6, 7, 9, 14, 30])
@pytest.mark.parametrize("window", [2, 3, 5, 12])
def test_drawn_cut_is_always_an_admitted_cut_within_the_window(n, window):
    class Recording:
        def __init__(self, seed):
            self.inner = random.Random(seed)
            self.draws = []

        def randint(self, a, b):
            value = self.inner.randint(a, b)
            self.draws.append(value)
            return value

    matrix = _matrix(n, 2, True)
    tour = list(range(n))
    for seed in range(300):
        rng = Recording(seed)
        _move(tour, matrix, rng, window)
        assert len(rng.draws) == 3, "exactly one cut is drawn with three randint calls"
        i, j, k = rng.draws
        assert _admitted(n, i, j, k, window), (n, window, seed, rng.draws)


def test_invalid_window_is_rejected():
    matrix = _matrix(8, 1, True)
    with pytest.raises(ValueError):
        _move(list(range(8)), matrix, random.Random(0), 1)


# ------------------------------------------------------------------------------ determinism


@pytest.mark.parametrize("symmetric", [True, False])
def test_same_seed_gives_the_same_run_result(symmetric):
    matrix = _matrix(14, 9, symmetric)

    def signature():
        cfg = RUNConfig(population_size=6, max_iterations=4, seed=5)
        res = RUN_TSP(cfg).solve_with_matrix(matrix)
        return list(res.tour), float(res.tour_length), list(res.history or [])

    first = signature()
    assert first == signature()
    assert sorted(first[0]) == list(range(14))
