"""Repeatable matrix-native validation plans for real routing datasets."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from academic_benchmark.matrix_run_summary import make_json_ready, summarize_run
from academic_benchmark.run_matrix_benchmark import run_matrix_benchmark
from academic_benchmark.tsplib_manager import DB_PATH


DEFAULT_PROBLEMS = (
    "A-n32-k5",
    "A-n33-k5",
    "B-n31-k5",
    "B-n34-k5",
    "C101",
    "C103",
    "R101",
    "R103",
    "RC101",
    "RC103",
)
DEFAULT_ALGORITHMS = ("OR-Tools", "PyVRP")
DEFAULT_VARIANTS = (
    ("time10-scale1000", 10),
    ("time20-scale1000", 20),
)
ORTOOLS_SEARCH_PARAMS = {
    "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
    "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
}


@dataclass(frozen=True)
class ValidationJob:
    run_id: str
    problems: tuple[str, ...]
    algorithms: tuple[str, ...]
    n_runs: int
    seed: int
    params: dict[str, Any]
    per_algorithm_params: dict[str, dict[str, Any]]


def build_validation_jobs(
    *,
    run_id_prefix: str,
    n_runs: int = 3,
    seed: int = 2000,
    problems: Sequence[str] = DEFAULT_PROBLEMS,
    algorithms: Sequence[str] = DEFAULT_ALGORITHMS,
    variants: Sequence[tuple[str, int]] = DEFAULT_VARIANTS,
) -> list[ValidationJob]:
    """Create named validation jobs for solver time-limit variants."""
    jobs: list[ValidationJob] = []
    for index, (variant_name, time_limit_seconds) in enumerate(variants):
        jobs.append(
            ValidationJob(
                run_id=f"{run_id_prefix}-{variant_name}",
                problems=tuple(problems),
                algorithms=tuple(algorithms),
                n_runs=int(n_runs),
                seed=int(seed) + index * 100,
                params={"time_limit_seconds": int(time_limit_seconds), "scale": 1000},
                per_algorithm_params={"OR-Tools": dict(ORTOOLS_SEARCH_PARAMS)},
            )
        )
    return jobs


def run_validation_jobs(
    jobs: Iterable[ValidationJob],
    *,
    db_path: str = DB_PATH,
    runner: Callable[..., Mapping[str, Any]] = run_matrix_benchmark,
    summarizer: Callable[..., Mapping[str, Any]] = summarize_run,
) -> list[dict[str, Any]]:
    """Run validation jobs and return runner output plus persisted DB summary."""
    outputs: list[dict[str, Any]] = []
    for job in jobs:
        result = dict(
            runner(
                db_path=db_path,
                run_id=job.run_id,
                algorithms=job.algorithms,
                problems=job.problems,
                n_runs=job.n_runs,
                seed=job.seed,
                algorithm_params=job.params,
                per_algorithm_params=job.per_algorithm_params,
                source="academic_matrix_validation",
            )
        )
        summary = dict(summarizer(job.run_id, db_path=db_path, limit=100_000))
        outputs.append({"job": asdict(job), "result": result, "summary": summary})
    return outputs


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run repeatable matrix-native validation variants")
    parser.add_argument("--run-id-prefix", required=True)
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2000)
    parser.add_argument("--problems", nargs="*", default=list(DEFAULT_PROBLEMS))
    parser.add_argument("--algorithms", nargs="*", default=list(DEFAULT_ALGORITHMS))
    parser.add_argument(
        "--variants",
        nargs="*",
        default=[f"{name}:{seconds}" for name, seconds in DEFAULT_VARIANTS],
        help="Variant specs as name:time_limit_seconds",
    )
    args = parser.parse_args(argv)

    jobs = build_validation_jobs(
        run_id_prefix=args.run_id_prefix,
        n_runs=args.n_runs,
        seed=args.seed,
        problems=tuple(args.problems),
        algorithms=tuple(args.algorithms),
        variants=_parse_variants(args.variants),
    )
    print(json.dumps(make_json_ready(run_validation_jobs(jobs, db_path=args.db_path)), indent=2, sort_keys=True))
    return 0


def _parse_variants(values: Sequence[str]) -> tuple[tuple[str, int], ...]:
    variants = []
    for value in values:
        name, _, seconds = value.partition(":")
        if not name or not seconds:
            raise ValueError(f"Invalid variant spec: {value!r}; expected name:seconds")
        variants.append((name, int(seconds)))
    return tuple(variants)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ValidationJob", "build_validation_jobs", "run_validation_jobs"]
