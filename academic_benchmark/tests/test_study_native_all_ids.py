"""Every algorithm ID of both study profiles can run natively and pass native validation (A18 OQ-4).

The committed profiles are not touched. A copy of each profile is built in ``tmp_path`` with
``secondary_protocol.algorithm_ids = null`` (every study ID) and a small ``termination``; the native rows
of the smallest instance (eil51, one replicate) run through the smoke service that the paper service
reuses (``run_study_smoke`` with the committed-artifact loader), so the native contract validation of
``_native_result_record`` and the composite check of the exported row both run for every ID.
"""
from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path

import pytest

from academic_benchmark.contracts.study import StudyManifestV1
from academic_benchmark.studies import build_study_plan
from academic_benchmark.studies.run import build_artifact_loader
from academic_benchmark.studies.smoke import ExecutionProtocol, run_study_smoke

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET = "academic_benchmark/datasets/eil51.json"
ARTIFACT = "academic_benchmark/tsplib_data/tsp/eil51.tsp"
PROFILES = ("bildiri2026", "yaem2026")


def _profile_repository(root: Path, profile: str, termination: dict) -> str:
    """Copy of ``profile`` limited to eil51, one run, native ids = null, the given termination."""
    source = REPOSITORY_ROOT / "academic_benchmark" / "studies" / profile
    target = root / "academic_benchmark" / "studies" / profile
    target.mkdir(parents=True)
    shutil.copy(source / "analysis_plan.json", target / "analysis_plan.json")
    for name in (DATASET, ARTIFACT):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPOSITORY_ROOT / name, root / name)
    payload = json.loads((source / "study.json").read_text(encoding="utf-8"))
    payload["dataset_manifest_refs"] = [DATASET]
    payload["scaled_fixed_budget_levels"]["levels_by_dataset"] = {
        "tsplib-eil51": payload["scaled_fixed_budget_levels"]["levels_by_dataset"]["tsplib-eil51"]
    }
    payload["run_count"] = 1
    payload["secondary_protocol"]["algorithm_ids"] = None
    payload["secondary_protocol"]["termination"] = termination
    (target / "study.json").write_text(json.dumps(payload), encoding="utf-8")
    return f"academic_benchmark/studies/{profile}/study.json"


def _native_only(plan):
    rows = tuple(r for r in plan.rows if r.protocol is not ExecutionProtocol.FIXED_BUDGET)
    return dataclasses.replace(plan, rows=rows)


def _run_native(tmp_path, profile, termination, skip=()):
    root = tmp_path / "repo"
    study_path = _profile_repository(root, profile, termination)
    plan = build_study_plan(study_path, repository_root=root)
    assert isinstance(plan.study, StudyManifestV1)
    assert plan.study.secondary_protocol.termination == termination
    plan = _native_only(plan)
    assert [r.algorithm_id for r in plan.rows] == list(plan.study.algorithm_ids)  # one native row per study ID
    plan = dataclasses.replace(plan, rows=tuple(r for r in plan.rows if not any(s in r.algorithm_id for s in skip)))
    expected = [r.algorithm_id for r in plan.rows]
    assert expected
    out = tmp_path / "out"
    report = run_study_smoke(
        plan, out, problem_loader=build_artifact_loader(plan, root), repository_root=root, replicates=1
    )
    detail = [(f.get("algorithm_id"), f.get("stage"), f.get("error")) for f in report.failed_rows]
    assert report.status == "passed", detail
    rows = [json.loads(line) for line in (out / "native_runs.jsonl").read_text("utf-8").splitlines()]
    assert [r["algorithm_id"] for r in rows] == expected
    return rows


@pytest.mark.parametrize("profile", PROFILES)
def test_the_thousand_iteration_form_runs_and_validates(tmp_path, profile):
    # the 3-opt based IDs (about 20 s each at 1000) are left to the 3-iteration test below
    rows = _run_native(tmp_path, profile, {"max_iterations": 1000}, skip=("ThreeOpt", "Memetic-3opt"))
    assert any(r["algorithm_id"] == "Core-OrOpt-TSP" for r in rows)
    assert all(r["evaluation_budget"] is None for r in rows)


@pytest.mark.parametrize("profile", PROFILES)
def test_every_study_id_produces_a_valid_native_row(tmp_path, profile):
    rows = _run_native(tmp_path, profile, {"max_iterations": 3})
    for row in rows:
        assert row["comparison_regime"] == "algorithm_native_termination"
        assert row["evaluation_budget"] is None
        assert row["hamiltonian_validation"] == "passed"
