"""Gate D, D-07: descriptive reports (smoke and paper); plan 2026-10-23 section 3, DECISION_LOG A18 (OQ-15, D-09 answers).

``academic_benchmark.analysis.report`` writes one descriptive table per comparison cell with exactly the column set of the
analysis plan (the seven OQ-15 statistics for each variable of the plan), the banner (mode, commit, dirty flag, profile status,
manifest index checksum) and, in paper mode only, the D-05 inferential section quoted from ``analyse_family``. Fixtures come
from the D-05 test module (synthetic rows with run manifests); the smoke integration uses the C-13 ``tiny10`` fixture of the
D-03 test module. No full profile is run.
"""
from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path

import pytest

import test_analysis_statistics as fx
import test_study_run_service as svc
import test_study_smoke_composite as comp
from academic_benchmark.analysis import report as report_module
from academic_benchmark.analysis import campaign_report as cr
from academic_benchmark.analysis.gaps import ExactReferenceTable
from academic_benchmark.exact_reference.reader import ExactReferenceRefused
from academic_benchmark.analysis.identity import ComparisonIdentityError
from academic_benchmark.analysis.manifests import ManifestError, load_verified_campaign, verify_campaign
from academic_benchmark.analysis.report import (
    ReportError,
    build_descriptive_table,
    build_report,
    write_report,
)
from academic_benchmark.analysis.statistics import analyse_family
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.studies.run import StudyRunError, run_study
from academic_benchmark.studies.service import load_study_with_plan
from academic_benchmark.studies.smoke import assert_no_ranking_words

SHA = "c" * 64
PLAN_COLUMNS = ["n", "median", "iqr", "min", "max", "mean", "sd"]
# statistics that are not in the OQ-15 set; none of them may appear in a descriptive report
FOREIGN_STATISTICS = (
    "variance", "stdev", "std ", "skew", "kurtosis", "percentile", "quartile", "geometric", "p-value",
    "confidence", "mad ", "cv ",
)


def _items(samples=None, problem="eil51", level=0, study_id="bildiri2026", dirty=False, **extra):
    """``samples`` = {algorithm: [gap, ...]}; consumed evaluations and termination reasons are set per row."""
    samples = samples or {"Core-GA-TSP": [1.0, 2.0, 3.0], "Core-PSO-TSP": [2.0, 4.0, 6.0], "Core-GWO-TSP-Pure": [3.0, 5.0, 10.0]}
    out = []
    for algorithm, values in samples.items():
        for replicate, gap in enumerate(values):
            budget = fx._levels(problem)[level]
            out.append(fx.make_item(
                problem, algorithm, replicate, gap, level=level, study_id=study_id, dirty=dirty,
                objective_evaluations=budget - replicate, termination_reason="budget_exhausted", **extra,
            ))
    return out


def _report(items, *, plan=None, mode="smoke", study=None, inference=(), notes=(), **index_options):
    return build_report(
        items, study=study or fx.study_for(items, plan), plan=plan, run_index=fx.index_for(items, mode, **index_options),
        index_sha256=SHA, inference=inference, notes=notes,
    )


def _load_plans():
    out = {}
    for name in ("bildiri2026", "yaem2026"):
        loaded = load_study_with_plan(f"academic_benchmark/studies/{name}/study.json", repository_root=fx.REPO, mode="smoke")
        out[name] = loaded.analysis_plan.plan
    return out


@pytest.fixture(scope="module")
def plans():
    return _load_plans()


@pytest.fixture(scope="module")
def draft(plans):
    return plans["bildiri2026"]


@pytest.fixture(scope="module")
def active(draft):
    return fx.activate(draft)


def _only_columns(plan, columns):
    spec = plan.descriptive.model_copy(update={"columns": list(columns)})
    return plan.model_copy(update={"descriptive": spec})


def _table(data, dataset="eil51"):
    return next(t for t in data["tables"] if t["cell"]["dataset_identity"] == dataset)


def _algorithm(table, algorithm):
    return next(a for a in table["algorithms"] if a["algorithm_id"] == algorithm)


# ------------------------------------------------------------------------------------------------ columns
def test_smoke_report_has_every_plan_column_for_every_variable_and_no_other_statistic(draft):
    report = _report(_items(), plan=draft)
    data = report.data
    assert data["mode"] == "smoke"
    spec = data["descriptive_spec"]
    assert spec["columns"] == PLAN_COLUMNS and spec["variables"] == list(draft.descriptive.variables)
    assert set(data["banner"]) >= {"mode", "commit", "dirty", "profile_status", "manifest_index_sha256"}
    table = _table(data)
    assert len(table["algorithms"]) == 3
    for algorithm in table["algorithms"]:
        assert list(algorithm["variables"]) == list(draft.descriptive.variables)
        for variable in draft.descriptive.variables:
            assert list(algorithm["variables"][variable]) == PLAN_COLUMNS  # exactly the plan's columns, in order
    for column in PLAN_COLUMNS:
        assert re.search(rf"(?<![\w-]){column}(?![\w-])", report.text), column
    lowered = report.text.lower()
    for word in FOREIGN_STATISTICS:
        assert word not in lowered, word
    assert_no_ranking_words(report.text)


def test_the_column_set_is_read_from_the_plan_not_from_the_code(draft):
    narrow = _only_columns(draft, ["n", "median"])
    report = _report(_items(), plan=narrow)
    for algorithm in _table(report.data)["algorithms"]:
        for variable in narrow.descriptive.variables:
            assert list(algorithm["variables"][variable]) == ["n", "median"]
    header_lines = [line for line in report.text.splitlines() if line.lstrip().startswith("algorithm")]
    assert header_lines
    for line in header_lines:
        assert "iqr" not in line and "mean" not in line and "sd" not in line.replace("-", " ").split()


def test_the_descriptive_values_follow_the_plan_conventions(draft):
    report = _report(_items(), plan=draft)
    gap = _algorithm(_table(report.data), "Core-GA-TSP")["variables"]["gap"]
    assert gap == {"n": 3, "median": 2.0, "iqr": 1.0, "min": 1.0, "max": 3.0, "mean": 2.0, "sd": 1.0}  # type 7 IQR, sample SD
    cost = _algorithm(_table(report.data), "Core-GA-TSP")["variables"]["cost"]
    assert cost["median"] == 502.0 and cost["min"] == 501.0
    budget = fx._levels("eil51")[0]
    evaluations = _algorithm(_table(report.data), "Core-GA-TSP")["variables"]["evaluations_consumed"]
    assert evaluations["max"] == budget and evaluations["min"] == budget - 2
    share = _algorithm(_table(report.data), "Core-GA-TSP")["variables"]["evaluation_budget_share"]
    assert math.isclose(share["max"], 1.0) and math.isclose(share["min"], (budget - 2) / budget)


def test_a_single_replicate_has_an_undefined_sample_sd_never_zero(draft):
    report = _report(_items({"Core-GA-TSP": [1.0], "Core-PSO-TSP": [2.0]}), plan=draft)
    gap = _algorithm(_table(report.data), "Core-GA-TSP")["variables"]["gap"]
    assert gap["n"] == 1 and gap["sd"] is None
    assert "undefined" in report.text


@pytest.mark.parametrize("study", ["bildiri2026", "yaem2026"])
def test_both_real_plans_give_a_report_with_their_own_columns_and_pass_the_wording_check(plans, study):
    plan = plans[study]
    items = _items(study_id=study)
    report = build_report(
        items, study=fx.study_for(items, plan), plan=plan, run_index=fx.index_for(items, "smoke", study_id=study), index_sha256=SHA,
    )
    assert report.data["descriptive_spec"]["columns"] == list(plan.descriptive.columns)
    assert report.data["banner"]["analysis_plan_id"] == plan.analysis_plan_id
    assert_no_ranking_words(report.text)


# ------------------------------------------------------------------------------------------------ banner
def test_the_banner_names_mode_commit_dirty_flag_profile_status_and_the_index_checksum(draft):
    report = _report(_items(), plan=draft)
    banner = report.data["banner"]
    assert banner["mode"] == "smoke" and banner["commit"] == fx.COMMIT and banner["dirty"] is False
    assert banner["profile_status"] == "draft" and banner["manifest_index_sha256"] == SHA
    assert banner["analysis_plan_id"] == draft.analysis_plan_id and banner["analysis_plan_status"] == "draft"
    head = report.text.split("\n\n", 1)[0]
    for needle in ("smoke", fx.COMMIT, "dirty: no", "draft", SHA):
        assert needle in head, needle


def test_a_dirty_smoke_campaign_is_flagged_in_the_banner(draft):
    report = _report(_items(dirty=True), plan=draft, dirty=True)
    assert report.data["banner"]["dirty"] is True
    assert "dirty: YES" in report.text


def test_the_banner_mode_comes_from_the_verified_run_index_and_the_index_checksum_is_required(draft):
    items = _items()
    with pytest.raises(ReportError, match="sha256"):
        build_report(items, study=fx.study_for(items, draft), plan=draft, run_index=fx.index_for(items, "smoke"), index_sha256="nope")
    paper = _report(_items(), plan=fx.activate(draft), mode="paper")
    assert paper.data["mode"] == "paper"


# ------------------------------------------------------------------------------------------------ one table = one cell
def test_a_table_refuses_rows_of_two_instances(draft):
    mixed = _items(problem="eil51") + _items(problem="berlin52")
    with pytest.raises(ReportError, match="comparison cell"):
        build_descriptive_table(mixed, draft)


def test_a_table_refuses_two_instances_even_when_their_budgets_are_equal(draft):
    assert fx._levels("kroA100") == fx._levels("rd100")  # same budget (the profile's own levels): only the instance identity tells them apart
    with pytest.raises(ReportError, match="comparison cell"):
        build_descriptive_table(_items(problem="kroA100") + _items(problem="rd100"), draft)


def test_a_table_refuses_rows_of_two_budget_levels(draft):
    mixed = _items(level=0) + _items(level=1)
    with pytest.raises(ReportError, match="comparison cell"):
        build_descriptive_table(mixed, draft)


def test_a_table_refuses_rows_of_two_studies(draft):
    mixed = _items(study_id="bildiri2026") + _items(study_id="yaem2026")
    with pytest.raises(ReportError, match="comparison cell"):
        build_descriptive_table(mixed, draft)


def test_a_table_refuses_a_row_without_a_manifest_and_an_exact_row(draft):
    items = _items()
    with pytest.raises(ReportError, match="manifest"):
        build_descriptive_table([(items[0][0], None)] + items[1:], draft)
    exact = {"record_kind": "exact_reference", "protocol_version": "uniride-exact-tsp-reference-v1", "problem": "eil51",
             "algorithm_id": "exact-reference", "replicate": 0}
    with pytest.raises(ReportError):
        build_descriptive_table(items + [(exact, items[0][1])], draft)


def test_a_report_with_two_cells_writes_one_table_per_cell_and_none_mixes_them(draft):
    report = _report(_items(problem="eil51") + _items(problem="berlin52") + _items(problem="eil51", level=1), plan=draft)
    cells = [(t["cell"]["dataset_identity"], t["cell"]["budget_level_index"]) for t in report.data["tables"]]
    assert sorted(cells) == [("berlin52", 0), ("eil51", 0), ("eil51", 1)]
    for table in report.data["tables"]:
        assert sum(a["variables"]["gap"]["n"] for a in table["algorithms"]) == 9


# ------------------------------------------------------------------------------------------------ plan guards
def test_a_plan_without_a_column_list_is_refused(draft):
    with pytest.raises(Exception):  # the contract itself needs a column list
        AnalysisPlanV1.model_validate({**draft.model_dump(mode="json"), "descriptive": {**draft.model_dump(mode="json")["descriptive"], "columns": []}})
    bare = _only_columns(draft, [])  # model_copy does not validate: the report must still refuse it
    with pytest.raises(ReportError, match="column"):
        _report(_items(), plan=bare)
    no_variables = draft.model_copy(update={"descriptive": draft.descriptive.model_copy(update={"variables": []})})
    with pytest.raises(ReportError, match="variable"):
        _report(_items(), plan=no_variables)


def test_a_plan_that_is_not_an_analysis_plan_is_refused():
    with pytest.raises(ReportError, match="AnalysisPlanV1"):
        _report(_items(), plan={"descriptive": {"columns": ["n"]}}, study=fx._BILDIRI)


def test_the_study_the_plan_and_the_index_must_belong_together(draft, plans):
    items = _items()
    with pytest.raises(ReportError, match="study"):
        build_report(items, study=fx.study_for(items, draft), plan=plans["yaem2026"], run_index=fx.index_for(items, "smoke"), index_sha256=SHA)
    with pytest.raises(ReportError, match="index"):
        build_report(items, study=fx.study_for(items, draft), plan=draft, run_index=fx.index_for(items, "smoke", study_id="yaem2026"), index_sha256=SHA)
    with pytest.raises(ReportError, match="index"):
        build_report(items, study=fx.study_for(items, draft), plan=draft, run_index=fx.index_for(items, "smoke", drop=(items[0][1].run_id,)), index_sha256=SHA)
    with pytest.raises(ReportError, match="digest"):
        build_report(items, study=fx.study_for(items, draft), plan=draft, run_index=fx.index_for(items, "smoke", digest_of="wrong"), index_sha256=SHA)


def test_a_row_without_the_gap_columns_is_refused(draft):
    items = _items()
    row = dict(items[0][0])
    del row["gap_to_exact_reference"]
    with pytest.raises(ReportError, match="gap"):
        _report([(row, items[0][1])] + items[1:], plan=draft)


# ------------------------------------------------------------------------------------------------ gap column
def test_a_negative_gap_is_flagged_visibly_and_never_printed_silently(draft):
    items = _items({"Core-GA-TSP": [1.0, -1.5, 3.0], "Core-PSO-TSP": [2.0, 4.0, 6.0]})
    report = _report(items, plan=draft)
    table = _table(report.data)
    flags = table["flags"]
    assert [f for f in flags if f["kind"] == "negative_gap"] == [
        {"kind": "negative_gap", "algorithm_id": "Core-GA-TSP", "replicate": 1, "gap": -1.5,
         "message": flags[0]["message"]}
    ]
    assert "NEGATIVE GAP" in report.text and "-1.5" in report.text
    assert "below the proven" in report.text
    assert _algorithm(table, "Core-GA-TSP")["variables"]["gap"]["min"] == -1.5  # reported, not clamped
    clean = _report(_items(), plan=draft)
    assert "NEGATIVE GAP" not in clean.text and not _table(clean.data)["flags"]


def test_a_row_without_an_exact_reference_shows_null_and_its_reason(draft):
    items = _items()
    reason = "no exact reference for instance 'eil51'"
    for row, _ in items[:3]:  # the three rows of the first algorithm
        row["gap_to_exact_reference"], row["gap_missing_reason"] = None, reason
    report = _report(items, plan=draft)
    ga = _algorithm(_table(report.data), "Core-GA-TSP")
    assert ga["variables"]["gap"] == {c: (0 if c == "n" else None) for c in PLAN_COLUMNS}
    assert ga["gap_missing"] == {"count": 3, "reasons": [reason]}
    assert "null" in report.text and reason in report.text
    assert _algorithm(_table(report.data), "Core-PSO-TSP")["gap_missing"] == {"count": 0, "reasons": []}


# ------------------------------------------------------------------------------------------------ counts
def test_termination_reason_counts_and_failed_run_counts_are_reported_per_algorithm(draft):
    items = _items()
    items[0][0]["termination_reason"] = "converged"
    items.append(fx.failed_item("eil51", "Core-GA-TSP", 5))
    report = _report(items, plan=draft)
    ga = _algorithm(_table(report.data), "Core-GA-TSP")
    assert ga["termination_reason_counts"] == {"budget_exhausted": 2, "converged": 1}
    assert ga["failed_run_count"] == 1
    assert _algorithm(_table(report.data), "Core-PSO-TSP")["failed_run_count"] == 0
    assert "failed run" in report.text.lower()


def test_a_cell_that_failed_completely_is_listed_and_not_dropped(draft):
    items = _items() + [fx.failed_item("berlin52", "Core-GA-TSP", 0, evaluation_budget=fx._levels("berlin52")[0])]
    report = _report(items, plan=draft)
    assert report.data["failed_only_cells"] == [
        {"algorithm_id": "Core-GA-TSP", "dataset_identity": "berlin52", "protocol": "fixed_budget", "evaluation_budget": fx._levels("berlin52")[0],
         "failed_run_count": 1}
    ]
    assert "berlin52" in report.text and "no completed run" in report.text


# ------------------------------------------------------------------------------------------------ paper section
def _paper_inference(active):
    items = fx.per_instance_items(fx.SEPARATED)
    for row, _ in items:  # a real row always carries what the run consumed and why it stopped
        row.setdefault("objective_evaluations", row["evaluation_budget"])
        row.setdefault("termination_reason", "budget_exhausted")
    analysis = analyse_family(items, study=fx.study_for(items, active), plan=active, family_id=fx.PER_INSTANCE,
                              run_index=fx.index_for(items, "paper"), index_sha256=SHA)  # SHA = the index the report is given
    return items, analysis


def test_the_inferential_section_is_absent_in_smoke_mode_and_cannot_be_forced_in(active):
    items, analysis = _paper_inference(active)
    smoke = _report(items, plan=active, mode="smoke")
    assert "nferential" not in smoke.text and smoke.data["inference"] == []
    with pytest.raises(ReportError, match="smoke"):
        _report(items, plan=active, mode="smoke", inference=[analysis])


def test_the_inferential_section_of_a_paper_report_is_the_d05_output_quoted_verbatim(active):
    items, analysis = _paper_inference(active)
    report = _report(items, plan=active, mode="paper", inference=[analysis])
    assert "Inferential results (D-05" in report.text
    assert analysis.text in report.text  # quoted, not recomputed
    section = report.data["inference"][0]
    assert section["family_id"] == fx.PER_INSTANCE and section["text"] == analysis.text
    assert section["omnibus"]["test"] == "kruskal_wallis"
    assert {p["method_used"] for p in section["pairs"]} <= {"asymptotic", "exact", "permutation"} and section["pairs"]
    assert section["exclusions"] == [] and section["inference_refused"] == []
    json.dumps(report.data)  # the whole report is JSON-serialisable


def test_a_paper_inference_of_another_plan_or_a_smoke_campaign_is_refused(active, draft):
    items, analysis = _paper_inference(active)
    smoke_analysis = analyse_family(items, study=fx.study_for(items, active), plan=active, family_id=fx.PER_INSTANCE,
                                    run_index=fx.index_for(items, "smoke"))
    with pytest.raises(ReportError, match="mode"):
        _report(items, plan=active, mode="paper", inference=[smoke_analysis])
    other = fx.activate(_load_plans()["yaem2026"])
    items2 = fx.per_instance_items(fx.SEPARATED, study_id="yaem2026")
    other_analysis = analyse_family(items2, study=fx.study_for(items2, other), plan=other, family_id=fx.PER_INSTANCE,
                                    run_index=fx.index_for(items2, "paper", study_id="yaem2026", plan_id=other.analysis_plan_id))
    with pytest.raises(ReportError, match="plan"):
        _report(items, plan=active, mode="paper", inference=[other_analysis])


def test_a_paper_report_refuses_a_dirty_campaign(active):
    items = _items(dirty=True)
    with pytest.raises(ReportError, match="dirty"):
        _report(items, plan=active, mode="paper", dirty=True)


def test_a_paper_report_refuses_a_run_index_that_records_a_dirty_tree_even_when_the_manifests_say_clean(active):
    with pytest.raises(ReportError, match="dirty"):
        _report(_items(), plan=active, mode="paper", dirty=True)  # clean manifests, dirty index


def test_report_py_computes_no_inferential_statistic_itself():
    source = Path(report_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(name.split(".")[0] in {"scipy", "statsmodels", "numpy"} for name in imported)
    for forbidden in ("multipletests", "mannwhitneyu", "friedmanchisquare", "kruskal(", "wilcoxon(", "norm.sf", "chi2"):
        assert forbidden not in source, forbidden


# ------------------------------------------------------------------------------------------------ writing
def test_write_report_writes_text_and_json_atomically_and_refuses_ranking_words(tmp_path, draft):
    report = _report(_items(), plan=draft)
    paths = write_report(report, tmp_path)
    assert sorted(p.name for p in paths) == ["descriptive_report.json", "descriptive_report.txt"]
    assert (tmp_path / "descriptive_report.txt").read_text("utf-8") == report.text
    assert json.loads((tmp_path / "descriptive_report.json").read_text("utf-8"))["banner"]["manifest_index_sha256"] == SHA
    assert not list(tmp_path.glob("*.tmp"))
    smoke_with_ranking = report_module.DescriptiveReport(text=report.text + "\nthe best algorithm wins", data=report.data, mode="smoke")
    with pytest.raises(Exception, match="ranking"):
        write_report(smoke_with_ranking, tmp_path / "other")
    assert not (tmp_path / "other").exists() or not list((tmp_path / "other").iterdir())


# ------------------------------------------------------------------------------------------------ smoke integration
def _smoke(tmp_path, *, reference=None, replicates=2):
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    kwargs = {} if reference is None else {"reference_table_provider": lambda _root: reference}
    run = run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(),
                    git_provider=svc.CLEAN, replicates=replicates, **kwargs)
    return run, out


def test_smoke_integration_writes_a_descriptive_report_that_verifies_with_the_campaign(tmp_path):
    run, out = _smoke(tmp_path, reference=ExactReferenceTable())
    assert run.status == "passed", run.text
    assert (out / "descriptive_report.txt").is_file() and (out / "descriptive_report.json").is_file()
    assert verify_campaign(out) == []  # the new files are known report files, not strays
    data = json.loads((out / "descriptive_report.json").read_text("utf-8"))
    plan_columns = json.loads((svc.REPOSITORY_ROOT / "academic_benchmark/studies/yaem2026/analysis_plan.json").read_text("utf-8"))["descriptive"]["columns"]
    assert data["descriptive_spec"]["columns"] == plan_columns
    index = out / "run_index.json"
    import hashlib
    assert data["banner"]["manifest_index_sha256"] == hashlib.sha256(index.read_bytes()).hexdigest()
    assert data["mode"] == "smoke" and data["banner"]["commit"] == svc.COMMIT
    assert_no_ranking_words((out / "descriptive_report.txt").read_text("utf-8"))
    assert "descriptive_report.txt" in run.files
    protocols = {t["cell"]["pooling_group"] for t in data["tables"]}
    assert protocols == {"fixed_budget", "native"}  # fixed and native cells are separate tables
    for table in data["tables"]:  # no exact reference for the fixture instance: null with the reason, never a value
        for algorithm in table["algorithms"]:
            assert algorithm["variables"]["gap"]["n"] == 0
            assert algorithm["gap_missing"]["reasons"] and "tiny10" in algorithm["gap_missing"]["reasons"][0]


def test_load_verified_campaign_refuses_a_campaign_that_does_not_verify(tmp_path):
    run, out = _smoke(tmp_path, reference=ExactReferenceTable())
    loaded = load_verified_campaign(out)
    assert len(loaded.items) == run.rows_completed and loaded.failed == []
    assert loaded.index_sha256 == __import__("hashlib").sha256((out / "run_index.json").read_bytes()).hexdigest()
    fixed = out / "fixed_runs.jsonl"
    fixed.write_bytes(fixed.read_bytes() + b" ")
    with pytest.raises(ManifestError, match="verif"):
        load_verified_campaign(out)


def test_smoke_integration_still_works_when_the_reference_cannot_be_loaded(tmp_path):
    def broken(_root):
        raise FileNotFoundError("reference unavailable in this test")  # only a missing reference is tolerated (round 2)

    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    run = run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(), git_provider=svc.CLEAN,
                    replicates=1, reference_table_provider=broken)
    assert run.status == "passed"
    data = json.loads((out / "descriptive_report.json").read_text("utf-8"))
    assert any("reference unavailable" in note for note in data["notes"])  # said, not hidden
    assert verify_campaign(out) == []


def test_smoke_integration_without_manifests_says_so_and_writes_no_descriptive_report(tmp_path):
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = tmp_path / "out"
    run = run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(), git_provider=svc.UNKNOWN,
                    replicates=1, reference_table_provider=lambda _r: ExactReferenceTable())
    assert not (out / "descriptive_report.txt").exists()
    assert "descriptive report not written" in run.text.lower()


# ------------------------------------------------------------------------------------------------ review polish (round 2)
def _sha(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _smoke_with(tmp_path, provider, *, out=None, replicates=1, overwrite=False, git=None, root=None):
    root = root or svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    out = out or tmp_path / "out"
    run = run_study(svc.STUDY, out, mode="smoke", repository_root=root, problem_loader=comp._loader(),
                    git_provider=git or svc.CLEAN, replicates=replicates, overwrite=overwrite, reference_table_provider=provider)
    return run, out, root


def _raises(exc):
    def provider(_root):
        raise exc

    return provider


def test_an_unavailable_reference_is_said_in_the_run_text_and_in_the_report(tmp_path):
    run, out, _ = _smoke_with(tmp_path, _raises(FileNotFoundError("no results index")))
    assert run.status == "passed"
    assert "unavailable" in run.text and "every gap is null" in run.text
    data = json.loads((out / "descriptive_report.json").read_text("utf-8"))
    assert any("unavailable" in note for note in data["notes"])


def test_an_integrity_refusal_of_the_reference_fails_the_smoke_loudly_and_writes_no_report(tmp_path):
    provider = _raises(ExactReferenceRefused("reference.csv: sha256 differs from the manifest outputs entry"))
    with pytest.raises(StudyRunError, match="descriptive report refused.*sha256 differs"):
        _smoke_with(tmp_path, provider)
    assert not (tmp_path / "out" / "descriptive_report.txt").exists()


def test_only_a_missing_reference_is_swallowed_other_provider_errors_propagate(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        _smoke_with(tmp_path, _raises(RuntimeError("boom")))


def test_the_default_reference_reader_reports_a_missing_index_as_unavailable(tmp_path):
    run, out, _ = _smoke_with(tmp_path, None)  # the default provider reads the repository's results_index.json: absent in the fixture
    assert run.status == "passed" and "unavailable" in run.text


def test_the_default_reference_reader_fails_on_a_corrupt_index_instead_of_nulling_the_gaps(tmp_path):
    root = svc._paper_repo(tmp_path, study_active=False, plan_status="draft")
    index = root / "academic_benchmark" / "exact_reference" / "results_index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("{not json", encoding="utf-8")
    with pytest.raises(StudyRunError, match="descriptive report refused"):
        _smoke_with(tmp_path, None, root=root)


def test_overwrite_removes_a_stale_descriptive_report_before_a_refused_run(tmp_path):
    run, out, root = _smoke_with(tmp_path, _raises(FileNotFoundError("none")))
    assert (out / "descriptive_report.txt").is_file() and (out / "descriptive_report.json").is_file()
    refused = _raises(ExactReferenceRefused("tampered"))
    with pytest.raises(StudyRunError):
        _smoke_with(tmp_path, refused, out=out, overwrite=True, root=root)
    assert not (out / "descriptive_report.txt").exists() and not (out / "descriptive_report.json").exists()


def test_the_manifest_presence_comes_from_the_smoke_report_not_from_a_stale_index_on_disk(tmp_path):
    first, out, root = _smoke_with(tmp_path, _raises(FileNotFoundError("none")))
    assert (out / "run_index.json").is_file()
    second, _, _ = _smoke_with(tmp_path, _raises(FileNotFoundError("none")), out=out, overwrite=True, root=root, git=svc.UNKNOWN)
    assert "descriptive report not written" in second.text.lower()
    assert not (out / "descriptive_report.txt").exists()  # the stale report of the first run is gone and none was rebuilt from the stale index


def test_the_smoke_report_carries_the_index_the_run_wrote(tmp_path):
    run, out, _ = _smoke_with(tmp_path, _raises(FileNotFoundError("none")))
    assert f"index sha256 {_sha(out / 'run_index.json')}" in run.text


def _head(root):
    import subprocess

    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, timeout=60).stdout.decode().strip()
    return {"revision": revision, "dirty": False}


def _campaign_dir(tmp_path):
    # a campaign that recorded the real HEAD of the fixture repository: the rebuild reads the analysis plan from git at that commit
    run, out, root = _smoke_with(tmp_path, _raises(FileNotFoundError("none")), git=_head)
    return run, out, root


def test_a_run_index_summary_that_differs_from_the_file_is_refused(tmp_path):
    _, out, root = _campaign_dir(tmp_path)
    loaded = load_study_with_plan(svc.STUDY, repository_root=root, mode="smoke")
    with pytest.raises(cr.CampaignReportError, match="sha256"):
        cr.write_smoke_descriptive_report(
            out, study=loaded.study, plan=loaded.analysis_plan.plan, plan_problem=None, root=root,
            run_index={"path": "run_index.json", "sha256": "0" * 64, "manifests": 1}, reference_table_provider=_raises(FileNotFoundError("x")),
        )


def test_a_plan_that_does_not_resolve_writes_no_report_and_says_why(tmp_path):
    _, out, root = _campaign_dir(tmp_path)
    for name in ("descriptive_report.txt", "descriptive_report.json"):
        (out / name).unlink()
    loaded = load_study_with_plan(svc.STUDY, repository_root=root, mode="smoke")
    lines = cr.write_smoke_descriptive_report(
        out, study=loaded.study, plan=None, plan_problem="analysis_plan.json is missing", root=root,
        run_index={"path": "run_index.json", "sha256": _sha(out / "run_index.json"), "manifests": 1},
    )
    assert len(lines) == 1 and "does not resolve" in lines[0] and "analysis_plan.json is missing" in lines[0]
    assert not (out / "descriptive_report.txt").exists()


# ---- rebuild from an existing campaign folder (a crash after the index)
def test_the_report_can_be_rebuilt_from_a_campaign_folder_and_equals_the_original(tmp_path):
    _, out, root = _campaign_dir(tmp_path)
    original = (out / "descriptive_report.txt").read_bytes(), (out / "descriptive_report.json").read_bytes()
    for name in ("descriptive_report.txt", "descriptive_report.json"):
        (out / name).unlink()
    lines = cr.rebuild_descriptive_report(out, svc.STUDY, repository_root=root, reference_table_provider=_raises(FileNotFoundError("none")))
    assert any("Descriptive report:" in line for line in lines)
    assert ((out / "descriptive_report.txt").read_bytes(), (out / "descriptive_report.json").read_bytes()) == original
    assert verify_campaign(out) == []


def test_the_rebuild_command_exit_codes_follow_the_run_service(tmp_path, capsys):
    _, out, root = _campaign_dir(tmp_path)
    for name in ("descriptive_report.txt", "descriptive_report.json"):
        (out / name).unlink()
    args = ["--study", svc.STUDY, "--repository-root", str(root)]
    assert cr.main([str(out), *args]) == 0
    assert (out / "descriptive_report.txt").is_file()
    assert cr.main([str(tmp_path / "nowhere"), *args]) == 2
    (out / "fixed_runs.jsonl").write_bytes((out / "fixed_runs.jsonl").read_bytes() + b" ")  # the campaign no longer verifies
    assert cr.main([str(out), *args]) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_the_rebuild_refuses_a_folder_inside_the_repository(tmp_path, capsys):
    import shutil

    _, out, root = _campaign_dir(tmp_path)
    inside = root / "copied_campaign"
    shutil.copytree(out, inside)
    assert cr.main([str(inside), "--study", svc.STUDY, "--repository-root", str(root)]) == 2
    assert "inside the repository" in capsys.readouterr().err
    assert (inside / "descriptive_report.txt").is_file()  # the copy keeps its old report: nothing was touched


# ------------------------------------------------------------------------------------------------ guards behind other guards
def test_the_evaluation_budget_check_is_a_guard_of_its_own(draft, monkeypatch):
    real = report_module.assert_single_comparison_family  # with the identity check silenced, the budget check must still refuse
    monkeypatch.setattr(report_module, "assert_single_comparison_family", lambda good, **kw: real(good[:1], **kw))
    with pytest.raises(ReportError, match="different evaluation budgets"):
        build_descriptive_table(_items(level=0) + _items(level=1), draft)


def test_the_wording_check_runs_when_the_report_is_built_also_in_paper_mode(active):
    with pytest.raises(ReportError, match="ranking"):
        _report(_items(), plan=active, mode="paper", notes=["the best algorithm wins"])
    with pytest.raises(ReportError, match="ranking"):
        _report(_items(), plan=active, mode="smoke", notes=["the best algorithm wins"])


def test_a_manifest_written_at_another_commit_than_the_run_index_is_refused(draft):
    items = _items()
    index = fx.index_for(items, "smoke")
    index = index.model_copy(update={"git": index.git.model_copy(update={"commit": "b" * 40})})
    with pytest.raises(ReportError, match="commit"):
        build_report(items, study=fx.study_for(items, draft), plan=draft, run_index=index, index_sha256=SHA)


def test_a_failed_run_of_another_cell_is_refused_by_the_table(draft):
    other = fx.failed_item("berlin52", "Core-GA-TSP", 0, evaluation_budget=fx._levels("berlin52")[0])
    with pytest.raises(ReportError, match="another comparison cell"):
        build_descriptive_table(_items() + [other], draft)
    wrong_budget = fx.failed_item("eil51", "Core-GA-TSP", 0, evaluation_budget=fx._levels("eil51")[1])
    with pytest.raises(ReportError, match="another comparison cell"):
        build_descriptive_table(_items() + [wrong_budget], draft)


def test_a_historical_unverified_row_is_never_reported(draft):
    with pytest.raises(ReportError, match="historical"):
        _report(_items(evidence="historical_unverified"), plan=draft)
    with pytest.raises(ReportError, match="historical"):
        build_descriptive_table(_items(evidence="invalid"), draft)


def test_one_table_refuses_a_fixed_budget_and_a_native_row(draft):
    native_row, native_manifest = fx.make_item(
        "eil51", "Core-GA-TSP", 9, 1.0, objective_evaluations=5, termination_reason="converged",
        protocol_version="uniride-native-tsp-v1", comparison_regime="algorithm_native_termination", evaluation_budget=None,
    )
    with pytest.raises(ReportError, match="pooling groups"):
        build_descriptive_table(_items() + [(native_row, native_manifest)], draft)


def test_one_table_refuses_a_backend_policy_mix(draft):
    items = _items({"Core-GA-TSP": [1.0, 2.0], "Core-PSO-TSP": [2.0, 4.0]})
    row, manifest = items[0]
    python_only = manifest.model_copy(update={"algorithm": manifest.algorithm.model_copy(update={"backend_policy": "python_only"})})
    with pytest.raises(ReportError, match="backend_policy"):
        build_descriptive_table([(row, python_only), *items[1:]], draft)


def test_a_refused_rebuild_leaves_no_old_report_next_to_the_campaign(tmp_path):
    _, out, root = _campaign_dir(tmp_path)
    assert (out / "descriptive_report.txt").is_file()
    (out / "fixed_runs.jsonl").write_bytes((out / "fixed_runs.jsonl").read_bytes() + b" ")
    assert cr.main([str(out), "--study", svc.STUDY, "--repository-root", str(root)]) == 2
    assert not (out / "descriptive_report.txt").exists() and not (out / "descriptive_report.json").exists()


# ------------------------------------------------------------------------------------------------ D-07: banner shows plan hash and planned runs
def test_the_banner_shows_the_analysis_plan_hash_and_the_planned_run_count(draft):
    items = _items()  # 3 algorithms x 3 replicates
    report = _report(items, plan=draft)
    banner = report.data["banner"]
    assert banner["analysis_plan_sha256"] == fx.PLAN_SHA
    assert banner["planned_runs"] == 9 and banner["planned_runs_per_cell"] == 3
    assert banner["completed_runs"] == 9 and banner["failed_runs"] == 0
    assert f"Analysis plan sha256: {fx.PLAN_SHA}" in report.text
    assert "Planned runs: 9 (3 per cell); completed 9; failed 0" in report.text


def test_the_banner_says_so_when_the_plan_file_hash_was_not_recorded(draft):
    report = _report(_items(), plan=draft, plan_sha="absent")
    assert report.data["banner"]["analysis_plan_sha256"] is None
    assert "Analysis plan sha256: not recorded (the analysis plan did not resolve)" in report.text


def test_the_banner_counts_failed_runs_from_the_index(draft):
    items = _items() + [fx.failed_item("eil51", "Core-PSO-TSP", 9)]
    report = _report(items, plan=draft)
    assert report.data["banner"]["failed_runs"] == 1
    assert "Planned runs: 10 (10 per cell); completed 9; failed 1" in report.text
