from __future__ import annotations

from itertools import permutations, product

import pytest

from uniride_core.algorithms.three_opt import (
    closed_tour_cost,
    generate_three_opt_candidates,
    improve_three_opt,
    is_symmetric_matrix,
    iter_three_opt_cuts,
)


def _cycle_key(route, symmetric):
    route = tuple(route)
    rotations = [route[i:] + route[:i] for i in range(len(route))]
    if symmetric:
        reverse = tuple(reversed(route))
        rotations.extend(reverse[i:] + reverse[:i] for i in range(len(route)))
    return min(rotations)


def _reference_candidates(route, i, j, k, directed):
    """Independent exhaustive segment reconnection enumerator."""
    segments = (
        route[i + 1:j + 1],
        route[j + 1:k + 1],
        route[k + 1:] + route[:i + 1],
    )
    original_key = _cycle_key(route, symmetric=not directed)
    keys = set()
    reversal_options = ((False, False, False),) if directed else product((False, True), repeat=3)
    reversal_options = tuple(reversal_options)
    for order in permutations(range(3)):
        for flags in reversal_options:
            candidate = []
            for segment_idx, reverse_segment in zip(order, flags):
                segment = segments[segment_idx]
                candidate.extend(reversed(segment) if reverse_segment else segment)
            key = _cycle_key(candidate, symmetric=not directed)
            if key != original_key:
                keys.add(key)
    return keys


def _undirected_edges(route):
    return {
        frozenset((node, route[(idx + 1) % len(route)]))
        for idx, node in enumerate(route)
    }


def _directed_edges(route):
    return {
        (node, route[(idx + 1) % len(route)])
        for idx, node in enumerate(route)
    }


def _matrix_for_preferred_cycle(preferred, default=50.0):
    n = len(preferred)
    matrix = [[0.0 if i == j else default for j in range(n)] for i in range(n)]
    for idx, node in enumerate(preferred):
        matrix[node][preferred[(idx + 1) % n]] = 1.0
    return matrix


def test_symmetric_neighborhood_matches_reference_and_has_four_genuine_moves():
    route = list(range(6))
    candidates = generate_three_opt_candidates(route, 0, 2, 4, directed=False)
    actual_keys = {_cycle_key(candidate, symmetric=True) for candidate in candidates}

    assert actual_keys == _reference_candidates(route, 0, 2, 4, directed=False)
    assert len(candidates) == 7

    original_edges = _undirected_edges(route)
    edge_changes = [len(original_edges - _undirected_edges(candidate)) for candidate in candidates]
    assert edge_changes.count(2) == 3
    assert edge_changes.count(3) == 4


def test_directed_neighborhood_matches_reference_and_preserves_internal_arcs():
    route = list(range(6))
    candidates = generate_three_opt_candidates(route, 0, 2, 4, directed=True)
    actual_keys = {_cycle_key(candidate, symmetric=False) for candidate in candidates}

    assert actual_keys == _reference_candidates(route, 0, 2, 4, directed=True)
    assert len(candidates) == 1
    candidate_edges = _directed_edges(candidates[0])
    assert {(1, 2), (3, 4), (5, 0)}.issubset(candidate_edges)


def test_directed_optimizer_uses_exact_asymmetric_closed_cycle_and_is_deterministic():
    route = list(range(6))
    preferred = [0, 3, 4, 1, 2, 5]
    matrix = _matrix_for_preferred_cycle(preferred)
    assert not is_symmetric_matrix(matrix)

    first = improve_three_opt(route, matrix, max_iterations=10, window=12)
    second = improve_three_opt(route, matrix, max_iterations=10, window=12)

    assert first.mode == "directed_atsp"
    assert first.route == preferred
    assert first.cost == pytest.approx(closed_tour_cost(first.route, matrix))
    assert first == second


def test_symmetric_optimizer_uses_complete_permutation_and_exact_cost():
    route = list(range(6))
    preferred = [0, 2, 1, 4, 3, 5]
    directed_matrix = _matrix_for_preferred_cycle(preferred)
    matrix = [
        [min(directed_matrix[i][j], directed_matrix[j][i]) for j in range(6)]
        for i in range(6)
    ]
    assert is_symmetric_matrix(matrix)

    result = improve_three_opt(route, matrix, max_iterations=10, window=12)

    assert result.mode == "symmetric_tsp"
    assert set(result.route) == set(route)
    assert result.cost == pytest.approx(closed_tour_cost(result.route, matrix))
    assert result.cost <= closed_tour_cost(route, matrix)


def test_window_bounds_cut_selection_without_reducing_case_coverage():
    route = list(range(8))
    cuts = list(iter_three_opt_cuts(len(route), window=2))

    assert cuts
    for i, j, k in cuts:
        assert j - i <= 2
        assert k - j <= 2
        assert len(generate_three_opt_candidates(route, i, j, k, directed=False)) == 7
        assert len(generate_three_opt_candidates(route, i, j, k, directed=True)) == 1


def test_small_and_invalid_inputs_follow_contract():
    small_route = [0, 1, 2, 3, 4]
    small_matrix = [[0.0 if i == j else 1.0 for j in range(5)] for i in range(5)]
    result = improve_three_opt(small_route, small_matrix)
    assert result.route == small_route
    assert result.iterations == 0
    assert result.evaluations == 0

    asymmetric = _matrix_for_preferred_cycle(list(range(6)))
    with pytest.raises(ValueError, match="symmetric 3-opt"):
        improve_three_opt(list(range(6)), asymmetric, directed=False)
    with pytest.raises(ValueError, match="square matrix"):
        improve_three_opt([0, 1], [[0.0, 1.0], [1.0]])
    with pytest.raises(ValueError, match="permutation"):
        improve_three_opt([0, 0], [[0.0, 1.0], [1.0, 0.0]])
