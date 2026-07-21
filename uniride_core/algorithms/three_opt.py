"""Canonical matrix-native 3-opt neighborhoods for TSP and ATSP.

Symmetric TSP and directed ATSP require different reconnection semantics.
For symmetric matrices, reversing a path preserves its internal undirected
edges, so the seven classical non-identity reconnections are admissible.  For
directed matrices, path orientation is preserved and only directed three-arc
exchanges that form one Hamiltonian cycle are generated.

This module is intentionally correctness-first.  Legacy Numba entry points
delegate here until a separately tested JIT implementation proves semantic
parity with these neighborhoods.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations, product
import math
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ThreeOptResult:
    """Result returned by :func:`improve_three_opt`."""

    route: List[int]
    cost: float
    iterations: int
    evaluations: int
    mode: str


def closed_tour_cost(route: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
    """Return the complete last-to-first matrix cost of ``route``."""
    if not route:
        return 0.0
    return sum(
        float(matrix[node][route[(idx + 1) % len(route)]])
        for idx, node in enumerate(route)
    )


def is_symmetric_matrix(
    matrix: Sequence[Sequence[float]],
    *,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-12,
) -> bool:
    """Return whether a square matrix is symmetric within tolerance."""
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if not math.isclose(
                float(matrix[i][j]),
                float(matrix[j][i]),
                rel_tol=rel_tol,
                abs_tol=abs_tol,
            ):
                return False
    return True


def iter_three_opt_cuts(n: int, window: Optional[int] = None) -> Iterable[Tuple[int, int, int]]:
    """Yield non-adjacent cut-edge triples in deterministic order.

    A cut index ``i`` denotes the cycle edge ``route[i] -> route[i + 1]``
    (with wraparound).  ``window`` bounds the two forward separations used by
    the historical bounded implementation; it never removes reconnection
    cases from a cut triple that is admitted.
    """
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


def _rotate_to_anchor(route: Sequence[int], anchor: int) -> List[int]:
    idx = route.index(anchor)
    return list(route[idx:]) + list(route[:idx])


def _directed_cycle_key(route: Sequence[int]) -> Tuple[int, ...]:
    values = tuple(route)
    return min(values[idx:] + values[:idx] for idx in range(len(values)))


def _symmetric_cycle_key(route: Sequence[int]) -> Tuple[int, ...]:
    values = tuple(route)
    reverse = tuple(reversed(values))
    rotations = [values[idx:] + values[:idx] for idx in range(len(values))]
    rotations.extend(reverse[idx:] + reverse[:idx] for idx in range(len(reverse)))
    return min(rotations)


def _undirected_edges(route: Sequence[int]) -> frozenset[frozenset[int]]:
    return frozenset(
        frozenset((node, route[(idx + 1) % len(route)]))
        for idx, node in enumerate(route)
    )


def generate_three_opt_candidates(
    route: Sequence[int],
    i: int,
    j: int,
    k: int,
    *,
    directed: bool,
) -> List[List[int]]:
    """Generate the complete non-identity neighborhood for one cut triple.

    Symmetric mode returns the seven classical reconnections (three
    2-opt-equivalent and four genuine 3-opt edge sets).  Directed mode returns
    the single non-identity orientation-preserving three-arc reconnection.
    """
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
        original_key = _directed_cycle_key(route_list)
        candidates = {}
        for order in permutations(range(3)):
            candidate = [node for segment_idx in order for node in segments[segment_idx]]
            key = _directed_cycle_key(candidate)
            if key != original_key:
                candidates.setdefault(key, _rotate_to_anchor(candidate, anchor))
        return [candidates[key] for key in sorted(candidates)]

    original_key = _symmetric_cycle_key(route_list)
    original_edges = _undirected_edges(route_list)
    candidates = {}
    for order in permutations(range(3)):
        for reversed_flags in product((False, True), repeat=3):
            candidate: List[int] = []
            for segment_idx, reverse_segment in zip(order, reversed_flags):
                segment = segments[segment_idx]
                candidate.extend(reversed(segment) if reverse_segment else segment)
            key = _symmetric_cycle_key(candidate)
            if key != original_key:
                candidates.setdefault(key, _rotate_to_anchor(candidate, anchor))

    ordered = list(candidates.values())
    ordered.sort(
        key=lambda candidate: (
            len(original_edges - _undirected_edges(candidate)),
            tuple(candidate),
        )
    )
    return ordered


def _validate_problem(route: Sequence[int], matrix: Sequence[Sequence[float]]) -> None:
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("3-opt requires a square matrix")
    if len(route) != n:
        raise ValueError("3-opt route length must equal matrix dimension")
    if len(set(route)) != n or set(route) != set(range(n)):
        raise ValueError("3-opt route must be a permutation of matrix indices 0..n-1")


def improve_three_opt(
    route: Sequence[int],
    matrix: Sequence[Sequence[float]],
    *,
    max_iterations: int = 500,
    first_improvement: bool = False,
    window: Optional[int] = 12,
    directed: Optional[bool] = None,
    tolerance: float = 1e-10,
) -> ThreeOptResult:
    """Improve a Hamiltonian cycle using canonical symmetric/directed 3-opt."""
    _validate_problem(route, matrix)
    if max_iterations < 0:
        raise ValueError("3-opt max_iterations must be non-negative")
    if tolerance < 0:
        raise ValueError("3-opt tolerance must be non-negative")

    matrix_is_symmetric = is_symmetric_matrix(matrix)
    if directed is None:
        directed = not matrix_is_symmetric
    elif not directed and not matrix_is_symmetric:
        raise ValueError("symmetric 3-opt cannot be used with an asymmetric matrix")

    current = list(route)
    current_cost = closed_tour_cost(current, matrix)
    mode = "directed_atsp" if directed else "symmetric_tsp"
    if len(current) < 6 or max_iterations == 0:
        return ThreeOptResult(current, current_cost, 0, 0, mode)

    iterations = 0
    evaluations = 0
    while iterations < max_iterations:
        iterations += 1
        selected_route: Optional[List[int]] = None
        selected_cost = current_cost

        stop = False
        for i, j, k in iter_three_opt_cuts(len(current), window):
            candidates = generate_three_opt_candidates(
                current, i, j, k, directed=bool(directed)
            )
            for candidate in candidates:
                candidate_cost = closed_tour_cost(candidate, matrix)
                evaluations += 1
                threshold = tolerance * max(1.0, abs(selected_cost))
                if candidate_cost < selected_cost - threshold:
                    selected_route = candidate
                    selected_cost = candidate_cost
                    if first_improvement:
                        stop = True
                        break
            if stop:
                break

        if selected_route is None:
            break
        current = selected_route
        current_cost = selected_cost

    return ThreeOptResult(current, current_cost, iterations, evaluations, mode)


__all__ = [
    "ThreeOptResult",
    "closed_tour_cost",
    "generate_three_opt_candidates",
    "improve_three_opt",
    "is_symmetric_matrix",
    "iter_three_opt_cuts",
]
