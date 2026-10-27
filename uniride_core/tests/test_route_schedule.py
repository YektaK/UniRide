"""MT1-01: contract tests for the pure school-route simulator.

Scenarios come from the audit (H2, H3, H4) and the approved MT1 plan
(docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md, section 3.1).
All times are minutes from midnight; the depot (school) is node 0.
"""

from __future__ import annotations

import random

import pytest

from uniride_core.algorithms.route_schedule import (
    DEADLINE,
    END_AFTER_DAY,
    START_BEFORE_DAY,
    WINDOW,
    RouteSchedule,
    ScheduleViolation,
    simulate_school_dropoff,
    simulate_school_pickup,
)

EPS = 1e-9


def make_arc(table):
    """Directed arc lookup from {(i, j): minutes}."""

    def arc(i, j):
        return table[(i, j)]

    return arc


def kinds(schedule: RouteSchedule) -> list[str]:
    return [v.kind for v in schedule.violations]


# --------------------------------------------------------------------------
# (1) audit H2: return arc after waiting
# --------------------------------------------------------------------------
def test_h2_waiting_makes_school_arrival_miss_deadline():
    # target 08:30, offset 15 -> deadline 08:15 = 495. Two students, windows
    # 08:00-08:30. Arcs D->A 10, A->B 20, B->D 20.
    arc = make_arc({(0, 1): 10, (1, 2): 20, (2, 0): 20})
    windows = {1: (480, 510), 2: (480, 510)}

    s = simulate_school_pickup([1, 2], arc, deadline=495, windows=windows)

    assert not s.feasible
    assert kinds(s) == [DEADLINE]
    v = s.violations[0]
    assert v.position is None
    assert v.limit == 495
    assert v.actual == pytest.approx(520)  # 08:40, as the audit states
    assert v.amount == pytest.approx(25)
    assert s.end == pytest.approx(520)
    assert s.waits == (pytest.approx(25), pytest.approx(0))
    assert s.start == pytest.approx(445)  # latest departure, 07:25


# --------------------------------------------------------------------------
# (2) audit H4: latest feasible departure, no truncation
# --------------------------------------------------------------------------
def test_h4_latest_departure_without_truncation():
    # target 08:15, offset 0, arcs 10.9 / 10.9 / 10.2, A closes 07:53 (473).
    arc = make_arc({(0, 1): 10.9, (1, 2): 10.9, (2, 0): 10.2})
    windows = {1: (0, 473)}

    s = simulate_school_pickup([1, 2], arc, deadline=495, windows=windows)

    assert s.feasible
    assert s.violations == ()
    assert s.start == pytest.approx(462.1, abs=1e-9)
    assert s.arrivals[0] == pytest.approx(473.0, abs=1e-9)
    assert s.arrivals[1] == pytest.approx(483.9, abs=1e-9)
    assert s.end == pytest.approx(494.1, abs=1e-9)
    assert s.waits == (pytest.approx(0), pytest.approx(0))


# --------------------------------------------------------------------------
# (3) audit H3: the schedule the certificate would simulate
# --------------------------------------------------------------------------
def test_h3_schedule_matches_certificate_simulation():
    # target 08:30, offset 15 -> deadline 495. A window 07:30-08:00,
    # B window 08:00-08:30. Arcs D->A 10, A->B 5, B->D 10.
    arc = make_arc({(0, 1): 10, (1, 2): 5, (2, 0): 10})
    windows = {1: (450, 480), 2: (480, 510)}

    s = simulate_school_pickup([1, 2], arc, deadline=495, windows=windows)

    assert s.feasible
    assert s.start == pytest.approx(470)  # 07:50
    assert s.arrivals == (pytest.approx(480), pytest.approx(485))  # 08:00, 08:05
    assert s.end == pytest.approx(495)  # 08:15


# --------------------------------------------------------------------------
# (4) demo shape: one anchor, no windows, no service
# --------------------------------------------------------------------------
def test_demo_shape_pickup_has_no_wait_and_ends_at_deadline():
    arc = make_arc(
        {(0, 1): 7.5, (1, 2): 4, (2, 3): 6.25, (3, 0): 9, (0, 2): 99, (3, 1): 99}
    )
    anchor = 8 * 60 + 15

    s = simulate_school_pickup([1, 2, 3], arc, deadline=anchor)

    travel = 7.5 + 4 + 6.25 + 9
    assert s.feasible
    assert s.start == pytest.approx(anchor - travel)
    assert s.waits == (0, 0, 0)
    assert s.end == pytest.approx(anchor)
    assert s.tour == pytest.approx(travel)


def test_demo_shape_dropoff_starts_at_ready_and_has_no_wait():
    arc = make_arc({(0, 1): 7.5, (1, 2): 4, (2, 0): 9})
    ready = 14 * 60

    s = simulate_school_dropoff([1, 2], arc, ready=ready)

    assert s.feasible
    assert s.start == ready
    assert s.waits == (0, 0)
    assert s.end == pytest.approx(ready + 7.5 + 4 + 9)
    assert s.tour == pytest.approx(20.5)


# --------------------------------------------------------------------------
# (5) drop-off with a late-opening window: the wait is counted
# --------------------------------------------------------------------------
def test_dropoff_waits_for_late_window_and_counts_it():
    arc = make_arc({(0, 1): 10, (1, 2): 10, (2, 0): 10})
    windows = {1: (440, 500)}  # opens 07:20, bus arrives 07:10

    s = simulate_school_dropoff([1, 2], arc, ready=420, windows=windows)

    assert s.feasible
    assert s.arrivals == (pytest.approx(430), pytest.approx(450))
    assert s.waits == (pytest.approx(10), pytest.approx(0))
    assert s.end == pytest.approx(460)
    assert s.tour == pytest.approx(40)  # wait counted in the tour
    # ride = school departure -> own arrival; the wait at stop 1 is aboard for stop 2
    assert s.ride_times == (pytest.approx(10), pytest.approx(30))


def test_dropoff_window_close_and_day_end_are_typed_violations():
    arc = make_arc({(0, 1): 10, (1, 0): 10})

    late = simulate_school_dropoff([1], arc, ready=420, windows={1: (0, 425)})
    assert kinds(late) == [WINDOW]
    assert late.violations[0].position == 0
    assert late.violations[0].amount == pytest.approx(5)

    over = simulate_school_dropoff([1], arc, ready=420, day_end=435)
    assert kinds(over) == [END_AFTER_DAY]
    assert over.violations[0].amount == pytest.approx(5)


# --------------------------------------------------------------------------
# more pickup rules
# --------------------------------------------------------------------------
def test_pickup_wait_after_boarding_counts_in_tour_and_ride():
    # Stop 2 opens at 495; the bus is there at 490 and waits 5 minutes.
    arc = make_arc({(0, 1): 10, (1, 2): 10, (2, 0): 10})
    windows = {1: (0, 480), 2: (495, 600)}

    s = simulate_school_pickup([1, 2], arc, deadline=600, windows=windows)

    assert s.feasible
    assert s.start == pytest.approx(470)
    assert s.arrivals == (pytest.approx(480), pytest.approx(490))
    assert s.waits == (pytest.approx(0), pytest.approx(5))
    assert s.end == pytest.approx(505)
    assert s.tour == pytest.approx(35)
    # student 1 boards at 480 and rides until school: 25 including the 5 minute wait
    assert s.ride_times == (pytest.approx(25), pytest.approx(10))


def test_pickup_window_violation_is_typed_with_position():
    arc = make_arc({(0, 1): 10, (1, 2): 10, (2, 0): 10})
    windows = {1: (480, 490), 2: (400, 482)}

    s = simulate_school_pickup([1, 2], arc, deadline=600, windows=windows)

    assert kinds(s) == [WINDOW]
    assert s.violations[0].position == 1
    assert s.violations[0].amount == pytest.approx(8)


def test_pickup_start_before_day_is_a_violation():
    arc = make_arc({(0, 1): 20, (1, 0): 20})

    s = simulate_school_pickup([1], arc, deadline=30)

    assert kinds(s) == [START_BEFORE_DAY]
    assert s.violations[0].amount == pytest.approx(10)
    assert simulate_school_pickup([1], arc, deadline=30, day_start=-10).feasible


def test_empty_route_is_trivially_feasible():
    arc = make_arc({})
    p = simulate_school_pickup([], arc, deadline=495)
    d = simulate_school_dropoff([], arc, ready=840)
    assert p.feasible and d.feasible
    assert p.arrivals == () and d.arrivals == ()
    assert p.tour == 0 and d.tour == 0


# --------------------------------------------------------------------------
# service time (OQ-MT1-5 b)
# --------------------------------------------------------------------------
def test_service_time_shifts_arrivals_and_counts_in_tour_and_ride():
    arc = make_arc({(0, 1): 10, (1, 2): 10, (2, 0): 10})

    base = simulate_school_pickup([1, 2], arc, deadline=495)
    assert base.start == pytest.approx(465)
    assert base.tour == pytest.approx(30)

    s = simulate_school_pickup([1, 2], arc, deadline=495, service={1: 3})
    assert s.feasible
    assert s.start == pytest.approx(462)
    assert s.arrivals == (pytest.approx(472), pytest.approx(485))
    assert s.end == pytest.approx(495)
    assert s.tour == pytest.approx(33)
    # student 1 boards at 472; own service, travel and arrival all count
    assert s.ride_times == (pytest.approx(23), pytest.approx(10))


def test_sw_boarding_time_is_added_per_sw_student_at_the_stop():
    arc = make_arc({(0, 1): 10, (1, 2): 10, (2, 0): 10})

    s = simulate_school_pickup(
        [1, 2],
        arc,
        deadline=495,
        service={1: 3},
        sw_boarding=2,
        sw_counts={2: 2},  # two Sw students at stop 2 -> 4 minutes
    )

    assert s.feasible
    assert s.services == (pytest.approx(3), pytest.approx(4))
    assert s.start == pytest.approx(458)
    assert s.arrivals == (pytest.approx(468), pytest.approx(481))
    assert s.tour == pytest.approx(37)


def test_service_time_can_push_dropoff_past_day_end():
    arc = make_arc({(0, 1): 10, (1, 0): 10})
    assert simulate_school_dropoff([1], arc, ready=420, day_end=440).feasible

    s = simulate_school_dropoff([1], arc, ready=420, day_end=440, service={1: 5})
    assert kinds(s) == [END_AFTER_DAY]
    assert s.end == pytest.approx(445)


def test_zero_service_equals_no_service():
    arc = make_arc({(0, 1): 10.9, (1, 2): 10.9, (2, 0): 10.2})
    windows = {1: (0, 473)}
    a = simulate_school_pickup([1, 2], arc, deadline=495, windows=windows)
    b = simulate_school_pickup(
        [1, 2],
        arc,
        deadline=495,
        windows=windows,
        service={1: 0, 2: 0},
        sw_boarding=0,
        sw_counts={1: 3},
    )
    assert a == b


def test_schedule_types_are_immutable():
    arc = make_arc({(0, 1): 10, (1, 0): 10})
    s = simulate_school_pickup([1], arc, deadline=495)
    with pytest.raises(Exception):
        s.start = 0  # type: ignore[misc]
    assert isinstance(ScheduleViolation(DEADLINE, None, 2.0, 1.0), ScheduleViolation)


# --------------------------------------------------------------------------
# (6) property tests: independent naive forward replay
# --------------------------------------------------------------------------
def naive_pickup(route, arc, start, deadline, windows, service):
    """Forward replay from `start`; True when every window and the deadline hold."""
    t = float(start)
    prev = 0
    for node in route:
        t += arc(prev, node)
        lo, hi = windows.get(node, (-1e18, 1e18))
        if t < lo:
            t = lo
        if t > hi + EPS:
            return False
        t += service.get(node, 0.0)
        prev = node
    t += arc(prev, 0)
    return t <= deadline + EPS


def naive_dropoff(route, arc, ready, day_end, windows, service):
    t = float(ready)
    prev = 0
    for node in route:
        t += arc(prev, node)
        lo, hi = windows.get(node, (-1e18, 1e18))
        if t < lo:
            t = lo
        if t > hi + EPS:
            return False
        t += service.get(node, 0.0)
        prev = node
    t += arc(prev, 0)
    return t <= day_end + EPS


def random_case(rng):
    n = rng.randint(1, 6)
    route = list(range(1, n + 1))
    decimal = rng.random() < 0.5
    table = {}
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                table[(i, j)] = (
                    round(rng.uniform(1, 25), 1) if decimal else float(rng.randint(1, 25))
                )
    windows = {}
    for node in route:
        if rng.random() < 0.6:
            opening = rng.uniform(150, 480)
            windows[node] = (opening, opening + rng.uniform(5, 120))
    service = {node: rng.choice([0.0, 0.0, 2.0, 3.5]) for node in route}
    return route, make_arc(table), windows, service


def test_property_pickup_feasible_replays_clean_and_infeasible_has_no_departure():
    rng = random.Random(20261027)
    deadline = 500.0
    feasible_seen = infeasible_seen = 0
    grid = [k * 0.05 for k in range(int(deadline / 0.05) + 1)]

    for _ in range(250):
        route, arc, windows, service = random_case(rng)
        s = simulate_school_pickup(
            route, arc, deadline=deadline, windows=windows, service=service
        )
        if s.feasible:
            feasible_seen += 1
            assert naive_pickup(route, arc, s.start, deadline, windows, service)
            # latest departure: a later one (by a visible margin) must fail
            assert not naive_pickup(route, arc, s.start + 0.01, deadline, windows, service)
        else:
            infeasible_seen += 1
            assert not any(
                naive_pickup(route, arc, g, deadline, windows, service) for g in grid
            )

    assert feasible_seen >= 20 and infeasible_seen >= 20


def test_property_pickup_arrivals_match_naive_replay_for_feasible_routes():
    rng = random.Random(7)
    checked = 0
    for _ in range(200):
        route, arc, windows, service = random_case(rng)
        s = simulate_school_pickup(
            route, arc, deadline=500.0, windows=windows, service=service
        )
        if not s.feasible:
            continue
        checked += 1
        t, prev = s.start, 0
        for idx, node in enumerate(route):
            t += arc(prev, node)
            assert s.arrivals[idx] == pytest.approx(t, abs=1e-6)
            lo = windows.get(node, (-1e18, 0))[0]
            if t < lo:
                assert s.waits[idx] == pytest.approx(lo - t, abs=1e-6)
                t = lo
            else:
                assert s.waits[idx] == pytest.approx(0, abs=1e-6)
            t += service.get(node, 0.0)
            prev = node
        assert s.end == pytest.approx(t + arc(prev, 0), abs=1e-6)
    assert checked >= 20


def test_property_dropoff_verdict_matches_naive_replay():
    rng = random.Random(99)
    ready, day_end = 300.0, 520.0
    feasible_seen = infeasible_seen = 0
    for _ in range(250):
        route, arc, windows, service = random_case(rng)
        s = simulate_school_dropoff(
            route, arc, ready=ready, windows=windows, service=service, day_end=day_end
        )
        expected = naive_dropoff(route, arc, ready, day_end, windows, service)
        assert s.feasible == expected
        if expected:
            feasible_seen += 1
        else:
            infeasible_seen += 1
    assert feasible_seen >= 20 and infeasible_seen >= 20
