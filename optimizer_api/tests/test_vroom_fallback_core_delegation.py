from __future__ import annotations

from optimizer_api.models import OptimizationRequest
from optimizer_api.strategies.vroom_strategy import VROOMFallbackStrategy
from uniride_core.algorithms.vroom_cvrp_engine import VROOMRoutePlan


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


def test_vroom_fallback_strategy_delegates_to_core_sweep_solver(monkeypatch):
    calls = []
    request = _request()
    context = {
        "student_ids": ["A", "B"],
        "location_ids": ["D", "A", "B"],
        "duration_matrix": [
            [0, 5, 8],
            [5, 0, 3],
            [8, 3, 0],
        ],
        "coordinates": {
            "D": {"lat": 0.0, "lng": 0.0},
            "A": {"lat": 1.0, "lng": 0.0},
            "B": {"lat": 2.0, "lng": 0.0},
        },
        "coordinates_list": [
            {"lat": 0.0, "lng": 0.0},
            {"lat": 1.0, "lng": 0.0},
            {"lat": 2.0, "lng": 0.0},
        ],
        "time_matrix": {
            "D": {"D": 0, "A": 5, "B": 8},
            "A": {"D": 5, "A": 0, "B": 3},
            "B": {"D": 8, "A": 3, "B": 0},
        },
        "distance_lookup": lambda origin, destination: 0.0 if origin == destination else 1.0,
    }

    monkeypatch.setattr(
        "optimizer_api.strategies.vroom_strategy._build_vroom_context",
        lambda passed_request: context,
    )

    def fake_solve_sweep_fallback_routes(**kwargs):
        calls.append(kwargs)
        return [
            VROOMRoutePlan(
                vehicle_index=0,
                customer_indices=[0],
                sw_count=1,
                so_count=0,
            ),
            VROOMRoutePlan(
                vehicle_index=1,
                customer_indices=[1],
                sw_count=0,
                so_count=1,
            ),
        ]

    monkeypatch.setattr(
        "optimizer_api.strategies.vroom_strategy.solve_sweep_fallback_routes",
        fake_solve_sweep_fallback_routes,
    )

    response = VROOMFallbackStrategy().optimize(request)

    assert response.success is True
    assert response.algorithm_used == "vroom_fallback"
    assert response.total_vehicles == 2
    assert len(calls) == 1
    assert calls[0]["customer_indices"] == [0, 1]
    assert calls[0]["coordinates"] == context["coordinates_list"]
    assert calls[0]["disability_types"] == ["Sw", "So"]
    assert calls[0]["depot_index"] == 0
    assert calls[0]["duration_lookup"](1, 2) == 3
    assert calls[0]["sw_capacity"] == 1
    assert calls[0]["so_capacity"] == 1
    assert calls[0]["max_route_duration"] == 120
