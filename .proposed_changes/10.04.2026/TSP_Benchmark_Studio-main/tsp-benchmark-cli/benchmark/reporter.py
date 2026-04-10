"""
TSP Benchmark Reporter — CSV, JSON, and console output.

Handles formatting and writing benchmark results to files and terminal.
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional


class BenchmarkReporter:
    """Formats and writes benchmark results."""

    # ── Console helpers ──────────────────────────────────────────

    @staticmethod
    def print_header(title: str = "TSP BENCHMARK RESULTS", width: int = 80):
        """Print a formatted section header."""
        print()
        print("=" * width)
        print(f"  {title}")
        print("=" * width)

    @staticmethod
    def print_separator(width: int = 80):
        print("-" * width)

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds into a human-readable string (Turkish)."""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}dk {secs}sn"
        hours = int(minutes // 60)
        minutes = int(minutes % 60)
        return f"{hours}sa {minutes}dk"

    # ── Result table ─────────────────────────────────────────────

    @staticmethod
    def print_results_table(results: List[Dict[str, Any]], show_convergence: bool = False):
        """Print a formatted results table to stdout."""
        if not results:
            print("\n  No results to display.")
            return

        reporter = BenchmarkReporter()
        reporter.print_header()

        # Column headers
        header = (
            f"{'Problem':<14} {'n':>4} │ {'Algorithm':<10} │ "
            f"{'Length':>10} │ {'Gap%':>8} │ {'Time':>10}"
        )
        print(header)
        reporter.print_separator()

        # Sort by problem dimension then algorithm
        sorted_results = sorted(results, key=lambda r: (r.get("dimension", 0), r.get("algorithm", "")))

        for r in sorted_results:
            gap = r.get("avg_gap", -1)
            gap_str = f"{gap:>7.2f}%" if gap >= 0 else "   N/A  "
            length = r.get("avg_length", r.get("tour_length", 0))
            time_ms = r.get("avg_time_ms", 0)
            time_str = reporter.format_time(time_ms / 1000)

            print(
                f"{r['problem']:<14} {r['dimension']:>4} │ "
                f"{r['algorithm']:<10} │ {length:>10.2f} │ "
                f"{gap_str} │ {time_str:>10}"
            )

        reporter.print_separator()

        # Summary statistics
        problems_tested = len(set(r["problem"] for r in results))
        algos_used = len(set(r["algorithm"] for r in results))
        print(f"  Problems: {problems_tested}  |  Algorithms: {algos_used}  |  Total tests: {len(results)}")

    # ── Algorithm ranking ────────────────────────────────────────

    @staticmethod
    def print_algorithm_ranking(results: List[Dict[str, Any]]):
        """Print per-algorithm aggregated statistics."""
        if not results:
            return

        reporter = BenchmarkReporter()
        reporter.print_header("ALGORITHM RANKING (sorted by average GAP)")

        # Aggregate
        algo_stats: Dict[str, Dict] = {}
        for r in results:
            alg = r["algorithm"]
            if alg not in algo_stats:
                algo_stats[alg] = {"gaps": [], "times": [], "best_gaps": []}

            gap = r.get("avg_gap", r.get("gap", 0))
            time_ms = r.get("avg_time_ms", r.get("execution_time_ms", 0))

            algo_stats[alg]["gaps"].append(gap)
            algo_stats[alg]["times"].append(time_ms)
            if "best_gap" in r:
                algo_stats[alg]["best_gaps"].append(r["best_gap"])

        # Sort by average gap
        sorted_algos = sorted(
            algo_stats.items(),
            key=lambda x: sum(x[1]["gaps"]) / len(x[1]["gaps"]) if x[1]["gaps"] else float("inf")
        )

        header = f"{'Algorithm':<14} │ {'Avg GAP%':>10} │ {'Best GAP%':>10} │ {'Avg Time':>12} │ {'Tests':>6}"
        print(header)
        reporter.print_separator()

        for alg, stats in sorted_algos:
            gaps = [g for g in stats["gaps"] if g >= 0]
            avg_gap = sum(gaps) / len(gaps) if gaps else -1
            best_gap = min(stats["best_gaps"]) if stats["best_gaps"] else -1
            avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0

            avg_str = f"{avg_gap:>9.2f}%" if avg_gap >= 0 else "      N/A "
            best_str = f"{best_gap:>9.2f}%" if best_gap >= 0 else "      N/A "
            time_str = reporter.format_time(avg_time / 1000)

            print(f"{alg:<14} │ {avg_str} │ {best_str} │ {time_str:>12} │ {len(stats['gaps']):>6}")

        reporter.print_separator()

    # ── CSV export ───────────────────────────────────────────────

    @staticmethod
    def save_csv(results: List[Dict[str, Any]], filepath: str):
        """Write results to a CSV file."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        fieldnames = [
            "problem", "dimension", "category", "optimal",
            "algorithm", "tour_length", "avg_length",
            "gap", "avg_gap", "best_gap",
            "execution_time_ms", "avg_time_ms",
            "n_runs", "numba_available", "timestamp"
        ]

        # Filter to only existing keys and add timestamp
        rows = []
        for r in results:
            row = {k: r.get(k, "") for k in fieldnames}
            row["timestamp"] = datetime.now().isoformat()
            rows.append(row)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        return filepath

    # ── JSON export ──────────────────────────────────────────────

    @staticmethod
    def save_json(results: List[Dict[str, Any]], filepath: str, pretty: bool = True):
        """Write results to a JSON file."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        output = {
            "benchmark_tool": "tsp-benchmark-cli",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": results,
        }

        indent = 2 if pretty else None
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=indent, ensure_ascii=False, default=str)

        return filepath

    # ── Metadata (for incremental benchmarking) ──────────────────

    @staticmethod
    def save_metadata(filepath: str, data: Dict[str, Any]):
        """Save benchmark metadata JSON (cached results)."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def load_metadata(filepath: str) -> Dict[str, Any]:
        """Load benchmark metadata JSON."""
        if not os.path.exists(filepath):
            return {"results": {}, "last_updated": ""}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"results": {}, "last_updated": ""}
