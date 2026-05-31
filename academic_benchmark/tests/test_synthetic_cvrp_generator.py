from academic_benchmark.synthetic_cvrp_generator import (
    batch_generate_cvrp,
    generate_cvrp_from_coordinates,
    generate_cvrp_from_tsplib,
    generate_cvrptw_from_tsplib,
)
from academic_benchmark.tsplib_manager import load_routing_problem, store_routing_problem
from uniride_core.adapters.matrix_builder import MatrixBuilder


TSPLIB_TEXT = """
NAME : tiny-tsp
TYPE : TSP
DIMENSION : 4
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
4 9 12
EOF
"""


def test_generate_cvrp_from_coordinates_is_deterministic():
    coords = [(0, 0), (3, 4), (6, 8)]
    first = generate_cvrp_from_coordinates("synthetic", coords, seed=7)
    second = generate_cvrp_from_coordinates("synthetic", coords, seed=7)

    assert first.problem_type == "cvrp"
    assert first.constraints.demands == second.constraints.demands
    assert first.constraints.demands[0] == [0]
    assert first.constraints.capacities[0] >= max(d[0] for d in first.constraints.demands)
    assert first.matrix.values.shape == (3, 3)


def test_generate_cvrp_from_tsplib_stores_unified_problem(tmp_path):
    db_path = str(tmp_path / "synthetic.db")
    base = MatrixBuilder.from_tsplib_text(TSPLIB_TEXT)
    store_routing_problem(base, db_path=db_path)

    generated = generate_cvrp_from_tsplib("tiny-tsp", db_path=db_path, seed=11, store=True)
    loaded = load_routing_problem(generated.name, db_path=db_path)

    assert generated.problem_type == "cvrp"
    assert loaded.problem_type == "cvrp"
    assert loaded.constraints.demands == generated.constraints.demands
    assert loaded.constraints.capacities == generated.constraints.capacities


def test_generate_cvrptw_from_tsplib_stores_time_windows(tmp_path):
    db_path = str(tmp_path / "synthetic.db")
    base = MatrixBuilder.from_tsplib_text(TSPLIB_TEXT)
    store_routing_problem(base, db_path=db_path)

    generated = generate_cvrptw_from_tsplib(
        "tiny-tsp",
        db_path=db_path,
        seed=13,
        time_window_width=45,
        service_time=3,
        store=True,
    )
    loaded = load_routing_problem(generated.name, db_path=db_path)

    assert generated.problem_type == "cvrptw"
    assert generated.matrix.kind == "synthetic_travel_time"
    assert loaded.constraints.time_windows == generated.constraints.time_windows
    assert loaded.constraints.service_times == [0, 3, 3, 3]
    assert loaded.matrix.kind == "synthetic_travel_time"


def test_batch_generate_cvrp_can_include_cvrptw(tmp_path):
    db_path = str(tmp_path / "synthetic.db")
    store_routing_problem(MatrixBuilder.from_tsplib_text(TSPLIB_TEXT), db_path=db_path)

    generated = batch_generate_cvrp(
        ["tiny-tsp"],
        db_path=db_path,
        seed=17,
        include_cvrptw=True,
        store=False,
    )

    assert [problem.problem_type for problem in generated] == ["cvrp", "cvrptw"]
