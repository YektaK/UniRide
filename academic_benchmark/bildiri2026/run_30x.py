#!/usr/bin/env python3
"""Run 30 independent runs on real time matrix - fast configuration."""

import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import os
import json
import csv
import math
import time
from datetime import datetime

from core import ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer

with open('data/student_matrix.json') as f:
    data = json.load(f)

time_matrix = data['time_matrix']
n = len(time_matrix)
n_students = n - 1

def tour_duration(tour):
    total = 0.0
    nodes = [0] + list(tour) + [0]
    for i in range(len(nodes) - 1):
        total += time_matrix[nodes[i]][nodes[i+1]]
    return total

algorithms = {
    "3-opt": lambda seed: ThreeOptSolver(
        max_iterations=500, first_improvement=True,
        multi_start=True, num_starts=5, random_seed=seed),
    "Or-opt": lambda seed: OrOptSolver(
        max_iterations=500, max_segment_size=3,
        multi_start=True, num_starts=5, random_seed=seed),
    "GA": lambda seed: GAOptimizer(
        population_size=80, generations=150, crossover_rate=0.85,
        mutation_rate=0.15, elite_count=2, tournament_size=3,
        max_no_improvement=40, random_seed=seed),
    "PSO": lambda seed: PSOOptimizer(
        swarm_size=30, max_iterations=150,
        max_no_improvement=40, random_seed=seed),
}

print("=" * 70)
print("TIME MATRIX BENCHMARK - 30 RUNS")
print(f"Students: {n_students} | Nodes: {n} | Runs: 30")
print("=" * 70)

all_results = []

for algo_name, factory in algorithms.items():
    print(f"\nAlgorithm: {algo_name}")
    runs = []
    for run in range(30):
        seed = 2000 + run
        solver = factory(seed)
        # Fast inline matrix wrapping: set matrix, solve, recalc
        solver._set_time_matrix(time_matrix)
        result = solver.solve(solver._coordinates)
        actual = tour_duration(result.tour)
        runs.append({
            "algorithm": algo_name,
            "run": run + 1,
            "tour_length_time": actual,
            "elapsed_ms": result.elapsed_ms,
            "iterations": result.iterations,
            "tour": result.tour,
            "seed": seed,
        })
        if (run + 1) % 10 == 0:
            print(f"  [{run + 1}/30] done")

    durations = [r["tour_length_time"] for r in runs]
    times = [r["elapsed_ms"] for r in runs]
    all_results.extend(runs)

    mean_d = sum(durations) / len(durations)
    std_d = (sum((x - mean_d)**2 for x in durations) / (len(durations)-1))**0.5 if len(durations) > 1 else 0
    mean_t = sum(times) / len(times)
    std_t = (sum((x - mean_t)**2 for x in times) / (len(times)-1))**0.5 if len(times) > 1 else 0

    print(f"  Best : {min(durations):.1f} min")
    print(f"  Mean : {mean_d:.1f} (±{std_d:.2f}) min")
    print(f"  Time : {mean_t:.0f} (±{std_t:.0f}) ms")

# Save
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs("results", exist_ok=True)

json_path = f"results/timematrix_{timestamp}.json"
with open(json_path, 'w') as f:
    json.dump({"timestamp": timestamp, "n_students": n_students,
               "num_runs": 30, "results": all_results}, f, indent=2)

csv_path = f"results/timematrix_{timestamp}.csv"
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["algorithm", "run", "tour_length_time", "elapsed_ms", "iterations", "seed"])
    writer.writeheader()
    writer.writerows(all_results)

print(f"\n{'='*70}")
print("COMPLETE")
print(f"  JSON: {json_path}")
print(f"  CSV : {csv_path}")
print(f"{'='*70}")
