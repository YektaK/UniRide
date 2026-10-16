"""WP-E2: the exact_reference_v1 protocol, its status labels and the exact_manifest.json schema
(design EXACT_SOLVER_AMPL_DESIGN.md sections 2 and 4). No AMPL needed."""
from __future__ import annotations

import copy

import pytest


def _proto():
    from academic_benchmark.exact_reference import protocol

    return protocol


def _stage(**over):
    row = dict(stage="stage1", status="optimal", stop_reason="optimal", timing_dependent=False,
               non_lexicographic=False, objective=3, bound=3.0, wall_seconds=0.4)
    row.update(over)
    return row


def _manifest():
    p = _proto()
    return {
        "protocol": p.PROTOCOL_ID,
        "schema_version": p.MANIFEST_SCHEMA_VERSION,
        "git_commit": "57675c0",
        "dirty_working_tree": False,
        "source_campaign": {"path": "docs/paper/results/week-2026-10-05-4sw5so", "manifest_sha256": "a" * 64},
        "matrix_sha256": {"2026-10-05_R90": "b" * 64},
        "peak_waves": {"2026-10-05": {"legs": 20, "wave_ids": ["2026-10-05:pickup:525"]}},
        "ampl": {"version": "AMPL Version 20260809 (MSVC 19.44.35228.0, 64-bit)", "amplpy_version": "0.18.0",
                 "location": "local AMPL installation used"},
        "solver": {"name": "gurobi", "version": "Gurobi 13.0.3",
                   "option_string": "mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=60 "
                                    "lim:work=20 outlev=1",
                   "peak_option_string": "mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 "
                                         "lim:time=600 lim:work=200 outlev=1",
                   "threads": 1, "seed": 0, "time_limit_seconds": 60, "peak_time_limit_seconds": 600,
                   "work_limit": 20, "peak_work_limit": 200, "mip_gap": 0, "mip_gap_abs": 0.99},
        "enumeration": {"column_cap": 2_000_000, "label_cap": 5_000_000, "wall_clock_limit_seconds": 600},
        "waves": [{"wave_id": "2026-10-05:pickup:525", "service_date": "2026-10-05", "R": 90, "peak": True,
                   "model": "SP", "columns": 45170, "labels": 171053,
                   "stages": [_stage(), _stage(stage="stage2", objective=1234, bound=1234.0),
                              _stage(stage="free", objective=1200, bound=1200.0)]},
                  {"wave_id": "2026-10-05:dropoff:795", "service_date": "2026-10-05", "R": 90, "peak": False,
                   "model": "SP", "columns": 15, "labels": 40, "stages": [_stage()]}],
        "python_version": "3.13.1",
        "host_os": "Windows-11",
    }


def test_protocol_identity_is_separate_from_heuristic_protocols():
    p = _proto()
    assert p.PROTOCOL_ID == "exact_reference_v1"
    assert p.PROTOCOL_ID not in ("fixed_budget", "native") and p.MANIFEST_FILENAME == "exact_manifest.json"


def test_status_labels_are_the_core_statuses_with_meanings():
    from uniride_core.exact import EXACT_STATUSES

    p = _proto()
    assert set(p.STATUS_LABELS) == set(EXACT_STATUSES) - {"not_run"}
    assert all(isinstance(v, str) and v for v in p.STATUS_LABELS.values())
    assert {"optimal", "work_limit", "wall_limit", "infeasible"} <= set(p.STOP_REASONS)
    # owner decision 2026-10-16 (E03): three extra stop reasons; other_limit is timing-dependent
    assert {"gap_tolerance", "solver_failure", "other_limit"} <= set(p.STOP_REASONS)
    assert set(p.TIMING_STOP_REASONS) == {"wall_limit", "other_limit"}
    assert (p.GUROBI_WORK_LIMIT, p.GUROBI_PEAK_WORK_LIMIT) == (20, 200)


def test_enumeration_caps_come_from_core():
    from uniride_core.exact import route_enumeration as re_

    p = _proto()
    assert p.ENUMERATION_CAPS == {"column_cap": re_.COLUMN_CAP_DEFAULT, "label_cap": re_.LABEL_CAP_DEFAULT,
                                  "wall_clock_limit_seconds": int(re_.WALL_CLOCK_LIMIT_DEFAULT)}
    assert (p.WALL_LIMIT_SECONDS, p.PEAK_WALL_LIMIT_SECONDS) == (60, 600)


def test_valid_manifest_passes():
    assert _proto().validate_manifest(_manifest()) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda m: m.pop("git_commit"), "git_commit"),
    (lambda m: m.update(protocol="native"), "protocol"),
    (lambda m: m["source_campaign"].update(path="C:\\Users\\x\\results"), "absolute path"),
    (lambda m: m["source_campaign"].update(path="/home/x/results"), "absolute path"),
    (lambda m: m["ampl"].update(location="C:/AMPL"), "ampl.location"),
    (lambda m: m["solver"].update(option_string="bestbound=1 lim:time=60"), "bare"),
    (lambda m: m["solver"].update(work_limit=30, peak_work_limit=300), "20/200"),
    (lambda m: m["solver"].update(option_string=m["solver"]["option_string"].replace("lim:time=60", "lim:time=90")),
     "lim:time disagrees"),
    (lambda m: m["solver"].update(peak_option_string=m["solver"]["peak_option_string"].replace("lim:work=200", "lim:work=300")),
     "lim:work disagrees"),
    (lambda m: m["solver"].update(name="highs"), "gurobi only"),
    (lambda m: m["solver"].pop("peak_option_string"), "peak_option_string"),
    (lambda m: m["waves"][0].update(peak=False), "peak must be True"),
    (lambda m: m["waves"][1].update(peak=True), "peak must be False"),
    (lambda m: m["waves"][0]["stages"][0].update(stop_reason="other_limit", status="feasible_with_gap"), "timing_dependent"),
    (lambda m: m["solver"].update(threads=4), "threads"),
    (lambda m: m["enumeration"].update(label_cap=1000), "label_cap"),
    (lambda m: m.update(host_os="owner@example.org"), "e-mail"),
    (lambda m: m["ampl"].update(version="AMPL Version 1\nLicense for x"), "license"),
    (lambda m: m["waves"][0]["stages"][0].update(status="best"), "status"),
    (lambda m: m["waves"][0]["stages"][0].update(stop_reason="wall_limit", status="feasible_with_gap"), "timing_dependent"),
    (lambda m: m["waves"][0]["stages"][0].update(non_lexicographic=True), "non_lexicographic"),
    (lambda m: m["waves"][0].update(model="MTZ"), "model"),
])
def test_invalid_manifest_is_reported(mutate, needle):
    m = _manifest()
    mutate(m)
    errors = _proto().validate_manifest(m)
    assert errors and any(needle in e for e in errors), errors


def test_stage_row_rules():
    p = _proto()
    assert p.validate_stage_row(_stage(stage="stage2", status="skipped_no_stage1_incumbent", stop_reason=None,
                                       objective=None, bound=None)) == []
    assert p.validate_stage_row(_stage(stage="stage2", non_lexicographic=True, status="optimal")) == []
    assert p.validate_stage_row(_stage(stage="stage1", status="skipped_no_stage1_incumbent", stop_reason=None))
    assert p.validate_stage_row(_stage(status="optimal", objective=None))


def test_protocol_limits_match_the_backend_defaults():
    from uniride_core.exact import ampl_backend as ab

    p = _proto()
    assert (ab.DEFAULT_WORK_LIMIT, ab.PEAK_WORK_LIMIT) == (p.GUROBI_WORK_LIMIT, p.GUROBI_PEAK_WORK_LIMIT)
    assert (ab.DEFAULT_WALL_LIMIT_SECONDS, ab.PEAK_WALL_LIMIT_SECONDS) == (p.WALL_LIMIT_SECONDS, p.PEAK_WALL_LIMIT_SECONDS)
    m = _manifest()
    s = ab.SolverSettings(solver="gurobi")
    m["solver"]["option_string"] = ab.solver_option_string(s, peak=False)
    m["solver"]["peak_option_string"] = ab.solver_option_string(s, peak=True)
    assert p.validate_manifest(m) == []


def test_rows_of_different_protocols_are_never_pooled():
    p = _proto()
    p.assert_not_pooled([{"protocol": p.PROTOCOL_ID}, {"protocol": p.PROTOCOL_ID}])
    with pytest.raises(ValueError):
        p.assert_not_pooled([{"protocol": p.PROTOCOL_ID}, {"protocol": "fixed_budget"}])
    with pytest.raises(ValueError):
        p.assert_not_pooled([{"protocol": p.PROTOCOL_ID}, {}])


def test_manifest_example_is_not_mutated_by_validation():
    m = _manifest()
    before = copy.deepcopy(m)
    _proto().validate_manifest(m)
    assert m == before
