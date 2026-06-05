from __future__ import annotations

from optimizer_api.models import LocationNode, OptimizationRequest, StudentNode
from optimizer_api.strategies.ortools_cvrp import ORToolsCVRPStrategy
from optimizer_api.strategies.pyvrp_strategy import PyVRPAlternativeStrategy, PyVRPStrategy
from uniride_core.algorithms.ortools_cvrp_engine import (
    ORToolsCVRPSolution,
    ORToolsRoutePlan,
    ORToolsRouteStep,
)
from uniride_core.algorithms.pyvrp_cvrp_engine import PyVRPCVRPSolution, PyVRPRoutePlan


def _request(algorithm: str = "ortools_cvrp") -> OptimizationRequest:
    return OptimizationRequest(
        algorithm=algorithm,
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id="student-1",
                location_code="S1",
                coordinates={"lat": 1.0, "lng": 0.0},
                disability_type="Sw",
            ),
            StudentNode(
                id="student-2",
                location_code="S2",
                coordinates={"lat": 2.0, "lng": 0.0},
                disability_type="So",
            ),
        ],
        sw_capacity=2,
        so_capacity=3,
        max_travel_time=90,
    )


def _context():
    time_matrix = {
        "D": {"D": 0, "S1": 5, "S2": 8},
        "S1": {"D": 5, "S1": 0, "S2": 3},
        "S2": {"D": 8, "S1": 3, "S2": 0},
    }
    coordinates = {
        "D": {"lat": 0.0, "lng": 0.0},
        "S1": {"lat": 1.0, "lng": 0.0},
        "S2": {"lat": 2.0, "lng": 0.0},
    }
    return {
        "student_ids": ["S1", "S2"],
        "time_matrix": time_matrix,
        "coordinates": coordinates,
        "distance_lookup": lambda origin, destination: 0.0 if origin == destination else 1.0,
    }


def test_ortools_strategy_delegates_routing_to_core_solver(monkeypatch):
    calls = []
    context = _context()
    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.build_sota_request_context",
        lambda students, depot: context,
    )

    def fake_solve_ortools_cvrp(**kwargs):
        calls.append(kwargs)
        return ORToolsCVRPSolution(
            success=True,
            routes=[
                ORToolsRoutePlan(
                    vehicle_index=1,
                    customer_indices=[0, 1],
                    steps=[
                        ORToolsRouteStep(from_index=0, to_index=1, duration=5.0),
                        ORToolsRouteStep(from_index=1, to_index=2, duration=3.0),
                        ORToolsRouteStep(from_index=2, to_index=0, duration=8.0),
                    ],
                    total_duration=16.0,
                    sw_count=1,
                    so_count=1,
                )
            ],
        )

    monkeypatch.setattr(
        "optimizer_api.strategies.ortools_cvrp.solve_ortools_cvrp",
        fake_solve_ortools_cvrp,
    )

    response = ORToolsCVRPStrategy().optimize(_request())

    assert response.success is True
    assert response.algorithm_used == "ortools_cvrp"
    assert response.total_vehicles == 1
    assert len(calls) == 1
    assert calls[0]["time_matrix"] == [[0, 5, 8], [5, 0, 3], [8, 3, 0]]
    assert calls[0]["disability_types"] == ["Sw", "So"]
    assert calls[0]["sw_capacity"] == 2
    assert calls[0]["so_capacity"] == 3
    assert calls[0]["max_route_duration"] == 90
    assert calls[0]["num_vehicles"] == 2
    assert calls[0]["time_limit_seconds"] == 30


def test_pyvrp_strategy_delegates_routing_to_core_solver(monkeypatch):
    calls = []
    context = _context()
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.build_sota_request_context",
        lambda students, depot: context,
    )

    def fake_solve_pyvrp_cvrp(**kwargs):
        calls.append(kwargs)
        return PyVRPCVRPSolution(
            success=True,
            routes=[PyVRPRoutePlan(vehicle_index=0, customer_indices=[0, 1], sw_count=1, so_count=1)],
        )

    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.solve_pyvrp_cvrp",
        fake_solve_pyvrp_cvrp,
    )

    response = PyVRPStrategy().optimize(_request("pyvrp"))

    assert response.success is True
    assert response.algorithm_used == "pyvrp"
    assert response.total_vehicles == 1
    assert len(calls) == 1
    assert calls[0]["duration_matrix"] == [[0, 5, 8], [5, 0, 3], [8, 3, 0]]
    assert calls[0]["coordinates"] == [
        {"lat": 0.0, "lng": 0.0},
        {"lat": 1.0, "lng": 0.0},
        {"lat": 2.0, "lng": 0.0},
    ]
    assert calls[0]["disability_types"] == ["Sw", "So"]
    assert calls[0]["sw_capacity"] == 2
    assert calls[0]["so_capacity"] == 3
    assert calls[0]["num_vehicles"] == 2
    assert calls[0]["time_limit_seconds"] == 30


def test_pyvrp_alternative_strategy_uses_same_core_solver_path(monkeypatch):
    calls = []
    context = _context()
    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.build_sota_request_context",
        lambda students, depot: context,
    )

    def fake_solve_pyvrp_cvrp(**kwargs):
        calls.append(kwargs)
        return PyVRPCVRPSolution(
            success=True,
            routes=[PyVRPRoutePlan(vehicle_index=0, customer_indices=[1], sw_count=0, so_count=1)],
        )

    monkeypatch.setattr(
        "optimizer_api.strategies.pyvrp_strategy.solve_pyvrp_cvrp",
        fake_solve_pyvrp_cvrp,
    )

    response = PyVRPAlternativeStrategy().optimize(_request("pyvrp_alt"))

    assert response.success is True
    assert response.algorithm_used == "pyvrp_alt"
    assert response.routes[0].vehicle_id == "Araç 1 (PyVRP-Alt)"
    assert len(calls) == 1

