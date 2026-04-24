#!/usr/bin/env python3
"""TSPLIB Benchmark - 30 runs with OPTIMIZED parameters."""
import sys, os, json, csv, math, time, statistics
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer
from benchmarks.tsplib_benchmark import parse_tsplib, TSPLIB_OPTIMALS

PROBLEMS = ["eil51", "berlin52", "st70", "eil76", "eil101"]
NUM_RUNS = 30
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "..", "optimizer_api", "tests", "tsplib_data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "results")

# OPTIMIZED PARAMETERS from eil51 parameter sweep (2024-04-23)
algorithms = {
    "2-opt": lambda seed: TwoOptSolver(
        max_iterations=500, first_improvement=True,
        multi_start=True, num_starts=10, random_seed=seed),
    "3-opt": lambda seed: ThreeOptSolver(
        max_iterations=400, first_improvement=True,
        multi_start=True, num_starts=5, random_seed=seed),
    "Or-opt": lambda seed: OrOptSolver(
        max_iterations=500, first_improvement=True,
        multi_start=True, num_starts=5, random_seed=seed),
    "GA": lambda seed: GAOptimizer(
        population_size=40, generations=100, crossover_rate=0.75,
        mutation_rate=0.25, elite_count=3, random_seed=seed),
    "PSO": lambda seed: PSOOptimizer(
        swarm_size=20, max_iterations=100,
        inertia_weight=0.9, cognitive_coeff=1.49445, random_seed=seed),
}

def stdev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean)**2 for x in values) / (len(values) - 1))

results = []
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

print("="*70)
print("TSPLIB FAST BENCHMARK")
print(f"Timestamp: {timestamp}")
print(f"Runs: {NUM_RUNS}")
print(f"Problems: {PROBLEMS}")
print("="*70)

for prob_name in PROBLEMS:
    print(f"\n{'='*70}")
    print(f"Problem: {prob_name}")
    print(f"{'='*70}")

    path = os.path.join(DATA_DIR, f"{prob_name}.tsp")
    prob = parse_tsplib(path)
    n = prob["dimension"]
    optimal = TSPLIB_OPTIMALS.get(prob_name)
    coords = prob["coordinates"]

    print(f"  Nodes: {n} | Optimal: {optimal}")

    for algo_name, factory in algorithms.items():
        print(f"\n  Algorithm: {algo_name}")
        run_results = []

        for run in range(NUM_RUNS):
            seed = 1000 + run
            solver = factory(seed)
            t0 = time.perf_counter()
            r = solver.solve(coords)
            elapsed = (time.perf_counter() - t0) * 1000

            gap = ((r.tour_length - optimal) / optimal * 100) if optimal else None

            run_results.append({
                "problem": prob_name, "algorithm": algo_name, "run": run+1,
                "dimension": n, "tour_length": r.tour_length,
                "optimal": optimal, "gap_percent": gap,
                "elapsed_ms": elapsed, "iterations": r.iterations, "seed": seed,
            })

            if (run + 1) % 10 == 0:
                print(f"    {run+1}/{NUM_RUNS} done")

        lengths = [x["tour_length"] for x in run_results]
        times = [x["elapsed_ms"] for x in run_results]
        gaps = [x["gap_percent"] for x in run_results if x["gap_percent"] is not None]

        print(f"    Best: {min(lengths):.2f} | Mean: {sum(lengths)/len(lengths):.2f} (±{stdev(lengths):.2f})")
        print(f"    Time: {sum(times)/len(times):.0f} ms (±{stdev(times):.0f})")
        if gaps:
            print(f"    Avg gap: {sum(gaps)/len(gaps):.2f}% (±{stdev(gaps):.2f}%)")

        results.extend(run_results)

os.makedirs(OUTPUT_DIR, exist_ok=True)
json_path = os.path.join(OUTPUT_DIR, f"tsplib_{timestamp}.json")
with open(json_path, 'w') as f:
    json.dump({"timestamp": timestamp, "num_runs": NUM_RUNS, "results": results}, f, indent=2)

csv_path = os.path.join(OUTPUT_DIR, f"tsplib_{timestamp}.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

print(f"\n{'='*70}")
print("COMPLETE")
print(f"  JSON: {json_path}")
print(f"  CSV:  {csv_path}")
print(f"{'='*70}")
