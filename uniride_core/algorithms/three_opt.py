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
import math
import operator
from typing import Callable, Iterable, List, Optional, Sequence, Tuple


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


DEFAULT_ACCEPTANCE_TOLERANCE = 1e-10


def is_improving(
    candidate_cost: float,
    incumbent_cost: float,
    tolerance: float = DEFAULT_ACCEPTANCE_TOLERANCE,
) -> bool:
    """Scale-aware acceptance rule shared by every 3-opt/2-opt/Or-opt controller (N-1).

    A candidate improves the incumbent only when it is cheaper by more than
    ``tolerance * max(1, |incumbent|)``; equal or nearly equal costs never replace it.
    """
    return candidate_cost < incumbent_cost - tolerance * max(1.0, abs(incumbent_cost))


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


def validate_three_opt_window(
    window: object, *, allow_none: bool = True, name: str = "window"
) -> Optional[int]:
    """Return ``window`` as a plain ``int`` or raise a ``ValueError`` naming ``name``.

    The one rule for the canonical 3-opt neighbourhood window: an integer
    (anything ``operator.index`` accepts, so numpy integers pass and ``12.0`` /
    ``12.5`` / strings do not) that is at least 2.  ``None`` means "unrestricted"
    only when ``allow_none`` is true; callers that record the window in a result
    (the academic registry) pass ``allow_none=False``.
    """
    if window is None:
        if allow_none:
            return None
        raise ValueError(f"3-opt {name} must be an integer, got None")
    try:
        value = operator.index(window)  # type: ignore[call-overload]
    except TypeError:
        expected = "None or an integer" if allow_none else "an integer"
        raise ValueError(f"3-opt {name} must be {expected}, got {window!r}") from None
    if value < 2:
        raise ValueError(f"3-opt {name} must be at least 2")
    return value


def iter_three_opt_cuts(n: int, window: Optional[int] = None) -> Iterable[Tuple[int, int, int]]:
    """Yield non-adjacent cut-edge triples in deterministic order.

    A cut index ``i`` denotes the cycle edge ``route[i] -> route[i + 1]``
    (with wraparound).  ``window`` bounds the two forward separations used by
    the historical bounded implementation; it never removes reconnection
    cases from a cut triple that is admitted.
    """
    if n < 6:
        return
    window = validate_three_opt_window(window)

    # Direct generation in the historical lexicographic order (i, then j, then
    # k): only triples that satisfy the separation rules and the window are
    # visited, instead of scanning all C(n, 3) triples and filtering (M25-a).
    max_gap = n if window is None else window
    for i in range(n - 4):
        j_stop = min(i + max_gap, n - 3)
        for j in range(i + 2, j_stop + 1):
            # k < n and the wrap-around segment needs n - k + i >= 2.
            k_stop = min(j + max_gap, n - 1, n + i - 2)
            for k in range(j + 2, k_stop + 1):
                yield i, j, k


def _rotate_to_anchor(route: Sequence[int], anchor: int) -> List[int]:
    idx = route.index(anchor)
    return list(route[idx:]) + list(route[:idx])


# Symmetric reconnection table (M25-b).  For a cut triple the cycle is three
# segments S1 = route[i+1:j+1], S2 = route[j+1:k+1], S3 = route[k+1:] +
# route[:i+1].  Every one of the 48 (segment order, reversal flags)
# arrangements is, as an undirected cycle, equal to exactly one of 8 classes
# (the identity plus 7 reconnections) whenever each segment has at least two
# nodes, which the admitted cuts guarantee.  The historical generator kept the
# first-encountered arrangement per class in (order, flags) iteration order;
# for every class that arrangement has the identity segment order, so the 7
# non-identity classes are the reversal-flag patterns below, with the number of
# undirected edges they change (2 for the three 2-opt equivalents, 3 for the
# four genuine 3-opt edge sets).  Exact parity with the historical generator
# is proven by test_three_opt_candidate_parity.py.
_SYMMETRIC_RECONNECTIONS: Tuple[Tuple[Tuple[bool, bool, bool], int], ...] = (
    ((False, False, True), 2),
    ((False, True, False), 2),
    ((False, True, True), 3),
    ((True, False, False), 2),
    ((True, False, True), 3),
    ((True, True, False), 3),
    ((True, True, True), 3),
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
        # The only non-identity orientation-preserving reconnection is
        # S1 + S3 + S2 (the other cyclic order of the three arcs).
        candidate = segments[0] + segments[2] + segments[1]
        return [_rotate_to_anchor(candidate, anchor)]

    # Same ordering as the historical generator: edges changed first, then the
    # anchor-rotated node sequence.  Lists compare like the former tuples.
    keyed = []
    for flags, edges_changed in _SYMMETRIC_RECONNECTIONS:
        candidate: List[int] = []
        for segment, reverse_segment in zip(segments, flags):
            candidate.extend(reversed(segment) if reverse_segment else segment)
        rotated = _rotate_to_anchor(candidate, anchor)
        keyed.append((edges_changed, rotated))
    keyed.sort()
    return [rotated for _, rotated in keyed]


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
    tolerance: float = DEFAULT_ACCEPTANCE_TOLERANCE,
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
                if is_improving(candidate_cost, selected_cost, tolerance):
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


# ---------------------------------------------------------------------------
# Path 3-opt for production local search (audit M14, MT6-04)
#
# "Path 3-opt, reversals fully costed": a neighbourhood over an OPEN sequence
# whose cost is a caller-supplied black-box objective (for example a Split
# decoded chromosome).  It is a production operator.  It is not the canonical
# cycle neighbourhood above (no matrix, no closing edge, no rotation to an
# anchor, no symmetric/directed mode) and must never be used for paper claims.
# Every candidate, reversed segments included, is costed in full by the
# caller's objective, so it is also valid when reversal is not cost-neutral.
# ---------------------------------------------------------------------------

# Fixed candidate order for one cut.  Each entry is
# (segment C first, reverse B, reverse C): the legacy production case order
# (B'C', B'C, BC', CB, C'B, CB') with the formerly missing C'B' appended; the
# identity BC is not a candidate.
_PATH_ARRANGEMENTS: Tuple[Tuple[bool, bool, bool], ...] = (
    (False, True, True),    # B'C'
    (False, True, False),   # B'C
    (False, False, True),   # BC'
    (True, False, False),   # CB
    (True, False, True),    # C'B
    (True, True, False),    # CB'
    (True, True, True),     # C'B'
)


@dataclass(frozen=True)
class PathThreeOptResult:
    """Result returned by :func:`improve_path_three_opt`."""

    route: list
    cost: float
    iterations: int
    evaluations: int


def iter_path_three_opt_cuts(
    n: int, window: Optional[int] = None
) -> Iterable[Tuple[int, int, int]]:
    """Yield path cuts ``-1 <= i < j < k <= n - 1`` in lexicographic order.

    ``B = route[i + 1:j + 1]`` and ``C = route[j + 1:k + 1]`` are non-empty;
    ``i = -1`` means an empty fixed prefix (the first position can move) and
    ``k = n - 1`` an empty fixed suffix.  ``window`` bounds the two segment
    lengths by the canonical rule ``j - i <= window`` and ``k - j <= window``
    (the same inequalities as :func:`iter_three_opt_cuts`); ``None`` admits
    every cut.
    """
    if window is not None and window < 1:
        raise ValueError("path 3-opt window must be at least 1")
    if n < 2:
        return
    max_gap = n if window is None else window
    for i in range(-1, n - 2):
        for j in range(i + 1, min(i + max_gap, n - 2) + 1):
            for k in range(j + 1, min(j + max_gap, n - 1) + 1):
                yield i, j, k


def generate_path_three_opt_candidates(
    route: Sequence, i: int, j: int, k: int
) -> List[list]:
    """Return the distinct non-identity arrangements of ``(B, C)`` for one cut.

    The seven arrangements (order x reversal) are produced in the fixed order
    ``B'C', B'C, BC', CB, C'B, CB', C'B'`` with ``A`` and ``D`` unchanged.
    A candidate equal (as a sequence) to the input or to an earlier candidate
    of the same cut is dropped: a one-node segment makes ``B' = B`` (or
    ``C' = C``).  Duplicates across different cuts are not removed.
    """
    route_list = list(route)
    n = len(route_list)
    if not (-1 <= i < j < k <= n - 1):
        raise ValueError("path 3-opt cuts must satisfy -1 <= i < j < k <= n - 1")

    prefix = route_list[:i + 1]
    seg_b = route_list[i + 1:j + 1]
    seg_c = route_list[j + 1:k + 1]
    suffix = route_list[k + 1:]

    seen: List[list] = [route_list]
    candidates: List[list] = []
    for c_first, reverse_b, reverse_c in _PATH_ARRANGEMENTS:
        b = seg_b[::-1] if reverse_b else seg_b
        c = seg_c[::-1] if reverse_c else seg_c
        candidate = prefix + (c + b if c_first else b + c) + suffix
        if candidate in seen:
            continue
        seen.append(candidate)
        candidates.append(candidate)
    return candidates


def improve_path_three_opt(
    route: Sequence,
    objective: Callable[[list], float],
    *,
    max_iterations: int = 500,
    first_improvement: bool = False,
    window: Optional[int] = 12,
) -> PathThreeOptResult:
    """Improve an open sequence with path 3-opt costed by ``objective``.

    Acceptance keeps the production semantics: a candidate is taken only if
    its objective is strictly lower than the incumbent's (no tolerance; equal
    or NaN costs never replace it).  ``first_improvement=False`` is a true
    best-improvement pass: every candidate of the pass is compared against the
    best found so far in that pass, and the best (the first of equal costs in
    scan order) replaces the incumbent once at the end of the pass.
    ``first_improvement=True`` takes the first strictly improving candidate in
    (cut, arrangement) order.  ``max_iterations`` bounds complete passes.  The
    objective is evaluated once for the start route and once per candidate.
    """
    if max_iterations < 0:
        raise ValueError("path 3-opt max_iterations must be non-negative")

    current = list(route)
    current_cost = objective(current)
    evaluations = 1
    iterations = 0
    while iterations < max_iterations:
        iterations += 1
        selected: Optional[list] = None
        selected_cost = current_cost
        stop = False
        for i, j, k in iter_path_three_opt_cuts(len(current), window):
            for candidate in generate_path_three_opt_candidates(current, i, j, k):
                candidate_cost = objective(candidate)
                evaluations += 1
                if candidate_cost < selected_cost:
                    selected = candidate
                    selected_cost = candidate_cost
                    if first_improvement:
                        stop = True
                        break
            if stop:
                break
        if selected is None:
            break
        current = selected
        current_cost = selected_cost

    return PathThreeOptResult(current, current_cost, iterations, evaluations)


__all__ = [
    "DEFAULT_ACCEPTANCE_TOLERANCE",
    "PathThreeOptResult",
    "ThreeOptResult",
    "closed_tour_cost",
    "generate_path_three_opt_candidates",
    "generate_three_opt_candidates",
    "improve_path_three_opt",
    "improve_three_opt",
    "is_improving",
    "is_symmetric_matrix",
    "iter_path_three_opt_cuts",
    "iter_three_opt_cuts",
]
