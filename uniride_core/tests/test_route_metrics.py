from uniride_core.algorithms.route_metrics import calculate_route_duration, get_duration


def test_get_duration_prefers_explicit_matrix():
    duration = get_duration(
        "a",
        "b",
        {"a": {"b": 7.5}},
        {"a": {"lat": 0, "lng": 0}, "b": {"lat": 10, "lng": 10}},
    )

    assert duration == 7.5


def test_get_duration_falls_back_to_coordinates():
    duration = get_duration(
        "a",
        "b",
        {},
        {"a": {"lat": 0, "lng": 0}, "b": {"lat": 0, "lng": 1}},
    )

    assert duration > 0


def test_calculate_route_duration_uses_depot_cycle():
    duration = calculate_route_duration(
        ["a", "b"],
        "depot",
        {
            "depot": {"a": 1},
            "a": {"b": 2},
            "b": {"depot": 3},
        },
        {},
    )

    assert duration == 6
