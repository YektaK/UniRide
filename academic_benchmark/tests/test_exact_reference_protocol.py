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


# ---- WP-E4a: several source campaigns (backward compatible with the single ``source_campaign``) ----
def _multi_manifest():
    m = _manifest()
    one = m.pop("source_campaign")
    m["source_campaigns"] = {"large+sedan": dict(one, path="docs/paper/results/week-2026-10-05-fleet-rerun-large-sedan"),
                             "large+doblo_cap3": dict(one, path="docs/paper/results/week-2026-10-05-fleet-rerun-doblo-cap3")}
    return m


def test_manifest_with_source_campaigns_instead_of_source_campaign_is_valid():
    assert _proto().validate_manifest(_multi_manifest()) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda m: m.pop("source_campaigns"), "source_campaign"),
    (lambda m: m.update(source_campaigns={}), "source_campaign"),
    (lambda m: m["source_campaigns"]["large+sedan"].update(path="/home/x/results"), "absolute path"),
    (lambda m: m["source_campaigns"]["large+sedan"].update(manifest_sha256="nothex"), "manifest_sha256"),
    (lambda m: m["source_campaigns"]["large+sedan"].pop("path"), "relative path"),
])
def test_invalid_source_campaigns_are_reported(mutate, needle):
    m = _multi_manifest()
    mutate(m)
    errors = _proto().validate_manifest(m)
    assert any(needle in e for e in errors), errors


def test_single_source_campaign_manifests_stay_valid_and_one_source_is_required():
    m = _manifest()
    assert _proto().validate_manifest(m) == []
    m.pop("source_campaign")
    assert any("source_campaign" in e for e in _proto().validate_manifest(m))


# ---------------------------------------------------------------------------------------------------------------
# WP-E6: the union_day_v1 manifest schema (WP-E4b manifest) is owned by protocol.py, not by the runner script.
# ---------------------------------------------------------------------------------------------------------------
import json  # noqa: E402
from pathlib import Path  # noqa: E402

_UNION_MANIFEST = (Path(__file__).resolve().parents[2] / "docs" / "paper" / "results" / "week-2026-10-05-exact"
                   / "wp-e4b-union-day" / "union_day_manifest.json")


def _union_manifest():
    return json.loads(_UNION_MANIFEST.read_text(encoding="utf-8"))


def test_union_day_protocol_id_and_filename_are_registered():
    p = _proto()
    assert p.UNION_DAY_PROTOCOL_ID == "union_day_v1"
    assert p.UNION_DAY_MANIFEST_FILENAME == "union_day_manifest.json"
    assert p.UNION_DAY_TIME_SCALE == 100


def test_committed_wp_e4b_manifest_is_valid_under_the_registered_schema():
    assert _proto().validate_union_day_manifest(_union_manifest()) == []


@pytest.mark.parametrize("key", ["protocol", "work_package", "git_commit", "dirty_working_tree", "source_campaigns",
                                 "exact_options_source", "cpsat", "time_scale", "router_caps", "tools",
                                 "python_provenance", "python_version", "host_os", "run_history", "claim",
                                 "ga_recompute", "labels", "blocking_errors", "total_wall_seconds"])
def test_union_day_manifest_requires_every_key(key):
    m = _union_manifest()
    del m[key]
    assert any(key in e for e in _proto().validate_union_day_manifest(m))


def test_union_day_manifest_rejects_a_wrong_protocol_id_time_scale_and_claim():
    p = _proto()
    for field, value, needle in (("protocol", "exact_reference_v1", "protocol"), ("time_scale", 1, "time_scale"),
                                 ("claim", "union is the global day optimum", "claim")):
        m = _union_manifest()
        m[field] = value
        assert any(needle in e for e in p.validate_union_day_manifest(m)), field


def test_union_day_manifest_rejects_private_data_and_bad_hashes_and_labels():
    p = _proto()
    m = _union_manifest()
    m["host_os"] = r"C:\Users\someone\box"
    assert any("absolute path" in e for e in p.validate_union_day_manifest(m))
    m = _union_manifest()
    m["tools"]["owner"] = "someone@example.org"
    assert any("e-mail" in e for e in p.validate_union_day_manifest(m))
    m = _union_manifest()
    next(iter(m["source_campaigns"].values()))["manifest_sha256"] = "xyz"
    assert any("manifest_sha256" in e for e in p.validate_union_day_manifest(m))
    m = _union_manifest()
    m["exact_options_source"]["exact_routes_sha256"] = "12"
    assert any("exact_routes_sha256" in e for e in p.validate_union_day_manifest(m))
    m = _union_manifest()
    m["labels"].pop("union_not_proven")
    assert any("labels" in e for e in p.validate_union_day_manifest(m))
    m = _union_manifest()
    m["git_commit"] = "not-a-commit"
    assert any("git_commit" in e for e in p.validate_union_day_manifest(m))


def test_validator_does_not_mutate_and_exact_reference_validator_is_unchanged():
    p = _proto()
    m = _union_manifest()
    before = json.dumps(m, sort_keys=True)
    p.validate_union_day_manifest(m)
    assert json.dumps(m, sort_keys=True) == before
    assert p.validate_manifest(_manifest()) == []  # exact_reference_v1 schema untouched


def test_runner_has_no_local_validator_and_uses_the_protocol_one():
    import re

    text = (Path(__file__).resolve().parents[2] / "scripts" / "run_exact_union_day.py").read_text(encoding="utf-8")
    assert not re.search(r"^def (validate_manifest|required_manifest_keys)\b", text, re.M)
    assert "protocol.validate_union_day_manifest(" in text


# ---------------------------------------------------------------------------------------------------------------
# WP-E7: the TSP/ATSP reference manifest (GOAL 2 stage 1). Same protocol id as the wave campaigns; rows are
# Hamiltonian-cycle rows and the manifest is its own kind, so validate_manifest / validate_union_day_manifest stay unchanged.
# ---------------------------------------------------------------------------------------------------------------
def _tsp_manifest():
    p = _proto()
    opts = "mip:bestbound=1 tech:threads=1 tech:seed=0 mip:gap=0 mip:gapabs=0.99 lim:time=600"
    return {
        "protocol": p.PROTOCOL_ID, "manifest_kind": p.TSP_REFERENCE_KIND, "schema_version": p.TSP_REFERENCE_SCHEMA_VERSION,
        "work_package": "WP-E7", "solution_kind": "hamiltonian_cycle", "git_commit": "0123456789abcdef0123456789abcdef01234567",
        "dirty_working_tree": False,
        "ampl": {"version": "AMPL Version 20260809", "amplpy_version": "0.18.0", "location": "local AMPL installation used"},
        "solvers": {
            "gurobi": {"name": "gurobi", "version": "Gurobi 13.0.3", "option_string": opts, "threads": 1, "seed": 0,
                       "time_limit_seconds": 600, "work_limit": None},
            "highs": {"name": "highs", "version": "HiGHS 1.15.1", "option_string": opts, "threads": 1, "seed": 0,
                      "time_limit_seconds": 600, "work_limit": None}},
        "limits": {"total_seconds_per_instance": 600, "threads": 1, "seed": 0, "mtz_limit_seconds": 120.0},
        "instances": {"eil51": {"problem_type": "TSP", "n": 51, "edge_weight_type": "EUC_2D", "data_source": "tsp_file",
                                "file": "eil51.tsp", "sha256": "a" * 64, "matrix_sha256": "b" * 64,
                                "published_optimum": 426, "published_source": "tsplib"}},
        "published_optimum_source": {"table": "problems.optimal", "cross_checks": ["tsplib_parser.TSPLIB_OPTIMALS"],
                                     "discrepancies": []},
        "python_provenance": {"uniride_core": "uniride_core/__init__.py"}, "python_version": "3.13.1", "host_os": "Windows-11",
        "claim": p.TSP_REFERENCE_CLAIM, "blocking_errors": [], "total_wall_seconds": 1.5,
    }


def test_tsp_reference_manifest_is_valid_and_registered():
    p = _proto()
    assert p.validate_tsp_reference_manifest(_tsp_manifest()) == []
    assert p.TSP_REFERENCE_TOTAL_SECONDS == 600 and p.TSP_REFERENCE_KIND == "tsp_reference"
    assert p.assert_not_pooled([{"protocol": p.PROTOCOL_ID}]) is None


@pytest.mark.parametrize("key", ["protocol", "manifest_kind", "schema_version", "git_commit", "dirty_working_tree", "ampl",
                                 "solvers", "limits", "instances", "published_optimum_source", "python_provenance",
                                 "claim", "blocking_errors", "solution_kind"])
def test_tsp_reference_manifest_requires_every_key(key):
    m = _tsp_manifest()
    del m[key]
    assert any(key in e for e in _proto().validate_tsp_reference_manifest(m))


@pytest.mark.parametrize("mutate,needle", [
    (lambda m: m.update(protocol="other"), "protocol"),
    (lambda m: m.update(manifest_kind="wave"), "manifest_kind"),
    (lambda m: m.update(git_commit="not-a-sha"), "git_commit"),
    (lambda m: m.update(solution_kind="vehicle_routes"), "solution_kind"),
    (lambda m: m.update(claim="TSPLIB solved, beats all heuristics"), "claim"),
    (lambda m: m["limits"].update(threads=4), "threads"),
    (lambda m: m["limits"].update(total_seconds_per_instance=60), "600"),
    (lambda m: m["solvers"]["gurobi"].update(threads=2), "threads"),
    (lambda m: m["solvers"]["gurobi"].update(option_string="bestbound=1 tech:threads=1 lim:time=600"), "bestbound"),
    (lambda m: m["solvers"]["gurobi"].update(option_string="mip:bestbound=1 tech:threads=1 tech:seed=0 lim:time=60"), "lim:time"),
    (lambda m: m["solvers"]["gurobi"].update(option_string=m["solvers"]["gurobi"]["option_string"] + " lim:work=20"), "work"),
    (lambda m: m["solvers"].pop("highs"), "highs"),
    (lambda m: m["instances"]["eil51"].update(sha256="xyz"), "sha256"),
    (lambda m: m["instances"]["eil51"].update(matrix_sha256="xyz"), "matrix_sha256"),
    (lambda m: m["instances"]["eil51"].pop("published_optimum"), "published_optimum"),
    (lambda m: m["instances"]["eil51"].update(published_source="our heuristic"), "published_source"),
    (lambda m: m["instances"]["eil51"].update(data_source="best_solutions"), "data_source"),
    (lambda m: m["ampl"].update(location="C:/Users/someone/AMPL"), "location"),
    (lambda m: m.update(note="see C:/Users/someone/x"), "absolute path"),
    (lambda m: m.update(note="Licensed to someone, licence file"), "license"),
    (lambda m: m.update(note="owner@example.com"), "e-mail"),
])
def test_tsp_reference_manifest_rejects_invalid_content(mutate, needle):
    m = _tsp_manifest()
    mutate(m)
    assert any(needle.lower() in e.lower() for e in _proto().validate_tsp_reference_manifest(m)), needle


def test_tsp_reference_validator_does_not_mutate_and_other_validators_are_unchanged():
    import json

    p = _proto()
    m = _tsp_manifest()
    before = json.dumps(m, sort_keys=True)
    p.validate_tsp_reference_manifest(m)
    assert json.dumps(m, sort_keys=True) == before
    assert p.validate_manifest(_manifest()) == []
