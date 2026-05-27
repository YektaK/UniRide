from uniride_core.algorithms.cvrptw_decoder import (
    CVRPTWDecoder,
    Direction,
    create_time_windows_from_students,
    parse_time_windows,
)


def test_cvrptw_decoder_uses_stable_core_split_decoder():
    decoder = CVRPTWDecoder(sw_capacity=1, so_capacity=2, max_tour_duration=30)
    result = decoder.decode(
        ["A", "B", "C"],
        "D",
        {
            "D": {"A": 5, "B": 6, "C": 7},
            "A": {"B": 4, "C": 8, "D": 5},
            "B": {"A": 4, "C": 3, "D": 6},
            "C": {"A": 8, "B": 3, "D": 7},
        },
        {"A": (1, 0), "B": (0, 1), "C": (0, 1)},
    )

    assert result["routes"]
    assert result["num_vehicles"] >= 1
    assert result["capacity_violations"] == 0


def test_cvrptw_decoder_uses_core_linear_split_decoder():
    decoder = CVRPTWDecoder(
        sw_capacity=1,
        so_capacity=1,
        max_tour_duration=12,
        time_windows={"A": (0, 10), "B": (0, 10)},
        use_sota_engine=True,
        direction=Direction.DROPOFF,
    )
    result = decoder.decode(
        ["A", "B"],
        "D",
        {
            "D": {"A": 5, "B": 5},
            "A": {"B": 5, "D": 5},
            "B": {"A": 5, "D": 5},
        },
        {"A": (1, 0), "B": (0, 1)},
    )

    assert result["routes"]
    assert result["num_vehicles"] >= 1
    assert "time_window_violations" in result


def test_cvrptw_time_window_helpers():
    assert parse_time_windows(["08:00"], ["09:30"]) == {
        "08:00": (480, 510),
        "09:30": (570, 600),
    }
    assert create_time_windows_from_students(
        [
            {"location_code": "A", "pickup_time": "08:00"},
            {"location_code": "A", "pickup_time": "08:15"},
            {"location_code": "B", "pickup_time": "bad"},
        ]
    ) == {"A": (480, 525)}
