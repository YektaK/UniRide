from optimizer_api.models import OptimizationRequest


def test_optimization_request_accepts_legacy_smoke_payload():
    request = OptimizationRequest(
        depot="A",
        locations=["B", "C"],
        distance_matrix={
            "A": {"A": 0, "B": 5, "C": 6},
            "B": {"A": 5, "B": 0, "C": 2},
            "C": {"A": 7, "B": 2, "C": 0},
        },
        demands={"B": (1, 0), "C": (0, 1)},
        vehicles=[{"id": "V1", "capacity_sw": 4, "capacity_so": 5}],
        target_time=8 * 60,
        direction="pickup",
    )

    assert request.depot.id == "A"
    assert [student.location_code for student in request.students] == ["B", "C"]
    assert request.students[0].disability_type == "Sw"
    assert request.students[1].disability_type == "So"
    assert request.vehicles[0].vehicle_id == "V1"
    assert request.target_time == "08:00"
    assert request.is_asymmetric is True

    request.strategy = "pso"
    assert request.algorithm == "pso"
