from __future__ import annotations

from optimizer_api.models import OptimizationRequest
from optimizer_api.strategies.greedy_heuristic import GreedyHeuristicStrategy
from uniride_core.algorithms.string_greedy_routing import GreedyRoutePlan, GreedyRouteStep


def _request() -> OptimizationRequest:
    return OptimizationRequest(
        depot="D",
        locations=["A", "B"],
        distance_matrix={
            "D": {"D": 0, "A": 5, "B": 8},
            "A": {"D": 5, "A": 0, "B": 3},
            "B": {"D": 8, "A": 3, "B": 0},
        },
        demands={"A": (1, 0), "B": (0, 1)},
        sw_capacity=1,
        so_capacity=1,
        max_travel_time=120,
    )


def test_greedy_strategy_delegates_to_core_solver(monkeypatch):
    calls = []
    request = _request()
    context = {
        "student_ids": ["A", "B"],
        "coordinates": {
            "D": {"lat": 0.0, "lng": 0.0},
            "A": {"lat": 1.0, "lng": 0.0},
            "B": {"lat": 2.0, "lng": 0.0},
        },
        "time_matrix": {
            "D": {"D": 0, "A": 5, "B": 8},
            "A": {"D": 5, "A": 0, "B": 3},
            "B": {"D": 8, "A": 3, "B": 0},
        },
        "distance_lookup": lambda origin, destination: 0.0 if origin == destination else 1.0,
    }

    monkeypatch.setattr(
        "optimizer_api.strategies.greedy_heuristic.build_sota_request_context",
        lambda students, depot: context,
    )

    def fake_solve_string_greedy_routes(**kwargs):
        calls.append(kwargs)
        return [
            GreedyRoutePlan(
                steps=[
                    GreedyRouteStep(location1="D", location2="A", duration=5.0),
                    GreedyRouteStep(location1="A", location2="D", duration=5.0),
                ],
                student_locations=["A"],
                total_duration=10.0,
                sw_count=1,
                so_count=0,
            ),
            GreedyRoutePlan(
                steps=[
                    GreedyRouteStep(location1="D", location2="B", duration=8.0),
                    GreedyRouteStep(location1="B", location2="D", duration=8.0),
                ],
                student_locations=["B"],
                total_duration=16.0,
                sw_count=0,
                so_count=1,
            ),
        ]

    monkeypatch.setattr(
        "optimizer_api.strategies.greedy_heuristic.solve_string_greedy_routes",
        fake_solve_string_greedy_routes,
    )

    response = GreedyHeuristicStrategy().optimize(request)

    assert response.success is True
    assert response.algorithm_used == "greedy"
    assert response.total_vehicles == 2
    assert len(calls) == 1
    assert calls[0]["customer_locations"] == ["A", "B"]
    assert calls[0]["disability_types"] == {"A": "Sw", "B": "So"}
    assert calls[0]["depot_id"] == "D"
    assert calls[0]["duration_lookup"]("A", "B") == 3
    assert calls[0]["sw_capacity"] == 1
    assert calls[0]["so_capacity"] == 1
    assert calls[0]["max_route_duration"] == 120
