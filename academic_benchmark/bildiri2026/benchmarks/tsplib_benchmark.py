"""
TSPLIB Benchmark Runner for Bildiri 2026

Runs GA, PSO, 2-opt, 3-opt, Or-opt on TSPLIB problems with 30 independent runs each.
Outputs CSV and JSON results for statistical analysis.

Usage:
    python tsplib_benchmark.py --output results/benchmark_$(date +%Y%m%d_%H%M%S)
"""

import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) in ('benchmarks', 'core'):
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
else:
    sys.path.insert(0, SCRIPT_DIR)

import os
import json
import csv
import time
import argparse
import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Import solvers
from core import (
    TwoOptSolver, ThreeOptSolver, OrOptSolver,
    GAOptimizer, PSOOptimizer, TSPResult
)


# TSPLIB Optimal Solutions
TSPLIB_OPTIMALS = {
    # Small problems (n <= 100)
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroA100": 21282, "eil101": 629, "pr107": 44303,
    # Medium problems (101-299)
    "kroA150": 26524, "kroB150": 26130, "kroA200": 29368,
    "a280": 2579, "lin318": 42029,
    # Large problems (slower, optional)
    # "pcb1173": 56892, "u1060": 224094,
}

TSPLIB_DOWNLOAD_URL = "http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/"


def download_tsplib(name: str, data_dir: str) -> str:
    """Download TSPLIB problem if not exists."""
    filepath = os.path.join(data_dir, f"{name}.tsp")
    if os.path.exists(filepath):
        return filepath
    
    url = f"{TSPLIB_DOWNLOAD_URL}/{name}.tsp.gz"
    import urllib.request
    import gzip
    
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"  Downloading {name}.tsp...")
    gz_path = filepath + ".gz"
    urllib.request.urlretrieve(url, gz_path)
    
    with gzip.open(gz_path, 'rt') as f_in:
        with open(filepath, 'w') as f_out:
            f_out.write(f_in.read())
    
    os.remove(gz_path)
    return filepath


def parse_tsplib(filepath: str) -> Optional[Dict]:
    """Parse a TSPLIB .tsp file."""
    import re
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    name_match = re.search(r'NAME\s*:\s*(\S+)', content, re.I)
    dim_match = re.search(r'DIMENSION\s*:\s*(\d+)', content, re.I)
    ewt_match = re.search(r'EDGE_WEIGHT_TYPE\s*:\s*(\S+)', content, re.I)
    
    if not dim_match:
        return None
    
    name = name_match.group(1).lower() if name_match else os.path.basename(filepath).replace('.tsp', '')
    dimension = int(dim_match.group(1))
    edge_weight_type = ewt_match.group(1) if ewt_match else "EUC_2D"
    
    # Parse coordinates
    coords = []
    coord_section = re.search(
        r'NODE_COORD_SECTION\s*\n(.*?)\n?(?:EOF|DISPLAY_DATA_SECTION)',
        content, re.DOTALL | re.I
    )
    
    if coord_section:
        lines = coord_section.group(1).strip().split('\n')
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                coords.append((float(parts[1]), float(parts[2])))
    
    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": edge_weight_type,
        "coordinates": coords,
    }


def load_problem(name: str, data_dir: str) -> Optional[Dict]:
    """Load or download a TSPLIB problem."""
    filepath = download_tsplib(name, data_dir)
    return parse_tsplib(filepath)


def run_benchmark_suite(
    problem_names: List[str],
    num_runs: int = 30,
    data_dir: str = "data",
    output_dir: str = "results",
    problem_size_limit: int = 300
) -> Dict:
    """
    Run benchmark suite with multiple algorithms on multiple problems.
    
    Args:
        problem_names: List of TSPLIB problem names
        num_runs: Number of independent runs per algorithm per problem
        data_dir: Directory for TSPLIB data files
        output_dir: Directory for results
        problem_size_limit: Skip problems larger than this (runtime)
    """
    
    # Algorithm configurations
    algorithms = {
        "2-opt": lambda seed: TwoOptSolver(
            max_iterations=5000,
            first_improvement=False,
            multi_start=True,
            num_starts=20,
            random_seed=seed
        ),
        "3-opt": lambda seed: ThreeOptSolver(
            max_iterations=1000,
            first_improvement=False,
            multi_start=False,
            random_seed=seed
        ),
        "Or-opt": lambda seed: OrOptSolver(
            max_iterations=1000,
            max_segment_size=3,
            multi_start=False,
            random_seed=seed
        ),
        "GA": lambda seed: GAOptimizer(
            population_size=100,
            generations=300,
            crossover_rate=0.85,
            mutation_rate=0.15,
            elite_count=2,
            tournament_size=3,
            max_no_improvement=80,
            random_seed=seed
        ),
        "PSO": lambda seed: PSOOptimizer(
            swarm_size=50,
            max_iterations=300,
            inertia_weight=0.729,
            cognitive_coeff=1.49445,
            social_coeff=1.49445,
            max_no_improvement=80,
            random_seed=seed
        ),
    }
    
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 70)
    print("TSPLIB BENCHMARK SUITE")
    print(f"Timestamp: {timestamp}")
    print(f"Runs per algorithm: {num_runs}")
    print(f"Problems: {problem_names}")
    print("=" * 70)
    
    for prob_name in problem_names:
        print(f"\n{'='*70}")
        print(f"Problem: {prob_name}")
        print(f"{'='*70}")
        
        # Load problem
        problem_data = load_problem(prob_name, data_dir)
        if not problem_data:
            print(f"  ERROR: Could not load {prob_name}")
            continue
        
        n = problem_data["dimension"]
        optimal = TSPLIB_OPTIMALS.get(prob_name)
        
        print(f"  Nodes: {n}")
        print(f"  Optimal: {optimal if optimal else 'Unknown'}")
        
        # Skip large problems
        if n > problem_size_limit:
            print(f"  SKIPPED: Problem too large ({n} > {problem_size_limit})")
            continue
        
        coords = problem_data["coordinates"]
        
        for algo_name, algo_factory in algorithms.items():
            print(f"\n  Algorithm: {algo_name}")
            run_results = []
            
            for run in range(num_runs):
                seed = 1000 + run  # Different seed for each run
                solver = algo_factory(seed)
                
                result = solver.solve(coords)
                
                gap = None
                if optimal:
                    gap = ((result.tour_length - optimal) / optimal) * 100
                
                result_dict = {
                    "problem": prob_name,
                    "algorithm": algo_name,
                    "run": run + 1,
                    "dimension": n,
                    "tour_length": result.tour_length,
                    "optimal": optimal,
                    "gap_percent": gap,
                    "elapsed_ms": result.elapsed_ms,
                    "iterations": result.iterations,
                    "seed": seed,
                }
                run_results.append(result_dict)
                results.append(result_dict)
                
                # Progress indicator
                if (run + 1) % 10 == 0:
                    print(f"    {run + 1}/{num_runs} runs completed")
            
            # Print summary for this algorithm
            lengths = [r["tour_length"] for r in run_results]
            times = [r["elapsed_ms"] for r in run_results]
            gaps = [r["gap_percent"] for r in run_results if r["gap_percent"] is not None]
            
            print(f"    SUMMARY:")
            print(f"      Best length:     {min(lengths):.2f}")
            print(f"      Mean length:     {sum(lengths)/len(lengths):.2f} (±{statistics_stdev(lengths):.2f})")
            print(f"      Mean time:       {sum(times)/len(times):.2f} ms (±{statistics_stdev(times):.2f})")
            if gaps:
                print(f"      Mean gap:        {sum(gaps)/len(gaps):.2f}% (±{statistics_stdev(gaps):.2f}%)")
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    
    # JSON
    json_path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
    with open(json_path, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "num_runs": num_runs,
            "results": results,
        }, f, indent=2)
    
    # CSV
    csv_path = os.path.join(output_dir, f"benchmark_{timestamp}.csv")
    if results:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print(f"\n{'='*70}")
    print("BENCHMARK COMPLETE")
    print(f"  Results saved to: {output_dir}")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print(f"{'='*70}")
    
    return {
        "timestamp": timestamp,
        "results": results,
        "json_path": json_path,
        "csv_path": csv_path,
    }


def statistics_stdev(values: List[float]) -> float:
    """Calculate sample standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def main():
    parser = argparse.ArgumentParser(description="TSPLIB Benchmark Runner")
    parser.add_argument(
        "--problems",
        nargs="+",
        default=["eil51", "berlin52", "st70", "eil76", "eil101"],
        help="TSPLIB problem names to benchmark"
    )
    parser.add_argument("--runs", type=int, default=30, help="Independent runs per algorithm")
    parser.add_argument("--data-dir", default="../data", help="TSPLIB data directory")
    parser.add_argument("--output", default="../results", help="Output directory")
    parser.add_argument("--size-limit", type=int, default=300, help="Max problem size")
    
    args = parser.parse_args()
    
    run_benchmark_suite(
        problem_names=args.problems,
        num_runs=args.runs,
        data_dir=args.data_dir,
        output_dir=args.output,
        problem_size_limit=args.size_limit,
    )


if __name__ == "__main__":
    main()
