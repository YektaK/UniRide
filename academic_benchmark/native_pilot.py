"""Isolated algorithm-native-termination pilot for academic TSP/ATSP."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from academic_benchmark.fair_pilot import (
    FairPilotError,
    _closed_cost,
    _csv_atomic,
    _environment_metadata,
    _git_metadata,
    _json_atomic,
    _jsonl_atomic,
    _prepare_output_dir,
    _registry_executor,
    _run_executor,
    preflight_numba_objective,
    resolve_problems,
)
from academic_benchmark.native_protocol import (
    APPROVED_NATIVE_ALGORITHMS,
    NATIVE_PROTOCOL,
    NATIVE_TERMINATION_REGIME,
    NativeComparisonManifest,
    NativeRunResult,
)


_GWO_HHO = frozenset({"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"})
_CONFIG_KEYS = frozenset({
    "protocol_version",
    "comparison_regime",
    "problems",
    "algorithms",
    "runs",
    "base_seed",
    "workers",
    "replay_replicates",
    "allow_repository_output",
    "overwrite",
})
_ALLOWED_ALGORITHM_KEYS = {
    "Core-GWO-TSP-Pure": frozenset({
        "pack_size", "max_iterations", "initial_a", "exploration_rate",
        "max_no_improvement",
    }),
    "Core-HHO-TSP-Pure": frozenset({
        "hawks", "max_iterations", "initial_energy", "jump_probability",
        "max_no_improvement", "dive_count", "levy_scale",
    }),
    "Numba-2-opt": frozenset({"max_iterations", "first_improvement"}),
    "Numba-3-opt-bounded": frozenset({
        "max_iterations", "first_improvement", "window",
    }),
}
_REQUIRED_ALGORITHM_KEYS = {
    "Core-GWO-TSP-Pure": frozenset({
        "pack_size", "max_iterations", "max_no_improvement",
    }),
    "Core-HHO-TSP-Pure": frozenset({
        "hawks", "max_iterations", "max_no_improvement",
    }),
    "Numba-2-opt": frozenset({"max_iterations", "first_improvement"}),
    "Numba-3-opt-bounded": frozenset({
        "max_iterations", "first_improvement", "window",
    }),
}
_REPLAY_FIELDS = (
    "tour",
    "objective_cost",
    "objective_evaluations",
    "termination_reason",
    "seed",
    "seed_group",
    "comparison_regime",
    "acceptance_policy",
    "neighborhood_window",
    "initialization_policy",
    "execution_backend",
    "polish_policy",
)


class NativePilotError(FairPilotError):
    """Configuration or scientific-integrity failure in the native pilot."""


def _strict_int(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise NativePilotError(f"{name} must be an integer >= {minimum}")
    return value


def _strict_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise NativePilotError(f"{name} must be a boolean")
    return value


@dataclass(frozen=True)
class NativePilotConfig:
    protocol_version: str
    comparison_regime: str
    problems: Tuple[str, ...]
    algorithms: Mapping[str, Mapping[str, Any]]
    runs: int
    base_seed: int
    workers: int
    replay_replicates: Tuple[int, ...]
    allow_repository_output: bool
    overwrite: bool

    @property
    def manifest(self) -> NativeComparisonManifest:
        return NativeComparisonManifest(
            protocol_version=self.protocol_version,
            comparison_regime=self.comparison_regime,
            base_seed=self.base_seed,
        )

    @property
    def native_comparison(self) -> Dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "comparison_regime": self.comparison_regime,
            "base_seed": self.base_seed,
        }


def _strict_number(
    value: Any,
    name: str,
    *,
    minimum: float = 0.0,
    maximum: Optional[float] = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativePilotError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise NativePilotError(f"{name} must be finite and >= {minimum}")
    if maximum is not None and number > maximum:
        raise NativePilotError(f"{name} must be <= {maximum}")
    return number


def _validate_algorithm_parameters(
    algorithms: Mapping[str, Mapping[str, Any]],
) -> None:
    for algorithm_id in sorted(APPROVED_NATIVE_ALGORITHMS):
        block = algorithms[algorithm_id]
        missing = _REQUIRED_ALGORITHM_KEYS[algorithm_id] - block.keys()
        unknown = block.keys() - _ALLOWED_ALGORITHM_KEYS[algorithm_id]
        if missing or unknown:
            raise NativePilotError(
                f"{algorithm_id} parameter schema mismatch; "
                f"missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        _strict_int(block["max_iterations"], f"{algorithm_id}.max_iterations", 1)

    gwo = algorithms["Core-GWO-TSP-Pure"]
    _strict_int(gwo["pack_size"], "Core-GWO-TSP-Pure.pack_size", 3)
    _strict_int(
        gwo["max_no_improvement"],
        "Core-GWO-TSP-Pure.max_no_improvement",
        1,
    )
    if "initial_a" in gwo:
        _strict_number(gwo["initial_a"], "Core-GWO-TSP-Pure.initial_a")
    if "exploration_rate" in gwo:
        _strict_number(
            gwo["exploration_rate"],
            "Core-GWO-TSP-Pure.exploration_rate",
            maximum=1.0,
        )

    hho = algorithms["Core-HHO-TSP-Pure"]
    _strict_int(hho["hawks"], "Core-HHO-TSP-Pure.hawks", 1)
    _strict_int(
        hho["max_no_improvement"],
        "Core-HHO-TSP-Pure.max_no_improvement",
        1,
    )
    if "dive_count" in hho:
        _strict_int(hho["dive_count"], "Core-HHO-TSP-Pure.dive_count", 0)
    if "initial_energy" in hho:
        _strict_number(hho["initial_energy"], "Core-HHO-TSP-Pure.initial_energy")
    if "jump_probability" in hho:
        _strict_number(
            hho["jump_probability"],
            "Core-HHO-TSP-Pure.jump_probability",
            maximum=1.0,
        )
    if "levy_scale" in hho:
        _strict_number(hho["levy_scale"], "Core-HHO-TSP-Pure.levy_scale")

    two_opt = algorithms["Numba-2-opt"]
    _strict_bool(
        two_opt["first_improvement"],
        "Numba-2-opt.first_improvement",
    )
    three_opt = algorithms["Numba-3-opt-bounded"]
    _strict_bool(
        three_opt["first_improvement"],
        "Numba-3-opt-bounded.first_improvement",
    )
    _strict_int(
        three_opt["window"],
        "Numba-3-opt-bounded.window",
        2,
    )


def load_native_pilot_config(path: str | Path) -> NativePilotConfig:
    """Load the exact JSON schema for ``uniride-native-tsp-v1``."""
    config_path = Path(path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NativePilotError(f"native config does not exist: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise NativePilotError(f"native config is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise NativePilotError("native config must be a JSON object")
    if "evaluation_budget" in data:
        raise NativePilotError("native config must not declare evaluation_budget")
    missing = _CONFIG_KEYS - data.keys()
    extra = data.keys() - _CONFIG_KEYS
    if missing or extra:
        raise NativePilotError(
            f"native config schema mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if data["protocol_version"] != NATIVE_PROTOCOL:
        raise NativePilotError(
            f"protocol_version must be {NATIVE_PROTOCOL!r}"
        )
    if data["comparison_regime"] != NATIVE_TERMINATION_REGIME:
        raise NativePilotError(
            "comparison_regime must be 'algorithm_native_termination'"
        )

    problems = data["problems"]
    if (
        not isinstance(problems, list)
        or not problems
        or any(not isinstance(name, str) or not name.strip() for name in problems)
        or len(set(problems)) != len(problems)
    ):
        raise NativePilotError("problems must be a non-empty list of unique names")
    algorithms = data["algorithms"]
    if not isinstance(algorithms, dict) or set(algorithms) != APPROVED_NATIVE_ALGORITHMS:
        raise NativePilotError(
            "algorithms must contain exactly the approved pure variants: "
            f"{sorted(APPROVED_NATIVE_ALGORITHMS)}"
        )
    if any(not isinstance(value, dict) for value in algorithms.values()):
        raise NativePilotError("each algorithm parameter block must be an object")
    _validate_algorithm_parameters(algorithms)

    runs = _strict_int(data["runs"], "runs", 1)
    workers = _strict_int(data["workers"], "workers", 1)
    if workers != 1:
        raise NativePilotError("workers must be 1 for deterministic native-pilot execution")
    replay_replicates = data["replay_replicates"]
    if (
        not isinstance(replay_replicates, list)
        or any(isinstance(item, bool) or not isinstance(item, int) for item in replay_replicates)
        or any(item < 0 or item >= runs for item in replay_replicates)
        or len(set(replay_replicates)) != len(replay_replicates)
    ):
        raise NativePilotError(
            "replay_replicates must be unique replicate indexes within runs"
        )
    return NativePilotConfig(
        protocol_version=data["protocol_version"],
        comparison_regime=data["comparison_regime"],
        problems=tuple(problems),
        algorithms={key: dict(value) for key, value in algorithms.items()},
        runs=runs,
        base_seed=_strict_int(data["base_seed"], "base_seed", 0),
        workers=workers,
        replay_replicates=tuple(replay_replicates),
        allow_repository_output=_strict_bool(
            data["allow_repository_output"], "allow_repository_output"
        ),
        overwrite=_strict_bool(data["overwrite"], "overwrite"),
    )


def _native_result_record(
    result: NativeRunResult,
    *,
    problem: Any,
    matrix: Sequence[Sequence[float]],
    matrix_sha256: str,
    algorithm_id: str,
    replicate: int,
    seed: int,
    config: NativePilotConfig,
    elapsed_ms: float,
    record_kind: str,
) -> Dict[str, Any]:
    try:
        config.manifest.validate_result(result)
    except ValueError as exc:
        raise NativePilotError(
            f"{problem.name}/{algorithm_id}/run-{replicate}: "
            f"native validation failed: {exc}"
        ) from exc
    independent = _closed_cost(result.tour, matrix)
    if not math.isclose(
        float(result.objective_cost), independent, rel_tol=0.0, abs_tol=1e-8
    ):
        raise NativePilotError(
            f"{problem.name}/{algorithm_id}/run-{replicate}: "
            "objective differs from independent cycle cost"
        )
    if algorithm_id in _GWO_HHO and result.execution_backend != "objective=numba;polish=none":
        raise NativePilotError(
            f"{problem.name}/{algorithm_id}/run-{replicate}: "
            "GWO/HHO did not use the exact pure Numba backend"
        )
    optimum = float(problem.optimal)
    return {
        "record_kind": record_kind,
        "protocol_version": config.protocol_version,
        "comparison_regime": config.comparison_regime,
        "problem": problem.name,
        "dimension": len(matrix),
        "problem_type": problem.problem_type,
        "edge_weight_type": getattr(problem, "edge_weight_type", "EXPLICIT"),
        "matrix_sha256": matrix_sha256,
        "optimum": optimum,
        "optimum_source": "problem.optimal",
        "algorithm_id": algorithm_id,
        "algorithm_family": result.algorithm_family,
        "variant": result.variant,
        "replicate": replicate,
        "seed": seed,
        "seed_group": result.seed_group,
        "initialization_policy": result.initialization_policy,
        "termination_policy": result.termination_policy,
        "termination_reason": result.termination_reason,
        "acceptance_policy": result.acceptance_policy,
        "neighborhood_window": result.neighborhood_window,
        "polish_policy": result.polish_policy,
        "execution_backend": result.execution_backend,
        "evaluation_budget": None,
        "objective_evaluations": result.objective_evaluations,
        "budget_terminated": False,
        "iterations": result.iterations,
        "tour": list(result.tour),
        "objective_cost": float(result.objective_cost),
        "independent_objective_cost": independent,
        "gap_pct": ((float(result.objective_cost) - optimum) / optimum) * 100.0,
        "elapsed_ms": elapsed_ms,
        "validation_status": "passed",
    }


def aggregate_native_records(
    rows: Sequence[Mapping[str, Any]], replay_ok: bool,
) -> List[Dict[str, Any]]:
    """Aggregate only native-v1 rows; reject fixed/native record mixing."""
    for row in rows:
        if row.get("protocol_version") != NATIVE_PROTOCOL:
            raise NativePilotError("native aggregate contains a foreign protocol record")
        if row.get("comparison_regime") != NATIVE_TERMINATION_REGIME:
            raise NativePilotError("native aggregate contains a foreign comparison regime")
        if row.get("evaluation_budget") is not None:
            raise NativePilotError("native aggregate contains a budgeted record")

    groups: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for row in rows:
        if row["record_kind"] == "primary":
            groups.setdefault(
                (str(row["problem"]), str(row["algorithm_id"])), []
            ).append(row)
    output: List[Dict[str, Any]] = []
    for (problem, algorithm), values in sorted(groups.items()):
        costs = [float(item["objective_cost"]) for item in values]
        gaps = [float(item["gap_pct"]) for item in values]
        elapsed = [float(item["elapsed_ms"]) for item in values]
        evaluations = [int(item["objective_evaluations"]) for item in values]
        output.append({
            "protocol_version": NATIVE_PROTOCOL,
            "comparison_regime": NATIVE_TERMINATION_REGIME,
            "problem": problem,
            "algorithm_id": algorithm,
            "runs": len(values),
            "best_cost": min(costs),
            "mean_cost": statistics.fmean(costs),
            "median_cost": statistics.median(costs),
            "stddev_cost": statistics.pstdev(costs),
            "mean_gap_pct": statistics.fmean(gaps),
            "mean_objective_evaluations": statistics.fmean(evaluations),
            "mean_elapsed_ms": statistics.fmean(elapsed),
            "median_elapsed_ms": statistics.median(elapsed),
            "replay_validation": "passed" if replay_ok else "not-requested",
        })
    return output


def run_native_pilot(
    config_path: str | Path,
    output_dir: str | Path,
    *,
    problem_loader: Callable[[], Iterable[Any]],
    registry_getter: Callable[[str], Any] = _registry_executor,
    repo_root: Optional[Path] = None,
    jit_preflight: Callable[[], None] = preflight_numba_objective,
) -> Dict[str, Any]:
    """Execute a deterministic, validated algorithm-native TSP/ATSP pilot."""
    config = load_native_pilot_config(config_path)
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    output = _prepare_output_dir(output_dir, config, root)
    validation: Dict[str, Any] = {"status": "failed", "checks": [], "error": None}
    try:
        resolved = resolve_problems(config, list(problem_loader()))
        executors: Dict[str, Callable[..., NativeRunResult]] = {}
        for algorithm_id in sorted(APPROVED_NATIVE_ALGORITHMS):
            executor = registry_getter(algorithm_id)
            if executor is None:
                raise NativePilotError(
                    f"approved algorithm is not registered: {algorithm_id}"
                )
            executors[algorithm_id] = executor
        jit_preflight()

        rows: List[Dict[str, Any]] = []
        for problem, matrix, matrix_sha256 in resolved:
            for replicate in range(config.runs):
                seed = config.manifest.paired_seed(problem.name, replicate)
                primary: Dict[str, Dict[str, Any]] = {}
                for algorithm_id in sorted(APPROVED_NATIVE_ALGORITHMS):
                    params = dict(config.algorithms[algorithm_id])
                    params["native_comparison"] = config.native_comparison
                    result, elapsed_ms = _run_executor(
                        executors[algorithm_id], problem, params, seed, replicate
                    )
                    row = _native_result_record(
                        result,
                        problem=problem,
                        matrix=matrix,
                        matrix_sha256=matrix_sha256,
                        algorithm_id=algorithm_id,
                        replicate=replicate,
                        seed=seed,
                        config=config,
                        elapsed_ms=elapsed_ms,
                        record_kind="primary",
                    )
                    rows.append(row)
                    primary[algorithm_id] = row
                if replicate in config.replay_replicates:
                    for algorithm_id in sorted(APPROVED_NATIVE_ALGORITHMS):
                        params = dict(config.algorithms[algorithm_id])
                        params["native_comparison"] = config.native_comparison
                        result, elapsed_ms = _run_executor(
                            executors[algorithm_id], problem, params, seed, replicate
                        )
                        replay = _native_result_record(
                            result,
                            problem=problem,
                            matrix=matrix,
                            matrix_sha256=matrix_sha256,
                            algorithm_id=algorithm_id,
                            replicate=replicate,
                            seed=seed,
                            config=config,
                            elapsed_ms=elapsed_ms,
                            record_kind="replay",
                        )
                        expected = primary[algorithm_id]
                        for field in _REPLAY_FIELDS:
                            if replay[field] != expected[field]:
                                raise NativePilotError(
                                    f"replay mismatch for {problem.name}/"
                                    f"{algorithm_id}/run-{replicate}: {field}"
                                )
                        rows.append(replay)

        validation.update({
            "status": "passed",
            "checks": [
                "strict-native-config",
                "problem-integrity",
                "numba-nopython",
                "native-manifest",
                "independent-objective",
                "paired-seeds",
                "replay",
                "protocol-isolation",
            ],
        })
        manifest = {
            "protocol_version": config.protocol_version,
            "comparison_regime": config.comparison_regime,
            "configuration": {
                "problems": list(config.problems),
                "algorithms": config.algorithms,
                "runs": config.runs,
                "base_seed": config.base_seed,
                "workers": config.workers,
                "replay_replicates": list(config.replay_replicates),
            },
            "environment": _environment_metadata(),
            "git": _git_metadata(root),
            "problems": [
                {
                    "name": problem.name,
                    "problem_type": problem.problem_type,
                    "dimension": len(matrix),
                    "matrix_sha256": matrix_hash,
                    "optimum": problem.optimal,
                }
                for problem, matrix, matrix_hash in resolved
            ],
        }
        aggregates = aggregate_native_records(rows, bool(config.replay_replicates))
        _json_atomic(output / "manifest.json", manifest)
        _jsonl_atomic(output / "runs.jsonl", rows)
        _csv_atomic(output / "aggregate.csv", aggregates)
        _json_atomic(output / "validation.json", validation)
        return {
            "output_dir": str(output),
            "records": len(rows),
            "validation": validation,
        }
    except Exception as exc:
        validation["error"] = str(exc)
        _json_atomic(output / "validation.json", validation)
        if isinstance(exc, FairPilotError):
            raise
        raise NativePilotError(str(exc)) from exc


def run_native_pilot_from_cli(
    config_path: str | Path,
    output_dir: str | Path,
    *,
    problem_loader: Callable[[], Iterable[Any]],
) -> int:
    try:
        result = run_native_pilot(
            config_path, output_dir, problem_loader=problem_loader
        )
    except FairPilotError as exc:
        print(f"[NATIVE PILOT ERROR] {exc}")
        return 1
    print(
        f"[NATIVE PILOT] validated {result['records']} records "
        f"in {result['output_dir']}"
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated UniRide algorithm-native TSP/ATSP pilot."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    from academic_benchmark.cli_engine import load_problems

    return run_native_pilot_from_cli(
        args.config, args.output, problem_loader=load_problems
    )


if __name__ == "__main__":
    raise SystemExit(main())