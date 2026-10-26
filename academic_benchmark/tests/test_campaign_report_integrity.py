"""Reporting integrity polish (Gate D, A18 D-05/D-07/run-index notes): the verified campaign carries the verifier's notes and is
verified against the root the caller loads the study from, the report compares the plan file it loads with the recorded plan hash
(refusal in paper mode, warning in smoke mode), the rebuild reads the plan as it was at the campaign commit and refuses with exit 2
when it cannot, and a reference cross-check failure is an integrity refusal."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import test_analysis_report as tar
import test_study_run_service as svc
from academic_benchmark.analysis import campaign_report as cr
from academic_benchmark.analysis.manifests import ManifestError, load_verified_campaign
from academic_benchmark.studies.service import load_study_with_plan

WRONG_HASH = "0" * 64


def _sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("integrity-paper")
    root = svc._paper_repo(tmp)
    out = tmp / "out"
    report = svc._paper(root, out)
    assert report.status == "passed", report.text
    return root, out


def _call(out: Path, root: Path, mode: str, **extra):
    loaded = load_study_with_plan(svc.STUDY, repository_root=root, mode=mode)
    return cr.write_smoke_descriptive_report(
        out, study=loaded.study, plan=loaded.analysis_plan.plan, plan_problem=None, root=root,
        run_index={"path": "run_index.json", "sha256": _sha_file(out / "run_index.json"), "manifests": 1},
        reference_table_provider=tar._raises(FileNotFoundError("none")), **extra,
    )


# ------------------------------------------------------------------------------------------------ run-index polish 2: root and notes
def test_load_verified_campaign_verifies_against_the_root_it_is_given_and_returns_the_notes(paper, tmp_path):
    root, out = paper
    loaded = load_verified_campaign(out, repository_root=root)
    assert any("sha256 match" in note for note in loaded.notes), loaded.notes
    copied = tmp_path / "repo-copy"
    shutil.copytree(root, copied)
    plan = copied / "studies" / "analysis_plan.json"
    plan.write_text(plan.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ManifestError, match="analysis plan"):
        load_verified_campaign(out, repository_root=copied)


def test_the_verifier_notes_are_shown_in_the_report_and_in_the_run_text(tmp_path):
    run, out, _root = tar._smoke_with(tmp_path, tar._raises(FileNotFoundError("none")))
    assert "hashes not checked" in run.text  # the smoke fixture ran at a commit the fixture repository is not at: a NOTE, not a pass
    text = (out / "descriptive_report.txt").read_text(encoding="utf-8")
    assert "hashes not checked" in text
    notes = json.loads((out / "descriptive_report.json").read_text(encoding="utf-8"))["notes"]
    assert any("hashes not checked" in note for note in notes)


def test_a_loaded_plan_that_differs_from_the_recorded_hash_is_a_warning_in_smoke_mode(tmp_path):
    _run, out, root = tar._smoke_with(tmp_path, tar._raises(FileNotFoundError("none")))
    lines = _call(out, root, "smoke", plan_sha256=WRONG_HASH)
    assert any("analysis plan" in line and "differs" in line for line in lines), lines
    notes = json.loads((out / "descriptive_report.json").read_text(encoding="utf-8"))["notes"]
    assert any("analysis plan" in note and "differs" in note for note in notes)  # the report says it too


def test_a_loaded_plan_that_equals_the_recorded_hash_gives_no_warning(tmp_path):
    run, out, root = tar._smoke_with(tmp_path, tar._raises(FileNotFoundError("none")))
    assert "differs" not in run.text  # the run service passes the hash of the plan file it loaded
    loaded = load_study_with_plan(svc.STUDY, repository_root=root, mode="smoke")
    lines = _call(out, root, "smoke", plan_sha256=loaded.analysis_plan.sha256)
    assert not any("differs" in line for line in lines), lines


def test_a_loaded_plan_that_differs_from_the_recorded_hash_is_refused_in_paper_mode(paper, tmp_path):
    root, out = paper
    copied = tmp_path / "out-copy"
    shutil.copytree(out, copied)
    with pytest.raises(cr.CampaignReportError, match="analysis plan"):
        _call(copied, root, "paper", plan_sha256=WRONG_HASH)
    assert not (copied / "descriptive_report.txt").exists()
    loaded = load_study_with_plan(svc.STUDY, repository_root=root, mode="paper")
    lines = _call(copied, root, "paper", plan_sha256=loaded.analysis_plan.sha256)
    assert (copied / "descriptive_report.txt").is_file() and not any("differs" in line for line in lines)
