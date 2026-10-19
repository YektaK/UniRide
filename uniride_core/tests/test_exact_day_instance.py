"""WP-E11 J1: day instance (columns, busy intervals, service-day filter), design JOINT_DAY_MODEL_DESIGN.md 1.2, 2.1, 2.3."""
from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from uniride_core.exact import VehicleTypeSpec, WaveInstance, compute_matrix_sha256
from uniride_core.exact.day_instance import (
    NOT_RUN_ENUMERATION_CAP,
    READY,
    SERVICE_DAY_END_MINUTES,
    build_day_instance,
)
from uniride_core.planning import fleet_selection_request as fsr

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "paper" / "results"
COUNTS_CSV = RESULTS / "week-2026-10-05-exact" / "wp-e1-enumeration" / "enumeration_counts.csv"
DEPOT = "D.Kampus"


def make_wave(wave_id, direction, anchor, locs, matrix_by_loc, *, date="2026-10-05", ride=40, tour=90):
    """A WaveInstance from a location-level matrix ``matrix_by_loc[(a, b)]``; ``locs`` = [(code, class), ...]."""
    codes = [DEPOT] + [c for c, _ in locs]
    n = len(codes)
    rows = []
    for i in range(n):
        rows.append(tuple(0 if i == j or codes[i] == codes[j] else matrix_by_loc[(codes[i], codes[j])] for j in range(n)))
    matrix = tuple(rows)
    return WaveInstance(
        wave_id=wave_id, service_date=date, direction=direction, anchor_minutes=anchor, max_ride_minutes=ride,
        max_tour_minutes=tour, depot_code=DEPOT, occurrence_ids=tuple(f"{wave_id}:{i}" for i in range(len(locs))),
        location_codes=tuple(c for c, _ in locs), classes=tuple(k for _, k in locs), matrix=matrix,
        matrix_sha256=compute_matrix_sha256(matrix), arc_slice_sha256="x", declared_snapshot_sha256="y")


# location arcs: depot<->A 10, depot<->B 15, A<->B 7 (symmetric)
ARCS = {(DEPOT, "SwA"): 10, ("SwA", DEPOT): 10, (DEPOT, "SoB"): 15, ("SoB", DEPOT): 15, ("SwA", "SoB"): 7, ("SoB", "SwA"): 7}
LOCS = [("SwA", "Sw"), ("SwA", "Sw"), ("SoB", "So")]
LARGE = VehicleTypeSpec("large", 4, 5, 10)
CAR = VehicleTypeSpec("car", 0, 4, 5)


def _facts_of(wave, enumeration, col):
    """RouteFacts of a column as the production request builder sees a verified route."""
    nodes = []
    used = [0] * len(enumeration.items)
    for it in col.stop_order:
        nodes.append(enumeration.items[it].nodes[used[it]])
        used[it] += 1
    path = [0] + nodes + [0]
    durations = tuple(wave.matrix[a][b] for a, b in zip(path, path[1:]))
    total = sum(durations)
    assert total == col.tour
    start = wave.anchor_minutes - total if wave.direction == "pickup" else wave.anchor_minutes
    end = wave.anchor_minutes if wave.direction == "pickup" else wave.anchor_minutes + total
    sw = sum(m for m, it in zip(col.multiplicity, enumeration.items) if it.cls == "Sw")
    so = sum(col.multiplicity) - sw
    return fsr.RouteFacts(start, end, durations, wave.direction, sw, so)


def _production_interval(wave, enumeration, col, types, time_scale):
    """(start, end, busy_end) from ``build_selection_request`` for one route."""
    by_id = {t.type_id: t for t in types}
    spec = by_id[col.type_id]
    limits = [fsr.TypeLimits(t.type_id, t.sw_capacity, t.so_capacity, t.total_capacity) for t in types]
    facts = _facts_of(wave, enumeration, col)
    req = fsr.build_selection_request(
        [("w", [("base", True, [facts])])], fixed_type=limits[0], minimise_type=limits[-1], max_large=1,
        ride_default=wave.max_ride_minutes, tour_default=wave.max_tour_minutes,
        cooldown_large_minutes=types[0].cooldown_minutes, cooldown_car_minutes=types[-1].cooldown_minutes,
        time_scale=time_scale)
    body = req["waves"][0]["options"][0]["routes"][0]
    cd = req["cooldown_large"] if spec is types[0] else req["cooldown_car"]
    return body["start"], body["end"], body["end"] + cd


# ---------- 1. interval equals the production request builder at time_scale = 100 ----------
@pytest.mark.parametrize("direction,anchor", [("pickup", 525), ("dropoff", 975)])
def test_column_interval_equals_build_selection_request_hand_instance(direction, anchor):
    wave = make_wave("w1", direction, anchor, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE, CAR))
    assert inst.status == READY
    day_wave = inst.waves[0]
    assert len(day_wave.columns) > 0 and {c.type_id for c in day_wave.columns} == {"large", "car"}
    for col in day_wave.columns:
        want = _production_interval(wave, day_wave.enumeration, day_wave.enumeration.columns[col.column_index], (LARGE, CAR), 100)
        assert col.interval(100) == want
        # integer-minute view used by the MIP: busy end = end + cooldown of the column's own type
        assert col.busy_end == col.end + {"large": 10, "car": 5}[col.type_id]


def test_zero_tour_column_keeps_the_one_unit_minimum_of_the_request_builder():
    wave = make_wave("w0", "pickup", 100, [(DEPOT, "Sw")], ARCS)
    inst = build_day_instance([wave], (LARGE,))
    (col,) = inst.waves[0].columns
    assert col.tour == 0 and (col.start, col.end) == (100, 100)
    assert col.interval(100) == (10000, 10001, 10001 + 1000)
    assert col.interval(100) == _production_interval(wave, inst.waves[0].enumeration, inst.waves[0].enumeration.columns[0], (LARGE,), 100)


def test_column_interval_equals_build_selection_request_on_archived_waves():
    loader = _load_loader("exact_archive_loader_j1a")
    camp = loader.load_campaign(RESULTS / "week-2026-10-05-fleet")
    types = camp.fleet_types
    checked = 0
    for wave in camp.waves_for(50)[:12]:
        inst = build_day_instance([wave], types, service_date=wave.service_date, filter_service_day=False)
        day_wave = inst.waves[0]
        for col in day_wave.columns:
            enum_col = day_wave.enumeration.columns[col.column_index]
            assert col.interval(100) == _production_interval(wave, day_wave.enumeration, enum_col, types, 100)
            checked += 1
    assert checked > 100


# ---------- 2. anchoring and the service-day filter ----------
def test_pickup_anchoring_ends_at_the_anchor_and_a_route_before_minute_zero_is_dropped():
    # tours: {SwA}=20, {SwA,SwA}=20 (same location), {SoB}=30, {SwA,SoB}: 10+7+15=32, ...
    wave = make_wave("early", "pickup", 25, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE,))
    cols = inst.waves[0].columns
    assert inst.waves[0].enumerated_columns > len(cols) > 0
    assert inst.waves[0].filtered_columns == inst.waves[0].enumerated_columns - len(cols)
    for c in cols:
        assert c.end == 25 and c.start == 25 - c.tour >= 0
    dropped = [c for c in inst.waves[0].enumeration.columns if c.tour > 25]
    assert dropped and len(dropped) == inst.waves[0].filtered_columns


def test_dropoff_anchoring_starts_at_the_anchor_and_a_route_after_minute_1440_is_dropped():
    wave = make_wave("late", "dropoff", SERVICE_DAY_END_MINUTES - 25, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE,))
    cols = inst.waves[0].columns
    assert len(cols) > 0
    for c in cols:
        assert c.start == SERVICE_DAY_END_MINUTES - 25 and c.end == c.start + c.tour <= SERVICE_DAY_END_MINUTES
    assert inst.waves[0].filtered_columns == sum(1 for c in inst.waves[0].enumeration.columns if c.tour > 25) > 0


def test_a_route_that_ends_exactly_at_minute_1440_or_starts_exactly_at_zero_is_kept():
    pick = make_wave("p", "pickup", 20, [("SwA", "Sw")], ARCS)  # tour 20 -> start 0
    drop = make_wave("d", "dropoff", SERVICE_DAY_END_MINUTES - 20, [("SwA", "Sw")], ARCS)  # tour 20 -> end 1440
    for wave, edge in ((pick, "start"), (drop, "end")):
        inst = build_day_instance([wave], (LARGE,))
        (col,) = inst.waves[0].columns
        assert getattr(col, edge) == (0 if edge == "start" else SERVICE_DAY_END_MINUTES)
        assert inst.waves[0].filtered_columns == 0


def test_filter_can_be_disabled_for_measurement():
    wave = make_wave("early", "pickup", 25, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE,), filter_service_day=False)
    assert len(inst.waves[0].columns) == inst.waves[0].enumerated_columns
    assert min(c.start for c in inst.waves[0].columns) < 0


# ---------- 3. incomplete enumeration refuses the cell ----------
def test_one_capped_wave_gives_not_run_enumeration_cap_and_no_columns():
    small = make_wave("small", "pickup", 525, [("SwA", "Sw")], ARCS)
    big = make_wave("big", "dropoff", 975, LOCS, ARCS)
    ok = build_day_instance([small, big], (LARGE,))
    assert ok.status == READY and all(w.enumeration_status == "complete" for w in ok.waves)
    # a column cap of 1 lets the one-column wave through and stops the other
    capped = build_day_instance([small, big], (LARGE,), column_cap=1)
    assert capped.status == NOT_RUN_ENUMERATION_CAP == "not_run_enumeration_cap"
    assert [(b.wave_id, b.enumeration_status, b.cap_fired) for b in capped.blocking] == [("big", "count_cap", "column_cap")]
    assert all(w.columns == () for w in capped.waves)
    assert [w.enumeration_status for w in capped.waves] == ["complete", "count_cap"]


def test_wall_clock_abort_also_refuses_the_cell():
    wave = make_wave("big", "dropoff", 975, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE,), wall_clock_limit=-1.0)
    assert inst.status == NOT_RUN_ENUMERATION_CAP
    assert inst.blocking[0].enumeration_status == "timing_dependent_abort"


# ---------- input contract ----------
def test_mixed_dates_or_rides_or_duplicate_ids_are_rejected():
    a = make_wave("a", "pickup", 525, LOCS, ARCS)
    with pytest.raises(ValueError, match="service date"):
        build_day_instance([a, make_wave("b", "pickup", 600, LOCS, ARCS, date="2026-10-06")], (LARGE,))
    with pytest.raises(ValueError, match="ride"):
        build_day_instance([a, make_wave("b", "pickup", 600, LOCS, ARCS, ride=50)], (LARGE,))
    with pytest.raises(ValueError, match="duplicate wave"):
        build_day_instance([a, make_wave("a", "pickup", 600, LOCS, ARCS)], (LARGE,))
    with pytest.raises(ValueError):
        build_day_instance([], (LARGE,))
    with pytest.raises(ValueError):
        build_day_instance([a], ())


def test_column_data_carries_type_multiplicity_tour_and_class_counts():
    wave = make_wave("w1", "pickup", 525, LOCS, ARCS)
    inst = build_day_instance([wave], (LARGE, CAR))
    day_wave = inst.waves[0]
    assert sorted((i.location_code, i.cls, i.multiplicity) for i in day_wave.items) == [("SoB", "So", 1), ("SwA", "Sw", 2)]
    sw_items = [i for i, it in enumerate(day_wave.items) if it.cls == "Sw"]
    for col in day_wave.columns:
        enum_col = day_wave.enumeration.columns[col.column_index]
        assert (col.type_id, col.multiplicity, col.stop_order, col.tour, col.ride) == (
            enum_col.type_id, enum_col.multiplicity, enum_col.stop_order, enum_col.tour, enum_col.ride)
        assert col.sw_count == sum(col.multiplicity[i] for i in sw_items)
        assert col.sw_count + col.so_count == sum(col.multiplicity)
        assert col.type_index == {"large": 0, "car": 1}[col.type_id]
        # the sedan has no Sw seat
        assert not (col.type_id == "car" and col.sw_count)


# ---------- 4. archive: per-day column totals equal the WP-E1 sums ----------
def _load_loader(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "exact_archive_loader.py")
    loader = importlib.util.module_from_spec(spec)
    sys.modules[name] = loader
    spec.loader.exec_module(loader)
    return loader


FLEET_LABEL = {"4sw5so": "single_4sw5so", "fleet": "large+sedan", "minivan-cap3": "large+doblo_cap3"}


@pytest.fixture(scope="module")
def archived_day_instances():
    loader = _load_loader("exact_archive_loader_j1b")
    campaigns = loader.load_all_valid(RESULTS)
    out = {}
    for key, camp in campaigns.items():
        for ride in camp.rides:
            by_date = defaultdict(list)
            for w in camp.waves_for(ride):
                by_date[w.service_date].append(w)
            for date, waves in sorted(by_date.items()):
                out[(FLEET_LABEL[key], date, ride)] = build_day_instance(waves, camp.fleet_types, service_date=date)
    return out


def test_per_day_column_totals_equal_the_wp_e1_sums(archived_day_instances, capsys):
    expected = defaultdict(int)
    waves_expected = defaultdict(int)
    with COUNTS_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            expected[(row["fleet"], row["service_date"], int(row["R"]))] += int(row["columns"])
            waves_expected[(row["fleet"], row["service_date"], int(row["R"]))] += 1
    assert len(archived_day_instances) == len(expected) == 3 * 5 * 4
    lines = []
    for key in sorted(archived_day_instances):
        inst = archived_day_instances[key]
        assert inst.status == READY, key
        assert len(inst.waves) == waves_expected[key], key
        assert inst.enumerated_columns == expected[key], key
        assert inst.columns_total + inst.filtered_total == inst.enumerated_columns
        assert inst.columns_total == sum(len(w.columns) for w in inst.waves)
        lines.append(f"{key[0]:17s} {key[1]} R{key[2]}: waves={len(inst.waves):2d} enumerated={inst.enumerated_columns:6d} "
                     f"kept={inst.columns_total:6d} filtered={inst.filtered_total:5d}")
    with capsys.disabled():
        print("\nJ1 counts per (fleet, date, R):\n" + "\n".join(lines))


@pytest.mark.parametrize("fleet,largest", [("single_4sw5so", 45302), ("large+sedan", 47215), ("large+doblo_cap3", 46571)])
def test_largest_day_totals(archived_day_instances, fleet, largest):
    totals = {k: v.enumerated_columns for k, v in archived_day_instances.items() if k[0] == fleet}
    assert max(totals.values()) == largest
    assert totals[(fleet, "2026-10-05", 90)] == largest


def test_every_kept_column_lies_inside_the_service_day(archived_day_instances):
    for inst in archived_day_instances.values():
        for w in inst.waves:
            for c in w.columns:
                assert 0 <= c.start <= c.end <= SERVICE_DAY_END_MINUTES
