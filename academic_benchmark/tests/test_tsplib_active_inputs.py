"""WP-E8 companion task: the TSPLIB inputs of the exact reference runner live in active, manifest-governed folders.

* ``academic_benchmark/tsplib_data/tsp/`` holds the 16 TSP verification instances (E09) with ``MANIFEST.json``;
* ``academic_benchmark/tsplib_data/opt_tours/`` holds the published optimal tours (copied from the Bildiri archive, never moved);
* the runner defaults to these folders, refuses any path in the archive, and ``--verify-tours`` of the committed
  stage-1 results passes without a database.

Nothing here opens ``tsplib.db``. A test that needs the database is not part of this file.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_exact_tsp_reference.py"
INPUTS_MODULE = REPO / "academic_benchmark" / "exact_reference" / "inputs.py"
TSP_DIR = REPO / "academic_benchmark" / "tsplib_data" / "tsp"
TOUR_DIR = REPO / "academic_benchmark" / "tsplib_data" / "opt_tours"
STAGE1 = REPO / "docs" / "paper" / "results" / "tsplib-exact-reference" / "stage1-verification"
ARCHIVE_MANIFEST = REPO / "archive" / "academic_benchmark" / "bildiri2026_legacy" / "manifest.json"

EXPECTED_TSP = ("burma14", "ulysses16", "ulysses22", "att48", "eil51", "berlin52", "st70", "eil76", "pr76", "gr96",
                "kroa100", "krob100", "kroc100", "krod100", "kroe100", "rd100")
NO_PUBLISHED_TOUR = ("burma14", "ft53", "krob100", "kroe100")
KINDS = {"local_copy", "archive_copy", "db_reconstruction"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def runner():
    spec = importlib.util.spec_from_file_location("run_exact_tsp_reference_active", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def inputs():
    from academic_benchmark.exact_reference import inputs as mod

    return mod


@pytest.fixture(scope="module")
def stage1():
    return json.loads((STAGE1 / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tsp_manifest():
    return json.loads((TSP_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tour_manifest():
    return json.loads((TOUR_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the 16 .tsp files
def test_tsp_manifest_lists_the_16_verification_instances_with_existing_files(tsp_manifest):
    assert tsp_manifest["schema_version"] == "uniride-tsp-collection/v1"
    assert [i["name"] for i in tsp_manifest["instances"]] == list(EXPECTED_TSP)
    for inst in tsp_manifest["instances"]:
        path = REPO / inst["artifact_path"]
        assert path.parent == TSP_DIR and path.is_file(), inst["name"]  # a missing file is a failure, never a skip
        assert path.stat().st_size == inst["size_bytes"] and _sha(path) == inst["sha256"], inst["name"]
        assert inst["problem_type"] == "TSP" and isinstance(inst["published_optimum"], int)
        assert inst["provenance"]["kind"] in KINDS and SHA.match(inst["provenance"]["source_sha256"])


def test_tsp_manifest_has_no_absolute_path_and_provenance_is_complete(tsp_manifest):
    text = json.dumps(tsp_manifest)
    assert not re.search(r'[A-Za-z]:\\\\|"/(?:Users|home)', text), "absolute path in the manifest"
    for inst in tsp_manifest["instances"]:
        prov = inst["provenance"]
        if prov["kind"] == "db_reconstruction":
            assert prov["source_path"] is None
            assert prov["database"]["file"] == "tsplib.db" and SHA.match(prov["database"]["sha256"]) and prov["database"]["size_bytes"] > 0
            assert prov["table"] == "coordinates" and "select x, y from coordinates" in prov["query"]
            head = (REPO / inst["artifact_path"]).read_text(encoding="utf-8").splitlines()[:6]
            assert any(line.startswith("COMMENT") and "tsplib.db" in line for line in head), inst["name"]
        else:
            assert prov["source_path"] and not Path(prov["source_path"]).is_absolute(), inst["name"]
            assert prov["source_sha256"] == inst["sha256"], "a copy is byte-identical to its source"


def test_committed_tsp_files_reproduce_the_stage1_inputs_without_a_database(runner, tsp_manifest, stage1):
    """The gate: file sha256 (``tsp_file`` instances) or the canonical coordinate-text sha256 (``tsplib_db_coordinates``
    instances) equals the stage-1 manifest, and so do dimension, edge weight type and the distance-matrix hash."""
    from uniride_core.algorithms import tsplib_parser

    checked = 0
    for inst in tsp_manifest["instances"]:
        want = stage1["instances"][inst["name"]]
        path = REPO / inst["artifact_path"]
        data = tsplib_parser.parse_tsplib_text(path.read_text(encoding="utf-8"), inst["name"])
        assert data is not None, inst["name"]
        coords = data["coordinates"]
        fingerprint = runner.coordinate_text_sha256(coords)
        assert fingerprint == inst["coordinate_text_sha256"], inst["name"]
        if want["data_source"] == "tsp_file":
            assert inst["sha256"] == want["sha256"], f"{inst['name']}: file bytes differ from the stage-1 file"
        else:
            assert want["data_source"] == "tsplib_db_coordinates"
            assert fingerprint == want["sha256"], f"{inst['name']}: coordinates differ from the stage-1 coordinates"
        assert inst["dimension"] == len(coords) == want["n"], inst["name"]
        assert inst["edge_weight_type"] == data["edge_weight_type"] == want["edge_weight_type"], inst["name"]
        assert inst["published_optimum"] == want["published_optimum"], inst["name"]
        assert runner.matrix_sha256(runner.build_matrix(inst["edge_weight_type"], coords)) == want["matrix_sha256"], inst["name"]
        checked += 1
    assert checked == 16


def test_ft53_atsp_file_matches_the_stage1_hash(stage1):
    assert _sha(REPO / "academic_benchmark" / "tsplib_data" / "ft53.atsp") == stage1["instances"]["ft53"]["sha256"]


def test_gitattributes_keep_the_copied_files_byte_exact_and_gitignore_admits_only_the_tsp_folder():
    attrs = (REPO / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "academic_benchmark/tsplib_data/tsp/*.tsp -text" in attrs
    assert "academic_benchmark/tsplib_data/opt_tours/*.opt.tour -text" in attrs
    assert "academic_benchmark/tsplib_data/tsp/MANIFEST.json text eol=lf" in attrs
    assert "academic_benchmark/tsplib_data/opt_tours/MANIFEST.json text eol=lf" in attrs
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "!academic_benchmark/tsplib_data/tsp/*.tsp" in ignore
    assert [l for l in ignore if l.startswith("!") and ".tsp" in l] == ["!academic_benchmark/tsplib_data/tsp/*.tsp"]


# ---------------------------------------------------------------- the published tours
def test_tour_manifest_hashes_and_archive_provenance(tour_manifest):
    assert tour_manifest["schema_version"] == "uniride-opt-tour-collection/v1"
    assert tour_manifest["tour_convention"] == {"node_base": 1, "closed": True, "terminator": -1}
    archive = {e["archive_path"]: e["sha256"] for e in json.loads(ARCHIVE_MANIFEST.read_text(encoding="utf-8"))["entries"]}
    with_tour = [i for i in tour_manifest["instances"] if i["source"] != "none"]
    without = sorted(i["name"] for i in tour_manifest["instances"] if i["source"] == "none")
    assert without == sorted(NO_PUBLISHED_TOUR)
    assert len(with_tour) == 13
    for inst in with_tour:
        path = REPO / inst["artifact_path"]
        assert path.parent == TOUR_DIR and path.is_file(), inst["name"]
        assert _sha(path) == inst["sha256"] and path.stat().st_size == inst["size_bytes"], inst["name"]
        prov = inst["provenance"]
        assert prov["kind"] == "archive_copy" and inst["source"] == "archive_copy"
        assert archive[prov["archive_path"]] == prov["archive_entry_sha256"] == inst["sha256"], inst["name"]
    for inst in tour_manifest["instances"]:
        if inst["source"] == "none":
            assert "artifact_path" not in inst and "sha256" not in inst


def test_every_published_tour_is_a_hamiltonian_cycle_of_the_used_data_with_the_published_length(runner, inputs, tsp_manifest, tour_manifest):
    from uniride_core.algorithms import tsplib_parser

    count = 0
    for inst in tsp_manifest["instances"]:
        got = inputs.read_collection_tour(inst["name"], TOUR_DIR)
        entry = next(i for i in tour_manifest["instances"] if i["name"] == inst["name"])
        if entry["source"] == "none":
            assert got is None, inst["name"]
            continue
        nodes, source = got
        assert source == "opt_tour_file" and len(nodes) == inst["dimension"], inst["name"]
        coords = tsplib_parser.parse_tsplib_text((REPO / inst["artifact_path"]).read_text(encoding="utf-8"), inst["name"])["coordinates"]
        matrix = runner.build_matrix(inst["edge_weight_type"], coords)
        spec = runner.InstanceSpec(inst["name"], "TSP", inst["dimension"], inst["edge_weight_type"], inst["published_optimum"], "tsplib")
        assert runner.check_published_tour(spec, matrix, nodes) == [], inst["name"]
        count += 1
    assert count == 13


def test_a_tour_file_with_several_nodes_per_line_is_parsed(runner):
    """ulysses16.opt.tour keeps all nodes on one line; the reader must not stop at, or choke on, such a line."""
    text = "NAME : t\nTYPE : TOUR\nDIMENSION : 5\nTOUR_SECTION\n1 3 2\n5 4\n-1\nEOF\n"
    assert runner._parse_tour_file(text) == [1, 3, 2, 5, 4]
    assert runner._parse_tour_file("TOUR_SECTION\r\n1\r\n2\r\n-1\r\nEOF\r\n") == [1, 2]
    assert runner._parse_tour_file("TOUR_SECTION\n1 2 -1\nEOF\n") == [1, 2]


def test_the_collection_reader_refuses_a_tour_file_that_differs_from_its_manifest(inputs, tmp_path):
    (tmp_path / "x1.opt.tour").write_text("TOUR_SECTION\n1\n2\n-1\nEOF\n", encoding="utf-8", newline="")
    manifest = {"schema_version": "uniride-opt-tour-collection/v1", "instances": [
        {"name": "x1", "file_name": "x1.opt.tour", "source": "archive_copy", "sha256": "0" * 64}]}
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match="sha256"):
        inputs.read_collection_tour("x1", tmp_path)


def test_the_collection_reader_refuses_an_unknown_schema(inputs, tmp_path):
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"schema_version": "other/v9", "instances": []}), encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match="schema"):
        inputs.read_collection_tour("x1", tmp_path)
    with pytest.raises(inputs.InputRefused, match="schema"):
        inputs.read_tsp_file("x1", tmp_path)


# ---------------------------------------------------------------- archive refusal and the runner defaults
@pytest.mark.parametrize("path", [
    "archive/academic_benchmark/bildiri2026_legacy/bildiri2026/data/tsplib",
    "./archive/x",
    "academic_benchmark/../archive/x",
    "ARCHIVE/x",
])
def test_refuse_archive_path_catches_relative_traversal_and_case_variants(inputs, path):
    assert inputs.archive_refusal(REPO / path) and inputs.archive_refusal(Path(path))


def test_refuse_archive_path_admits_the_active_folders(inputs):
    assert inputs.archive_refusal(TSP_DIR) == "" and inputs.archive_refusal(TOUR_DIR) == ""
    assert inputs.archive_refusal(Path("academic_benchmark/tsplib_data/opt_tours")) == ""


def test_runner_defaults_are_the_active_manifest_governed_folders(runner):
    assert runner.OPT_TOUR_DIR == TOUR_DIR and runner.TSP_DIR == TSP_DIR
    args = runner.parse_args([])
    assert Path(args.opt_tour_dir) == TOUR_DIR and Path(args.tsp_dir) == TSP_DIR
    assert (TSP_DIR / "MANIFEST.json").is_file() and (TOUR_DIR / "MANIFEST.json").is_file()


@pytest.mark.parametrize("flag", ["--opt-tour-dir", "--tsp-dir", "--data-dir"])
def test_runner_refuses_an_archive_input_path_with_exit_2(runner, flag, capsys, tmp_path):
    archive_dir = REPO / "archive" / "academic_benchmark" / "bildiri2026_legacy" / "bildiri2026" / "data" / "tsplib"
    rc = runner.main([flag, str(archive_dir), "--out", str(tmp_path / "unused")])
    err = capsys.readouterr().err
    assert rc == 2 and "refused" in err and flag in err, err


def test_verify_tours_refuses_an_archive_tour_dir_with_exit_2(runner, capsys):
    archive_dir = REPO / "archive" / "academic_benchmark" / "bildiri2026_legacy"
    rc = runner.main(["--verify-tours", str(STAGE1), "--opt-tour-dir", str(archive_dir)])
    assert rc == 2 and "refused" in capsys.readouterr().err


def test_exact_runner_and_the_new_modules_contain_no_archive_path_string():
    pattern = re.compile(r"archive[/\\]|/\s*[\"']archive[\"']|[\"']archive[\"']\s*/|[\"']archive[\"']\s*,\s*[\"']")
    for path in (SCRIPT, INPUTS_MODULE):
        assert path.is_file(), path
        hits = [(n, line.strip()) for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
        assert not hits, f"{path.name}: {hits}"


# ---------------------------------------------------------------- --verify-tours needs no database
def test_verify_tours_of_the_committed_stage1_results_passes_without_a_database(runner, monkeypatch, capsys, tmp_path):
    def no_database(*args, **kwargs):
        raise AssertionError("the database must not be opened")

    monkeypatch.setattr(sqlite3, "connect", no_database)
    monkeypatch.setattr(runner.sqlite3, "connect", no_database)
    (tmp_path / "tsplib.db").write_bytes(b"this is not a database")  # a database in --data-dir must stay unread
    (tmp_path / "tsplib.db-wal").write_bytes(b"not empty")
    rc = runner.main(["--verify-tours", str(STAGE1), "--data-dir", str(tmp_path)])
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert "tours checked: 17; errors: 0" in out.out


def test_verify_tours_detects_a_tampered_tour_without_a_database(runner, tmp_path, capsys):
    doc = json.loads((STAGE1 / "tours.json").read_text(encoding="utf-8"))
    tour = doc["tours"]["eil51"]["tour"]
    tour[0], tour[1] = tour[1], tour[0]
    (tmp_path / "tours.json").write_text(json.dumps(doc), encoding="utf-8")
    rc = runner.main(["--verify-tours", str(tmp_path)])
    out = capsys.readouterr()
    assert rc == 1 and "eil51" in out.err


def test_load_instance_takes_the_committed_file_and_never_touches_the_database(runner, tsp_manifest, monkeypatch):
    inst = next(i for i in tsp_manifest["instances"] if i["name"] == "ulysses16")  # a rebuilt instance: no .tsp file existed before
    spec = runner.InstanceSpec("ulysses16", "TSP", inst["dimension"], inst["edge_weight_type"], inst["published_optimum"], "tsplib")
    matrix, coords, rec = runner.load_instance(spec, REPO / "academic_benchmark" / "tsplib_data", None, TOUR_DIR, TSP_DIR)
    assert rec["data_source"] == "tsp_file" and rec["file"] == inst["file_name"] and rec["sha256"] == inst["sha256"]
    assert rec["published_tour_check"] == {"source": "opt_tour_file", "tour_length": 6859, "equals_published_optimum": True}
    assert len(matrix) == 16 and len(coords) == 16


def test_load_instance_refuses_a_committed_file_that_differs_from_its_manifest(runner, inputs, tmp_path):
    (tmp_path / "tsp").mkdir()
    (tmp_path / "tsp" / "MANIFEST.json").write_text((TSP_DIR / "MANIFEST.json").read_text(encoding="utf-8"), encoding="utf-8")
    entry = json.loads((TSP_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["instances"][0]
    (tmp_path / "tsp" / entry["file_name"]).write_text("NAME : x\n", encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match="sha256"):
        inputs.read_tsp_file(entry["name"], tmp_path / "tsp")
