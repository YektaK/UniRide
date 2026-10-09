"""WP1 tests for the typed split decoder (heterogeneous fleet design 3.1, 7 P3, 9)."""

from __future__ import annotations

import itertools
import random

import pytest

from uniride_core.algorithms.string_split_decoder import Direction, decode_giant_tour
from uniride_core.algorithms.typed_split_decoder import VehicleType, decode_typed
from uniride_core.tests.test_split_parity_golden import DEPOT, _instance

LARGE = VehicleType("large", 4, 5, 120.0, None, 10)
CAR = VehicleType("car", 0, 4, 120.0, None, 10)


def _line(n, step=5):
    names = [DEPOT] + [f"L{i}" for i in range(1, n + 1)]
    pos = {x: (0 if x == DEPOT else int(x[1:]) * step) for x in names}
    return {a: {b: abs(pos[a] - pos[b]) for b in names} for a in names}


def _typed(tour, m, dem, types, **kw):
    return decode_typed(tour, DEPOT, m, dem, types, **kw)


def test_sw_segment_never_on_zero_sw_type():
    m = _line(4)
    dem = {"L1": (1, 0), "L2": (0, 1), "L3": (0, 1), "L4": (0, 1)}
    r = _typed(["L1", "L2", "L3", "L4"], m, dem, [LARGE, CAR],
               minimize_type="car", quota_type="large", quota=1)
    assert r.feasible
    for route, t in zip(r.routes, r.type_ids):
        if any(dem[s][0] for s in route):
            assert t == "large"
    assert r.type_ids.count("large") <= 1


def test_quota_zero_forces_cars_or_infeasible():
    m = _line(3)
    no_sw = {f"L{i}": (0, 1) for i in range(1, 4)}
    r = _typed(["L1", "L2", "L3"], m, no_sw, [LARGE, CAR],
               minimize_type="car", quota_type="large", quota=0)
    assert r.feasible and set(r.type_ids) == {"car"}
    with_sw = dict(no_sw, L2=(1, 0))
    r = _typed(["L1", "L2", "L3"], m, with_sw, [LARGE, CAR],
               minimize_type="car", quota_type="large", quota=0)
    assert not r.feasible and r.routes == []  # no singleton fallback


def test_quota_limits_large_routes_and_minimises_cars():
    m = _line(4)
    dem = {f"L{i}": (0, 1) for i in range(1, 5)}
    big = VehicleType("large", 4, 1, 120.0)  # one So seat -> one stop per large route
    r = _typed(list(dem), m, dem, [big, CAR], minimize_type="car",
               quota_type="large", quota=2)
    assert r.type_ids.count("large") <= 2
    assert r.routes_by_type["car"] == 1  # one car route takes the rest


def test_per_type_ride_and_tour_limits():
    m = _line(3, step=10)
    dem = {f"L{i}": (0, 1) for i in range(1, 4)}
    tight = VehicleType("tight", 0, 4, 120.0, max_ride_time=25)
    loose = VehicleType("loose", 0, 4, 120.0, max_ride_time=60)
    r = _typed(["L3", "L2", "L1"], m, dem, [tight, loose], minimize_type="tight")
    assert r.feasible
    for route, t in zip(r.routes, r.type_ids):
        ride = sum(m[a][b] for a, b in zip(route, route[1:] + [DEPOT]))
        assert ride <= {"tight": 25, "loose": 60}[t]
    # L3 alone rides 30 > 25: the tight type can never carry it.
    r2 = _typed(["L3", "L2"], m, dem, [tight, loose], minimize_type="loose")
    assert r2.feasible
    assert all(t == "loose" for rt, t in zip(r2.routes, r2.type_ids) if "L3" in rt)
    r3 = _typed(["L3"], m, dem, [VehicleType("x", 0, 4, max_tour_duration=40)])
    assert not r3.feasible  # 30 + 30 > 40
    r4 = _typed(["L3"], m, dem, [VehicleType("x", 0, 4, max_tour_duration=60)])
    assert r4.feasible


def test_missing_arc_is_infeasible():
    m = _line(2)
    del m["L2"][DEPOT]
    dem = {"L1": (0, 1), "L2": (0, 1)}
    r = _typed(["L1", "L2"], m, dem, [CAR], is_asymmetric=True)
    # L2 can never be visited because its return arc is missing.
    assert not r.feasible


@pytest.mark.parametrize("n,asym,direction,swc,soc,tour,ride", [
    (9, False, "pickup", 4, 5, 90.0, 50.0),
    (8, True, "dropoff", 4, 5, 120.0, 90.0),
    (7, False, "pickup", 2, 3, 70.0, None),
])
def test_p3_one_type_matches_decode_giant_tour_on_golden_instances(
        n, asym, direction, swc, soc, tour, ride):
    wps, matrix, demands = _instance(n, asym)
    one = VehicleType("large", swc, soc, tour, ride)
    rng = random.Random(n)
    orders = [wps, wps[::-1]] + [rng.sample(wps, len(wps)) for _ in range(60)]
    compared = 0
    for order in orders:
        ref = decode_giant_tour(order, DEPOT, matrix, demands, swc, soc, tour,
                                is_asymmetric=asym, max_ride_time=ride,
                                direction=Direction(direction))
        got = decode_typed(order, DEPOT, matrix, demands, [one],
                           is_asymmetric=asym, direction=Direction(direction))
        if "error" in ref:
            assert not got.feasible
            continue
        assert got.feasible
        assert got.routes == ref["routes"]
        assert got.costs == ref["costs"]
        assert got.total_cost == ref["total_cost"]
        assert got.num_vehicles == ref["num_vehicles"]
        compared += 1
    assert compared > 0


# ---- brute force ---------------------------------------------------------

def _seg_cost(seg, t, m, dem, dropoff):
    if sum(dem[s][0] for s in seg) > t.sw_capacity or sum(dem[s][1] for s in seg) > t.so_capacity:
        return None
    if t.total_capacity is not None and sum(dem[s][0] + dem[s][1] for s in seg) > t.total_capacity:
        return None
    arcs = [m[a][b] for a, b in zip([DEPOT] + seg, seg + [DEPOT])]
    total = sum(arcs)
    if total > t.max_tour_duration:
        return None
    if t.max_ride_time is not None:
        ride = sum(arcs[:-1]) if dropoff else sum(arcs[1:])
        if ride > t.max_ride_time:
            return None
    return total


def _brute(tour, m, dem, types, minimize, quota_type, quota, dropoff):
    n = len(tour)
    best = None
    for cuts in itertools.product([0, 1], repeat=n - 1):
        segs, cur = [], [tour[0]]
        for c, s in zip(cuts, tour[1:]):
            if c:
                segs.append(cur)
                cur = []
            cur.append(s)
        segs.append(cur)
        for labels in itertools.product(range(len(types)), repeat=len(segs)):
            cost, cars, big, ok = 0.0, 0, 0, True
            for seg, li in zip(segs, labels):
                c = _seg_cost(seg, types[li], m, dem, dropoff)
                if c is None:
                    ok = False
                    break
                cost += c
                cars += types[li].id == minimize
                big += types[li].id == quota_type
            if not ok or (quota is not None and big > quota):
                continue
            if best is None or (cars, cost) < best:
                best = (cars, cost)
    return best


def test_brute_force_cross_check_tiny_instances():
    rng = random.Random(2026)
    checked = infeasible = 0
    for _ in range(400):
        n = rng.randint(1, 7)
        names = [DEPOT] + [f"L{i}" for i in range(1, n + 1)]
        m = {a: {b: (0 if a == b else rng.randint(2, 15)) for b in names} for a in names}
        dem = {f"L{i}": ((1, 0) if rng.random() < 0.3 else (0, rng.randint(0, 2)))
               for i in range(1, n + 1)}
        types = [
            VehicleType("large", rng.randint(1, 3), rng.randint(1, 4),
                        rng.choice([40.0, 60.0, 200.0]), rng.choice([None, 20.0, 35.0])),
            VehicleType("car", rng.choice([0, 0, 1]), rng.randint(1, 3),
                        rng.choice([40.0, 60.0, 200.0]), rng.choice([None, 20.0, 35.0])),
        ]
        quota = rng.choice([None, 0, 1, 2])
        direction = rng.choice(["pickup", "dropoff"])
        tour = names[1:]
        rng.shuffle(tour)
        want = _brute(tour, m, dem, types, "car", "large", quota, direction == "dropoff")
        got = decode_typed(tour, DEPOT, m, dem, types, minimize_type="car",
                           quota_type="large", quota=quota, is_asymmetric=True,
                           direction=Direction(direction))
        if want is None:
            assert not got.feasible
            infeasible += 1
            continue
        assert got.feasible
        assert got.routes_by_type["car"] == want[0]
        assert got.total_cost == pytest.approx(want[1])
        assert got.routes_by_type["large"] <= (quota if quota is not None else n)
        assert sum(map(len, got.routes)) == n
        checked += 1
    assert checked > 100 and infeasible > 10


# ---- optional shared total_capacity (Doblo: 1sw3so, 3 seats in total) -------

DOBLO = VehicleType("doblo", 1, 3, 500.0, None, 10, total_capacity=3)


@pytest.mark.parametrize("sw,so,ok", [(0, 3, True), (1, 2, True), (1, 3, False), (0, 4, False)])
def test_total_capacity_accepts_and_rejects_loads(sw, so, ok):
    stops = ["L1"]  # one stop carrying the whole load, so the route cannot be split
    m = _line(1)
    dem = {"L1": (sw, so)}
    got = _typed(stops, m, dem, [DOBLO], is_asymmetric=True)
    if ok:
        assert got.feasible and got.routes == [stops] and got.type_ids == ["doblo"]
    else:
        assert not got.feasible
    # without the cap the pools alone would still allow 1Sw+3So (but not 4 So)
    uncapped = VehicleType("doblo", 1, 3, 500.0, None, 10)
    assert _typed(stops, m, dem, [uncapped], is_asymmetric=True).feasible == (so <= 3)


def test_total_capacity_splits_when_pools_would_allow_more():
    stops = ["L1", "L2", "L3", "L4"]
    m = _line(4)
    dem = {"L1": (1, 0), "L2": (0, 1), "L3": (0, 1), "L4": (0, 1)}
    got = _typed(stops, m, dem, [DOBLO], is_asymmetric=True)
    assert got.feasible and len(got.routes) == 2
    assert all(sum(sum(dem[s]) for s in r) <= 3 for r in got.routes)


def test_total_capacity_must_be_positive():
    with pytest.raises(ValueError):
        _typed(["L1"], _line(1), {"L1": (0, 1)}, [VehicleType("x", 1, 3, total_capacity=0)])


def test_brute_force_cross_check_with_total_capacity_type():
    rng = random.Random(20261009)
    checked = infeasible = 0
    for _ in range(400):
        n = rng.randint(1, 7)
        names = [DEPOT] + [f"L{i}" for i in range(1, n + 1)]
        m = {a: {b: (0 if a == b else rng.randint(2, 15)) for b in names} for a in names}
        dem = {f"L{i}": ((1, 0) if rng.random() < 0.3 else (0, rng.randint(0, 2)))
               for i in range(1, n + 1)}
        types = [
            VehicleType("large", rng.randint(1, 3), rng.randint(1, 4),
                        rng.choice([40.0, 60.0, 200.0]), rng.choice([None, 20.0, 35.0]),
                        total_capacity=rng.choice([None, 2, 3, 4])),
            VehicleType("car", 1, 3, rng.choice([40.0, 60.0, 200.0]),
                        rng.choice([None, 20.0, 35.0]), total_capacity=rng.choice([2, 3])),
        ]
        quota = rng.choice([None, 0, 1, 2])
        direction = rng.choice(["pickup", "dropoff"])
        tour = names[1:]
        rng.shuffle(tour)
        want = _brute(tour, m, dem, types, "car", "large", quota, direction == "dropoff")
        got = decode_typed(tour, DEPOT, m, dem, types, minimize_type="car",
                           quota_type="large", quota=quota, is_asymmetric=True,
                           direction=Direction(direction))
        if want is None:
            assert not got.feasible
            infeasible += 1
            continue
        assert got.feasible
        assert got.routes_by_type["car"] == want[0]
        assert got.total_cost == pytest.approx(want[1])
        for r, lab in zip(got.routes, got.type_ids):
            cap = next(t.total_capacity for t in types if t.id == lab)
            assert cap is None or sum(sum(dem[s]) for s in r) <= cap
        checked += 1
    assert checked > 100
