"""WP-E8 polish of the companion task: the shared verified read of ``exact_reference.inputs`` refuses archive locations,
manifest ``file_name``/``artifact_path`` cannot leave their folder or the dataset root, the runner no longer carries an
unmanifested tour reader, its help text names the archive rule, and a disagreement between the committed manifests and the
database specs blocks the normal runner path.

Nothing here opens the real ``tsplib.db``; the cross-check tests use a small fixture database in ``tmp_path``.
Archive-like folder names are built from components.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_exact_tsp_reference.py"
TSP_DIR = REPO / "academic_benchmark" / "tsplib_data" / "tsp"
REFUSED = "arch" + "ive"  # the refused path component, built from parts
TOUR_BODY = b"NAME : x1.opt.tour\nTYPE : TOUR\nDIMENSION : 2\nTOUR_SECTION\n1\n2\n-1\nEOF\n"


@pytest.fixture(scope="module")
def runner():
    spec = importlib.util.spec_from_file_location("run_exact_tsp_reference_confinement", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def inputs():
    from academic_benchmark.exact_reference import inputs as mod

    return mod


def _tour_collection(folder: Path, file_name: str = "x1.opt.tour", body: bytes = TOUR_BODY, *, write: bool = True) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    if write:
        (folder / file_name).write_bytes(body)
    manifest = {"schema_version": "uniride-opt-tour-collection/v1", "instances": [
        {"name": "x1", "file_name": file_name, "source": "archive_copy", "sha256": hashlib.sha256(body).hexdigest()}]}
    (folder / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


# ---------------------------------------------------------------- archive refusal inside the shared verified read
def test_the_shared_read_refuses_a_collection_below_an_archive_folder(inputs, tmp_path):
    folder = _tour_collection(tmp_path / REFUSED / "tours")
    with pytest.raises(inputs.InputRefused, match=REFUSED):
        inputs.read_collection_tour("x1", folder)
    ok = _tour_collection(tmp_path / "active" / "tours")  # same bytes, another location: read
    assert inputs.read_collection_tour("x1", ok) == ([1, 2], "opt_tour_file")


def test_the_shared_read_refuses_a_resolved_file_path_in_an_archive_folder(inputs, tmp_path):
    """The manifest is in an active folder; its file_name stays inside that folder but resolves into a sub-folder named
    like the archive: ``_verified_bytes`` applies the refusal to the resolved file path itself."""
    folder = tmp_path / "tours"
    (folder / REFUSED).mkdir(parents=True)
    (folder / REFUSED / "x1.opt.tour").write_bytes(TOUR_BODY)
    _tour_collection(folder, file_name=f"{REFUSED}/x1.opt.tour", write=False)
    with pytest.raises(inputs.InputRefused, match=REFUSED):
        inputs.read_collection_tour("x1", folder)


def test_the_tsp_reader_refuses_an_archive_location_too(inputs, tmp_path):
    folder = tmp_path / REFUSED / "tsp"
    folder.mkdir(parents=True)
    body = b"NAME : x\n"
    (folder / "x1.tsp").write_bytes(body)
    entry = {"name": "x1", "file_name": "x1.tsp", "sha256": hashlib.sha256(body).hexdigest()}
    (folder / "MANIFEST.json").write_text(json.dumps({"schema_version": "uniride-tsp-collection/v1", "instances": [entry]}),
                                          encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match=REFUSED):
        inputs.read_tsp_file("x1", folder)


# ---------------------------------------------------------------- confinement of manifest paths
@pytest.mark.parametrize("bad_name", ["../outside.opt.tour", "sub/../../outside.opt.tour", "/abs/outside.opt.tour",
                                      "C:/outside.opt.tour", ".."])
def test_manifest_file_name_cannot_leave_the_collection_folder(inputs, tmp_path, bad_name):
    (tmp_path / "outside.opt.tour").write_bytes(TOUR_BODY)  # exists and has the right sha: only the location is wrong
    folder = _tour_collection(tmp_path / "tours", file_name=bad_name, write=False)
    with pytest.raises(inputs.InputRefused, match="file_name"):
        inputs.read_collection_tour("x1", folder)


def test_tsp_manifest_file_name_cannot_leave_the_collection_folder(inputs, tmp_path):
    body = b"NAME : x\n"
    (tmp_path / "outside.tsp").write_bytes(body)
    folder = tmp_path / "tsp"
    folder.mkdir()
    entry = {"name": "x1", "file_name": "../outside.tsp", "sha256": hashlib.sha256(body).hexdigest()}
    (folder / "MANIFEST.json").write_text(json.dumps({"schema_version": "uniride-tsp-collection/v1", "instances": [entry]}),
                                          encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match="file_name"):
        inputs.read_tsp_file("x1", folder)


@pytest.mark.parametrize("artifact_path", [
    "academic_benchmark/tsplib_data/atsp/../../../README.md",  # normalises to a file outside the dataset root
    "../outside.atsp",
    "/abs/outside.atsp",
])
def test_atsp_artifact_path_must_stay_inside_the_dataset_root(inputs, tmp_path, artifact_path):
    manifest = {"schema_version": "uniride-atsp-collection/v1", "instances": [
        {"name": "x1", "artifact_path": artifact_path, "sha256": "0" * 64}]}
    path = tmp_path / "MANIFEST.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(inputs.InputRefused, match="artifact_path"):
        inputs.read_atsp_file("x1", path)


def test_the_committed_collections_are_still_read(inputs):
    """Regression guard for the confinement: every committed instance, tour and ft53 is read (CI: no skip)."""
    tsp_entries = json.loads((TSP_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["instances"]
    assert len(tsp_entries) == 16
    for inst in tsp_entries:
        assert inputs.read_tsp_file(inst["name"])[1]["sha256"] == inst["sha256"]
    tours = json.loads((REPO / "academic_benchmark" / "tsplib_data" / "opt_tours" / "MANIFEST.json").read_text(encoding="utf-8"))
    published = [t for t in tours["instances"] if t.get("source") != "none"]
    assert len(published) == 13
    for t in published:
        assert inputs.read_collection_tour(t["name"]) is not None
    text, entry = inputs.read_atsp_file("ft53")
    assert entry["name"] == "ft53" and "DIMENSION" in text


# ---------------------------------------------------------------- runner: (a) dead reader removed, (d) help text
def test_runner_has_no_database_or_unmanifested_tour_reader(runner):
    assert not hasattr(runner, "read_published_tour")
    source = SCRIPT.read_text(encoding="utf-8")
    assert "tour_nodes" not in source and "from opt_tours" not in source, "the runner reads no opt_tours table"


def test_help_text_says_that_any_archive_path_component_is_refused(runner, capsys):
    with pytest.raises(SystemExit):
        runner.parse_args(["--help"])
    text = " ".join(capsys.readouterr().out.split())
    assert text.count("any path component named archive") == 4, text


# ---------------------------------------------------------------- runner: (c) manifest versus database
def _fixture_db(path: Path, overrides=None) -> Path:
    """A ``problems`` table whose rows equal the committed manifests except ``overrides`` ({name: (dimension, optimal)}):
    a fixture stand-in for the read-only database, never the real file."""
    committed = {e["name"]: (e["dimension"], e["published_optimum"], e["edge_weight_type"])
                 for e in json.loads((TSP_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["instances"]}
    committed["ft53"] = (53, 6905, "EXPLICIT")
    conn = sqlite3.connect(path)
    conn.execute("create table problems (name text primary key, dimension integer not null, optimal integer, category text, "
                 "edge_weight_type text, problem_type text, source text)")
    for name in ("burma14", "ulysses16", "ft53"):
        dim, opt, ewt = committed[name]
        dim, opt = (overrides or {}).get(name, (dim, opt))
        conn.execute("insert into problems values (?,?,?,?,?,?,?)",
                     (name, dim, opt, "small", ewt, "ATSP" if name == "ft53" else "TSP", "tsplib"))
    conn.commit()
    conn.close()
    return path


def _specs(runner, db: Path):
    conn = runner.open_db_readonly(db)
    try:
        return runner.read_instance_set(conn)
    finally:
        conn.close()


def test_manifest_and_database_specs_agree_on_a_faithful_fixture(runner, tmp_path):
    specs = _specs(runner, _fixture_db(tmp_path / "tsplib.db"))
    assert {s.name for s in specs} == {"burma14", "ulysses16", "ft53"}
    assert runner.cross_check_manifest_specs(specs, runner.collection_specs(TSP_DIR)) == []


@pytest.mark.parametrize("override, expect", [
    ({"burma14": (14, 3324)}, "published_optimum 3323 differs from problems.optimal 3324"),
    ({"ulysses16": (17, 6859)}, "dimension 16 differs from problems.dimension 17"),
    ({"ft53": (53, 6906)}, "published_optimum 6905 differs from problems.optimal 6906"),
])
def test_a_disagreement_between_manifest_and_database_blocks_the_normal_runner_path(runner, tmp_path, capsys, override, expect):
    data = tmp_path / "data"
    data.mkdir()
    _fixture_db(data / "tsplib.db", override)
    out = tmp_path / "results-unused"
    args = runner.parse_args(["--data-dir", str(data), "--out", str(out), "--instances", "burma14,ulysses16,ft53"])
    rc = runner._run(args, out, "0" * 40, False, None, None)  # compares before any solver is touched: sessions stay None
    err = " ".join(capsys.readouterr().err.split())
    assert rc == 2 and "refused" in err and expect in err, err
    assert not out.exists(), "nothing is written when the inputs disagree"


def test_agreeing_manifest_and_database_reach_instance_loading_and_the_first_solve(runner, tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    data.mkdir()
    _fixture_db(data / "tsplib.db")
    out = tmp_path / "results-unused"
    args = runner.parse_args(["--data-dir", str(data), "--out", str(out), "--instances", "burma14,ulysses16,ft53"])

    class ReachedSolve(Exception):
        pass

    def stop(*a, **k):
        raise ReachedSolve

    monkeypatch.setattr(runner, "evaluate_instance", stop)  # every instance loaded without refusal; the solve is not run
    with pytest.raises(ReachedSolve):
        runner._run(args, out, "0" * 40, False, None, None)
    assert "refused" not in capsys.readouterr().err
