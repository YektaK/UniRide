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
