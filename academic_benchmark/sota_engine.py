#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide SOTA Engine — Benchmark Orchestration for SOTA TSP Solvers
===================================================================

Provides tuning, benchmarking, and parameter management for the SOTA
algorithm suite (E²BSO, R²DMA, P-AOEA, CGO, RUN, ALNS) implemented in
``uniride_core.algorithms.sota_tsp/``.

Re-implemented from master_sota_engine.py (removed during refactoring)
against the consolidated cli_engine.py patterns.

Usage:
    from academic_benchmark.sota_engine import (
        run_engine_tuning, run_engine_default, run_engine_with_params,
        run_sota_optuna_tuning,
    )
"""

import concurrent.futures
import dataclasses
import io
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from uniride_core.algorithms._platform import fix_windows_encoding
fix_windows_encoding()

# Prevent OpenBLAS/NumPy crashes in ProcessPoolExecutor workers
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from academic_benchmark.benchmark_utils import (
    TSPLIB_OPTIMALS,
    append_csv_row,
    compute_gap,
    format_time,
    generate_combinations,
    param_signature,
)
from academic_benchmark.param_spaces import SOTA_PARAM_SPACES
from uniride_core.algorithms.sota_tsp import (
    ALNSConfig,
    ALNS_TSP,
    CGOConfig,
    CGO_TSP,
    E2BSOTSPConfig,
    E2BSO_TSP,
    PAOEAConfig,
    PAOEA_TSP,
    R2DMATSPConfig,
    R2DMA_TSP,
    RUNConfig,
    RUN_TSP,
)

# ── SOTA Algorithm Registry ──────────────────────────────────────────────────

SOTA_ALGO_MAP: Dict[str, Tuple[Any, Any]] = {
    "E2BSO-TSP":     (E2BSO_TSP,     E2BSOTSPConfig),
    "R2DMA-TSP":     (R2DMA_TSP,     R2DMATSPConfig),
    "P-AOEA-TSP":    (PAOEA_TSP,     PAOEAConfig),
    "CGO-TSP":       (CGO_TSP,       CGOConfig),
    "RUN-TSP":       (RUN_TSP,       RUNConfig),
    "ALNS-TSP":      (ALNS_TSP,      ALNSConfig),
}

ALL_ALGOS: List[str] = list(SOTA_ALGO_MAP.keys())

# ── Problem Type Alias ───────────────────────────────────────────────────────

from uniride_core.models import ProblemInstance as TSPProblem

# ── Paths ────────────────────────────────────────────────────────────────────

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(_ENGINE_DIR, "sota_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_sota_param_space(algo_name: str) -> Dict[str, List[Any]]:
    """Return the DoE parameter space for a SOTA algorithm."""
    raw = algo_name.upper()
    if raw in SOTA_PARAM_SPACES:
        return {k: v["doe"] for k, v in SOTA_PARAM_SPACES[raw].items() if "doe" in v}
    return {}


def _build_sota_config(algo_name: str, params: Dict[str, Any], seed: int):
    """Build a SOTA config object from a parameter dict."""
    _, cfg_cls = SOTA_ALGO_MAP[algo_name]
    valid_fields = {f.name for f in dataclasses.fields(cfg_cls)}
    cfg_kwargs = {k: v for k, v in params.items() if k in valid_fields}
    cfg_kwargs["seed"] = seed
    return cfg_cls(**cfg_kwargs)


def _build_sota_parameter_space(algo_name: str) -> Dict[str, List[Any]]:
    """Build the DoE parameter space for a SOTA algorithm.

    Args:
        algo_name: SOTA algorithm name (e.g. "E2BSO-TSP").

    Returns:
        Dict mapping parameter name to list of discrete values.
    """
    return _get_sota_param_space(algo_name)


def _load_distance_matrix(problem):
    """Try to load the correct distance matrix from TSPLIB DB cache."""
    try:
        from academic_benchmark.tsplib_manager import get_distance_matrix
        db_path = os.path.join(_ENGINE_DIR, "tsplib_data", "tsplib.db")
        return get_distance_matrix(problem.name, db_path)
    except Exception:
        return None


# ── Single Experiment Runner ────────────────────────────────────────────────

def _run_single_sota_experiment(args: Tuple) -> Dict[str, Any]:
    """Worker function for running a single SOTA experiment.

    Args:
        args: (problem_dict, algo_name, params, seed, run_idx)

    Returns:
        Dict with tour_length, gap, time_ms, algorithm, problem, run_idx, seed.
    """
    problem_dict, algo_name, params, seed, run_idx = args

    cls, _ = SOTA_ALGO_MAP[algo_name]
    config = _build_sota_config(algo_name, params, seed)
    solver = cls(config=config)

    coords = problem_dict.get("coordinates", [])
    optimal = problem_dict.get("optimal")

    start_time = time.perf_counter()
    dist_matrix_np = _load_distance_matrix(type("P", (), {
        "name": problem_dict.get("name", ""),
        "coordinates": coords,
    })())

    if dist_matrix_np is not None:
        result = solver.solve_with_matrix(dist_matrix_np)
    else:
        result = solver.solve(coords)

    elapsed = time.perf_counter() - start_time

    tour_length = float(result.tour_length)
    gap_pct: Optional[float] = None
    if optimal and optimal > 0:
        gap_pct = round(((tour_length - optimal) / optimal) * 100, 4)

    return {
        "problem": problem_dict.get("name", "unknown"),
        "algorithm": algo_name,
        "run_idx": run_idx,
        "seed": seed,
        "tour_length": tour_length,
        "gap": gap_pct,
        "time_ms": round(elapsed * 1000, 2),
        "iterations": result.iterations,
        "error": None,
    }


# ── DOE Tuning ───────────────────────────────────────────────────────────────

def _run_engine_tuning(
    problems: List[TSPProblem],
    algos: List[str],
    n_runs: int,
    max_combos: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Run DoE parameter tuning for SOTA algorithms.

    Mirrors the Numba engine's _tune_parameters() but uses SOTA solvers
    from uniride_core.algorithms.sota_tsp/.

    Args:
        problems: List of TSPProblem instances.
        algos: SOTA algorithm names (e.g. ["E2BSO-TSP", "R2DMA-TSP"]).
        n_runs: Number of runs per parameter combination.
        max_combos: Max parameter combinations to try per (problem, algo).
        workers: Parallel worker count.
        metadata: Metadata dict to update with results.
        skip_cached: Skip already-completed combinations.

    Returns:
        Best parameters found per (problem, algorithm) pair.
    """
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})
    tuning_tasks: List[Tuple] = []

    for problem in problems:
        problem_dict = {
            "name": problem.name,
            "dimension": problem.dimension,
            "optimal": problem.optimal,
            "coordinates": problem.coordinates,
            "category": problem.category,
            "source": problem.source,
        }

        for algo in algos:
            if algo not in SOTA_ALGO_MAP:
                print(f"[WARN] Unknown SOTA algorithm: {algo}, skipping.")
                continue

            space = _get_sota_param_space(algo)
            if not space:
                # No DoE space defined — use defaults
                combos = [{}]
            else:
                combos = generate_combinations(space, max_combos)

            for combo in combos:
                base_params = {}
                base_params.update(combo)
                for run_idx in range(1, n_runs + 1):
                    tuning_tasks.append(
                        (problem_dict, algo, base_params, run_idx, run_idx)
                    )

    if not tuning_tasks:
        print("[INFO] No SOTA tuning tasks to run.")
        return best_params

    print(f"\n[START] SOTA TUNING ({len(tuning_tasks)} tasks, {workers} workers)")

    csv_path = os.path.join(RESULTS_DIR, "sota_tuning_progress.csv")
    fields = [
        "timestamp", "problem", "algorithm", "run_idx", "seed",
        "tour_length", "gap", "time_ms", "iterations",
    ]

    completed = 0
    total = len(tuning_tasks)

    def _on_result(result: Dict[str, Any]):
        nonlocal completed
        completed += 1

        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "algorithm": result["algorithm"],
            "run_idx": result["run_idx"],
            "seed": result["seed"],
            "tour_length": result["tour_length"],
            "gap": result["gap"] if result["gap"] is not None else "",
            "time_ms": result["time_ms"],
            "iterations": result.get("iterations", 0),
        }
        append_csv_row(csv_path, fields, row)

        # Track best
        best_key = f"{result['problem']}::{result['algorithm']}"
        current_best = best_params.get(best_key)
        if result["error"] is None:
            if current_best is None or result["tour_length"] < current_best.get("tour_length", float("inf")):
                best_params[best_key] = {
                    "problem": result["problem"],
                    "algorithm": result["algorithm"],
                    "tour_length": result["tour_length"],
                    "gap": result["gap"],
                    "time_ms": result["time_ms"],
                    "params": base_params,
                }

        gap_str = f"{result['gap']:.2f}%" if result["gap"] is not None else "N/A"
        print(
            f"  [{completed:>4}/{total}] {result['problem']:<12} "
            f"{result['algorithm']:<12} GAP: {gap_str:>8} "
            f"{result['time_ms']:>8.0f}ms",
            flush=True,
        )

    # Execute
    if workers <= 1:
        for task in tuning_tasks:
            result = _run_single_sota_experiment(task)
            _on_result(result)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_single_sota_experiment, t) for t in tuning_tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "problem": "unknown", "algorithm": "unknown",
                        "run_idx": 0, "seed": 0, "tour_length": float("inf"),
                        "gap": None, "time_ms": 0, "iterations": 0, "error": str(e),
                    }
                _on_result(result)

    metadata["best_params"] = best_params
    with open(os.path.join(RESULTS_DIR, "sota_best_params.json"), "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2, ensure_ascii=False)

    return best_params


# ── Bayesian Tuning (Optuna) ─────────────────────────────────────────────────

def _run_sota_optuna_tuning(
    problems: List[TSPProblem],
    algos: List[str],
    n_runs: int,
    max_combos: int,
    workers: int,
    metadata: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Run Bayesian parameter tuning for SOTA algorithms using Optuna.

    Args:
        problems: List of TSPProblem instances.
        algos: SOTA algorithm names.
        n_runs: Number of runs per parameter evaluation.
        max_combos: Max Optuna trials per (problem, algorithm).
        workers: Parallel worker count.
        metadata: Metadata dict.

    Returns:
        Best parameters found per (problem, algorithm) pair.
    """
    try:
        import optuna
    except ImportError:
        raise ImportError(
            "Optuna is required for Bayesian tuning. Install: pip install optuna"
        )

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})

    for problem in problems:
        problem_dict = {
            "name": problem.name,
            "dimension": problem.dimension,
            "optimal": problem.optimal,
            "coordinates": problem.coordinates,
            "category": problem.category,
            "source": problem.source,
        }

        for algo in algos:
            if algo not in SOTA_ALGO_MAP:
                print(f"[WARN] Unknown SOTA algorithm: {algo}, skipping.")
                continue

            space = _get_sota_param_space(algo)
            if not space:
                print(f"[INFO] No DoE space for {algo}, skipping Optuna tuning.")
                continue

            study_name = f"sota_{algo}_{problem.name}"
            study = optuna.create_study(
                study_name=study_name,
                direction="minimize",
                sampler=optuna.samplers.TPESampler(seed=42),
            )

            def _objective(trial: optuna.Trial, _algo=algo, _pd=problem_dict) -> float:
                params = {}
                for param_name, values in space.items():
                    if not values:
                        continue
                    if isinstance(values[0], int):
                        params[param_name] = trial.suggest_int(param_name, min(values), max(values))
                    elif isinstance(values[0], float):
                        params[param_name] = trial.suggest_float(param_name, min(values), max(values))
                    else:
                        params[param_name] = trial.suggest_categorical(param_name, values)

                total_length = 0.0
                for run_idx in range(1, n_runs + 1):
                    task = (_pd, algo, params, 42 + run_idx, run_idx)
                    result = _run_single_sota_experiment(task)
                    if result["error"]:
                        return float("inf")
                    total_length += result["tour_length"]
                return total_length / n_runs

            print(f"\n[OPTUNA] {algo} on {problem.name} ({max_combos} trials)")
            study.optimize(_objective, n_trials=max_combos)

            best_key = f"{problem.name}::{algo}"
            best_params[best_key] = {
                "problem": problem.name,
                "algorithm": algo,
                "tour_length": study.best_value,
                "params": study.best_params,
            }
            print(f"  Best: {study.best_value:.2f}  params={study.best_params}")

    metadata["best_params"] = best_params
    with open(os.path.join(RESULTS_DIR, "sota_optuna_best.json"), "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2, ensure_ascii=False)

    return best_params


# ── Default Benchmark ────────────────────────────────────────────────────────

def _run_engine_default(
    problems: List[TSPProblem],
    algos: List[str],
    n_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run SOTA benchmark with default parameters.

    Args:
        problems: List of TSPProblem instances.
        algos: SOTA algorithm names.
        n_runs: Number of runs per (problem, algorithm).
        workers: Parallel worker count.
        metadata: Metadata dict.

    Returns:
        List of result dicts.
    """
    tasks: List[Tuple] = []
    for problem in problems:
        problem_dict = {
            "name": problem.name,
            "dimension": problem.dimension,
            "optimal": problem.optimal,
            "coordinates": problem.coordinates,
            "category": problem.category,
            "source": problem.source,
        }
        for algo in algos:
            for run_idx in range(1, n_runs + 1):
                tasks.append((problem_dict, algo, {}, run_idx, run_idx))

    print(f"\n[START] SOTA DEFAULT BENCHMARK ({len(tasks)} tasks, {workers} workers)")

    results: List[Dict[str, Any]] = []

    if workers <= 1:
        for task in tasks:
            result = _run_single_sota_experiment(task)
            results.append(result)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_single_sota_experiment, t) for t in tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "problem": "unknown", "algorithm": "unknown",
                        "run_idx": 0, "seed": 0, "tour_length": float("inf"),
                        "gap": None, "time_ms": 0, "iterations": 0, "error": str(e),
                    }
                results.append(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"sota_default_{timestamp}.csv")
    if results:
        fields = list(results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)

    return results


# ── Benchmark with Custom Parameters ─────────────────────────────────────────

def _run_engine_with_params(
    problems: List[TSPProblem],
    algos: List[str],
    params: Dict[str, Dict[str, Any]],
    n_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run SOTA benchmark with custom (user-specified) parameters.

    Args:
        problems: List of TSPProblem instances.
        algos: SOTA algorithm names.
        params: Dict mapping algo_name -> param_dict.
        n_runs: Number of runs per (problem, algorithm).
        workers: Parallel worker count.
        metadata: Metadata dict.

    Returns:
        List of result dicts.
    """
    tasks: List[Tuple] = []
    for problem in problems:
        problem_dict = {
            "name": problem.name,
            "dimension": problem.dimension,
            "optimal": problem.optimal,
            "coordinates": problem.coordinates,
            "category": problem.category,
            "source": problem.source,
        }
        for algo in algos:
            algo_params = params.get(algo, {})
            for run_idx in range(1, n_runs + 1):
                tasks.append((problem_dict, algo, algo_params, run_idx, run_idx))

    print(f"\n[START] SOTA CUSTOM BENCHMARK ({len(tasks)} tasks, {workers} workers)")

    results: List[Dict[str, Any]] = []

    if workers <= 1:
        for task in tasks:
            result = _run_single_sota_experiment(task)
            results.append(result)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_single_sota_experiment, t) for t in tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "problem": "unknown", "algorithm": "unknown",
                        "run_idx": 0, "seed": 0, "tour_length": float("inf"),
                        "gap": None, "time_ms": 0, "iterations": 0, "error": str(e),
                    }
                results.append(result)

    return results


# ── Interactive Stubs (CLI menu helpers) ─────────────────────────────────────

def _manual_param_entry_interactive(algos: List[str]) -> Dict[str, Dict[str, Any]]:
    """Interactive parameter entry for SOTA algorithms.

    Args:
        algos: List of SOTA algorithm names.

    Returns:
        Dict mapping algo_name -> param_dict.
    """
    params: Dict[str, Dict[str, Any]] = {}
    for algo in algos:
        print(f"\n--- {algo} Parameters ---")
        space = _get_sota_param_space(algo)
        if not space:
            print("  (no DoE space defined, using defaults)")
            params[algo] = {}
            continue
        entry = {}
        for param_name, values in space.items():
            while True:
                raw = input(f"  {param_name} {values} [default={values[0]}]: ").strip()
                if not raw:
                    entry[param_name] = values[0]
                    break
                try:
                    # Try int first, then float
                    if "." in raw:
                        entry[param_name] = float(raw)
                    else:
                        entry[param_name] = int(raw)
                    break
                except ValueError:
                    print("    Invalid number, try again.")
        params[algo] = entry
    return params


def _load_params_from_db_interactive(
    problems: List[TSPProblem],
    algos: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Load best parameters from the parameter DB for given problems/algos."""
    from academic_benchmark.param_db import get_best_for

    params: Dict[str, Dict[str, Any]] = {}
    for algo in algos:
        for problem in problems:
            rec = get_best_for(problem.name, algo)
            if rec and rec.get("params"):
                params.setdefault(algo, {}).update(rec["params"])
    return params


def _save_best_to_param_db(
    best_params: Dict[str, Dict[str, Any]],
    problems: List[TSPProblem],
    algos: List[str],
) -> int:
    """Save best parameters to the parameter database.

    Returns number of entries saved.
    """
    from academic_benchmark.param_db import save_entry

    saved = 0
    for algo in algos:
        for problem in problems:
            key = f"{problem.name}::{algo}"
            if key in best_params:
                entry = best_params[key]
                save_entry(
                    problem=problem.name,
                    algorithm=algo,
                    params=entry.get("params", {}),
                    best_score=entry.get("tour_length", 0.0),
                    gap=entry.get("gap", 0.0),
                    runs=1,
                    dimension=problem.dimension,
                    category=problem.category,
                )
                saved += 1
    return saved


def _edit_param_space_interactive(algo_name: str) -> Dict[str, List[Any]]:
    """Interactively edit the parameter space for a SOTA algorithm."""
    space = _get_sota_param_space(algo_name)
    if not space:
        print(f"No DoE space defined for {algo_name}.")
        return {}
    print(f"\nCurrent parameter space for {algo_name}:")
    for k, v in space.items():
        print(f"  {k}: {v}")
    print("\nEnter new values (comma-separated) or press Enter to keep current.")
    edited = {}
    for param_name, current_values in space.items():
        raw = input(f"  {param_name} [{current_values}]: ").strip()
        if not raw:
            edited[param_name] = current_values
            continue
        try:
            values = [int(x.strip()) if "." not in x else float(x.strip()) for x in raw.split(",")]
            edited[param_name] = values
        except ValueError:
            print(f"    Invalid input, keeping {current_values}")
            edited[param_name] = current_values
    return edited


def _param_db_menu() -> None:
    """Interactive parameter database menu for SOTA results."""
    from academic_benchmark.param_db import list_entries

    entries = list_entries()
    if not entries:
        print("\nParameter database is empty.")
        return

    print(f"\n{'ID':>4} {'Timestamp':<20} {'Problem':<12} {'Algorithm':<12} {'Score':>10} {'Gap':>8}")
    print("-" * 72)
    for e in entries:
        print(f"{e['id']:>4} {e['timestamp']:<20} {e['problem']:<12} "
              f"{e['algorithm']:<12} {e.get('best_score', 0):>10.2f} "
              f"{e.get('gap', 0):>8.2f}%")


def load_problems(**kwargs) -> List[TSPProblem]:
    """Load problems — delegates to cli_engine's load_problems."""
    from academic_benchmark.cli_engine import load_problems as _load
    return _load(**kwargs)


# ── Aliases matching the old master_sota_engine API ─────────────────────────

run_engine_tuning = _run_engine_tuning
run_engine_default = _run_engine_default
run_engine_with_params = _run_engine_with_params
run_sota_optuna_tuning = _run_sota_optuna_tuning

def _select_problems_from_args(args, all_problems, interactive: bool = False):
    """Select problems from CLI args — delegates to ProblemSelector.

    Mirrors the Numba engine's _select_problems_from_args in cli_engine.py.
    """
    from academic_benchmark.benchmark_utils import ProblemSelector

    selector = ProblemSelector(all_problems)

    if args.select:
        return selector.quick_select(args.select)

    if args.problems:
        wanted = {x.strip().lower() for x in args.problems.split(",") if x.strip()}
        return [p for p in all_problems if p.name.lower() in wanted]

    if args.size_limit:
        return [p for p in all_problems if p.dimension <= args.size_limit]

    if interactive:
        return selector.interactive_select()

    return list(all_problems)
