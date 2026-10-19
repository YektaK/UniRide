"""C-18: ``uniride-dataset/v1`` manifests for the six TSPLIB study instances.

The manifests are checked against the committed files and the two collection
manifests (``tsp/MANIFEST.json`` and ``opt_tours/MANIFEST.json``). Nothing here
reads ``tsplib.db`` or the archive.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from academic_benchmark.contracts import DatasetManifestV1

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = REPO_ROOT / "academic_benchmark" / "datasets"
TSP_MANIFEST = REPO_ROOT / "academic_benchmark" / "tsplib_data" / "tsp" / "MANIFEST.json"
TOUR_MANIFEST = REPO_ROOT / "academic_benchmark" / "tsplib_data" / "opt_tours" / "MANIFEST.json"

# manifest file stem -> instance name in the collection manifests (kroA100 is lower-case there)
STUDY_INSTANCES = {
    "berlin52": "berlin52",
    "eil51": "eil51",
    "st70": "st70",
    "kroA100": "kroa100",
    "eil76": "eil76",
    "rd100": "rd100",
}


def sha256_of_file(relative_path: str) -> str:
    """Checksum helper: sha256 of the committed bytes of a repository-relative file."""
    return hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()


def _load_manifest(stem: str) -> DatasetManifestV1:
    path = DATASETS_DIR / f"{stem}.json"
    return DatasetManifestV1.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _collection_entry(stem: str) -> dict:
    wanted = STUDY_INSTANCES[stem]
    entries = [e for e in json.loads(TSP_MANIFEST.read_text(encoding="utf-8"))["instances"] if e["name"].lower() == wanted.lower()]
    assert len(entries) == 1
    return entries[0]


def _tour_entry(stem: str) -> dict:
    wanted = STUDY_INSTANCES[stem]
    entries = [e for e in json.loads(TOUR_MANIFEST.read_text(encoding="utf-8"))["instances"] if e["name"].lower() == wanted.lower()]
    assert len(entries) == 1
    return entries[0]


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_manifest_resolves_through_dataset_contract(stem: str) -> None:
    manifest = _load_manifest(stem)
    assert manifest.schema_version == "uniride-dataset/v1"
    assert manifest.dataset_id == f"tsplib-{STUDY_INSTANCES[stem]}"
    assert manifest.problem_type == "TSP"


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_checksum_matches_referenced_file_and_collection_manifest(stem: str) -> None:
    manifest = _load_manifest(stem)
    entry = _collection_entry(stem)
    assert manifest.artifact_path == entry["artifact_path"]
    assert manifest.checksum.algorithm == "sha256"
    assert manifest.checksum.value == entry["sha256"]
    assert sha256_of_file(manifest.artifact_path) == manifest.checksum.value


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_dimension_and_metric_semantics_follow_the_collection_manifest(stem: str) -> None:
    manifest = _load_manifest(stem)
    entry = _collection_entry(stem)
    assert manifest.dimension == entry["dimension"] == _tour_entry(stem)["dimension"]
    semantics = manifest.matrix_semantics
    # EUC_2D is the TSPLIB nearest-integer Euclidean distance (E10/T06); the symmetric TSP is undirected.
    assert entry["edge_weight_type"] == "EUC_2D"
    assert semantics.edge_weight_type == "EUC_2D"
    assert semantics.directed is False
    assert semantics.edge_weight_format is None
    assert semantics.diagonal_semantics == "zero"


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_optimum_equals_published_optimum_of_collection_manifest(stem: str) -> None:
    manifest = _load_manifest(stem)
    entry = _collection_entry(stem)
    assert manifest.best_known.status == "optimal"
    assert manifest.best_known.value == float(entry["published_optimum"])
    tour = _tour_entry(stem)
    assert tour["source"] == "archive_copy"
    # the optimum provenance names the committed collection manifests and the committed optimal tour
    assert "academic_benchmark/tsplib_data/tsp/MANIFEST.json" in manifest.best_known.provenance
    assert tour["artifact_path"] in manifest.best_known.provenance
    assert tour["sha256"] in manifest.best_known.provenance


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_source_is_the_tsplib95_authority_named_by_the_tour_manifest(stem: str) -> None:
    manifest = _load_manifest(stem)
    tour_url = _tour_entry(stem)["authority_url"]
    assert tour_url.endswith(".opt.tour.gz")
    assert manifest.source.authority_url == tour_url[: -len(".opt.tour.gz")] + ".tsp.gz"
    # no download is performed; the date is the collection manifest's recorded date
    assert manifest.source.retrieved_on.isoformat() == _collection_entry(stem)["retrieved_on"]


@pytest.mark.parametrize("stem", sorted(STUDY_INSTANCES))
def test_paths_are_repository_relative_without_archive_or_database(stem: str) -> None:
    raw = (DATASETS_DIR / f"{stem}.json").read_text(encoding="utf-8")
    manifest = _load_manifest(stem)
    for path in (manifest.artifact_path,):
        assert not Path(path).is_absolute()
        assert ".." not in Path(path).parts
        assert (REPO_ROOT / path).is_file()
    assert "archive/" not in raw
    assert "tsplib.db" not in raw
    assert ":\\" not in raw and "C:/" not in raw


def test_gil262_is_not_part_of_the_study_manifests() -> None:
    assert not (DATASETS_DIR / "gil262.json").exists()
