"""
YAEM 2026 — HHO vs GWO TSP/VRP Benchmark Runner

Replicates the YAEM 2026 methodology (Optuna DOE → TSPLIB
benchmark → real-world Student Time Matrix validation) with HHO and GWO
replacing GA and PSO.

Two variants per algorithm:
  - "Pure"  (Core-GWO-TSP-Pure / Core-HHO-TSP-Pure): no built-in 2-opt
    polish — fair comparison against 2-opt/3-opt baselines
  - "Memetic" (Core-GWO-TSP / Core-HHO-TSP): bildiri2026 memetic hybrid with
    300-iteration final 2-opt — best absolute solution quality

Usage:
    python benchmark_runner.py --mode tune          # Taguchi DOE on 5 problems
    python benchmark_runner.py --mode benchmark      # full TSPLIB benchmark
    python benchmark_runner.py --mode timematrix     # Student Time Matrix
    python benchmark_runner.py --mode all            # everything in sequence
"""

import os
import sys
import json
import csv
import math
import time
import random
import itertools
import statistics
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

# Ensure the project root is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from academic_benchmark.engine_core import AlgorithmRegistry, RunResult
from uniride_core.algorithms.tsplib_parser import (
    parse_tsplib_file,
    TSPLIB_OPTIMALS,
    download_tsplib_problem,
    TSPLIB_DATA_DIR,
)
from academic_benchmark.param_spaces import (
    NUMBA_PARAM_SPACES,
    build_doe_space,
)

# Also register the algorithms if not yet loaded
import academic_benchmark.core.registry_setup  # noqa: F401 — registers Core-* variants


# ── Configuration ──────────────────────────────────────────────────────────────

YAEM_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(YAEM_DIR, "results")
TSPLIB_CACHE = os.path.join(YAEM_DIR, "data", "tsplib")
TIMEMATRIX_DIR = os.path.join(YAEM_DIR, "data", "timematrix")

# The 5-problem tuning set
TUNE_PROBLEMS = ["berlin52", "eil51", "st70", "kroA100", "rd100"]

# YAEM 2026 algorithm variants
VARIANTS = {
    "HHO-Pure":     "Core-HHO-TSP-Pure",
    "GWO-Pure":     "Core-GWO-TSP-Pure",
    "HHO-Memetic":  "Core-HHO-TSP",
    "GWO-Memetic":  "Core-GWO-TSP",
}


# ── Problem Loading ────────────────────────────────────────────────────────────

FALLBACK_CACHES = [
    os.path.join(os.path.dirname(YAEM_DIR), "bildiri2026", "data", "tsplib"),
    TSPLIB_DATA_DIR,
]


def _load_tsplib_problem(name: str) -> Optional[Dict[str, Any]]:
    """Load a TSPLIB problem from cache, with fallback and download."""
    os.makedirs(TSPLIB_CACHE, exist_ok=True)
    name_lower = name.lower()
    tsp_path = os.path.join(TSPLIB_CACHE, f"{name_lower}.tsp")

    if not os.path.exists(tsp_path):
        for fallback in FALLBACK_CACHES:
            candidate = os.path.join(fallback, f"{name_lower}.tsp")
            if os.path.exists(candidate):
                try:
                    import shutil
                    shutil.copy2(candidate, tsp_path)
                    print(f"  [CACHE] Copied {name_lower}.tsp from {fallback}")
                    break
                except Exception:
                    continue
        else:
            try:
                print(f"  [DOWNLOAD] Fetching {name_lower}.tsp...")
                download_tsplib_problem(name, TSPLIB_CACHE)
            except Exception as e:
                print(f"  [WARN] Could not download {name}: {e}")
                return None

    try:
        return parse_tsplib_file(tsp_path)
    except Exception as e:
        print(f"  [WARN] Could not parse {name}: {e}")
        return None


def _compute_gap(tour_cost: float, problem_name: str) -> Optional[float]:
    """Compute optimality gap percentage."""
    opt = TSPLIB_OPTIMALS.get(problem_name.lower())
    if opt and opt > 0:
        return (tour_cost - opt) / opt * 100.0
    return None


# ── Algorithm Execution ────────────────────────────────────────────────────────

def _run_single(
    algo_registry_name: str,
    problem_data: Dict[str, Any],
    params: Dict[str, Any],
    seed: int,
    run_idx: int,
) -> Optional[RunResult]:
    """Execute one algorithm run through the AlgorithmRegistry."""
    try:
        executor = AlgorithmRegistry.get_executor(algo_registry_name)
    except ValueError:
        print(f"  [ERROR] Algorithm '{algo_registry_name}' not registered.")
        return None

    # Build a minimal ProblemInstance
    from uniride_core.models import ProblemInstance
    coords = problem_data.get("coordinates", [])
    is_tm = "time_matrix" in problem_data
    prob = ProblemInstance(
        name=problem_data.get("name", "unknown"),
        dimension=problem_data.get("dimension", len(coords)),
        coordinates=coords if not is_tm else None,
        optimal=TSPLIB_OPTIMALS.get(problem_data.get("name", "").lower()),
        is_time_matrix=is_tm,
        time_matrix=problem_data.get("time_matrix") if is_tm else None,
    )

    try:
        result = executor(prob, params, seed, run_idx)
        return result
    except Exception as e:
        print(f"  [ERROR] Run {run_idx} failed: {e}")
        return None


# ── Taguchi DOE Tuning ─────────────────────────────────────────────────────────

def _generate_taguchi_grid(algo_space: Dict[str, List[Any]], max_combos: int = 81) -> List[Dict[str, Any]]:
    """Generate full-factorial DOE grid from param space."""
    keys = list(algo_space.keys())
    values = [algo_space[k] for k in keys]
    combos = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    if len(combos) > max_combos:
        rng = random.Random(42)
        combos = rng.sample(combos, max_combos)
    return combos


def tune_variant(
    variant_name: str,
    registry_name: str,
    problems: List[str],
    runs_per_combo: int = 3,
    max_combos: int = 81,
) -> Dict[str, Any]:
    """Run Taguchi DOE tuning for one algorithm variant."""
    # Find the right param space key
    param_key = variant_name.split("-")[0] + "-Pure" if "Pure" in variant_name else variant_name.split("-")[0]
    if param_key not in NUMBA_PARAM_SPACES:
        # Fallback: try the variant name directly
        param_key = variant_name
    space = NUMBA_PARAM_SPACES.get(param_key, NUMBA_PARAM_SPACES.get("GWO-Pure", {}))
    doe_space = {k: v["doe"] for k, v in space.items()}

    all_combos = _generate_taguchi_grid(doe_space, max_combos)
    print(f"\n  [{variant_name}] {len(all_combos)} parameter combinations x {runs_per_combo} runs")

    per_problem_results: Dict[str, List[Tuple[float, Dict[str, Any]]]] = {}

    for prob_name in problems:
        print(f"    Tuning on {prob_name}...")
        prob_data = _load_tsplib_problem(prob_name)
        if prob_data is None:
            continue
        prob_data["name"] = prob_name

        results: List[Tuple[float, Dict[str, Any]]] = []

        with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            futures = {}
            for cidx, combo_params in enumerate(all_combos):
                for run in range(runs_per_combo):
                    seed = 10000 + cidx * 10 + run
                    f = pool.submit(_run_single, registry_name, prob_data, combo_params, seed, run + 1)
                    futures[f] = (cidx, combo_params)

            for f in as_completed(futures):
                cidx, combo_params = futures[f]
                r = f.result()
                if r is not None and r.gap_pct is not None:
                    results.append((r.tour_cost, combo_params))

        per_problem_results[prob_name] = results

    # Aggregate: pick the params with lowest mean cost across all 5 problems
    combo_scores: Dict[str, List[float]] = {}
    for prob_name, res_list in per_problem_results.items():
        for cost, params in res_list:
            key = json.dumps(params, sort_keys=True)
            if key not in combo_scores:
                combo_scores[key] = []
            combo_scores[key].append(cost)

    best_key = min(combo_scores, key=lambda k: statistics.mean(combo_scores[k]))
    best_params = json.loads(best_key)
    best_mean = statistics.mean(combo_scores[best_key])

    print(f"    Best params: {best_params} (mean cost: {best_mean:.2f})")
    return {
        "variant": variant_name,
        "registry_name": registry_name,
        "parameters": best_params,
        "best_mean_cost": best_mean,
        "search_space": doe_space,
        "timestamp": datetime.now().isoformat(),
    }


# ── Benchmark Runner ───────────────────────────────────────────────────────────

def run_benchmark(
    tuned_db: List[Dict[str, Any]],
    problem_names: List[str],
    num_runs: int = 30,
    label: str = "benchmark",
) -> List[Dict[str, Any]]:
    """Run tuned models on a set of TSPLIB problems."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"{label}_{timestamp}.csv")

    all_results: List[Dict[str, Any]] = []

    header = ["problem", "algorithm", "variant", "run", "seed", "tour_cost",
              "gap_pct", "elapsed_sec", "dimension"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

    for prob_name in problem_names:
        prob_data = _load_tsplib_problem(prob_name)
        if prob_data is None:
            continue
        prob_data["name"] = prob_name
        dim = prob_data.get("dimension", 0)

        print(f"\n  Problem: {prob_name} (n={dim})")

        for entry in tuned_db:
            variant = entry["variant"]
            registry_name = entry["registry_name"]
            params = entry["parameters"]
            print(f"    {variant}: {num_runs} runs...", end=" ", flush=True)

            run_results: List[Dict[str, Any]] = []

            with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
                futures = {}
                for run in range(num_runs):
                    seed = 20000 + run + hash(variant) % 10000
                    f = pool.submit(_run_single, registry_name, prob_data, params, seed, run + 1)
                    futures[f] = run + 1

                for f in as_completed(futures):
                    run_idx = futures[f]
                    r = f.result()
                    if r is not None:
                        row = {
                            "problem": prob_name,
                            "algorithm": variant.split("-")[0],
                            "variant": variant,
                            "run": run_idx,
                            "seed": r.seed,
                            "tour_cost": r.tour_cost,
                            "gap_pct": r.gap_pct,
                            "elapsed_sec": r.elapsed_sec,
                            "dimension": dim,
                        }
                        run_results.append(row)
                        all_results.append(row)

            costs = [rr["tour_cost"] for rr in run_results]
            gaps = [rr["gap_pct"] for rr in run_results if rr["gap_pct"] is not None]
            if costs:
                print(f"mean={statistics.mean(costs):.1f} "
                      f"gap={statistics.mean(gaps):.2f}%" if gaps else "done")

            # Append to CSV
            with open(csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                for row in run_results:
                    writer.writerow([row[h] for h in header])

    # Summary table
    print(f"\n  Results saved to: {csv_path}")
    _print_summary(all_results)

    return all_results


def _print_summary(results: List[Dict[str, Any]]):
    """Print a grouped summary table."""
    groups: Dict[str, List[float]] = {}
    for r in results:
        key = f"{r['variant']} on {r['problem']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(r["tour_cost"])

    print(f"\n  {'Variant':<25} {'Problem':<12} {'Mean':>10} {'Std':>8} {'Min':>10} {'Max':>10}")
    print("  " + "-" * 75)
    for key, costs in sorted(groups.items()):
        parts = key.split(" on ")
        variant, prob = parts[0], parts[1] if len(parts) > 1 else "?"
        m = statistics.mean(costs)
        s = statistics.stdev(costs) if len(costs) > 1 else 0
        mn = min(costs)
        mx = max(costs)
        print(f"  {variant:<25} {prob:<12} {m:>10.1f} {s:>8.1f} {mn:>10.1f} {mx:>10.1f}")


# ── Time Matrix Benchmark ──────────────────────────────────────────────────────

def create_sample_time_matrix(n_students: int = 29, seed: int = 42) -> List[List[float]]:
    """Create a synthetic Student Time Matrix for testing."""
    rng = random.Random(seed)
    n = n_students + 1
    coords = [(0.0, 0.0)] + [(rng.uniform(-15, 15), rng.uniform(-15, 15))
                             for _ in range(n_students)]
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dx = coords[i][0] - coords[j][0]
                dy = coords[i][1] - coords[j][1]
                dist = math.sqrt(dx * dx + dy * dy)
                matrix[i][j] = round(dist / 20 * 60, 2)
    return matrix


def load_time_matrix(matrix_path: str) -> List[List[float]]:
    """Load time matrix from JSON file, or create sample if not found."""
    if os.path.exists(matrix_path):
        with open(matrix_path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("time_matrix", [])
    return create_sample_time_matrix()


def run_timematrix_benchmark(
    tuned_db: List[Dict[str, Any]],
    time_matrix: List[List[float]],
    num_runs: int = 30,
    label: str = "timematrix",
) -> List[Dict[str, Any]]:
    """Run tuned models on real-world Student Time Matrix."""
    n = len(time_matrix)
    n_students = n - 1
    print(f"\n  Students: {n_students}, Matrix size: {n}x{n}")

    prob_data = {
        "name": f"students_{n_students}",
        "dimension": n_students,
        "coordinates": None,
        "time_matrix": time_matrix,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"{label}_{timestamp}.csv")
    all_results: List[Dict[str, Any]] = []

    header = ["problem", "algorithm", "variant", "run", "seed",
              "tour_cost", "elapsed_sec"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

    for entry in tuned_db:
        variant = entry["variant"]
        registry_name = entry["registry_name"]
        params = entry["parameters"]
        print(f"    {variant}: {num_runs} runs...", end=" ", flush=True)

        run_results: List[Dict[str, Any]] = []

        with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            futures = {}
            for run in range(num_runs):
                seed = 30000 + run + hash(variant) % 10000
                f = pool.submit(_run_single, registry_name, prob_data, params, seed, run + 1)
                futures[f] = run + 1

            for f in as_completed(futures):
                run_idx = futures[f]
                r = f.result()
                if r is not None:
                    row = {
                        "problem": prob_data["name"],
                        "algorithm": variant.split("-")[0],
                        "variant": variant,
                        "run": run_idx,
                        "seed": r.seed,
                        "tour_cost": r.tour_cost,
                        "elapsed_sec": r.elapsed_sec,
                    }
                    run_results.append(row)
                    all_results.append(row)

        costs = [rr["tour_cost"] for rr in run_results]
        if costs:
            print(f"mean={statistics.mean(costs):.1f} min={min(costs):.1f}")

        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            for row in run_results:
                writer.writerow([row[h] for h in header])

    _print_summary(all_results)
    return all_results


# ── CLI ────────────────────────────────────────────────────────────────────────

def _ensure_registry():
    """Warm up the algorithm registry to verify all variants exist."""
    available = AlgorithmRegistry.list_algorithms()
    for name, reg_name in VARIANTS.items():
        if reg_name in available:
            print(f"  [OK] {name:15} → {reg_name}")
        else:
            print(f"  [WARN] {name:15} → {reg_name} NOT REGISTERED")


def main():
    parser = argparse.ArgumentParser(description="YAEM 2026 Benchmark Runner")
    parser.add_argument("--mode", choices=["tune", "benchmark", "timematrix", "all", "check"],
                        default="check", help="Execution mode")
    parser.add_argument("--runs", type=int, default=30, help="Runs per variant per problem")
    parser.add_argument("--tune-runs", type=int, default=3, help="Runs per DOE combination")
    parser.add_argument("--max-combos", type=int, default=81, help="Max Taguchi combinations per algo")
    parser.add_argument("--problems", nargs="+", default=TUNE_PROBLEMS,
                        help="TSPLIB problems for benchmark")
    parser.add_argument("--matrix-file", help="Time matrix JSON file path")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(TSPLIB_CACHE, exist_ok=True)
    os.makedirs(TIMEMATRIX_DIR, exist_ok=True)

    print("=" * 70)
    print("YAEM 2026 — HHO vs GWO Benchmark Suite")
    print("=" * 70)
    print(f"\nRegistered algorithms:")
    _ensure_registry()

    if args.mode == "check":
        print("\nReady. Use --mode tune|benchmark|timematrix|all to run.")
        return

    tuned_db_path = os.path.join(RESULTS_DIR, "tuned_params.json")

    # ── Step 1: Tune ──────────────────────────────────────────────────────
    if args.mode in ("tune", "all"):
        print(f"\n{'='*70}")
        print("STEP 1: Taguchi DOE Parameter Tuning")
        print(f"{'='*70}")
        print(f"  Problems: {args.problems}")
        print(f"  Runs/combo: {args.tune_runs}, Max combos: {args.max_combos}")

        tuned_db = []
        for variant_name, registry_name in VARIANTS.items():
            result = tune_variant(
                variant_name, registry_name, args.problems,
                runs_per_combo=args.tune_runs, max_combos=args.max_combos,
            )
            tuned_db.append(result)

        with open(tuned_db_path, "w") as f:
            json.dump(tuned_db, f, indent=2)
        print(f"\n  Tuned parameters saved to: {tuned_db_path}")

    # ── Step 2: Benchmarks ────────────────────────────────────────────────
    if args.mode in ("benchmark", "all"):
        print(f"\n{'='*70}")
        print("STEP 2: TSPLIB Benchmark")
        print(f"{'='*70}")

        if args.mode == "all":
            with open(tuned_db_path) as f:
                tuned_db = json.load(f)
        else:
            tuned_db_path_alt = tuned_db_path
            if os.path.exists(tuned_db_path_alt):
                with open(tuned_db_path_alt) as f:
                    tuned_db = json.load(f)
            else:
                print("  [ERROR] No tuned params found. Run --mode tune first.")
                return

        run_benchmark(tuned_db, args.problems, num_runs=args.runs, label="tsplib_benchmark")

    # ── Step 3: Time Matrix ───────────────────────────────────────────────
    if args.mode in ("timematrix", "all"):
        print(f"\n{'='*70}")
        print("STEP 3: Student Time Matrix Validation")
        print(f"{'='*70}")

        if args.mode == "all":
            with open(tuned_db_path) as f:
                tuned_db = json.load(f)
        else:
            if os.path.exists(tuned_db_path):
                with open(tuned_db_path) as f:
                    tuned_db = json.load(f)
            else:
                print("  [ERROR] No tuned params found. Run --mode tune first.")
                return

        matrix = load_time_matrix(args.matrix_file or os.path.join(TIMEMATRIX_DIR, "time_matrix.json"))
        run_timematrix_benchmark(tuned_db, matrix, num_runs=args.runs, label="timematrix")

    print(f"\n{'='*70}")
    print("DONE.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
