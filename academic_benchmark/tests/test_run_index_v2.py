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
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

import test_study_run_service as svc
import test_study_smoke_composite as comp
from academic_benchmark.analysis.manifests import (
    ManifestError,
    file_sha256,
    home_relative,
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
    (lambda d: d["output_location"].update(path="~other/out"), "only the own home folder is written as a tilde"),
    (lambda d: d["output_location"].update(path="~\\out"), "the tilde form is ~ or ~/<rest>"),
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
    assert index.output_location.path == home_relative(out.resolve())  # the home prefix is written as ~ (A20 L8)
    check = index.output_location.outside_repository_check
    assert check.result == "outside_repository" and home_relative(root.resolve()) in check.checked_against


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
    assert index.output_location.path == home_relative(out.resolve())  # the home prefix is written as ~ (A20 L8)
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


# ------------------------------------------------------------------------------------------------ run-index polish 1
def test_a_smoke_run_whose_plan_file_exists_but_does_not_resolve_records_no_hash_and_says_why(tmp_path):
    """A hash of a plan that did not resolve describes nothing the analysis used: the plan file is there but names another
    plan id, so the index records the id with a null path and a null hash, and the reason stays in the run report."""
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    plan_file = root / "studies" / "analysis_plan.json"
    payload = json.loads(plan_file.read_text(encoding="utf-8"))
    payload["analysis_plan_id"] = "some-other-plan-v9"
    plan_file.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    report = svc.run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(),
                           git_provider=svc.CLEAN, replicates=1)
    assert report.status == "passed", report.text
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.analysis_plan.analysis_plan_id == "fixture-plan-v1"
    assert index.analysis_plan.path is None and index.analysis_plan.sha256 is None
    assert "unresolved" in report.text and "some-other-plan-v9" in report.text
    assert verify_campaign_detailed(out).ok


def test_the_plan_hash_is_recorded_when_the_plan_resolves_even_as_a_draft(smoke):
    root, out, _report = smoke
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    assert index.analysis_plan.path == "studies/analysis_plan.json"
    assert index.analysis_plan.sha256 == _sha(root / "studies" / "analysis_plan.json")


# ------------------------------------------------------------------------------------------------ failed-run record contract (readiness 2, part 5)
def _failed_record(**changes) -> dict:
    record = {
        "algorithm_id": "a", "dataset_id": "tsplib-eil51", "problem": "eil51", "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget", "evaluation_budget": 63750, "replicate": 0, "stage": "run",
        "exception_category": "RuntimeError", "error": "synthetic failure",
    }
    record.update(changes)
    return record


def test_a_fixed_budget_failed_record_without_an_evaluation_budget_is_refused_not_turned_into_null():
    from academic_benchmark.analysis.manifests import failed_run_entries

    assert failed_run_entries([_failed_record()])[0].evaluation_budget == 63750
    missing = _failed_record()
    del missing["evaluation_budget"]
    with pytest.raises(ManifestError, match="evaluation_budget"):
        failed_run_entries([missing])
    with pytest.raises(ManifestError, match="evaluation_budget"):
        failed_run_entries([_failed_record(evaluation_budget=None)])


def test_a_native_failed_record_has_no_budget_and_is_accepted():
    from academic_benchmark.analysis.manifests import failed_run_entries

    native = _failed_record(protocol_version="uniride-native-tsp-v1", comparison_regime="algorithm_native_termination", evaluation_budget=None)
    assert failed_run_entries([native])[0].evaluation_budget is None
    without_key = dict(native)
    del without_key["evaluation_budget"]
    assert failed_run_entries([without_key])[0].evaluation_budget is None  # a native run has no budget to record


def test_the_index_contract_itself_refuses_a_fixed_failed_record_without_a_budget(paper):
    _root, out, _report = paper
    data = _index_json(out)
    data["status"], data["failed_runs"] = "failed", [_failed_record(evaluation_budget=None)]
    with pytest.raises(ValidationError, match="evaluation_budget"):
        RunIndexV2.model_validate(data)


def test_a_negative_replicate_is_refused_by_the_contract_and_the_schema():
    from academic_benchmark.contracts.run_index import FailedRunV1

    with pytest.raises(ValidationError):
        FailedRunV1.model_validate(_failed_record(replicate=-1))
    assert FailedRunV1.model_validate(_failed_record(replicate=0)).replicate == 0
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "run-index-v2.schema.json").read_text(encoding="utf-8"))
    assert schema["$defs"]["FailedRunV1"]["properties"]["replicate"]["minimum"] == 0


def _schema_refuses_failed_record(definition: dict, record: dict) -> bool:
    """Evaluates only the ``if``/``then`` of the exported FailedRunV1 definition (``jsonschema`` is not installed): refused when
    the ``if`` holds and the ``then`` requires a key the record lacks or a type it does not have."""
    condition, consequence = definition["if"], definition["then"]
    holds = all(key in record for key in condition["required"]) and all(
        record[name] == rule["const"] for name, rule in condition["properties"].items()
    )
    if not holds:
        return False
    types = {"integer": int}
    for key in consequence["required"]:
        if key not in record:
            return True
    for name, rule in consequence["properties"].items():
        value = record[name]
        if isinstance(value, bool) or not isinstance(value, types[rule["type"]]):
            return True
    return False


def test_the_exported_schema_refuses_a_fixed_failed_record_without_a_budget():
    """The pydantic validator is not the only place of the rule: the exported (and the committed) JSON schema says it too."""
    for schema in (
        json.loads(render_schemas()["run-index-v2.schema.json"]),
        json.loads((Path(__file__).resolve().parents[1] / "schemas" / "run-index-v2.schema.json").read_text(encoding="utf-8")),
    ):
        definition = schema["$defs"]["FailedRunV1"]
        assert "if" in definition and "then" in definition
        assert _schema_refuses_failed_record(definition, _failed_record(evaluation_budget=None))  # fixed regime, null budget
        missing = _failed_record()
        del missing["evaluation_budget"]
        assert _schema_refuses_failed_record(definition, missing)
        assert not _schema_refuses_failed_record(definition, _failed_record())  # fixed regime with its budget
        native = _failed_record(protocol_version="uniride-native-tsp-v1", comparison_regime="algorithm_native_termination", evaluation_budget=None)
        assert not _schema_refuses_failed_record(definition, native)  # null is for native runs


# ------------------------------------------------------------------------------------------------ L8: no user name in output_location.path
def _fake_home(monkeypatch, home: Path) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert Path.home() == home
    return home


def test_the_output_location_is_written_with_the_home_prefix_replaced_by_a_tilde(tmp_path, monkeypatch):
    from academic_benchmark.analysis.manifests import outside_location

    home = _fake_home(monkeypatch, tmp_path / "alice")
    inside = home / "campaigns" / "paper-1"
    assert outside_location(inside, [tmp_path / "repo"])["path"] == "~/campaigns/paper-1"
    assert outside_location(home, [tmp_path / "repo"])["path"] == "~"
    elsewhere = tmp_path / "data" / "out"
    assert outside_location(elsewhere, [tmp_path / "repo"])["path"] == str(elsewhere.resolve())  # not under the home folder: unchanged
    from academic_benchmark.contracts.run_index import OutputLocationV1

    record = outside_location(inside, [tmp_path / "repo"])
    assert OutputLocationV1.model_validate(record).path == "~/campaigns/paper-1"  # the contract accepts the tilde form


def test_only_a_leading_home_prefix_is_replaced(tmp_path, monkeypatch):
    from academic_benchmark.analysis.manifests import outside_location

    home = _fake_home(monkeypatch, tmp_path / "bob")
    lookalike = tmp_path / "bobby" / "out"  # shares the text prefix, is not under the home folder
    assert outside_location(lookalike, [tmp_path / "repo"])["path"] == str(lookalike.resolve())
    nested = tmp_path / "x" / "bob" / "out"  # the home folder's name as a later component only
    assert outside_location(nested, [tmp_path / "repo"])["path"] == str(nested.resolve())
    assert outside_location(home / "bob" / "bob", [tmp_path / "repo"])["path"] == "~/bob/bob"


@pytest.mark.skipif(os.name != "nt", reason="path case is insignificant on Windows only")
def test_the_home_prefix_is_matched_case_insensitively_on_windows(tmp_path, monkeypatch):
    from academic_benchmark.analysis.manifests import outside_location

    home = _fake_home(monkeypatch, tmp_path / "Carol")
    shouted = Path(str(home).upper()) / "Out"
    assert outside_location(shouted, [tmp_path / "repo"])["path"] == "~/Out"


@pytest.mark.skipif(os.name != "nt", reason="path case is insignificant on Windows only")
def test_home_relative_compares_an_unresolved_path_with_normcase(tmp_path, monkeypatch):
    """``outside_location`` resolves its output path (which also repairs the case), so the test above cannot see whether
    ``home_relative`` compares case-insensitively; here it is called directly with a path whose home part differs in case."""
    from academic_benchmark.analysis.manifests import home_relative

    home = (tmp_path / "Erin").resolve()
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    shouted = Path(str(home).upper()) / "Work"
    assert str(shouted) != str(home / "Work")  # the spelling really differs in case
    assert home_relative(shouted) == "~/Work"
    assert home_relative(Path(str(home).lower())) == "~"


def test_the_verifier_expands_the_tilde_and_old_absolute_paths_still_verify(smoke, monkeypatch):
    _root, out, _report = smoke
    _fake_home(monkeypatch, out.parent)
    _reseal(out, lambda d: d["output_location"].update(path=f"~/{out.name}"))
    result = verify_campaign_detailed(out)
    assert result.ok, result.errors
    assert not any("recorded output location" in note for note in result.notes)  # ~ expands to this folder: not moved
    _reseal(out, lambda d: d["output_location"].update(path=str(out.resolve())))  # an index written before L8
    result = verify_campaign_detailed(out)
    assert result.ok and not any("recorded output location" in note for note in result.notes)
    _reseal(out, lambda d: d["output_location"].update(path=f"~/{out.name}"))
    _fake_home(monkeypatch, out.parent / "elsewhere")  # another home folder: the folder is not where the index says
    assert any("recorded output location" in note for note in verify_campaign_detailed(out).notes)
    _reseal(out, lambda d: d["output_location"].update(path=str(out.resolve())))  # leave the shared fixture as it was


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _all_strings(key)
            yield from _all_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _all_strings(item)


def test_checked_against_is_written_without_the_home_prefix(tmp_path, monkeypatch):
    from academic_benchmark.analysis.manifests import outside_location

    home = _fake_home(monkeypatch, tmp_path / "dora")
    elsewhere = tmp_path / "mirror" / "repo"
    record = outside_location(home / "out", [home / "repo", elsewhere, home])
    assert record["outside_repository_check"]["checked_against"] == ["~/repo", str(elsewhere), "~"]
    strings = list(_all_strings(record))  # the decoded values, not their JSON text (where a Windows backslash is doubled)
    assert len(strings) >= 4
    assert not [s for s in strings if str(home) in s or home.as_posix() in s]  # neither the path nor the checked trees carry the home prefix


def test_an_index_with_absolute_checked_against_paths_still_verifies_and_so_does_the_tilde_form(smoke, monkeypatch):
    """Nothing in the verifier compares ``checked_against``; old indexes (absolute) and new ones (``~``) both verify."""
    root, out, _report = smoke
    original = _index_json(out)["output_location"]["outside_repository_check"]["checked_against"]
    try:
        _reseal(out, lambda d: d["output_location"]["outside_repository_check"].update(checked_against=[str(root.resolve())]))
        assert verify_campaign_detailed(out).ok
        _fake_home(monkeypatch, root.parent)
        _reseal(out, lambda d: d["output_location"]["outside_repository_check"].update(checked_against=[f"~/{root.name}"]))
        result = verify_campaign_detailed(out)
        assert result.ok, result.errors
    finally:
        _reseal(out, lambda d: d["output_location"]["outside_repository_check"].update(checked_against=original))
