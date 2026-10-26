"""The rebuild command of the descriptive report (``python -m academic_benchmark.analysis.campaign_report <dir>``), D-07 polish.

Exit codes: 0 written, 1 written for a campaign whose run status is "failed", 2 refused. A reference cross-check failure is an
integrity refusal (exit 2), the rebuild reads the analysis plan as committed at the campaign's commit, and the three guards that had
no test of their own (no TSP reference listed, main-tree half of the folder guard, exit 1 for a failed campaign) are pinned here.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import test_analysis_report as tar
import test_study_run_service as svc
import test_study_smoke_composite as comp
from academic_benchmark.analysis import campaign_report as cr
from academic_benchmark.analysis.gaps import ReferenceCrossCheckError
from academic_benchmark.exact_reference import reader as reference_reader

REPORT_FILES = ("descriptive_report.txt", "descriptive_report.json")


def _head(root: Path) -> dict:
    """The real HEAD of the fixture repository: the commit a campaign run from it records (and git can show files at)."""
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, timeout=60).stdout.decode().strip()
    return {"revision": revision, "dirty": False}


def _campaign(tmp_path: Path, *, provider=None, git=_head, **run_options):
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    report = svc.run_study(
        svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(), git_provider=git, replicates=1,
        reference_table_provider=provider or tar._raises(FileNotFoundError("none")), **run_options,
    )
    return report, out, root


def _args(root: Path) -> list:
    return ["--study", svc.STUDY, "--repository-root", str(root)]


# ------------------------------------------------------------------------------------------------ integrity refusal
def test_a_reference_cross_check_failure_is_an_integrity_refusal_with_exit_2(tmp_path, monkeypatch, capsys):
    _report, out, root = _campaign(tmp_path)
    monkeypatch.setattr(cr, "default_reference_table", tar._raises(ReferenceCrossCheckError("eil51: two reference sets disagree")))
    assert cr.main([str(out), *_args(root)]) == 2
    assert "REFUSED" in capsys.readouterr().err
    assert not any((out / name).exists() for name in REPORT_FILES)  # no old report is left next to a refused rebuild


def test_a_reference_cross_check_failure_refuses_the_smoke_run_report_too(tmp_path):
    from academic_benchmark.studies.run import StudyRunError

    with pytest.raises(StudyRunError, match="descriptive report refused.*disagree"):
        _campaign(tmp_path / "again", provider=tar._raises(ReferenceCrossCheckError("two reference sets disagree")))


# ------------------------------------------------------------------------------------------------ the plan as committed
def test_the_rebuild_reads_the_analysis_plan_as_it_was_at_the_campaign_commit(tmp_path):
    report, out, root = _campaign(tmp_path)
    assert report.status == "passed", report.text
    plan_file = root / "studies" / "analysis_plan.json"
    plan_file.write_text("{ this plan is no longer valid JSON", encoding="utf-8")  # a later commit changes the plan
    svc._git(root, "add", "-A")
    svc._git(root, "commit", "-q", "-m", "break the plan after the campaign")
    for name in REPORT_FILES:
        (out / name).unlink()
    assert cr.main([str(out), *_args(root)]) == 0  # the plan of the campaign commit still resolves
    text = (out / "descriptive_report.txt").read_text(encoding="utf-8")
    assert "Analysis plan: fixture-plan-v1 (status draft)" in text
    assert "differs" not in text  # the plan read from git is the one the index recorded


def test_the_rebuild_refuses_with_exit_2_when_the_plan_at_the_campaign_commit_cannot_be_read(tmp_path, capsys):
    _report, out, root = _campaign(tmp_path, git=svc.CLEAN)  # the campaign recorded a commit this repository does not have
    assert cr.main([str(out), *_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "campaign commit" in err and "analysis plan" in err


def test_a_plan_file_with_another_line_ending_still_counts_as_the_recorded_plan():
    raw = b'{"a": 1}\n{"b": 2}\n'
    crlf = raw.replace(b"\n", b"\r\n")
    hashes = cr._plan_bytes_hashes(raw)
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == hashes[0]
    assert hashlib.sha256(crlf).hexdigest() in hashes  # the working-tree hash of a CRLF checkout of these committed bytes
    assert hashlib.sha256(raw.replace(b"x", b"y") + b" ").hexdigest() not in hashes


# ------------------------------------------------------------------------------------------------ guards without a test of their own
def test_no_tsp_reference_listed_means_unavailable_not_an_error(tmp_path):
    index = tmp_path / reference_reader.INDEX_RELATIVE_PATH
    index.parent.mkdir(parents=True)
    index.write_text(json.dumps({
        "schema_version": reference_reader.INDEX_SCHEMA,
        "entries": [{"results_dir": "wave-only", "manifest_kind": reference_reader.KIND_WAVE, "manifest_sha256": "0" * 64, "rows": 1}],
    }), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="no tsp_reference"):
        cr.default_reference_table(tmp_path)


def test_the_rebuild_refuses_a_folder_inside_the_main_working_tree_of_a_linked_worktree(tmp_path, monkeypatch, capsys):
    """The folder is outside the worktree ``root`` but inside the main checkout the worktree belongs to."""
    _report, out, root = _campaign(tmp_path)
    main_tree = tmp_path / "main-checkout"
    inside = main_tree / "campaign"
    shutil.copytree(out, inside)
    monkeypatch.setattr("academic_benchmark.studies.run._main_working_tree", lambda _root: main_tree)
    assert cr.main([str(inside), *_args(root)]) == 2
    assert "inside the repository" in capsys.readouterr().err
    assert (inside / "descriptive_report.txt").is_file()  # untouched
    monkeypatch.setattr("academic_benchmark.studies.run._main_working_tree", lambda _root: None)
    assert cr.main([str(inside), *_args(root)]) == 0  # the same folder is fine when no main tree is named


def test_the_rebuild_exits_1_for_a_campaign_whose_run_failed(tmp_path):
    calls = []

    def second_call_fails(**kwargs):
        from academic_benchmark.core.execution_gateway import execute_preflighted

        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("synthetic failure")
        return execute_preflighted(**kwargs)

    report, out, root = _campaign(tmp_path, gateway_executor=second_call_fails)
    assert report.status == "failed"
    for name in REPORT_FILES:
        (out / name).unlink(missing_ok=True)
    assert cr.main([str(out), *_args(root)]) == 1
    assert (out / "descriptive_report.txt").is_file()  # written even though the campaign failed
