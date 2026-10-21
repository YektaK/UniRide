"""C-19: instance-scaled fixed budget levels (owner 2026-10-21, DECISION_LOG A17).

Each level is a number of full 2-opt scans: ``multiplier x n(n-1)/2`` objective evaluations, with
``n`` the dataset dimension. The study states the rule, the multipliers and the resulting table;
the contract checks its internal consistency and the study service recomputes every entry from the
dataset manifest (and the artifact's DIMENSION header) and refuses a mismatch.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts import StudyManifestV1
from academic_benchmark.studies.service import (
    StudyServiceError,
    build_study_plan,
    expand_plan,
    fixed_budget_levels_for,
    resolve_datasets,
)
from academic_benchmark.studies.smoke import StudySmokeError, select_smoke_rows, write_rows_file
from uniride_core.algorithms.capabilities import ExecutionProtocol

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BILDIRI_STUDY = "academic_benchmark/studies/bildiri2026/study.json"
TINY_BYTES = b"NAME: TinyName\nTYPE: ATSP\nDIMENSION: 3\nEDGE_WEIGHT_SECTION\n"


def _base_payload() -> dict:
    payload = json.loads((REPOSITORY_ROOT / BILDIRI_STUDY).read_text(encoding="utf-8"))
    payload.pop("scaled_fixed_budget_levels", None)
    payload.pop("fixed_budget_levels", None)
    return payload


def _scaled(table: dict, multipliers=(20, 100)) -> dict:
    return {
        "rule": "two_opt_scan_multiples_v1",
        "scan_multipliers": list(multipliers),
        "levels_by_dataset": table,
    }


def _contract(scaled=None, levels=None) -> dict:
    payload = _base_payload()
    if scaled is not None:
        payload["scaled_fixed_budget_levels"] = scaled
    if levels is not None:
        payload["fixed_budget_levels"] = levels
    return payload


# ---------------------------------------------------------------- contract (no file access)

def test_scaled_levels_are_accepted_and_fixed_levels_stay_valid():
    study = StudyManifestV1.model_validate(_contract(_scaled({"tsplib-ft53": [27560, 137800]})))
    assert study.fixed_budget_levels is None
    assert study.scaled_fixed_budget_levels.levels_by_dataset == {"tsplib-ft53": [27560, 137800]}
    legacy = StudyManifestV1.model_validate(_contract(levels=[10000, 50000]))
    assert legacy.fixed_budget_levels == [10000, 50000]
    assert legacy.scaled_fixed_budget_levels is None


@pytest.mark.parametrize(
    "payload,match",
    [
        (_contract(_scaled({"tsplib-ft53": [27560, 137800]}), [100]), "exactly one"),
        (_contract(), "exactly one"),
        (_contract(_scaled({"tsplib-ft53": [137800, 27560]}, (100, 20))), "increasing"),
        (_contract(_scaled({"tsplib-ft53": [27560, 27560]}, (20, 20))), "increasing"),
        (_contract(_scaled({"tsplib-ft53": [27560]})), "one level per multiplier"),
        (_contract(_scaled({"tsplib-ft53": [27560, 137801]})), "multiplier x n\\(n-1\\)/2"),
        (_contract(_scaled({"tsplib-ft53": [27560, 140000]})), "multiplier x n\\(n-1\\)/2"),
        (_contract(_scaled({"x": [80, 400]})), "n\\(n-1\\)/2"),  # k = 4 is not n(n-1)/2
        (_contract(_scaled({})), "levels_by_dataset"),
    ],
)
def test_inconsistent_scaled_tables_are_refused_by_the_contract(payload, match):
    with pytest.raises(ValidationError, match=match):
        StudyManifestV1.model_validate(payload)


def test_unknown_rule_is_refused():
    scaled = _scaled({"tsplib-ft53": [27560, 137800]})
    scaled["rule"] = "something_else"
    with pytest.raises(ValidationError):
        StudyManifestV1.model_validate(_contract(scaled))


# ---------------------------------------------------------------- service (recomputation)

def _tiny_repo(root: Path, table: dict, *, multipliers=(20, 100), manifest_dimension: int = 3,
               artifact: bytes = TINY_BYTES) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name in ("data", "datasets", "studies"):
        (root / name).mkdir(exist_ok=True)
    (root / "data" / "tiny.atsp").write_bytes(artifact)
    dataset = {
        "schema_version": "uniride-dataset/v1",
        "dataset_id": "tiny",
        "artifact_path": "data/tiny.atsp",
        "source": {"authority_url": "https://example.invalid/tiny", "retrieved_on": "2026-10-21"},
        "checksum": {"algorithm": "sha256", "value": hashlib.sha256(artifact).hexdigest()},
        "problem_type": "ATSP",
        "dimension": manifest_dimension,
        "matrix_semantics": {
            "directed": True, "edge_weight_type": "EXPLICIT",
            "edge_weight_format": "FULL_MATRIX", "diagonal_semantics": "sentinel",
        },
        "best_known": {"status": "unknown", "value": None, "provenance": "none"},
    }
    (root / "datasets" / "tiny.json").write_text(json.dumps(dataset), encoding="utf-8")
    payload = _contract(_scaled(table, multipliers))
    payload["dataset_manifest_refs"] = ["datasets/tiny.json"]
    payload["problem_families"] = ["ATSP"]
    (root / "studies" / "study.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def _plan(root: Path):
    return build_study_plan("studies/study.json", repository_root=root)


def test_scaled_plan_rows_carry_the_recomputed_levels(tmp_path):
    plan = _plan(_tiny_repo(tmp_path, {"tiny": [60, 300]}))  # n = 3 -> 3 candidates per scan
    fixed = [r for r in plan.rows if r.protocol is ExecutionProtocol.FIXED_BUDGET]
    assert {r.budget_level for r in fixed} == {60, 300}
    assert len(fixed) == 2 * len(plan.study.algorithm_ids) * plan.study.run_count
    assert fixed_budget_levels_for(plan.study, plan.datasets[0]) == (60, 300)


@pytest.mark.parametrize(
    "table,multipliers,match",
    [
        ({"tiny": [120, 600]}, (20, 100), "n\\(n-1\\)/2 = 3"),  # table built for n = 4
        ({"tiny": [60, 300]}, (10, 50), "n\\(n-1\\)/2 = 3"),  # wrong multipliers for n = 3
        ({"other": [60, 300]}, (20, 100), "dataset ids"),
        ({"tiny": [60, 300], "other": [60, 300]}, (20, 100), "dataset ids"),
    ],
)
def test_service_refuses_a_table_that_does_not_match_the_dataset(tmp_path, table, multipliers, match):
    with pytest.raises(StudyServiceError, match=match):
        _plan(_tiny_repo(tmp_path, table, multipliers=multipliers))


def test_manifest_dimension_must_match_the_artifact_header_in_scaled_mode(tmp_path):
    # manifest says n = 4 and the table is consistent with it, the artifact says DIMENSION: 3
    with pytest.raises(StudyServiceError, match="DIMENSION"):
        _plan(_tiny_repo(tmp_path, {"tiny": [120, 600]}, manifest_dimension=4))


def test_expand_plan_recomputes_even_when_called_directly(tmp_path):
    root = _tiny_repo(tmp_path, {"tiny": [60, 300]})
    plan = _plan(root)
    payload = plan.study.model_dump(mode="json")
    payload["scaled_fixed_budget_levels"]["levels_by_dataset"] = {"tiny": [120, 600]}
    forged = StudyManifestV1.model_validate(payload)
    with pytest.raises(StudyServiceError, match="n\\(n-1\\)/2 = 3"):
        expand_plan(forged, plan.datasets)


# ---------------------------------------------------------------- the live Bildiri profile

EXPECTED_SCANS = {  # n(n-1)/2 per dataset id
    "tsplib-berlin52": 1326, "tsplib-eil51": 1275, "tsplib-st70": 2415,
    "tsplib-kroa100": 4950, "tsplib-rd100": 4950, "tsplib-eil76": 2850, "tsplib-ft53": 1378,
}


def test_live_profile_levels_are_20_and_100_scans_of_every_instance():
    plan = build_study_plan(BILDIRI_STUDY, repository_root=REPOSITORY_ROOT)
    scaled = plan.study.scaled_fixed_budget_levels
    assert plan.study.fixed_budget_levels is None
    assert scaled.rule == "two_opt_scan_multiples_v1" and scaled.scan_multipliers == [20, 100]
    for dataset in plan.datasets:
        k = EXPECTED_SCANS[dataset.dataset_id]
        assert fixed_budget_levels_for(plan.study, dataset) == (20 * k, 100 * k)
        rows = [r for r in plan.rows if r.dataset_id == dataset.dataset_id
                and r.protocol is ExecutionProtocol.FIXED_BUDGET]
        assert {r.budget_level for r in rows} == {20 * k, 100 * k}
        for level in (20 * k, 100 * k):  # every algorithm gets the same budget on the instance
            assert {r.algorithm_id for r in rows if r.budget_level == level} == set(plan.study.algorithm_ids)


def test_live_profile_smoke_slice_takes_the_lowest_level_per_dataset():
    plan = build_study_plan(BILDIRI_STUDY, repository_root=REPOSITORY_ROOT)
    rows = select_smoke_rows(plan, replicates=1)
    by_dataset = {}
    for row in rows:
        if row.protocol is ExecutionProtocol.FIXED_BUDGET:
            by_dataset.setdefault(row.dataset_id, set()).add(row.budget_level)
    assert by_dataset == {d: {20 * k} for d, k in EXPECTED_SCANS.items()}
    one = select_smoke_rows(plan, replicates=1, budget_level=100 * 1378)
    assert {(r.dataset_id, r.budget_level) for r in one if r.protocol is ExecutionProtocol.FIXED_BUDGET} == {
        ("tsplib-ft53", 137800)
    }
    with pytest.raises(StudySmokeError, match="budget level"):
        select_smoke_rows(plan, replicates=1, budget_level=10000)


def test_rows_file_allows_one_level_per_dataset_only_when_asked(tmp_path):
    fixed = {"comparison_regime": "fixed_evaluation_budget", "protocol_version": "uniride-fair-tsp-v2"}
    rows = [dict(fixed, dataset_id="a", evaluation_budget=60), dict(fixed, dataset_id="b", evaluation_budget=120)]
    with pytest.raises(StudySmokeError, match="budget level"):
        write_rows_file(tmp_path / "x.jsonl", rows, expected_group="fixed_budget")
    write_rows_file(tmp_path / "y.jsonl", rows, expected_group="fixed_budget", per_dataset_levels=True)
    mixed = rows + [dict(fixed, dataset_id="a", evaluation_budget=300)]
    with pytest.raises(StudySmokeError, match="budget level"):
        write_rows_file(tmp_path / "z.jsonl", mixed, expected_group="fixed_budget", per_dataset_levels=True)
    assert not (tmp_path / "x.jsonl").exists() and not (tmp_path / "z.jsonl").exists()
