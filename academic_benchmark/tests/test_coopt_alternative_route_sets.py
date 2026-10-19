"""WP-E11 J8: the 7 co-optimal (wave, R) rows (design JOINT_DAY_MODEL_DESIGN.md section 5.4).

In 7 of the 228 single-type (wave, R) rows the prototype (Claude Science, branch docs/science-review-2026-10) and WP-E3
choose different passenger groupings while (K*, D*) are equal. The fixture holds both route sets of each row with the
arcs they need and the provenance of the copied data. The assertions: both sets pass the independent day-plan checker at
wave level, both recompute to the committed (K*, D*), and the comparison used by the reproduction step calls the pair a
``co_optimal_alternative`` (equal objective, different routes), never a ``mismatch``. A set with one minute more is a
``mismatch``. The fixture is read-only data; nothing is solved here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from academic_benchmark.exact_reference.day_compare import CO_OPTIMAL_ALTERNATIVE, MISMATCH, compare_objectives
from academic_benchmark.validation import day_plan as dp

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "coopt_waves_2026-10-19.json"
FIX = json.loads(FIXTURE.read_text(encoding="utf-8"))
E3_DIR = REPO / "docs" / "paper" / "results" / "week-2026-10-05-exact" / "wp-e3-goal1-single"
ROWS = FIX["rows"]
ROW_IDS = [f"{r['wave_id']}|R{r['R']}" for r in ROWS]
SETS = ("prototype_routes", "wp_e3_routes")


def _kwargs(row, key, *, minute_more=False):
    wave = dp.Wave(row["wave_id"], row["direction"], row["anchor_minutes"], dict(row["occurrences"]))
    spec = FIX["type"]
    large = dp.TypeSpec(spec["type_id"], spec["sw_capacity"], spec["so_capacity"], spec["cooldown_minutes"])
    routes = [dp.Route(row["wave_id"], large.type_id, tuple(r["stops"]), claimed_minutes=r["claimed_minutes"]) for r in row[key]]
    arcs = {(o, d): v for o, d, v in row["arcs"]}
    if minute_more:  # lengthen every arc out of the depot by one minute: the same routes now cost one minute more each
        arcs = {k: v + (1 if k[0] == FIX["depot"] else 0) for k, v in arcs.items()}
    return dict(waves=[wave], routes=routes, types={large.type_id: large}, arcs=arcs, depot=FIX["depot"],
                tour_limit=row["limits"]["tour_minutes"], ride_limit=row["limits"]["ride_minutes"])


def _objective(row, key):
    report = dp.check_day_plan(**_kwargs(row, key))
    return report.route_count, report.total_minutes


def _grouping(row, key):
    return frozenset(frozenset(r["stops"]) for r in row[key])


def test_the_fixture_holds_the_seven_rows_with_provenance():
    assert len(ROWS) == 7 and len(set(ROW_IDS)) == 7
    proto = FIX["provenance"]["prototype"]
    assert proto["branch"] == "docs/science-review-2026-10" and proto["commit"].startswith("74f28f5e")
    assert len(proto["source_sha256"]) == 64 and proto["source_path"].endswith("wave_exact_rerun_resolved.jsonl")
    assert FIX["provenance"]["wp_e3"]["path"].endswith("wp-e3-goal1-single/exact_routes.json")


def test_the_wp_e3_part_of_the_fixture_still_equals_the_committed_result_files():
    prov = FIX["provenance"]["wp_e3"]
    raw = (E3_DIR / "exact_routes.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == prov["sha256"]
    live = {(w["wave_id"], w["R"]): w for w in json.loads(raw)["waves"]}
    for row in ROWS:
        routes = live[(row["wave_id"], row["R"])]["routes"]
        assert [r["occurrence_ids"] for r in routes] == [r["stops"] for r in row["wp_e3_routes"]]


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
@pytest.mark.parametrize("key", SETS)
def test_each_route_set_passes_the_wave_level_checker_and_recomputes_the_committed_objective(row, key):
    committed = row["committed"]
    claims = dp.DayClaims(route_count=committed["K_star"], total_minutes=committed["D_star"],
                          peaks={"large": committed["K_star"]})
    report = dp.check_day_plan(**_kwargs(row, key), claims=claims)
    assert report.ok, report.violations
    assert (report.route_count, report.total_minutes) == (committed["K_star"], committed["D_star"])


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_the_two_sets_group_the_passengers_differently_and_compare_as_co_optimal_alternative(row):
    assert _grouping(row, "prototype_routes") != _grouping(row, "wp_e3_routes")
    assert compare_objectives(_objective(row, "prototype_routes"), _objective(row, "wp_e3_routes")) == CO_OPTIMAL_ALTERNATIVE


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_one_minute_more_is_a_mismatch(row):
    k, d = _objective(row, "wp_e3_routes")
    assert compare_objectives((k, d + 1), (k, d)) == MISMATCH
    assert compare_objectives((k, d), (k, d + 1)) == MISMATCH
    # the same routes on a matrix with one more minute on each depot arc: the checker recomputes a longer plan
    longer = dp.check_day_plan(**_kwargs(row, "wp_e3_routes", minute_more=True))
    assert longer.total_minutes > d
    assert compare_objectives((longer.route_count, longer.total_minutes), (k, d)) == MISMATCH


def test_one_route_more_is_a_mismatch_even_at_equal_minutes():
    assert compare_objectives((3, 300), (4, 300)) == MISMATCH


def test_route_identity_is_not_compared():
    # different groupings, same (K, D): never a mismatch
    assert compare_objectives((2, 142), (2, 142)) == CO_OPTIMAL_ALTERNATIVE


@pytest.mark.parametrize("bad", [((1, 2), (1, 2, 3)), ((1, True), (1, 1)), ((1.0, 2), (1, 2)), ((), ())])
def test_the_comparison_refuses_malformed_objectives(bad):
    with pytest.raises(ValueError):
        compare_objectives(*bad)
