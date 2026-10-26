"""Guards of the run index v2 that had no test of their own (reviewer's surviving mutations, run-index completeness).

Each test pins one guard in isolation: the paper plan-hash validator, the plan path next to the profile, the failed-file output
rule (writer and verifier) and the main working tree in ``checked_against``.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

import test_run_index_v2 as tri
import test_study_run_service as svc
from academic_benchmark.analysis.manifests import ManifestError, write_run_campaign
from academic_benchmark.contracts.run_index import RunIndexV2

paper = tri.paper
failed_paper = tri.failed_paper


def test_a_paper_index_with_neither_plan_path_nor_plan_hash_is_refused(paper):
    """Both None passes the 'recorded together or not at all' rule, so only the paper validator can refuse it."""
    _root, out, _report = paper
    data = tri._index_json(out)
    data["analysis_plan"].update(path=None, sha256=None)
    with pytest.raises(ValidationError, match="paper campaign records the sha256"):
        RunIndexV2.model_validate(data)
    data["mode"] = "smoke"
    RunIndexV2.model_validate(data)  # the same fields are fine in smoke mode


def test_the_verifier_refuses_a_plan_path_that_is_not_next_to_the_profile(paper, tmp_path):
    _root, out, _report = paper
    copied = tri._copy(out, tmp_path)
    tri._reseal(copied, lambda d: d["analysis_plan"].update(path="elsewhere/analysis_plan.json"))
    text = tri._errors(copied)
    assert "next to the profile" in text and "elsewhere/analysis_plan.json" in text


def test_the_verifier_accepts_the_plan_path_next_to_the_profile(paper):
    _root, out, _report = paper
    assert "next to the profile" not in tri._errors(out)


def test_the_verifier_needs_the_failed_file_exactly_when_failures_are_listed(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    copied = tri._copy(out, tmp_path)
    tri._reseal(copied, lambda d: d.update(outputs=[o for o in d["outputs"] if o["path"] != "failed_runs.jsonl"]))
    assert "must be an output exactly when" in tri._errors(copied)


def test_the_verifier_refuses_a_failed_file_output_when_no_failure_is_listed(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    copied = tri._copy(out, tmp_path)
    tri._reseal(copied, lambda d: d.update(failed_runs=[], status="passed"))
    assert "must be an output exactly when" in tri._errors(copied)


def test_the_writer_needs_the_failed_file_exactly_when_failures_are_listed(failed_paper, tmp_path):
    _root, out, _report = failed_paper
    without_file = tmp_path / "w1"
    with pytest.raises(ManifestError, match="must be an output exactly when"):
        write_run_campaign(without_file, **tri._writer_kwargs(out, without_file, output_files=[]))
    assert not (without_file / "run_index.json").exists()
    without_failures = tmp_path / "w2"
    with pytest.raises(ManifestError, match="must be an output exactly when"):
        write_run_campaign(without_failures, **tri._writer_kwargs(out, without_failures, failed_runs=[], status="passed"))
    assert not (without_failures / "run_index.json").exists()


# ------------------------------------------------------------------------------------------------ main tree in checked_against
def _checked_against(tmp_path, monkeypatch, main_tree):
    root = svc._paper_repo(tmp_path)
    monkeypatch.setattr("academic_benchmark.studies.run._main_working_tree", lambda _root: main_tree(root))
    out = tmp_path / "out"
    report = svc._paper(root, out)
    assert report.status == "passed", report.text
    index = RunIndexV2.model_validate_json((out / "run_index.json").read_bytes())
    return root, index.output_location.outside_repository_check.checked_against


def test_the_check_lists_the_main_working_tree_when_it_differs_from_the_root(tmp_path, monkeypatch):
    main = tmp_path / "main-checkout"
    main.mkdir()
    root, checked = _checked_against(tmp_path, monkeypatch, lambda _root: main)
    assert checked == [str(root), str(main)]


def test_the_check_lists_the_root_once_when_it_is_the_main_working_tree(tmp_path, monkeypatch):
    root, checked = _checked_against(tmp_path, monkeypatch, lambda repo: repo)
    assert checked == [str(root)]


def test_the_check_lists_only_the_root_when_git_cannot_name_the_main_tree(tmp_path, monkeypatch):
    root, checked = _checked_against(tmp_path, monkeypatch, lambda _repo: None)
    assert checked == [str(root)]
