"""The gated paper report command (DECISION_LOG A20 L12 and L7; Gate D close).

``python -m academic_benchmark.analysis.campaign_report <campaign dir> --paper`` builds ``paper_report.txt`` and
``paper_report.json`` from a finished, verified paper campaign: the descriptive tables plus the D-05 inferential section of every
comparison family the analysis plan declares, each family analysed with the run-index sha256 and the campaign commit. The paper run
service prints the exact command when a paper campaign ends and runs no analysis itself.

The campaign is the synthetic ``tiny10`` fixture of ``test_study_run_service`` (one instance, two algorithms, two budget levels and the
native protocol, two replicates per cell) run in paper mode in a temporary git repository. Its analysis plan is the fixture's active
plan with ``minimum_n_per_cell`` lowered from 5 to 2 (the fixture runs two replicates), so that inference is not refused for a small
sample; the real plans are still draft with ``minimum_n_per_cell`` unresolved and no real paper campaign exists. The exact reference
is a synthetic table (one value for ``tiny10``), not a proven optimum.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import shlex
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_analysis_statistics as stats_fx
import test_campaign_rebuild as rebuild
import test_study_run_service as svc
from academic_benchmark.analysis import campaign_report as cr
from academic_benchmark.analysis.gaps import ExactReferenceTable, ExactReferenceValue
from academic_benchmark.analysis.manifests import verify_campaign
from academic_benchmark.analysis.statistics import StatisticsRefusal, analyse_family

PAPER_FILES = ("paper_report.txt", "paper_report.json")


def _reference_table() -> ExactReferenceTable:
    value = ExactReferenceValue(
        instance_id="tiny10", value=1, published_optimum=1, problem_contract="TSP", solver_name="synthetic", solver_version="0",
        results_dir="synthetic", manifest_sha256="0" * 64, ub_validated=True,
    )
    return ExactReferenceTable(values={"tiny10": value})


def _provider(_root):
    return _reference_table()


def _paper_campaign(tmp_path: Path, *, minimum_n: int = 2, gateway=None, tsplib_ids: bool = False):
    """A finished paper campaign of the fixture in a real git repository (HEAD is the commit the index records).

    ``tsplib_ids=True`` names the fixture dataset ``tsplib-tiny10`` (the form of every real dataset id and of the ids the analysis plans
    declare) instead of ``tiny10``; failed runs are only analysed under that form."""
    root = svc._paper_repo(tmp_path)
    plan_file = root / "studies" / "analysis_plan.json"
    plan = json.loads(plan_file.read_text("utf-8"))
    plan["minimum_n_per_cell"] = minimum_n
    if tsplib_ids:
        plan["families"][0]["dataset_ids"] = ["tsplib-tiny10"]
        dataset_file = root / "datasets" / "tiny10.json"
        dataset = json.loads(dataset_file.read_text("utf-8"))
        dataset["dataset_id"] = "tsplib-tiny10"
        dataset_file.write_text(json.dumps(dataset), encoding="utf-8")
        study_file = root / svc.STUDY
        study = json.loads(study_file.read_text("utf-8"))
        levels = study["scaled_fixed_budget_levels"]["levels_by_dataset"]
        levels["tsplib-tiny10"] = levels.pop("tiny10")
        study_file.write_text(json.dumps(study), encoding="utf-8")
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    svc._git(root, "add", "-A")
    svc._git(root, "commit", "-q", "-m", "fixture plan with a small minimum")
    out = tmp_path / "out"
    kwargs = {} if gateway is None else {"gateway_executor": gateway}
    report = svc._paper(root, out, git_provider=rebuild._head, **kwargs)
    return root, out, report


def _paper_args(root: Path) -> list:
    return ["--paper", "--repository-root", str(root)]


@pytest.fixture
def default_reference(monkeypatch):
    """The command reads the reference table of the repository; the tests give it the synthetic table."""
    monkeypatch.setattr(cr, "default_reference_table", _provider)


# ------------------------------------------------------------------------------------------------ the report
def test_a_verified_paper_campaign_gets_a_paper_report_with_the_inferential_section_and_the_campaign_identity(tmp_path, default_reference, capsys):
    root, out, run = _paper_campaign(tmp_path)
    assert run.status == "passed", run.text
    assert cr.main([str(out), *_paper_args(root)]) == 0
    assert all((out / name).is_file() for name in PAPER_FILES)
    assert verify_campaign(out) == []  # the paper report files are known report files, not strays
    index_sha = hashlib.sha256((out / "run_index.json").read_bytes()).hexdigest()
    head = rebuild._head(root)["revision"]
    text = (out / "paper_report.txt").read_text("utf-8")
    data = json.loads((out / "paper_report.json").read_text("utf-8"))
    assert "Inferential results (D-05" in text and "Mode: paper" in text and index_sha in text
    assert data["schema_version"] == "uniride-paper-report/v1" and text.splitlines()[0] == "UniRide paper report"  # A20 L13
    assert data["mode"] == "paper" and data["banner"]["manifest_index_sha256"] == index_sha and data["banner"]["commit"] == head
    sections = data["inference"]
    # one analysis per comparison cell of the plan's one family: two fixed-budget levels and the native protocol, never pooled
    cells = sorted((s["comparison_cell"]["pooling_group"], s["comparison_cell"]["budget_level_index"]) for s in sections)
    assert cells == [("fixed_budget", 0), ("fixed_budget", 1), ("native", None)]
    for section in sections:
        assert section["family_id"] == "per-instance-independent" and section["campaign_mode"] == "paper"
        assert section["index_sha256"] == index_sha and section["campaign_commit"] == head
        assert section["analysis_plan_id"] == "fixture-plan-v1" and section["plan_status"] == "active"
        assert section["omnibus"] is not None and section["inference_refused"] == []  # 2 replicates meet the lowered minimum of 2
        assert section["comparison_cell"]["dataset_identity"] == "tiny10"
    # the descriptive tables are the same ones the smoke rebuild writes
    assert {t["cell"]["pooling_group"] for t in data["tables"]} == {"fixed_budget", "native"}
    stdout = capsys.readouterr().out
    assert "paper_report.txt" in stdout


def test_the_paper_report_is_rebuilt_identically_from_the_same_campaign(tmp_path, default_reference):
    root, out, _run = _paper_campaign(tmp_path)
    assert cr.main([str(out), *_paper_args(root)]) == 0
    first = [(out / name).read_bytes() for name in PAPER_FILES]
    assert cr.main([str(out), *_paper_args(root)]) == 0
    assert [(out / name).read_bytes() for name in PAPER_FILES] == first


def test_the_paper_command_leaves_the_descriptive_rebuild_alone(tmp_path, default_reference):
    root, out, _run = _paper_campaign(tmp_path)
    assert cr.main([str(out), "--repository-root", str(root)]) == 0  # no --paper: the descriptive report, as before
    assert (out / "descriptive_report.txt").is_file() and not any((out / name).exists() for name in PAPER_FILES)
    assert "Inferential results" not in (out / "descriptive_report.txt").read_text("utf-8")


# ------------------------------------------------------------------------------------------------ refusals (exit 2)
def test_a_smoke_campaign_is_refused_with_exit_2_and_no_paper_report(tmp_path, capsys):
    _report, out, root = rebuild._campaign(tmp_path)  # a smoke campaign of the draft fixture
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "smoke" in err and "paper campaign" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_an_interrupted_campaign_is_refused_with_exit_2(tmp_path, capsys):
    with pytest.raises(svc._Killed):
        _paper_campaign(tmp_path, gateway=svc._gateway(kill_after=3))
    out = tmp_path / "out"
    assert not (out / "run_index.json").exists()  # nothing was finalised
    assert cr.main([str(out), *_paper_args(tmp_path / "repo")]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "does not verify" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_a_truncated_campaign_is_refused_with_exit_2(tmp_path, default_reference, capsys):
    root, out, _run = _paper_campaign(tmp_path)
    fixed = out / "fixed_runs.jsonl"
    lines = fixed.read_text("utf-8").splitlines()
    fixed.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")  # a row missing: checksum and index no longer agree
    assert cr.main([str(out), *_paper_args(root)]) == 2
    assert "does not verify" in capsys.readouterr().err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_a_tampered_run_index_is_refused_with_exit_2(tmp_path, default_reference, capsys):
    root, out, _run = _paper_campaign(tmp_path)
    index = out / "run_index.json"
    payload = json.loads(index.read_text("utf-8"))
    payload["environment"]["statistics_library"] = "edited"
    index.write_text(json.dumps(payload), encoding="utf-8")  # the sidecar checksum no longer matches
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "does not verify" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_a_campaign_that_ran_with_an_uncommitted_plan_is_refused_with_exit_2(tmp_path, default_reference, capsys):
    """The run hashed a working-tree plan that git does not hold at the campaign commit: the plan the campaign ran with cannot be
    read back, so the paper report is refused (the rebuild reads the plan at the commit and compares the hash)."""
    root = svc._paper_repo(tmp_path)
    plan_file = root / "studies" / "analysis_plan.json"
    plan = json.loads(plan_file.read_text("utf-8"))
    plan["minimum_n_per_cell"] = 2
    plan_file.write_text(json.dumps(plan), encoding="utf-8")  # edited after the last commit, never committed
    out = tmp_path / "out"
    assert svc._paper(root, out, git_provider=rebuild._head).status == "passed"
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "analysis plan differs" in err and "paper report needs the plan the campaign ran with" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_a_plan_committed_after_the_campaign_does_not_change_the_paper_report(tmp_path, default_reference):
    root, out, _run = _paper_campaign(tmp_path)
    assert cr.main([str(out), *_paper_args(root)]) == 0
    first = json.loads((out / "paper_report.json").read_text("utf-8"))
    plan_file = root / "studies" / "analysis_plan.json"
    plan = json.loads(plan_file.read_text("utf-8"))
    plan["alpha"] = 0.01
    plan["minimum_n_per_cell"] = 99
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    svc._git(root, "add", "-A")
    svc._git(root, "commit", "-q", "-m", "change the plan after the campaign")
    assert cr.main([str(out), *_paper_args(root)]) == 0  # the plan of the campaign commit is the one that counts
    second = json.loads((out / "paper_report.json").read_text("utf-8"))
    # only the verifier's note differs: with HEAD moved on it says the recorded hashes were not compared with the working tree
    assert first.pop("notes") != second.pop("notes")
    assert second == first  # same analysis plan (alpha 0.05, minimum 2), same inferential results


def test_a_statistics_refusal_is_exit_2_with_the_reason_and_leaves_no_old_paper_report(tmp_path, monkeypatch, capsys):
    root, out, _run = _paper_campaign(tmp_path)
    monkeypatch.setattr(cr, "default_reference_table", _provider)
    assert cr.main([str(out), *_paper_args(root)]) == 0
    assert all((out / name).is_file() for name in PAPER_FILES)

    def unavailable(_root):
        raise FileNotFoundError("no reference in this test")

    monkeypatch.setattr(cr, "default_reference_table", unavailable)  # null gaps: the statistics service has no response variable
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "no gap to the exact reference" in err
    assert not any((out / name).exists() for name in PAPER_FILES)  # the stale report of the first run is gone


def test_a_campaign_folder_inside_the_repository_is_refused_for_the_paper_report_too(tmp_path, default_reference, capsys):
    root, out, _run = _paper_campaign(tmp_path)
    inside = root / "results-copy"
    import shutil

    assert cr.main([str(out), *_paper_args(root)]) == 0
    shutil.copytree(out, inside)  # a folder with a paper report of an earlier run
    before = {name: (inside / name).read_bytes() for name in PAPER_FILES}
    assert cr.main([str(inside), *_paper_args(root)]) == 2
    assert "inside the repository" in capsys.readouterr().err
    # the refusal touches nothing inside the repository: the existing paper report is still there, byte for byte
    assert {name: (inside / name).read_bytes() for name in PAPER_FILES} == before


def test_a_smoke_overwrite_removes_a_paper_report_of_an_earlier_run(tmp_path):
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    options = dict(repository_root=root, problem_loader=rebuild.comp._loader(), git_provider=rebuild._head, replicates=1,
                   reference_table_provider=rebuild.tar._raises(FileNotFoundError("none")))
    svc.run_study(svc.STUDY, out, mode="smoke", **options)
    for name in PAPER_FILES:
        (out / name).write_text("stale", encoding="utf-8")
    svc.run_study(svc.STUDY, out, mode="smoke", overwrite=True, **options)
    assert not any((out / name).exists() for name in PAPER_FILES)


# ------------------------------------------------------------------------------------------------ the guards in front of the analysis
def test_a_dirty_run_index_is_refused_before_any_analysis(tmp_path, default_reference, monkeypatch, capsys):
    import dataclasses

    root, out, _run = _paper_campaign(tmp_path)
    real = cr.load_verified_campaign

    def dirty(directory, **kwargs):  # the run service never writes a dirty paper index; model one that does
        campaign = real(directory, **kwargs)
        git = campaign.index.git.model_copy(update={"dirty": True})
        return dataclasses.replace(campaign, index=campaign.index.model_copy(update={"git": git}))

    monkeypatch.setattr(cr, "load_verified_campaign", dirty)
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "dirty working tree" in err and "statistics service" not in err  # refused by the command's own guard
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_a_profile_that_is_not_active_is_refused(tmp_path, default_reference, monkeypatch, capsys):
    import academic_benchmark.studies.service as service

    root, out, _run = _paper_campaign(tmp_path)
    real = service.load_study_bytes
    monkeypatch.setattr(service, "load_study_bytes", lambda *a, **k: real(*a, **k).model_copy(update={"status": "draft"}))
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "needs an active profile" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


def test_an_analysis_plan_that_is_not_active_is_refused(tmp_path, default_reference, monkeypatch, capsys):
    import academic_benchmark.studies.service as service

    root, out, _run = _paper_campaign(tmp_path)
    real = service.resolve_analysis_plan_bytes

    def draft_plan(study, plan_name, plan_bytes, **kwargs):  # the same plan bytes, but the plan the resolver sees says draft
        payload = json.loads(plan_bytes)
        payload["status"] = "draft"
        return real(study, plan_name, json.dumps(payload).encode("utf-8"), **kwargs)

    monkeypatch.setattr(service, "resolve_analysis_plan_bytes", draft_plan)
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "needs an active plan" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


# ------------------------------------------------------------------------------------------------ a failed campaign (exit 1)
def _fail_one(kwargs):
    return kwargs["requested_algorithm_id"] == svc.ALGS[0] and kwargs["run_idx"] == 1 and kwargs["evaluation_budget"] == svc.LEVELS[0]


def test_a_paper_campaign_with_failed_runs_gets_its_report_with_exit_1_and_names_the_excluded_cell(tmp_path, default_reference):
    root, out, run = _paper_campaign(tmp_path, gateway=svc._gateway(fail=_fail_one), tsplib_ids=True)
    assert run.status == "failed" and run.rows_failed >= 1
    assert cr.main([str(out), *_paper_args(root)]) == 1
    data = json.loads((out / "paper_report.json").read_text("utf-8"))
    assert data["banner"]["failed_runs"] == run.rows_failed
    assert verify_campaign(out) == []
    excluded = [
        (s["comparison_cell"]["budget_level_index"], e["algorithm_id"], e["failed_runs"])
        for s in data["inference"] for e in s["exclusions"] if e["dataset_identity"] is not None
    ]
    assert excluded == [(0, svc.ALGS[0], 1)]  # the failed cell reached the statistics service and is named as an exclusion
    assert "excluded from inference" in (out / "paper_report.txt").read_text("utf-8")


def test_a_failed_run_with_a_dataset_id_that_is_not_in_the_tsplib_form_is_refused_with_exit_2(tmp_path, default_reference, capsys):
    root, out, run = _paper_campaign(tmp_path, gateway=svc._gateway(fail=_fail_one))  # the fixture's dataset id is "tiny10"
    assert run.status == "failed"
    assert cr.main([str(out), *_paper_args(root)]) == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err and "dataset id 'tiny10'" in err and "tsplib-" in err
    assert not any((out / name).exists() for name in PAPER_FILES)


# ------------------------------------------------------------------------------------------------ _paper_analyses with the Bildiri-shaped fixtures
draft_plans, draft, active = stats_fx.draft_plans, stats_fx.draft, stats_fx.active  # the module fixtures of the statistics tests


def _stub(items):
    """What ``_paper_analyses`` reads of a verified campaign: its run index and the sha256 of ``run_index.json``."""
    return SimpleNamespace(index=stats_fx.index_for(items, "paper"), index_sha256=stats_fx.INDEX_SHA256)


def _analyses(items, plan):
    return cr._paper_analyses(items, study=stats_fx.study_for(items, plan), plan=plan, campaign=_stub(items))


def test_a_cross_instance_family_is_analysed_once_per_protocol_and_level_and_the_per_instance_family_once_per_instance(active):
    items = []
    for level in (0, 1):  # two budget levels of the same six instances and three algorithms
        for i, problem in enumerate(stats_fx.CROSS_INSTANCES):
            for a, algorithm in enumerate(stats_fx.ALGORITHMS):
                for r, offset in enumerate((-0.1, 0.0, 0.1)):
                    items.append(stats_fx.make_item(problem, algorithm, r, float(i + a) + offset, level=level))
    analyses, cells, notes = _analyses(items, active)
    across = [(a, c) for a, c in zip(analyses, cells) if a.family_id == stats_fx.ACROSS]
    per_instance = [(a, c) for a, c in zip(analyses, cells) if a.family_id == stats_fx.PER_INSTANCE]
    assert [c["budget_level_index"] for _, c in across] == [0, 1]  # one analysis per level, never one per instance
    assert all(c["pooling_group"] == "fixed_budget" and c["dataset_identity"] is None for _, c in across)
    for analysis, _cell in across:
        assert analysis.inference is not None and analysis.inference.omnibus.test == "friedman"
        assert {cell.dataset_identity for cell in analysis.cells} == {"berlin52", "eil51", "st70", "kroa100", "rd100", "eil76"}
    assert len(per_instance) == 12  # six instances at two levels
    assert {c["dataset_identity"] for _, c in per_instance} == {"berlin52", "eil51", "st70", "kroa100", "rd100", "eil76"}
    assert all(a.inference.omnibus.test == "kruskal_wallis" for a, _ in per_instance)
    assert len(analyses) == len(cells) == 14 and notes == []


def test_a_failed_cell_reaches_the_statistics_service_and_is_excluded_not_counted_as_a_small_sample(active):
    samples = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [6, 7, 8, 9], "Core-GWO-TSP-Pure": [11, 12, 13, 14, 15]}
    items = stats_fx.per_instance_items(samples)
    items.append(stats_fx.failed_item("eil51", "Core-PSO-TSP", 4))  # PSO's fifth replicate failed
    analyses, cells, notes = _analyses(items, active)
    per_instance = [a for a in analyses if a.family_id == stats_fx.PER_INSTANCE]
    assert len(per_instance) == 1
    analysis = per_instance[0]
    assert [(e["algorithm_id"], e["dataset_identity"], e["failed_runs"]) for e in analysis.exclusions] == [("Core-PSO-TSP", "eil51", 1)]
    assert "excluded from inference" in analysis.text
    assert analysis.inference_refused == ()  # not "insufficient sample": GA and GWO are compared, PSO's cell is excluded
    assert analysis.inference is not None
    assert {cell.algorithm_id for cell in analysis.cells} == {"Core-GA-TSP", "Core-GWO-TSP-Pure"}
    assert notes == []


def test_a_failed_run_whose_dataset_id_is_not_a_tsplib_id_is_refused_by_name(active):
    items = stats_fx.per_instance_items(stats_fx.SEPARATED)
    row, manifest = stats_fx.failed_item("eil51", "Core-PSO-TSP", 9, dataset_id="tiny10")
    with pytest.raises(cr.CampaignReportError, match="dataset id 'tiny10'.*tsplib-"):
        _analyses([*items, (row, manifest)], active)


# ------------------------------------------------------------------------------------------------ the run service prints the command
def test_the_run_service_prints_the_exact_command_that_builds_the_paper_report_and_runs_no_analysis(tmp_path):
    _root, out, run = _paper_campaign(tmp_path)
    command = f"python -m academic_benchmark.analysis.campaign_report {out} --paper"
    assert command in run.text.splitlines()
    assert command in (out / "run_report.txt").read_text("utf-8").splitlines()  # the saved run report says the same
    assert not any((out / name).exists() for name in PAPER_FILES)  # nothing was analysed by the run itself
    argv = shlex.split(command, posix=False)
    assert argv[:3] == ["python", "-m", "academic_benchmark.analysis.campaign_report"] and argv[3:] == [str(out), "--paper"]


def test_a_campaign_with_failed_runs_prints_the_command_too_and_says_the_failed_cells_are_excluded_and_the_exit_is_1(tmp_path):
    _root, out, run = _paper_campaign(tmp_path, gateway=svc._gateway(fail=lambda k: k["run_idx"] == 1))
    assert run.status == "failed"
    command = f"python -m academic_benchmark.analysis.campaign_report {out} --paper"
    lines = run.text.splitlines()
    assert command in lines and command in (out / "run_report.txt").read_text("utf-8").splitlines()
    assert any(
        "failed" in line and "excluded" in line and "exits 1 when the report is written (2 if it is refused)" in line for line in lines
    )
    assert not any("exits 1 (not 0)" in line for line in lines)
    assert not any((out / name).exists() for name in PAPER_FILES)  # still no analysis in the run itself


# ------------------------------------------------------------------------------------------------ A20 L7
def test_analyse_family_requires_the_index_sha256_keyword():
    parameter = inspect.signature(analyse_family).parameters["index_sha256"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY and parameter.default is inspect.Parameter.empty
    items = stats_fx.per_instance_items(stats_fx.SEPARATED)
    with pytest.raises(TypeError, match="index_sha256"):
        analyse_family(  # noqa: the call is the test: no index_sha256
            items, study=stats_fx.study_for(items), plan=None, family_id=stats_fx.PER_INSTANCE, run_index=stats_fx.index_for(items, "paper"),
        )


@pytest.mark.parametrize("value", [None, "", "e" * 63, "e" * 65, "E" * 64, "g" * 64, 5, b"e" * 64])
def test_analyse_family_refuses_an_index_sha256_that_is_not_64_lower_case_hex(active, value):
    items = stats_fx.per_instance_items(stats_fx.SEPARATED)
    with pytest.raises(StatisticsRefusal, match="index_sha256"):
        analyse_family(
            items, study=stats_fx.study_for(items, active), plan=active, family_id=stats_fx.PER_INSTANCE,
            run_index=stats_fx.index_for(items, "paper"), index_sha256=value,
        )
