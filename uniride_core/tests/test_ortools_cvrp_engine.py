from uniride_core.algorithms.ortools_cvrp_engine import solve_ortools_cvrp


def test_solve_ortools_cvrp_returns_capacity_feasible_routes():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 2, 3, 4],
            [2, 0, 1, 5],
            [3, 1, 0, 2],
            [4, 5, 2, 0],
        ],
        disability_types=["Sw", "So", "So"],
        sw_capacity=1,
        so_capacity=2,
        max_route_duration=20,
        num_vehicles=3,
        time_limit_seconds=1,
    )

    assert solution.success is True
    visited = sorted(idx for route in solution.routes for idx in route.customer_indices)
    assert visited == [0, 1, 2]
    assert all(route.sw_count <= 1 for route in solution.routes)
    assert all(route.so_count <= 2 for route in solution.routes)


def test_solve_ortools_cvrp_reports_infeasible_problem():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 2],
            [2, 0],
        ],
        disability_types=["Sw"],
        sw_capacity=0,
        so_capacity=1,
        max_route_duration=20,
        num_vehicles=1,
        time_limit_seconds=1,
    )

    assert solution.success is False
    assert solution.error_message


def test_solve_ortools_cvrptw_enforces_time_windows():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 10],
            [10, 0],
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


def test_solve_ortools_cvrptw_allows_waiting_for_ready_time():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 5],
            [5, 0],
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


def test_solve_ortools_cvrp_accepts_search_strategy_names():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 2, 3],
            [2, 0, 1],
            [3, 1, 0],
        ],
        demand_vectors=[[0], [1], [1]],
        capacities=[2],
        max_route_duration=20,
        num_vehicles=1,
        time_limit_seconds=1,
        first_solution_strategy="parallel_cheapest_insertion",
        local_search_metaheuristic="guided_local_search",
    )

    assert solution.success is True
    assert sorted(idx for route in solution.routes for idx in route.customer_indices) == [0, 1]


def test_solve_ortools_cvrp_reports_invalid_search_strategy_name():
    solution = solve_ortools_cvrp(
        time_matrix=[
            [0, 2],
            [2, 0],
        ],
        demand_vectors=[[0], [1]],
        capacities=[1],
        num_vehicles=1,
        first_solution_strategy="not-a-strategy",
    )

    assert solution.success is False
    assert "first_solution_strategy" in str(solution.error_message)
