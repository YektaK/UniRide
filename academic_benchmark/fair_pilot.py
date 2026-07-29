"""Isolated fair-comparison pilot runner for academic TSP/ATSP experiments.

This module intentionally bypasses the legacy benchmark engine's database and
CSV writers.  It runs only the registry's approved pure variants and writes
validated, self-contained artifacts to a caller-selected external directory.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from academic_benchmark.fairness import FairComparisonManifest, FairRunResult
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import (
    execute_preflighted,
    serialize_preflight_decision as _decision_metadata,
)
from academic_benchmark.core.preflight import (
    RuntimeBackendAvailability,
    probe_runtime_backends,
)
from academic_benchmark.core.problem_validation import validate_problem_for_preflight
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol

V1_PROTOCOL = "uniride-fair-tsp-v1"
V2_PROTOCOL = "uniride-fair-tsp-v2"
SUPPORTED_PROTOCOLS = frozenset({V1_PROTOCOL, V2_PROTOCOL})
FIXED_EVALUATION_REGIME = "fixed_evaluation_budget"
NATIVE_TERMINATION_REGIME = "algorithm_native_termination"
APPROVED_ALGORITHMS = frozenset({
    "Core-GWO-TSP-Pure",
    "Core-HHO-TSP-Pure",
    "Core-TwoOpt-TSP",
    "Core-ThreeOpt-TSP",
})
_V1_ALGORITHM_ALIASES = {
    "Numba-2-opt": "Core-TwoOpt-TSP",
    "Numba-3-opt-bounded": "Core-ThreeOpt-TSP",
}
_GWO_HHO = frozenset({"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"})
_CONFIG_KEYS_V1 = frozenset({
    "protocol_version", "problems", "algorithms", "runs", "evaluation_budget",
    "base_seed", "budget_policy", "workers", "replay_replicates",
    "allow_repository_output", "overwrite",
})
_CONFIG_KEYS_V2 = _CONFIG_KEYS_V1 | {"comparison_regime"}


class FairPilotError(RuntimeError):
    """A configuration or scientific-integrity failure in the fair pilot."""


@dataclass(frozen=True)
class FairPilotConfig:
    protocol_version: str
    problems: Tuple[str, ...]
    algorithms: Mapping[str, Mapping[str, Any]]
    runs: int
    evaluation_budget: int
    base_seed: int
    budget_policy: str
    comparison_regime: Optional[str]
    workers: int
    replay_replicates: Tuple[int, ...]
    allow_repository_output: bool
    overwrite: bool

    @property
    def manifest(self) -> FairComparisonManifest:
        return FairComparisonManifest(
            protocol_version=self.protocol_version,
            base_seed=self.base_seed,
            evaluation_budget=self.evaluation_budget,
            budget_policy=self.budget_policy,
            comparison_regime=self.comparison_regime,
        )

    @property
    def fair_comparison(self) -> Dict[str, Any]:
        value = {
            "protocol_version": self.protocol_version,
            "base_seed": self.base_seed,
            "evaluation_budget": self.evaluation_budget,
            "budget_policy": self.budget_policy,
        }
        if self.comparison_regime is not None:
            value["comparison_regime"] = self.comparison_regime
        return value


def _strict_int(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise FairPilotError(f"{name} must be an integer >= {minimum}")
    return value


def _strict_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise FairPilotError(f"{name} must be a boolean")
    return value


def _validate_v2_algorithm_policy(algorithms: Mapping[str, Mapping[str, Any]]) -> None:
    for algorithm_id in _GWO_HHO:
        block = algorithms[algorithm_id]
        forbidden = {"first_improvement", "window", "max_segment_length"} & block.keys()
        if forbidden:
            raise FairPilotError(
                f"{algorithm_id} cannot declare local-search policy fields: {sorted(forbidden)}"
            )

    two_opt = algorithms["Core-TwoOpt-TSP"]
    _strict_bool(two_opt.get("first_improvement"), "Core-TwoOpt-TSP.first_improvement")
    forbidden = {"window", "max_segment_length"} & two_opt.keys()
    if forbidden:
        raise FairPilotError(
            f"Core-TwoOpt-TSP cannot declare neighborhood-window fields: {sorted(forbidden)}"
        )

    three_opt = algorithms["Core-ThreeOpt-TSP"]
    _strict_bool(three_opt.get("first_improvement"), "Core-ThreeOpt-TSP.first_improvement")
    if "window" not in three_opt:
        raise FairPilotError("Core-ThreeOpt-TSP.window is required for protocol v2")
    _strict_int(three_opt["window"], "Core-ThreeOpt-TSP.window", 2)
    if "max_segment_length" in three_opt:
        raise FairPilotError(
            "Core-ThreeOpt-TSP.max_segment_length is ambiguous; use window"
        )


def load_fair_pilot_config(path: str | Path) -> FairPilotConfig:
    """Load a strictly validated JSON configuration; YAML is deliberately unsupported."""
    config_path = Path(path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FairPilotError(f"fair config does not exist: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise FairPilotError(f"fair config is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FairPilotError("fair config must be a JSON object")
    protocol_version = data.get("protocol_version")
    if protocol_version not in SUPPORTED_PROTOCOLS:
        raise FairPilotError(f"unsupported protocol_version: {protocol_version!r}")
    expected_keys = _CONFIG_KEYS_V2 if protocol_version == V2_PROTOCOL else _CONFIG_KEYS_V1
    missing = expected_keys - data.keys()
    extra = data.keys() - expected_keys
    if missing or extra:
        raise FairPilotError(
            f"fair config schema mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    comparison_regime = None
    if protocol_version == V2_PROTOCOL:
        comparison_regime = data["comparison_regime"]
        if comparison_regime == NATIVE_TERMINATION_REGIME:
            raise FairPilotError("algorithm_native_termination is not implemented")
        if comparison_regime != FIXED_EVALUATION_REGIME:
            raise FairPilotError(
                "protocol v2 comparison_regime must be 'fixed_evaluation_budget'"
            )
    problems = data["problems"]
    if (not isinstance(problems, list) or not problems or
            any(not isinstance(name, str) or not name.strip() for name in problems) or
            len(set(problems)) != len(problems)):
        raise FairPilotError("problems must be a non-empty list of unique names")
    algorithms = data["algorithms"]
    if protocol_version == V1_PROTOCOL and isinstance(algorithms, dict):
        canonical_algorithms: Dict[str, Any] = {}
        for requested_id, block in algorithms.items():
            canonical_id = _V1_ALGORITHM_ALIASES.get(requested_id, requested_id)
            if canonical_id in canonical_algorithms:
                raise FairPilotError(
                    f"duplicate canonical algorithm after v1 migration: {canonical_id}"
                )
            canonical_algorithms[canonical_id] = block
        algorithms = canonical_algorithms
    if not isinstance(algorithms, dict) or set(algorithms) != APPROVED_ALGORITHMS:
        raise FairPilotError(
            "algorithms must contain exactly the approved pure variants: "
            f"{sorted(APPROVED_ALGORITHMS)}"
        )
    if any(not isinstance(value, dict) for value in algorithms.values()):
        raise FairPilotError("each algorithm parameter block must be an object")
    if protocol_version == V2_PROTOCOL:
        _validate_v2_algorithm_policy(algorithms)
    runs = _strict_int(data["runs"], "runs", 1)
    evaluation_budget = _strict_int(data["evaluation_budget"], "evaluation_budget", 1)
    base_seed = _strict_int(data["base_seed"], "base_seed", 0)
    budget_policy = data["budget_policy"]
    if budget_policy != "atomic_upper_bound_v1":
        raise FairPilotError("budget_policy must be 'atomic_upper_bound_v1'")
    workers = _strict_int(data["workers"], "workers", 1)
    if workers != 1:
        raise FairPilotError("workers must be 1 for deterministic fair-pilot execution")
    replay_replicates = data["replay_replicates"]
    if (not isinstance(replay_replicates, list) or
            any(isinstance(item, bool) or not isinstance(item, int) for item in replay_replicates) or
            any(item < 0 or item >= runs for item in replay_replicates) or
            len(set(replay_replicates)) != len(replay_replicates)):
        raise FairPilotError("replay_replicates must be unique replicate indexes within runs")
    return FairPilotConfig(
        protocol_version=protocol_version,
        problems=tuple(problems), algorithms={key: dict(value) for key, value in algorithms.items()},
        runs=runs, evaluation_budget=evaluation_budget, base_seed=base_seed,
        budget_policy=budget_policy, comparison_regime=comparison_regime, workers=workers,
        replay_replicates=tuple(replay_replicates),
        allow_repository_output=_strict_bool(data["allow_repository_output"], "allow_repository_output"),
        overwrite=_strict_bool(data["overwrite"], "overwrite"),
    )


def _matrix_for_problem(problem: Any) -> List[List[float]]:
    try:
        return [list(row) for row in validate_problem_for_preflight(problem).matrix]
    except ValueError as exc:
        raise FairPilotError(str(exc)) from exc


def resolve_problems(config: FairPilotConfig, available: Iterable[Any]) -> List[Tuple[Any, List[List[float]], str]]:
    """Resolve exact selected problems and reject malformed/mismatched TSP/ATSP data."""
    by_name = {str(getattr(problem, "name", "")): problem for problem in available}
    resolved: List[Tuple[Any, List[List[float]], str]] = []
    types: set[str] = set()
    for name in config.problems:
        problem = by_name.get(name)
        if problem is None:
            raise FairPilotError(f"requested problem is unavailable: {name}")
        optimum = getattr(problem, "optimal", None)
        if not isinstance(optimum, (int, float)) or not math.isfinite(float(optimum)) or optimum <= 0:
            raise FairPilotError(f"{name}: a positive canonical optimum is required")
        try:
            report = validate_problem_for_preflight(problem)
        except ValueError as exc:
            raise FairPilotError(str(exc)) from exc
        matrix = report.matrix
        if report.dimension < 3:
            raise FairPilotError(f"{name}: matrix must be square with n >= 3")
        problem_type = report.contract.value
        if problem_type == "tsp" and report.observed_asymmetric:
            raise FairPilotError(f"{name}: TSP matrix is not symmetric")
        if problem_type == "atsp" and not report.observed_asymmetric:
            raise FairPilotError(f"{name}: ATSP matrix has no directed asymmetry")
        types.add(problem_type)
        resolved.append((problem, matrix, report.matrix_sha256))
    if types != {"tsp", "atsp"}:
        raise FairPilotError("the pilot configuration must include at least one TSP and one ATSP")
    return resolved


def preflight_numba_objective() -> None:
    """Compatibility wrapper requiring the canonical runtime Numba probe."""
    availability = probe_runtime_backends()
    if not availability.numba_nopython:
        raise FairPilotError(availability.detail)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _prepare_output_dir(path: str | Path, config: FairPilotConfig, repo_root: Path) -> Path:
    output = Path(path).expanduser().resolve()
    if _is_within(output, repo_root) and not config.allow_repository_output:
        raise FairPilotError("repository-contained output is forbidden unless allow_repository_output is true")
    if output.exists() and any(output.iterdir()) and not config.overwrite:
        raise FairPilotError("output directory is non-empty; set overwrite=true to reuse it")
    output.mkdir(parents=True, exist_ok=True)
    return output


def _json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _jsonl_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.replace(temporary, path)


def _csv_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _closed_cost(tour: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
    dimension = len(matrix)
    if len(tour) != dimension or set(tour) != set(range(1, dimension + 1)):
        raise FairPilotError("solver returned an incomplete or non-1-indexed tour")
    route = [node - 1 for node in tour]
    return float(sum(matrix[node][route[(index + 1) % dimension]] for index, node in enumerate(route)))


def _result_record(
    result: FairRunResult,
    *, problem: Any,
    matrix: Sequence[Sequence[float]],
    matrix_sha256: str,
    algorithm_id: str,
    replicate: int,
    seed: int,
    config: FairPilotConfig,
    decision: Any,
    elapsed_ms: float,
    record_kind: str,
) -> Dict[str, Any]:
    manifest = config.manifest
    try:
        manifest.validate_result(result)
    except ValueError as exc:
        raise FairPilotError(f"{problem.name}/{algorithm_id}/run-{replicate}: fairness validation failed: {exc}") from exc
    independent = _closed_cost(result.tour, matrix)
    if not math.isclose(float(result.objective_cost), independent, rel_tol=0.0, abs_tol=1e-8):
        raise FairPilotError(f"{problem.name}/{algorithm_id}/run-{replicate}: objective differs from independent cycle cost")
    optimum = float(problem.optimal)
    return {
        "record_kind": record_kind,
        "protocol_version": config.protocol_version,
        "comparison_regime": result.comparison_regime,
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
        "evaluation_budget": config.evaluation_budget,
        "objective_evaluations": result.objective_evaluations,
        "budget_terminated": result.budget_terminated,
        "iterations": result.iterations,
        "tour": list(result.tour),
        "objective_cost": float(result.objective_cost),
        "independent_objective_cost": independent,
        "gap_pct": ((float(result.objective_cost) - optimum) / optimum) * 100.0,
        "elapsed_ms": elapsed_ms,
        **_decision_metadata(decision),
        "validation_status": "passed",
    }


def _run_executor(executor: Callable[..., FairRunResult], problem: Any, params: Mapping[str, Any], seed: int, replicate: int) -> Tuple[FairRunResult, float]:
    started = time.perf_counter()
    result = executor(problem, dict(params), seed, replicate)
    return result, (time.perf_counter() - started) * 1000.0


def _execute_preflighted_run(
    *,
    requested_algorithm_id: str,
    identifier_source: IdentifierSource,
    problem: object,
    params: Mapping[str, Any],
    seed: int,
    run_idx: int,
    protocol: ExecutionProtocol,
    backend_policy: BackendPolicy,
    evaluation_budget: int | None,
    registered_algorithm_ids: frozenset[str],
    runtime_backends: RuntimeBackendAvailability,
    registry_getter: Callable[[str], Callable[..., FairRunResult]],
    gateway_executor: Callable[..., Any] = execute_preflighted,
) -> tuple[FairRunResult, Any, float]:
    """Execute one pilot run only through the decision-bound gateway."""
    started = time.perf_counter()
    result, decision = gateway_executor(
        requested_algorithm_id=requested_algorithm_id,
        identifier_source=identifier_source,
        problem=problem,
        params=params,
        seed=seed,
        run_idx=run_idx,
        protocol=protocol,
        backend_policy=backend_policy,
        evaluation_budget=evaluation_budget,
        registered_algorithm_ids=registered_algorithm_ids,
        runtime_backends=runtime_backends,
        registry_getter=registry_getter,
    )
    return result, decision, (time.perf_counter() - started) * 1000.0



def _registered_algorithm_ids() -> frozenset[str]:
    from academic_benchmark.engine_core import AlgorithmRegistry
    import academic_benchmark.core.registry_setup  # noqa: F401

    return frozenset(AlgorithmRegistry.list_algorithms())


def _backend_policy(algorithm_id: str) -> BackendPolicy:
    if algorithm_id in _GWO_HHO:
        return BackendPolicy.REQUIRE_NUMBA_OBJECTIVE
    return BackendPolicy.PYTHON_ONLY


def _git_metadata(repo_root: Path) -> Dict[str, Any]:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip())
        return {"revision": revision, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}


def _environment_metadata() -> Dict[str, Any]:
    versions: Dict[str, Any] = {"python": sys.version}
    for package in ("numpy", "numba", "llvmlite"):
        try:
            module = __import__(package)
            versions[package] = getattr(module, "__version__", None)
        except Exception:
            versions[package] = None
    return versions


def _aggregate(rows: Sequence[Mapping[str, Any]], replay_ok: bool) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for row in rows:
        if row["record_kind"] == "primary":
            groups.setdefault((str(row["problem"]), str(row["algorithm_id"])), []).append(row)
    output: List[Dict[str, Any]] = []
    for (problem, algorithm), values in sorted(groups.items()):
        costs = [float(item["objective_cost"]) for item in values]
        gaps = [float(item["gap_pct"]) for item in values]
        elapsed = [float(item["elapsed_ms"]) for item in values]
        evaluations = [int(item["objective_evaluations"]) for item in values]
        output.append({
            "problem": problem, "algorithm_id": algorithm, "runs": len(values),
            "best_cost": min(costs), "mean_cost": statistics.fmean(costs),
            "median_cost": statistics.median(costs), "stddev_cost": statistics.pstdev(costs),
            "mean_gap_pct": statistics.fmean(gaps), "mean_objective_evaluations": statistics.fmean(evaluations),
            "budget_terminated_count": sum(bool(item["budget_terminated"]) for item in values),
            "mean_elapsed_ms": statistics.fmean(elapsed), "median_elapsed_ms": statistics.median(elapsed),
            "replay_validation": "passed" if replay_ok else "not-requested",
        })
    return output


def _registry_executor(algorithm_id: str) -> Callable[..., FairRunResult]:
    """Lazily populate the registry so injected test runners avoid JIT imports."""
    from academic_benchmark.engine_core import AlgorithmRegistry
    import academic_benchmark.core.registry_setup  # noqa: F401
    return AlgorithmRegistry.get_executor(algorithm_id)


def run_fair_pilot(
    config_path: str | Path,
    output_dir: str | Path,
    *,
    problem_loader: Callable[[], Iterable[Any]],
    registry_getter: Callable[[str], Any] = _registry_executor,
    repo_root: Optional[Path] = None,
    runtime_probe: Callable[[], RuntimeBackendAvailability] = probe_runtime_backends,
    registered_algorithms_provider: Callable[[], Iterable[str]] = _registered_algorithm_ids,
    gateway_executor: Callable[..., Any] = execute_preflighted,
) -> Dict[str, Any]:
    """Execute a small, deterministic, validated fair TSP/ATSP pilot."""
    config = load_fair_pilot_config(config_path)
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    output = _prepare_output_dir(output_dir, config, root)
    validation: Dict[str, Any] = {"status": "failed", "checks": [], "error": None}
    try:
        available = list(problem_loader())
        resolved = resolve_problems(config, available)
        runtime_backends = runtime_probe()
        registered_algorithm_ids = frozenset(registered_algorithms_provider())
        rows: List[Dict[str, Any]] = []
        replay_ok = True
        for problem, matrix, matrix_sha256 in resolved:
            for replicate in range(config.runs):
                seed = config.manifest.paired_seed(problem.name, replicate)
                primary: Dict[str, Dict[str, Any]] = {}
                for algorithm_id in sorted(APPROVED_ALGORITHMS):
                    params = dict(config.algorithms[algorithm_id])
                    params["fair_comparison"] = config.fair_comparison
                    result, decision, elapsed_ms = _execute_preflighted_run(
                        requested_algorithm_id=algorithm_id,
                        identifier_source=IdentifierSource.MANIFEST,
                        problem=problem,
                        params=params,
                        seed=seed,
                        run_idx=replicate,
                        protocol=ExecutionProtocol.FIXED_BUDGET,
                        backend_policy=_backend_policy(algorithm_id),
                        evaluation_budget=config.evaluation_budget,
                        registered_algorithm_ids=registered_algorithm_ids,
                        runtime_backends=runtime_backends,
                        registry_getter=registry_getter,
                        gateway_executor=gateway_executor,
                    )
                    row = _result_record(result, problem=problem, matrix=matrix, matrix_sha256=matrix_sha256,
                                         algorithm_id=algorithm_id, replicate=replicate, seed=seed,
                                         config=config, decision=decision,
                                         elapsed_ms=elapsed_ms, record_kind="primary")
                    rows.append(row)
                    primary[algorithm_id] = row
                if replicate in config.replay_replicates:
                    for algorithm_id in sorted(APPROVED_ALGORITHMS):
                        params = dict(config.algorithms[algorithm_id])
                        params["fair_comparison"] = config.fair_comparison
                        result, decision, elapsed_ms = _execute_preflighted_run(
                            requested_algorithm_id=algorithm_id,
                            identifier_source=IdentifierSource.MANIFEST,
                            problem=problem,
                            params=params,
                            seed=seed,
                            run_idx=replicate,
                            protocol=ExecutionProtocol.FIXED_BUDGET,
                            backend_policy=_backend_policy(algorithm_id),
                            evaluation_budget=config.evaluation_budget,
                            registered_algorithm_ids=registered_algorithm_ids,
                            runtime_backends=runtime_backends,
                            registry_getter=registry_getter,
                            gateway_executor=gateway_executor,
                        )
                        replay = _result_record(result, problem=problem, matrix=matrix, matrix_sha256=matrix_sha256,
                                                algorithm_id=algorithm_id, replicate=replicate, seed=seed,
                                                config=config, decision=decision,
                                                elapsed_ms=elapsed_ms, record_kind="replay")
                        expected = primary[algorithm_id]
                        for field in ("tour", "objective_cost", "objective_evaluations", "budget_terminated", "seed", "seed_group"):
                            if replay[field] != expected[field]:
                                raise FairPilotError(f"replay mismatch for {problem.name}/{algorithm_id}/run-{replicate}: {field}")
                        rows.append(replay)
        validation.update({"status": "passed", "checks": ["strict-config", "problem-integrity", "runtime-backend-probe", "preflight-gateway", "fairness-manifest", "independent-objective", "replay"]})
        manifest = {
            "protocol_version": config.protocol_version,
            "configuration": {
                "problems": list(config.problems), "algorithms": config.algorithms, "runs": config.runs,
                "evaluation_budget": config.evaluation_budget, "base_seed": config.base_seed,
                "budget_policy": config.budget_policy, "comparison_regime": config.comparison_regime,
                "workers": config.workers,
                "replay_replicates": list(config.replay_replicates),
            },
            "environment": _environment_metadata(), "git": _git_metadata(root),
            "problems": [{"name": problem.name, "problem_type": problem.problem_type,
                          "dimension": len(matrix), "matrix_sha256": matrix_hash,
                          "optimum": problem.optimal} for problem, matrix, matrix_hash in resolved],
        }
        _json_atomic(output / "manifest.json", manifest)
        _jsonl_atomic(output / "runs.jsonl", rows)
        _csv_atomic(output / "aggregate.csv", _aggregate(rows, bool(config.replay_replicates)))
        _json_atomic(output / "validation.json", validation)
        return {"output_dir": str(output), "records": len(rows), "validation": validation}
    except Exception as exc:
        validation["error"] = str(exc)
        _json_atomic(output / "validation.json", validation)
        if isinstance(exc, FairPilotError):
            raise
        raise FairPilotError(str(exc)) from exc


def run_fair_pilot_from_cli(config_path: str | Path, output_dir: str | Path, *, problem_loader: Callable[[], Iterable[Any]]) -> int:
    try:
        result = run_fair_pilot(config_path, output_dir, problem_loader=problem_loader)
    except FairPilotError as exc:
        print(f"[FAIR PILOT ERROR] {exc}")
        return 1
    print(f"[FAIR PILOT] validated {result['records']} records in {result['output_dir']}")
    return 0
