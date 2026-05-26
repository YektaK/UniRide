from optimizer_api.models import LocationNode, OptimizationRequest, StudentNode
from uniride_core.adapters import uniride_request_to_problem


def test_optimizer_request_converts_to_core_routing_problem():
    request = OptimizationRequest(
        depot=LocationNode(id="D", lat=0.0, lng=0.0),
        students=[
            StudentNode(
                id="S1",
                location_code="L1",
                coordinates={"lat": 1.0, "lng": 0.0},
                disability_type="Sw",
                pickup_time="08:00",
            ),
            StudentNode(
                id="S2",
                location_code="L2",
                coordinates={"lat": 2.0, "lng": 0.0},
                disability_type="So",
                pickup_time="08:10",
            ),
        ],
        sw_capacity=1,
        so_capacity=2,
        direction="pickup",
        target_time="08:20",
        is_asymmetric=True,
    )

    problem = uniride_request_to_problem(
        request,
        matrix=[
            [0, 5, 9],
            [6, 0, 3],
            [8, 4, 0],
        ],
    )

    assert problem.source == "uniride"
    assert problem.matrix.labels == ["D", "L1", "L2"]
    assert problem.constraints.demands == [[0, 0], [1, 0], [0, 1]]
    assert problem.constraints.capacities == [1, 2]
    assert problem.constraints.time_windows[1] == (450, 480)
    assert problem.constraints.target_time == 500
