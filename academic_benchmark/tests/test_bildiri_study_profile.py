from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts import DatasetManifestV1, StudyManifestV1
from academic_benchmark.native_protocol import NATIVE_PROTOCOL
from academic_benchmark.tests.profile_status import assert_real_status
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
# C-19 (owner 2026-10-19/21): the paper's algorithm set plus the current GWO/HHO entries.
PRIMARY_ALGORITHM_IDS = [
    "Core-TwoOpt-TSP",
    "Core-ThreeOpt-TSP",
    "Core-OrOpt-TSP",
    "Core-GA-TSP",
    "Core-PSO-TSP",
    "Core-GA-TSP-Memetic-2opt",
    "Core-GWO-TSP-Pure",
    "Core-HHO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt",
    "Core-HHO-TSP-Memetic-2opt",
]
DATASET_REFS = [
    "academic_benchmark/datasets/berlin52.json",
    "academic_benchmark/datasets/eil51.json",
    "academic_benchmark/datasets/st70.json",
    "academic_benchmark/datasets/kroA100.json",
    "academic_benchmark/datasets/rd100.json",
    "academic_benchmark/datasets/eil76.json",
    "academic_benchmark/datasets/ft53.json",
]
# n(n-1)/2 (one full 2-opt scan) per dataset; levels are 50 and 250 scans (owner 2026-10-21, revised)
SCAN_SIZES = {
    "tsplib-berlin52": 1326, "tsplib-eil51": 1275, "tsplib-st70": 2415, "tsplib-kroa100": 4950,
    "tsplib-rd100": 4950, "tsplib-eil76": 2850, "tsplib-ft53": 1378,
}
# The budget is the stopping rule (owner 2026-10-21): iteration and stagnation limits of the
# non-memetic-swarm entries equal the largest level of the profile (250 x 4950, kroA100/rd100).
LARGEST_LEVEL = 1237500
GA_C16A_DEFAULTS = {
    "max_iterations": LARGEST_LEVEL, "crossover_rate": 0.85, "mutation_rate": 0.15, "elite_count": 2,
    "tournament_size": 3, "max_no_improvement": LARGEST_LEVEL,
}
SECONDARY_ALGORITHM_IDS = [  # all ten study algorithms (A18 OQ-4 a)
    "Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-OrOpt-TSP", "Core-GA-TSP", "Core-PSO-TSP",
    "Core-GA-TSP-Memetic-2opt", "Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure",
    "Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt",
]


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
        assert_real_status(study_manifest.status)  # draft until the approval commit, active after it
        assert study_manifest.problem_families == ["TSP", "ATSP"]
        assert study_manifest.run_count == 30  # A18 OQ-1 a (owner 2026-10-26); smoke caps replicates at 3 (SMOKE_MAX_REPLICATES)
        assert study_manifest.seed_protocol_version == "sha256-seed-v1"
        assert study_manifest.output_policy.repository_outputs == "smoke_only"

    def test_paper_venue_is_the_congress_name(self, study_manifest: StudyManifestV1):
        # D-10 Prepare step (owner 2026-10-28): the venue is named; the status is draft until the approval commit, active after it.
        assert_real_status(study_manifest.status)
        assert study_manifest.paper_metadata.venue == "14. Uluslararası Göbeklitepe Bilimsel Çalışmalar Kongresi"
        assert study_manifest.paper_metadata.year == 2026
        assert "draft" not in study_manifest.paper_metadata.venue.lower()

    def test_primary_protocol_holds_the_ten_paper_aligned_ids(self, study_manifest: StudyManifestV1):
        assert study_manifest.algorithm_ids == PRIMARY_ALGORITHM_IDS
        assert set(study_manifest.algorithm_parameters) == set(PRIMARY_ALGORITHM_IDS)
        assert study_manifest.primary_protocol.protocol_id == "fixed_evaluation_budget"

    def test_budget_levels_are_50_and_250_two_opt_scans_per_instance(
        self, study_manifest: StudyManifestV1
    ):
        assert study_manifest.fixed_budget_levels is None
        scaled = study_manifest.scaled_fixed_budget_levels
        assert scaled.rule == "two_opt_scan_multiples_v1"
        assert scaled.scan_multipliers == [50, 250]
        assert scaled.levels_by_dataset == {
            dataset_id: [50 * k, 250 * k] for dataset_id, k in SCAN_SIZES.items()
        }

    def test_ga_entries_use_population_20_and_explicit_c16a_defaults(
        self, study_manifest: StudyManifestV1
    ):
        params = study_manifest.algorithm_parameters
        assert params["Core-GA-TSP"] == {"population_size": 20, **GA_C16A_DEFAULTS}
        assert params["Core-GA-TSP-Memetic-2opt"] == {
            "population_size": 20, **GA_C16A_DEFAULTS,
            "initial_polish_iters": 1, "final_polish_iters": 1,
        }

    def test_local_search_entries_state_the_registry_defaults(self, study_manifest: StudyManifestV1):
        params = study_manifest.algorithm_parameters
        assert params["Core-TwoOpt-TSP"] == {"max_iterations": 1000, "first_improvement": False}
        assert params["Core-ThreeOpt-TSP"] == {"max_iterations": 1000, "first_improvement": False, "window": 12}
        assert params["Core-OrOpt-TSP"] == {"max_iterations": 1000, "first_improvement": False, "window": 3}

    def test_memetic_entries_use_one_scan_per_polish(self, study_manifest: StudyManifestV1):
        params = study_manifest.algorithm_parameters
        for algorithm_id in ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt"):
            entry = params[algorithm_id]
            assert (entry["polish_iters"], entry["final_polish_iters"]) == (1, 1), algorithm_id
            assert entry["polish_interval"] == 25, algorithm_id  # the solver default, stated
        for algorithm_id in ("Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"):
            assert not {"polish_iters", "final_polish_iters", "polish_interval"} & set(params[algorithm_id])

    def test_secondary_protocol_selects_native_compatible_intersection(
        self, study_manifest: StudyManifestV1
    ):
        secondary = study_manifest.secondary_protocol
        assert secondary is not None
        assert secondary.protocol_version == NATIVE_PROTOCOL
        # A18 OQ-4 a (owner 2026-10-26): every study algorithm runs natively, in the order of algorithm_ids,
        # with the single safety limit max_iterations 1000 (pre-approval values commit).
        assert secondary.algorithm_ids == SECONDARY_ALGORITHM_IDS == study_manifest.algorithm_ids
        assert secondary.termination == {"max_iterations": 1000}
        # APPROVED_NATIVE_ALGORITHMS is the legacy native-pilot set (GWO/HHO pure, 2-opt, 3-opt, Or-opt, ALNS) and
        # no longer bounds the study profile: native admission of all ten IDs is proven by
        # test_study_native_all_ids.py (A18 branch fix/native-admission-all-study-ids).

    def test_verified_ids_are_canonical_manifest_declarations(
        self, study_manifest: StudyManifestV1
    ):
        from uniride_core.algorithms.capabilities import LifecycleStatus, get_algorithm_capability

        assert all(
            get_algorithm_capability(algorithm_id).lifecycle is LifecycleStatus.VERIFIED
            for algorithm_id in study_manifest.algorithm_ids
        )

    def test_dataset_refs_are_the_six_paper_instances_and_ft53(
        self, study_manifest: StudyManifestV1
    ):
        assert study_manifest.dataset_manifest_refs == DATASET_REFS

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
            (["Numba-2-opt"], "is not canonical"),
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
