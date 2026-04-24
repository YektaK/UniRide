#!/usr/bin/env python3
"""Quick test of solvers on real time matrix data."""

import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import json
from core import ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer

# Load time matrix
with open('data/student_matrix.json') as f:
    data = json.load(f)

time_matrix = data['time_matrix']
locations = data['locations']

print("=" * 70)
print("TIME MATRIX SOLVER TEST")
print(f"  Locations: {len(locations)}")
print(f"  Depot: {locations[0]}")
print(f"  Students: {len(locations) - 1}")
print("=" * 70)

# Quick test: 1 run each, shorter iterations
solvers = [
    ("3-opt", ThreeOptSolver(max_iterations=500, multi_start=True, num_starts=5, random_seed=42)),
    ("Or-opt", OrOptSolver(max_iterations=500, multi_start=True, num_starts=5, random_seed=42)),
    ("GA", GAOptimizer(population_size=50, generations=100, random_seed=42)),
    ("PSO", PSOOptimizer(swarm_size=30, max_iterations=100, random_seed=42)),
]

results = []
for name, solver in solvers:
    print(f"\n{name}:")
    result = solver.solve_with_matrix(time_matrix)
    results.append((name, result))
    print(f"  Total duration: {result.tour_length:.1f} minutes")
    print(f"  Time: {result.elapsed_ms:.1f} ms")
    print(f"  Iterations: {result.iterations}")
    
    # Show first few stops
    tour_with_depot = [0] + result.tour + [0]
    stop_names = [locations[i] for i in tour_with_depot[:6]]
    print(f"  Route start: {' -> '.join(stop_names)} -> ...")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
sorted_results = sorted(results, key=lambda x: x[1].tour_length)
for rank, (name, result) in enumerate(sorted_results, 1):
    print(f"  {rank}. {name:8s}: {result.tour_length:8.1f} min ({result.elapsed_ms:8.1f} ms)")

print("\nTest completed successfully!")
