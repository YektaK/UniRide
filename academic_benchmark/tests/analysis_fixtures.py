"""Synthetic-row builders and module fixtures shared by the Gate D analysis tests (D-05 onward; plan 2026-10-23 section 3).

This is a helper module, not a test module (no ``test_`` prefix, never collected): the analysis tests import it with
``from academic_benchmark.tests.analysis_fixtures import ...``. It must stay free of SciPy and statsmodels at import, so that every
test module that uses it can be collected in the per-push CI environment, which does not install the academic analysis extra
(``requirements-analysis.txt``, DECISION_LOG D-04a). The tests that need the extra at run time carry the
``requires_analysis_extra`` marker (see ``conftest.py``).

Every builder is synthetic; nothing here runs a solver or reads a result file.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from academic_benchmark.analysis.identity import comparison_cell_key
from academic_benchmark.analysis.manifests import make_run_id
from academic_benchmark.analysis.statistics import analyse_family
from academic_benchmark.contracts import RunManifestV1
from academic_benchmark.contracts.analysis_plan import AnalysisPlanV1
from academic_benchmark.contracts.run_index import RunIndexV2
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.studies.service import load_study_with_plan

REPO = Path(__file__).resolve().parents[2]
FAIR_V2 = "uniride-fair-tsp-v2"
COMMIT = "a" * 40
INDEX_SHA256 = "e" * 64  # the fixed run-index sha256 of the tests that build no campaign (A20 L7: analyse_family requires it)
PER_INSTANCE = "per-instance-independent"
ACROSS = "across-instances-tsp-matched"
_BILDIRI = load_study_with_plan("academic_benchmark/studies/bildiri2026/study.json", repository_root=REPO, mode="smoke").study
STUDY3 = _BILDIRI.model_copy(update={"algorithm_ids": ["Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP-Pure"]})  # the three algorithms of the fixtures
CROSS_INSTANCES = ["berlin52", "eil51", "st70", "kroA100", "rd100", "eil76"]
SEPARATED = {"Core-GA-TSP": [1, 2, 3, 4, 5], "Core-PSO-TSP": [6, 7, 8, 9, 10], "Core-GWO-TSP-Pure": [11, 12, 13, 14, 15]}
INTERLEAVED = {"Core-GA-TSP": [1, 4, 7, 10, 13], "Core-PSO-TSP": [2, 5, 8, 11, 14], "Core-GWO-TSP-Pure": [3, 6, 9, 12, 15]}


# ---------------------------------------------------------------- fixtures
def _dataset(dataset_id, dimension=51):
    return {
        "schema_version": "uniride-dataset/v1", "dataset_id": dataset_id,
        "artifact_path": f"academic_benchmark/tsplib_data/tsp/{dataset_id}.tsp",
        "source": {"authority_url": "https://example.invalid/x", "retrieved_on": "2026-10-19"},
        "checksum": {"algorithm": "sha256", "value": "0" * 64}, "problem_type": "TSP", "dimension": dimension,
        "matrix_semantics": {"directed": False, "edge_weight_type": "EUC_2D", "diagonal_semantics": "zero"},
        "best_known": {"status": "optimal", "value": 426.0, "provenance": "fixture"},
    }


def _levels(problem):
    """The study profile's own level list of the instance (what the run service records); a made-up pair for other names."""
    scaled = _BILDIRI.scaled_fixed_budget_levels.levels_by_dataset.get(f"tsplib-{normalize_problem(problem)}")
    if scaled is not None:
        return tuple(scaled)
    base = 1000 + 17 * len(problem)
    return (base, base * 5)


def make_item(problem, algorithm, replicate, gap, *, dirty=False, evidence=None, level=0, study_id="bildiri2026", **row_extra):
    levels = _levels(problem)
    dataset_id = f"tsplib-{normalize_problem(problem)}"
    manifest = RunManifestV1.model_validate({
        "schema_version": "uniride-run/v1", "run_id": make_run_id(study_id, dataset_id, algorithm, level, replicate),
        "study_id": study_id, "protocol_version": FAIR_V2, "git": {"commit": COMMIT, "dirty": dirty},
        "environment": {"python": "3.13", "operating_system": "test", "cpu": "test", "numpy": "2.4.6",
                        "numba": "0.66.0", "llvmlite": "0.48.0", "statistics_library": "none"},
        "dataset": _dataset(dataset_id),
        "algorithm": {"algorithm_id": algorithm, "capabilities": {}, "backend_policy": "prefer_numba",
                      "backend_profile": {"objective": "numba", "polish": "none"}, "capability_evidence_ids": ["fixture"],
                      "configuration": {"population": 20, "algorithm": algorithm}, "composition_stages": []},
        "seeds": {"base_seed": 2026, "derived": {"run_seed": 1}},
        "budget": {"levels": list(levels), "policy": "atomic_upper_bound_v1", "objective_evaluations": 5, "stage_allocation": {}},
        "termination": {"reason": "evaluation_budget_exhausted", "runtime_seconds": 0.1},
        "validation": {"passed": True, "checks": ["hamiltonian"]}, "outputs": [],
    })
    row = {
        "protocol_version": FAIR_V2, "comparison_regime": "fixed_evaluation_budget", "problem": problem,
        "algorithm_id": algorithm, "variant": "pure", "study_id": study_id, "evaluation_budget": levels[level],
        "termination_policy": "atomic_upper_bound_v1;max_iterations=1237500;max_no_improvement=1237500",
        "polish_policy": {"enabled": False, "initial": False, "periodic": False, "final": False, "operator": None},
        "objective_cost": 500.0 + gap, "elapsed_ms": 1.0, "replicate": replicate,
        "gap_to_exact_reference": gap, "gap_unit": "percent", "exact_reference_value": 426, "gap_missing_reason": None,
    }
    if evidence is not None:
        row["evidence_class"] = evidence
    row.update(row_extra)
    return row, manifest


def failed_item(problem, algorithm, replicate, **overrides):
    row = {
        "record_kind": "failed_run", "validation_status": "failed", "protocol_version": FAIR_V2, "study_id": "bildiri2026",
        "comparison_regime": "fixed_evaluation_budget", "problem": problem, "algorithm_id": algorithm,
        "replicate": replicate, "evaluation_budget": _levels(problem)[0],
    }
    row.update(overrides)
    return row, None


PLAN_SHA = "2" * 64
PROFILE_SHA = "1" * 64


def index_for(items, mode="paper", *, study_id="bildiri2026", dirty=False, drop=(), digest_of=None, extra_items=(),
              failed=None, plan_sha=PLAN_SHA, plan_id=None):
    """A ``RunIndexV2`` that lists the manifest of every completed item (the campaign index the caller has verified).

    ``failed`` are the failed items the index lists (default: every failed item of ``items``); ``plan_sha="absent"`` models a
    smoke campaign whose analysis plan file did not resolve."""
    runs = []
    for row, manifest in [*items, *extra_items]:
        if manifest is None or manifest.run_id in drop or any(r["run_id"] == manifest.run_id for r in runs):
            continue
        digest = comparison_cell_key(row, manifest, allow_dirty=True).digest()
        runs.append({"run_id": manifest.run_id, "manifest_path": f"manifests/{manifest.run_id}.json",
                     "manifest_checksum": {"algorithm": "sha256", "value": "b" * 64},
                     "comparison_key_digest": "0" * 64 if digest_of == "wrong" else digest})
    listed = [row for row, manifest in items if manifest is None and row.get("record_kind") == "failed_run"] if failed is None else [row for row, _ in failed]
    failed_runs = [{
        "algorithm_id": row["algorithm_id"], "dataset_id": row.get("dataset_id") or f"tsplib-{normalize_problem(row['problem'])}",
        "problem": row["problem"], "protocol_version": row["protocol_version"], "comparison_regime": row["comparison_regime"],
        "evaluation_budget": row.get("evaluation_budget"), "replicate": row["replicate"],
        "stage": "run", "exception_category": "RuntimeError", "error": "synthetic failure",
    } for row in listed]
    replicates = [row.get("replicate", 0) for row, _ in [*items, *extra_items]] or [0]
    environment = {"python": "3.13", "operating_system": "test", "cpu": "test", "numpy": "2.4.6", "numba": "0.66.0",
                   "llvmlite": "0.48.0", "statistics_library": "none"}
    absent = plan_sha == "absent"
    return RunIndexV2.model_validate({
        "schema_version": "uniride-run-index/v2", "study_id": study_id, "mode": mode,
        "status": "failed" if failed_runs else "passed",
        "seed_protocol_version": "sha256-seed-v1", "base_seed": 2026, "git": {"commit": COMMIT, "dirty": dirty},
        "environment": environment, "runs": runs, "outputs": [],
        "profile": {"path": f"academic_benchmark/studies/{study_id}/study.json", "sha256": PROFILE_SHA},
        "analysis_plan": {
            "analysis_plan_id": plan_id or _BILDIRI.analysis_plan_id,
            "path": None if absent else f"academic_benchmark/studies/{study_id}/analysis_plan.json",
            "sha256": None if absent else plan_sha,
        },
        "planned": {"runs_per_cell": max(replicates) + 1, "runs": max(1, len(runs) + len(failed_runs))},
        "output_location": {"path": "/campaign/out", "outside_repository_check": {"result": "outside_repository", "checked_against": ["/repo"]}},
        "failed_runs": failed_runs,
    })


def per_instance_items(samples, problem="eil51", study_id="bildiri2026"):
    return [make_item(problem, algorithm, r, gap, study_id=study_id) for algorithm, values in samples.items() for r, gap in enumerate(values)]


ALGORITHMS = ("Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP-Pure")


def cross_items(shift=0.0, problems=CROSS_INSTANCES, algorithms=ALGORITHMS, *, centres=None, skew=None):
    """Every instance orders the algorithms the same way; the per-instance median of A, B, C is i, i + 1, i + 2 unless
    ``centres[(problem, algorithm)]`` overrides it. ``skew[(problem, algorithm)]`` replaces the symmetric replicate offsets
    (-0.1, 0, +0.1) of that cell, so that its mean differs from its median (the median stays the centre)."""
    items = []
    for i, problem in enumerate(problems):
        for a, algorithm in enumerate(algorithms):
            centre = (centres or {}).get((problem, algorithm), float(i + a)) + shift
            offsets = (skew or {}).get((problem, algorithm), (-0.1, 0.0, 0.1))
            for r, offset in enumerate(offsets):
                items.append(make_item(problem, algorithm, r, centre + offset))
    return items


@pytest.fixture(scope="module")
def draft_plans():
    out = {}
    for study in ("bildiri2026", "yaem2026"):
        loaded = load_study_with_plan(f"academic_benchmark/studies/{study}/study.json", repository_root=REPO, mode="smoke")
        out[study] = loaded.analysis_plan.plan
    return out


@pytest.fixture(scope="module")
def draft(draft_plans):
    return draft_plans["bildiri2026"]


def activate(plan, *, minimum_n=3, alpha=None, rule=None, mutate=None):
    data = plan.model_dump(mode="json")
    data.update(status="active", unresolved=[], minimum_n_per_cell=minimum_n)
    if alpha is not None:
        data["alpha"] = alpha
    if rule is not None:
        for family in data["families"]:
            family["post_hoc"]["rule"] = rule
    if mutate is not None:
        mutate(data)
    return AnalysisPlanV1.model_validate(data)


@pytest.fixture(scope="module")
def active(draft):
    return activate(draft)


def study_for(items, plan=None):
    """The profile of a test: the Bildiri study with exactly the algorithms that occur in the items (completed or failed)."""
    names = {row["algorithm_id"] for row, _ in items}
    update = {"algorithm_ids": [a for a in (*ALGORITHMS, *sorted(names - set(ALGORITHMS))) if a in names]}
    if getattr(plan, "study_id", None) is not None:
        update["study_id"] = plan.study_id
        update["analysis_plan_id"] = plan.analysis_plan_id
    return _BILDIRI.model_copy(update=update)


def run(items, plan, family=PER_INSTANCE, *, mode="paper", study=None, **index_options):
    index_options.setdefault("plan_id", getattr(plan, "analysis_plan_id", None))
    return analyse_family(
        items, study=study or study_for(items, plan), plan=plan, family_id=family, run_index=index_for(items, mode, **index_options),
        index_sha256=INDEX_SHA256,
    )
