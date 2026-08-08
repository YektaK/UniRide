from uniride_core.algorithms.route_metrics import (
    TravelTimeUnavailableError,
    calculate_route_duration,
    get_duration,
)


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


def test_get_duration_strict_raises_when_unavailable():
    try:
        get_duration(
            "a",
            "b",
            {},
            {},
            strict=True,
        )
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass


def test_get_duration_strict_still_uses_matrix_and_coordinates():
    assert get_duration("a", "b", {"a": {"b": 3.0}}, {}, strict=True) == 3.0
    coord_hit = get_duration(
        "a", "b", {}, {"a": {"lat": 0, "lng": 0}, "b": {"lat": 0, "lng": 1}}, strict=True
    )
    assert coord_hit > 0


def test_get_duration_non_strict_keeps_generic_fallback():
    from uniride_core.algorithms.route_metrics import DEFAULT_TRAVEL_FALLBACK_MINUTES

    assert (
        get_duration("a", "b", {}, {}, strict=False)
        == DEFAULT_TRAVEL_FALLBACK_MINUTES
    )


def test_calculate_route_duration_strict_forwards():
    try:
        calculate_route_duration(["a"], "depot", {}, {}, strict=True)
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass


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
