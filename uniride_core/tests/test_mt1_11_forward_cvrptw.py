"""MT1-11 / audit H16: Solomon CVRPTW is validated with the forward rules.

Forward rules: leave the depot at its ready time, wait for early windows, serve every
customer, return by the depot due time. The audit scenario (depot window (0, 45),
customers (0, 50), service 10, route [1, 2] returns at 54.14) must be infeasible on every
path: split path, certificates and dashboard. A Solomon smoke test checks that the split
path and the certificate agree with the holistic counter
(``holistic_matrix_engine._time_window_violations``).
"""
from __future__ import annotations

import itertools

import pytest

from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.base_engine import StaticPermutationEngine
from uniride_core.algorithms.feasibility_certificate import (
    TIME_WINDOW_VIOLATION,
    certify_problem_instance,
    certify_routing_result,
    certify_split_result,
)
from uniride_core.algorithms.holistic_matrix_engine import _time_window_violations
from uniride_core.algorithms.split_decoder import (
    split_with_time_windows_result,
    validate_cvrptw_solution,
)
from uniride_core.models import ConstraintProfile, RoutingProblem, RoutingResult

AUDIT_SCENARIO = """
H16
VEHICLE
NUMBER     CAPACITY
2          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           45        0
1         10       0        1       0           50        10
2         10       10       1       0           50        10
"""

# Five customers with windows tight enough that some orders are late and some are not.
SMOKE = """
SMOKE5
VEHICLE
NUMBER     CAPACITY
3          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           120         0
1         10       0        2       0           30          5
2         10       10       2       15          45          5
3         0        10       2       40          70          5
4         -10      10       2       0           60          5
5         -10      0        2       50          100         5
"""


def _audit_problem() -> RoutingProblem:
    return MatrixBuilder.from_solomon_text(AUDIT_SCENARIO)


def _split(problem: RoutingProblem, permutation):
    c = problem.constraints
    return split_with_time_windows_result(
        permutation, problem.matrix.values, c.demands, c.capacities, c.time_windows,
        c.service_times, depot=c.depot_index, max_route_duration=c.max_route_duration,
        direction=c.direction, target_time=c.target_time, offset_minutes=c.offset_minutes,
    )


def test_return_time_of_the_audit_scenario_is_past_the_depot_due_time():
    problem = _audit_problem()
    dm = problem.matrix.values
    end = dm[0, 1] + 10 + dm[1, 2] + 10 + dm[2, 0]
    assert end == pytest.approx(34.1421356 + 20, abs=1e-6)
    assert end > problem.constraints.time_windows[0][1]


def test_default_profile_for_other_callers_stays_pickup():
    assert ConstraintProfile().direction == "pickup"


def test_split_path_counts_the_late_depot_return():
    problem = _audit_problem()
    split = _split(problem, [1, 2])
    assert split.routes == [[1, 2]]
    assert split.tw_violations == 1
    assert _time_window_violations(split.routes, problem.matrix.values, problem) == 1


def test_engine_solve_problem_reports_the_violation():
    problem = _audit_problem()
    result = StaticPermutationEngine([1, 2]).solve_problem(problem, seed=1)
    assert result.routes == [[1, 2]]
    assert result.tw_violations == 1


def test_validate_cvrptw_solution_rejects_the_late_return():
    problem = _audit_problem()
    c = problem.constraints
    ok, errors = validate_cvrptw_solution(
        [[1, 2]], problem.matrix.values, c.demands, c.capacities, c.time_windows,
        c.service_times, depot=c.depot_index, direction=c.direction,
    )
    assert not ok
    assert any("time-window" in e for e in errors)


def test_certificate_for_problem_instance_is_infeasible():
    problem = _audit_problem()
    instance = MatrixBuilder.to_problem_instance(problem)
    result = RoutingResult(
        algorithm="t", problem_type="CVRPTW", objective_cost=34.14, routes=[[1, 2]],
        tw_violations=0,  # the old split path claimed 0
    )
    cert = certify_problem_instance(result, instance, success=True)
    assert not cert.is_feasible
    assert any(v.type == TIME_WINDOW_VIOLATION for v in cert.violations)


def test_certificate_for_routing_problem_and_split_result_is_infeasible():
    problem = _audit_problem()
    result = RoutingResult(
        algorithm="t", problem_type="CVRPTW", objective_cost=34.14, routes=[[1, 2]],
    )
    assert not certify_routing_result(result, problem).is_feasible
    split = _split(problem, [1, 2])
    split.tw_violations = 0  # a stale count must not make the certificate pass
    assert not certify_split_result(split, problem).is_feasible


def test_route_back_in_time_is_certified_feasible():
    problem = _audit_problem()
    problem.constraints.time_windows[0] = (0, 60)  # return at 54.14 is now on time
    instance = MatrixBuilder.to_problem_instance(problem)
    result = RoutingResult(
        algorithm="t", problem_type="CVRPTW", objective_cost=34.14, routes=[[1, 2]],
    )
    assert certify_problem_instance(result, instance).is_feasible


def test_early_arrival_waits_and_is_not_a_violation():
    problem = _audit_problem()
    problem.constraints.time_windows[1] = (20, 50)  # arrive 10, wait 10
    problem.constraints.time_windows[0] = (0, 60)
    # the wait pushes the return to 64.14 > 60 -> late; with 70 it is on time
    result = RoutingResult(algorithm="t", problem_type="CVRPTW", objective_cost=0, routes=[[1, 2]])
    assert not certify_routing_result(result, problem).is_feasible
    problem.constraints.time_windows[0] = (0, 70)
    assert certify_routing_result(result, problem).is_feasible


def test_depot_ready_time_is_the_departure_time():
    problem = _audit_problem()
    problem.constraints.time_windows[0] = (30, 200)
    problem.constraints.time_windows[1] = (0, 35)  # leaving at 30 arrives at 40 > 35
    result = RoutingResult(algorithm="t", problem_type="CVRPTW", objective_cost=0, routes=[[1, 2]])
    assert not certify_routing_result(result, problem).is_feasible
    assert _time_window_violations([[1, 2]], problem.matrix.values, problem) >= 1


def test_solomon_smoke_split_path_and_certificate_agree_with_the_holistic_counter():
    problem = MatrixBuilder.from_solomon_text(SMOKE)
    assert problem.constraints.direction == "forward_tw"
    instance = MatrixBuilder.to_problem_instance(problem)
    seen = set()
    for permutation in itertools.permutations(range(1, 6)):
        split = _split(problem, list(permutation))
        holistic = _time_window_violations(split.routes, problem.matrix.values, problem)
        assert split.tw_violations == holistic, (permutation, split.routes)
        result = RoutingResult(
            algorithm="t", problem_type="CVRPTW", objective_cost=split.total_cost,
            routes=split.routes, tw_violations=split.tw_violations,
        )
        cert = certify_problem_instance(result, instance)
        assert cert.is_feasible == (holistic == 0), (permutation, split.routes)
        seen.add(holistic == 0)
    assert seen == {True, False}, "smoke instance must contain feasible and infeasible orders"
