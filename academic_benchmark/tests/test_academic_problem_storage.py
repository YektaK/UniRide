from academic_benchmark.tsplib_manager import (
    get_all_problems,
    get_distance_matrix,
    load_routing_problem,
    problem_row_to_instance,
    store_academic_text,
)


def test_store_and_load_cvrplib_problem(tmp_path):
    db_path = str(tmp_path / "academic.db")
    text = """
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

    stored = store_academic_text(text, "cvrplib", db_path=db_path)
    loaded = load_routing_problem("tiny-cvrp", db_path=db_path)
    rows = get_all_problems(db_path=db_path, max_dim=10, exclude_explicit=False)

    assert stored.problem_type == "cvrp"
    assert loaded.problem_type == "cvrp"
    assert loaded.constraints.demands == [[0], [2], [3]]
    assert loaded.constraints.capacities == [5]
    assert loaded.matrix.values[0, 1] == 5
    assert rows[0]["problem_type"] == "CVRP"
    assert rows[0]["demands"] == [[0], [2], [3]]
    assert rows[0]["capacities"] == [5]
    legacy = problem_row_to_instance(rows[0])
    assert legacy.problem_type == "cvrp"
    assert legacy.demands == [0, 2, 3]
    assert legacy.capacities == [5]


def test_store_and_load_solomon_problem(tmp_path):
    db_path = str(tmp_path / "academic.db")
    text = """
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

    stored = store_academic_text(text, "solomon", db_path=db_path)
    loaded = load_routing_problem("R101", db_path=db_path)
    matrix = get_distance_matrix("R101", db_path=db_path)

    assert stored.problem_type == "cvrptw"
    assert loaded.problem_type == "cvrptw"
    assert loaded.constraints.capacities == [10]
    assert loaded.constraints.time_windows == [(0, 1000), (10, 50), (20, 70)]
    assert loaded.constraints.service_times == [0, 5, 5]
    assert loaded.metadata["vehicles"] == 2
    assert matrix.shape == (3, 3)
    assert matrix[0, 1] == 5
