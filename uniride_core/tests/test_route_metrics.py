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


def test_get_duration_does_not_fall_back_to_coordinates_by_default():
    # C2 / owner requirement 2026-10-05: no haversine stand-in for a pair
    # missing from the stored matrix unless explicitly opted in.
    try:
        get_duration(
            "a",
            "b",
            {},
            {"a": {"lat": 0, "lng": 0}, "b": {"lat": 0, "lng": 1}},
        )
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass


def test_get_duration_coordinate_fallback_is_explicit_opt_in():
    duration = get_duration(
        "a",
        "b",
        {},
        {"a": {"lat": 0, "lng": 0}, "b": {"lat": 0, "lng": 1}},
        allow_coordinate_fallback=True,
    )

    assert duration > 0


def test_get_duration_opt_in_still_raises_without_coordinates():
    try:
        get_duration("a", "b", {}, {}, allow_coordinate_fallback=True)
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass


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


def test_get_duration_strict_still_uses_matrix_and_opted_in_coordinates():
    assert get_duration("a", "b", {"a": {"b": 3.0}}, {}, strict=True) == 3.0
    coord_hit = get_duration(
        "a",
        "b",
        {},
        {"a": {"lat": 0, "lng": 0}, "b": {"lat": 0, "lng": 1}},
        strict=True,
        allow_coordinate_fallback=True,
    )
    assert coord_hit > 0


def test_get_duration_is_strict_by_default():
    try:
        get_duration("a", "b", {}, {})
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass


def test_get_duration_explicit_non_strict_keeps_generic_fallback():
    from uniride_core.algorithms.route_metrics import DEFAULT_TRAVEL_FALLBACK_MINUTES

    assert (
        get_duration("a", "b", {}, {}, strict=False)
        == DEFAULT_TRAVEL_FALLBACK_MINUTES
    )


def test_calculate_route_duration_is_strict_and_coordinate_free_by_default():
    coords = {"depot": {"lat": 0, "lng": 0}, "a": {"lat": 0, "lng": 1}}
    try:
        calculate_route_duration(["a"], "depot", {}, coords)
        raise AssertionError("expected TravelTimeUnavailableError")
    except TravelTimeUnavailableError:
        pass
    assert calculate_route_duration(["a"], "depot", {}, coords, allow_coordinate_fallback=True) > 0


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
