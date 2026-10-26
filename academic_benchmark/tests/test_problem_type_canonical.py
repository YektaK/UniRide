"""A20 L10: the analysis layer compares problem types as canonical ``ProblemContract`` values, never as raw strings.

The run service stores the lowercase problem type in every row (``studies/run.py`` ``problem_type="tsp"``); the exact-reference
records and the dataset manifests carry the uppercase contract. The first test runs a real smoke study through the run service
with the committed exact-reference table and requires the descriptive report; before the fix it ended in
``descriptive report refused: berlin52: row problem type 'tsp' differs from the exact reference contract 'TSP'`` because no
test combined the run service rows with the real reference data.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from academic_benchmark.analysis.campaign_report import default_reference_table
from academic_benchmark.analysis.problem_contract import ProblemContractError, canonical_problem_contract
from academic_benchmark.studies.run import run_study
from uniride_core.algorithms.capabilities import ProblemContract

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROFILES = ("bildiri2026", "yaem2026")
TSP_DATASET = "academic_benchmark/datasets/eil51.json"
TSP_ARTIFACT = "academic_benchmark/tsplib_data/tsp/eil51.tsp"
CLEAN = lambda _root: {"revision": "c" * 40, "dirty": False}  # noqa: E731


# ------------------------------------------------------------------------------------------------- the helper
@pytest.mark.parametrize("value", ["tsp", "TSP", "Tsp", ProblemContract.TSP])
def test_tsp_spellings_map_to_one_contract(value):
    assert canonical_problem_contract(value) is ProblemContract.TSP


@pytest.mark.parametrize("value", ["atsp", "ATSP", "Atsp", ProblemContract.ATSP])
def test_atsp_spellings_map_to_one_contract(value):
    assert canonical_problem_contract(value) is ProblemContract.ATSP


@pytest.mark.parametrize("value", ["", "cvrp", "uniride_wave", "tsp2", None, 3, b"tsp", " tsp ", "tsp\n", "\tATSP", "atsp "])  # case mapping only: no trimming (A20 L10)
def test_unknown_problem_types_are_refused(value):
    with pytest.raises(ProblemContractError):
        canonical_problem_contract(value)


# ------------------------------------------------------------------------------------------- the comparison sites
def test_gap_columns_accept_a_lowercase_row_and_refuse_a_wrong_contract():
    from academic_benchmark.analysis.gaps import GapColumnError, add_gap_columns

    table = default_reference_table(REPOSITORY_ROOT)
    plan = _plan()
    base = {
        "record_kind": "primary", "protocol_version": "uniride-fair-tsp-v2", "comparison_regime": "fixed_evaluation_budget",
        "problem": "eil51", "algorithm_id": "Core-GA-TSP", "replicate": 0, "seed": 7, "evaluation_budget": 63750,
        "objective_cost": 430.0, "validation_status": "passed",
    }
    # the row format keeps the lowercase spelling; the reference says TSP
    for spelling in ("tsp", "TSP"):
        out = add_gap_columns([{**base, "problem_type": spelling}], table, plan=plan)
        assert out[0]["exact_reference_value"] == 426
    with pytest.raises(GapColumnError, match="problem type"):
        add_gap_columns([{**base, "problem_type": "atsp"}], table, plan=plan)
    with pytest.raises(GapColumnError, match="problem type"):
        add_gap_columns([{**base, "problem_type": "cvrp"}], table, plan=plan)


def _with_problem_type(items, spelling):
    """The same items with the dataset problem type of every manifest set to ``spelling`` (no validation: a test of the comparison)."""
    out = []
    for row, manifest in items:
        dataset = manifest.dataset.model_copy(update={"problem_type": spelling})
        out.append((row, manifest.model_copy(update={"dataset": dataset})))
    return out


def test_the_statistics_service_accepts_a_lowercase_manifest_problem_type_and_refuses_an_unknown_one():
    """A20 L10 polish: the manifest-versus-family comparison in ``analyse_family`` is canonical (statistics.py, the in_family check)."""
    import test_analysis_statistics as fx
    from academic_benchmark.analysis.statistics import StatisticsRefusal

    plan = fx.activate(_plan())
    items = fx.per_instance_items(fx.SEPARATED)
    assert fx.run(_with_problem_type(items, "TSP"), plan, study=fx.STUDY3).inference is not None  # the baseline
    assert fx.run(_with_problem_type(items, "tsp"), plan, study=fx.STUDY3).inference is not None  # lowercase on one side
    with pytest.raises(StatisticsRefusal, match="not a known problem contract"):
        fx.run(_with_problem_type(items, "cvrp"), plan, study=fx.STUDY3)  # a valid manifest type that is no TSP/ATSP contract


def _study_datasets():
    from academic_benchmark.studies.service import load_study_with_plan, resolve_datasets

    loaded = load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=REPOSITORY_ROOT, mode="smoke")
    return list(resolve_datasets(loaded.study, repository_root=REPOSITORY_ROOT))


def _spelled(datasets, spelling):
    first = datasets[0]
    manifest = first.manifest.model_copy(update={"problem_type": spelling})
    return [first.__class__(first.manifest_path, manifest, first.artifact_sha256, first.problem_name, first.artifact_dimension)]


def test_the_dataset_cross_check_accepts_a_lowercase_manifest_problem_type_and_refuses_an_unknown_one():
    """A20 L10 polish: the dataset-manifest-versus-reference comparison in ``cross_check_study_datasets`` is canonical."""
    from academic_benchmark.analysis.gaps import ReferenceCrossCheckError, cross_check_study_datasets

    table = default_reference_table(REPOSITORY_ROOT)
    datasets = _study_datasets()
    assert datasets[0].manifest.problem_type in {"TSP", "ATSP"}
    declared = datasets[0].manifest.problem_type
    assert len(cross_check_study_datasets(table, _spelled(datasets, declared.lower()))) == 1  # lowercase on one side
    with pytest.raises(ReferenceCrossCheckError, match="not a known problem contract"):
        cross_check_study_datasets(table, _spelled(datasets, "cvrp"))


def test_an_unknown_contract_in_a_reference_set_is_a_cross_check_error_not_a_bare_contract_error():
    """A20 L10 polish: two reference sets for one instance whose contract spelling is unknown refuse as ``ReferenceCrossCheckError``."""
    import test_analysis_gap_columns as gc
    from academic_benchmark.analysis.gaps import ReferenceCrossCheckError, build_reference_table

    good = gc.exact_row("eil51", value=426)
    odd = good.model_copy(update={"problem_contract": "weird"})
    other = "docs/paper/results/tsplib-exact-reference/other"

    def unchecked(row, results_dir):  # the set validates its rows, so an unknown contract only gets in without validation
        return gc.ExactReferenceSet.model_construct(
            results_dir=results_dir, manifest_kind="tsp_reference", manifest_sha256=gc.SHA, manifest={}, rows=[row]
        )

    first_dir = "docs/paper/results/tsplib-exact-reference/stage1-verification"
    with pytest.raises(ReferenceCrossCheckError, match="eil51.*not a known problem contract"):
        build_reference_table([unchecked(good, first_dir), unchecked(odd, other)])
    with pytest.raises(ReferenceCrossCheckError, match="eil51.*not a known problem contract"):
        build_reference_table([unchecked(odd, first_dir), unchecked(good, other)])


def _plan():
    from academic_benchmark.studies.service import load_study_with_plan

    return load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=REPOSITORY_ROOT, mode="smoke").analysis_plan.plan


# ----------------------------------------------------------------------------------------- end to end, real data
def _profile_slice(root: Path, profile: str) -> str:
    """Copy of ``profile`` with eil51 (TSP), ft53 (ATSP) when the profile has it, and two cheap algorithms."""
    source = REPOSITORY_ROOT / "academic_benchmark" / "studies" / profile
    target = root / "academic_benchmark" / "studies" / profile
    target.mkdir(parents=True)
    payload = json.loads((source / "study.json").read_text(encoding="utf-8"))
    refs = [TSP_DATASET]
    levels = {"tsplib-eil51": payload["scaled_fixed_budget_levels"]["levels_by_dataset"]["tsplib-eil51"]}
    if "academic_benchmark/datasets/ft53.json" in payload["dataset_manifest_refs"]:
        refs.append("academic_benchmark/datasets/ft53.json")
        levels["tsplib-ft53"] = payload["scaled_fixed_budget_levels"]["levels_by_dataset"]["tsplib-ft53"]
    for ref in refs:
        manifest = json.loads((REPOSITORY_ROOT / ref).read_text(encoding="utf-8"))
        for name in (ref, manifest["artifact_path"]):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPOSITORY_ROOT / name, root / name)
    # the analysis plan is restricted to the slice (its families must name datasets of the study)
    plan = json.loads((source / "analysis_plan.json").read_text(encoding="utf-8"))
    plan["families"] = [f for f in plan["families"] if f["scope"] == "per_instance"]
    for family in plan["families"]:
        family["dataset_ids"] = [d for d in family["dataset_ids"] if d in levels]
    (target / "analysis_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    algorithms = ["Core-OrOpt-TSP", "Core-TwoOpt-TSP"]
    payload["algorithm_ids"] = algorithms
    payload["algorithm_parameters"] = {a: payload["algorithm_parameters"][a] for a in algorithms}
    payload["dataset_manifest_refs"] = refs
    payload["scaled_fixed_budget_levels"]["levels_by_dataset"] = levels
    payload["run_count"] = 1
    payload["secondary_protocol"]["algorithm_ids"] = [algorithms[0]]
    payload["secondary_protocol"]["termination"] = {"max_iterations": 2}
    (target / "study.json").write_text(json.dumps(payload), encoding="utf-8")
    return f"academic_benchmark/studies/{profile}/study.json"


@pytest.mark.parametrize("profile", PROFILES)
def test_smoke_study_writes_the_descriptive_report_with_gap_columns(tmp_path, profile):
    root = tmp_path / "repo"
    study_path = _profile_slice(root, profile)
    report = run_study(
        study_path, tmp_path / "out", mode="smoke", repository_root=root, replicates=1, git_provider=CLEAN,
        reference_table_provider=lambda _root: default_reference_table(REPOSITORY_ROOT),
    )
    assert report.status == "passed", report.text
    assert "descriptive_report.txt" in report.files and "descriptive_report.json" in report.files
    text = (tmp_path / "out" / "descriptive_report.txt").read_text(encoding="utf-8")
    data = json.loads((tmp_path / "out" / "descriptive_report.json").read_text(encoding="utf-8"))
    assert "Variable gap: gap to the exact reference" in text
    datasets = {table["cell"]["dataset_identity"] for table in data["tables"]}
    assert "eil51" in datasets
    assert ("ft53" in datasets) == (profile == "bildiri2026")  # the ATSP instance is only in the Bildiri profile
    for table in data["tables"]:
        for algorithm in table["algorithms"]:
            gap = algorithm["variables"]["gap"]
            assert gap["n"] >= 1 and gap["median"] is not None, (table["cell"], algorithm["algorithm_id"])
            assert algorithm["gap_missing"]["count"] == 0
    # the gap is 100 * (cost - proven optimum) / optimum: eil51 optimum 426
    first = next(t for t in data["tables"] if t["cell"]["dataset_identity"] == "eil51")
    for algorithm in first["algorithms"]:
        cost = algorithm["variables"]["cost"]["median"]
        assert algorithm["variables"]["gap"]["median"] == pytest.approx(100 * (cost - 426) / 426)
