from types import SimpleNamespace

from optimizer_api.routers import benchmark
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem
import numpy as np
import pytest


def test_load_benchmark_problem_preserves_academic_problem_metadata(monkeypatch):
    info = SimpleNamespace(
        name="tiny-cvrptw",
        dimension=3,
        coordinates=[],
        optimal=42,
        category="small",
        source="solomon",
        problem_type="CVRPTW",
        is_time_matrix=True,
        time_matrix=[[0, 5, 9], [6, 0, 4], [8, 3, 0]],
        dist_matrix=None,
        edge_weight_type="EXPLICIT",
        capacity=10,
        capacities=[10],
        demands=[0, 2, 3],
        service_times=[0, 5, 5],
        num_vehicles=2,
        max_route_duration=120,
        matrix_kind="travel_time",
        direction="pickup",
        time_windows=[(0, 1000), (10, 50), (20, 70)],
        depot_index=0,
        file_path="tiny.sol",
    )
    monkeypatch.setattr(benchmark, "get_problem_by_name", lambda name: info)
    monkeypatch.setattr(benchmark, "load_problem_coordinates", lambda name: [(0, 0), (3, 4), (6, 8)])

    problem = benchmark._load_benchmark_problem("tiny-cvrptw")

    assert problem is not None
    assert problem.problem_type == "cvrptw"
    assert problem.source == "solomon"
    assert problem.coordinates == [(0, 0), (3, 4), (6, 8)]
    assert problem.time_matrix == [[0, 5, 9], [6, 0, 4], [8, 3, 0]]
    assert problem.capacity == 10
    assert problem.capacities == [10]
    assert problem.demands == [0, 2, 3]
    assert problem.time_windows == [(0, 1000), (10, 50), (20, 70)]


def test_load_benchmark_problem_rejects_instances_without_coordinates(monkeypatch):
    info = SimpleNamespace(
        name="matrix-only",
        dimension=3,
        coordinates=[],
        optimal=None,
        category="small",
        problem_type="ATSP",
        file_path="matrix-only.atsp",
        dist_matrix=[[0, 1, 9], [4, 0, 2], [3, 8, 0]],
        time_matrix=None,
    )
    monkeypatch.setattr(benchmark, "get_problem_by_name", lambda name: info)
    monkeypatch.setattr(benchmark, "load_problem_coordinates", lambda name: None)

    assert benchmark._load_benchmark_problem("matrix-only") is None


def test_convert_cli_record_to_web_preserves_routing_fields():
    converted = benchmark._convert_cli_record_to_web(
        {
            "strategy": "Core-Greedy-Routing",
            "problem": "tiny-cvrptw",
            "dimension": 3,
            "avg_length": 40.0,
            "avg_gap": 0.0,
            "avg_time_ms": 12.0,
            "n_runs": 1,
            "problem_type": "cvrptw",
            "matrix_kind": "distance",
            "objective_cost": 40.0,
            "num_vehicles": 1,
            "capacity_violations": 0,
            "tw_violations": 1,
            "routes_json": "[[1, 2]]",
        }
    )

    assert converted["metadata"]["problem_type"] == "cvrptw"
    assert converted["metadata"]["matrix_kind"] == "distance"
    assert converted["metadata"]["vehicles_used"] == 1
    assert converted["metadata"]["routes"] == [[1, 2]]
    assert converted["metadata"]["tw_violations"] == 1


def test_academic_problems_endpoint_returns_reader_payload(monkeypatch):
    monkeypatch.setattr(
        "academic_benchmark.results_reader.get_academic_problems",
        lambda **kwargs: {"source": "academic_db", "count": 1, "results": [{"name": "tiny"}], "kwargs": kwargs},
    )

    result = benchmark.get_academic_problems(problem_type="cvrp", category="synthetic", max_dim=10, limit=5)

    assert result["source"] == "academic_db"
    assert result["count"] == 1
    assert result["kwargs"] == {
        "problem_type": "cvrp",
        "category": "synthetic",
        "max_dim": 10,
        "limit": 5,
    }


def test_academic_problems_endpoint_direct_call_resolves_query_defaults(monkeypatch):
    captured = {}

    def fake_get_problems(**kwargs):
        captured.update(kwargs)
        return {"source": "academic_db", "count": 1, "results": [{"name": "tiny-cvrp"}]}

    monkeypatch.setattr("academic_benchmark.results_reader.get_academic_problems", fake_get_problems)

    result = benchmark.get_academic_problems(problem_type="cvrp", max_dim=10)

    assert result["source"] == "academic_db"
    assert captured == {
        "problem_type": "cvrp",
        "category": None,
        "max_dim": 10,
        "limit": 1000,
    }


def test_academic_benchmark_results_endpoint_uses_results_reader(monkeypatch):
    monkeypatch.setattr(
        "academic_benchmark.results_reader.get_benchmark_rows",
        lambda limit=100, feasible_only=False: {
            "source": "academic_csv",
            "count": 1,
            "limit": limit,
            "feasible_only": feasible_only,
            "results": [],
        },
    )

    result = benchmark.get_academic_benchmark_results(limit=5, feasible_only=True)

    assert result["source"] == "academic_csv"
    assert result["limit"] == 5
    assert result["feasible_only"] is True


def test_academic_benchmark_results_endpoint_direct_call_resolves_query_default(monkeypatch):
    monkeypatch.setattr(
        "academic_benchmark.results_reader.get_benchmark_rows",
        lambda limit=100, feasible_only=False: {
            "source": "academic_db",
            "count": 0,
            "limit": limit,
            "feasible_only": feasible_only,
            "results": [],
        },
    )

    result = benchmark.get_academic_benchmark_results()

    assert result["source"] == "academic_db"
    assert result["limit"] == 100
    assert result["feasible_only"] is False


def test_matrix_native_benchmark_run_executes_and_persists(monkeypatch):
    class ImmediateThread:
        def __init__(self, target, daemon=True, name=None):
            self.target = target

        def start(self):
            self.target()

    saved_runs = []
    saved_results = []
    problem = RoutingProblem(
        name="tiny-cvrp",
        problem_type="cvrp",
        matrix=CostMatrix(np.array([[0, 5, 6], [5, 0, 1], [6, 1, 0]], dtype=float)),
        constraints=ConstraintProfile(demands=[[0], [1], [1]], capacities=[2]),
    )

    monkeypatch.setattr(benchmark.threading, "Thread", ImmediateThread)
    monkeypatch.setattr("academic_benchmark.tsplib_manager.load_routing_problem", lambda name: problem)
    monkeypatch.setattr("academic_benchmark.tsplib_manager.save_benchmark_run", lambda *args, **kwargs: saved_runs.append((args, kwargs)) or args[0])
    monkeypatch.setattr("academic_benchmark.tsplib_manager.save_benchmark_result", lambda *args, **kwargs: saved_results.append((args, kwargs)) or 1)

    run_id = "matrix-native-test"
    result = benchmark._start_benchmark_impl(
        run_id,
        algorithms=[{"id": "Core-Greedy-Routing", "params": {}}],
        problems=["tiny-cvrp"],
        settings={"execution_mode": "matrix_native", "n_runs": 1, "seed": 7},
    )
    state = benchmark.benchmark_state_manager.get_run(run_id)

    assert result["execution_mode"] == "matrix_native"
    assert state.status.value == "completed"
    assert state.results_count == 1
    assert saved_results[0][1] == {}
    assert saved_results[0][0][0] == run_id
    assert saved_results[0][0][1]["problem_type"] == "cvrp"
    assert saved_results[0][0][1]["routes"]
    assert saved_runs[-1][1]["status"] == "completed"


@pytest.mark.parametrize(
    ("algorithm", "params"),
    [
        ("Core-TwoOpt-TSP", {"max_iterations": 12}),
        (
            "Core-GA-TSP",
            {
                "population_size": 8,
                "max_iterations": 5,
                "crossover_rate": 0.8,
                "mutation_rate": 0.2,
                "elite_count": 2,
                "tournament_size": 3,
                "max_no_improvement": 4,
            },
        ),
        (
            "Core-PSO-TSP",
            {
                "num_particles": 8,
                "max_iterations": 5,
                "cognitive_weight": 1.2,
                "social_weight": 1.2,
                "inertia_weight": 0.7,
                "max_velocity_size": 3,
                "local_search_rate": 0.0,
            },
        ),
        (
            "Core-GWO-TSP",
            {
                "num_wolves": 8,
                "max_iterations": 5,
                "a_initial": 2.0,
                "local_search_rate": 0.0,
            },
        ),
        (
            "Core-HHO-TSP",
            {
                "num_hawks": 8,
                "max_iterations": 5,
                "escape_energy_factor": 2.0,
                "jump_probability": 0.5,
                "levy_beta": 1.5,
                "local_search_rate": 0.0,
            },
        ),
    ],
)
def test_matrix_native_benchmark_run_accepts_core_tsp_engines(monkeypatch, algorithm, params):
    class ImmediateThread:
        def __init__(self, target, daemon=True, name=None):
            self.target = target

        def start(self):
            self.target()

    saved_runs = []
    saved_results = []
    problem = RoutingProblem(
        name="tiny-tsp",
        problem_type="tsp",
        matrix=CostMatrix(np.array([[0, 1, 2, 1], [1, 0, 1, 2], [2, 1, 0, 1], [1, 2, 1, 0]], dtype=float)),
        optimal=4.0,
    )

    monkeypatch.setattr(benchmark.threading, "Thread", ImmediateThread)
    monkeypatch.setattr("academic_benchmark.tsplib_manager.load_routing_problem", lambda name: problem)
    monkeypatch.setattr("academic_benchmark.tsplib_manager.save_benchmark_run", lambda *args, **kwargs: saved_runs.append((args, kwargs)) or args[0])
    monkeypatch.setattr("academic_benchmark.tsplib_manager.save_benchmark_result", lambda *args, **kwargs: saved_results.append((args, kwargs)) or 1)

    run_id = f"matrix-native-{algorithm.lower()}-test"
    result = benchmark._start_benchmark_impl(
        run_id,
        algorithms=[{"id": algorithm, "params": params}],
        problems=["tiny-tsp"],
        settings={"execution_mode": "matrix_native", "n_runs": 1, "seed": 7},
    )
    state = benchmark.benchmark_state_manager.get_run(run_id)

    assert result["execution_mode"] == "matrix_native"
    assert state.status.value == "completed"
    assert saved_results[0][0][1]["algorithm"] == algorithm
    assert saved_results[0][0][1]["problem_type"] == "tsp"
    assert saved_results[0][0][1]["tour"]
    assert saved_runs[-1][1]["status"] == "completed"
