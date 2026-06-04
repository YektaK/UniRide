from __future__ import annotations

from optimizer_api.strategies.permutation_tsp import PermutationTSPStrategy


def test_permutation_tsp_strategy_delegates_exact_search_to_core(monkeypatch):
    calls = []
    strategy = PermutationTSPStrategy()
    time_matrix = {
        "D": {"D": 0, "A": 5, "B": 8},
        "A": {"D": 5, "A": 0, "B": 3},
        "B": {"D": 8, "A": 3, "B": 0},
    }

    def fake_solve_exact_tsp_route(waypoints, depot, duration_lookup, *, max_permutation_size):
        calls.append({
            "waypoints": waypoints,
            "depot": depot,
            "max_permutation_size": max_permutation_size,
            "duration_ab": duration_lookup("A", "B"),
        })
        return ["B", "A"], 16.0

    monkeypatch.setattr(
        "optimizer_api.strategies.permutation_tsp.solve_exact_tsp_route",
        fake_solve_exact_tsp_route,
    )

    route, duration = strategy._solve_tsp_optimal(
        ["A", "B"],
        "D",
        time_matrix,
        coordinates={},
    )

    assert route == ["B", "A"]
    assert duration == 16.0
    assert calls == [
        {
            "waypoints": ["A", "B"],
            "depot": "D",
            "max_permutation_size": strategy.MAX_PERMUTATION_SIZE,
            "duration_ab": 3,
        }
    ]
