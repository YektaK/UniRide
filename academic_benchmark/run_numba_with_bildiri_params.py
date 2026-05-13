#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run master_numba_engine benchmark using tuned parameters from bildiri2026.

This script does not modify any existing engine logic or defaults. It only
loads tuned parameters, maps them to the Numba engine parameter schema, and
runs a benchmark with a separate output directory.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from academic_benchmark import master_numba_engine as mne

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "bildiri2026",
    "data",
    "tuned_parameters_db.json",
)

DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "numba_results",
    "bildiri_import",
)


def _load_bildiri_db(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"DB file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("DB file must contain a list of entries")
    return data


def _select_best_entries(entries: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in entries:
        problem = str(item.get("problem", "")).strip().lower()
        algorithm = str(item.get("algorithm", "")).strip()
        if not problem or not algorithm:
            continue
        key = (problem, algorithm)
        score = float(item.get("best_mean_length", float("inf")))
        current = best.get(key)
        if current is None or score < float(current.get("best_mean_length", float("inf"))):
            best[key] = item
    return best


def _map_params(algorithm: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    mapped: Dict[str, Any] = {}
    ignored: List[str] = []
    algo_upper = algorithm.upper()

    if algo_upper == "GA":
        if "population_size" in params:
            mapped["pop_size"] = params["population_size"]
        if "generations" in params:
            mapped["generations"] = params["generations"]
        if "mutation_rate" in params:
            mapped["mutation_rate"] = params["mutation_rate"]
        if "elite_count" in params:
            mapped["elite_size"] = params["elite_count"]
        if "crossover_rate" in params:
            ignored.append("crossover_rate")

    elif algo_upper == "PSO":
        if "swarm_size" in params:
            mapped["swarm_size"] = params["swarm_size"]
        if "max_iterations" in params:
            mapped["iterations"] = params["max_iterations"]
        if "inertia_weight" in params:
            mapped["w"] = params["inertia_weight"]
        if "cognitive_coeff" in params:
            mapped["c1"] = params["cognitive_coeff"]
            mapped["c2"] = params.get("cognitive_coeff")

    elif algo_upper in ("2-OPT", "3-OPT", "OR-OPT"):
        if "max_iterations" in params:
            mapped["max_iterations"] = params["max_iterations"]
        for key in ("first_improvement", "max_segment_size", "num_starts"):
            if key in params:
                ignored.append(key)

    else:
        mapped = params.copy()

    return mapped, ignored


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run master_numba_engine with tuned parameters from bildiri2026"
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to tuned_parameters_db.json")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--runs", type=int, default=10, help="Number of runs per algorithm")
    parser.add_argument("--workers", type=int, default=0, help="Worker count (0 = auto)")
    parser.add_argument("--problems", default="", help="Comma-separated problem names")
    parser.add_argument("--algos", default="", help="Comma-separated algorithm names")
    parser.add_argument("--size-limit", type=int, default=0, help="Problem size limit")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    entries = _load_bildiri_db(args.db)
    best_entries = _select_best_entries(entries)

    problems = mne.load_problems(size_limit=args.size_limit)
    problem_by_name = {p.name.lower(): p for p in problems}

    specs = mne._all_strategy_specs()
    spec_by_name = {s.name: s for s in specs}

    selected_problems = {p.strip().lower() for p in args.problems.split(",") if p.strip()} if args.problems else None
    selected_algos = {a.strip() for a in args.algos.split(",") if a.strip()} if args.algos else None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    progress_csv = os.path.join(args.output_dir, f"benchmark_progress_{timestamp}.csv")
    summary_csv = os.path.join(args.output_dir, f"benchmark_summary_{timestamp}.csv")
    report_json = os.path.join(args.output_dir, f"import_report_{timestamp}.json")

    workers = args.workers if args.workers > 0 else max(1, min(os.cpu_count() or 4, 4))

    tasks = []
    import_report = {
        "timestamp": timestamp,
        "db_path": args.db,
        "output_dir": args.output_dir,
        "runs": args.runs,
        "workers": workers,
        "ignored_params": [],
        "skipped": [],
    }

    for (problem_name, algo_name), entry in best_entries.items():
        if selected_problems is not None and problem_name not in selected_problems:
            continue
        if selected_algos is not None and algo_name not in selected_algos:
            continue

        problem = problem_by_name.get(problem_name)
        spec = spec_by_name.get(algo_name)
        if problem is None:
            import_report["skipped"].append({
                "problem": problem_name,
                "algorithm": algo_name,
                "reason": "problem_not_found_in_master_engine",
            })
            continue
        if spec is None:
            import_report["skipped"].append({
                "problem": problem_name,
                "algorithm": algo_name,
                "reason": "algorithm_not_supported_in_master_engine",
            })
            continue

        raw_params = entry.get("parameters", {})
        mapped, ignored = _map_params(algo_name, raw_params)
        if ignored:
            import_report["ignored_params"].append({
                "problem": problem_name,
                "algorithm": algo_name,
                "ignored": ignored,
            })

        params = spec.default_params.copy()
        params.update(mapped)
        params["algorithm_type"] = spec.algorithm_type

        tasks.append((
            mne._make_problem_dict(problem),
            spec.name,
            mne._resolve_strategy_payload(spec),
            params,
            1,
            args.runs,
        ))

    if not tasks:
        print("[INFO] No tasks to run. Check filters or DB content.")
        return 0

    with open(progress_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "problem",
            "strategy",
            "avg_length",
            "avg_gap",
            "avg_time_ms",
            "n_runs",
            "params_json",
        ])

    rows: List[Dict[str, Any]] = []

    def on_result(idx: int, result: Dict[str, Any], total: int) -> None:
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["strategy"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if result["avg_gap"] != result["avg_gap"] else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "params_json": json.dumps(result["params"], sort_keys=True),
        }
        rows.append(row)
        with open(progress_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                row["timestamp"],
                row["problem"],
                row["strategy"],
                row["avg_length"],
                row["avg_gap"],
                row["avg_time_ms"],
                row["n_runs"],
                row["params_json"],
            ])

        remain = total - (idx + 1)
        print(
            f"  [{idx + 1:>3}/{total}] {row['problem']:<12} {row['strategy']:<8} "
            f"GAP: {row['avg_gap'] if row['avg_gap'] is not None else 'nan':>6} "
            f"{row['avg_time_ms']:>7.0f}ms [LEFT: {remain}]",
            flush=True,
        )

    start = time.time()
    mne._run_pool(tasks, workers, on_result=on_result)
    elapsed = time.time() - start

    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs"])
        for row in rows:
            writer.writerow([
                row["problem"],
                row["strategy"],
                row["avg_length"],
                row["avg_gap"],
                row["avg_time_ms"],
                row["n_runs"],
            ])

    import_report["elapsed_sec"] = round(elapsed, 2)
    import_report["tasks"] = len(tasks)
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(import_report, f, indent=2)

    print(f"\n[OK] Completed in {elapsed:.1f}s")
    print(f"[OK] Progress CSV: {progress_csv}")
    print(f"[OK] Summary CSV : {summary_csv}")
    print(f"[OK] Report JSON : {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
