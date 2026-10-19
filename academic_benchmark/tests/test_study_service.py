"""C-11: study service (load, resolve, preflight, expand)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from academic_benchmark.contracts import StudyManifestV1
from academic_benchmark.core.execution_gateway import (
    governed_comparison_manifest,
    governed_contract_seed,
)
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from academic_benchmark.studies import (
    StudyPlan,
    StudyServiceError,
    build_study_plan,
    expand_plan,
    load_study,
    preflight_study,
    resolve_datasets,
)
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BILDIRI_STUDY = "academic_benchmark/studies/bildiri2026/study.json"
TINY_PROBLEM_NAME = "TinyName"
ARTIFACT_BYTES = b"NAME: TinyName\nTYPE: ATSP\nDIMENSION: 3\n"


def _bildiri_payload() -> dict:
    return json.loads((REPOSITORY_ROOT / BILDIRI_STUDY).read_text(encoding="utf-8"))


def _dataset_payload(*, checksum: str | None = None, artifact_path: str = "data/tiny.atsp") -> dict:
    return {
        "schema_version": "uniride-dataset/v1",
        "dataset_id": "tiny",
        "artifact_path": artifact_path,
        "source": {"authority_url": "https://example.invalid/tiny", "retrieved_on": "2026-10-20"},
        "checksum": {
            "algorithm": "sha256",
            "value": checksum or hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
        },
        "problem_type": "ATSP",
        "dimension": 3,
        "matrix_semantics": {
            "directed": True,
            "edge_weight_type": "EXPLICIT",
            "edge_weight_format": "FULL_MATRIX",
            "diagonal_semantics": "sentinel",
        },
        "best_known": {"status": "unknown", "value": None, "provenance": "none"},
    }


def _tmp_study(root: Path, mutate=None, *, dataset: dict | None = None) -> Path:
    """Write a tiny repository (study + dataset manifest + artifact) under ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    for name in ("data", "datasets", "studies"):
        (root / name).mkdir(exist_ok=True)
    (root / "data" / "tiny.atsp").write_bytes(ARTIFACT_BYTES)
    (root / "datasets" / "tiny.json").write_text(
        json.dumps(dataset or _dataset_payload()), encoding="utf-8"
    )
    payload = _bildiri_payload()
    payload["dataset_manifest_refs"] = ["datasets/tiny.json"]
    if mutate is not None:
        mutate(payload)
    (root / "studies" / "study.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def _plan(root: Path, **kwargs) -> StudyPlan:
    return build_study_plan("studies/study.json", repository_root=root, **kwargs)


def test_bildiri_profile_loads_and_expands():
    plan = build_study_plan(BILDIRI_STUDY, repository_root=REPOSITORY_ROOT)
    study = plan.study
    assert study.study_id == "bildiri2026"
    fixed = [row for row in plan.rows if row.protocol is ExecutionProtocol.FIXED_BUDGET]
    native = [row for row in plan.rows if row.protocol is ExecutionProtocol.NATIVE_TERMINATION]
    datasets = len(study.dataset_manifest_refs)
    assert len(fixed) == (
        datasets * len(study.algorithm_ids) * len(study.fixed_budget_levels) * study.run_count
    )
    assert len(native) == (
        datasets * len(study.secondary_protocol.algorithm_ids) * study.run_count
    )


def test_secondary_memetic_without_native_claim_is_rejected(tmp_path):
    def mutate(payload):
        payload["secondary_protocol"]["algorithm_ids"] = ["Core-GWO-TSP-Memetic-2opt"]

    root = _tmp_study(tmp_path, mutate)
    # the contract alone accepts the profile ...
    StudyManifestV1.model_validate(
        json.loads((root / "studies" / "study.json").read_text(encoding="utf-8"))
    )
    # ... the service refuses it because no verified native claim exists.
    with pytest.raises(StudyServiceError, match="native_termination claim for Core-GWO-TSP-Memetic-2opt"):
        _plan(root)


def test_unknown_dataset_ref_is_rejected(tmp_path):
    def mutate(payload):
        payload["dataset_manifest_refs"] = ["datasets/missing.json"]

    root = _tmp_study(tmp_path, mutate)
    with pytest.raises(StudyServiceError, match="missing.json"):
        _plan(root)


def test_checksum_mismatch_is_rejected(tmp_path):
    root = _tmp_study(tmp_path, dataset=_dataset_payload(checksum="0" * 64))
    with pytest.raises(StudyServiceError, match="checksum"):
        _plan(root)


def test_absolute_dataset_ref_is_rejected(tmp_path):
    def mutate(payload):
        payload["dataset_manifest_refs"] = [str(tmp_path / "datasets" / "tiny.json")]

    root = _tmp_study(tmp_path, mutate)
    with pytest.raises(StudyServiceError):
        _plan(root)


def test_absolute_study_path_is_rejected(tmp_path):
    root = _tmp_study(tmp_path)
    with pytest.raises(StudyServiceError, match="repository-relative"):
        load_study(str(root / "studies" / "study.json"), repository_root=root)


def test_absolute_artifact_path_is_rejected(tmp_path):
    root = _tmp_study(
        tmp_path, dataset=_dataset_payload(artifact_path=str(tmp_path / "data" / "tiny.atsp"))
    )
    with pytest.raises(StudyServiceError):
        _plan(root)


@pytest.mark.parametrize("alias", ["Numba-GWO", "GWO-LKH", "gwo", "Core-GWO-TSP"])
def test_alias_algorithm_id_is_rejected(tmp_path, alias):
    def mutate(payload):
        payload["algorithm_ids"][0] = alias
        payload["algorithm_parameters"][alias] = payload["algorithm_parameters"].pop(
            "Core-GWO-TSP-Pure"
        )
        payload["secondary_protocol"]["algorithm_ids"] = ["Core-HHO-TSP-Pure"]

    root = _tmp_study(tmp_path, mutate)
    with pytest.raises(StudyServiceError):
        _plan(root)


def test_every_row_carries_its_budget_level_and_levels_are_never_merged(tmp_path):
    plan = _plan(_tmp_study(tmp_path))
    levels = plan.study.fixed_budget_levels
    fixed = [row for row in plan.rows if row.protocol is ExecutionProtocol.FIXED_BUDGET]
    assert {row.budget_level for row in fixed} == set(levels)
    for level in levels:
        at_level = [row for row in fixed if row.budget_level == level]
        assert len(at_level) == len(plan.study.algorithm_ids) * plan.study.run_count
    for row in plan.rows:
        if row.protocol is ExecutionProtocol.NATIVE_TERMINATION:
            assert row.budget_level is None
        else:
            assert isinstance(row.budget_level, int) and row.budget_level in levels
    keys = [
        (r.dataset_id, r.algorithm_id, r.protocol, r.budget_level, r.replicate) for r in plan.rows
    ]
    assert len(keys) == len(set(keys))


def test_fixed_seeds_equal_paired_seed_and_are_paired_across_levels(tmp_path):
    plan = _plan(_tmp_study(tmp_path))
    study = plan.study
    seeds_by_replicate: dict[tuple[str, int], set[int]] = {}
    for row in plan.rows:
        if row.protocol is not ExecutionProtocol.FIXED_BUDGET:
            continue
        # the seed identity is the TSPLIB NAME header (TINY_PROBLEM_NAME), never the dataset_id
        assert row.problem_name == TINY_PROBLEM_NAME != row.dataset_id
        manifest = FairComparisonManifest(
            evaluation_budget=row.budget_level,
            base_seed=study.base_seed,
            protocol_version=study.primary_protocol.protocol_version,
            budget_policy=study.primary_protocol.budget_policy,
            comparison_regime="fixed_evaluation_budget",
        )
        assert row.seed == manifest.paired_seed(TINY_PROBLEM_NAME, row.replicate)
        assert row.seed_group == manifest.seed_group(TINY_PROBLEM_NAME, row.replicate)
        assert row.seed != manifest.paired_seed(row.dataset_id, row.replicate)
        seeds_by_replicate.setdefault((row.problem_name, row.replicate), set()).add(row.seed)
    assert seeds_by_replicate
    assert all(len(seeds) == 1 for seeds in seeds_by_replicate.values())


def test_native_seeds_equal_native_manifest_paired_seed(tmp_path):
    plan = _plan(_tmp_study(tmp_path))
    study = plan.study
    native_rows = [r for r in plan.rows if r.protocol is ExecutionProtocol.NATIVE_TERMINATION]
    assert native_rows
    manifest = NativeComparisonManifest(
        base_seed=study.base_seed, protocol_version=study.secondary_protocol.protocol_version
    )
    for row in native_rows:
        assert row.seed == manifest.paired_seed(TINY_PROBLEM_NAME, row.replicate)
        assert row.seed_group == manifest.seed_group(TINY_PROBLEM_NAME, row.replicate)


def _assert_rows_match_gateway(plan_rows, study, expected_problem_name):
    """Cross-entry-point check: the plan seed is the seed the governed gateway accepts."""
    assert plan_rows
    for row in plan_rows:
        assert row.problem_name == expected_problem_name
        assert row.seed == governed_contract_seed(
            row.protocol, row.budget_level, study.base_seed, expected_problem_name, row.replicate
        )
        assert row.seed_group == governed_comparison_manifest(
            row.protocol, row.budget_level, study.base_seed
        ).seed_group(expected_problem_name, row.replicate)


def test_plan_seeds_equal_the_gateway_seeds_for_ft53_fixed_and_native():
    plan = build_study_plan(BILDIRI_STUDY, repository_root=REPOSITORY_ROOT)
    assert {r.protocol for r in plan.rows} == {
        ExecutionProtocol.FIXED_BUDGET,
        ExecutionProtocol.NATIVE_TERMINATION,
    }
    assert {r.dataset_id for r in plan.rows} == {"tsplib-ft53"}
    _assert_rows_match_gateway(plan.rows, plan.study, "ft53")


@pytest.mark.parametrize(
    "ref,family,name",
    [
        ("academic_benchmark/datasets/berlin52.json", "TSP", "berlin52"),
        ("academic_benchmark/datasets/eil51.json", "TSP", "eil51"),
        ("academic_benchmark/datasets/kroA100.json", "TSP", "kroA100"),
    ],
)
def test_plan_seeds_equal_the_gateway_seeds_for_c18_instances(ref, family, name):
    payload = _bildiri_payload()
    payload["dataset_manifest_refs"] = [ref]
    payload["problem_families"] = [family]
    study = StudyManifestV1.model_validate(payload)
    datasets = resolve_datasets(study, repository_root=REPOSITORY_ROOT)
    claims = preflight_study(study, datasets)
    assert claims
    _assert_rows_match_gateway(expand_plan(study, datasets), study, name)


def test_artifact_without_name_header_is_refused(tmp_path):
    no_name = b"TYPE: ATSP\nDIMENSION: 3\n"
    root = _tmp_study(tmp_path)
    (root / "data" / "tiny.atsp").write_bytes(no_name)
    (root / "datasets" / "tiny.json").write_text(
        json.dumps(_dataset_payload(checksum=hashlib.sha256(no_name).hexdigest())),
        encoding="utf-8",
    )
    with pytest.raises(StudyServiceError, match="NAME"):
        _plan(root)


def test_artifact_with_two_conflicting_name_headers_is_refused(tmp_path):
    two = b"NAME: one\nNAME: two\nTYPE: ATSP\nDIMENSION: 3\n"
    root = _tmp_study(tmp_path)
    (root / "data" / "tiny.atsp").write_bytes(two)
    (root / "datasets" / "tiny.json").write_text(
        json.dumps(_dataset_payload(checksum=hashlib.sha256(two).hexdigest())), encoding="utf-8"
    )
    with pytest.raises(StudyServiceError, match="NAME"):
        _plan(root)


def test_primary_protocol_version_must_be_the_gateway_fair_version(tmp_path):
    def mutate(payload):
        payload["primary_protocol"]["protocol_version"] = "uniride-fair-tsp-v1"

    with pytest.raises(StudyServiceError, match="uniride-fair-tsp-v2"):
        _plan(_tmp_study(tmp_path, mutate))


def test_secondary_protocol_version_must_be_the_gateway_native_version(tmp_path):
    def mutate(payload):
        payload["secondary_protocol"]["protocol_version"] = "uniride-native-tsp-v2"

    with pytest.raises(StudyServiceError, match="uniride-native-tsp-v1"):
        _plan(_tmp_study(tmp_path, mutate))


def test_secondary_without_algorithm_list_means_all_study_algorithms(tmp_path):
    def mutate(payload):
        payload["algorithm_ids"] = ["Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"]
        payload["algorithm_parameters"] = {
            key: payload["algorithm_parameters"][key] for key in payload["algorithm_ids"]
        }
        del payload["secondary_protocol"]["algorithm_ids"]

    plan = _plan(_tmp_study(tmp_path, mutate))
    native = [r for r in plan.rows if r.protocol is ExecutionProtocol.NATIVE_TERMINATION]
    assert {r.algorithm_id for r in native} == {"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"}
    assert {c.algorithm_id for c in plan.claims if c.protocol is ExecutionProtocol.NATIVE_TERMINATION} == {
        "Core-GWO-TSP-Pure",
        "Core-HHO-TSP-Pure",
    }


def test_study_base_seed_drives_the_plan_seeds(tmp_path):
    first = _plan(_tmp_study(tmp_path / "a"))

    def mutate(payload):
        payload["base_seed"] = payload["base_seed"] + 1

    second = _plan(_tmp_study(tmp_path / "b", mutate))
    assert [r.seed for r in first.rows] != [r.seed for r in second.rows]


def test_plan_is_immutable(tmp_path):
    plan = _plan(_tmp_study(tmp_path))
    assert isinstance(plan.rows, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.rows = ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.rows[0].seed = 1


def test_python_only_policy_rejects_numba_only_algorithms(tmp_path):
    root = _tmp_study(tmp_path)
    with pytest.raises(StudyServiceError, match="Core-GWO-TSP-Pure"):
        _plan(root, backend_policy=BackendPolicy.PYTHON_ONLY)


def test_unsupported_problem_family_is_rejected(tmp_path):
    def mutate(payload):
        payload["problem_families"] = ["CVRP"]

    root = _tmp_study(tmp_path, mutate)
    with pytest.raises(StudyServiceError):
        _plan(root)


def test_dataset_problem_type_must_be_declared_by_the_study(tmp_path):
    def mutate(payload):
        payload["problem_families"] = ["TSP"]

    root = _tmp_study(tmp_path, mutate)
    with pytest.raises(StudyServiceError, match="problem"):
        _plan(root)
