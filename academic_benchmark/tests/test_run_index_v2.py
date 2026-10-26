"""Run-index completeness (D-02/D-03 follow-up; D-10 gaps G1, G2, G3, G6, G7): ``uniride-run-index/v2``.

The index of every campaign records what the run service hashed and planned, where it wrote, and which runs failed:
G1 the profile and analysis-plan sha256 (until now only in the deleted ``checkpoint/campaign.json``), G2 the analysis-plan
id, G3 the planned runs per cell and the planned number of runs, G6 the output folder and the outside-the-repository
check made at start, G7 one record per failed run. The verifier refuses v1, checks the failed list against
``failed_runs.jsonl`` and the recorded hashes against the files the campaign names (and says when it cannot).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import test_study_run_service as svc
import test_study_smoke_composite as comp
from academic_benchmark.analysis.manifests import (
    ManifestError,
    file_sha256,
    load_verified_campaign,
    verify_campaign_detailed,
    write_json_with_sidecar,
)
from academic_benchmark.contracts.export_schemas import MODELS, check_schemas, render_schemas
from academic_benchmark.contracts.run_index import RunIndexV2
from academic_benchmark.studies.smoke import run_study_smoke
from academic_benchmark.studies.verify_manifests import main as verify_main

NEW_FIELDS = ("profile", "analysis_plan", "planned", "output_location", "failed_runs")
VICTIM = (svc.ALGS[0], 1, svc.LEVELS[0])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_json(out: Path) -> dict:
    return json.loads((out / "run_index.json").read_text(encoding="utf-8"))


def _reseal(out: Path, mutate, *, outputs=()) -> None:
    """Rewrite ``run_index.json`` (with a fresh sidecar) after ``mutate(data)``; ``outputs`` get their checksums refreshed."""
    data = _index_json(out)
    mutate(data)
    for item in data["outputs"]:
        if item["path"] in outputs:
            item["checksum"]["value"] = file_sha256(out / item["path"])
    write_json_with_sidecar(out / "run_index.json", data)


def _copy(out: Path, tmp_path: Path, name: str = "copy") -> Path:
    import shutil

    target = tmp_path / name
    shutil.copytree(out, target)
    return target


def _errors(out: Path, **kwargs) -> str:
    return "\n".join(verify_campaign_detailed(out, **kwargs).errors)


@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("runidx-paper")
    root = svc._paper_repo(tmp)
    out = tmp / "out"
    return root, out, svc._paper(root, out)


@pytest.fixture(scope="module")
def failed_paper(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("runidx-failed")
    root = svc._paper_repo(tmp)
    out = tmp / "out"
    report = svc._paper(root, out, gateway_executor=svc._gateway(
        fail=lambda k: (k["requested_algorithm_id"], k["run_idx"], k["evaluation_budget"]) == VICTIM))
    return root, out, report


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("runidx-smoke")
    root = svc._paper_repo(tmp, study_active=False, plan_status="draft")
    out = tmp / "out"
    report = svc.run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(),
                           git_provider=svc.CLEAN, replicates=1)
    return root, out, report


# ------------------------------------------------------------------------------------------------ contract
def test_the_schema_is_v2_requires_the_new_fields_and_the_v1_snapshot_is_gone():
    assert "run-index-v1.schema.json" not in MODELS and "run-index-v2.schema.json" in MODELS
    assert check_schemas() == []
    schema = json.loads(render_schemas()["run-index-v2.schema.json"])
    assert schema["$id"] == "uniride-run-index/v2" and schema["additionalProperties"] is False
    assert set(NEW_FIELDS) <= set(schema["required"])
    assert not (Path(__file__).resolve().parents[1] / "schemas" / "run-index-v1.schema.json").exists()


@pytest.mark.parametrize("field", NEW_FIELDS)
def test_every_new_field_is_required(paper, field):
    _root, out, _report = paper
    data = _index_json(out)
    del data[field]
    with pytest.raises(ValidationError):
        RunIndexV2.model_validate(data)


def test_a_v1_index_is_not_a_valid_v2_index(paper):
    _root, out, _report = paper
    data = _index_json(out)
    data["schema_version"] = "uniride-run-index/v1"
    with pytest.raises(ValidationError):
        RunIndexV2.model_validate(data)


@pytest.mark.parametrize("change, what", [
    (lambda d: d["analysis_plan"].update(sha256=None), "a paper index needs the plan file hash"),
    (lambda d: d["analysis_plan"].update(path=None), "a paper index needs the plan file path"),
    (lambda d: d["output_location"].update(path="relative/out"), "the output folder is recorded as an absolute path"),
    (lambda d: d["output_location"]["outside_repository_check"].update(result="inside_repository"), "only a passed check can be recorded"),
    (lambda d: d["output_location"]["outside_repository_check"].update(checked_against=[]), "the check names what it checked against"),
    (lambda d: d["planned"].update(runs=0), "a campaign plans at least one run"),
    (lambda d: d["planned"].update(runs_per_cell=0), "a cell has at least one run"),
    (lambda d: d["profile"].update(sha256="xyz"), "the profile hash is a sha256"),
    (lambda d: d.update(profile={**d["profile"], "extra": 1}), "no free fields"),
])
def test_contract_rules(paper, change, what):
    _root, out, _report = paper
    data = _index_json(out)
    change(data)
    with pytest.raises(ValidationError):
        RunIndexV2.model_validate(data)


def test_a_smoke_index_may_have_no_plan_file_but_a_failed_run_record_needs_its_fields(paper):
    _root, out, _report = paper
    data = _index_json(out)
    data["mode"] = "smoke"
    data["analysis_plan"].update(path=None, sha256=None)
    RunIndexV2.model_validate(data)
    data["failed_runs"] = [{"algorithm_id": "a"}]
    with pytest.raises(ValidationError):
        RunIndexV2.model_validate(data)


# ------------------------------------------------------------------------------------------------ G1, G2, G3, G6: paper
def test_the_paper_index_records_profile_plan_counts_and_output_location(paper):
    root, out, report = paper
    assert report.status == "passed", report.text
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.schema_version == "uniride-run-index/v2"
    assert index.profile.path == "studies/study.json" and index.profile.sha256 == _sha(root / "studies" / "study.json")
    assert index.analysis_plan.analysis_plan_id == "fixture-plan-v1"
    assert index.analysis_plan.path == "studies/analysis_plan.json"
    assert index.analysis_plan.sha256 == _sha(root / "studies" / "analysis_plan.json")
    assert index.planned.runs == 12 and index.planned.runs_per_cell == 2 and len(index.runs) == 12
    assert index.failed_runs == []
    assert index.output_location.path == str(out.resolve())
    check = index.output_location.outside_repository_check
    assert check.result == "outside_repository" and str(root.resolve()) in check.checked_against


def test_the_recorded_hashes_are_the_ones_the_run_service_hashed(paper):
    """The campaign fingerprint and the index come from one reading of the files (resume compares them)."""
    root, out, _report = paper
    from academic_benchmark.studies.service import build_study_plan

    plan = build_study_plan(svc.STUDY, repository_root=root)
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert (plan.study_path, plan.study_sha256) == (index.profile.path, index.profile.sha256)
    assert (plan.analysis_plan_path, plan.analysis_plan_sha256) == (index.analysis_plan.path, index.analysis_plan.sha256)


def test_the_paper_campaign_verifies_and_the_hashes_are_checked_against_the_files(paper):
    root, out, _report = paper
    result = verify_campaign_detailed(out, repository_root=root)
    assert result.ok, result.errors
    assert any("profile" in n and "analysis plan" in n and "match" in n for n in result.notes), result.notes


def test_a_changed_profile_file_fails_the_hash_check(paper, tmp_path):
    root, out, _report = paper
    copied = _copy(root, tmp_path, "repo-copy")
    study = copied / "studies" / "study.json"
    study.write_text(study.read_text(encoding="utf-8") + " ", encoding="utf-8")
    text = _errors(out, repository_root=copied)
    assert "profile" in text and "sha256" in text and "studies/study.json" in text


def test_a_changed_analysis_plan_file_fails_the_hash_check(paper, tmp_path):
    root, out, _report = paper
    copied = _copy(root, tmp_path, "repo-copy")
    plan = copied / "studies" / "analysis_plan.json"
    plan.write_text(plan.read_text(encoding="utf-8") + " ", encoding="utf-8")
    text = _errors(out, repository_root=copied)
    assert "analysis plan" in text and "sha256" in text


def test_a_repository_without_git_or_at_another_commit_is_reported_not_silently_accepted(paper, tmp_path):
    root, out, _report = paper
    nogit = tmp_path / "no-git"
    nogit.mkdir()
    result = verify_campaign_detailed(out, repository_root=nogit)
    assert result.ok and any("not checked" in n for n in result.notes), result.notes
    other = svc._paper_repo(tmp_path, name="other-repo")
    svc._git(other, "commit", "-q", "--allow-empty", "-m", "moved on")
    result = verify_campaign_detailed(out, repository_root=other)
    assert result.ok and any("not checked" in n and "commit" in n for n in result.notes), result.notes


def test_the_cli_prints_the_notes_and_takes_a_repository_root(paper, capsys):
    root, out, _report = paper
    assert verify_main([str(out), "--repository-root", str(root)]) == 0
    printed = capsys.readouterr().out
    assert "OK" in printed and "NOTE" in printed and "match" in printed


# ------------------------------------------------------------------------------------------------ v1 is refused
def _as_v1(data: dict) -> None:
    data["schema_version"] = "uniride-run-index/v1"
    for field in NEW_FIELDS:
        del data[field]


def test_the_verifier_refuses_a_v1_index_with_a_clear_message(paper, tmp_path):
    _root, out, _report = paper
    copied = _copy(out, tmp_path)
    _reseal(copied, _as_v1)
    text = _errors(copied)
    assert "uniride-run-index/v1" in text and "uniride-run-index/v2" in text and "re-run" in text
    with pytest.raises(ManifestError, match="uniride-run-index/v1"):
        load_verified_campaign(copied)


# ------------------------------------------------------------------------------------------------ G3: planned counts
def test_a_paper_index_that_lists_fewer_runs_than_it_planned_does_not_verify(paper, tmp_path):
    _root, out, _report = paper
    copied = _copy(out, tmp_path)
    _reseal(copied, lambda d: d["planned"].update(runs=13))
    assert "planned" in _errors(copied)


def test_no_index_lists_more_runs_than_it_planned(paper, tmp_path):
    _root, out, _report = paper
    copied = _copy(out, tmp_path)
    _reseal(copied, lambda d: (d.update(mode="smoke"), d["planned"].update(runs=3)))
    assert "planned" in _errors(copied)


# ------------------------------------------------------------------------------------------------ G7: failed runs
def test_a_failed_paper_run_is_one_record_in_the_index(failed_paper):
    root, out, report = failed_paper
    assert report.status == "failed" and report.rows_failed == 1
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.status == "failed" and len(index.failed_runs) == 1 and len(index.runs) == 11
    assert index.planned.runs == 12  # 11 completed + 1 failed
    record = index.failed_runs[0]
    assert record.algorithm_id == VICTIM[0] and record.replicate == VICTIM[1] and record.evaluation_budget == VICTIM[2]
    assert record.dataset_id == "tiny10" and record.problem == "tiny10"
    assert record.protocol_version == "uniride-fair-tsp-v2" and record.comparison_regime == "fixed_evaluation_budget"
    assert record.exception_category == "RuntimeError" and "injected solver failure" in record.error
    assert record.stage
    assert "failed_runs.jsonl" in {o.path for o in index.outputs}
    assert verify_campaign_detailed(out, repository_root=root).ok


def test_the_failed_list_equals_the_failed_runs_file(failed_paper):
    _root, out, _report = failed_paper
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    rows = svc._read(out / "failed_runs.jsonl")
    assert [(r["algorithm_id"], r["dataset_id"], r["evaluation_budget"], r["replicate"], r["protocol_version"],
             r["comparison_regime"], r["stage"], r["exception_category"], r["error"]) for r in rows] == \
           [(f.algorithm_id, f.dataset_id, f.evaluation_budget, f.replicate, f.protocol_version, f.comparison_regime,
             f.stage, f.exception_category, f.error) for f in index.failed_runs]


def test_a_failed_runs_file_that_differs_from_the_index_list_does_not_verify(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    copied = _copy(out, tmp_path)
    rows = svc._read(copied / "failed_runs.jsonl")
    rows[0]["replicate"] += 5
    (copied / "failed_runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    _reseal(copied, lambda d: None, outputs=("failed_runs.jsonl",))  # the checksum holds, the content no longer matches
    text = _errors(copied)
    assert "failed" in text and "run_index.json" in text


def test_an_index_that_lists_no_failure_while_the_file_holds_one_does_not_verify(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    copied = _copy(out, tmp_path)
    _reseal(copied, lambda d: d.update(failed_runs=[]))
    assert "failed" in _errors(copied)


def test_an_index_that_lists_a_failure_the_file_does_not_hold_does_not_verify(paper, tmp_path):
    _root, out, _report = paper
    copied = _copy(out, tmp_path)
    record = {
        "algorithm_id": svc.ALGS[0], "dataset_id": "tiny10", "problem": "tiny10", "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget", "evaluation_budget": svc.LEVELS[0], "replicate": 0,
        "stage": "run", "exception_category": "RuntimeError", "error": "invented",
    }
    _reseal(copied, lambda d: d.update(failed_runs=[record], status="failed"))
    assert "failed" in _errors(copied)


def test_the_index_status_must_agree_with_the_failed_list(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    copied = _copy(out, tmp_path)
    _reseal(copied, lambda d: d.update(status="passed"))
    assert "status" in _errors(copied)


# ------------------------------------------------------------------------------------------------ smoke fills the same fields
def test_a_smoke_index_fills_the_same_fields_and_verifies(smoke):
    root, out, report = smoke
    assert report.status == "passed", report.text
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.mode == "smoke"
    assert index.profile.path == "studies/study.json" and index.profile.sha256 == _sha(root / "studies" / "study.json")
    assert index.analysis_plan.analysis_plan_id == "fixture-plan-v1" and index.analysis_plan.sha256 == _sha(root / "studies" / "analysis_plan.json")
    assert index.planned.runs == len(index.runs) == len(comp.COMPOSITES) * 2 and index.planned.runs_per_cell == 1
    assert index.output_location.path == str(out.resolve())
    assert index.output_location.outside_repository_check.result == "outside_repository"
    assert verify_campaign_detailed(out).ok


def test_a_smoke_run_without_a_resolvable_plan_file_records_the_id_and_no_hash(tmp_path):
    root = comp._repository(tmp_path / "repo")  # analysis_plan_id "fixture", no plan file next to the profile
    out = tmp_path / "out"
    report = run_study_smoke(comp._plan(root), out, problem_loader=comp._loader(), repository_root=root, replicates=1,
                             git_provider=svc.CLEAN)
    assert report.status == "passed", report.text
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.analysis_plan.analysis_plan_id == "fixture"
    assert index.analysis_plan.path is None and index.analysis_plan.sha256 is None
    assert index.profile.sha256 == _sha(root / "studies" / "study.json")
    assert verify_campaign_detailed(out).ok


def test_a_smoke_run_that_stops_at_its_first_failure_lists_it_and_planned_exceeds_the_runs_done(tmp_path):
    root = comp._repository(tmp_path / "repo")
    calls = []

    def failing_gateway(**kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("synthetic failure")
        from academic_benchmark.core.execution_gateway import execute_preflighted

        return execute_preflighted(**kwargs)

    out = tmp_path / "out"
    report = run_study_smoke(comp._plan(root), out, problem_loader=comp._loader(), repository_root=root, replicates=1,
                             git_provider=svc.CLEAN, gateway_executor=failing_gateway)
    assert report.status == "failed"
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.status == "failed" and len(index.runs) == 1 and len(index.failed_runs) == 1
    assert index.failed_runs[0].error == "synthetic failure"
    assert index.planned.runs > len(index.runs) + len(index.failed_runs)  # smoke stops at the first failure
    assert verify_campaign_detailed(out).ok


# ------------------------------------------------------------------------------------------------ the writer enforces the same rules
def _writer_kwargs(out: Path, target: Path, **changes) -> dict:
    import shutil

    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    target.mkdir()
    shutil.copy(out / "failed_runs.jsonl", target / "failed_runs.jsonl")
    kwargs = dict(
        mode="smoke", study_id=index.study_id, seed_protocol_version=index.seed_protocol_version, base_seed=index.base_seed,
        git=index.git, environment=index.environment, status="failed", runs=[], output_files=["failed_runs.jsonl"],
        profile=index.profile, analysis_plan=index.analysis_plan, planned={"runs_per_cell": 1, "runs": 5},
        output_location=index.output_location, failed_runs=index.failed_runs,
    )
    kwargs.update(changes)
    return kwargs


def test_the_writer_refuses_a_failed_list_that_differs_from_the_failed_runs_file(failed_paper, tmp_path):
    from academic_benchmark.analysis.manifests import write_run_campaign

    _root, out, _report = failed_paper
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    altered = [index.failed_runs[0].model_copy(update={"replicate": 99})]
    target = tmp_path / "w"
    with pytest.raises(ManifestError, match="differ from failed_runs.jsonl"):
        write_run_campaign(target, **_writer_kwargs(out, target, failed_runs=altered))
    assert not (target / "run_index.json").exists()


def test_the_writer_refuses_fewer_planned_runs_than_listed_and_a_status_that_disagrees(failed_paper, tmp_path):
    from academic_benchmark.analysis.manifests import write_run_campaign

    _root, out, _report = failed_paper
    target = tmp_path / "w"
    with pytest.raises(ManifestError, match="planned"):
        write_run_campaign(target, **_writer_kwargs(out, target, planned={"runs_per_cell": 1, "runs": 1}, runs=[]) | {"failed_runs": [
            *RunIndexV2.model_validate_json((out / "run_index.json").read_bytes()).failed_runs] * 2})
    other = tmp_path / "w2"
    with pytest.raises(ManifestError, match="status"):
        write_run_campaign(other, **_writer_kwargs(out, other, status="passed"))
