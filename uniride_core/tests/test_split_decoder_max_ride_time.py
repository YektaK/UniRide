"""Per-student maximum ride time (``max_ride_time``) in the split decoder.

Owner decision 2026-10-04.  Route = depot -> s1 .. sk -> depot with arcs
a0 (depot->s1), a1..a(k-1), ak (sk->depot).

* pickup  : ride of stop m = travel from stop m to the campus, including the
            closing arc.  Longest = first student = total - a0.
* dropoff : ride of stop m = travel from the campus to stop m.  Longest =
            last student = total - ak.

``max_ride_time=None`` must leave every existing behaviour unchanged.
"""

import itertools
import math
import random

import pytest

from uniride_core.algorithms.string_split_decoder import (
    Direction,
    SplitDecoder,
    decode_giant_tour,
    decode_with_time_windows,
)

DEPOT = "D"


def _line_matrix():
    """Stops on a line: D=0, A=10, B=20, C=30 (symmetric)."""
    pos = {DEPOT: 0.0, "A": 10.0, "B": 20.0, "C": 30.0}
    return {a: {b: abs(pa - pb) for b, pb in pos.items() if b != a} for a, pa in pos.items()}


def _detour_matrix():
    """Directed fixture where the dropoff tour D->A->B->C is a long detour."""
    return {
        DEPOT: {"A": 5.0, "B": 5.0, "C": 5.0},
        "A": {DEPOT: 5.0, "B": 5.0, "C": 50.0},
        "B": {DEPOT: 9.0, "A": 50.0, "C": 5.0},
        "C": {DEPOT: 5.0, "A": 50.0, "B": 50.0},
    }


DEMANDS = {"A": (0, 1), "B": (0, 1), "C": (0, 1)}


def _arcs(route, dm):
    chain = [DEPOT] + list(route) + [DEPOT]
    return [dm[a][b] for a, b in zip(chain, chain[1:])]


def max_ride(route, dm, direction):
    arcs = _arcs(route, dm)
    if direction == Direction.PICKUP:
        return sum(arcs[1:])  # total - a0 (first student's ride)
    return sum(arcs[:-1])  # total - ak (last student's ride)


def _decode(dm, direction, max_ride_time, tour=("A", "B", "C"), **kw):
    return decode_giant_tour(
        giant_tour=list(tour),
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
        max_ride_time=max_ride_time,
        direction=direction,
        **kw,
    )


# -- default None: unchanged ------------------------------------------------


@pytest.mark.parametrize("direction", [Direction.PICKUP, Direction.DROPOFF])
def test_default_none_keeps_single_route(direction):
    res = _decode(_line_matrix(), direction, None)
    assert res["routes"] == [["A", "B", "C"]]


def test_omitting_new_arguments_matches_none():
    base = decode_giant_tour(
        ["A", "B", "C"], DEPOT, _line_matrix(), DEMANDS, 4, 10, 1000
    )
    explicit = _decode(_line_matrix(), Direction.PICKUP, None)
    assert base["routes"] == explicit["routes"]
    assert base["total_cost"] == explicit["total_cost"]


# -- pickup -----------------------------------------------------------------


def test_pickup_tour_fits_travel_limit_but_ride_splits():
    dm = _line_matrix()
    # whole tour = 60 <= max_tour_duration, longest pickup ride (A) = 50 > 35
    res = _decode(dm, Direction.PICKUP, 35)
    assert res["routes"] == [["A", "B"], ["C"]]
    for route in res["routes"]:
        assert max_ride(route, dm, Direction.PICKUP) <= 35


def test_pickup_boundary_exactly_at_limit_is_not_split():
    dm = _line_matrix()
    assert max_ride(["A", "B", "C"], dm, Direction.PICKUP) == 50
    assert _decode(dm, Direction.PICKUP, 50)["routes"] == [["A", "B", "C"]]
    assert len(_decode(dm, Direction.PICKUP, 49)["routes"]) > 1


# -- dropoff ----------------------------------------------------------------


def test_dropoff_tour_fits_travel_limit_but_ride_splits():
    dm = _detour_matrix()
    # D->A->B->C: rides 5, 10, 15, return 5 -> tour 20 well within 1000
    assert max_ride(["A", "B", "C"], dm, Direction.DROPOFF) == 15
    res = _decode(dm, Direction.DROPOFF, 12)
    assert len(res["routes"]) >= 2
    for route in res["routes"]:
        assert max_ride(route, dm, Direction.DROPOFF) <= 12
    assert sorted(loc for r in res["routes"] for loc in r) == ["A", "B", "C"]


def test_dropoff_boundary_exactly_at_limit_is_not_split():
    dm = _line_matrix()
    assert max_ride(["A", "B", "C"], dm, Direction.DROPOFF) == 30
    assert _decode(dm, Direction.DROPOFF, 30)["routes"] == [["A", "B", "C"]]
    # C alone is 30 too, so 29 is infeasible for every split -> fallback
    res = _decode(dm, Direction.DROPOFF, 29)
    assert "error" in res
    assert res["total_cost"] == math.inf


def test_direction_changes_the_split():
    dm = _line_matrix()
    pickup = _decode(dm, Direction.PICKUP, 35)
    dropoff = _decode(dm, Direction.DROPOFF, 35)
    assert len(pickup["routes"]) == 2
    assert dropoff["routes"] == [["A", "B", "C"]]


def test_direction_accepts_string_values():
    dm = _line_matrix()
    assert _decode(dm, "pickup", 35)["routes"] == [["A", "B"], ["C"]]
    assert _decode(dm, "dropoff", 35)["routes"] == [["A", "B", "C"]]


# -- oracle: DP result equals brute-force optimum -----------------------------


def _partitions(tour):
    n = len(tour)
    for cuts in itertools.product([0, 1], repeat=n - 1):
        parts, cur = [], [tour[0]]
        for cut, node in zip(cuts, tour[1:]):
            if cut:
                parts.append(cur)
                cur = [node]
            else:
                cur.append(node)
        parts.append(cur)
        yield parts


@pytest.mark.parametrize("direction", [Direction.PICKUP, Direction.DROPOFF])
@pytest.mark.parametrize("seed", range(6))
def test_dp_matches_bruteforce_with_ride_limit(direction, seed):
    rng = random.Random(seed)
    nodes = [DEPOT, "A", "B", "C", "E"]
    dm = {a: {b: float(rng.randint(2, 30)) for b in nodes if b != a} for a in nodes}
    demands = {n: (0, 1) for n in nodes[1:]}
    tour = ["A", "B", "C", "E"]
    limit = rng.choice([25, 35, 50, 70])

    res = decode_giant_tour(
        tour, DEPOT, dm, demands, 4, 10, 10_000,
        is_asymmetric=True, max_ride_time=limit, direction=direction,
    )

    best = math.inf
    for parts in _partitions(tour):
        if all(max_ride(p, dm, direction) <= limit for p in parts):
            best = min(best, sum(sum(_arcs(p, dm)) for p in parts))

    if math.isinf(best):
        assert "error" in res
    else:
        assert res["total_cost"] == pytest.approx(best)
        for route in res["routes"]:
            assert max_ride(route, dm, direction) <= limit


# -- time-window paths ------------------------------------------------------


def test_time_window_pickup_path_enforces_ride_limit():
    dm = _line_matrix()
    res = decode_with_time_windows(
        giant_tour=["A", "B", "C"],
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        time_windows={"A": (0, 1440), "B": (0, 1440), "C": (0, 1440)},
        direction=Direction.PICKUP,
        target_time=600,
        offset_minutes=0,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
        max_ride_time=35,
    )
    assert res["routes"] == [["A", "B"], ["C"]]


def test_time_window_dropoff_path_enforces_ride_limit():
    dm = _detour_matrix()
    res = decode_with_time_windows(
        giant_tour=["A", "B", "C"],
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        time_windows={"A": (0, 1440), "B": (0, 1440), "C": (0, 1440)},
        direction=Direction.DROPOFF,
        target_time=900,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
        max_ride_time=12,
    )
    assert len(res["routes"]) >= 2
    for route in res["routes"]:
        assert max_ride(route, dm, Direction.DROPOFF) <= 12


def test_time_window_dropoff_waiting_inside_vehicle_counts():
    """Waiting for a window to open while students are aboard is ride time."""
    dm = _line_matrix()
    # departure 480; C's window opens at 540, so the vehicle waits there.
    windows = {"A": (480, 1440), "B": (480, 1440), "C": (540, 1440)}
    kw = dict(
        giant_tour=["A", "B", "C"],
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        time_windows=windows,
        direction=Direction.DROPOFF,
        target_time=480,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
    )
    # pure travel ride to C is 30; with the wait it is 60 (arrive 540 - 480)
    assert decode_with_time_windows(max_ride_time=40, **kw)["routes"] != [["A", "B", "C"]]
    assert decode_with_time_windows(max_ride_time=60, **kw)["routes"] == [["A", "B", "C"]]


def test_time_window_pickup_waiting_after_first_pickup_counts():
    dm = _line_matrix()
    # Backward scheduling: departure 1440 - 60 = 1380, B reached at 1400 but
    # its window opens at 1405: the vehicle waits 5 minutes with A aboard.
    windows = {"A": (0, 1440), "B": (1405, 1440), "C": (0, 1440)}
    kw = dict(
        giant_tour=["A", "B", "C"],
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        time_windows=windows,
        direction=Direction.PICKUP,
        target_time=420,
        offset_minutes=0,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
    )
    # travel-only ride of A is 50, plus the 5 minute wait aboard = 55
    assert decode_with_time_windows(max_ride_time=52, **kw)["routes"] != [["A", "B", "C"]]
    assert decode_with_time_windows(max_ride_time=55, **kw)["routes"] == [["A", "B", "C"]]


def test_time_window_pickup_wait_at_first_stop_is_not_ride_time():
    """The first student boards after the wait, so it is not part of any ride."""
    dm = _line_matrix()
    # departure 1440 - 60 = 1380; A reached at 1390 but opens at 1395: a
    # 5 minute wait at the FIRST stop, before anyone is aboard.
    windows = {"A": (1395, 1440), "B": (0, 1440), "C": (0, 1440)}
    kw = dict(
        giant_tour=["A", "B", "C"],
        depot=DEPOT,
        distance_matrix=dm,
        demands=DEMANDS,
        time_windows=windows,
        direction=Direction.PICKUP,
        target_time=420,
        offset_minutes=0,
        sw_capacity=4,
        so_capacity=10,
        max_tour_duration=1000,
        is_asymmetric=True,
    )
    # pure travel ride of A is exactly 50; the first-stop wait must not add to it
    assert decode_with_time_windows(max_ride_time=50, **kw)["routes"] == [["A", "B", "C"]]
    assert decode_with_time_windows(max_ride_time=49, **kw)["routes"] != [["A", "B", "C"]]


# -- decoder class contract ---------------------------------------------------


def test_split_decoder_defaults_to_no_limit():
    assert SplitDecoder().max_ride_time is None
