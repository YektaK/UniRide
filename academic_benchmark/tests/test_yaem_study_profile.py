"""C-13: the active YAEM 2026 study profile (draft, smoke only; owner Q1 option a).

The profile mirrors the legacy YAEM set under truthful canonical IDs: ``GWO-LKH``/``HHO-LKH`` were
false historical labels and are replaced by ``Core-GWO-TSP-Memetic-3opt``/``Core-HHO-TSP-Memetic-3opt``.
Budget levels (the Bildiri rule ``two_opt_scan_multiples_v1`` with the same multipliers), run count and
seed are draft placeholders until a paper plan exists. Nothing here makes a claim about an algorithm.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from academic_benchmark.committed_bytes import run_git
from academic_benchmark.composite_protocol import COMPOSITE_ALGORITHMS
from academic_benchmark.fairness import validate_scientific_composite_params
from academic_benchmark.studies import (
    StudyServiceError,
    build_study_plan,
    load_study,
)
from academic_benchmark.studies.smoke import run_study_smoke
from uniride_core.algorithms.capabilities import ExecutionProtocol
from uniride_core.algorithms.distance import tsplib_distance_by_type
from uniride_core.algorithms.tsplib_parser import parse_tsplib_text

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
YAEM_STUDY = "academic_benchmark/studies/yaem2026/study.json"
EXPECTED_ALGORITHM_IDS = [
    "Core-TwoOpt-TSP",
    "Core-ThreeOpt-TSP",
    "Core-OrOpt-TSP",
    "Core-GWO-TSP-Pure",
    "Core-HHO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Memetic-2opt",
    "Core-GWO-TSP-Memetic-3opt",
    "Core-HHO-TSP-Memetic-3opt",
    "Core-GWO-TSP-Memetic-ALNS",
    "Core-HHO-TSP-Memetic-ALNS",
]
EXPECTED_DATASET_REFS = [
    "academic_benchmark/datasets/berlin52.json",
    "academic_benchmark/datasets/eil51.json",
    "academic_benchmark/datasets/st70.json",
    "academic_benchmark/datasets/kroA100.json",
]
# n(n-1)/2 per instance: one full 2-opt scan (C-19 rule); the draft levels are 50 and 250 scans
SCAN_SIZES = {"tsplib-berlin52": 1326, "tsplib-eil51": 1275, "tsplib-st70": 2415, "tsplib-kroa100": 4950}
BERLIN52_LOWEST_LEVEL = 50 * 1326
MEMETIC_2OPT = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads((REPOSITORY_ROOT / YAEM_STUDY).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan():
    return build_study_plan(YAEM_STUDY, repository_root=REPOSITORY_ROOT)


# ------------------------------------------------------------------------------------- the profile
def test_profile_loads_through_the_study_service_and_passes_preflight(plan):
    study = plan.study
    assert study.study_id == "yaem2026"
    assert study.status == "draft"
    assert study.output_policy.repository_outputs == "smoke_only"
    assert study.problem_families == ["TSP"]
    assert study.algorithm_ids == EXPECTED_ALGORITHM_IDS
    assert study.dataset_manifest_refs == EXPECTED_DATASET_REFS
    assert study.primary_protocol.protocol_id == "fixed_evaluation_budget"
    assert study.secondary_protocol.protocol_id == "algorithm_native_termination"
    # one verified claim per algorithm and protocol (fixed and native), TSP only
    claimed = {(c.algorithm_id, c.protocol) for c in plan.claims}
    assert claimed == {(a, p) for a in EXPECTED_ALGORITHM_IDS for p in ExecutionProtocol}


def test_budget_levels_are_the_bildiri_rule_with_its_multipliers_and_recompute(plan):
    scaled = plan.study.scaled_fixed_budget_levels
    assert scaled.rule == "two_opt_scan_multiples_v1" and scaled.scan_multipliers == [50, 250]
    fixed = [r for r in plan.rows if r.protocol is ExecutionProtocol.FIXED_BUDGET]
    for dataset_id, scan in SCAN_SIZES.items():
        levels = {r.budget_level for r in fixed if r.dataset_id == dataset_id}
        assert levels == {50 * scan, 250 * scan}  # recomputed by the service from the manifests
    assert plan.study.run_count == 3  # smoke placeholder


def test_every_algorithm_runs_both_protocols_and_rows_are_not_pooled(plan):
    native = [r for r in plan.rows if r.protocol is ExecutionProtocol.NATIVE_TERMINATION]
    assert {r.algorithm_id for r in native} == set(EXPECTED_ALGORITHM_IDS)
    assert all(r.budget_level is None for r in native)
    fixed = [r for r in plan.rows if r.protocol is ExecutionProtocol.FIXED_BUDGET]
    assert all(r.budget_level is not None for r in fixed)


@pytest.mark.parametrize("algorithm_id", sorted(COMPOSITE_ALGORITHMS))
def test_composite_entries_state_global_fraction_explicitly_and_validate(payload, algorithm_id):
    block = payload["algorithm_parameters"][algorithm_id]
    assert block["global_fraction"] == 0.80
    validate_scientific_composite_params(algorithm_id, block, fixed_budget=True)
    native_block = {k: v for k, v in block.items() if k != "global_fraction"}
    validate_scientific_composite_params(algorithm_id, native_block, fixed_budget=False)


@pytest.mark.parametrize("algorithm_id", MEMETIC_2OPT)
def test_memetic_2opt_entries_state_non_zero_polish_explicitly(payload, algorithm_id):
    block = payload["algorithm_parameters"][algorithm_id]
    for key in ("polish_iters", "final_polish_iters", "polish_interval"):
        assert key in block, f"{algorithm_id}.{key} must be explicit (C-04: no default)"
        assert type(block[key]) is int and block[key] >= 1


def test_pure_and_polish_free_entries_carry_no_polish_keys(payload):
    for algorithm_id in ("Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure", "Core-TwoOpt-TSP"):
        assert not {"polish_iters", "final_polish_iters", "polish_interval", "global_fraction"} & set(
            payload["algorithm_parameters"][algorithm_id]
        )


# --------------------------------------------------------------------------- truthful labels only
def _mutated(tmp_path: Path, mutate) -> str:
    """Write a mutated copy of the profile inside a copy of the repository layout it needs."""
    root = tmp_path / "repo"
    (root / "studies").mkdir(parents=True)
    value = json.loads((REPOSITORY_ROOT / YAEM_STUDY).read_text(encoding="utf-8"))
    mutate(value)
    (root / "studies" / "study.json").write_text(json.dumps(value), encoding="utf-8")
    return str(root)


def _rename_in_ids(old: str, new: str):
    def mutate(value):
        value["algorithm_ids"][value["algorithm_ids"].index(old)] = new
        value["algorithm_parameters"][new] = value["algorithm_parameters"].pop(old)

    return mutate


def _rename_in_secondary(new: str):
    def mutate(value):
        value["secondary_protocol"]["algorithm_ids"] = [new]

    return mutate


def _rename_in_parameter_keys(old: str, new: str):
    def mutate(value):
        value["algorithm_parameters"][new] = value["algorithm_parameters"].pop(old)

    return mutate


@pytest.mark.parametrize(
    "false_label, replacement",
    [("GWO-LKH", "Core-GWO-TSP-Memetic-3opt"), ("HHO-LKH", "Core-HHO-TSP-Memetic-3opt")],
)
@pytest.mark.parametrize("field", ["algorithm_ids", "secondary_protocol", "algorithm_parameters"])
def test_false_lkh_labels_are_refused_with_the_truthful_replacement_named(
    tmp_path, false_label, replacement, field
):
    mutate = {
        "algorithm_ids": _rename_in_ids(replacement, false_label),
        "secondary_protocol": _rename_in_secondary(false_label),
        "algorithm_parameters": _rename_in_parameter_keys(replacement, false_label),
    }[field]
    root = _mutated(tmp_path, mutate)
    with pytest.raises(StudyServiceError) as caught:
        load_study("studies/study.json", repository_root=Path(root))
    assert replacement in str(caught.value)


def test_the_profile_text_never_uses_an_lkh_label():
    text = (REPOSITORY_ROOT / YAEM_STUDY).read_text(encoding="utf-8")
    assert "lkh" not in text.lower()


def test_no_archive_path_anywhere_in_the_profile_or_its_datasets(plan):
    text = (REPOSITORY_ROOT / YAEM_STUDY).read_text(encoding="utf-8")
    assert not re.search(r"archive[\/]", text, re.IGNORECASE)
    for dataset in plan.datasets:
        manifest_text = (REPOSITORY_ROOT / dataset.manifest_path).read_text(encoding="utf-8")
        assert not re.search(r"archive[\/]", manifest_text, re.IGNORECASE), dataset.manifest_path
        assert not dataset.manifest.artifact_path.startswith("archive")


# ---------------------------------------------------------------------------------- smoke on berlin52
@dataclass
class _Problem:
    name: str
    dist_matrix: list
    problem_type: str = "tsp"
    optimal: float = 7542.0
    edge_weight_type: str = "EUC_2D"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


def _berlin52_loader():
    text = (REPOSITORY_ROOT / "academic_benchmark/tsplib_data/tsp/berlin52.tsp").read_text(encoding="utf-8")
    data = parse_tsplib_text(text, "berlin52")
    coords = data["coordinates"]
    matrix = [
        [0.0 if i == j else float(tsplib_distance_by_type("EUC_2D", coords[i], coords[j]))
         for j in range(len(coords))]
        for i in range(len(coords))
    ]
    problem = _Problem(name=data["name"], dist_matrix=matrix)
    return lambda _name: problem


def _git_status() -> str:
    return run_git(["status", "--porcelain"], REPOSITORY_ROOT).decode("utf-8", "replace")


def test_smoke_run_of_the_profile_on_berlin52_at_the_lowest_budget_passes(plan, tmp_path):
    berlin = dataclasses.replace(
        plan,
        datasets=tuple(d for d in plan.datasets if d.dataset_id == "tsplib-berlin52"),
        rows=tuple(r for r in plan.rows if r.dataset_id == "tsplib-berlin52"),
    )
    before = _git_status()
    report = run_study_smoke(
        berlin, tmp_path / "out", problem_loader=_berlin52_loader(),
        repository_root=REPOSITORY_ROOT, replicates=1,
    )
    assert report.status == "passed", report.text
    assert report.budget_level == BERLIN52_LOWEST_LEVEL
    out = tmp_path / "out"
    fixed = [json.loads(line) for line in (out / "fixed_runs.jsonl").read_text(encoding="utf-8").splitlines()]
    native = [json.loads(line) for line in (out / "native_runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["algorithm_id"] for r in fixed] == EXPECTED_ALGORITHM_IDS
    assert [r["algorithm_id"] for r in native] == EXPECTED_ALGORITHM_IDS
    assert {r["evaluation_budget"] for r in fixed} == {BERLIN52_LOWEST_LEVEL}
    assert {r["evaluation_budget"] for r in native} == {None}
    for row in fixed + native:
        assert row["validation_status"] == "passed" and row["hamiltonian_validation"] == "passed"
        assert row["problem"] == "berlin52" and row["smoke"] is True
    for row in fixed + native:
        assert ("composition" in row) == (row["algorithm_id"] in COMPOSITE_ALGORITHMS)
    for row in fixed:
        if row["algorithm_id"] in COMPOSITE_ALGORITHMS:
            assert row["composition"]["global_fraction"] == 0.80
    assert not (out / "failed_runs.jsonl").exists()
    assert _git_status() == before  # the smoke output left nothing in the repository


# ------------------------------------------------------------------------------------- seed identity
BILDIRI_STUDY = "academic_benchmark/studies/bildiri2026/study.json"


def test_yaem_and_bildiri_profiles_do_not_share_a_base_seed(payload):
    """Owner decision 2026-10-23 (A17): independent replicates on the shared instances need distinct seeds."""
    bildiri = json.loads((REPOSITORY_ROOT / BILDIRI_STUDY).read_text(encoding="utf-8"))
    assert payload["base_seed"] != bildiri["base_seed"]
    assert payload["base_seed"] == 2027  # draft placeholder chosen by the lead, owner-approved
    assert payload["status"] == "draft"
