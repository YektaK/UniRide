import json

from optimizer_api.benchmark_runner import AlgorithmConfig, BenchmarkRunner
from optimizer_api.models.schemas import (
    OptimizationMode,
    OptimizationRequest,
    OptimizationResponse,
    RouteStep,
    TripDirection,
    LocationNode,
    StudentNode,
    VehicleRoute,
)
from optimizer_api.strategies import get_strategy
from optimizer_api.verification.response_certifier import certify_benchmark_response

from uniride_core.algorithms.distance import tsplib_euc_2d_distance
from uniride_core.models import ProblemInstance


def _small_tsp_problem():
    return ProblemInstance(
        name="tiny4",
        dimension=4,
        problem_type="tsp",
        edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
    )


def _benchmark_request(coords):
    depot = LocationNode(id="depot", lat=coords[0][0], lng=coords[0][1])
    students = []
    for i in range(1, len(coords)):
        c = coords[i]
        students.append(StudentNode(
            id=f"student_{i}",
            name=f"Student {i}",
            location_code=f"loc_{i}",
            coordinates={"lat": c[0], "lng": c[1]},
            disability_type="So",
        ))
    return OptimizationRequest(
        algorithm="greedy",
        students=students,
        depot=depot,
        max_travel_time=99999,
        sw_capacity=4,
        so_capacity=4,
        direction=TripDirection.PICKUP,
        use_time_windows=False,
        mode=OptimizationMode.BENCHMARK,
        is_asymmetric=False,
    )


def _make_response(node_key_routes, success=True, algorithm="unit-test"):
    routes = []
    for node_keys in node_key_routes:
        steps = []
        current = "depot"
        for key in node_keys:
            steps.append(RouteStep(location1=current, location2=key, duration=1.0, distance=1.0))
            current = key
        steps.append(RouteStep(location1=current, location2="depot", duration=1.0, distance=1.0))
        routes.append(VehicleRoute(
            vehicle_id=f"V{len(routes) + 1}",
            route_details=steps,
            total_duration_minutes=len(steps) * 1.0,
        ))
    return OptimizationResponse(
        algorithm_used=algorithm,
        success=success,
        routes=routes,
        total_vehicles=len(routes),
        total_duration_minutes=sum(r.total_duration_minutes for r in routes),
    )


class StubStrategy:
    def __init__(self, response):
        self._response = response

    def optimize(self, request):
        return self._response


def test_greedy_tsp_certificate_is_feasible():
    problem = _small_tsp_problem()
    request = _benchmark_request(problem.coordinates)
    response = get_strategy("greedy").optimize(request)

    certificate = certify_benchmark_response(problem, response)

    assert certificate["is_feasible"] is True
    assert certificate["violation_count"] == 0
    assert certificate["violations"] == []


def test_incomplete_directed_matrix_surfaces_missing_arc():
    coords = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    matrix = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            if i != j:
                matrix[i][j] = float(tsplib_euc_2d_distance(coords[i], coords[j]))
    matrix[1][2] = float("nan")

    problem = ProblemInstance(
        name="atsp-incomplete",
        dimension=4,
        problem_type="atsp",
        edge_weight_type="EUC_2D",
        coordinates=coords,
        dist_matrix=matrix,
        is_time_matrix=False,
        depot_index=0,
    )

    response = _make_response([["loc_1", "loc_2", "loc_3"]])
    certificate = certify_benchmark_response(problem, response)

    assert certificate["is_feasible"] is False
    assert certificate["violation_count"] > 0
    types = {v["type"] for v in certificate["violations"]}
    assert "missing_arc" in types


def test_unmappable_location_key_never_raises():
    problem = _small_tsp_problem()
    response = _make_response([["loc_1", "ghost_9", "loc_3"]])

    certificate = certify_benchmark_response(problem, response)

    assert isinstance(certificate, dict)
    assert certificate["is_feasible"] is False
    assert certificate["violation_count"] > 0


def test_runner_metadata_includes_json_serializable_certificate():
    problem = _small_tsp_problem()
    response = _make_response([["loc_1", "loc_2", "loc_3"]])
    runner = BenchmarkRunner(strategies_registry={"stub": StubStrategy(response)})

    result = runner._run_single_experiment(
        problem,
        AlgorithmConfig(name="Stub", algorithm_id="stub", params={}),
        1,
    )

    certificate = result.metadata["feasibility_certificate"]
    assert certificate["is_feasible"] is True
    assert certificate["violation_count"] == 0
    assert isinstance(certificate["violations"], list)
    json.dumps(result.metadata)