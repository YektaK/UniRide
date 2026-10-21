"""WP-E11 J9c: the runner's label hook is J9b's ``label_cell`` (no placeholder), end to end with the fake backend.

Every test runs the real runner (certification, independent checker, wave-value verdicts, bounds) and the real
``uniride_core.exact.day_labels.label_cell``; only the solvers and the TypeScript CLI are the fakes of
``test_exact_day_joint_runner.py``. Proof gates under test (DECISION_LOG E14 and its 2026-10-20 / 2026-10-21 notes):
``optimal`` and ``infeasible_solver_proven`` need the day verdict ``agree``; a tier-2 certificate needs the wave verdict;
``optimal_stage1_by_bound`` needs a verified LB0 / LB0w / LB_S equal to stage 1 and the wave verdict (day verdict not
blocking); any ``bound_above_incumbent`` withholds the claim; a blocking verdict of either kind rejects the cell.
"""
from __future__ import annotations

import dataclasses
import json

import pytest

import test_exact_day_joint_runner as base
from test_exact_day_joint_runner import SUBSET, clean_git, hb, make_deps, make_fake_day_solver, read_csv, rj, run

__all__ = ["clean_git"]  # the autouse fixture of the runner tests (clean git state)
HOMO = rj.HOMOGENEOUS
LABEL_COLUMNS = ("bound_proof", "flags", "unverified_bounds", "proof_claim_allowed", "proof_claim_reason", "reason")


def one_row(tmp_path, *args, deps=None, fleets=HOMO, subset=SUBSET):
    rc, out = run(tmp_path, "--fleets", fleets, *subset, *args, deps=deps)
    return rc, read_csv(out / "day_joint.csv")[0], out


# ---------------------------------------------------------------- the columns
def test_day_joint_csv_has_the_cell_label_columns():
    for column in LABEL_COLUMNS:
        assert column in rj.CSV_FIELDS
    assert rj.CSV_FIELDS.index("bound_source") < rj.CSV_FIELDS.index("proof_claim_allowed")


# ---------------------------------------------------------------- (1) optimal with the day verdict agree
@pytest.mark.parametrize("fleets", [HOMO, "large+sedan"])
def test_agreeing_cell_is_optimal_and_may_claim_a_proof(tmp_path, fleets):
    rc, row, _ = one_row(tmp_path, fleets=fleets)
    assert rc == 0
    assert (row["day_status"], row["crosscheck_status"], row["wave_values_status"]) == ("optimal", "agree", "agree")
    assert row["proof_claim_allowed"] == "True" and row["proof_claim_reason"] == "crosscheck_agree"


# ---------------------------------------------------------------- (2) wave blocking rejects, even when the day verdict agrees
def test_wave_blocking_rejects_the_cell_although_the_day_verdict_agrees(tmp_path):
    rc, row, _ = one_row(tmp_path, deps=base.deps_with_waves(base.skewed_wave_solver("plus1")))
    assert rc == 1
    assert row["crosscheck_status"] == "agree" and row["wave_values_status"] == "blocking"
    assert row["day_status"] == "rejected" and row["proof_claim_allowed"] == "False"
    assert row["reason"] == "wave_values_crosscheck_disagreement"


# ---------------------------------------------------------------- (3) and (4) certificates
def test_tier1_certificate_claims_without_any_verdict(tmp_path, monkeypatch):
    rc, row, seen, calls = base._certificate_cell(tmp_path, monkeypatch, "not_run", 1)
    assert row["day_status"] == "infeasible_certified" and row["certificate_tier"] == "1" and calls == []
    assert row["proof_claim_allowed"] == "True" and row["proof_claim_reason"] == "arithmetic_certificate"
    assert row["crosscheck_status"] == "not_run" and row["wave_values_status"] == "not_run"


def test_tier2_certificate_with_agreeing_wave_values_claims(tmp_path, monkeypatch):
    rc, row, seen, calls = base._certificate_cell(tmp_path, monkeypatch, "agree", 2)
    assert row["day_status"] == "infeasible_certified" and row["certificate_tier"] == "2" and calls == []
    assert row["proof_claim_allowed"] == "True" and row["proof_claim_reason"] == "wave_values_crosscheck_agree"


def _infeasible_proven(result):
    return dataclasses.replace(result, status="infeasible_proven", stages=(), objective=None)


@pytest.mark.parametrize("wave_status", ["inconclusive", "not_run"])
def test_tier2_certificate_without_wave_agreement_is_withheld(tmp_path, monkeypatch, wave_status):
    deps = make_deps(crosscheck=False, highs_hook=_infeasible_proven)
    bm = rj.bounds_mod
    cert_ = bm.InfeasibilityCertificate(bm.INFEASIBLE_CERTIFIED, 2, "certificate_wave_min_large", 10, 11, 525,
                                        (bm.Contribution("w1", 11, "solver_proven"),))
    real = rj.day_bounds

    def fake_bounds(instance, fleet, limit, deps_, cfg, errors, tag):
        b, records = real(instance, fleet, limit, deps_, cfg, errors, tag)
        records = [rj.WaveRecord(r.kind, r.wave_id, r.used, wave_status, r.detail) for r in records]
        return bm.DayBounds(lb_l=b.lb_l, lb_s=b.lb_s, certificate=cert_), records

    monkeypatch.setattr(rj, "day_bounds", fake_bounds)
    rc, row, _ = one_row(tmp_path, "--no-crosscheck", deps=deps, fleets="large+sedan")
    assert row["proof_claim_allowed"] == "False"
    assert row["proof_claim_reason"] == f"wave_values_crosscheck_{wave_status}"


def test_tier2_certificate_with_blocking_wave_values_is_rejected(tmp_path, monkeypatch):
    rc, row, seen, calls = base._certificate_cell(tmp_path, monkeypatch, "blocking", 2)
    assert row["day_status"] == "rejected" and row["proof_claim_allowed"] == "False"
    assert row["reason"] == "wave_values_crosscheck_disagreement"


# ---------------------------------------------------------------- (5) optimal_stage1_by_bound
def _time_limited_stage1(result):
    stages = list(result.stages)
    s1 = stages[0]
    k = s1.result.objective
    r1 = dataclasses.replace(s1.result, status="feasible_with_gap", stop_reason="wall_limit", bound=k - 1, bound_ceil=k - 1)
    stages[0] = dataclasses.replace(s1, result=r1)
    return dataclasses.replace(result, status="feasible_with_gap", stages=tuple(stages))


def _date_where_lb0_equals_stage1(tmp_path):
    rc, out = run(tmp_path / "probe", "--fleets", HOMO, "--rides", "50")
    stages = {(r["date"]): r for r in read_csv(out / "day_joint_stages.csv") if r["solver"] == "highs" and r["stage"] == "1"}
    for r in read_csv(out / "day_joint.csv"):
        if r["lb0"] != "" and int(r["lb0"]) == int(float(stages[r["date"]]["objective"])):
            return r["date"]
    pytest.fail("no committed day has LB0 == the fake stage-1 value; the by-bound cell cannot be built")


def test_by_bound_cell_claims_with_wave_agreement_and_an_inconclusive_day_verdict(tmp_path):
    date = _date_where_lb0_equals_stage1(tmp_path)
    deps = make_deps(highs_hook=_time_limited_stage1)
    rc, row, _ = one_row(tmp_path / "run", deps=deps, subset=("--rides", "50", "--dates", date))
    assert row["day_status"] == "optimal_stage1_by_bound"
    assert row["crosscheck_status"] != "blocking" and row["crosscheck_status"] != "agree"
    assert row["wave_values_status"] == "agree"
    assert row["bound_source"] in ("lb0", "lb0w") and row["bound_proof"] == "solver_proven"
    assert row["proof_claim_allowed"] == "True" and row["proof_claim_reason"] == "checked_plan_and_wave_values_agree"


def test_by_bound_cell_without_wave_agreement_does_not_claim(tmp_path):
    date = _date_where_lb0_equals_stage1(tmp_path)
    deps = base.deps_with_waves(base.skewed_wave_solver("bound"), highs_hook=_time_limited_stage1)
    rc, row, _ = one_row(tmp_path / "run", deps=deps, subset=("--rides", "50", "--dates", date))
    assert row["wave_values_status"] == "inconclusive"
    assert row["proof_claim_allowed"] == "False" and row["proof_claim_reason"] == "wave_values_crosscheck_inconclusive"


# ---------------------------------------------------------------- (6) bound_above_incumbent withholds
def _bound_above_incumbent(result):
    stages = list(result.stages)
    s1 = stages[0]
    r1 = dataclasses.replace(s1.result, solver_message=hb.BOUND_ABOVE_INCUMBENT + " (planted)")
    stages[0] = dataclasses.replace(s1, result=r1)
    return dataclasses.replace(result, stages=tuple(stages))


def test_bound_above_incumbent_withholds_the_claim(tmp_path):
    rc, row, _ = one_row(tmp_path, deps=make_deps(highs_hook=_bound_above_incumbent))
    assert row["day_status"] == "optimal" and row["crosscheck_status"] == "agree"
    assert row["proof_claim_allowed"] == "False" and row["proof_claim_reason"] == hb.BOUND_ABOVE_INCUMBENT
    assert row["flags"].startswith(hb.BOUND_ABOVE_INCUMBENT + ":stage1")
    assert row["unverified_bounds"] == "" or isinstance(row["unverified_bounds"], str)


# ---------------------------------------------------------------- (7) --no-crosscheck: development run, no claim anywhere
@pytest.mark.parametrize("fleets", [HOMO, "large+sedan"])
def test_no_crosscheck_run_claims_nothing_and_is_a_development_run(tmp_path, fleets):
    rc, out = run(tmp_path, "--fleets", fleets, *SUBSET, "--no-crosscheck", deps=make_deps(crosscheck=False))
    rows = read_csv(out / "day_joint.csv")
    assert rc == 0 and rows
    assert all(r["proof_claim_allowed"] == "False" for r in rows)
    assert all(r["proof_claim_reason"] in ("crosscheck_not_run", "wave_values_crosscheck_not_run") for r in rows)
    assert json.loads((out / rj.MANIFEST_FILENAME).read_text(encoding="utf-8"))["development_run"] is True


# ---------------------------------------------------------------- runner rejections are final
def _failing_cli(cases):
    return {c["caseId"]: {"caseId": c["caseId"], "ok": False, "assignment": {"status": "proven", "cars": 0},
                          "problems": ["planted"], "recheck": {"routesChecked": 0, "failures": []}, "intervalDifferences": []}
            for c in cases}, ""


def test_a_failing_ts_confirmation_stays_rejected_whatever_label_cell_says(tmp_path):
    rc, row, _ = one_row(tmp_path, deps=make_deps(cli=_failing_cli), fleets="large+sedan")
    assert rc == 1 and row["ts_confirmation"] == "failed"
    assert row["day_status"] == "rejected" and row["proof_claim_allowed"] == "False"


def test_input_rejected_row_claims_nothing(tmp_path, monkeypatch):
    real = rj.read_json

    def altered(path):
        doc = real(path)
        if str(path).endswith(".menu_options.json"):
            doc = json.loads(json.dumps(doc))
            doc["waves"][0]["anchorMinutes"] += 1
        return doc

    monkeypatch.setattr(rj, "read_json", altered)
    rc, row, _ = one_row(tmp_path, fleets="large+sedan")
    assert row["day_status"] == "input_rejected" and row["proof_claim_allowed"] == "False"


def test_the_runner_label_is_label_cell_not_a_placeholder():
    import inspect

    assert "label_cell" in inspect.getsource(rj.label_day_cell)
    assert not hasattr(rj, "placeholder_label")


def test_cells_not_proven_counts_unclaimed_optimal_cells(tmp_path):
    rc, out = run(tmp_path, "--fleets", HOMO, *SUBSET, "--no-crosscheck", deps=make_deps(crosscheck=False))
    week = read_csv(out / "day_joint_week.csv")[0]
    assert read_csv(out / "day_joint.csv")[0]["day_status"] == "optimal" and week["cells_not_proven"] == "1"


# ---------------------------------------------------------------- hardening: what the bounds really received
def _spy_compute_day_bounds(monkeypatch):
    calls: list = []
    real = rj.bounds_mod.compute_day_bounds

    def spy(instance, **kw):
        calls.append(kw)
        return real(instance, **kw)

    monkeypatch.setattr(rj.bounds_mod, "compute_day_bounds", spy)
    return calls


def _by_wave(rows, bound):
    out = {}
    for r in rows:
        if r["bound"] == bound:
            wave_id, _, _ = r["contributions"].rsplit(":", 2)  # wave ids hold colons
            out[wave_id] = (r["used_value"], r["used_proof"])
    return out


@pytest.mark.parametrize("fleets,wave_solver", [(HOMO, None), ("large+sedan", None), ("large+sedan", ("plus1", "l")),
                                                (HOMO, ("plus1", None))])
def test_the_bounds_receive_exactly_the_values_lb0_csv_reports(tmp_path, monkeypatch, fleets, wave_solver):
    calls = _spy_compute_day_bounds(monkeypatch)
    deps = base.deps_with_waves(base.skewed_wave_solver(wave_solver[0], only=wave_solver[1])) if wave_solver else None
    rc, row, out = one_row(tmp_path, deps=deps, fleets=fleets)
    assert len(calls) == 1
    lb = read_csv(out / "lb0.csv")
    kw = calls[0]
    k_any = kw.get("k_any", kw.get("k"))
    assert {w: (str(v.value), v.proof) for w, v in k_any.items()} == _by_wave(lb, "wave_k_any")
    if fleets == HOMO:
        assert "l" not in kw
    else:
        assert {w: (str(v.value), v.proof) for w, v in kw["l"].items()} == _by_wave(lb, "wave_l")
        assert kw["large_limit"] == 10
    if wave_solver and wave_solver[1] == "l":
        assert {v.value for v in kw["l"].values()} == {0} and {v.proof for v in kw["l"].values()} == {"arithmetic_floor"}
