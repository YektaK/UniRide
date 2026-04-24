"""Quick test for all solvers."""
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer

# Simple 5-node TSP (0=depot)
coords = [
    (0.0, 0.0),   # 0: depot
    (1.0, 0.0),   # 1
    (1.0, 1.0),   # 2
    (0.0, 1.0),   # 3
    (0.5, 0.5),   # 4
]

print("=" * 60)
print("Solver Quick Test - Simple 5-node TSP")
print("=" * 60)

optimal = 4.0 + 4**0.5  # approximate

solvers = [
    TwoOptSolver(random_seed=42),
    ThreeOptSolver(random_seed=42),
    OrOptSolver(random_seed=42),
    GAOptimizer(population_size=20, generations=50, random_seed=42),
    PSOOptimizer(swarm_size=20, max_iterations=50, random_seed=42),
]

for solver in solvers:
    print(f"\n{solver.name}:")
    result = solver.solve(coords)
    print(f"  Tour length: {result.tour_length:.2f}")
    print(f"  Time: {result.elapsed_ms:.2f} ms")
    print(f"  Iterations: {result.iterations}")
    print(f"  Tour: {result.tour}")

print("\n\nAll solvers completed successfully!")
