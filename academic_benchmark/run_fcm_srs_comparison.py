"""Run a deterministic matrix-native FCM-SRS comparison benchmark."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from academic_benchmark.tsplib_manager import DB_PATH, save_benchmark_result, save_benchmark_run
from uniride_core.algorithms.engine_factory import create_matrix_engine
from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner
from uniride_core.models import CostMatrix, RoutingProblem


DEFAULT_ALGORITHMS = ("Core-GA-TSP", "FCM-GA-TSP", "Core-PSO-TSP", "FCM-PSO-TSP")


def run_fcm_srs_comparison(
    *,
    db_path: str = DB_PATH,
    run_id: str | None = None,
    dimension: int = 36,
    algorithms: Iterable[str] = DEFAULT_ALGORITHMS,
    seed: int = 20_000,
) -> Dict[str, object]:
    """Run FCM-vs-core TSP comparison and persist results to SQLite."""
    problem = build_synthetic_large_tsp(dimension)
    algorithm_configs = [_algorithm_config(name) for name in algorithms]
    runner = MatrixBenchmarkRunner(algorithm_configs)
    effective_run_id = run_id or f"fcm-srs-comparison-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"

    save_benchmark_run(
        effective_run_id,
        source="fcm_srs_comparison",
        status="running",
        settings={
            "problem_name": problem.name,
            "dimension": problem.dimension,
            "algorithms": [algorithm.name for algorithm in algorithm_configs],
        },
        db_path=db_path,
    )

    saved = 0
    errors: List[Dict[str, str]] = []
    for run_number, algorithm in enumerate(runner.algorithms, start=1):
        result = runner.run_one(problem, algorithm, run_number=run_number, seed=seed + run_number)
        save_benchmark_result(effective_run_id, asdict(result), db_path=db_path)
        saved += 1
        if result.error:
            errors.append({"algorithm": algorithm.name, "error": result.error})

    save_benchmark_run(
        effective_run_id,
        source="fcm_srs_comparison",
        status="failed" if errors else "completed",
        settings={
            "problem_name": problem.name,
            "dimension": problem.dimension,
            "algorithms": [algorithm.name for algorithm in algorithm_configs],
            "saved_results": saved,
            "errors": errors,
        },
        db_path=db_path,
    )
    return {"run_id": effective_run_id, "saved_results": saved, "errors": errors}


def build_synthetic_large_tsp(dimension: int = 36) -> RoutingProblem:
    """Create a clustered coordinate-backed TSP for FCM validation."""
    if dimension < 8:
        raise ValueError("dimension must be at least 8 for FCM-SRS comparison")

    centers = [(-20.0, -20.0), (20.0, -20.0), (20.0, 20.0), (-20.0, 20.0)]
    coordinates: List[Tuple[float, float]] = []
    for idx in range(dimension):
        cx, cy = centers[idx % len(centers)]
        ring = idx // len(centers)
        angle = (ring * 137.508 + idx * 17.0) * np.pi / 180.0
        radius = 2.0 + (ring % 5)
        coordinates.append((cx + radius * float(np.cos(angle)), cy + radius * float(np.sin(angle))))

    matrix = np.zeros((dimension, dimension), dtype=float)
    for i in range(dimension):
        x1, y1 = coordinates[i]
        for j in range(i + 1, dimension):
            x2, y2 = coordinates[j]
            dist = float(np.hypot(x1 - x2, y1 - y2))
            matrix[i, j] = dist
            matrix[j, i] = dist

    return RoutingProblem(
        name=f"synthetic-fcm-tsp-{dimension}",
        problem_type="tsp",
        matrix=CostMatrix(matrix, kind="distance"),
        coordinates=coordinates,
        category="large" if dimension >= 500 else "medium",
        source="synthetic_fcm_srs",
    )


def _algorithm_config(name: str) -> MatrixAlgorithmConfig:
    base_params = {
        "population_size": 10,
        "num_particles": 10,
        "num_wolves": 10,
        "num_hawks": 10,
        "max_iterations": 8,
        "iterations": 8,
        "elite_count": 2,
        "tournament_size": 3,
        "max_no_improvement": 6,
        "fcm_clusters": 4,
        "fcm_m": 2.0,
        "fcm_iterations": 12,
        "fcm_min_cluster_size": 4,
        "fcm_polish_iterations": 40,
        "local_search_rate": 0.0,
    }
    return MatrixAlgorithmConfig(name=name, engine=create_matrix_engine(name), params=base_params)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FCM-SRS matrix-native comparison benchmark")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--run-id")
    parser.add_argument("--dimension", type=int, default=36)
    parser.add_argument("--algorithms", nargs="*", default=list(DEFAULT_ALGORITHMS))
    args = parser.parse_args()

    result = run_fcm_srs_comparison(
        db_path=args.db_path,
        run_id=args.run_id,
        dimension=args.dimension,
        algorithms=args.algorithms,
    )
    print(f"run_id={result['run_id']}")
    print(f"saved_results={result['saved_results']}")
    print(f"errors={result['errors']}")


if __name__ == "__main__":
    main()
