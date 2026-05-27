from uniride_core.algorithms.vroom_cvrp_engine import solve_sweep_fallback_routes, solve_vroom_cvrp


def test_solve_sweep_fallback_routes_respects_capacity():
    routes = solve_sweep_fallback_routes(
        customer_indices=[0, 1, 2],
        coordinates=[
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
            {"lat": 1, "lng": 0},
            {"lat": 0, "lng": -1},
        ],
        disability_types=["Sw", "So", "So"],
        depot_index=0,
        duration_lookup=lambda origin, destination: 1.0,
        sw_capacity=1,
        so_capacity=1,
        max_route_duration=10,
    )

    visited = sorted(idx for route in routes for idx in route.customer_indices)
    assert visited == [0, 1, 2]
    assert all(route.sw_count <= 1 for route in routes)
    assert all(route.so_count <= 1 for route in routes)


def test_solve_vroom_cvrp_has_clean_failure_or_complete_solution():
    solution = solve_vroom_cvrp(
        duration_matrix=[
            [0, 2],
            [2, 0],
        ],
        disability_types=["Sw"],
        sw_capacity=1,
        so_capacity=1,
        max_route_duration=20,
        num_vehicles=1,
    )

    if solution.success:
        assert [idx for route in solution.routes for idx in route.customer_indices] == [0]
    else:
        assert solution.error_message
