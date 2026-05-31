from collections import Counter

from academic_benchmark.seed_smoke_datasets import seed_smoke_datasets
from academic_benchmark.tsplib_manager import get_all_problems, load_routing_problem


def test_seed_smoke_datasets_populates_all_problem_types(tmp_path):
    db_path = str(tmp_path / "academic.db")

    result = seed_smoke_datasets(db_path=db_path)
    rows = get_all_problems(db_path=db_path, max_dim=100, exclude_explicit=False)
    counts = Counter(row["problem_type"] for row in rows)

    assert set(result["stored"]) == {
        "smoke-tsp",
        "smoke-atsp",
        "smoke-cvrp",
        "smoke-solomon",
        "smoke-uniride",
    }
    assert counts["TSP"] == 1
    assert counts["ATSP"] == 1
    assert counts["CVRP"] == 1
    assert counts["CVRPTW"] == 1
    assert counts["UNIRIDE"] == 1

    uniride = load_routing_problem("smoke-uniride", db_path=db_path)
    assert uniride.problem_type == "uniride"
    assert uniride.matrix.kind == "travel_time"
    assert uniride.matrix.is_asymmetric is True
    assert uniride.constraints.capacities == [1, 2]
    assert uniride.constraints.demands == [[0, 0], [1, 0], [0, 1], [0, 1]]


def test_seed_smoke_datasets_is_idempotent(tmp_path):
    db_path = str(tmp_path / "academic.db")

    first = seed_smoke_datasets(db_path=db_path)
    second = seed_smoke_datasets(db_path=db_path)
    rows = get_all_problems(db_path=db_path, max_dim=100, exclude_explicit=False)

    assert len(first["stored"]) == 5
    assert second["stored"] == []
    assert set(second["skipped"]) == set(first["stored"])
    assert len(rows) == 5
