"""Mutation-proof: real core solver output at every engine surface.

Each core engine solves a tiny CVRP for real; the unmutated ``RoutingResult``
must certify feasible (control), and every injected mutation of that output
(or of the instance matrix) must make the certificate infeasible. A mutation
surviving certification would let a solver report a hard violation while
claiming a feasible success.
"""

import numpy as np
import pytest

from uniride_core.algorithms.engine_factory import create_matrix_engine
from uniride_core.algorithms.feasibility_certificate import certify_routing_result
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem

try:
    import ortools  # noqa: F401
except ImportError:  # pragma: no cover - CI without OR-Tools
    ortools = None

# ---------------------------------------------------------------------------
# Tiny CVRP: depot 0, customers 1..4, unit demands, capacity 2.
# ---------------------------------------------------------------------------

MATRIX_5 = np.array(
    [
        [0.0, 10.0, 15.0, 20.0, 25.0],
        [10.0, 0.0, 35.0, 25.0, 30.0],
        [15.0, 35.0, 0.0, 30.0, 20.0],
        [20.0, 25.0, 30.0, 0.0, 15.0],
        [25.0, 30.0, 20.0, 15.0, 0.0],
    ],
    dtype=float,
)

DEMANDS_5 = [[0], [1], [1], [1], [1]]
CAPACITIES_5 = [2]


def _problem():
    return RoutingProblem(
        name="tiny-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(
            MATRIX_5.copy(), kind="distance", occurrence_ids=["depot", "A", "B", "C", "D"]
        ),
        constraints=ConstraintProfile(
            demands=DEMANDS_5,
            capacities=CAPACITIES_5,
            depot_index=0,
        ),
    )


# Every canonical core engine surface that solves CVRP.
ENGINE_KEYS = [
    "Core-Greedy-Routing",
    "Core-GA-TSP",
    "Core-PSO-TSP",
    "Core-GWO-TSP",
    "Core-HHO-TSP",
    "OR-Tools",
]


def _skip_if_unavailable(key):
    if key == "OR-Tools" and ortools is None:
        pytest.skip("OR-Tools is not installed")


def _real_result(key):
    return create_matrix_engine(key).solve_problem(_problem())


def _cert(result):
    return certify_routing_result(result, _problem())


@pytest.mark.parametrize("key", ENGINE_KEYS)
def test_engine_output_certifies_feasible(key):
    """Control: unmutated real engine output must certify feasible."""
    _skip_if_unavailable(key)
    result = _real_result(key)
    cert = _cert(result)
    assert cert.is_feasible is True, (key, cert.violations)


@pytest.mark.parametrize("key", ENGINE_KEYS)
def test_engine_missing_node_never_survives(key):
    _skip_if_unavailable(key)
    result = _real_result(key)
    route = max(result.routes, key=len)
    route.pop()
    cert = _cert(result)
    assert cert.is_feasible is False, key


@pytest.mark.parametrize("key", ENGINE_KEYS)
def test_engine_duplicate_node_never_survives(key):
    _skip_if_unavailable(key)
    result = _real_result(key)
    result.routes[0].append(result.routes[0][0])
    cert = _cert(result)
    assert cert.is_feasible is False, key


@pytest.mark.parametrize("key", ENGINE_KEYS)
def test_engine_capacity_overflow_never_survives(key):
    """Move a customer into an already-full route: coverage stays complete
    but the reported route exceeds vehicle capacity."""
    _skip_if_unavailable(key)
    result = _real_result(key)
    fullest = max(result.routes, key=len)
    other = next(r for r in result.routes if r is not fullest and r)
    assert len(fullest) >= 2 and len(fullest) <= CAPACITIES_5[0]
    fullest.append(other.pop())
    cert = _cert(result)
    assert cert.is_feasible is False, key


@pytest.mark.parametrize("key", ENGINE_KEYS)
def test_engine_nonfinite_arc_never_survives(key):
    """Instance-level mutation: a NaN arc actually used by the result's
    routes must not certify."""
    _skip_if_unavailable(key)
    problem = _problem()
    result = create_matrix_engine(key).solve_problem(problem)
    arc = next(
        (a, b) for route in result.routes for a, b in zip(route, route[1:])
    )
    problem.matrix.values[arc[0]][arc[1]] = float("nan")
    cert = certify_routing_result(result, problem)
    assert cert.is_feasible is False, key