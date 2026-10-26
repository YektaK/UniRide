from uniride_core.algorithms.local_search import LocalSearchType, TwoOptLocalSearch, apply_local_search


def _line_duration(route):
    coords = {
        "Depot": (0, 0),
        "A": (1, 0),
        "B": (2, 0),
        "C": (3, 0),
        "D": (4, 0),
    }
    full_route = ["Depot"] + list(route) + ["Depot"]
    return sum(
        ((coords[a][0] - coords[b][0]) ** 2 + (coords[a][1] - coords[b][1]) ** 2) ** 0.5
        for a, b in zip(full_route, full_route[1:])
    )


def test_core_local_search_two_opt_preserves_route_membership():
    route = ["A", "D", "B", "C"]
    improved, cost = apply_local_search(route, _line_duration, LocalSearchType.TWO_OPT)

    assert cost <= _line_duration(route)
    assert set(improved) == set(route)


def test_core_local_search_keeps_legacy_two_opt_swap_helper():
    ls = TwoOptLocalSearch()

    assert ls._two_opt_swap(["A", "B", "C", "D"], 1, 2) == ["A", "C", "B", "D"]


def test_core_three_opt_uses_path_neighbourhood_through_apply_local_search():
    # M14 (MT6-04): the first position can move and C'B' is reachable; ["A".."D"] with
    # cost = position of "D" must end with "D" first.
    route = ["A", "B", "C", "D"]
    improved, cost = apply_local_search(
        route, lambda r: float(r.index("D")), LocalSearchType.THREE_OPT
    )

    assert improved[0] == "D"
    assert cost == 0.0


def test_core_three_opt_small_route_is_unchanged_not_two_opt():
    route = ["A", "B", "C"]
    improved, cost = apply_local_search(
        route, lambda r: float(r.index("C")), LocalSearchType.THREE_OPT
    )

    assert improved == route
    assert cost == 2.0
