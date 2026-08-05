"""Deterministic unit tests for the solver-independent feasibility certificate."""

import numpy as np
import pytest

from uniride_core.algorithms.feasibility_certificate import (
    CAPACITY_VIOLATION,
    DEPOT_CLOSURE,
    DURATION_VIOLATION,
    HARD_VIOLATION,
    MATRIX_SHAPE,
    MISSING_ARC,
    OCCURRENCE_COVERAGE,
    ROUTE_CONTINUITY,
    TIME_WINDOW_VIOLATION,
    FeasibilityCertificate,
    Violation,
    certify_problem_instance,
    certify_routing_result,
    certify_split_result,
    check_capacity_vectors,
    check_depot_closure,
    check_duration,
    check_hard_violation_rejection,
    check_matrix_shape,
    check_missing_arcs,
    check_occurrence_coverage,
    check_route_continuity,
    check_time_windows,
)
from uniride_core.algorithms.split_decoder import SplitResult
from uniride_core.models import (
    ConstraintProfile,
    CostMatrix,
    ProblemInstance,
    RoutingProblem,
    RoutingResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

MATRIX_4 = np.array(
    [
        [0.0, 10.0, 15.0, 20.0],
        [10.0, 0.0, 35.0, 25.0],
        [15.0, 35.0, 0.0, 30.0],
        [20.0, 25.0, 30.0, 0.0],
    ],
    dtype=float,
)

DEMANDS_4 = [[0], [1], [1], [1]]
CAPACITIES_4 = [2]
TIME_WINDOWS_4 = [(0, 200), (0, 100), (0, 100), (0, 100)]
SERVICE_TIMES_4 = [0, 5, 5, 5]


def _problem(**constraint_overrides) -> RoutingProblem:
    defaults = dict(
        demands=DEMANDS_4,
        capacities=CAPACITIES_4,
        time_windows=TIME_WINDOWS_4,
        service_times=SERVICE_TIMES_4,
        depot_index=0,
        max_route_duration=200.0,
    )
    defaults.update(constraint_overrides)
    constraints = ConstraintProfile(**defaults)
    return RoutingProblem(
        name="tiny-cvrptw",
        problem_type="cvrptw",
        matrix=CostMatrix(MATRIX_4, kind="travel_time", occurrence_ids=["depot", "A", "B", "C"]),
        constraints=constraints,
    )


def _valid_result() -> RoutingResult:
    return RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=80.0,
        routes=[[1, 2], [3]],
        num_vehicles=2,
        route_loads=[[2], [1]],
    )


# ── Valid route ───────────────────────────────────────────────────────────────


def test_valid_route_produces_feasible_certificate():
    cert = certify_routing_result(_valid_result(), _problem())
    assert cert.is_feasible is True
    assert cert.violation_count == 0
    assert cert.violations == []


# ── Occurrence coverage ──────────────────────────────────────────────────────


def test_occurrence_coverage_missing_customer():
    violations = check_occurrence_coverage([[1]], dimension=4, depot=0)
    assert len(violations) > 0
    assert all(v.type == OCCURRENCE_COVERAGE for v in violations)
    details = " ".join(v.details for v in violations)
    assert "missing" in details.lower() or "2" in details


def test_occurrence_coverage_duplicate_customer():
    violations = check_occurrence_coverage([[1, 2], [2, 3]], dimension=4, depot=0)
    assert len(violations) > 0
    assert any(v.type == OCCURRENCE_COVERAGE for v in violations)


def test_occurrence_coverage_unexpected_node():
    violations = check_occurrence_coverage([[1, 2, 99]], dimension=4, depot=0)
    assert len(violations) > 0
    assert any(v.type == OCCURRENCE_COVERAGE for v in violations)


def test_occurrence_coverage_with_occurrence_ids():
    violations = check_occurrence_coverage(
        [[1]], dimension=4, depot=0, occurrence_ids=["depot", "A", "B", "C"]
    )
    assert len(violations) > 0
    details = " ".join(v.details for v in violations)
    assert "B" in details or "C" in details


# ── Depot closure ─────────────────────────────────────────────────────────────


def test_depot_closure_empty_route():
    violations = check_depot_closure([[]], depot=0, dimension=4)
    assert len(violations) > 0
    assert all(v.type == DEPOT_CLOSURE for v in violations)


def test_depot_closure_invalid_depot_index():
    violations = check_depot_closure([[1, 2]], depot=99, dimension=4)
    assert len(violations) > 0
    assert any(v.type == DEPOT_CLOSURE for v in violations)


def test_depot_closure_no_routes_with_customers():
    violations = check_depot_closure([], depot=0, dimension=4)
    assert len(violations) > 0
    assert any(v.type == DEPOT_CLOSURE for v in violations)


def test_depot_closure_valid():
    violations = check_depot_closure([[1, 2], [3]], depot=0, dimension=4)
    assert violations == []


# ── Capacity vectors ──────────────────────────────────────────────────────────


def test_capacity_vectors_exceeded():
    violations = check_capacity_vectors([[1, 2, 3]], demands=DEMANDS_4, capacities=[2])
    assert len(violations) > 0
    assert all(v.type == CAPACITY_VIOLATION for v in violations)


def test_capacity_vectors_vector_capacity():
    demands_vec = [[0, 0], [1, 0], [0, 1], [1, 1]]
    violations = check_capacity_vectors([[1, 2, 3]], demands=demands_vec, capacities=[1, 1])
    assert len(violations) > 0
    assert any(v.type == CAPACITY_VIOLATION for v in violations)


def test_capacity_vectors_valid():
    violations = check_capacity_vectors([[1, 2], [3]], demands=DEMANDS_4, capacities=[2])
    assert violations == []


def test_capacity_vectors_none_demands_skips():
    violations = check_capacity_vectors([[1, 2]], demands=None, capacities=[2])
    assert violations == []


# ── Duration ──────────────────────────────────────────────────────────────────


def test_duration_exceeded():
    violations = check_duration(
        [[1, 2, 3]], MATRIX_4, depot=0, max_route_duration=30.0
    )
    assert len(violations) > 0
    assert all(v.type == DURATION_VIOLATION for v in violations)


def test_duration_with_service_times():
    violations = check_duration(
        [[1, 2, 3]], MATRIX_4, depot=0, max_route_duration=100.0,
        service_times=SERVICE_TIMES_4,
    )
    assert len(violations) > 0
    assert all(v.type == DURATION_VIOLATION for v in violations)


def test_duration_valid():
    violations = check_duration(
        [[1, 2], [3]], MATRIX_4, depot=0, max_route_duration=200.0
    )
    assert violations == []


def test_duration_none_limit_skips():
    violations = check_duration([[1, 2, 3]], MATRIX_4, depot=0, max_route_duration=None)
    assert violations == []


# ── Time windows ──────────────────────────────────────────────────────────────


def test_time_windows_violated():
    tight_tw = [(0, 200), (0, 5), (0, 5), (0, 5)]
    violations = check_time_windows(
        [[1, 2, 3]], MATRIX_4, depot=0, time_windows=tight_tw,
        service_times=SERVICE_TIMES_4,
    )
    assert len(violations) > 0
    assert all(v.type == TIME_WINDOW_VIOLATION for v in violations)


def test_time_windows_valid():
    violations = check_time_windows(
        [[1, 2], [3]], MATRIX_4, depot=0, time_windows=TIME_WINDOWS_4,
        service_times=SERVICE_TIMES_4,
    )
    assert violations == []


def test_time_windows_none_skips():
    violations = check_time_windows([[1, 2]], MATRIX_4, depot=0, time_windows=None)
    assert violations == []


# ── Matrix shape ──────────────────────────────────────────────────────────────


def test_matrix_shape_wrong_dimension():
    violations = check_matrix_shape(MATRIX_4, dimension=5)
    assert len(violations) > 0
    assert all(v.type == MATRIX_SHAPE for v in violations)


def test_matrix_shape_non_square():
    bad = np.ones((3, 4))
    violations = check_matrix_shape(bad, dimension=3)
    assert len(violations) > 0
    assert any(v.type == MATRIX_SHAPE for v in violations)


def test_matrix_shape_none():
    violations = check_matrix_shape(None, dimension=4)
    assert len(violations) > 0
    assert any(v.type == MATRIX_SHAPE for v in violations)


def test_matrix_shape_valid():
    violations = check_matrix_shape(MATRIX_4, dimension=4)
    assert violations == []


# ── Missing arcs ──────────────────────────────────────────────────────────────


def test_missing_arcs_inf_value():
    bad_matrix = MATRIX_4.copy()
    bad_matrix[0, 1] = float("inf")
    violations = check_missing_arcs([[1, 2]], bad_matrix, depot=0)
    assert len(violations) > 0
    assert all(v.type == MISSING_ARC for v in violations)


def test_missing_arcs_nan_value():
    bad_matrix = MATRIX_4.copy()
    bad_matrix[2, 3] = float("nan")
    violations = check_missing_arcs([[1, 2, 3]], bad_matrix, depot=0)
    assert len(violations) > 0
    assert any(v.type == MISSING_ARC for v in violations)


def test_missing_arcs_valid():
    violations = check_missing_arcs([[1, 2], [3]], MATRIX_4, depot=0)
    assert violations == []


# ── Route continuity ──────────────────────────────────────────────────────────


def test_route_continuity_invalid_node_index():
    violations = check_route_continuity([[1, 99]], dimension=4)
    assert len(violations) > 0
    assert all(v.type == ROUTE_CONTINUITY for v in violations)


def test_route_continuity_negative_index():
    violations = check_route_continuity([[-1, 2]], dimension=4)
    assert len(violations) > 0
    assert any(v.type == ROUTE_CONTINUITY for v in violations)


def test_route_continuity_intra_route_duplicate():
    violations = check_route_continuity([[1, 1, 2]], dimension=4)
    assert len(violations) > 0
    assert any(v.type == ROUTE_CONTINUITY for v in violations)


def test_route_continuity_valid():
    violations = check_route_continuity([[1, 2], [3]], dimension=4)
    assert violations == []


# ── Hard violation rejection ──────────────────────────────────────────────────


def test_hard_violation_rejection_success_with_violations():
    existing = [Violation(type=CAPACITY_VIOLATION, severity="error", details="over")]
    violations = check_hard_violation_rejection(True, existing)
    assert len(violations) == 1
    assert violations[0].type == HARD_VIOLATION


def test_hard_violation_rejection_success_no_violations():
    violations = check_hard_violation_rejection(True, [])
    assert violations == []


def test_hard_violation_rejection_failure_with_violations():
    existing = [Violation(type=CAPACITY_VIOLATION, severity="error", details="over")]
    violations = check_hard_violation_rejection(False, existing)
    assert violations == []


def test_hard_violation_rejection_none_success():
    existing = [Violation(type=CAPACITY_VIOLATION, severity="error", details="over")]
    violations = check_hard_violation_rejection(None, existing)
    assert violations == []


# ── Adapter: certify_routing_result ──────────────────────────────────────────


def test_certify_routing_result_detects_capacity_violation():
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=100.0,
        routes=[[1, 2, 3]],
        num_vehicles=1,
        capacity_violations=0,
        tw_violations=0,
    )
    cert = certify_routing_result(result, _problem())
    assert cert.is_feasible is False
    assert any(v.type == CAPACITY_VIOLATION for v in cert.violations)


def test_certify_routing_result_hard_violation_inferred():
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=100.0,
        routes=[[1, 2, 3]],
        num_vehicles=1,
        capacity_violations=0,
        tw_violations=0,
    )
    cert = certify_routing_result(result, _problem())
    assert any(v.type == HARD_VIOLATION for v in cert.violations)


def test_certify_routing_result_explicit_success_false():
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=100.0,
        routes=[[1, 2, 3]],
        num_vehicles=1,
        capacity_violations=0,
        tw_violations=0,
    )
    cert = certify_routing_result(result, _problem(), success=False)
    assert not any(v.type == HARD_VIOLATION for v in cert.violations)


def test_certify_routing_result_tour_fallback():
    result = RoutingResult(
        algorithm="test",
        problem_type="tsp",
        objective_cost=50.0,
        routes=[],
        tour=[1, 2, 3],
    )
    problem = _problem(demands=None, capacities=None, time_windows=None,
                       service_times=None, max_route_duration=None)
    cert = certify_routing_result(result, problem)
    assert isinstance(cert, FeasibilityCertificate)


# ── Adapter: certify_split_result ────────────────────────────────────────────


def test_certify_split_result_valid():
    split = SplitResult(
        routes=[[1, 2], [3]],
        total_cost=80.0,
        route_costs=[45.0, 35.0],
        route_loads=[[2], [1]],
    )
    cert = certify_split_result(split, _problem())
    assert cert.is_feasible is True


def test_certify_split_result_capacity_violation():
    split = SplitResult(
        routes=[[1, 2, 3]],
        total_cost=100.0,
        route_costs=[100.0],
        route_loads=[[3]],
        capacity_violations=0,
    )
    cert = certify_split_result(split, _problem())
    assert cert.is_feasible is False
    assert any(v.type == CAPACITY_VIOLATION for v in cert.violations)


# ── Adapter: certify_problem_instance ────────────────────────────────────────


def test_certify_problem_instance_valid():
    instance = ProblemInstance(
        name="tiny",
        dimension=4,
        problem_type="cvrptw",
        is_time_matrix=True,
        time_matrix=MATRIX_4.tolist(),
        demands=[0, 1, 1, 1],
        capacities=[2],
        time_windows=TIME_WINDOWS_4,
        service_times=SERVICE_TIMES_4,
        depot_index=0,
        max_route_duration=200.0,
    )
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=80.0,
        routes=[[1, 2], [3]],
        num_vehicles=2,
    )
    cert = certify_problem_instance(result, instance)
    assert cert.is_feasible is True


def test_certify_problem_instance_detects_violation():
    instance = ProblemInstance(
        name="tiny",
        dimension=4,
        problem_type="cvrptw",
        is_time_matrix=True,
        time_matrix=MATRIX_4.tolist(),
        demands=[0, 1, 1, 1],
        capacities=[1],
        time_windows=TIME_WINDOWS_4,
        service_times=SERVICE_TIMES_4,
        depot_index=0,
        max_route_duration=200.0,
    )
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrptw",
        objective_cost=100.0,
        routes=[[1, 2, 3]],
        num_vehicles=1,
    )
    cert = certify_problem_instance(result, instance)
    assert cert.is_feasible is False
    assert any(v.type == CAPACITY_VIOLATION for v in cert.violations)


def test_certify_problem_instance_uses_dist_matrix():
    instance = ProblemInstance(
        name="tiny",
        dimension=4,
        problem_type="cvrp",
        is_time_matrix=False,
        dist_matrix=MATRIX_4.tolist(),
        demands=[0, 1, 1, 1],
        capacities=[2],
        depot_index=0,
    )
    result = RoutingResult(
        algorithm="test",
        problem_type="cvrp",
        objective_cost=80.0,
        routes=[[1, 2], [3]],
        num_vehicles=2,
    )
    cert = certify_problem_instance(result, instance)
    assert isinstance(cert, FeasibilityCertificate)
