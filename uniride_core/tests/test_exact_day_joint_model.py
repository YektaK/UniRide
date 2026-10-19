"""WP-E11 J3: joint day model builder, canonical MPS and day oracle (design JOINT_DAY_MODEL_DESIGN.md 2.2, 2.4, 5.2).

Everything here is pure Python: the day oracle (``day_oracle.brute_force_day_optimum``) enumerates every route
set of a tiny day on its own arithmetic, and the model is solved by a tiny exhaustive enumeration of the MIP
(``day_oracle.enumerate_stage_optimum``, at most 12 integer column variables). No external solver is used.
"""
from __future__ import annotations

import hashlib
import random

import pytest

from uniride_core.exact import VehicleTypeSpec, WaveInstance, compute_matrix_sha256
from uniride_core.exact.day_instance import READY, build_day_instance
from uniride_core.exact.day_joint import build_joint_model
from uniride_core.exact.day_oracle import (
    MAX_ENUMERATION_COLUMNS,
    brute_force_day_optimum,
    enumerate_lexicographic_optimum,
    enumerate_stage_optimum,
)

DEPOT = "D.Kampus"
LARGE = VehicleTypeSpec("large", 4, 5, 10)
CAR = VehicleTypeSpec("car", 0, 4, 10)  # sedan: no Sw (H01)
DOBLO = VehicleTypeSpec("doblo", 1, 3, 10, total_capacity=3)  # Doblo cap3 (H03)
ARCS = {(DEPOT, "SwA"): 10, ("SwA", DEPOT): 10, (DEPOT, "SoB"): 15, ("SoB", DEPOT): 15, ("SwA", "SoB"): 7, ("SoB", "SwA"): 7}
# nonmetric revisit (test_exact_route_enumeration.REVISIT_L): the only way to cover B is A -> B -> A
REVISIT = {(DEPOT, "A"): 5, (DEPOT, "B"): 100, ("A", DEPOT): 4, ("A", "B"): 5, ("B", DEPOT): 100, ("B", "A"): 6}


def make_wave(wave_id, direction, anchor, locs, arcs, *, ride=40, tour=90, date="2026-10-05"):
    codes = [DEPOT] + [c for c, _ in locs]
    n = len(codes)
    rows = tuple(tuple(0 if i == j or codes[i] == codes[j] else arcs[(codes[i], codes[j])] for j in range(n))
                 for i in range(n))
    return WaveInstance(
        wave_id=wave_id, service_date=date, direction=direction, anchor_minutes=anchor, max_ride_minutes=ride,
        max_tour_minutes=tour, depot_code=DEPOT, occurrence_ids=tuple(f"{wave_id}:{i}" for i in range(len(locs))),
        location_codes=tuple(c for c, _ in locs), classes=tuple(k for _, k in locs), matrix=rows,
        matrix_sha256=compute_matrix_sha256(rows), arc_slice_sha256="x", declared_snapshot_sha256="y")


def transposed(arcs):
    return {(b, a): v for (a, b), v in arcs.items()}


def cell(waves, types):
    inst = build_day_instance(waves, types)
    assert inst.status == READY
    return inst


def _day_column(inst, var):
    wave_index, column_index = var.ref
    return next(c for c in inst.waves[wave_index].columns if c.column_index == column_index)


def model_tuple(inst, *, large_limit=None, aggregate=False):
    return enumerate_lexicographic_optimum(inst, large_limit=large_limit, aggregate=aggregate)


# ------------------------------------------------------------------ hand instances (oracle set)
def hand_cases():
    """(name, waves, types, large_limit); every model has <= 12 integer column variables."""
    cases = []
    for d1, d2 in (("pickup", "pickup"), ("pickup", "dropoff"), ("dropoff", "pickup"), ("dropoff", "dropoff")):
        for gap in (0, 12, 60):
            w1 = make_wave("w1", d1, 500, [("SwA", "Sw"), ("SoB", "So")], ARCS)
            w2 = make_wave("w2", d2, 500 + gap, [("SoB", "So"), ("SoB", "So")], ARCS)
            tag = f"{d1}-{d2}-gap{gap}"
            cases.append((f"homog-{tag}", [w1, w2], (LARGE,), None))
            for L in (0, 1, 2):
                cases.append((f"sedan-{tag}-L{L}", [w1, w2], (LARGE, CAR), L))
            w3 = make_wave("w3", d2, 500 + gap, [("SwA", "Sw"), ("SoB", "So")], ARCS)
            for L in (0, 1, 2):
                cases.append((f"doblo-{tag}-L{L}", [w1, w3], (LARGE, DOBLO), L))
    # nonmetric revisit wave (both directions), plus a small wave that overlaps it
    for direction in ("pickup", "dropoff"):
        arcs = REVISIT if direction == "pickup" else transposed(REVISIT)
        rev = make_wave("rev", direction, 520, [("A", "So"), ("A", "So"), ("B", "So")], arcs, ride=50, tour=60)
        other = make_wave("oth", "pickup", 530, [("A", "So")], REVISIT, ride=50, tour=60)
        cases.append((f"revisit-{direction}-homog", [rev, other], (LARGE,), None))
        for L in (0, 1):
            cases.append((f"revisit-{direction}-sedan-L{L}", [rev, other], (LARGE, CAR), L))
            cases.append((f"revisit-{direction}-doblo-L{L}", [rev, other], (LARGE, DOBLO), L))
    return cases


HAND = hand_cases()


def random_cases():
    cases = []
    for seed in range(80):
        rng = random.Random(seed)
        names = ["P", "Q", "R"]
        arcs = {}
        for a in [DEPOT] + names:
            for b in [DEPOT] + names:
                if a != b:
                    arcs[(a, b)] = rng.randint(3, 20)
        ride, tour = rng.choice((25, 40)), rng.choice((50, 90))  # one ride/tour limit per cell (J1 contract)
        waves = []
        for k in range(rng.choice((2, 3))):
            locs = [(rng.choice(names), rng.choice(("Sw", "So"))) for _ in range(rng.choice((1, 2)))]
            waves.append(make_wave(f"r{k}", rng.choice(("pickup", "dropoff")), 500 + rng.choice((0, 5, 15, 30, 70)), locs,
                                   arcs, ride=ride, tour=tour))
        types = rng.choice(((LARGE,), (LARGE, CAR), (LARGE, DOBLO)))
        cases.append((f"rand{seed}", waves, types, None if len(types) == 1 else rng.choice((0, 1, 2))))
    return cases


RANDOM = random_cases()


def _fits(waves, types):
    inst = build_day_instance(waves, types)
    return inst.status == READY and 0 < inst.columns_total <= MAX_ENUMERATION_COLUMNS


# ------------------------------------------------------------------ 1. byte-identical MPS
@pytest.mark.parametrize("aggregate", [False, True])
@pytest.mark.parametrize("types,large_limit,stages", [((LARGE,), None, (1, 2)), ((LARGE, CAR), 1, (1, 2, 3)),
                                                      ((LARGE, DOBLO), 2, (1, 2, 3))])
def test_two_builds_of_one_cell_give_byte_identical_mps(types, large_limit, stages, aggregate):
    fixed = {"peak": 1, "total_minutes": 77}
    waves = [make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS),
             make_wave("w2", "dropoff", 505, [("SoB", "So"), ("SoB", "So")], ARCS)]
    for stage in stages:
        mps = []
        for _ in range(2):  # fresh instance each time: nothing may depend on object identity or dict history
            inst = build_day_instance(list(waves), types)
            m = build_joint_model(inst, stage=stage, large_limit=large_limit, fixed=fixed, aggregate=aggregate)
            mps.append((m.to_mps(), m.mps_sha256))
        assert mps[0][0] == mps[1][0] and isinstance(mps[0][0], bytes)
        assert mps[0][1] == mps[1][1] == hashlib.sha256(mps[0][0]).hexdigest()
        assert mps[0][0].endswith(b"ENDATA\n") and b"\r" not in mps[0][0]


def test_aggregation_and_stage_change_the_model_bytes():
    waves = [make_wave("w1", "pickup", 500, [("SoB", "So"), ("SoB", "So"), ("SoB", "So")], ARCS, ride=60, tour=90)]
    inst = cell(waves, (LARGE,))
    plain = build_joint_model(inst, stage=1).to_mps()
    agg = build_joint_model(inst, stage=1, aggregate=True).to_mps()
    s2 = build_joint_model(inst, stage=2, fixed={"peak": 1}).to_mps()
    assert len({plain, agg, s2}) == 3


# ------------------------------------------------------------------ 2. oracle equality, plain and aggregated
def _check_case(name, waves, types, large_limit):
    inst = build_day_instance(waves, types)
    oracle = brute_force_day_optimum(waves, types, large_limit=large_limit)
    plain = model_tuple(inst, large_limit=large_limit, aggregate=False)
    agg = model_tuple(inst, large_limit=large_limit, aggregate=True)
    assert plain == agg == oracle.objective, f"{name}: plain {plain} aggregated {agg} oracle {oracle.objective}"
    return oracle.objective


@pytest.mark.parametrize("name,waves,types,large_limit", HAND, ids=[c[0] for c in HAND])
def test_hand_instances_model_equals_day_oracle_plain_and_aggregated(name, waves, types, large_limit):
    assert _fits(waves, types), f"{name} exceeds the enumeration limit"
    _check_case(name, waves, types, large_limit)


def test_oracle_set_covers_both_directions_all_type_sets_and_feasible_and_infeasible_cells():
    objectives = {}
    for name, waves, types, large_limit in HAND:
        objectives[name] = _check_case(name, waves, types, large_limit)
    names = list(objectives)
    for kind in ("homog", "sedan", "doblo", "revisit-pickup", "revisit-dropoff"):
        assert any(n.startswith(kind) for n in names)
    assert any(v is None for v in objectives.values())  # at least one infeasible L
    assert any(v is not None for v in objectives.values())
    assert any(v is not None and len(v) == 3 for v in objectives.values())  # typed tuple (S, total, car minutes)
    # the revisit wave really takes the A -> B -> A route (tour 20 pickup), so its minutes appear in the optimum
    assert objectives["revisit-pickup-homog"][1] >= 20


def test_random_instances_model_equals_day_oracle_plain_and_aggregated():
    checked, typed_feasible, infeasible = 0, 0, 0
    for name, waves, types, large_limit in RANDOM:
        if not _fits(waves, types):
            continue
        obj = _check_case(name, waves, types, large_limit)
        checked += 1
        typed_feasible += obj is not None and len(types) > 1
        infeasible += obj is None
    assert checked >= 40 and typed_feasible >= 10


# ------------------------------------------------------------------ 3. a column needed twice (E02)
def test_a_column_needed_twice_has_upper_bound_two_and_two_copies_in_the_optimum():
    one_seat = VehicleTypeSpec("one", 1, 0, 10)  # a single Sw seat: every Sw needs its own route
    wave = make_wave("w", "pickup", 500, [("SwA", "Sw"), ("SwA", "Sw")], ARCS)
    inst = cell([wave], (one_seat,))
    assert len(inst.waves[0].columns) == 1 and inst.waves[0].columns[0].multiplicity == (1,)
    for aggregate in (False, True):
        m = build_joint_model(inst, stage=1, aggregate=aggregate)
        col_var = [v for v in m.variables if v.kind == "column"]
        assert [v.upper for v in col_var] == [2]  # E02: floor(n / a) = 2, not binary
        sol = enumerate_stage_optimum(m)
        assert sol is not None and sol.objective == 2  # K = 2 needs lambda = 2
        assert sol.values[col_var[0].name] == 2
    assert brute_force_day_optimum([wave], (one_seat,)).objective == (2, 40)
    assert model_tuple(inst) == (2, 40)


def test_upper_bound_is_the_minimum_over_items_of_floor_n_over_a():
    # items (SwA,Sw) n = 3 and (SoB,So) n = 2; column {SwA, SoB} -> min(3, 2) = 2; column {SwA} -> 3; {SoB} -> 2
    wave = make_wave("w", "pickup", 500, [("SwA", "Sw")] * 3 + [("SoB", "So")] * 2, ARCS, ride=60, tour=120)
    inst = cell([wave], (LARGE,))
    m = build_joint_model(inst, stage=1)
    day_cols = inst.waves[0].columns
    ub = {v.ref[1]: v.upper for v in m.variables if v.kind == "column"}
    for c in day_cols:
        want = min(inst.waves[0].items[i].multiplicity // a for i, a in enumerate(c.multiplicity) if a > 0)
        assert ub[c.column_index] == want
    assert 3 in ub.values() and 2 in ub.values()


# ------------------------------------------------------------------ 4. cooldown 0 vs 10
def test_cooldown_zero_versus_ten_changes_the_oracle_optimum():
    # route 1 pickup ends at 100 (tour 20); route 2 dropoff starts at 105. cooldown 10 keeps vehicle 1 busy until 110.
    def day(cd):
        t = VehicleTypeSpec("t", 4, 5, cd)
        return ([make_wave("a", "pickup", 100, [("SwA", "Sw")], ARCS), make_wave("b", "dropoff", 105, [("SwA", "Sw")], ARCS)], (t,))

    waves0, types0 = day(0)
    waves10, types10 = day(10)
    o0 = brute_force_day_optimum(waves0, types0).objective
    o10 = brute_force_day_optimum(waves10, types10).objective
    assert o0 == (1, 40) and o10 == (2, 40)
    assert model_tuple(build_day_instance(waves0, types0)) == o0
    assert model_tuple(build_day_instance(waves10, types10), aggregate=True) == o10


def test_cooldown_is_per_type():
    big = VehicleTypeSpec("large", 4, 5, 10)
    car = VehicleTypeSpec("car", 0, 4, 0)
    # tour 30: route a is busy on [70, 100 + cd), route b starts at 105
    waves = [make_wave("a", "pickup", 100, [("SoB", "So")], ARCS), make_wave("b", "dropoff", 105, [("SoB", "So")], ARCS)]
    inst = cell(waves, (big, car))
    # large cooldown 10 -> two large routes overlap at 105; the car has cooldown 0 -> one car serves both
    assert brute_force_day_optimum(waves, (big, car), large_limit=0).objective == (1, 60, 60)
    assert model_tuple(inst, large_limit=0) == (1, 60, 60)


# ------------------------------------------------------------------ 5. typed model never crosses types
@pytest.mark.parametrize("other", [CAR, DOBLO], ids=["sedan", "doblo"])
@pytest.mark.parametrize("aggregate", [False, True])
def test_typed_model_never_assigns_a_column_to_the_other_type(other, aggregate):
    waves = [make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS),
             make_wave("w2", "dropoff", 505, [("SoB", "So"), ("SoB", "So")], ARCS)]
    inst = cell(waves, (LARGE, other))
    by_type = {c.type_id: [] for c in (LARGE, other)}
    for w in inst.waves:
        for c in w.columns:
            by_type[c.type_id].append((w.wave_id, c.column_index))
    assert by_type[LARGE.type_id] and by_type[other.type_id]
    for stage in (1, 2, 3):
        m = build_joint_model(inst, stage=stage, large_limit=2, fixed={"peak": 1, "total_minutes": 100}, aggregate=aggregate)
        # structural: a concurrency row of a type contains only that type's columns (directly or through z)
        for row in m.rows:
            if row.kind != "concurrency":
                continue
            types_in_row = set()
            for vi, _ in row.terms:
                v = m.variables[vi]
                if v.kind in ("column", "aggregate"):
                    types_in_row.add(v.type_id)
            assert types_in_row <= {row.type_id}
    # behavioural: in the optimum every chosen column belongs to the type that admits it
    m = build_joint_model(inst, stage=1, large_limit=2, aggregate=aggregate)
    sol = enumerate_stage_optimum(m)
    assert sol is not None
    chosen = [v for v in m.variables if v.kind == "column" and sol.values[v.name] > 0]
    assert chosen
    spec = {LARGE.type_id: LARGE, other.type_id: other}
    for v in chosen:
        col = _day_column(inst, v)
        t = spec[col.type_id]
        assert col.type_id == v.type_id
        assert col.sw_count <= t.sw_capacity and col.so_count <= t.so_capacity
        assert t.total_capacity is None or col.sw_count + col.so_count <= t.total_capacity
        if col.sw_count > 0 and other is CAR:
            assert col.type_id == "large"  # the sedan never carries the Sw student


def test_typed_large_cap_is_a_constant_and_the_minimised_peak_is_a_variable():
    waves = [make_wave("w1", "pickup", 500, [("SoB", "So")], ARCS), make_wave("w2", "pickup", 500, [("SoB", "So")], ARCS)]
    inst = cell(waves, (LARGE, CAR))
    m = build_joint_model(inst, stage=1, large_limit=1)
    rows = {r.name: r for r in m.rows}
    large_rows = [r for r in m.rows if r.kind == "concurrency" and r.type_id == "large"]
    car_rows = [r for r in m.rows if r.kind == "concurrency" and r.type_id == "car"]
    assert large_rows and car_rows
    assert all(r.sense == "L" and r.rhs == 1 and all(c == 1 for _, c in r.terms) for r in large_rows)
    peak = [i for i, v in enumerate(m.variables) if v.kind == "peak"]
    assert len(peak) == 1
    assert all(r.rhs == 0 and (peak[0], -1) in r.terms for r in car_rows)
    assert rows  # unique names
    assert len({r.name for r in m.rows}) == len(m.rows) and len({v.name for v in m.variables}) == len(m.variables)


# ------------------------------------------------------------------ event points use DayColumn.interval (J1 reviewer note)
def test_event_points_come_from_interval_not_from_busy_end_minutes():
    # a zero-tour column (a student at the depot) is busy on [10000, 10001 + 1000) centi-minutes in production, one
    # centi-unit longer than busy_end * 100. A route that starts exactly cooldown minutes later (110) is therefore
    # still overlapped, so one vehicle is not enough.
    types = (VehicleTypeSpec("t", 4, 5, 10),)
    waves = [make_wave("z", "pickup", 100, [(DEPOT, "Sw")], ARCS), make_wave("n", "dropoff", 110, [("SwA", "Sw")], ARCS)]
    inst = cell(waves, types)
    zero = inst.waves[0].columns[0]
    assert zero.tour == 0 and zero.interval(100) == (10000, 10001, 11001)
    assert brute_force_day_optimum(waves, types).objective == (2, 20)
    for aggregate in (False, True):
        assert model_tuple(inst, aggregate=aggregate) == (2, 20)
    # one minute later the vehicle is free
    waves = [make_wave("z", "pickup", 100, [(DEPOT, "Sw")], ARCS), make_wave("n", "dropoff", 111, [("SwA", "Sw")], ARCS)]
    assert brute_force_day_optimum(waves, types).objective == (1, 20)
    assert model_tuple(cell(waves, types)) == (1, 20)


# ------------------------------------------------------------------ model summary and structure
def test_model_summary_counts_rows_and_columns_for_each_stage():
    waves = [make_wave("w1", "pickup", 500, [("SwA", "Sw"), ("SoB", "So")], ARCS),
             make_wave("w2", "dropoff", 505, [("SoB", "So"), ("SoB", "So")], ARCS)]
    inst = cell(waves, (LARGE, CAR))
    m1 = build_joint_model(inst, stage=1, large_limit=1)
    m2 = build_joint_model(inst, stage=2, large_limit=1, fixed={"peak": 1})
    m3 = build_joint_model(inst, stage=3, large_limit=1, fixed={"peak": 1, "total_minutes": 100})
    c = m1.counts
    assert c["column_variables"] == inst.columns_total and c["peak_variables"] == 1
    assert c["cover_rows"] == sum(len(w.items) for w in inst.waves)
    assert m2.counts["cover_rows"] == m3.counts["cover_rows"] == c["cover_rows"]
    assert m3.counts["fix_total_rows"] == 1 and m1.counts["fix_total_rows"] == 0
    peak2 = next(v for v in m2.variables if v.kind == "peak")
    assert peak2.lower == peak2.upper == 1
    # stage 1 objective is the peak only; stage 2 minutes; stage 3 car minutes only
    assert [v.name for v in m1.variables if v.objective] == ["peak"]
    assert all(v.objective == v.tour for v in m2.variables if v.kind == "column")
    assert all(v.objective == (v.tour if v.type_id == "car" else 0) for v in m3.variables if v.kind == "column")


def test_homogeneous_stages_and_refusals():
    inst = cell([make_wave("w", "pickup", 500, [("SwA", "Sw")], ARCS)], (LARGE,))
    with pytest.raises(ValueError):
        build_joint_model(inst, stage=3)
    with pytest.raises(ValueError):
        build_joint_model(inst, stage=2)  # needs the stage-1 value
    typed = cell([make_wave("w", "pickup", 500, [("SwA", "Sw")], ARCS)], (LARGE, CAR))
    with pytest.raises(ValueError):
        build_joint_model(typed, stage=1)  # needs the large limit
    with pytest.raises(ValueError):
        build_joint_model(typed, stage=3, large_limit=1, fixed={"peak": 1})  # needs total minutes
    capped = build_day_instance([make_wave("w", "pickup", 500, [("SwA", "Sw")], ARCS)], (LARGE,), column_cap=0)
    with pytest.raises(ValueError):
        build_joint_model(capped, stage=1)  # only a ready cell is modelled


def test_max_cars_bounds_the_minimised_peak():
    waves = [make_wave("w1", "pickup", 500, [("SoB", "So")], ARCS), make_wave("w2", "pickup", 500, [("SoB", "So")], ARCS)]
    inst = cell(waves, (LARGE, CAR))
    m = build_joint_model(inst, stage=1, large_limit=0, max_cars=1)
    assert next(v for v in m.variables if v.kind == "peak").upper == 1
    assert enumerate_stage_optimum(m) is None  # two concurrent routes, no large vehicle, one car
    assert enumerate_stage_optimum(build_joint_model(inst, stage=1, large_limit=0, max_cars=2)).objective == 2


def test_aggregation_adds_aggregates_only_for_groups_of_equal_wave_type_and_tour():
    wave = make_wave("w", "pickup", 500, [("SoB", "So")] * 3, ARCS, ride=90, tour=120)
    inst = cell([wave], (LARGE,))
    plain = build_joint_model(inst, stage=1)
    agg = build_joint_model(inst, stage=1, aggregate=True)
    assert plain.counts["aggregate_variables"] == 0 and agg.counts["aggregate_variables"] >= 0
    # every aggregate sums only columns of one (wave, type, tour)
    for v in agg.variables:
        if v.kind == "aggregate":
            link = next(r for r in agg.rows if r.kind == "link" and agg.variables[r.terms[0][0]] is v)
            members = [agg.variables[i] for i, _ in link.terms[1:]]
            assert len({(m.ref[0], m.type_id, m.tour) for m in members}) == 1 and len(members) > 1
    assert agg.counts["concurrency_nonzeros"] <= plain.counts["concurrency_nonzeros"]
