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
ALL_IMPORTED_VARIANTS = (("time10-scale1000", 10),)
ORTOOLS_SEARCH_PARAMS = {
    "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
    "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
}
VALIDATION_PROFILES = ("quick-real", "all-imported")


@dataclass(frozen=True)
class ValidationJob:
    run_id: str
    problems: tuple[str, ...]
    problem_types: tuple[str, ...]
    algorithms: tuple[str, ...]
    n_runs: int
    seed: int
    max_dim: int
    limit: int
    params: dict[str, Any]
    per_algorithm_params: dict[str, dict[str, Any]]
    source: str = "academic_matrix_validation"


def build_validation_jobs(
    *,
    run_id_prefix: str,
    n_runs: int = 3,
    seed: int = 2000,
    problems: Sequence[str] = DEFAULT_PROBLEMS,
    problem_types: Sequence[str] = (),
    algorithms: Sequence[str] = DEFAULT_ALGORITHMS,
    variants: Sequence[tuple[str, int]] = DEFAULT_VARIANTS,
    max_dim: int = 10_000,
    limit: int = 100,
    source: str = "academic_matrix_validation",
) -> list[ValidationJob]:
    """Create named validation jobs for solver time-limit variants."""
    jobs: list[ValidationJob] = []
    for index, (variant_name, time_limit_seconds) in enumerate(variants):
        jobs.append(
            ValidationJob(
                run_id=f"{run_id_prefix}-{variant_name}",
                problems=tuple(problems),
                problem_types=tuple(problem_types),
                algorithms=tuple(algorithms),
                n_runs=int(n_runs),
                seed=int(seed) + index * 100,
                max_dim=int(max_dim),
                limit=int(limit),
                params={"time_limit_seconds": int(time_limit_seconds), "scale": 1000},
                per_algorithm_params={"OR-Tools": dict(ORTOOLS_SEARCH_PARAMS)},
                source=source,
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
                problem_types=job.problem_types,
                n_runs=job.n_runs,
                seed=job.seed,
                max_dim=job.max_dim,
                limit=job.limit,
                algorithm_params=job.params,
                per_algorithm_params=job.per_algorithm_params,
                source=job.source,
            )
        )
        summary = dict(summarizer(job.run_id, db_path=db_path, limit=100_000))
        outputs.append({"job": asdict(job), "result": result, "summary": summary})
    return outputs


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run repeatable matrix-native validation variants")
    parser.add_argument(
        "--profile",
        choices=VALIDATION_PROFILES,
        default="quick-real",
        help="Named validation profile. all-imported selects all stored CVRP/CVRPTW rows from SQLite.",
    )
    parser.add_argument("--run-id-prefix", required=True)
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--n-runs", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--problems", nargs="*")
    parser.add_argument("--problem-types", nargs="*")
    parser.add_argument("--algorithms", nargs="*")
    parser.add_argument("--max-dim", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--variants",
        nargs="*",
        default=None,
        help="Variant specs as name:time_limit_seconds",
    )
    args = parser.parse_args(argv)
    defaults = _profile_defaults(args.profile)

    jobs = build_validation_jobs(
        run_id_prefix=args.run_id_prefix,
        n_runs=args.n_runs if args.n_runs is not None else defaults["n_runs"],
        seed=args.seed if args.seed is not None else defaults["seed"],
        problems=tuple(args.problems) if args.problems is not None else defaults["problems"],
        problem_types=tuple(args.problem_types) if args.problem_types is not None else defaults["problem_types"],
        algorithms=tuple(args.algorithms) if args.algorithms is not None else defaults["algorithms"],
        variants=_parse_variants(args.variants) if args.variants is not None else defaults["variants"],
        max_dim=args.max_dim if args.max_dim is not None else defaults["max_dim"],
        limit=args.limit if args.limit is not None else defaults["limit"],
    )
    print(json.dumps(make_json_ready(run_validation_jobs(jobs, db_path=args.db_path)), indent=2, sort_keys=True))
    return 0


def _profile_defaults(profile: str) -> dict[str, Any]:
    if profile == "all-imported":
        return {
            "n_runs": 1,
            "seed": 2000,
            "problems": (),
            "problem_types": ("cvrp", "cvrptw"),
            "algorithms": DEFAULT_ALGORITHMS,
            "variants": ALL_IMPORTED_VARIANTS,
            "max_dim": 10_000,
            "limit": 100_000,
        }
    return {
        "n_runs": 3,
        "seed": 2000,
        "problems": DEFAULT_PROBLEMS,
        "problem_types": (),
        "algorithms": DEFAULT_ALGORITHMS,
        "variants": DEFAULT_VARIANTS,
        "max_dim": 10_000,
        "limit": 100,
    }


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
