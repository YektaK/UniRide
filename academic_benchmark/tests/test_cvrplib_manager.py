from academic_benchmark.cvrplib_manager import (
    get_cvrp_problem_as_instance,
    get_cvrp_problems,
    import_cvrp_paths,
    import_cvrplib_text,
    import_solomon_text,
    load_cvrp_problem,
    scan_cvrp_paths,
    summarize_cvrp_store,
)


CVRPLIB_TEXT = """
NAME : tiny-cvrp
TYPE : CVRP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 5
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
DEMAND_SECTION
1 0
2 2
3 3
DEPOT_SECTION
1
-1
EOF
"""


SOLOMON_TEXT = """
R101
VEHICLE
NUMBER     CAPACITY
2          10
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           1000      0
1         3        4        2       10          50        5
2         6        8        3       20          70        5
"""


def test_cvrplib_facade_uses_unified_storage(tmp_path):
    db_path = str(tmp_path / "academic.db")

    stored = import_cvrplib_text(CVRPLIB_TEXT, db_path=db_path)
    loaded = load_cvrp_problem("tiny-cvrp", db_path=db_path)
    rows = get_cvrp_problems(db_path=db_path)
    legacy = get_cvrp_problem_as_instance("tiny-cvrp", db_path=db_path)

    assert stored.problem_type == "cvrp"
    assert loaded.problem_type == "cvrp"
    assert len(rows) == 1
    assert rows[0]["name"] == "tiny-cvrp"
    assert legacy.problem_type == "cvrp"
    assert legacy.capacities == [5]


def test_solomon_facade_uses_unified_storage(tmp_path):
    db_path = str(tmp_path / "academic.db")

    stored = import_solomon_text(SOLOMON_TEXT, db_path=db_path)
    loaded = load_cvrp_problem("R101", db_path=db_path)
    rows = get_cvrp_problems(db_path=db_path)

    assert stored.problem_type == "cvrptw"
    assert loaded.problem_type == "cvrptw"
    assert loaded.constraints.time_windows == [(0, 1000), (10, 50), (20, 70)]
    assert [row["name"] for row in rows] == ["R101"]


def test_import_cvrp_paths_imports_supported_files_from_directory(tmp_path):
    db_path = str(tmp_path / "academic.db")
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "tiny-cvrp.vrp").write_text(CVRPLIB_TEXT, encoding="utf-8")
    (input_dir / "R101.txt").write_text(SOLOMON_TEXT, encoding="utf-8")
    (input_dir / "ignore.md").write_text("not a routing instance", encoding="utf-8")

    result = import_cvrp_paths([input_dir], db_path=db_path)

    assert result == {"imported": ["R101", "tiny-cvrp"], "skipped": ["ignore.md"]}
    rows = get_cvrp_problems(db_path=db_path)
    assert [row["problem_type"] for row in rows] == ["CVRPTW", "CVRP"]


def test_scan_cvrp_paths_reports_supported_and_skipped_files(tmp_path):
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "tiny-cvrp.vrp").write_text(CVRPLIB_TEXT, encoding="utf-8")
    (input_dir / "R101.vrptw").write_text(SOLOMON_TEXT, encoding="utf-8")
    (input_dir / "ignore.md").write_text("not a routing instance", encoding="utf-8")

    result = scan_cvrp_paths([input_dir])

    assert result["supported"] == [
        {"path": str(input_dir / "R101.vrptw"), "kind": "solomon"},
        {"path": str(input_dir / "tiny-cvrp.vrp"), "kind": "cvrplib"},
    ]
    assert result["skipped"] == [str(input_dir / "ignore.md")]
    assert result["missing"] == []


def test_import_cvrp_paths_supports_vrptw_solomon_extension(tmp_path):
    db_path = str(tmp_path / "academic.db")
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "R101.vrptw").write_text(SOLOMON_TEXT, encoding="utf-8")

    result = import_cvrp_paths([input_dir], db_path=db_path)

    assert result == {"imported": ["R101"], "skipped": []}
    assert load_cvrp_problem("R101", db_path=db_path).problem_type == "cvrptw"


def test_summarize_cvrp_store_counts_cvrp_and_cvrptw(tmp_path):
    db_path = str(tmp_path / "academic.db")
    import_cvrplib_text(CVRPLIB_TEXT, db_path=db_path)
    import_solomon_text(SOLOMON_TEXT, db_path=db_path)

    summary = summarize_cvrp_store(db_path=db_path)

    assert summary["total"] == 2
    assert summary["by_type"] == {"CVRP": 1, "CVRPTW": 1}
