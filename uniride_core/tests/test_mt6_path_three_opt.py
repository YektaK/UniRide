"""MT6-04 (audit M14): path 3-opt for the production hybrid local search.

The production hybrid costs an open sequence with a caller's black-box
objective (for example a Split-decoded chromosome).  The path neighbourhood in
``uniride_core.algorithms.three_opt`` is tested here against an independent
brute-force enumerator written in this module.  The enumerator does not import
or call the generator under test (CANONICAL_THREE_OPT_DESIGN.md, verification
strategy: reference tests must not reuse the code under test).

Neighbourhood under test: cuts ``-1 <= i < j < k <= n - 1``,
``B = route[i + 1:j + 1]``, ``C = route[j + 1:k + 1]`` (both non-empty), the
prefix ``A = route[:i + 1]`` and suffix ``D = route[k + 1:]`` fixed; the 7
non-identity arrangements of (B, C) order x reversal, deduplicated per cut by
sequence equality.
"""

from __future__ import annotations

import itertools
import random
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import pytest

from uniride_core.algorithms import local_search as ls_module
from uniride_core.algorithms import three_opt as core_three_opt
from uniride_core.algorithms.local_search import (
    HybridLocalSearch,
    LocalSearchType,
    ThreeOptLocalSearch,
    TwoOptLocalSearch,
)


# --------------------------------------------------------------------------
# Independent brute-force reference (no import of the generator under test)
# --------------------------------------------------------------------------

def _ref_cuts(n: int, window: Optional[int]) -> List[Tuple[int, int, int]]:
    """All cuts with non-empty B and C, filtered by the canonical window rule."""
    cuts = []
    for i, j, k in itertools.combinations(range(-1, n), 3):
        if k > n - 1:
            continue
        if window is not None and (j - i > window or k - j > window):
            continue
        cuts.append((i, j, k))
    return cuts


def _ref_neighbours(route: Sequence, i: int, j: int, k: int) -> Set[Tuple]:
    """Every distinct non-identity sequence reachable for one cut."""
    n = len(route)
    positions = list(range(n))
    prefix = positions[: i + 1]
    seg_b = positions[i + 1: j + 1]
    seg_c = positions[j + 1: k + 1]
    suffix = positions[k + 1:]
    found: Set[Tuple] = set()
    for c_first, rev_b, rev_c in itertools.product((False, True), repeat=3):
        b = seg_b[::-1] if rev_b else seg_b
        c = seg_c[::-1] if rev_c else seg_c
        middle = (c + b) if c_first else (b + c)
        order = prefix + middle + suffix
        found.add(tuple(route[p] for p in order))
    found.discard(tuple(route))
    return found


def _ref_all_neighbours(route: Sequence, window: Optional[int]) -> Set[Tuple]:
    out: Set[Tuple] = set()
    for i, j, k in _ref_cuts(len(route), window):
        out |= _ref_neighbours(route, i, j, k)
    return out


def _random_objective(n: int, seed: int) -> Callable[[List[int]], float]:
    """Asymmetric depot-closed path cost over nodes 1..n (node 0 is the depot)."""
    rng = random.Random(seed)
    matrix = [[0.0 if a == b else rng.uniform(1.0, 100.0) for b in range(n + 1)]
              for a in range(n + 1)]

    def cost(route: List[int]) -> float:
        full = [0] + list(route) + [0]
        return sum(matrix[a][b] for a, b in zip(full, full[1:]))

    return cost


# --------------------------------------------------------------------------
# Candidate generation
# --------------------------------------------------------------------------

def test_c_prime_b_prime_is_generated():
    route = list(range(8))
    candidates = core_three_opt.generate_path_three_opt_candidates(route, 1, 3, 5)
    # B = [2, 3], C = [4, 5]; C'B' = [5, 4, 3, 2]
    assert [0, 1, 5, 4, 3, 2, 6, 7] in candidates


def test_candidates_equal_independent_reference_for_every_cut():
    for n in (2, 3, 4, 5, 6, 7, 8):
        route = list(range(10, 10 + n))
        for i, j, k in _ref_cuts(n, None):
            produced = core_three_opt.generate_path_three_opt_candidates(route, i, j, k)
            assert len(produced) == len({tuple(c) for c in produced}), "no duplicates"
            assert {tuple(c) for c in produced} == _ref_neighbours(route, i, j, k), (n, i, j, k)


def test_first_position_can_move_with_empty_prefix():
    route = ["A", "B", "C", "D"]
    candidates = core_three_opt.generate_path_three_opt_candidates(route, -1, 1, 3)
    # B = [A, B], C = [C, D]
    assert ["C", "D", "A", "B"] in candidates
    assert ["D", "C", "B", "A"] in candidates
    assert all(c[0] != "A" for c in candidates), "every arrangement moves the first node"


def test_single_node_segments_give_no_duplicates_and_no_identity():
    route = [0, 1, 2, 3, 4, 5]
    # B = [2], C = [3]: only the swap differs from the identity.
    assert core_three_opt.generate_path_three_opt_candidates(route, 1, 2, 3) == [
        [0, 1, 3, 2, 4, 5]
    ]
    # B = [2], C = [3, 4]: B' == B, so B'C == BC (identity) and B'C' == BC'.
    produced = core_three_opt.generate_path_three_opt_candidates(route, 1, 2, 4)
    tuples = [tuple(c) for c in produced]
    assert len(tuples) == len(set(tuples))
    assert tuple(route) not in tuples
    # Distinct non-identity arrangements: BC', CB, C'B (CB' == CB, C'B' == C'B).
    assert sorted(tuples) == [
        (0, 1, 2, 4, 3, 5), (0, 1, 3, 4, 2, 5), (0, 1, 4, 3, 2, 5),
    ]


def test_every_candidate_is_a_distinct_permutation_for_all_cuts():
    route = [5, 3, 9, 1, 7, 2]
    for i, j, k in _ref_cuts(len(route), None):
        produced = core_three_opt.generate_path_three_opt_candidates(route, i, j, k)
        tuples = [tuple(c) for c in produced]
        assert len(tuples) == len(set(tuples))
        assert tuple(route) not in tuples
        for cand in produced:
            assert sorted(cand) == sorted(route)


def test_candidate_order_is_the_documented_fixed_order():
    route = list(range(8))
    # i=1, j=3, k=5: A = [0, 1], B = [2, 3], C = [4, 5], D = [6, 7]
    expected = [
        [0, 1, 3, 2, 5, 4, 6, 7],  # B'C'
        [0, 1, 3, 2, 4, 5, 6, 7],  # B'C
        [0, 1, 2, 3, 5, 4, 6, 7],  # BC'
        [0, 1, 4, 5, 2, 3, 6, 7],  # CB
        [0, 1, 5, 4, 2, 3, 6, 7],  # C'B
        [0, 1, 4, 5, 3, 2, 6, 7],  # CB'
        [0, 1, 5, 4, 3, 2, 6, 7],  # C'B'
    ]
    assert core_three_opt.generate_path_three_opt_candidates(route, 1, 3, 5) == expected


def test_generator_does_not_modify_its_input():
    route = [4, 2, 7, 1, 9]
    snapshot = list(route)
    core_three_opt.generate_path_three_opt_candidates(route, 0, 2, 3)
    assert route == snapshot


@pytest.mark.parametrize("bad", [(-2, 0, 1), (0, 0, 1), (1, 2, 5), (0, 3, 2)])
def test_invalid_cuts_raise(bad):
    with pytest.raises(ValueError):
        core_three_opt.generate_path_three_opt_candidates(list(range(5)), *bad)


# --------------------------------------------------------------------------
# Cut enumeration and window rule
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 8, 11])
@pytest.mark.parametrize("window", [None, 1, 2, 3, 5, 12])
def test_path_cuts_equal_reference_and_window_rule(n, window):
    produced = list(core_three_opt.iter_path_three_opt_cuts(n, window))
    assert produced == sorted(produced), "cuts must come in lexicographic order"
    assert set(produced) == set(_ref_cuts(n, window))
    if window is not None:
        assert all(j - i <= window and k - j <= window for i, j, k in produced)


@pytest.mark.parametrize("n", [6, 8, 11])
@pytest.mark.parametrize("window", [2, 3, 5])
def test_path_window_bound_equals_the_canonical_rule(n, window):
    """Every cut the canonical (cycle) generator admits is admitted by the path
    generator with the same window, and both use ``j - i <= w``, ``k - j <= w``."""
    path_cuts = set(core_three_opt.iter_path_three_opt_cuts(n, window))
    canonical = set(core_three_opt.iter_three_opt_cuts(n, window))
    assert canonical <= path_cuts
    # The only extra cuts are the ones the cycle form excludes: segments of one
    # node or an empty prefix.
    for i, j, k in path_cuts - canonical:
        assert i == -1 or j - i < 2 or k - j < 2 or n - k + i < 2


# --------------------------------------------------------------------------
# Local search: delegation, best improvement, small routes, acceptance
# --------------------------------------------------------------------------

def test_three_opt_local_search_has_no_private_case_generator():
    assert not hasattr(ThreeOptLocalSearch, "_three_opt_cases")


@pytest.mark.parametrize("size", [2, 3, 5])
def test_three_opt_local_search_never_runs_two_opt(monkeypatch, size):
    def boom(self, route, duration_func):  # pragma: no cover - must not run
        raise AssertionError("2-opt must not run under the 3-opt name")

    monkeypatch.setattr(TwoOptLocalSearch, "improve", boom)
    route = [f"N{idx}" for idx in range(size)]
    out, cost = ThreeOptLocalSearch().improve(route, lambda r: float(len(r)))
    assert sorted(out) == sorted(route)
    assert cost == float(size)


@pytest.mark.parametrize("size", [0, 1, 2, 3])
def test_routes_shorter_than_four_are_returned_unchanged(size):
    route = [f"N{idx}" for idx in range(size)]
    # Heavy nodes late is costly: a 2-opt (reversal) would improve a 3-node route.
    out, cost = ThreeOptLocalSearch().improve(route, lambda r: float(sum(
        pos * int(name[1:]) for pos, name in enumerate(r))))
    assert out == route
    assert cost == float(sum(pos * int(name[1:]) for pos, name in enumerate(route)))


def test_first_position_moves_through_local_search():
    route = ["A", "B", "C", "D", "E"]
    # Cost is the position of "E": the optimum puts it first.
    out, cost = ThreeOptLocalSearch(max_iterations=5).improve(
        route, lambda r: float(r.index("E"))
    )
    assert out[0] == "E"
    assert cost == 0.0


@pytest.mark.parametrize("n", [4, 5, 6, 7])
@pytest.mark.parametrize("seed", range(12))
def test_best_improvement_pass_returns_the_reference_best_move(n, seed):
    objective = _random_objective(n, seed)
    rng = random.Random(1000 + seed)
    route = list(range(1, n + 1))
    rng.shuffle(route)
    start_cost = objective(route)

    neighbours = _ref_all_neighbours(route, window=None)
    best_cost = min(objective(list(c)) for c in neighbours)

    out, cost = ThreeOptLocalSearch(max_iterations=1, window=None).improve(
        list(route), objective
    )
    if best_cost < start_cost:
        assert cost == best_cost
        assert objective(out) == best_cost
        assert tuple(out) in neighbours
    else:
        assert out == route
        assert cost == start_cost


@pytest.mark.parametrize("seed", range(6))
def test_windowed_pass_returns_best_of_windowed_reference(seed):
    n = 9
    objective = _random_objective(n, 50 + seed)
    route = list(range(1, n + 1))
    random.Random(seed).shuffle(route)
    neighbours = _ref_all_neighbours(route, window=2)
    best_cost = min(objective(list(c)) for c in neighbours)
    out, cost = ThreeOptLocalSearch(max_iterations=1, window=2).improve(
        list(route), objective
    )
    if best_cost < objective(route):
        assert cost == best_cost
        assert tuple(out) in neighbours
    else:
        assert out == route


def test_pass_is_best_improvement_not_running_best():
    """The first improving candidate is not the best one: the pass must still
    return the best (no replacement of the scanned route mid-scan)."""
    objective = _random_objective(7, 3)
    route = [3, 1, 4, 7, 2, 6, 5]
    neighbours = _ref_all_neighbours(route, window=None)
    costs = sorted(objective(list(c)) for c in neighbours)
    start = objective(route)
    improving = [c for c in costs if c < start]
    assert len(improving) >= 2, "fixture must have several improving moves"
    _, cost = ThreeOptLocalSearch(max_iterations=1, window=None).improve(
        list(route), objective
    )
    assert cost == improving[0]


def test_equal_cost_candidate_never_replaces_incumbent_and_counts_calls():
    calls: List[Tuple] = []

    def constant(route):
        calls.append(tuple(route))
        return 10.0

    route = list(range(6))
    out, cost = ThreeOptLocalSearch(max_iterations=15, window=None).improve(
        list(route), constant
    )
    assert out == route and cost == 10.0
    # One evaluation of the start route plus one per candidate of the single
    # (non-improving) pass.
    per_cut = sum(
        len(_ref_neighbours(route, i, j, k)) for i, j, k in _ref_cuts(6, None)
    )
    assert len(calls) == 1 + per_cut


def test_first_improvement_takes_a_strict_improvement_in_scan_order():
    objective = _random_objective(7, 11)
    route = [2, 5, 1, 7, 3, 6, 4]
    start = objective(route)
    out, cost = ThreeOptLocalSearch(
        max_iterations=1, first_improvement=True, window=None
    ).improve(list(route), objective)
    assert cost < start
    assert tuple(out) in _ref_all_neighbours(route, window=None)

    # The documented scan order is (i, j, k) lexicographic, candidates in table
    # order; the first strict improvement in that order must be returned.
    expected = None
    for i, j, k in _ref_cuts(len(route), None):
        produced = core_three_opt.generate_path_three_opt_candidates(route, i, j, k)
        for cand in produced:
            if objective(cand) < start:
                expected = cand
                break
        if expected is not None:
            break
    assert out == expected


def test_local_search_improves_to_a_local_optimum_and_returns_exact_cost():
    objective = _random_objective(8, 21)
    route = [8, 7, 6, 5, 4, 3, 2, 1]
    out, cost = ThreeOptLocalSearch(max_iterations=50, window=12).improve(
        list(route), objective
    )
    assert sorted(out) == sorted(route)
    assert cost == objective(out)
    assert cost <= objective(route)
    for neighbour in _ref_all_neighbours(out, window=12):
        assert objective(list(neighbour)) >= cost


def test_local_search_does_not_modify_input_route():
    route = [4, 3, 2, 1, 5]
    snapshot = list(route)
    ThreeOptLocalSearch().improve(route, _random_objective(5, 1))
    assert route == snapshot


def test_core_improve_path_three_opt_result_fields():
    objective = _random_objective(6, 5)
    route = [6, 5, 4, 3, 2, 1]
    result = core_three_opt.improve_path_three_opt(
        route, objective, max_iterations=10, window=12
    )
    assert result.cost == objective(result.route)
    assert 1 <= result.iterations <= 10
    assert result.evaluations >= 1
    assert sorted(result.route) == sorted(route)


# --------------------------------------------------------------------------
# Hybrid keeps its limits
# --------------------------------------------------------------------------

def test_hybrid_three_opt_step_keeps_max_iterations_15_and_window_12(monkeypatch):
    seen: List[Tuple[int, int]] = []
    original_init = ThreeOptLocalSearch.__init__

    def spy(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        seen.append((self.max_iterations, self.window))

    monkeypatch.setattr(ThreeOptLocalSearch, "__init__", spy)
    hybrid = HybridLocalSearch(
        methods=[LocalSearchType.THREE_OPT], max_iterations=1
    )
    hybrid.improve(["A", "B", "C", "D", "E"], lambda r: float(len(r)))
    assert seen and all(entry == (15, 12) for entry in seen)
