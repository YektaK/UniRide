import pytest

from uniride_core.algorithms.string_exact_tsp import (
    ExactTSPSizeError,
    route_duration,
    solve_exact_tsp_route,
)


def test_solve_exact_tsp_route_finds_best_order():
    durations = {
        ("D", "A"): 1,
        ("D", "B"): 9,
        ("D", "C"): 4,
        ("A", "B"): 1,
        ("A", "C"): 8,
        ("B", "A"): 1,
        ("B", "C"): 1,
        ("C", "A"): 8,
        ("C", "B"): 1,
        ("A", "D"): 1,
        ("B", "D"): 9,
        ("C", "D"): 1,
    }

    route, duration = solve_exact_tsp_route(
        ["A", "B", "C"],
        "D",
        lambda origin, destination: durations[(origin, destination)],
    )

    assert route == ["A", "B", "C"]
    assert duration == 4.0


def test_route_duration_handles_empty_and_singleton_routes():
    assert route_duration([], "D", lambda origin, destination: 99) == 0.0
    route, duration = solve_exact_tsp_route(["A"], "D", lambda origin, destination: 2)

    assert route == ["A"]
    assert duration == 4.0


def test_solve_exact_tsp_route_rejects_oversize_search():
    with pytest.raises(
        ExactTSPSizeError,
        match="3 waypoints exceeds exact-search limit 2",
    ):
        solve_exact_tsp_route(
            ["A", "B", "C"],
            "D",
            lambda origin, destination: 1,
            max_permutation_size=2,
        )


def test_solve_exact_tsp_route_raises_before_any_duration_lookup():
    calls = []

    def tracked_lookup(origin, destination):
        calls.append((origin, destination))
        return 1

    with pytest.raises(ExactTSPSizeError):
        solve_exact_tsp_route(
            ["A", "B", "C", "D"],
            "E",
            tracked_lookup,
            max_permutation_size=2,
        )

    assert calls == []


def test_solve_exact_tsp_route_preserves_behavior_at_and_below_limit():
    route, duration = solve_exact_tsp_route(
        ["A", "B"],
        "D",
        lambda origin, destination: 1,
        max_permutation_size=2,
    )

    assert set(route) == {"A", "B"}
    assert duration == 3.0
