import argparse
from typing import Tuple

def build_parser() -> argparse.ArgumentParser:
    """Build shared CLI parser for academic benchmark."""
    parser = argparse.ArgumentParser(description="UniRide Academic Benchmark CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")
    
    # Run Subcommand
    run_parser = subparsers.add_parser("run", help="Run algorithms with default or specified parameters")
    run_parser.add_argument("--algos", help="Comma-separated list of algorithms")
    run_parser.add_argument("--problems", help="Comma-separated list of problems")
    run_parser.add_argument("--select", help="Universal problem selection syntax (e.g. 1-10, small)")
    run_parser.add_argument("--runs", type=int, default=5, help="Number of repetitions")
    run_parser.add_argument("--size-limit", type=int, default=2500, help="Maximum problem size")
    run_parser.add_argument("--workers", type=int, help="Number of parallel workers")
    
    # Tune Subcommand
    tune_parser = subparsers.add_parser("tune", help="Run DoE parameter optimization")
    tune_parser.add_argument("--algos", help="Comma-separated list of algorithms")
    tune_parser.add_argument("--problems", help="Comma-separated list of problems")
    tune_parser.add_argument("--select", help="Universal problem selection syntax")
    tune_parser.add_argument("--runs", type=int, default=3, help="Runs per combination")
    tune_parser.add_argument("--max-combos", type=int, default=12, help="Max combinations to try")
    tune_parser.add_argument("--size-limit", type=int, default=500, help="Maximum problem size")
    tune_parser.add_argument("--workers", type=int, help="Number of parallel workers")
    
    # Dashboard Subcommand
    subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")
    
    return parser

def parse_args() -> Tuple[argparse.Namespace, list]:
    """Parse CLI arguments."""
    parser = build_parser()
    return parser.parse_known_args()
