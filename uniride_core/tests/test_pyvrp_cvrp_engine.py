from uniride_core.algorithms.pyvrp_cvrp_engine import solve_pyvrp_cvrp


def test_solve_pyvrp_cvrp_returns_capacity_feasible_routes():
    solution = solve_pyvrp_cvrp(
        duration_matrix=[
            [0, 2, 3],
            [2, 0, 1],
            [3, 1, 0],
        ],
        coordinates=[
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
            {"lat": 0, "lng": 2},
        ],
        disability_types=["Sw", "So"],
        sw_capacity=1,
        so_capacity=1,
        num_vehicles=2,
        time_limit_seconds=1,
    )

    assert solution.success is True
    visited = sorted(idx for route in solution.routes for idx in route.customer_indices)
    assert visited == [0, 1]
    assert all(route.sw_count <= 1 for route in solution.routes)
    assert all(route.so_count <= 1 for route in solution.routes)


def test_solve_pyvrp_cvrp_reports_infeasible_problem():
    solution = solve_pyvrp_cvrp(
        duration_matrix=[
            [0, 2],
            [2, 0],
        ],
        coordinates=[
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        ],
        disability_types=["Sw"],
        sw_capacity=0,
        so_capacity=1,
        num_vehicles=1,
        time_limit_seconds=1,
    )

    assert solution.success is False
    assert solution.error_message


def test_solve_pyvrp_cvrptw_enforces_time_windows():
    solution = solve_pyvrp_cvrp(
        duration_matrix=[
            [0, 10],
            [10, 0],
        ],
        coordinates=[
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        ],
        demand_vectors=[[0], [1]],
        capacities=[1],
        time_windows=[(0, 100), (0, 5)],
        service_times=[0, 0],
        max_route_duration=100,
        num_vehicles=1,
        time_limit_seconds=1,
    )

    assert solution.success is False
    assert solution.error_message


def test_solve_pyvrp_cvrptw_allows_waiting_for_ready_time():
    solution = solve_pyvrp_cvrp(
        duration_matrix=[
            [0, 5],
            [5, 0],
        ],
        coordinates=[
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        ],
        demand_vectors=[[0], [1]],
        capacities=[1],
        time_windows=[(0, 100), (10, 20)],
        service_times=[0, 0],
        max_route_duration=100,
        num_vehicles=1,
        time_limit_seconds=1,
    )

    assert solution.success is True
    assert [route.customer_indices for route in solution.routes] == [[0]]
