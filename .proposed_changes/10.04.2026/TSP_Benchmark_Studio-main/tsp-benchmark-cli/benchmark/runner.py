"""
TSP Benchmark Runner — orchestrates running algorithms on problems.

Supports sequential and parallel execution, multi-run averaging,
incremental caching, and graceful shutdown.
"""

import os
import signal
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..core.tsp_problem import TSPProblem, compute_distance_matrix
from ..core.algorithms import get_algorithm, ALGORITHM_REGISTRY
from ..core.algorithms.base import AlgorithmResult
from .reporter import BenchmarkReporter


# ── Graceful shutdown ───────────────────────────────────────────

_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n⚠️  DURDURMA İSTEĞİ ALINDI!")
    print("📝 Mevcut sonuçlar kaydediliyor...")


signal.signal(signal.SIGINT, _signal_handler)


# ── Configuration ───────────────────────────────────────────────

class BenchmarkConfig:
    """Holds all benchmark configuration options."""

    def __init__(
        self,
        algorithms: Optional[List[str]] = None,
        problems: Optional[List[TSPProblem]] = None,
        n_runs: int = 3,
        seed: int = 42,
        time_limit: float = 300.0,
        num_workers: int = 1,
        output_dir: str = "results",
        output_format: str = "both",  # "csv", "json", "both"
        skip_cached: bool = False,
        metadata_path: Optional[str] = None,
    ):
        self.algorithms = algorithms or list(ALGORITHM_REGISTRY.keys())
        self.problems = problems or []
        self.n_runs = n_runs
        self.seed = seed
        self.time_limit = time_limit
        self.num_workers = max(1, min(num_workers, cpu_count()))
        self.output_dir = output_dir
        self.output_format = output_format
        self.skip_cached = skip_cached
        self.metadata_path = metadata_path or os.path.join(output_dir, "metadata.json")

    @property
    def total_tests(self) -> int:
        return len(self.problems) * len(self.algorithms) * self.n_runs


# ── Worker function for multiprocessing ─────────────────────────

def _run_single_worker(args: tuple) -> Dict[str, Any]:
    """Run a single (problem, algorithm, run) test — for multiprocessing."""
    problem_dict, algo_name, algo_kwargs, run_idx, n_runs_total = args

    # Reconstruct problem
    problem = TSPProblem(
        name=problem_dict["name"],
        dimension=problem_dict["dimension"],
        optimal_value=problem_dict["optimal_value"],
        coordinates=[tuple(c) for c in problem_dict["coordinates"]],
        edge_weight_type=problem_dict.get("edge_weight_type", "EUC_2D"),
    )

    # Build distance matrix
    dist_matrix = compute_distance_matrix(problem)

    # Get algorithm instance
    algorithm = get_algorithm(algo_name, **algo_kwargs)
    seed = (run_idx + 1) * 42

    # Solve
    result = algorithm.solve(
        dist_matrix=dist_matrix,
        optimal_value=float(problem.optimal_value),
        seed=seed,
        time_limit=300.0,
    )

    return {
        "problem": problem.name,
        "dimension": problem.dimension,
        "category": problem.category,
        "optimal": problem.optimal_value,
        "algorithm": algo_name,
        "tour_length": result.tour_length,
        "gap": result.gap,
        "execution_time_ms": result.execution_time_ms,
        "iterations": result.iterations,
        "run_index": run_idx,
        "timestamp": datetime.now().isoformat(),
    }


# ── Main runner ─────────────────────────────────────────────────

class BenchmarkRunner:
    """Orchestrates TSP benchmark execution."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = BenchmarkReporter.load_metadata(config.metadata_path)
        self.start_time: float = 0

    # ── Cache management ──────────────────────────────────────

    def _get_cached(self, problem_name: str, algo_name: str) -> Optional[Dict]:
        """Check if a result is already cached."""
        saved = self.metadata.get("results", {})
        if problem_name in saved and algo_name in saved[problem_name]:
            return saved[problem_name][algo_name]
        return None

    def _save_to_cache(self, result: Dict):
        """Save a single aggregated result to metadata cache."""
        saved = self.metadata.setdefault("results", {})
        problem_name = result["problem"]
        algo_name = result["algorithm"]

        if problem_name not in saved:
            saved[problem_name] = {}

        saved[problem_name][algo_name] = {
            "avg_length": result.get("avg_length", result.get("tour_length", 0)),
            "avg_gap": result.get("avg_gap", result.get("gap", 0)),
            "best_gap": result.get("best_gap", result.get("gap", 0)),
            "avg_time_ms": result.get("avg_time_ms", result.get("execution_time_ms", 0)),
            "n_runs": result.get("n_runs", 1),
            "timestamp": datetime.now().isoformat(),
        }

        self.metadata["last_updated"] = datetime.now().isoformat()
        BenchmarkReporter.save_metadata(self.config.metadata_path, self.metadata)

    # ── Sequential execution ──────────────────────────────────

    def _run_sequential(self) -> List[Dict[str, Any]]:
        """Run all benchmarks sequentially with progress display."""
        config = self.config
        results: List[Dict[str, Any]] = []
        total_tests = len(config.problems) * len(config.algorithms)
        completed = 0

        reporter = BenchmarkReporter()
        self.start_time = time.time()

        for prob_idx, problem in enumerate(config.problems, 1):
            if _shutdown_requested:
                break

            # Build distance matrix once per problem
            dist_matrix = compute_distance_matrix(problem)
            print(f"\n[{prob_idx}/{len(config.problems)}] {problem.name} "
                  f"(n={problem.dimension}, opt={problem.optimal_value})")

            for algo_name in config.algorithms:
                if _shutdown_requested:
                    break

                completed += 1
                elapsed = time.time() - self.start_time
                pct = completed / total_tests * 100

                # Check cache
                if config.skip_cached:
                    cached = self._get_cached(problem.name, algo_name)
                    if cached:
                        results.append({
                            "problem": problem.name,
                            "dimension": problem.dimension,
                            "category": problem.category,
                            "optimal": problem.optimal_value,
                            "algorithm": algo_name,
                            "avg_length": cached["avg_length"],
                            "avg_gap": cached["avg_gap"],
                            "best_gap": cached["best_gap"],
                            "avg_time_ms": cached["avg_time_ms"],
                            "n_runs": cached["n_runs"],
                            "cached": True,
                        })
                        continue

                # Progress
                remaining = ((total_tests - completed) * (elapsed / max(completed, 1)))
                print(f"  [{algo_name:<10}] {pct:>5.1f}% ~{reporter.format_time(remaining)} kaldı", end="", flush=True)

                # Run multiple times
                run_results: List[AlgorithmResult] = []
                for run_idx in range(config.n_runs):
                    if _shutdown_requested:
                        break
                    seed = (run_idx + 1) * 42 + config.seed
                    try:
                        algo = get_algorithm(algo_name)
                        result = algo.solve(
                            dist_matrix=dist_matrix,
                            optimal_value=float(problem.optimal_value),
                            seed=seed,
                            time_limit=config.time_limit,
                        )
                        run_results.append(result)
                    except Exception as e:
                        print(f" ❌ HATA: {e}")
                        break

                if not run_results:
                    continue

                # Aggregate
                avg_length = sum(r.tour_length for r in run_results) / len(run_results)
                avg_gap = sum(r.gap for r in run_results) / len(run_results)
                avg_time = sum(r.execution_time_ms for r in run_results) / len(run_results)
                best_gap = min(r.gap for r in run_results)

                # Status indicator
                if best_gap <= 1:
                    status = "⭐"
                elif best_gap <= 3:
                    status = "✅"
                elif best_gap <= 5:
                    status = "👍"
                elif best_gap <= 10:
                    status = "⚠️"
                else:
                    status = "❌"

                print(f" {status} GAP: {avg_gap:.2f}% (best: {best_gap:.2f}%) "
                      f"({reporter.format_time(avg_time / 1000)})")

                aggregated = {
                    "problem": problem.name,
                    "dimension": problem.dimension,
                    "category": problem.category,
                    "optimal": problem.optimal_value,
                    "algorithm": algo_name,
                    "avg_length": round(avg_length, 2),
                    "avg_gap": round(avg_gap, 4),
                    "best_gap": round(best_gap, 4),
                    "avg_time_ms": round(avg_time, 2),
                    "n_runs": len(run_results),
                    "timestamp": datetime.now().isoformat(),
                }
                results.append(aggregated)
                self._save_to_cache(aggregated)

        return results

    # ── Parallel execution ────────────────────────────────────

    def _run_parallel(self) -> List[Dict[str, Any]]:
        """Run benchmarks in parallel using multiprocessing."""
        config = self.config
        tasks: List[tuple] = []

        # Build task list
        for problem in config.problems:
            problem_dict = {
                "name": problem.name,
                "dimension": problem.dimension,
                "optimal_value": problem.optimal_value,
                "coordinates": problem.coordinates,
                "edge_weight_type": problem.edge_weight_type,
            }

            for algo_name in config.algorithms:
                if config.skip_cached and self._get_cached(problem.name, algo_name):
                    continue

                for run_idx in range(config.n_runs):
                    tasks.append((problem_dict, algo_name, {}, run_idx, config.n_runs))

        if not tasks:
            return self.results

        print(f"\n🚀 Paralel çalıştırma: {len(tasks)} görev, {config.num_workers} worker")

        # Run
        raw_results: List[Dict] = []
        completed = 0
        total = len(tasks)

        try:
            with Pool(processes=config.num_workers) as pool:
                for result in pool.imap_unordered(_run_single_worker, tasks):
                    completed += 1
                    raw_results.append(result)

                    if completed % 10 == 0 or completed == total:
                        print(f"  [{completed}/{total}] tamamlandı")
        except KeyboardInterrupt:
            print("\n  ⚠️ Paralel çalıştırma kesildi")

        # Aggregate by (problem, algorithm)
        aggregated_map: Dict[str, Dict[str, List]] = {}
        for r in raw_results:
            key = f"{r['problem']}|{r['algorithm']}"
            if key not in aggregated_map:
                aggregated_map[key] = {"results": [], "info": r}
            aggregated_map[key]["results"].append(r)

        results: List[Dict] = []
        for key, data in aggregated_map.items():
            runs = data["results"]
            info = data["info"]
            avg_length = sum(r["tour_length"] for r in runs) / len(runs)
            avg_gap = sum(r["gap"] for r in runs) / len(runs)
            avg_time = sum(r["execution_time_ms"] for r in runs) / len(runs)
            best_gap = min(r["gap"] for r in runs)

            aggregated = {
                "problem": info["problem"],
                "dimension": info["dimension"],
                "category": info["category"],
                "optimal": info["optimal"],
                "algorithm": info["algorithm"],
                "avg_length": round(avg_length, 2),
                "avg_gap": round(avg_gap, 4),
                "best_gap": round(best_gap, 4),
                "avg_time_ms": round(avg_time, 2),
                "n_runs": len(runs),
                "timestamp": datetime.now().isoformat(),
            }
            results.append(aggregated)
            self._save_to_cache(aggregated)

        return results

    # ── Main run method ───────────────────────────────────────

    def run(self, parallel: bool = False) -> List[Dict[str, Any]]:
        """Execute the full benchmark suite.

        Args:
            parallel: If True, use multiprocessing for parallel execution.

        Returns:
            List of aggregated result dictionaries.
        """
        print(f"\n{'='*70}")
        print(f"  TSP BENCHMARK CLI v1.0.0")
        print(f"{'='*70}")
        print(f"  Problemler  : {len(self.config.problems)}")
        print(f"  Algoritmalar: {', '.join(self.config.algorithms)}")
        print(f"  Çalıştırma  : {self.config.n_runs} run / test")
        print(f"  Toplam test : {self.config.total_tests}")
        if parallel and self.config.num_workers > 1:
            print(f"  Worker      : {self.config.num_workers} (paralel)")
        print(f"{'='*70}")

        if parallel and self.config.num_workers > 1:
            self.results = self._run_parallel()
        else:
            self.results = self._run_sequential()

        return self.results

    # ── Output ────────────────────────────────────────────────

    def save_results(self, results: Optional[List[Dict]] = None):
        """Save results to files based on config."""
        results = results or self.results
        if not results:
            return

        config = self.config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporter = BenchmarkReporter()

        if config.output_format in ("csv", "both"):
            csv_path = os.path.join(config.output_dir, f"benchmark_{timestamp}.csv")
            reporter.save_csv(results, csv_path)
            print(f"\n💾 CSV: {csv_path}")

        if config.output_format in ("json", "both"):
            json_path = os.path.join(config.output_dir, f"benchmark_{timestamp}.json")
            reporter.save_json(results, json_path)
            print(f"💾 JSON: {json_path}")

    def print_summary(self, results: Optional[List[Dict]] = None):
        """Print formatted summary to console."""
        results = results or self.results
        if not results:
            return

        reporter = BenchmarkReporter()
        reporter.print_results_table(results)
        reporter.print_algorithm_ranking(results)

        if self.start_time:
            elapsed = time.time() - self.start_time
            print(f"\n  ⏱️  Toplam süre: {reporter.format_time(elapsed)}")
