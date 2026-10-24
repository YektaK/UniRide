"""Gate D, D-03: study run service with smoke and paper modes (plan 2026-10-23, section 3, D-03; DECISION_LOG A18).

Paper mode is built and tested here, not used for paper-scale runs. The synthetic ``tiny10`` study of the C-13 fixture
(composite IDs, fixed and native rows) is copied into a temporary git repository, made ``active`` with an active
analysis plan, and run through ``academic_benchmark.studies.run``. Real profiles are only used to show that paper mode
refuses them today (both are ``draft``, and so are their analysis plans).
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import test_study_smoke_composite as comp
from academic_benchmark.analysis import environment as analysis_environment
from academic_benchmark.analysis.environment import AnalysisEnvironmentError, statistics_library_identifier
from academic_benchmark.analysis.manifests import collect_environment, verify_campaign
from academic_benchmark.contracts.run_index import RunIndexV1
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.studies import build_study_plan
from academic_benchmark.studies import run as run_module
from academic_benchmark.studies.run import StudyRunError, build_artifact_loader, main, run_study
from academic_benchmark.studies.smoke import (
    SMOKE_MAX_REPLICATES, StudySmokeError, assert_no_ranking_words, comparable_row, write_rows_file,
)
from academic_benchmark.studies.service import fixed_budget_levels_for

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STUDY = "studies/study.json"
ALGS = list(comp.COMPOSITES[:2])
LEVELS = [20 * comp.SCAN, 40 * comp.SCAN]  # 900, 1800
COMMIT = "c" * 40
CLEAN = lambda _root: {"revision": COMMIT, "dirty": False}  # noqa: E731
DIRTY = lambda _root: {"revision": COMMIT, "dirty": True}  # noqa: E731
UNKNOWN = lambda _root: {"revision": None, "dirty": None, "git_error": "unavailable"}  # noqa: E731


class _Killed(BaseException):
    """Simulates a process kill: not an ``Exception``, so no row failure handler may swallow it."""


# ------------------------------------------------------------------------------------------------ fixtures
def _mutate_to_active(payload: dict) -> None:
    payload["status"] = "active"
    payload["algorithm_ids"] = list(ALGS)
    payload["algorithm_parameters"] = {a: comp._entry(a) for a in ALGS}
    payload["scaled_fixed_budget_levels"] = {
        "rule": "two_opt_scan_multiples_v1", "scan_multipliers": [20, 40], "levels_by_dataset": {"tiny10": LEVELS},
    }
    payload["run_count"] = 2
    payload["analysis_plan_id"] = "fixture-plan-v1"


def _analysis_plan(status: str = "active") -> dict:
    plan = json.loads((REPOSITORY_ROOT / "academic_benchmark/studies/yaem2026/analysis_plan.json").read_text("utf-8"))
    plan["analysis_plan_id"] = "fixture-plan-v1"
    plan["study_id"] = "composite-smoke-fixture"
    plan["families"] = [f for f in plan["families"] if f["scope"] == "per_instance"]
    plan["families"][0]["dataset_ids"] = ["tiny10"]
    plan["status"] = status
    if status == "active":
        plan["unresolved"], plan["minimum_n_per_cell"] = [], 5
    return plan


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false", *args],
        cwd=root, check=True, capture_output=True, timeout=60,
    )


def _paper_repo(tmp_path: Path, *, study_active: bool = True, plan_status: str = "active", name: str = "repo") -> Path:
    root = comp._repository(tmp_path / name, mutate=_mutate_to_active if study_active else None)
    if not study_active:  # a draft study, but with the same ids so that the plan still belongs to it
        path = root / STUDY
        payload = json.loads(path.read_text("utf-8"))
        payload["analysis_plan_id"] = "fixture-plan-v1"
        path.write_text(json.dumps(payload), encoding="utf-8")
    (root / "studies" / "analysis_plan.json").write_text(json.dumps(_analysis_plan(plan_status)), encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "fixture")
    return root


def _paper(root: Path, out: Path, **kwargs):
    kwargs.setdefault("problem_loader", comp._loader())
    return run_study(STUDY, out, mode="paper", repository_root=root, **kwargs)


def _gateway(*, kill_after: int | None = None, fail=None, log: list | None = None):
    """Real gateway, optionally killed after ``kill_after`` executed runs and failing the runs ``fail`` accepts."""
    state = {"executed": 0}

    def gateway(**kwargs):
        if log is not None:
            log.append((kwargs["requested_algorithm_id"], kwargs["run_idx"], kwargs["evaluation_budget"]))
        if kill_after is not None and state["executed"] >= kill_after:
            raise _Killed()
        state["executed"] += 1
        if fail is not None and fail(kwargs):
            raise RuntimeError("injected solver failure")
        return execute_preflighted(**kwargs)

    return gateway


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _view(out: Path) -> dict:
    """Comparable rows (no timing) of both result files, keyed by run identity."""
    rows = {}
    for name in ("fixed_runs.jsonl", "native_runs.jsonl"):
        for row in _read(out / name):
            rows[(name, row["algorithm_id"], row["evaluation_budget"], row["replicate"])] = comparable_row(row)
    return rows


# ---------------------------------------------------------------------------- paper mode refusals (no execution)
@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_paper_mode_refuses_both_real_profiles_naming_the_status(tmp_path, study):
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match="status 'draft'"):
        run_study(f"academic_benchmark/studies/{study}/study.json", out, mode="paper",
                  repository_root=REPOSITORY_ROOT, git_provider=CLEAN)
    assert not out.exists()


@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_paper_mode_refuses_the_real_draft_analysis_plans_even_when_the_profile_is_active(tmp_path, study):
    root = tmp_path / "repo"
    source = REPOSITORY_ROOT / "academic_benchmark" / "studies" / study
    target = root / "academic_benchmark" / "studies" / study
    target.mkdir(parents=True)
    profile = json.loads((source / "study.json").read_text("utf-8"))
    for ref in profile["dataset_manifest_refs"]:
        (root / ref).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPOSITORY_ROOT / ref, root / ref)
    profile["status"] = "active"  # only the profile is forced; the committed plan stays what it is
    (target / "study.json").write_text(json.dumps(profile), encoding="utf-8")
    shutil.copy(source / "analysis_plan.json", target / "analysis_plan.json")
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match="analysis plan.*draft"):
        run_study(f"academic_benchmark/studies/{study}/study.json", out, mode="paper", repository_root=root,
                  git_provider=CLEAN)
    assert not out.exists()


def test_paper_mode_refuses_an_unresolved_analysis_plan(tmp_path):
    root = _paper_repo(tmp_path)
    (root / "studies" / "analysis_plan.json").unlink()
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match="does not resolve"):
        _paper(root, out, git_provider=CLEAN)
    assert not out.exists()


def test_paper_mode_refuses_a_draft_analysis_plan_on_an_active_profile(tmp_path):
    root = _paper_repo(tmp_path, plan_status="draft")
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match="analysis plan.*draft"):
        _paper(root, out, git_provider=CLEAN)
    assert not out.exists()


def test_paper_mode_refuses_a_draft_study_profile(tmp_path):
    root = _paper_repo(tmp_path, study_active=False)
    with pytest.raises(StudyRunError, match="status 'draft'"):
        _paper(root, tmp_path / "out", git_provider=CLEAN)


def test_paper_mode_refuses_a_dirty_tree_in_a_real_git_repository(tmp_path):
    root = _paper_repo(tmp_path)
    (root / "stray.txt").write_text("uncommitted", encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match="dirty"):
        _paper(root, out)  # real git state
    assert not out.exists()


def test_paper_mode_accepts_a_clean_real_git_repository(tmp_path):
    root = _paper_repo(tmp_path)
    report = _paper(root, tmp_path / "out")
    assert report.status == "passed", report.text


@pytest.mark.parametrize("provider,word", [(DIRTY, "dirty"), (UNKNOWN, "unknown")])
def test_paper_mode_refuses_dirty_and_unknown_git_states(tmp_path, provider, word):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    with pytest.raises(StudyRunError, match=word):
        _paper(root, out, git_provider=provider)
    assert not out.exists()


def test_paper_mode_refuses_output_inside_the_repository(tmp_path):
    root = _paper_repo(tmp_path)
    with pytest.raises(StudyRunError, match="inside the repository"):
        _paper(root, root / "results", git_provider=CLEAN)
    assert not (root / "results").exists()


def test_paper_mode_refuses_a_non_empty_output_without_resume(tmp_path):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StudyRunError, match="not empty"):
        _paper(root, out, git_provider=CLEAN)


def test_paper_mode_calls_the_analysis_environment_guard_before_any_write(tmp_path, monkeypatch):
    root = _paper_repo(tmp_path)

    def missing():
        raise AnalysisEnvironmentError("analysis library 'scipy' is not installed")

    monkeypatch.setattr(run_module, "require_analysis_environment", missing)
    out = tmp_path / "out"
    with pytest.raises(AnalysisEnvironmentError, match="scipy"):
        _paper(root, out, git_provider=CLEAN)
    assert not out.exists()


# ---------------------------------------------------------------------------------- paper mode, full campaign
@pytest.fixture(scope="module")
def paper_campaign(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("d03")
    root = _paper_repo(tmp)
    out = tmp / "out"
    return root, out, _paper(root, out)


def test_paper_campaign_runs_every_plan_row_and_verifies(paper_campaign):
    root, out, report = paper_campaign
    plan = build_study_plan(STUDY, repository_root=root)
    assert report.status == "passed", report.text
    assert report.mode == "paper" and report.rows_planned == len(plan.rows) == 12
    fixed, native = _read(out / "fixed_runs.jsonl"), _read(out / "native_runs.jsonl")
    assert len(fixed) == 8 and len(native) == 4
    assert {r["evaluation_budget"] for r in fixed} == set(LEVELS)  # the whole level list, not the smoke slice
    assert {r["replicate"] for r in fixed} == {0, 1}
    assert verify_campaign(out) == []
    assert not (out / "checkpoint").exists()  # progress files are gone once the campaign is final


def test_paper_rows_are_validated_like_smoke_rows_and_are_not_smoke(paper_campaign):
    _root, out, _report = paper_campaign
    for row in _read(out / "fixed_runs.jsonl") + _read(out / "native_runs.jsonl"):
        assert row["validation_status"] == "passed" and row["hamiltonian_validation"] == "passed"
        assert row["smoke"] is False
        assert row["study_id"] == "composite-smoke-fixture"
    assert all(r["composition"]["stages"] for r in _read(out / "fixed_runs.jsonl"))


def test_paper_index_records_the_mode_the_clean_commit_and_the_statistics_library(paper_campaign):
    root, out, _report = paper_campaign
    index = RunIndexV1.model_validate_json((out / "run_index.json").read_bytes())
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    assert index.mode == "paper" and index.status == "passed"
    assert index.git.commit == head and index.git.dirty is False
    assert index.environment.statistics_library == statistics_library_identifier()
    assert index.environment.statistics_library != "none"
    assert len(index.runs) == 12


def test_paper_report_names_mode_commit_and_makes_no_claim(paper_campaign):
    _root, out, report = paper_campaign
    text = (out / "run_report.txt").read_text(encoding="utf-8")
    assert text == report.text
    assert "paper mode" in text.lower() and "working tree clean" in text.lower()
    assert_no_ranking_words(text)
    payload = json.loads((out / "run_report.json").read_text(encoding="utf-8"))
    assert payload["mode"] == "paper" and payload["excluded_cells"] == []


# -------------------------------------------------------------------------------------- interruption and resume
def test_interrupted_run_leaves_nothing_that_verifies_and_resume_equals_an_uninterrupted_run(tmp_path):
    root = _paper_repo(tmp_path)
    whole = tmp_path / "whole"
    _paper(root, whole)
    out = tmp_path / "interrupted"
    with pytest.raises(_Killed):
        _paper(root, out, gateway_executor=_gateway(kill_after=5))
    assert not (out / "run_index.json").exists()
    assert verify_campaign(out) != []  # an interrupted campaign never verifies as complete
    assert not (out / "fixed_runs.jsonl").exists()
    report = _paper(root, out, resume=True)
    assert report.status == "passed", report.text
    assert verify_campaign(out) == []
    assert _view(out) == _view(whole)  # same comparable rows, none duplicated, none missing
    assert len(_read(out / "fixed_runs.jsonl")) == 8 and len(_read(out / "native_runs.jsonl")) == 4
    assert not (out / "checkpoint").exists()


def test_resume_runs_only_the_rows_that_are_not_done(tmp_path):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    with pytest.raises(_Killed):
        _paper(root, out, gateway_executor=_gateway(kill_after=5))
    log: list = []
    _paper(root, out, resume=True, gateway_executor=_gateway(log=log))
    assert len(log) == 12 - 5


def _interrupted(tmp_path, **kwargs):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    with pytest.raises(_Killed):
        _paper(root, out, git_provider=CLEAN, gateway_executor=_gateway(kill_after=3), **kwargs)
    return root, out


def test_resume_refuses_a_changed_profile_parameter(tmp_path):
    root, out = _interrupted(tmp_path)
    path = root / STUDY
    payload = json.loads(path.read_text("utf-8"))
    payload["algorithm_parameters"][ALGS[0]]["global"]["max_iterations"] = 61
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(StudyRunError, match="profile"):
        _paper(root, out, resume=True, git_provider=CLEAN)


def test_resume_refuses_a_changed_commit(tmp_path):
    root, out = _interrupted(tmp_path)
    with pytest.raises(StudyRunError, match="commit"):
        _paper(root, out, resume=True, git_provider=lambda _r: {"revision": "d" * 40, "dirty": False})


def test_resume_refuses_a_changed_environment(tmp_path):
    root, out = _interrupted(tmp_path)

    def other(statistics_library):
        return collect_environment(statistics_library).model_copy(update={"python": "0.0.0"})

    with pytest.raises(StudyRunError, match="environment"):
        _paper(root, out, resume=True, git_provider=CLEAN, environment_provider=other)


def test_resume_refuses_a_tampered_progress_file(tmp_path):
    root, out = _interrupted(tmp_path)
    victim = sorted((out / "checkpoint" / "rows").glob("*.json"))[0]
    data = bytearray(victim.read_bytes())
    data[len(data) // 2] ^= 0x01
    victim.write_bytes(bytes(data))
    with pytest.raises(StudyRunError, match="checksum|corrupt|not valid"):
        _paper(root, out, resume=True, git_provider=CLEAN)


def test_resume_refuses_a_complete_campaign_and_a_missing_one(tmp_path, paper_campaign):
    root, out, _report = paper_campaign
    with pytest.raises(StudyRunError, match="complete"):
        _paper(root, out, resume=True)
    with pytest.raises(StudyRunError, match="nothing to resume"):
        _paper(root, tmp_path / "never-started", resume=True)


# ------------------------------------------------------------------------------------------- failure policy
def test_paper_failure_is_recorded_the_campaign_continues_and_the_cell_is_excluded(tmp_path):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    victim = (ALGS[0], 1, LEVELS[0])
    report = _paper(root, out, gateway_executor=_gateway(
        fail=lambda k: (k["requested_algorithm_id"], k["run_idx"], k["evaluation_budget"]) == victim))
    assert report.status == "failed" and report.rows_failed == 1
    failed = _read(out / "failed_runs.jsonl")
    assert len(failed) == 1 and failed[0]["record_kind"] == "failed_run" and failed[0]["smoke"] is False
    assert (failed[0]["algorithm_id"], failed[0]["replicate"], failed[0]["evaluation_budget"]) == victim
    assert len(_read(out / "fixed_runs.jsonl")) == 7 and len(_read(out / "native_runs.jsonl")) == 4  # the rest ran
    cells = report.excluded_cells
    assert len(cells) == 1 and cells[0]["algorithm_id"] == ALGS[0] and cells[0]["budget_level"] == LEVELS[0]
    assert cells[0]["failed_replicates"] == [1]
    assert "excluded from inference" in report.text
    assert json.loads((out / "run_report.json").read_text("utf-8"))["excluded_cells"] == list(cells)
    assert RunIndexV1.model_validate_json((out / "run_index.json").read_bytes()).status == "failed"
    assert verify_campaign(out) == []


def test_resume_never_retries_a_recorded_failure(tmp_path):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    with pytest.raises(_Killed):
        _paper(root, out, gateway_executor=_gateway(kill_after=4, fail=lambda k: k["run_idx"] >= 0))
    log: list = []
    report = _paper(root, out, resume=True, gateway_executor=_gateway(log=log))
    assert report.rows_failed == 4  # the four recorded failures stay failures (OQ-9 a: no retry)
    assert len(log) == 12 - 4
    assert verify_campaign(out) == []


# ------------------------------------------------------------------------------------------------ smoke mode
def test_smoke_mode_keeps_working_on_a_draft_profile_and_says_descriptive_only(tmp_path):
    root = _paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    report = run_study(STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(),
                       git_provider=CLEAN, replicates=1)
    assert report.status == "passed", report.text
    assert report.mode == "smoke"
    assert "descriptive output only" in report.text
    assert json.loads((out / "smoke_report.json").read_text("utf-8"))["analysis_plan"].startswith("analysis plan")
    assert verify_campaign(out) == []
    assert all(r["smoke"] is True for r in _read(out / "fixed_runs.jsonl"))
    index = RunIndexV1.model_validate_json((out / "run_index.json").read_bytes())
    assert index.mode == "smoke" and index.environment.statistics_library == "none"


def test_smoke_mode_is_not_resumable(tmp_path):
    root = _paper_repo(tmp_path, study_active=False, plan_status="draft")
    with pytest.raises(StudyRunError, match="smoke"):
        run_study(STUDY, tmp_path / "out", mode="smoke", repository_root=root, problem_loader=comp._loader(),
                  git_provider=CLEAN, resume=True)


def test_unknown_mode_is_refused(tmp_path):
    with pytest.raises(StudyRunError, match="mode"):
        run_study(STUDY, tmp_path / "out", mode="full", repository_root=REPOSITORY_ROOT)


# ------------------------------------------------------------------------------------ level guard of the rows file
def test_write_rows_file_accepts_each_datasets_own_level_list_and_refuses_a_foreign_level(tmp_path, paper_campaign):
    _root, out, _report = paper_campaign
    rows = _read(out / "fixed_runs.jsonl")
    write_rows_file(tmp_path / "ok.jsonl", rows, expected_group="fixed_budget",
                    levels_by_dataset={"tiny10": tuple(LEVELS)})
    with pytest.raises(StudySmokeError, match="level"):
        write_rows_file(tmp_path / "bad.jsonl", rows, expected_group="fixed_budget",
                        levels_by_dataset={"tiny10": (LEVELS[0], 5000)})
    assert not (tmp_path / "bad.jsonl").exists()
    with pytest.raises(StudySmokeError):  # without the level list the one-level rule of smoke still holds
        write_rows_file(tmp_path / "old.jsonl", rows, expected_group="fixed_budget")


# --------------------------------------------------------------------------------------------- artifact loader
@pytest.mark.parametrize("name", ["ft53", "berlin52"])
def test_artifact_loader_builds_the_problem_from_the_committed_artifact_only(name):
    plan = build_study_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=REPOSITORY_ROOT)
    dataset = next(d for d in plan.datasets if d.problem_name.lower() == name)
    problem = build_artifact_loader(plan, REPOSITORY_ROOT)(dataset.problem_name)
    assert problem.name == name and problem.dimension == dataset.manifest.dimension == len(problem.dist_matrix)
    assert problem.optimal == dataset.manifest.best_known.value
    from academic_benchmark.studies.smoke import _independent_cost
    n, cost = _independent_cost(dataset, REPOSITORY_ROOT)
    assert n == problem.dimension
    for i, j in ((0, 1), (1, 0), (2, 7), (7, 2), (n - 1, 0)):
        assert problem.dist_matrix[i][j] == cost(i, j)
    assert problem.problem_type == dataset.manifest.problem_type.lower()


def test_artifact_loader_refuses_a_dataset_without_a_known_value(tmp_path):
    root = _paper_repo(tmp_path)  # tiny10: best_known status "unknown"
    plan = build_study_plan(STUDY, repository_root=root)
    with pytest.raises(StudyRunError, match="best_known"):
        build_artifact_loader(plan, root)("tiny10")


# ------------------------------------------------------------------------------------------------------- CLI
def test_cli_refuses_a_real_draft_profile_with_exit_code_2_and_prints_the_reason(tmp_path, capsys):
    out = tmp_path / "out"
    code = main(["--study", "academic_benchmark/studies/bildiri2026/study.json", "--mode", "paper", "--out", str(out)])
    assert code == 2 and not out.exists()
    assert "status 'draft'" in capsys.readouterr().err


def test_smoke_replicate_cap_is_unchanged():
    assert SMOKE_MAX_REPLICATES == 3


# ------------------------------------------------------------------------------------------- review polish (D-03)
def test_paper_mode_refuses_output_inside_the_main_checkout_when_run_from_a_linked_worktree(tmp_path):
    main = _paper_repo(tmp_path)  # worktrees of this project live inside the main checkout
    linked = main / ".claude" / "worktrees" / "linked"
    _git(main, "worktree", "add", "-q", str(linked), "-b", "linked-branch")
    for target in (main / "results", main / ".claude" / "elsewhere", linked / "results"):
        with pytest.raises(StudyRunError, match="inside the repository"):
            _paper(linked, target, git_provider=CLEAN)
        assert not target.exists()


def test_paper_mode_still_accepts_an_output_outside_every_checkout_from_a_linked_worktree(tmp_path):
    main = _paper_repo(tmp_path)
    linked = tmp_path / "linked-outside"
    _git(main, "worktree", "add", "-q", str(linked), "-b", "linked-branch")
    report = _paper(linked, tmp_path / "out", git_provider=CLEAN)
    assert report.status == "passed", report.text


def test_a_partial_checkpoint_removal_can_never_be_resumed(tmp_path, monkeypatch):
    root = _paper_repo(tmp_path)
    out = tmp_path / "out"
    real_rmtree = shutil.rmtree

    def dying_rmtree(path, *args, **kwargs):
        if Path(path).name == "checkpoint":
            raise OSError("simulated crash while removing the progress folder")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(run_module.shutil, "rmtree", dying_rmtree)
    with pytest.raises(OSError, match="simulated crash"):
        _paper(root, out, git_provider=CLEAN)
    monkeypatch.undo()
    assert not (out / "checkpoint" / "campaign.json").exists()  # the marker goes first
    log: list = []
    with pytest.raises(StudyRunError, match="complete|nothing to resume"):
        _paper(root, out, resume=True, git_provider=CLEAN, gateway_executor=_gateway(log=log))
    assert log == []  # no recorded row, failed or not, ran again


def test_report_files_are_written_before_the_checkpoint_goes_and_the_index_does_not_list_them(paper_campaign):
    _root, out, _report = paper_campaign
    index = RunIndexV1.model_validate_json((out / "run_index.json").read_bytes())
    # the report quotes the index checksum, so the index cannot cover it (run_index.py: "never lists ... the report")
    assert not any(item.path.startswith("run_report") for item in index.outputs)
    assert json.loads((out / "run_report.json").read_text("utf-8"))["run_index"]["sha256"] == \
        __import__("hashlib").sha256((out / "run_index.json").read_bytes()).hexdigest()


def test_paper_mode_refuses_any_explicit_replicates_value(tmp_path, capsys):
    root = _paper_repo(tmp_path)
    for value in (1, SMOKE_MAX_REPLICATES):  # also the old default value 3
        with pytest.raises(StudyRunError, match="replicates"):
            _paper(root, tmp_path / "out", git_provider=CLEAN, replicates=value)
    assert not (tmp_path / "out").exists()
    code = main(["--study", "academic_benchmark/studies/bildiri2026/study.json", "--mode", "paper",
                 "--out", str(tmp_path / "cli-out"), "--replicates", "3"])
    assert code == 2 and "replicates" in capsys.readouterr().err
    assert _paper(root, tmp_path / "ok", git_provider=CLEAN).status == "passed"  # not giving it is fine
