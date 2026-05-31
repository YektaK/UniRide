from academic_benchmark.cvrplib_manager import (
    get_cvrp_problem_as_instance,
    get_cvrp_problems,
    import_cvrplib_text,
    import_solomon_text,
    load_cvrp_problem,
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
