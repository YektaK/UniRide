"""Run matrix-native academic benchmarks from the SQLite problem store."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Sequence

from academic_benchmark.seed_smoke_datasets import seed_smoke_datasets
from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_all_problems,
    load_routing_problem,
    save_benchmark_result,
    save_benchmark_run,
)
from uniride_core.algorithms.engine_factory import canonical_matrix_engine_name, create_matrix_engine
from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner


DEFAULT_ALGORITHMS = ("Core-Greedy-Routing",)


def run_matrix_benchmark(
    *,
    db_path: str = DB_PATH,
    run_id: str | None = None,
    algorithms: Iterable[str] = DEFAULT_ALGORITHMS,
    problems: Iterable[str] | None = None,
    problem_types: Iterable[str] | None = None,
    n_runs: int = 1,
    seed: int = 42,
    max_dim: int = 10_000,
    limit: int = 100,
    seed_missing_smoke: bool = False,
    source: str = "academic_matrix_cli",
    algorithm_params: Mapping[str, object] | None = None,
    per_algorithm_params: Mapping[str, Mapping[str, object]] | None = None,
) -> Dict[str, object]:
    """Run named matrix-native engines on stored academic RoutingProblems."""
    if seed_missing_smoke:
        seed_smoke_datasets(db_path=db_path)

    problem_names = _select_problem_names(
        db_path=db_path,
        problems=list(problems or []),
        problem_types={item.lower() for item in problem_types or []},
        max_dim=max_dim,
        limit=limit,
    )
    if not problem_names:
        raise RuntimeError("No academic matrix-native problems matched the requested selection")

    routing_problems = []
    missing = []
    for name in problem_names:
        loaded = load_routing_problem(name, db_path=db_path)
        if loaded is None:
            missing.append(name)
        else:
            routing_problems.append(loaded)
    if missing:
        raise RuntimeError(f"Stored problem rows could not be loaded as RoutingProblem objects: {missing}")

    effective_algorithm_params = dict(algorithm_params or {})
    effective_per_algorithm_params = {
        str(key): dict(value)
        for key, value in (per_algorithm_params or {}).items()
    }
    algorithm_configs = [
        _build_algorithm_config(
            name,
            params={
                **effective_algorithm_params,
                **_params_for_algorithm(name, effective_per_algorithm_params),
            },
        )
        for name in algorithms
    ]
    if not algorithm_configs:
        raise RuntimeError("No matrix-native algorithms were requested")

    effective_run_id = run_id or f"matrix-benchmark-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    settings = {
        "problem_names": [problem.name for problem in routing_problems],
        "problem_types": sorted({problem.problem_type for problem in routing_problems}),
        "algorithms": [algorithm.name for algorithm in algorithm_configs],
        "n_runs": int(n_runs),
        "seed": int(seed),
        "max_dim": int(max_dim),
        "limit": int(limit),
        "algorithm_params": effective_algorithm_params,
        "per_algorithm_params": effective_per_algorithm_params,
    }
    save_benchmark_run(effective_run_id, source=source, status="running", settings=settings, db_path=db_path)

    runner = MatrixBenchmarkRunner(algorithm_configs)
    saved = 0
    errors: List[Dict[str, str]] = []
    for result in runner.run(routing_problems, n_runs=max(1, int(n_runs)), seed=int(seed)):
        save_benchmark_result(effective_run_id, asdict(result), db_path=db_path)
        saved += 1
        if result.error:
            errors.append({"problem": result.problem, "algorithm": result.algorithm, "error": result.error})

    save_benchmark_run(
        effective_run_id,
        source=source,
        status="failed" if errors else "completed",
        settings={**settings, "saved_results": saved, "errors": errors},
        db_path=db_path,
    )
    return {"run_id": effective_run_id, "saved_results": saved, "errors": errors}


def _build_algorithm_config(name: str, *, params: Mapping[str, object] | None = None) -> MatrixAlgorithmConfig:
    canonical = canonical_matrix_engine_name(name)
    return MatrixAlgorithmConfig(name=canonical, engine=create_matrix_engine(name), params=dict(params or {}))


def _params_for_algorithm(name: str, per_algorithm_params: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    canonical = canonical_matrix_engine_name(name)
    params = per_algorithm_params.get(str(name)) or per_algorithm_params.get(canonical) or {}
    return dict(params)


def _select_problem_names(
    *,
    db_path: str,
    problems: Sequence[str],
    problem_types: set[str],
    max_dim: int,
    limit: int,
) -> List[str]:
    if problems:
        return list(dict.fromkeys(name for name in problems if name))

    rows = get_all_problems(db_path=db_path, max_dim=max_dim, exclude_explicit=False)
    if problem_types:
        rows = [row for row in rows if str(row.get("problem_type", "")).lower() in problem_types]
    rows = rows[: max(1, int(limit))]
    return [str(row["name"]) for row in rows]


def _split_csv(values: Sequence[str]) -> List[str]:
    result: List[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def _parse_params_json(value: str) -> Dict[str, object]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--params-json must decode to a JSON object")
    return dict(parsed)


def _parse_algorithm_params_json(value: str) -> Dict[str, Dict[str, object]]:
    parsed = _parse_params_json(value)
    result: Dict[str, Dict[str, object]] = {}
    for key, params in parsed.items():
        if not isinstance(params, dict):
            raise argparse.ArgumentTypeError("--algorithm-params-json values must be JSON objects")
        result[str(key)] = dict(params)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run matrix-native academic benchmarks from SQLite")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--run-id")
    parser.add_argument("--algorithms", nargs="+", default=list(DEFAULT_ALGORITHMS))
    parser.add_argument("--problems", nargs="*", default=[])
    parser.add_argument("--problem-types", nargs="*", default=[])
    parser.add_argument("--n-runs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-dim", type=int, default=10_000)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed-smoke", action="store_true")
    parser.add_argument(
        "--params-json",
        type=_parse_params_json,
        default={},
        help="JSON object passed as params to every selected matrix-native algorithm.",
    )
    parser.add_argument(
        "--algorithm-params-json",
        type=_parse_algorithm_params_json,
        default={},
        help="JSON object mapping algorithm names to per-algorithm params; merged over --params-json.",
    )
    args = parser.parse_args(argv)

    result = run_matrix_benchmark(
        db_path=args.db_path,
        run_id=args.run_id,
        algorithms=_split_csv(args.algorithms),
        problems=_split_csv(args.problems),
        problem_types=_split_csv(args.problem_types),
        n_runs=args.n_runs,
        seed=args.seed,
        max_dim=args.max_dim,
        limit=args.limit,
        seed_missing_smoke=args.seed_smoke,
        algorithm_params=args.params_json,
        per_algorithm_params=args.algorithm_params_json,
    )
    print(f"run_id={result['run_id']}")
    print(f"saved_results={result['saved_results']}")
    print(f"errors={result['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
