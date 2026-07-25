from pathlib import Path

from academic_benchmark.bildiri2026 import data_manager


def test_localize_tsplib_copies_from_explicit_source(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    local_data_dir = tmp_path / "data"
    local_tsplib_dir = local_data_dir / "tsplib"
    source_dir.mkdir()
    (source_dir / "sample.tsp").write_text("NAME: sample\nTYPE: TSP\n", encoding="utf-8")
    (source_dir / "ignore.txt").write_text("ignore\n", encoding="utf-8")

    monkeypatch.setattr(data_manager, "LOCAL_DATA_DIR", str(local_data_dir))
    monkeypatch.setattr(data_manager, "LOCAL_TSPLIB_DIR", str(local_tsplib_dir))

    copied = data_manager.localize_tsplib(source_dir=str(source_dir))

    assert copied == 1
    assert (local_tsplib_dir / "sample.tsp").read_text(encoding="utf-8").startswith("NAME")


def test_localize_tsplib_noops_when_local_data_already_exists(tmp_path, monkeypatch):
    local_data_dir = tmp_path / "data"
    local_tsplib_dir = local_data_dir / "tsplib"
    local_tsplib_dir.mkdir(parents=True)
    (local_tsplib_dir / "existing.tsp").write_text("NAME: existing\nTYPE: TSP\n", encoding="utf-8")

    monkeypatch.setattr(data_manager, "LOCAL_DATA_DIR", str(local_data_dir))
    monkeypatch.setattr(data_manager, "LOCAL_TSPLIB_DIR", str(local_tsplib_dir))
    monkeypatch.setattr(data_manager, "DEFAULT_TSPLIB_SOURCE_DIRS", (str(local_tsplib_dir),))

    copied = data_manager.localize_tsplib()

    assert copied == 0
    assert (local_tsplib_dir / "existing.tsp").exists()


def test_list_local_problems_includes_tsplib_and_time_matrices(tmp_path, monkeypatch):
    local_data_dir = tmp_path / "data"
    local_tsplib_dir = local_data_dir / "tsplib"
    local_tsplib_dir.mkdir(parents=True)
    (local_tsplib_dir / "berlin52.tsp").write_text("NAME: berlin52\nTYPE: TSP\n", encoding="utf-8")
    (local_data_dir / "campus_matrix.json").write_text("{}", encoding="utf-8")
    (local_data_dir / "tuned_parameters_db.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(data_manager, "LOCAL_DATA_DIR", str(local_data_dir))
    monkeypatch.setattr(data_manager, "LOCAL_TSPLIB_DIR", str(local_tsplib_dir))

    problems = data_manager.list_local_problems()

    assert {
        "type": "tsplib",
        "name": "berlin52",
        "path_relative": "data/tsplib/berlin52.tsp",
    } in problems
    assert {
        "type": "time_matrix",
        "name": "campus_matrix",
        "path_relative": "data/campus_matrix.json",
    } in problems


def test_active_academic_modules_do_not_reference_application_layer():
    forbidden = "optimizer" + "_api"
    root = Path(__file__).resolve().parents[1]
    offenders = []

    for path in root.rglob("*.py"):
        relative_parts = path.relative_to(root).parts
        if "__pycache__" in relative_parts or "archive_old" in relative_parts:
            continue
        text = path.read_text(encoding="utf-8")
        if forbidden in text:
            offenders.append(str(path.relative_to(root)))

    assert offenders == []
