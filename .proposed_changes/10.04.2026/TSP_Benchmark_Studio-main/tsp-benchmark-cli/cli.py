#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TSP Benchmark CLI — Command-line interface for TSP optimization benchmarking.

Supports 9 algorithms (2-opt, 3-opt, Or-opt, Swap, Hybrid, SA, GA, ACO, TS),
TSPLIB file loading, multiprocessing, CSV/JSON output, and GAP calculation.

Usage:
    python -m tsp_benchmark_cli run --problems data/ --algorithms 2-opt,sa,ga
    python -m tsp_benchmark_cli list-algorithms
    python -m tsp_benchmark_cli info --algorithm sa
"""

import argparse
import os
import sys
from multiprocessing import cpu_count

from .core.tsp_problem import load_tsplib, load_tsplib_directory, TSPProblem
from .core.algorithms import ALGORITHM_REGISTRY, get_algorithm
from .core.numba_utils import NUMBA_AVAILABLE
from .benchmark.runner import BenchmarkRunner, BenchmarkConfig
from .benchmark.reporter import BenchmarkReporter


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="tsp-benchmark",
        description=(
            "TSP Benchmark CLI — Benchmark 9 optimization algorithms "
            "on TSPLIB problem instances."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all algorithms on all problems in a directory
  python -m tsp_benchmark_cli run -p data/tsplib/ -a all

  # Run specific algorithms on a single problem
  python -m tsp_benchmark_cli run -p berlin52.tsp -a 2-opt,sa,ga -n 5

  # Run with parallel execution (4 workers)
  python -m tsp_benchmark_cli run -p data/ -a hybrid,aco,ts --parallel --workers 4

  # List available algorithms
  python -m tsp_benchmark_cli list-algorithms

  # Show algorithm details
  python -m tsp_benchmark_cli info -a sa
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── run command ──────────────────────────────────────────
    run_parser = subparsers.add_parser(
        "run",
        help="Run benchmark suite",
        description="Execute algorithms on TSP problems and collect results.",
    )

    run_parser.add_argument(
        "-p", "--problems",
        required=True,
        help="Path to .tsp file or directory containing .tsp files",
    )
    run_parser.add_argument(
        "-a", "--algorithms",
        default="all",
        help="Comma-separated algorithm names or 'all' (default: all)",
    )
    run_parser.add_argument(
        "-n", "--runs",
        type=int,
        default=3,
        help="Number of runs per (problem, algorithm) pair (default: 3)",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    run_parser.add_argument(
        "--time-limit",
        type=float,
        default=300.0,
        help="Max execution time per solve in seconds (default: 300)",
    )
    run_parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel execution with multiprocessing",
    )
    run_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Number of parallel workers (default: min({cpu_count()}, 4))",
    )
    run_parser.add_argument(
        "-o", "--output-dir",
        default="results",
        help="Output directory for results (default: results)",
    )
    run_parser.add_argument(
        "-f", "--format",
        choices=["csv", "json", "both"],
        default="both",
        help="Output format (default: both)",
    )
    run_parser.add_argument(
        "--skip-cached",
        action="store_true",
        help="Skip (problem, algorithm) pairs that have cached results",
    )
    run_parser.add_argument(
        "--no-display",
        action="store_true",
        help="Skip printing results to console (only save to files)",
    )
    run_parser.add_argument(
        "--category",
        choices=["small", "medium", "large"],
        default=None,
        help="Filter problems by size category",
    )

    # ── list-algorithms command ──────────────────────────────
    subparsers.add_parser(
        "list-algorithms",
        aliases=["list"],
        help="List all available algorithms",
    )

    # ── info command ─────────────────────────────────────────
    info_parser = subparsers.add_parser(
        "info",
        help="Show detailed information about an algorithm",
    )
    info_parser.add_argument(
        "-a", "--algorithm",
        required=True,
        help="Algorithm name to inspect",
    )

    # ── quick command (convenience shortcut) ──────────────────
    quick_parser = subparsers.add_parser(
        "quick",
        help="Quick benchmark: 3 small problems, all algorithms, 1 run",
    )
    quick_parser.add_argument(
        "-p", "--problems",
        default=None,
        help="Path to .tsp file or directory (default: built-in demo problems)",
    )

    return parser


def _parse_algorithms(algo_str: str) -> list:
    """Parse comma-separated algorithm string into list."""
    if algo_str.lower() == "all":
        return list(ALGORITHM_REGISTRY.keys())

    algorithms = []
    for part in algo_str.split(","):
        name = part.strip().lower()
        if name in ALGORITHM_REGISTRY:
            algorithms.append(name)
        else:
            print(f"❌ Unknown algorithm: '{name}'")
            print(f"   Available: {', '.join(ALGORITHM_REGISTRY.keys())}")
            sys.exit(1)
    return algorithms


def _load_problems(path: str, category: str = None) -> list:
    """Load TSP problems from file or directory."""
    if os.path.isdir(path):
        problems = load_tsplib_directory(path)
    elif os.path.isfile(path):
        problems = [load_tsplib(path)]
    else:
        print(f"❌ Path not found: {path}")
        sys.exit(1)

    if category:
        problems = [p for p in problems if p.category == category]
        if not problems:
            print(f"❌ No problems found in category '{category}'")
            sys.exit(1)

    return sorted(problems, key=lambda p: p.dimension)


def _create_demo_problems() -> list:
    """Create small demo problems for quick testing."""
    problems = []

    # Problem 1: Simple 5-city TSP
    coords = [(0, 0), (10, 0), (10, 10), (0, 10), (5, 5)]
    problems.append(TSPProblem(
        name="demo_5",
        dimension=5,
        optimal_value=0,  # Will be computed
        coordinates=coords,
    ))

    # Problem 2: 10-city TSP
    coords2 = [
        (0, 0), (1, 3), (2, 1), (4, 4), (5, 2),
        (6, 6), (7, 1), (8, 5), (9, 3), (3, 7),
    ]
    problems.append(TSPProblem(
        name="demo_10",
        dimension=10,
        optimal_value=0,
        coordinates=coords2,
    ))

    # Problem 3: 20-city TSP
    import random
    random.seed(42)
    coords3 = [(random.randint(0, 100), random.randint(0, 100)) for _ in range(20)]
    problems.append(TSPProblem(
        name="demo_20",
        dimension=20,
        optimal_value=0,
        coordinates=coords3,
    ))

    return problems


# ── Command handlers ─────────────────────────────────────────

def cmd_run(args):
    """Handle the 'run' command."""
    algorithms = _parse_algorithms(args.algorithms)
    problems = _load_problems(args.problems, args.category)

    if not problems:
        print("❌ No problems to benchmark.")
        sys.exit(1)

    workers = args.workers or min(cpu_count(), 4)

    config = BenchmarkConfig(
        algorithms=algorithms,
        problems=problems,
        n_runs=args.runs,
        seed=args.seed,
        time_limit=args.time_limit,
        num_workers=workers,
        output_dir=args.output_dir,
        output_format=args.format,
        skip_cached=args.skip_cached,
    )

    runner = BenchmarkRunner(config)
    results = runner.run(parallel=args.parallel)

    if results and not args.no_display:
        runner.print_summary(results)

    runner.save_results(results)

    return results


def cmd_list_algorithms(args):
    """Handle the 'list-algorithms' command."""
    print(f"\n{'='*60}")
    print("  AVAILABLE TSP ALGORITHMS")
    print(f"{'='*60}")
    print(f"\n  NUMBA JIT: {'✅ ENABLED' if NUMBA_AVAILABLE else '⚠️  DISABLED (pip install numba)'}")
    print()

    # Local search algorithms
    local_search = ["2-opt", "3-opt", "or-opt", "swap", "hybrid"]
    metaheuristics = ["sa", "ga", "aco", "ts"]

    print("  LOCAL SEARCH:")
    for name in local_search:
        cls = ALGORITHM_REGISTRY[name]
        algo = cls()
        print(f"    {name:<8} — {algo.display_name}")

    print("\n  METAHEURISTICS:")
    for name in metaheuristics:
        cls = ALGORITHM_REGISTRY[name]
        algo = cls()
        print(f"    {name:<8} — {algo.display_name}")

    print(f"\n  Total: {len(ALGORITHM_REGISTRY)} algorithms")
    print()


def cmd_info(args):
    """Handle the 'info' command."""
    name = args.algorithm.lower()
    if name not in ALGORITHM_REGISTRY:
        print(f"❌ Unknown algorithm: '{name}'")
        print(f"   Available: {', '.join(ALGORITHM_REGISTRY.keys())}")
        sys.exit(1)

    cls = ALGORITHM_REGISTRY[name]
    algo = cls()

    print(f"\n{'='*60}")
    print(f"  {algo.display_name} ({algo.name})")
    print(f"{'='*60}")
    print(f"\n  Type: {'Local Search' if name in ['2-opt','3-opt','or-opt','swap','hybrid'] else 'Metaheuristic'}")
    print(f"  NUMBA: {'Yes (JIT compiled)' if NUMBA_AVAILABLE else 'Pure Python fallback'}")
    print(f"\n  Parameters:")

    import inspect
    sig = inspect.signature(cls.__init__)
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        default = param.default
        if default == inspect.Parameter.empty:
            default = "(required)"
        print(f"    {param_name}: {default}")

    print()


def cmd_quick(args):
    """Handle the 'quick' command."""
    if args.problems:
        problems = _load_problems(args.problems)
    else:
        problems = _create_demo_problems()

    algorithms = list(ALGORITHM_REGISTRY.keys())

    print(f"\n⚡ QUICK BENCHMARK MODE")
    print(f"   Problems: {len(problems)} demo")
    print(f"   Algorithms: {len(algorithms)} (all)")
    print(f"   Runs: 1 per test")

    config = BenchmarkConfig(
        algorithms=algorithms,
        problems=problems,
        n_runs=1,
        seed=42,
        time_limit=60.0,
        num_workers=1,
        output_dir="results",
        output_format="both",
    )

    runner = BenchmarkRunner(config)
    results = runner.run(parallel=False)

    if results:
        runner.print_summary(results)
    runner.save_results(results)

    return results


# ── Main ────────────────────────────────────────────────────

def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command in ("run",):
        cmd_run(args)
    elif args.command in ("list-algorithms", "list"):
        cmd_list_algorithms(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "quick":
        cmd_quick(args)


if __name__ == "__main__":
    main()
