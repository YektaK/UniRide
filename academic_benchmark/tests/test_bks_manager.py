import json

from academic_benchmark.bks_manager import (
    apply_bks_from_solution_dirs,
    parse_cvrplib_solution_text,
    parse_routes,
    parse_solomon_solution_text,
)
from academic_benchmark.cvrplib_manager import import_cvrplib_text, import_solomon_text
from academic_benchmark.tests.test_cvrplib_manager import CVRPLIB_TEXT, SOLOMON_TEXT
from academic_benchmark.tsplib_manager import get_db, load_routing_problem


def test_parse_cvrplib_solution_text_reads_cost_and_routes():
    record = parse_cvrplib_solution_text(
        """
Route #1: 2
Route #2: 3
Cost 123.45
""",
        problem_name="tiny-cvrp",
    )

    assert record.problem_name == "tiny-cvrp"
    assert record.cost == 123.45
    assert record.vehicles == 2
    assert record.routes == [[2], [3]]


def test_parse_solomon_solution_text_computes_cost_from_stored_matrix(tmp_path):
    db_path = str(tmp_path / "academic.db")
    import_solomon_text(SOLOMON_TEXT, db_path=db_path)

    record = parse_solomon_solution_text(
        """
Solution
Route 1 : 1 2
""",
        problem_name="R101",
        db_path=db_path,
    )

    assert record.problem_name == "R101"
    assert record.vehicles == 1
    assert record.routes == [[1, 2]]
    assert record.cost == 20.0


def test_apply_bks_from_solution_dirs_updates_problem_optimal_and_metadata(tmp_path):
    db_path = str(tmp_path / "academic.db")
    import_cvrplib_text(CVRPLIB_TEXT, db_path=db_path)
    import_solomon_text(SOLOMON_TEXT, db_path=db_path)
    cvrp_dir = tmp_path / "cvrp_solutions"
    solomon_dir = tmp_path / "solomon_solutions"
    cvrp_dir.mkdir()
    solomon_dir.mkdir()
    (cvrp_dir / "tiny-cvrp.sol").write_text("Route #1: 2 3\nCost 42\n", encoding="utf-8")
    (solomon_dir / "r101.txt").write_text("Route 1 : 1 2\n", encoding="utf-8")

    result = apply_bks_from_solution_dirs(
        cvrplib_solution_dir=str(cvrp_dir),
        solomon_solution_dir=str(solomon_dir),
        db_path=db_path,
    )

    assert result["updated_count"] == 2
    assert result["skipped"] == []
    assert load_routing_problem("tiny-cvrp", db_path=db_path).optimal == 42.0
    assert load_routing_problem("R101", db_path=db_path).optimal == 20.0

    conn = get_db(db_path)
    row = conn.execute(
        "SELECT metadata_json FROM routing_constraints WHERE problem_name=?",
        ("R101",),
    ).fetchone()
    conn.close()
    metadata = json.loads(row["metadata_json"])
    assert metadata["bks_cost"] == 20.0
    assert metadata["bks_vehicles"] == 1


def test_parse_routes_accepts_cvrplib_and_solomon_route_prefixes():
    assert parse_routes("Route #1: 2 3\nRoute 2 : 004 005") == [[2, 3], [4, 5]]
