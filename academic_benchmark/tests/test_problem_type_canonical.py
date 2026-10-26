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
@pytest.mark.parametrize("value", ["tsp", "TSP", "Tsp", " tsp ", ProblemContract.TSP])
def test_tsp_spellings_map_to_one_contract(value):
    assert canonical_problem_contract(value) is ProblemContract.TSP


@pytest.mark.parametrize("value", ["atsp", "ATSP", "Atsp", ProblemContract.ATSP])
def test_atsp_spellings_map_to_one_contract(value):
    assert canonical_problem_contract(value) is ProblemContract.ATSP


@pytest.mark.parametrize("value", ["", "cvrp", "uniride_wave", "tsp2", None, 3, b"tsp"])
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
    assert "eil51" in text and "gap" in text.lower()
    assert "426" in json.dumps(data)  # the proven eil51 optimum is the reference value of the gap
