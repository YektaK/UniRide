from __future__ import annotations

import json
from importlib.resources import files

import pytest
from pydantic import ValidationError

from academic_benchmark.core.algorithm_errors import CandidateAlgorithmError
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.core.preflight import PreflightRequest, RuntimeBackendAvailability, preflight_run
from academic_benchmark.contracts import DatasetManifestV1, RunManifestV1, StudyManifestV1
from academic_benchmark.contracts.export_schemas import check_schemas, render_schemas
from academic_benchmark.contracts.common import (
    ChecksumV1,
    RepositoryRelativePath,
    StrictContract,
)
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol


class _PathProbe(StrictContract):
    path: RepositoryRelativePath


@pytest.mark.parametrize(
    "value",
    ["academic_benchmark/datasets/ft53.json", "studies/yaem2026/study.json"],
)
def test_repository_relative_path_accepts_normalized_paths(value: str):
    assert _PathProbe(path=value).path == value


@pytest.mark.parametrize(
    "value",
    ["/absolute/file.json", r"C:\\secret\\file.json", "../escape.json", "a/../../escape.json", "", "."],
)
def test_repository_relative_path_rejects_absolute_or_traversal(value: str):
    with pytest.raises(ValidationError):
        _PathProbe(path=value)


def test_strict_contract_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ChecksumV1(algorithm="sha256", value="a" * 64, unexpected=True)


def test_sha256_contract_rejects_non_hex_or_wrong_length():
    with pytest.raises(ValidationError):
        ChecksumV1(algorithm="sha256", value="not-a-digest")


def _study_payload() -> dict:
    return {
        "schema_version": "uniride-study/v1",
        "study_id": "yaem2026",
        "title": "YAEM 2026 Reproducible Study",
        "status": "draft",
        "algorithm_ids": ["Core-GWO-TSP-Pure"],
        "algorithm_parameters": {"Core-GWO-TSP-Pure": {"pack_size": 20}},
        "dataset_manifest_refs": ["academic_benchmark/datasets/ft53.json"],
        "primary_protocol": {
            "protocol_id": "fixed_evaluation_budget",
            "protocol_version": "uniride-fair-tsp-v2",
            "budget_policy": "atomic_upper_bound_v1",
        },
        "secondary_protocol": {
            "protocol_id": "algorithm_native_termination",
            "protocol_version": "uniride-native-tsp-v1",
            "termination": {"max_iterations": 250},
        },
        "fixed_budget_levels": [1000, 5000],
        "run_count": 30,
        "base_seed": 2026,
        "seed_protocol_version": "sha256-seed-v1",
        "problem_families": ["TSP", "ATSP"],
        "analysis_plan_id": "yaem2026-analysis-v1",
        "output_policy": {"repository_outputs": "smoke_only", "paper_scale_location": "external"},
        "paper_metadata": {"paper_id": "yaem2026", "year": 2026, "venue": "YAEM"},
    }


def _dataset_payload() -> dict:
    return {
        "schema_version": "uniride-dataset/v1",
        "dataset_id": "tsplib-ft53",
        "artifact_path": "academic_benchmark/tsplib_data/ft53.atsp",
        "source": {
            "authority_url": "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz",
            "retrieved_on": "2026-07-20",
        },
        "checksum": {"algorithm": "sha256", "value": "6" * 64},
        "problem_type": "ATSP",
        "dimension": 53,
        "matrix_semantics": {
            "directed": True,
            "edge_weight_type": "EXPLICIT",
            "edge_weight_format": "FULL_MATRIX",
            "diagonal_semantics": "sentinel",
        },
        "best_known": {
            "status": "optimal",
            "value": 6905.0,
            "provenance": "TSPLIB canonical optimum",
        },
    }


def _run_payload() -> dict:
    return {
        "schema_version": "uniride-run/v1",
        "run_id": "yaem2026-ft53-gwo-r00-b1000",
        "study_id": "yaem2026",
        "protocol_version": "uniride-fair-tsp-v2",
        "git": {"commit": "a" * 40, "dirty": False},
        "environment": {
            "python": "3.14.3", "operating_system": "Windows", "cpu": "test-cpu",
            "numpy": "2.4.6", "numba": "0.66.0", "llvmlite": "0.48.0",
            "statistics_library": "scipy-unavailable",
        },
        "dataset": _dataset_payload(),
        "algorithm": {
            "algorithm_id": "Core-GWO-TSP-Pure",
            "requested_algorithm_id": None,
            "backend_policy": "require_numba",
            "backend_profile": {"objective": "numba", "polish": "none"},
            "capability_evidence_ids": ["test_exact_capability"],
            "capabilities": {"problem_types": ["TSP", "ATSP"], "directed_costs": True},
            "configuration": {"pack_size": 20},
            "composition_stages": [],
        },
        "seeds": {"base_seed": 2026, "derived": {"replicate_0": 17}},
        "budget": {
            "levels": [1000], "policy": "atomic_upper_bound_v1",
            "objective_evaluations": 998, "stage_allocation": {},
        },
        "termination": {"reason": "evaluation_budget_exhausted", "runtime_seconds": 0.25},
        "validation": {"passed": True, "checks": ["complete_tour", "closed_cycle_cost"]},
        "outputs": [{"path": "academic_benchmark/results/smoke.json", "checksum": {"algorithm": "sha256", "value": "b" * 64}}],
    }

def test_all_v1_contracts_accept_complete_payloads():
    assert StudyManifestV1.model_validate(_study_payload()).study_id == "yaem2026"
    assert DatasetManifestV1.model_validate(_dataset_payload()).dimension == 53
    assert RunManifestV1.model_validate(_run_payload()).budget.objective_evaluations == 998


def test_study_requires_exact_parameter_keys_for_algorithm_ids():
    payload = _study_payload()
    payload["algorithm_parameters"] = {"different-id": {}}
    with pytest.raises(ValidationError, match="algorithm_parameters keys"):
        StudyManifestV1.model_validate(payload)



@pytest.mark.parametrize(
    "algorithm_id",
    ["Numba-GWO", "GWO", "unknown", "Core-GWO-TSP-Memetic-3opt"],
)
def test_study_rejects_alias_unknown_and_planned_primary_ids(algorithm_id: str):
    payload = _study_payload()
    payload["algorithm_ids"] = [algorithm_id]
    payload["algorithm_parameters"] = {algorithm_id: {}}
    with pytest.raises(ValidationError):
        StudyManifestV1.model_validate(payload)


@pytest.mark.parametrize(
    "algorithm_id", ["Numba-GWO", "unknown", "Core-GWO-TSP-Memetic-3opt"]
)
def test_study_rejects_alias_unknown_and_planned_secondary_ids(algorithm_id: str):
    payload = _study_payload()
    payload["secondary_protocol"]["algorithm_ids"] = [algorithm_id]
    with pytest.raises(ValidationError):
        StudyManifestV1.model_validate(payload)


def test_canonical_candidate_manifest_id_is_structurally_valid_but_preflight_rejects_it():
    manifest = StudyManifestV1.model_validate(_study_payload())
    candidate_id = manifest.algorithm_ids[0]
    problem = type(
        "Problem",
        (),
        {
            "name": "candidate-boundary",
            "problem_type": "atsp",
            "dimension": 3,
            "dist_matrix": [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]],
        },
    )()
    with pytest.raises(CandidateAlgorithmError):
        preflight_run(
            PreflightRequest(
                resolution=resolve_algorithm_id(candidate_id, IdentifierSource.MANIFEST),
                problem=problem,
                protocol=ExecutionProtocol.FIXED_BUDGET,
                backend_policy=BackendPolicy.REQUIRE_NUMBA_OBJECTIVE,
                evaluation_budget=10,
                registered_algorithm_ids=frozenset({candidate_id}),
                runtime_backends=RuntimeBackendAvailability(True, True, "unit test"),
            )
        )


def test_algorithm_run_requires_strict_decision_provenance():
    for field in ("backend_policy", "backend_profile", "capability_evidence_ids"):
        invalid = _run_payload()
        invalid["algorithm"].pop(field)
        with pytest.raises(ValidationError):
            RunManifestV1.model_validate(invalid)

    for backend_profile in (
        {"objective": "python"},
        {"objective": "python", "polish": "none", "extra": "no"},
        {"objective": "unused", "polish": "none"},
        {"objective": "python", "polish": "mixed"},
    ):
        invalid = _run_payload()
        invalid["algorithm"]["backend_profile"] = backend_profile
        with pytest.raises(ValidationError):
            RunManifestV1.model_validate(invalid)

    payload = _run_payload()
    payload["algorithm"]["requested_algorithm_id"] = "Numba-GWO"
    validated = RunManifestV1.model_validate(payload)
    assert validated.algorithm.requested_algorithm_id == "Numba-GWO"


def test_algorithm_run_rejects_nonliteral_policy_and_nonlist_evidence():
    invalid_policy = _run_payload()
    invalid_policy["algorithm"]["backend_policy"] = "prefer_numba_objective"
    with pytest.raises(ValidationError):
        RunManifestV1.model_validate(invalid_policy)

    invalid_evidence = _run_payload()
    invalid_evidence["algorithm"]["capability_evidence_ids"] = ("test",)
    with pytest.raises(ValidationError):
        RunManifestV1.model_validate(invalid_evidence)
@pytest.mark.parametrize("model,payload", [(StudyManifestV1, _study_payload), (DatasetManifestV1, _dataset_payload), (RunManifestV1, _run_payload)])
def test_v1_contracts_reject_unknown_top_level_fields(model, payload):
    value = payload()
    value["unknown"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate(value)


def test_schema_versions_are_exact_not_heuristic():
    payload = _study_payload()
    payload["schema_version"] = "uniride-study/v2"
    with pytest.raises(ValidationError):
        StudyManifestV1.model_validate(payload)


def test_schema_snapshots_match_models_and_have_exact_ids():
    assert check_schemas() == []
    expected_ids = {
        "study-v1.schema.json": "uniride-study/v1",
        "dataset-v1.schema.json": "uniride-dataset/v1",
        "run-v1.schema.json": "uniride-run/v1",
    }
    for name, rendered in render_schemas().items():
        schema = json.loads(rendered)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == expected_ids[name]
        assert schema["additionalProperties"] is False


def test_schema_snapshots_are_package_resources():
    root = files("academic_benchmark.schemas")
    for name in ("study-v1.schema.json", "dataset-v1.schema.json", "run-v1.schema.json"):
        assert json.loads(root.joinpath(name).read_text(encoding="utf-8"))["$id"]
