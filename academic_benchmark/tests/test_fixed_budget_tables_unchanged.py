"""Byte-identity baseline for the fixed-budget and native-termination output tables (WP-E8 Task 1).

``fixtures/fixed_budget_tables_golden_v1.json`` was captured once at the WP-E8 base commit (0626517d), before any
production file changed, with ``capture_golden`` below (never hand-edited). Every WP-E8 change must leave these
outputs byte-identical: the fixed-budget pilot (``fair_pilot.run_fair_pilot``: manifest, runs, aggregate and
validation files), the native-termination pilot (``native_pilot.run_native_pilot``, real deterministic executors),
``matrix_run_summary.summarize_benchmark_rows`` and the ``results_reader`` accessors.

Only time-dependent values are pinned: elapsed time (1.0 ms through a counter replacing ``time`` in ``fair_pilot``),
git/environment metadata (constants) and database timestamps (dropped by ``_strip_volatile``).

The fair-pilot stub was later changed to ``runs: 3`` (WP-E8 polish item 5: with two runs the mean of the varying costs is a
multiple of 0.5, so a 2-dp rounding of ``mean_cost`` was invisible) and the fixture regenerated with ``capture_golden`` from
fixed-budget/native modules identical to commit f53d5ed1; only the ``fair_pilot`` part of the fixture changed.

The test also pins the sha256 of the committed exact result files and of the Bildiri study profile, so a rewrite of
committed evidence is detected.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from academic_benchmark import fair_pilot, native_pilot
from academic_benchmark.core.preflight import RuntimeBackendAvailability
from academic_benchmark.fair_pilot import APPROVED_ALGORITHMS, run_fair_pilot
from academic_benchmark.fairness import FairComparisonManifest, FairRunResult
from academic_benchmark.matrix_run_summary import make_json_ready, summarize_benchmark_rows
from academic_benchmark.native_pilot import run_native_pilot
from academic_benchmark.native_protocol import (
    APPROVED_NATIVE_ALGORITHMS,
    NATIVE_PROTOCOL,
    NATIVE_TERMINATION_REGIME,
)
from academic_benchmark.results_reader import get_benchmark_rows, get_best_result, get_leaderboard
from academic_benchmark.tsplib_manager import get_db, init_db, save_benchmark_result, save_benchmark_run, save_best_solution
from uniride_core.algorithms.capabilities import BackendKind, ExecutionBackendProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "fixed_budget_tables_golden_v1.json"
RUNTIME = RuntimeBackendAvailability(True, True, "deterministic golden fixture")
_VOLATILE_KEYS = {"created_at", "updated_at", "timestamp", "started_at", "finished_at", "created", "updated", "ts", "time"}

# sha256 of committed exact evidence, captured at the base commit. The exact result trees are ``-text`` in
# .gitattributes, so their raw bytes are pinned; ``study.json`` has no attribute (a Windows checkout with
# core.autocrlf holds CRLF), so its bytes are pinned after a CRLF -> LF normalisation.
PINNED_FILES = {
    "docs/paper/results/tsplib-exact-reference/stage1-verification/README.md": "raw",
    "docs/paper/results/tsplib-exact-reference/stage1-verification/manifest.json": "raw",
    "docs/paper/results/tsplib-exact-reference/stage1-verification/reference.csv": "raw",
    "docs/paper/results/tsplib-exact-reference/stage1-verification/tours.json": "raw",
    "docs/paper/results/week-2026-10-05-exact/wp-e3-goal1-single/exact_manifest.json": "raw",
    "docs/paper/results/week-2026-10-05-exact/wp-e4a-typed-options/exact_manifest.json": "raw",
    "academic_benchmark/studies/bildiri2026/study.json": "lf",
}


def _pinned_sha(rel: str) -> str:
    data = (REPO_ROOT / rel).read_bytes()
    if PINNED_FILES[rel] == "lf":
        data = data.replace(bytes([13, 10]), bytes([10]))
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------------------ fixed-budget stubs
@dataclass
class _FairProblem:
    name: str
    problem_type: str
    dist_matrix: list
    optimal: float
    dimension: int = 4
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False


_ALNS_PARAMS = {
    "max_iterations": 8, "max_no_improvement": 3, "remove_ratio": 0.34, "min_remove": 1, "segment_length": 2,
    "weight_update_factor": 0.2, "use_sa": True, "sa_start_temp": 4.0, "sa_cooling_rate": 0.9,
}


def _fair_problems() -> list:
    return [
        _FairProblem("tiny-tsp", "tsp", [[0, 2, 7, 4], [2, 0, 5, 6], [7, 5, 0, 7], [4, 6, 7, 0]], 18),
        _FairProblem("tiny-atsp", "atsp", [[0, 2, 8, 9], [6, 0, 3, 8], [4, 7, 0, 5], [9, 1, 6, 0]], 19),
    ]


def _fair_registry(algorithm_id: str):
    family = {"Core-GWO-TSP-Pure": "GWO", "Core-HHO-TSP-Pure": "HHO", "Core-TwoOpt-TSP": "2-opt",
              "Core-ThreeOpt-TSP": "3-opt", "ALNS-TSP": "ALNS"}[algorithm_id]

    def execute(problem, params, seed, run_idx):
        manifest = FairComparisonManifest.from_value(params["fair_comparison"])
        tour = [[1, 2, 3, 4], [1, 3, 2, 4], [1, 2, 4, 3]][(run_idx + len(algorithm_id)) % 3]  # costs vary by run and algorithm, so means, medians and gaps are not integers
        cost = float(sum(problem.dist_matrix[tour[i] - 1][tour[(i + 1) % 4] - 1] for i in range(4)))
        return FairRunResult(
            problem=problem.name, algorithm=algorithm_id, algorithm_id=algorithm_id, algorithm_family=family,
            variant="pure", run=run_idx, seed=seed, seed_group=manifest.seed_group(problem.name, run_idx), dimension=4,
            optimal=problem.optimal, tour_cost=cost, objective_cost=cost,
            gap_pct=((cost - problem.optimal) / problem.optimal) * 100, elapsed_sec=0.001, iterations=2, evaluations=5,
            objective_evaluations=5, evaluation_budget=manifest.evaluation_budget, budget_terminated=False, tour=tour,
            initialization_policy="paired_seed_random_permutation_all_nodes", termination_policy="atomic_upper_bound_v1",
            execution_backend=("numba-objective" if family in {"GWO", "HHO"} else "python-canonical-matrix"),
            polish_policy={"enabled": False, "initial": False, "periodic": False, "final": False, "operator": None},
        )

    return execute


def _fair_gateway(**kwargs: Any):
    algorithm_id = kwargs["requested_algorithm_id"]
    result = kwargs["registry_getter"](algorithm_id)(kwargs["problem"], kwargs["params"], kwargs["seed"], kwargs["run_idx"])
    backend = BackendKind.NUMBA_NOPYTHON if algorithm_id in {"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"} else BackendKind.PYTHON
    decision = SimpleNamespace(
        resolution=SimpleNamespace(requested_id=algorithm_id, canonical_id=algorithm_id),
        backend_policy=kwargs["backend_policy"], selected_backend=ExecutionBackendProfile(backend), fallback_reason=None,
        executor_registry_id=algorithm_id, evidence_ids=(f"fixture::{algorithm_id}",),
    )
    return result, decision


# ------------------------------------------------------------------------------------------ native fixtures
@dataclass
class _NativeProblem:
    name: str
    dist_matrix: list
    problem_type: str
    optimal: float = 1.0
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


_SYMMETRIC = [[0, 3, 8, 7, 6, 4], [3, 0, 5, 9, 3, 7], [8, 5, 0, 4, 8, 6], [7, 9, 4, 0, 2, 5], [6, 3, 8, 2, 0, 4],
              [4, 7, 6, 5, 4, 0]]
_DIRECTED = [[0, 2, 9, 7, 6, 4], [8, 0, 3, 9, 2, 7], [5, 6, 0, 2, 8, 3], [4, 7, 6, 0, 2, 5], [9, 3, 7, 8, 0, 2],
             [3, 8, 4, 6, 9, 0]]


def _native_problems() -> list:
    return [
        _NativeProblem("tiny-tsp", [[float(v) for v in row] for row in _SYMMETRIC], "tsp", 18.0),
        _NativeProblem("tiny-atsp", [[float(v) for v in row] for row in _DIRECTED], "atsp", 18.0),
    ]


def _native_config() -> dict:
    return {
        "protocol_version": NATIVE_PROTOCOL, "comparison_regime": NATIVE_TERMINATION_REGIME,
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {
            "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 1},
            "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "max_no_improvement": 1, "dive_count": 1},
            "Core-TwoOpt-TSP": {"max_iterations": 2, "first_improvement": False},
            "Core-ThreeOpt-TSP": {"max_iterations": 2, "first_improvement": True, "window": 4},
            "Core-OrOpt-TSP": {"max_iterations": 3, "first_improvement": False, "window": 3},
            "ALNS-TSP": dict(_ALNS_PARAMS),
        },
        "runs": 1, "base_seed": 71, "workers": 1, "replay_replicates": [0],
        "allow_repository_output": False, "overwrite": False,
    }


# ------------------------------------------------------------------------------------------ rendering
def _read_dir(path: Path) -> dict:
    return {p.name: p.read_bytes().decode("utf-8") for p in sorted(path.iterdir())}


def _strip_volatile(value: Any) -> Any:
    """Drop database timestamps and reduce the temporary ``path`` entries to their file name."""
    if isinstance(value, dict):
        return {k: (Path(v).name if k == "path" and isinstance(v, str) else _strip_volatile(v))
                for k, v in value.items() if k not in _VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def _clock():
    state = {"calls": 0}

    def perf_counter() -> float:
        state["calls"] += 1
        return 0.0 if state["calls"] % 2 == 1 else 0.001  # start, end: exactly 1.0 ms

    return SimpleNamespace(perf_counter=perf_counter)


def _render_fair(tmp_path: Path) -> dict:
    config = {
        "protocol_version": "uniride-fair-tsp-v1", "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {a: dict(_ALNS_PARAMS) if a == "ALNS-TSP" else {} for a in APPROVED_ALGORITHMS},
        "runs": 3, "evaluation_budget": 20, "base_seed": 123, "budget_policy": "atomic_upper_bound_v1", "workers": 1,
        "replay_replicates": [0], "allow_repository_output": False, "overwrite": False,
    }
    path = tmp_path / "fair.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    out = tmp_path / "fair-out"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(fair_pilot, "time", _clock())
        mp.setattr(fair_pilot, "_git_metadata", lambda root: {"commit": "golden"})
        mp.setattr(fair_pilot, "_environment_metadata", lambda: {"python": "golden"})
        run_fair_pilot(path, out, problem_loader=_fair_problems, registry_getter=_fair_registry,
                       repo_root=tmp_path / "repository", runtime_probe=lambda: RUNTIME,
                       registered_algorithms_provider=lambda: APPROVED_ALGORITHMS, gateway_executor=_fair_gateway)
    return _read_dir(out)


def _render_native(tmp_path: Path) -> dict:
    path = tmp_path / "native.json"
    path.write_text(json.dumps(_native_config()), encoding="utf-8")
    out = tmp_path / "native-out"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(fair_pilot, "time", _clock())
        mp.setattr(native_pilot, "_git_metadata", lambda root: {"commit": "golden"})
        mp.setattr(native_pilot, "_environment_metadata", lambda: {"python": "golden"})
        run_native_pilot(path, out, problem_loader=_native_problems, runtime_probe=lambda: RUNTIME,
                         repo_root=tmp_path / "separate-repository-root",
                         registered_algorithms_provider=lambda: APPROVED_NATIVE_ALGORITHMS)
    return _read_dir(out)


_SUMMARY_ROWS = [
    {"problem": "C101", "algorithm": "OR-Tools", "problem_type": "CVRPTW", "objective_cost": 828.9, "gap": 0.0,
     "num_vehicles": 10, "capacity_violations": 0, "tw_violations": 0,
     "metadata": {"bks_vehicles": 10, "vehicle_gap": 0, "execution_failed": False}},
    {"problem": "R101", "algorithm": "PyVRP", "problem_type": "CVRPTW", "objective_cost": 1642.8, "gap": None,
     "num_vehicles": 20, "capacity_violations": 0, "tw_violations": 0,
     "metadata": {"bks_vehicles": 19, "vehicle_gap": 1, "execution_failed": False}},
    {"problem": "A-n32-k5", "algorithm": "OR-Tools", "problem_type": "CVRP", "objective_cost": 800.0, "gap": 2.0,
     "num_vehicles": 5, "capacity_violations": 0, "tw_violations": 0, "metadata": {"execution_failed": False}},
    {"problem": "A-n32-k5", "algorithm": "OR-Tools", "problem_type": "CVRP", "objective_cost": 790.0, "gap": 1.0,
     "num_vehicles": 5, "capacity_violations": 0, "tw_violations": 0, "metadata": {"execution_failed": False}},
    {"problem": "X-n101", "algorithm": "PyVRP", "problem_type": "CVRP", "objective_cost": 700.0, "gap": 0.5,
     "num_vehicles": 4, "capacity_violations": 1, "tw_violations": 0, "metadata": {"execution_failed": False}},
    {"problem": "bad", "algorithm": "PyVRP", "problem_type": "CVRP", "objective_cost": None, "gap": None,
     "error": "boom", "metadata": {"execution_failed": True}},
]


def _render_results_reader(tmp_path: Path) -> dict:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "problem_type",
              "matrix_kind", "objective_cost", "num_vehicles", "capacity_violations", "tw_violations", "routes_json",
              "route_loads_json", "route_costs_json", "params_json", "gap_type"]
    with open(csv_dir / "benchmark_progress.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"timestamp": "2026-11-26T00:00:00", "problem": "tiny-cvrptw", "strategy": "Core-Greedy-Routing",
                         "avg_length": "40", "avg_gap": "0", "avg_time_ms": "12", "n_runs": "1", "problem_type": "cvrptw",
                         "matrix_kind": "distance", "objective_cost": "40", "num_vehicles": "1",
                         "capacity_violations": "0", "tw_violations": "1", "routes_json": json.dumps([[1, 2]]),
                         "route_loads_json": json.dumps([[2]]), "route_costs_json": json.dumps([40]),
                         "params_json": json.dumps({"alpha": 1}), "gap_type": "unknown"})
    db_path = str(tmp_path / "tsplib.db")
    conn = get_db(db_path)
    init_db(conn)
    conn.execute("INSERT INTO problems (name, dimension, optimal, category, edge_weight_type, problem_type) "
                 "VALUES (?, ?, ?, ?, ?, ?)", ("tiny", 4, 10, "small", "EUC_2D", "TSP"))
    conn.commit()
    conn.close()
    save_best_solution("tiny", "GA", {"population_size": 8}, [1, 2, 3, 4], 12.0, 20.0, db_path=db_path)
    save_benchmark_run("run-1", source="web_matrix_native", settings={"n_runs": 1}, db_path=db_path)
    save_benchmark_result("run-1", {
        "problem": "tiny-cvrp", "algorithm": "Core-Greedy-Routing", "run_number": 1, "problem_type": "cvrp",
        "matrix_kind": "distance", "objective_cost": 42.0, "tour_cost": 42.0, "gap": 0.0, "elapsed_ms": 5.0,
        "routes": [[1, 2]], "num_vehicles": 1, "capacity_violations": 0, "tw_violations": 0, "params": {"mode": "test"},
    }, db_path=db_path)
    return _strip_volatile({
        "leaderboard": get_leaderboard(limit=10, db_path=db_path),
        "best_result": get_best_result("tiny", "GA", db_path=db_path),
        "benchmark_rows_csv": get_benchmark_rows(results_dir=str(csv_dir), limit=10, prefer_db=False),
        "benchmark_rows_db": get_benchmark_rows(db_path=db_path, results_dir=str(tmp_path), limit=10),
    })


def render_all(tmp_path: Path) -> str:
    """The golden document: sorted-key JSON with a final newline."""
    document = {
        "fair_pilot": _render_fair(tmp_path),
        "native_pilot": _render_native(tmp_path),
        "matrix_run_summary": make_json_ready(summarize_benchmark_rows(_SUMMARY_ROWS)),
        "results_reader": _render_results_reader(tmp_path),
        "pinned_files": {rel: _pinned_sha(rel) for rel in sorted(PINNED_FILES)},
    }
    return json.dumps(document, sort_keys=True, indent=1, ensure_ascii=True) + "\n"


def capture_golden(tmp_path: Path) -> None:
    """Write the fixture. Run once at the base commit; never edit the fixture by hand."""
    GOLDEN.write_bytes(render_all(tmp_path).encode("utf-8"))


# ------------------------------------------------------------------------------------------ tests
def test_fixed_budget_and_native_outputs_are_byte_identical(tmp_path):
    rendered = render_all(tmp_path).encode("utf-8")
    assert rendered == GOLDEN.read_bytes()


def test_golden_pins_every_declared_committed_file():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert sorted(golden["pinned_files"]) == sorted(PINNED_FILES)
    assert all(len(v) == 64 for v in golden["pinned_files"].values())


def test_golden_covers_both_protocols_and_the_summary_readers():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(golden) == {"fair_pilot", "native_pilot", "matrix_run_summary", "results_reader", "pinned_files"}
    for part in ("fair_pilot", "native_pilot"):
        assert set(golden[part]) == {"aggregate.csv", "manifest.json", "runs.jsonl", "validation.json"}
    assert "uniride-native-tsp-v1" in golden["native_pilot"]["aggregate.csv"]
