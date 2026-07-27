from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts import DatasetManifestV1, StudyManifestV1
from academic_benchmark.native_protocol import APPROVED_NATIVE_ALGORITHMS, NATIVE_PROTOCOL
from uniride_core.algorithms.tsplib_parser import parse_atsp_text


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_MANIFEST_PATH = REPOSITORY_ROOT / "academic_benchmark" / "datasets" / "ft53.json"
STUDY_MANIFEST_PATH = (
    REPOSITORY_ROOT / "academic_benchmark" / "studies" / "bildiri2026" / "study.json"
)
APPROVED_ARTIFACT_RELATIVE_PATH = "academic_benchmark/tsplib_data/ft53.atsp"
APPROVED_ARTIFACT_PATH = REPOSITORY_ROOT / APPROVED_ARTIFACT_RELATIVE_PATH
APPROVED_SHA256 = "692ae545e226d88aa095e3e726c8a1dadf4ecc9b97852d0cdbb2ca2a98dd2634"
APPROVED_AUTHORITY_URL = (
    "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/ft53.atsp.gz"
)
APPROVED_OPTIMUM_PROVENANCE = "TSPLIB95 canonical ATSP optimum"
PRIMARY_ALGORITHM_IDS = [
    "Core-GWO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Pure",
    "Core-HHO-TSP-Memetic-2opt",
]
SECONDARY_ALGORITHM_IDS = ["Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"]


@pytest.fixture(scope="module")
def dataset_manifest_payload() -> dict:
    payload = json.loads(DATASET_MANIFEST_PATH.read_text(encoding="utf-8"))
    DatasetManifestV1.model_validate(payload)
    return payload


@pytest.fixture(scope="module")
def dataset_manifest(dataset_manifest_payload: dict) -> DatasetManifestV1:
    return DatasetManifestV1.model_validate(dataset_manifest_payload)


@pytest.fixture(scope="module")
def study_manifest_payload() -> dict:
    payload = json.loads(STUDY_MANIFEST_PATH.read_text(encoding="utf-8"))
    StudyManifestV1.model_validate(payload)
    return payload


@pytest.fixture(scope="module")
def study_manifest(study_manifest_payload: dict) -> StudyManifestV1:
    return StudyManifestV1.model_validate(study_manifest_payload)


@pytest.fixture(scope="module")
def declared_artifact_path(dataset_manifest: DatasetManifestV1) -> Path:
    resolved = (REPOSITORY_ROOT / dataset_manifest.artifact_path).resolve()
    assert dataset_manifest.artifact_path == APPROVED_ARTIFACT_RELATIVE_PATH
    assert resolved == APPROVED_ARTIFACT_PATH.resolve()
    assert resolved.is_file(), f"Missing manifest-declared dataset artifact: {resolved}"
    return resolved


class TestDatasetManifest:
    def test_identity_and_atsp_shape(self, dataset_manifest: DatasetManifestV1):
        assert dataset_manifest.schema_version == "uniride-dataset/v1"
        assert dataset_manifest.dataset_id == "tsplib-ft53"
        assert dataset_manifest.problem_type == "ATSP"
        assert dataset_manifest.dimension == 53

    def test_pins_approved_checksum(self, dataset_manifest: DatasetManifestV1):
        assert dataset_manifest.checksum.algorithm == "sha256"
        assert dataset_manifest.checksum.value == APPROVED_SHA256

    def test_pins_source_provenance(self, dataset_manifest: DatasetManifestV1):
        assert dataset_manifest.source.authority_url == APPROVED_AUTHORITY_URL
        assert dataset_manifest.source.retrieved_on == date(2026, 7, 20)
        assert dataset_manifest.best_known.status == "optimal"
        assert dataset_manifest.best_known.value == 6905.0
        assert dataset_manifest.best_known.provenance == APPROVED_OPTIMUM_PROVENANCE

    def test_pins_directed_full_matrix_semantics(self, dataset_manifest: DatasetManifestV1):
        semantics = dataset_manifest.matrix_semantics
        assert semantics.directed is True
        assert semantics.edge_weight_type == "EXPLICIT"
        assert semantics.edge_weight_format == "FULL_MATRIX"
        assert semantics.diagonal_semantics == "sentinel"


class TestStudyManifest:
    def test_profile_identity_and_scope(self, study_manifest: StudyManifestV1):
        assert study_manifest.schema_version == "uniride-study/v1"
        assert study_manifest.study_id == "bildiri2026"
        assert study_manifest.status == "draft"
        assert study_manifest.problem_families == ["ATSP"]
        assert study_manifest.seed_protocol_version == "sha256-seed-v1"
        assert study_manifest.output_policy.repository_outputs == "smoke_only"

    def test_primary_protocol_retains_all_four_variants(self, study_manifest: StudyManifestV1):
        assert study_manifest.algorithm_ids == PRIMARY_ALGORITHM_IDS
        assert set(study_manifest.algorithm_parameters) == set(PRIMARY_ALGORITHM_IDS)
        assert study_manifest.primary_protocol.protocol_id == "fixed_evaluation_budget"

    def test_secondary_protocol_selects_native_compatible_intersection(
        self, study_manifest: StudyManifestV1
    ):
        secondary = study_manifest.secondary_protocol
        assert secondary is not None
        assert secondary.protocol_version == NATIVE_PROTOCOL
        assert secondary.algorithm_ids == SECONDARY_ALGORITHM_IDS
        assert set(secondary.algorithm_ids) == (
            set(study_manifest.algorithm_ids) & APPROVED_NATIVE_ALGORITHMS
        )
        assert set(secondary.algorithm_ids) <= APPROVED_NATIVE_ALGORITHMS

    def test_dataset_manifest_reference_is_the_validated_ft53_manifest(
        self, study_manifest: StudyManifestV1
    ):
        assert study_manifest.dataset_manifest_refs == [
            "academic_benchmark/datasets/ft53.json"
        ]

    def test_secondary_algorithm_ids_remain_optional_for_existing_manifests(
        self, study_manifest_payload: dict
    ):
        payload = deepcopy(study_manifest_payload)
        payload["secondary_protocol"].pop("algorithm_ids", None)
        validated = StudyManifestV1.model_validate(payload)
        assert validated.secondary_protocol is not None
        assert validated.secondary_protocol.algorithm_ids is None

    @pytest.mark.parametrize(
        "algorithm_ids,error",
        [
            ([], "secondary_protocol.algorithm_ids must be non-empty"),
            (
                ["Core-GWO-TSP-Pure", "Core-GWO-TSP-Pure"],
                "secondary_protocol.algorithm_ids must be unique",
            ),
            (["Numba-2-opt"], "secondary_protocol.algorithm_ids must be a subset"),
        ],
    )
    def test_secondary_algorithm_ids_are_a_non_empty_unique_study_subset(
        self,
        study_manifest_payload: dict,
        algorithm_ids: list[str],
        error: str,
    ):
        payload = deepcopy(study_manifest_payload)
        payload["secondary_protocol"]["algorithm_ids"] = algorithm_ids
        with pytest.raises(ValidationError, match=error):
            StudyManifestV1.model_validate(payload)

    def test_secondary_protocol_still_rejects_unknown_fields(
        self, study_manifest_payload: dict
    ):
        payload = deepcopy(study_manifest_payload)
        payload["secondary_protocol"]["unknown"] = True
        with pytest.raises(ValidationError, match="extra_forbidden"):
            StudyManifestV1.model_validate(payload)


class TestManifestDeclaredArtifact:
    def test_exact_sha256(
        self,
        dataset_manifest: DatasetManifestV1,
        declared_artifact_path: Path,
    ):
        digest = hashlib.sha256(declared_artifact_path.read_bytes()).hexdigest()
        assert digest == APPROVED_SHA256
        assert digest == dataset_manifest.checksum.value

    def test_parsed_atsp_metadata_and_matrix(
        self,
        dataset_manifest: DatasetManifestV1,
        declared_artifact_path: Path,
    ):
        text = declared_artifact_path.read_text(encoding="utf-8")
        header, weight_section = text.split("EDGE_WEIGHT_SECTION", maxsplit=1)
        weight_text = weight_section.split("EOF", maxsplit=1)[0]
        weights = [int(token) for token in weight_text.split()]

        assert "TYPE: ATSP" in header
        assert "DIMENSION: 53" in header
        assert "EDGE_WEIGHT_TYPE: EXPLICIT" in header
        assert "EDGE_WEIGHT_FORMAT: FULL_MATRIX" in header
        assert len(weights) == 53 * 53 == 2809

        parsed = parse_atsp_text(text, "ft53")
        assert parsed is not None
        assert parsed["problem_type"] == dataset_manifest.problem_type == "ATSP"
        assert parsed["dimension"] == dataset_manifest.dimension == 53
        assert parsed["edge_weight_type"] == "EXPLICIT"

        matrix = parsed["explicit_matrix"]
        assert len(matrix) == 53
        assert all(len(row) == 53 for row in matrix)
        assert all(matrix[index][index] == 9999999 for index in range(53))
        assert any(
            matrix[row][column] != matrix[column][row]
            for row in range(53)
            for column in range(row + 1, 53)
        )
