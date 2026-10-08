"""WP4: exact day selection (CP-SAT) versus enumeration."""

import itertools
import random

import pytest

pytest.importorskip("ortools")

from uniride_core.planning import typed_day_selection as tds
from uniride_core.planning.typed_day_selection import (
    Option,
    Route,
    Wave,
    solve_day_selection,
)

CD = 10


def peak_concurrency(intervals):
    """Local oracle copy (independent of the production helper)."""
    return max((sum(1 for s, e in intervals if s <= a < e) for a, _ in intervals), default=0)
SCALE = 1000


def _random_waves(rng, n_waves, n_opts, max_routes, car_forced_p=0.25):
    waves = []
    for w in range(n_waves):
        base = rng.randrange(0, 120)
        opts = []
        for o in range(rng.randint(1, n_opts)):
            routes = []
            for _ in range(rng.randint(1, max_routes)):
                s = base + rng.randrange(0, 40)
                e = s + rng.randint(5, 45)
                routes.append(Route(s, e, float(e - s) + rng.choice([0, 0.5]),
                                    True, rng.random() >= car_forced_p))
            opts.append(Option(f"o{o}", tuple(routes)))
        waves.append(Wave(f"w{w}", tuple(opts)))
    return waves


def _brute(waves, max_large, max_cars=None, cd_l=CD, cd_c=CD):
    """Lexicographic optimum (cars, car_min, total_min, idx_sum) or None."""
    best = None
    for combo in itertools.product(*[range(len(w.options)) for w in waves]):
        routes = [r for w, oi in zip(waves, combo) for r in w.options[oi].routes]
        total = sum(r.minutes for r in routes)
        idx = sum(combo)
        for labels in itertools.product((0, 1), repeat=len(routes)):  # 1 = car
            if any((l and not r.car_ok) or (not l and not r.large_ok)
                   for l, r in zip(labels, routes)):
                continue
            big = [(r.start, r.end + cd_l) for l, r in zip(labels, routes) if not l]
            car = [(r.start, r.end + cd_c) for l, r in zip(labels, routes) if l]
            if peak_concurrency(big) > max_large:
                continue
            c = peak_concurrency(car)
            if max_cars is not None and c > max_cars:
                continue
            cm = sum(r.minutes for l, r in zip(labels, routes) if l)
            key = (c, round(cm * SCALE), round(total * SCALE), idx)
            if best is None or key < best:
                best = key
    return best


def _validate(waves, res, max_large, cd_l=CD, cd_c=CD):
    assert set(res.selection) == {w.wave_id for w in waves}
    big, car = [], []
    for w in waves:
        sel = res.selection[w.wave_id]
        o = w.options[sel["option_index"]]
        assert o.option_id == sel["option_id"] and len(sel["labels"]) == len(o.routes)
        for r, lab in zip(o.routes, sel["labels"]):
            assert (r.car_ok if lab == "car" else r.large_ok)
            (car if lab == "car" else big).append(
                (r.start, r.end + (cd_c if lab == "car" else cd_l)))
    assert peak_concurrency(big) <= max_large
    assert peak_concurrency(car) == res.cars == res.stats["stage_values"]["cars"]


@pytest.mark.parametrize("seed", range(60))
def test_matches_bruteforce_on_tiny_instances(seed):
    rng = random.Random(seed)
    waves = _random_waves(rng, rng.randint(1, 4), 3, 3)
    max_large = rng.randint(0, 3)
    expect = _brute(waves, max_large)
    res = solve_day_selection(waves, max_large, time_limit_s=20)
    if expect is None:
        assert res.status == tds.STATUS_INFEASIBLE_FOR_L
        return
    assert res.status == tds.STATUS_OPTIMAL
    _validate(waves, res, max_large)
    got = (res.cars, round(res.car_minutes * SCALE), round(res.total_minutes * SCALE),
           sum(v["option_index"] for v in res.selection.values()))
    assert got == expect


def test_bruteforce_with_car_cap_and_distinct_cooldowns():
    rng = random.Random(7)
    checked = 0
    for _ in range(30):
        waves = _random_waves(rng, 3, 3, 3)
        cap = rng.randint(0, 2)
        expect = _brute(waves, 2, max_cars=cap, cd_l=5, cd_c=15)
        res = solve_day_selection(waves, 2, max_cars=cap, cooldown_large=5, cooldown_car=15)
        if expect is None:
            assert res.status == tds.STATUS_INFEASIBLE_FOR_L
        else:
            assert res.status == tds.STATUS_OPTIMAL and res.cars == expect[0]
            checked += 1
    assert checked >= 5


@pytest.mark.parametrize("seed", range(25))
def test_cars_non_increasing_in_L(seed):
    rng = random.Random(1000 + seed)
    waves = _random_waves(rng, rng.randint(2, 5), 4, 4)
    prev = None
    feasible_seen = False
    for L in range(0, 7):
        res = solve_day_selection(waves, L, time_limit_s=20)
        if res.status == tds.STATUS_INFEASIBLE_FOR_L:
            assert not feasible_seen  # once feasible, always feasible for larger L
            continue
        assert res.status == tds.STATUS_OPTIMAL
        feasible_seen = True
        if prev is not None:
            assert res.cars <= prev
        prev = res.cars
    assert feasible_seen


def test_zero_cars_when_large_unconstrained():
    waves = [Wave("a", (Option("q0", (Route(0, 30, 30.0), Route(5, 35, 30.0))),))]
    assert solve_day_selection(waves, 1).cars == 1  # overlap: one route must be a car
    res = solve_day_selection(waves, 2)
    assert res.cars == 0 and res.car_minutes == 0


def test_cooldown_blocks_reuse_of_large_vehicle():
    # second route starts 5 min after the first ends: cooldown 10 -> needs a 2nd vehicle
    r1, r2 = Route(0, 30, 30.0), Route(35, 60, 25.0)
    waves = [Wave("a", (Option("o", (r1, r2)),))]
    assert solve_day_selection(waves, 1).cars == 1
    assert solve_day_selection(waves, 1, cooldown_large=0, cooldown_car=0).cars == 0
    assert solve_day_selection(waves, 2).cars == 0


def test_infeasible_for_L_reports_sw_wave_and_lower_bound():
    sw = lambda s: Route(s, s + 30, 30.0, True, False)  # noqa: E731
    waves = [
        Wave("w1", (Option("a", (sw(0),)), Option("b", (sw(0),)))),
        Wave("w2", (Option("a", (sw(100), sw(105), sw(110))),)),
    ]
    res = solve_day_selection(waves, 2)
    assert res.status == tds.STATUS_INFEASIBLE_FOR_L
    assert res.diagnostics["reason"] == "SW_DEMAND_EXCEEDS_LARGE_CAPACITY"
    assert res.diagnostics["waves_exceeding_L"] == ["w2"]
    assert res.diagnostics["lower_bound_L"] == 3
    assert solve_day_selection(waves, 3).status == tds.STATUS_OPTIMAL


def test_infeasible_for_L_cross_wave_conflict_and_car_cap():
    sw = lambda s: Route(s, s + 30, 30.0, True, False)  # noqa: E731
    waves = [Wave("w1", (Option("a", (sw(0),)),)), Wave("w2", (Option("a", (sw(10),)),))]
    res = solve_day_selection(waves, 1)
    assert res.status == tds.STATUS_INFEASIBLE_FOR_L
    assert res.diagnostics["reason"] == "CROSS_WAVE_CONFLICT"
    assert res.diagnostics["waves_exceeding_L"] == []
    # car cap: two overlapping routes, only L=1 large -> one car needed, cap 0 fails
    waves = [Wave("w", (Option("a", (Route(0, 30, 30.0), Route(5, 35, 30.0))),))]
    res = solve_day_selection(waves, 1, max_cars=0)
    assert res.status == tds.STATUS_INFEASIBLE_FOR_L
    assert res.diagnostics["reason"] == "CROSS_WAVE_CONFLICT_OR_CAR_CAP"


def test_infeasible_data_cases():
    bad = [
        [Wave("w", ())],
        [Wave("w", (Option("a", (Route(0, 10, 10.0, False, False),)),))],
        [Wave("w", (Option("a", (Route(10, 10, 1.0),)),))],
        [Wave("w", (Option("a", ()),)), Wave("w", (Option("a", ()),))],
    ]
    for waves in bad:
        res = solve_day_selection(waves, 1)
        assert res.status == tds.STATUS_INFEASIBLE_DATA
        assert res.diagnostics["problems"]


def test_empty_option_is_allowed_and_free():
    waves = [Wave("w", (Option("empty", ()), Option("r", (Route(0, 10, 10.0),))))]
    res = solve_day_selection(waves, 0)
    assert res.status == tds.STATUS_OPTIMAL and res.selection["w"]["option_id"] == "empty"


def test_time_limit_hit_reports_not_proven(monkeypatch):
    rng = random.Random(3)
    waves = _random_waves(rng, 20, 5, 8)
    res = solve_day_selection(waves, 3, time_limit_s=1e-6)
    assert res.status in (tds.STATUS_FEASIBLE, tds.STATUS_INDETERMINATE, tds.STATUS_OPTIMAL)
    if res.status == tds.STATUS_FEASIBLE:
        assert "not proven" in res.diagnostics["claim"]


def test_deterministic_across_runs():
    rng = random.Random(11)
    waves = _random_waves(rng, 6, 4, 4)
    runs = [solve_day_selection(waves, 2, time_limit_s=20) for _ in range(3)]
    key = lambda r: (r.status, r.cars, r.car_minutes, r.total_minutes, r.selection)  # noqa: E731
    assert key(runs[0]) == key(runs[1]) == key(runs[2])
    assert runs[0].stats["num_workers"] == 1


def test_option_index_tiebreak_prefers_lowest_index():
    r = (Route(0, 10, 10.0),)
    waves = [Wave("w", (Option("a", r), Option("b", r)))]
    assert solve_day_selection(waves, 1).selection["w"]["option_index"] == 0


@pytest.mark.parametrize("gap,cars", [(0, 1), (-1, 2)])
def test_car_cooldown_boundary(gap, cars):
    # L=0 forces cars. next start = end + cooldown + gap: equal -> reusable, one earlier -> 2 cars.
    r1 = Route(0, 30, 30.0)
    nxt = 30 + CD + gap
    r2 = Route(nxt, nxt + 20, 20.0)
    waves = [Wave("a", (Option("o", (r1, r2)),))]
    res = solve_day_selection(waves, 0, cooldown_large=CD, cooldown_car=CD)
    assert res.status == tds.STATUS_OPTIMAL and res.cars == cars
    assert res.stats["stage_values"]["cars"] == cars  # the model's own C, not the recomputed peak
    assert _brute(waves, 0)[0] == cars


@pytest.mark.parametrize("gap,large", [(0, 1), (-1, 2)])
def test_large_cooldown_boundary(gap, large):
    r1 = Route(0, 30, 30.0, True, False)
    nxt = 30 + CD + gap
    r2 = Route(nxt, nxt + 20, 20.0, True, False)
    waves = [Wave("a", (Option("o", (r1, r2)),))]
    assert solve_day_selection(waves, large).status == tds.STATUS_OPTIMAL
    if large == 2:
        assert solve_day_selection(waves, 1).status == tds.STATUS_INFEASIBLE_FOR_L
