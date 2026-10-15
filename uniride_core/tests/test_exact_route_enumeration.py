"""WP-E1: route enumeration (design EXACT_SOLVER_AMPL_DESIGN.md section 1.1 Step A) and
its brute-force oracle; verification rows of section 8 that need no AMPL."""
from __future__ import annotations

import ast
import itertools
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from exact_enum_helpers import column_search, random_instance

REPO = Path(__file__).resolve().parents[2]
ORACLE_INSTANCES = 500


def _enum(inst, **kw):
    from uniride_core.exact.route_enumeration import enumerate_routes

    return enumerate_routes(inst["direction"], inst["matrix"], inst["location_codes"], inst["classes"],
                            inst["types"], max_ride=inst["ride"], max_tour=inst["tour"], **kw)


def _oracle(inst):
    from uniride_core.exact.brute_force import brute_force_optimum

    return brute_force_optimum(inst["direction"], inst["matrix"], inst["classes"], inst["types"],
                               max_ride=inst["ride"], max_tour=inst["tour"],
                               minimize_type=inst["minimize_type"], quota=inst["quota"])


def _route_cost(direction, matrix, nodes):
    """(tour, ride) of depot -> nodes -> depot under F1; None if an arc is missing."""
    path = [0] + list(nodes) + [0]
    arcs = [matrix[a][b] for a, b in zip(path, path[1:])]
    if any(a is None for a in arcs):
        return None
    tour = sum(arcs)
    ride = tour - arcs[0] if direction == "pickup" else tour - arcs[-1]
    return tour, ride


def _expand(result, col):
    """Representative node order of a column (k-th visit of an item uses its k-th node)."""
    used = [0] * len(result.items)
    out = []
    for it in col.stop_order:
        out.append(result.items[it].nodes[used[it]])
        used[it] += 1
    return tuple(out)


def _loc_matrix(L, loc_of):
    locs = [0] + list(loc_of)
    return tuple(tuple(L[locs[i]][locs[j]] for j in range(len(locs))) for i in range(len(locs)))


def _single(sw=4, so=5, total=None, ride=None, tour=None):
    from uniride_core.exact import VehicleTypeSpec

    return (VehicleTypeSpec("large", sw, so, 10, total, ride, tour),)


# ---------- enumeration vs brute-force oracle (section 8 row "Enumeration vs oracle") ----------
def test_enumeration_matches_brute_force_on_500_random_instances():
    mismatches = []
    stats = {"feasible": 0, "infeasible": 0, "typed": 0, "pickup": 0, "colocated": 0, "missing_arc": 0}
    for seed in range(ORACLE_INSTANCES):
        inst = random_instance(seed)
        res = _enum(inst)
        assert res.status == "complete", (seed, res.status)
        got = column_search(res, inst["minimize_type"], inst["quota"])
        want = _oracle(inst)
        got_obj = got[0] if got else None
        if got_obj != want.objective:
            mismatches.append((seed, got_obj, want.objective))
        stats["feasible" if want.objective else "infeasible"] += 1
        stats["typed"] += inst["minimize_type"] is not None
        stats["pickup"] += inst["direction"] == "pickup"
        stats["colocated"] += len(set(inst["location_codes"])) < len(inst["location_codes"])
        stats["missing_arc"] += any(v is None for row in inst["matrix"] for v in row)
    print(f"oracle summary over {ORACLE_INSTANCES} instances: {stats}")
    assert mismatches == []
    # the generator really covers every case the design asks for
    assert stats["feasible"] >= 200 and stats["infeasible"] >= 10
    assert 200 <= stats["typed"] <= 300 and 150 <= stats["pickup"] <= 350
    assert stats["colocated"] >= 150 and stats["missing_arc"] >= 30


def test_quota_and_total_capacity_are_honoured_by_the_oracle_and_columns():
    from uniride_core.exact import VehicleTypeSpec

    # 3 So students at distinct locations, all arcs 5. large 0sw/3so (quota), car 0sw/2so total 1.
    L = [[0, 5, 5, 5], [5, 0, 5, 5], [5, 5, 0, 5], [5, 5, 5, 0]]
    matrix = _loc_matrix(L, (1, 2, 3))
    types = (VehicleTypeSpec("large", 0, 3, 10), VehicleTypeSpec("car", 0, 2, 10, 1))
    inst = dict(direction="pickup", matrix=matrix, location_codes=("A", "B", "C"), classes=("So",) * 3,
                types=types, ride=100, tour=150, minimize_type="car", quota=("large", 0))
    res = _enum(inst)
    assert all(sum(c.multiplicity) <= 1 for c in res.columns if c.type_id == "car")  # total_capacity 1
    assert _oracle(inst).objective == (3, 30) == column_search(res, "car", ("large", 0))[0]
    inst["quota"] = ("large", 1)
    assert _oracle(inst).objective == (0, 20) == column_search(res, "car", ("large", 1))[0]


def test_same_multiset_column_can_be_needed_twice():
    """Two Sw students at one location, Sw capacity 1: the optimum uses the same
    (multiset, type) column twice, so the SP cover needs integer lambda (finding for WP-E2)."""
    L = [[0, 7], [7, 0]]
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 1)), location_codes=("A", "A"),
                classes=("Sw", "Sw"), types=_single(sw=1, so=0), ride=50, tour=150, minimize_type=None, quota=None)
    res = _enum(inst)
    assert len(res.columns) == 1
    (obj, chosen) = column_search(res)
    assert obj == (2, 28) == _oracle(inst).objective
    assert chosen == [(res.columns[0], 2)]


# ---------- column record ----------
def test_column_records_are_consistent_integer_and_feasible():
    for seed in range(0, 120):
        inst = random_instance(seed)
        res = _enum(inst)
        types = {t.type_id: t for t in res.types}
        for col in res.columns:
            nodes = _expand(res, col)
            assert len(nodes) == sum(col.multiplicity)
            assert [sum(1 for s in col.stop_order if s == i) for i in range(len(res.items))] == list(col.multiplicity)
            tour, ride = _route_cost(inst["direction"], inst["matrix"], nodes)
            assert (col.tour, col.ride, col.cost) == (tour, ride, tour)
            assert all(isinstance(v, int) and not isinstance(v, bool) for v in (col.cost, col.ride, col.tour))
            t = types[col.type_id]
            sw = sum(m for m, it in zip(col.multiplicity, res.items) if it.cls == "Sw")
            so = sum(col.multiplicity) - sw
            assert sw <= t.sw_capacity and so <= t.so_capacity
            assert t.total_capacity is None or sw + so <= t.total_capacity
            assert ride <= t.ride_limit and tour <= t.tour_limit


def test_items_group_occurrences_by_location_and_class():
    L = [[0, 3, 4], [3, 0, 2], [4, 2, 0]]
    res = _enum(dict(direction="pickup", matrix=_loc_matrix(L, (1, 2, 1, 1)), location_codes=("A", "B", "A", "A"),
                     classes=("So", "So", "Sw", "So"), types=_single(), ride=50, tour=150))
    assert [(i.location_code, i.cls, i.multiplicity, i.nodes) for i in res.items] == [
        ("A", "So", 2, (1, 4)), ("A", "Sw", 1, (3,)), ("B", "So", 1, (2,))]


# ---------- dominance (section 8 row "Dominance") ----------
@pytest.mark.parametrize("seed", range(1000, 1012))
def test_dominance_minimum_tour_per_subset_and_type(seed):
    """For every (S, t): a column exists iff a feasible order exists, and its tour is the
    minimum tour over all feasible orders (brute force over permutations, n <= 8)."""
    from uniride_core.exact.brute_force import best_orders_by_subset

    import random as _r

    inst = random_instance(seed)
    rng = _r.Random(seed)
    # widen to n = 8 by duplicating a random student (co-located, same class)
    if len(inst["classes"]) < 8:
        k = rng.randrange(len(inst["classes"]))
        m = [list(r) for r in inst["matrix"]]
        for r in m:
            r.append(r[k + 1])
        m.append(list(m[k + 1]))
        m[-1][-1] = 0
        m[k + 1][-1] = 0
        m[-1][k + 1] = 0
        inst["matrix"] = tuple(tuple(r) for r in m)
        inst["location_codes"] = inst["location_codes"] + (inst["location_codes"][k],)
        inst["classes"] = inst["classes"] + (inst["classes"][k],)
    inst["ride"], inst["tour"] = 80, 150  # loose limits keep many subsets feasible
    res = _enum(inst)
    brute = best_orders_by_subset(inst["direction"], inst["matrix"], inst["classes"], inst["types"],
                                  max_ride=inst["ride"], max_tour=inst["tour"], max_n=8)
    node_item = {nd: idx for idx, it in enumerate(res.items) for nd in it.nodes}
    want = {}
    for (nodes, tid), (tour, _ride, _order) in brute.items():
        mult = [0] * len(res.items)
        for nd in nodes:
            mult[node_item[nd]] += 1
        key = (tuple(mult), tid)
        assert want.get(key, tour) == tour  # interchangeable nodes give the same optimum
        want[key] = tour
    got = {(c.multiplicity, c.type_id): c.tour for c in res.columns}
    assert len(got) == len(res.columns)  # exactly one column per (S, t)
    assert got == want


# ---------- nonmetric revisit (section 8 row "Nonmetric revisit") ----------
REVISIT_L = [  # depot, A, B
    [0, 5, 100],
    [4, 0, 5],
    [100, 6, 0],
]


@pytest.mark.parametrize("direction", ["pickup", "dropoff"])
def test_nonmetric_revisit_route_is_the_only_feasible_cover(direction):
    L = REVISIT_L if direction == "pickup" else [list(r) for r in zip(*REVISIT_L)]
    inst = dict(direction=direction, matrix=_loc_matrix(L, (1, 1, 2)), location_codes=("A", "A", "B"),
                classes=("So",) * 3, types=_single(), ride=50, tour=60, minimize_type=None, quota=None)
    res = _enum(inst)
    full = [c for c in res.columns if c.multiplicity == (2, 1)]
    assert len(full) == 1
    a, b = 0, 1
    assert full[0].stop_order == (a, b, a) and full[0].tour == 20
    assert not [c for c in res.columns if c.multiplicity == (0, 1) or c.multiplicity == (1, 1)]
    assert column_search(res)[0] == (1, 20) == _oracle(inst).objective


# ---------- missing arcs (O06) ----------
def test_missing_arc_never_crashes_and_never_forms_a_column():
    L = [[0, 4, 4, 6], [4, 0, None, 3], [4, 3, 0, 3], [None, 3, 3, 0]]  # A->B and C->depot missing
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 2, 3)), location_codes=("A", "B", "C"),
                classes=("So",) * 3, types=_single(), ride=80, tour=150, minimize_type=None, quota=None)
    res = _enum(inst)
    assert res.status == "complete"
    for col in res.columns:
        assert _route_cost("pickup", inst["matrix"], _expand(res, col)) is not None
        assert col.stop_order[-1] != 2  # C cannot end a pickup route (C->depot missing)
    assert (0, 0, 1) not in {c.multiplicity for c in res.columns}
    assert column_search(res)[0] == _oracle(inst).objective


def test_student_without_any_route_gives_no_column_and_no_crash():
    L = [[0, 4, None], [4, 0, 3], [None, None, 0]]  # B unreachable and cannot reach anything
    res = _enum(dict(direction="dropoff", matrix=_loc_matrix(L, (1, 2)), location_codes=("A", "B"),
                     classes=("So", "So"), types=_single(), ride=80, tour=150))
    assert res.status == "complete"
    assert all(c.multiplicity[1] == 0 for c in res.columns)
    assert column_search(res) is None


@pytest.mark.parametrize("bad", [-1, 1.5, True, "3"])
def test_non_integer_or_negative_arc_is_an_input_error(bad):
    m = ((0, 3), (bad, 0))
    with pytest.raises(ValueError):
        _enum(dict(direction="pickup", matrix=m, location_codes=("A",), classes=("So",), types=_single(),
                   ride=50, tour=150))


def test_co_located_occurrences_must_be_interchangeable():
    m = ((0, 3, 3), (4, 0, 0), (5, 0, 0))  # same location A, different arcs to the depot
    with pytest.raises(ValueError):
        _enum(dict(direction="pickup", matrix=m, location_codes=("A", "A"), classes=("So", "So"),
                   types=_single(), ride=50, tour=150))


# ---------- clique floor (section 8 row "Clique floor") ----------
def test_clique_floor_does_not_mark_jointly_feasible_pair_incompatible():
    from uniride_core.exact.route_enumeration import clique_floor, incompatible_student_pairs

    # pickup; i=node1 at I, j=node2 at J, k=node3 at K. {i,j} alone infeasible (I<->J 100),
    # but i -> k -> j -> depot is cheap; capacity 3 So.
    L = [  # depot, I, J, K
        [0, 10, 10, 10],
        [30, 0, 100, 5],
        [5, 100, 0, 30],
        [30, 30, 5, 0],
    ]
    inst = dict(direction="pickup", matrix=_loc_matrix(L, (1, 2, 3)), location_codes=("I", "J", "K"),
                classes=("So",) * 3, types=_single(sw=0, so=3), ride=40, tour=60, minimize_type=None, quota=None)
    res = _enum(inst)
    mults = {c.multiplicity for c in res.columns}
    assert (1, 1, 0) not in mults and (1, 1, 1) in mults  # items sorted I, J, K
    pairs = incompatible_student_pairs(res)
    assert (1, 2) not in pairs
    size, members = clique_floor(res)
    k_star = _oracle(inst).objective[0]
    assert size <= k_star == 1


def test_clique_floor_counts_genuinely_incompatible_students():
    from uniride_core.exact.route_enumeration import clique_floor, incompatible_student_pairs

    # three So students, capacity 1 seat: every pair is incompatible -> clique 3 = K*
    L = [[0, 5, 6, 7], [5, 0, 1, 1], [6, 1, 0, 1], [7, 1, 1, 0]]
    inst = dict(direction="dropoff", matrix=_loc_matrix(L, (1, 2, 3)), location_codes=("A", "B", "C"),
                classes=("So",) * 3, types=_single(sw=0, so=1), ride=50, tour=150, minimize_type=None, quota=None)
    res = _enum(inst)
    assert incompatible_student_pairs(res) == frozenset({(1, 2), (1, 3), (2, 3)})
    assert clique_floor(res)[0] == 3 == _oracle(inst).objective[0]
    # co-located pair at one location with 2 seats: compatible
    L2 = [[0, 5], [5, 0]]
    res2 = _enum(dict(direction="pickup", matrix=_loc_matrix(L2, (1, 1)), location_codes=("A", "A"),
                      classes=("So", "So"), types=_single(sw=0, so=2), ride=50, tour=150))
    assert incompatible_student_pairs(res2) == frozenset()


# ---------- determinism ----------
_DET_SCRIPT = """
import hashlib, sys
sys.path.insert(0, {tests!r}); sys.path.insert(0, {repo!r})
from exact_enum_helpers import random_instance
from uniride_core.exact.route_enumeration import enumerate_routes
h = hashlib.sha256()
for seed in (3, 8, 11, 42):
    i = random_instance(seed)
    r = enumerate_routes(i['direction'], i['matrix'], i['location_codes'], i['classes'], i['types'],
                         max_ride=i['ride'], max_tour=i['tour'])
    h.update(repr((r.items, r.columns, r.label_count, r.labels_per_level)).encode())
print(h.hexdigest())
"""


def test_enumeration_is_deterministic_across_runs_and_hash_seeds(tmp_path):
    script = tmp_path / "det.py"
    script.write_text(_DET_SCRIPT.format(tests=str(Path(__file__).parent), repo=str(REPO)), encoding="utf-8")
    digests = set()
    for hs in ("0", "1", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        out = subprocess.run([sys.executable, "-B", str(script)], cwd=REPO, env=env,
                             capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr
        digests.add(out.stdout.strip())
    assert len(digests) == 1
    inst = random_instance(42)
    assert _enum(inst) == _enum(inst)


# ---------- caps ----------
def _big_instance():
    L = [[0] + [3] * 8] + [[3] + [2 if a != b else 0 for b in range(8)] for a in range(8)]
    return dict(direction="pickup", matrix=_loc_matrix(L, tuple(range(1, 9))),
                location_codes=tuple(f"S{i}" for i in range(8)), classes=("So",) * 8,
                types=_single(sw=0, so=5), ride=90, tour=150)


def test_count_caps_fire_deterministically_and_route_to_compact():
    from uniride_core.exact.route_enumeration import COLUMN_CAP_DEFAULT

    assert COLUMN_CAP_DEFAULT == 2_000_000
    full = _enum(_big_instance())
    assert full.status == "complete" and full.cap_fired is None and full.model == "SP"
    for kw, cap in ((dict(column_cap=50), "column_cap"), (dict(label_cap=100), "label_cap")):
        a = _enum(_big_instance(), **kw)
        b = _enum(_big_instance(), **kw)
        assert a.status == "count_cap" and a.cap_fired == cap and a.model == "compact"
        assert a.columns == () and (a.column_count, a.label_count) == (b.column_count, b.label_count)
    assert _enum(_big_instance(), column_cap=50).column_count == 51
    assert _enum(_big_instance(), label_cap=100).label_count == 101
    ok = _enum(_big_instance(), column_cap=full.column_count, label_cap=full.label_count)
    assert ok.status == "complete" and ok.columns == full.columns


def test_wall_clock_limit_aborts_without_model_switch():
    ticks = itertools.chain([0.0], itertools.repeat(1000.0))  # start, then every later reading is late

    res = _enum(_big_instance(), wall_clock_limit=5.0, clock=lambda: next(ticks))
    assert res.status == "timing_dependent_abort" and res.cap_fired == "wall_clock"
    assert res.model is None and res.columns == ()
    # count caps that are not reached never abort
    res2 = _enum(_big_instance(), wall_clock_limit=600.0)
    assert res2.status == "complete"


def test_label_cap_default_is_recorded_on_the_result():
    from uniride_core.exact.route_enumeration import LABEL_CAP_DEFAULT

    res = _enum(_big_instance())
    assert isinstance(LABEL_CAP_DEFAULT, int) and LABEL_CAP_DEFAULT > 0
    assert (res.column_cap, res.label_cap, res.wall_clock_limit) == (2_000_000, LABEL_CAP_DEFAULT, 600.0)
    assert sum(res.labels_per_level) == res.label_count


# ---------- WaveInstance entry point ----------
def test_enumerate_wave_uses_wave_limits_and_type_overrides():
    from uniride_core.exact import VehicleTypeSpec, WaveInstance, compute_matrix_sha256
    from uniride_core.exact.route_enumeration import enumerate_wave

    m = ((0, 10, 30), (10, 0, 25), (30, 25, 0))
    w = WaveInstance(wave_id="w", service_date="2026-10-05", direction="pickup", anchor_minutes=525,
                     max_ride_minutes=30, max_tour_minutes=150, depot_code="D", occurrence_ids=("a~1", "b~1"),
                     location_codes=("So1", "So2"), classes=("So", "So"), matrix=m,
                     matrix_sha256=compute_matrix_sha256(m), arc_slice_sha256="x", declared_snapshot_sha256="y")
    res = enumerate_wave(w, (VehicleTypeSpec("large", 0, 5, 10),))
    assert {c.multiplicity for c in res.columns} == {(1, 0), (0, 1)}  # 2 -> 1 -> depot rides 35 > 30
    res2 = enumerate_wave(w, (VehicleTypeSpec("large", 0, 5, 10, None, 35),))
    assert (1, 1) in {c.multiplicity for c in res2.columns}
    assert res2.types[0].ride_limit == 35 and res2.types[0].tour_limit == 150


# ---------- brute force self-checks ----------
def test_brute_force_refuses_large_instances():
    from uniride_core.exact.brute_force import brute_force_optimum

    m = tuple(tuple(0 if i == j else 1 for j in range(9)) for i in range(9))
    with pytest.raises(ValueError):
        brute_force_optimum("pickup", m, ("So",) * 8, _single(), max_ride=50, max_tour=150)


def test_brute_force_small_hand_instance():
    from uniride_core.exact.brute_force import brute_force_optimum

    L = [[0, 10, 20], [10, 0, 5], [20, 5, 0]]
    m = _loc_matrix(L, (1, 2))
    r = brute_force_optimum("pickup", m, ("So", "So"), _single(sw=0, so=2), max_ride=50, max_tour=150)
    # orders: 1->2->0 tour 10+5+20=35; 2->1->0 tour 20+5+10=35; separate 20+40=60
    assert r.objective == (1, 35)
    r2 = brute_force_optimum("pickup", m, ("So", "So"), _single(sw=0, so=1), max_ride=50, max_tour=150)
    assert r2.objective == (2, 60)


# ---------- boundary guards (section 8 row "Boundary", section 2) ----------
def test_new_modules_do_not_import_amplpy_or_network():
    code = ("import sys, uniride_core.exact.route_enumeration, uniride_core.exact.brute_force; "
            "sys.exit(1 if 'amplpy' in sys.modules else 0)")
    res = subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    banned = {"amplpy", "requests", "urllib", "http", "socket", "sqlite3", "supabase", "httpx", "optimizer_api"}
    for name in ("route_enumeration.py", "brute_force.py"):
        tree = ast.parse((REPO / "uniride_core" / "exact" / name).read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                mods.add((node.module or "").split(".")[0])
        assert not mods & banned, (name, mods & banned)


def test_typescript_src_never_references_uniride_core_exact():
    offenders = []
    for path in itertools.chain((REPO / "src").rglob("*.ts"), (REPO / "src").rglob("*.tsx")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "uniride_core.exact" in text or "uniride_core/exact" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


def test_brute_force_is_test_only():
    """brute_force is an oracle: nothing outside tests imports it."""
    offenders = []
    for top in ("uniride_core", "optimizer_api", "academic_benchmark", "scripts"):
        for path in (REPO / top).rglob("*.py"):
            if "tests" in path.parts or path.name == "brute_force.py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"exact\.brute_force|from \.brute_force import|exact import [^\n]*brute_force", text):
                offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


# ---------- archived waves (WP-E1 acceptance: counts logged, GA routes inside the search space) ----------
RESULTS = REPO / "docs" / "paper" / "results"
COUNTS_CSV = RESULTS / "week-2026-10-05-exact" / "wp-e1-enumeration" / "enumeration_counts.csv"


@pytest.fixture(scope="module")
def archived_enumerations():
    import importlib.util

    spec = importlib.util.spec_from_file_location("exact_archive_loader_e1", REPO / "scripts" / "exact_archive_loader.py")
    loader = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_e1"] = loader
    spec.loader.exec_module(loader)
    from uniride_core.exact.route_enumeration import enumerate_wave

    campaigns = loader.load_all_valid(RESULTS)
    label = {"4sw5so": "single_4sw5so", "fleet": "large+sedan", "minivan-cap3": "large+doblo_cap3"}
    out = {}
    for key, camp in campaigns.items():
        for ride in camp.rides:
            for w in camp.waves_for(ride):
                out[(label[key], ride, w.wave_id)] = (w, enumerate_wave(w, camp.fleet_types))
    return out


def test_every_archived_wave_completes_under_default_caps_and_matches_the_logged_counts(archived_enumerations):
    import csv

    assert len(archived_enumerations) == 3 * 4 * 57
    for (_, _, _), (_, res) in archived_enumerations.items():
        assert res.status == "complete" and res.model == "SP" and res.cap_fired is None
    with COUNTS_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(archived_enumerations)
    for row in rows:
        _, res = archived_enumerations[(row["fleet"], int(row["R"]), row["wave_id"])]
        assert (int(row["columns"]), int(row["labels"]), row["status"]) == (res.column_count, res.label_count, res.status)


def test_archived_ga_routes_lie_inside_the_enumerated_search_space():
    """Every archived single-type GA route (4sw5so, all R) is matched by the column of its
    multiset with a tour <= the GA route minutes, and the GA minutes equal the F1 recomputation."""
    import importlib.util
    import json

    spec = importlib.util.spec_from_file_location("exact_archive_loader_e1b", REPO / "scripts" / "exact_archive_loader.py")
    loader = importlib.util.module_from_spec(spec)
    sys.modules["exact_archive_loader_e1b"] = loader
    spec.loader.exec_module(loader)
    from uniride_core.exact.route_enumeration import enumerate_wave

    camp = loader.load_campaign(RESULTS / "week-2026-10-05-4sw5so")
    routes = shorter = 0
    for ride in camp.rides:
        waves = {w.wave_id: w for w in camp.waves_for(ride)}
        for f in sorted((RESULTS / "week-2026-10-05-4sw5so").glob(f"*_R{ride}_repeat1.response.json")):
            for job in json.loads(f.read_text(encoding="utf-8"))["jobs"]:
                w = waves[job["id"]]
                res = enumerate_wave(w, camp.fleet_types)
                cols = {c.multiplicity: c for c in res.columns}
                node = {o: i + 1 for i, o in enumerate(w.occurrence_ids)}
                item_of = {nd: idx for idx, it in enumerate(res.items) for nd in it.nodes}
                for r in job["result"]["routes"]:
                    order = [node[o] for o in r["student_ids"]]
                    tour, ride_min = _route_cost(w.direction, w.matrix, order)
                    assert tour == r["total_duration_minutes"]
                    assert ride_min <= ride and tour <= w.max_tour_minutes
                    mult = [0] * len(res.items)
                    for nd in order:
                        mult[item_of[nd]] += 1
                    col = cols[tuple(mult)]
                    assert col.tour <= tour
                    routes += 1
                    shorter += col.tour < tour
    print(f"archived GA routes checked: {routes}; enumerated column strictly shorter: {shorter}")
    assert routes > 0
