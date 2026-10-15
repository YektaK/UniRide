"""M18 follow-up (DECISION_LOG A14): cli_engine rounding and int() truncation.

Site groups:
  D  cli_engine.run_single_test_with_matrix: time-matrix branch rounded to 2 dp,
     non-time branch truncated with int().
  E  registry_setup legacy executor: int() truncation on a fractional distance
     matrix (the time-matrix branch is covered in the sibling test module).
  F  cli_engine._execute_benchmark_tasks: avg_length / objective_cost rounded to
     4 dp before the CSV write and save_benchmark_result.
Integer instances (TSPLIB) must keep identical int values.
"""
from __future__ import annotations

import csv
import itertools
from types import SimpleNamespace

import numpy as np
import pytest

from academic_benchmark import cli_engine
from academic_benchmark.core import registry_setup  # noqa: F401 - registration
from academic_benchmark.engine_core import AlgorithmRegistry
from uniride_core.algorithms.local_search_numba import LocalSearchType
from uniride_core.models import ProblemInstance

N = 6


def _fractional(n: int = N) -> list[list[float]]:
    return [
        [
            0.0 if i == j else ((i + 1) * 1.1237 + (j + 1) * 0.3141 + (i * j % 5) * 0.00713)
            for j in range(n)
        ]
        for i in range(n)
    ]


def _integer(n: int = N) -> list[list[int]]:
    return [
        [0 if i == j else (i + 1) * 11 + (j + 1) * 3 + (i * j % 5) for j in range(n)]
        for i in range(n)
    ]


def _all_cycle_costs(matrix) -> list[float]:
    n = len(matrix)
    costs = []
    for perm in itertools.permutations(range(1, n)):
        route = (0, *perm)
        costs.append(sum(float(matrix[route[i]][route[(i + 1) % n]]) for i in range(n)))
    return costs


def _is_some_cycle_cost(value: float, matrix) -> bool:
    return any(abs(value - c) <= 1e-9 for c in _all_cycle_costs(matrix))


def test_fixture_cycle_costs_are_not_two_decimal_exact() -> None:
    # Guards the fixture: otherwise rounding would be invisible.
    assert all(abs(c - round(c, 2)) > 1e-6 for c in _all_cycle_costs(_fractional()))


def _matrix_run(matrix, *, is_time_matrix: bool):
    problem = SimpleNamespace(dimension=len(matrix), is_time_matrix=is_time_matrix, optimal=10.0)
    return cli_engine.run_single_test_with_matrix(
        problem, LocalSearchType.TWO_OPT, 5, {"max_iterations": 30}, matrix
    )


# -- Group D: cli_engine.py:631 ------------------------------------------------

def test_cli_time_matrix_branch_reports_unrounded_cost() -> None:
    matrix = _fractional()
    result = _matrix_run(matrix, is_time_matrix=True)
    assert _is_some_cycle_cost(result["tour_length"], matrix)


def test_cli_non_time_branch_does_not_truncate_fractional_matrix() -> None:
    matrix = _fractional()
    result = _matrix_run(matrix, is_time_matrix=False)
    assert _is_some_cycle_cost(result["tour_length"], matrix)


def test_cli_integer_instance_keeps_identical_int_value() -> None:
    matrix = _integer()
    for is_tm in (False, True):
        result = _matrix_run(matrix, is_time_matrix=is_tm)
        assert _is_some_cycle_cost(result["tour_length"], matrix)
    result = _matrix_run(matrix, is_time_matrix=False)
    assert isinstance(result["tour_length"], int)
    assert result["tour_length"] == int(result["tour_length"])


# -- Group E: registry_setup.py:431 (int() truncation) -------------------------

def _dist_problem(matrix) -> ProblemInstance:
    return ProblemInstance(
        name="m18-trunc", dimension=len(matrix), coordinates=[], optimal=10.0,
        problem_type="atsp", dist_matrix=matrix,
    )


@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_legacy_executor_does_not_truncate_fractional_distance_matrix(algorithm: str) -> None:
    matrix = _fractional()
    result = AlgorithmRegistry.get_executor(algorithm)(
        _dist_problem(matrix), {"max_iterations": 30}, 7, 0
    )
    route = [n - 1 for n in result.tour]
    independent = sum(matrix[route[i]][route[(i + 1) % N]] for i in range(N))
    assert abs(result.tour_cost - independent) <= 1e-9
    assert abs(result.objective_cost - independent) <= 1e-9
    assert result.matrix_kind == "distance"


@pytest.mark.parametrize("algorithm", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_legacy_executor_integer_distance_instance_stays_int(algorithm: str) -> None:
    for matrix in (_integer(), np.array(_integer(), dtype=np.int32)):
        problem = _dist_problem(matrix)
        result = AlgorithmRegistry.get_executor(algorithm)(problem, {"max_iterations": 30}, 7, 0)
        route = [n - 1 for n in result.tour]
        independent = sum(int(matrix[route[i]][route[(i + 1) % N]]) for i in range(N))
        assert isinstance(result.tour_cost, int)
        assert result.tour_cost == independent
        assert result.objective_cost == independent


# -- Group F: cli_engine.py:1456-1465 -----------------------------------------

def test_benchmark_rows_and_db_store_unrounded_costs(tmp_path, monkeypatch) -> None:
    from academic_benchmark import tsplib_manager

    avg = 40.286919999999995
    objective = 40.28691999999
    fake_result = {
        "problem": "p", "strategy": "s", "avg_length": avg, "avg_gap": 1.23456789,
        "avg_time_ms": 12.3456789, "n_runs": 1, "params": {},
        "objective_cost": objective, "optimal": 10.0,
    }
    saved: list[dict] = []

    def fake_run_pool(tasks, workers, on_result=None):
        for index, result in enumerate([fake_result]):
            on_result(index, result, 1)
        return [fake_result]

    monkeypatch.setattr(cli_engine, "_run_pool", fake_run_pool)
    monkeypatch.setattr(cli_engine, "RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(cli_engine, "METADATA_PATH", str(tmp_path / "meta.json"))
    monkeypatch.setattr(cli_engine, "TSPLIB_DB", str(tmp_path / "none.db"))
    monkeypatch.setattr(tsplib_manager, "save_benchmark_run", lambda *a, **k: None)
    monkeypatch.setattr(
        tsplib_manager, "save_benchmark_result", lambda run_id, payload, **k: saved.append(payload)
    )

    rows = cli_engine._execute_benchmark_tasks([("task",)], 1, {}, "BENCH")

    assert rows[0]["avg_length"] == avg
    assert rows[0]["objective_cost"] == objective
    assert saved[0]["tour_cost"] == avg
    assert saved[0]["objective_cost"] == objective
    with open(tmp_path / "benchmark_progress.csv", newline="", encoding="utf-8") as handle:
        written = next(csv.DictReader(handle))
    assert float(written["avg_length"]) == avg
    assert float(written["objective_cost"]) == objective
