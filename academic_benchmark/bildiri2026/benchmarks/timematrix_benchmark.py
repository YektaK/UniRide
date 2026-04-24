"""
Time Matrix Benchmark for 29 Students - Bildiri 2026

This script runs GA, PSO, 3-opt, and Or-opt on time matrix data
for 29 special needs students, comparing solution quality and runtime.

Input: JSON file with time matrix (30x30: depot + 29 students)
Output: CSV and JSON results with statistical analysis
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

from core import ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer, TSPResult


class MatrixTSPSolver:
    """Wrapper to solve TSP with time matrix instead of coordinates."""
    
    def __init__(self, time_matrix: List[List[float]], solver):
        self.time_matrix = time_matrix
        self.solver = solver
        self._n = len(time_matrix)
        
        # Convert time matrix to pseudo-coordinates for solver compatibility
        self.coordinates = self._matrix_to_coordinates()
    
    def _matrix_to_coordinates(self) -> List[Tuple[float, float]]:
        """
        Convert distance/time matrix to approximate 2D coordinates
        using multidimensional scaling (MDS) approximation.
        """
        import numpy as np
        
        n = self._n
        # Convert to numpy array
        D = np.array(self.time_matrix, dtype=float)
        
        # Classical MDS
        # B = -0.5 * H * D^2 * H
        H = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * H @ (D ** 2) @ H
        
        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(B)
        
        # Take top 2 eigenvalues/vectors
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Coordinates
        coords = eigenvectors[:, :2] * np.sqrt(np.maximum(eigenvalues[:2], 0))
        
        return [(coords[i, 0], coords[i, 1]) for i in range(n)]
    
    def tour_duration(self, tour: List[int]) -> float:
        """Calculate total duration using time matrix."""
        total = 0.0
        # Tour is 0-indexed, node 0 is depot
        # Full tour: 0 -> tour[0] -> tour[1] -> ... -> 0
        nodes = [0] + tour + [0]
        for i in range(len(nodes) - 1):
            from_node = nodes[i]
            to_node = nodes[i + 1]
            total += self.time_matrix[from_node][to_node]
        return total
    
    def solve(self) -> Dict:
        """Run solver and return results with time matrix."""
        start = time.perf_counter()
        
        # Solve using pseudo-coordinates
        result = self.solver.solve(self.coordinates)
        
        # Recalculate with actual time matrix
        actual_duration = self.tour_duration(result.tour)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return {
            "algorithm": result.algorithm,
            "tour": result.tour,
            "tour_length_time": actual_duration,  # Actual minutes
            "elapsed_ms": elapsed_ms,
            "iterations": result.iterations,
            "params": result.params,
            "seed": result.seed,
        }


def create_sample_time_matrix(n_students: int = 29) -> List[List[float]]:
    """
    Create a sample symmetric time matrix for testing.
    In production, replace with real data from database.
    
    Returns (n+1) x (n+1) matrix where index 0 is school/depot.
    """
    import random
    rng = random.Random(42)
    
    n = n_students + 1  # +1 for depot
    
    # Generate random coordinates and compute times
    coords = [(0.0, 0.0)]  # Depot at origin
    for _ in range(n_students):
        coords.append((rng.uniform(-15, 15), rng.uniform(-15, 15)))
    
    # Compute Euclidean distances and scale to minutes
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dx = coords[i][0] - coords[j][0]
                dy = coords[i][1] - coords[j][1]
                dist = math.sqrt(dx * dx + dy * dy)
                # Scale: assume ~2 km per unit, 20 km/h avg speed
                # time = distance / speed * 60 minutes
                matrix[i][j] = round(dist / 20 * 60, 2)
    
    return matrix


def run_timematrix_benchmark(
    time_matrix: List[List[float]],
    num_runs: int = 30,
    output_dir: str = "../results",
    output_prefix: str = "timematrix"
) -> Dict:
    """
    Run benchmark on time matrix data.
    
    Args:
        time_matrix: (n+1) x (n+1) time matrix in minutes
        num_runs: Number of independent runs
        output_dir: Output directory
        output_prefix: Prefix for output files
    """
    
    n = len(time_matrix)
    n_students = n - 1
    
    print("=" * 70)
    print("TIME MATRIX BENCHMARK - SBRP")
    print(f"Students: {n_students}")
    print(f"Total nodes (incl. depot): {n}")
    print(f"Runs per algorithm: {num_runs}")
    print("=" * 70)
    
    algorithms = {
        "3-opt": lambda seed: ThreeOptSolver(
            max_iterations=1000,
            first_improvement=False,
            multi_start=True,
            num_starts=10,
            random_seed=seed
        ),
        "Or-opt": lambda seed: OrOptSolver(
            max_iterations=1000,
            max_segment_size=3,
            multi_start=True,
            num_starts=10,
            random_seed=seed
        ),
        "GA": lambda seed: GAOptimizer(
            population_size=100,
            generations=200,
            crossover_rate=0.85,
            mutation_rate=0.15,
            elite_count=2,
            tournament_size=3,
            max_no_improvement=50,
            random_seed=seed
        ),
        "PSO": lambda seed: PSOOptimizer(
            swarm_size=50,
            max_iterations=200,
            inertia_weight=0.729,
            cognitive_coeff=1.49445,
            social_coeff=1.49445,
            max_no_improvement=50,
            random_seed=seed
        ),
    }
    
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for algo_name, algo_factory in algorithms.items():
        print(f"\nAlgorithm: {algo_name}")
        
        run_results = []
        for run in range(num_runs):
            seed = 2000 + run
            solver = algo_factory(seed)
            
            matrix_solver = MatrixTSPSolver(time_matrix, solver)
            result = matrix_solver.solve()
            
            result["run"] = run + 1
            result["n_students"] = n_students
            run_results.append(result)
            results.append(result)
            
            if (run + 1) % 10 == 0:
                print(f"  {run + 1}/{num_runs} runs completed")
        
        # Summary
        durations = [r["tour_length_time"] for r in run_results]
        times = [r["elapsed_ms"] for r in run_results]
        
        print(f"  SUMMARY:")
        print(f"    Best duration:    {min(durations):.2f} min")
        print(f"    Mean duration:    {sum(durations)/len(durations):.2f} (±{statistics_stdev(durations):.2f})")
        print(f"    Mean time:        {sum(times)/len(times):.2f} ms (±{statistics_stdev(times):.2f})")
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    
    json_path = os.path.join(output_dir, f"{output_prefix}_{timestamp}.json")
    with open(json_path, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "num_students": n_students,
            "num_runs": num_runs,
            "results": results,
        }, f, indent=2)
    
    csv_path = os.path.join(output_dir, f"{output_prefix}_{timestamp}.csv")
    if results:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
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
    parser = argparse.ArgumentParser(description="Time Matrix Benchmark")
    parser.add_argument("--matrix-file", help="JSON file with time matrix")
    parser.add_argument("--n-students", type=int, default=29, help="Number of students")
    parser.add_argument("--runs", type=int, default=30, help="Independent runs")
    parser.add_argument("--output-dir", default="../results", help="Output directory")
    
    args = parser.parse_args()
    
    if args.matrix_file:
        with open(args.matrix_file) as f:
            data = json.load(f)
            time_matrix = data if isinstance(data, list) else data.get("time_matrix", [])
    else:
        print("No matrix file provided, generating sample data...")
        time_matrix = create_sample_time_matrix(args.n_students)
        
        # Save sample
        sample_path = os.path.join(args.output_dir, "sample_matrix.json")
        os.makedirs(args.output_dir, exist_ok=True)
        with open(sample_path, 'w') as f:
            json.dump(time_matrix, f, indent=2)
        print(f"Sample matrix saved to: {sample_path}")
    
    run_timematrix_benchmark(
        time_matrix=time_matrix,
        num_runs=args.runs,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
