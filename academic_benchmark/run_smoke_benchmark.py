"""Run a small matrix-native benchmark over the seeded academic smoke problems."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from academic_benchmark.seed_smoke_datasets import seed_smoke_datasets
from academic_benchmark.tsplib_manager import (
    DB_PATH,
    load_routing_problem,
    save_benchmark_result,
    save_benchmark_run,
)
from uniride_core.algorithms.greedy_engine import GreedyMatrixEngine
from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner


SMOKE_PROBLEM_NAMES = [
    "smoke-tsp",
    "smoke-atsp",
    "smoke-cvrp",
    "smoke-solomon",
    "smoke-uniride",
]


def run_smoke_benchmark(
    *,
    db_path: str = DB_PATH,
    run_id: str | None = None,
    seed_missing: bool = True,
    algorithms: Iterable[MatrixAlgorithmConfig] | None = None,
) -> Dict[str, object]:
    """Run deterministic matrix-native smoke benchmarks and persist results."""
    if seed_missing:
        seed_smoke_datasets(db_path=db_path)

    problems = []
    missing = []
    for name in SMOKE_PROBLEM_NAMES:
        problem = load_routing_problem(name, db_path=db_path)
        if problem is None:
            missing.append(name)
        else:
            problems.append(problem)
    if missing:
        raise RuntimeError(f"Missing smoke benchmark problems: {missing}")

    algorithm_configs = list(
        algorithms
        or [
            MatrixAlgorithmConfig(
                name="Core-Greedy-Routing",
                engine=GreedyMatrixEngine(),
                params={"smoke": True},
            )
        ]
    )
    runner = MatrixBenchmarkRunner(algorithm_configs)
    effective_run_id = run_id or f"matrix-smoke-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"

    save_benchmark_run(
        effective_run_id,
        source="academic_matrix_smoke",
        status="running",
        settings={
            "problem_names": [problem.name for problem in problems],
            "algorithms": [algorithm.name for algorithm in algorithm_configs],
        },
        db_path=db_path,
    )

    saved = 0
    errors: List[Dict[str, str]] = []
    run_number = 0
    for problem in problems:
        for algorithm in runner.algorithms:
            run_number += 1
            result = runner.run_one(problem, algorithm, run_number=run_number, seed=10_000 + run_number)
            save_benchmark_result(effective_run_id, asdict(result), db_path=db_path)
            saved += 1
            if result.error:
                errors.append({"problem": problem.name, "algorithm": algorithm.name, "error": result.error})

    save_benchmark_run(
        effective_run_id,
        source="academic_matrix_smoke",
        status="failed" if errors else "completed",
        settings={
            "problem_names": [problem.name for problem in problems],
            "algorithms": [algorithm.name for algorithm in algorithm_configs],
            "saved_results": saved,
            "errors": errors,
        },
        db_path=db_path,
    )
    return {"run_id": effective_run_id, "saved_results": saved, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run academic matrix-native smoke benchmark")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--run-id")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()
    result = run_smoke_benchmark(db_path=args.db_path, run_id=args.run_id, seed_missing=not args.no_seed)
    print(f"run_id={result['run_id']}")
    print(f"saved_results={result['saved_results']}")
    print(f"errors={result['errors']}")


if __name__ == "__main__":
    main()

