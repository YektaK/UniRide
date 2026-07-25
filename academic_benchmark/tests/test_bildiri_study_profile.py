from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def dataset_manifest() -> dict:
    path = Path(__file__).resolve().parent.parent / "datasets" / "ft53.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def study_manifest() -> dict:
    path = Path(__file__).resolve().parent.parent / "studies" / "bildiri2026" / "study.json"
    return json.loads(path.read_text(encoding="utf-8"))


class TestDatasetManifest:
    def test_schema_version_is_v1(self, dataset_manifest: dict):
        assert dataset_manifest["schema_version"] == "uniride-dataset/v1"

    def test_dataset_id_matches_ft53(self, dataset_manifest: dict):
        assert dataset_manifest["dataset_id"] == "tsplib-ft53"

    def test_artifact_path_is_relative(self, dataset_manifest: dict):
        artifact = dataset_manifest["artifact_path"]
        assert not Path(artifact).is_absolute()
        assert ".." not in Path(artifact).parts

    def test_checksum_is_sha256(self, dataset_manifest: dict):
        checksum = dataset_manifest["checksum"]
        assert checksum["algorithm"] == "sha256"
        assert len(checksum["value"]) == 64
        assert all(c in "0123456789abcdef" for c in checksum["value"])

    def test_problem_type_is_atsp(self, dataset_manifest: dict):
        assert dataset_manifest["problem_type"] == "ATSP"

    def test_dimension_is_53(self, dataset_manifest: dict):
        assert dataset_manifest["dimension"] == 53

    def test_matrix_semantics_directed(self, dataset_manifest: dict):
        semantics = dataset_manifest["matrix_semantics"]
        assert semantics["directed"] is True
        assert semantics["edge_weight_type"] == "EXPLICIT"
        assert semantics["edge_weight_format"] == "FULL_MATRIX"
        assert semantics["diagonal_semantics"] == "sentinel"

    def test_best_known_optimal(self, dataset_manifest: dict):
        best = dataset_manifest["best_known"]
        assert best["status"] == "optimal"
        assert best["value"] == 6905.0

    def test_source_has_authority_url(self, dataset_manifest: dict):
        source = dataset_manifest["source"]
        assert source["authority_url"].startswith("https://")
        assert "retrieved_on" in source


class TestStudyManifest:
    def test_schema_version_is_v1(self, study_manifest: dict):
        assert study_manifest["schema_version"] == "uniride-study/v1"

    def test_study_id_is_bildiri2026(self, study_manifest: dict):
        assert study_manifest["study_id"] == "bildiri2026"

    def test_status_is_draft(self, study_manifest: dict):
        assert study_manifest["status"] == "draft"

    def test_algorithm_ids_are_explicit(self, study_manifest: dict):
        ids = study_manifest["algorithm_ids"]
        assert len(ids) == 4
        assert all(id.startswith("Core-") for id in ids)
        assert all("GWO" in id or "HHO" in id for id in ids)

    def test_algorithm_parameters_match_ids(self, study_manifest: dict):
        ids = set(study_manifest["algorithm_ids"])
        params = set(study_manifest["algorithm_parameters"].keys())
        assert ids == params

    def test_dataset_manifest_refs_relative(self, study_manifest: dict):
        for ref in study_manifest["dataset_manifest_refs"]:
            assert not Path(ref).is_absolute()
            assert ".." not in Path(ref).parts

    def test_primary_protocol_present(self, study_manifest: dict):
        protocol = study_manifest["primary_protocol"]
        assert protocol["protocol_id"] == "fixed_evaluation_budget"
        assert "protocol_version" in protocol

    def test_secondary_protocol_present(self, study_manifest: dict):
        protocol = study_manifest["secondary_protocol"]
        assert protocol["protocol_id"] == "algorithm_native_termination"

    def test_problem_families_atsp_only(self, study_manifest: dict):
        assert study_manifest["problem_families"] == ["ATSP"]

    def test_seed_protocol_version(self, study_manifest: dict):
        assert study_manifest["seed_protocol_version"] == "sha256-seed-v1"

    def test_output_policy_smoke_only(self, study_manifest: dict):
        policy = study_manifest["output_policy"]
        assert policy["repository_outputs"] == "smoke_only"


class TestDatasetArtifactExists:
    def test_ft53_atsp_file_exists(self):
        path = Path(__file__).resolve().parent.parent / "tsplib_data" / "ft53.atsp"
        assert path.exists(), f"Missing dataset artifact: {path}"

    def test_ft53_atsp_file_matches_checksum(self, dataset_manifest: dict):
        import hashlib
        path = Path(__file__).resolve().parent.parent / "tsplib_data" / "ft53.atsp"
        if not path.exists():
            pytest.skip("ft53.atsp not present")
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        assert digest.hexdigest() == dataset_manifest["checksum"]["value"]
