from uniride_core.algorithms.string_greedy_routing import solve_string_greedy_routes


def test_string_greedy_routes_respect_capacity_and_duration():
    durations = {
        ("D", "A"): 2.0,
        ("D", "B"): 3.0,
        ("D", "C"): 5.0,
        ("A", "D"): 2.0,
        ("B", "D"): 3.0,
        ("C", "D"): 5.0,
        ("A", "B"): 2.0,
        ("B", "A"): 2.0,
        ("A", "C"): 6.0,
        ("C", "A"): 6.0,
        ("B", "C"): 2.0,
        ("C", "B"): 2.0,
    }

    routes = solve_string_greedy_routes(
        customer_locations=["A", "B", "C"],
        disability_types={"A": "Sw", "B": "So", "C": "So"},
        depot_id="D",
        duration_lookup=lambda origin, destination: durations[(origin, destination)],
        sw_capacity=1,
        so_capacity=1,
        max_route_duration=11,
    )

    assert [[step.location2 for step in route.steps] for route in routes] == [["A", "B", "D"], ["C", "D"]]
    assert [route.student_locations for route in routes] == [["A", "B"], ["C"]]
    assert [route.total_duration for route in routes] == [7.0, 10.0]
    assert [(route.sw_count, route.so_count) for route in routes] == [(1, 1), (0, 1)]


def test_string_greedy_routes_stops_when_no_customer_is_feasible():
    routes = solve_string_greedy_routes(
        customer_locations=["A"],
        disability_types={"A": "Sw"},
        depot_id="D",
        duration_lookup=lambda origin, destination: 100.0,
        sw_capacity=1,
        so_capacity=1,
        max_route_duration=10,
    )

    assert routes == []
