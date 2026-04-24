#!/usr/bin/env python3
"""Fast TSPLIB benchmark (30 runs) - quick config for 5 problems."""

import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import os, json, csv, math, time
from datetime import datetime
from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer
from benchmarks.tsplib_benchmark import parse_tsplib, TSPLIB_OPTIMALS

PROBLEMS = ["eil51", "berlin52", "st70", "eil76", "eil101"]
NUM_RUNS = 30
DATA_DIR = "../../optimizer_api/tests/tsplib_data"
OUTPUT_DIR = "results"

def stdev(values):
    if len(values) < 2: return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean)**2 for x in values) / (len(values) - 1))

results = []
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

print("="*70)
print("TSPLIB QUICK BENCHMARK - 30 Runs")
print(f"Timestamp: {timestamp}")
print("="*70)

for prob_name in PROBLEMS:
    print(f"\n{'='*70}")
    print(f"Problem: {prob_name}")
    print(f"{'='*70}")

    path = os.path.join(DATA_DIR, f"{prob_name}.tsp")
    prob = parse_tsplib(path)
    n = prob["dimension"]; optimal = TSPLIB_OPTIMALS.get(prob_name); coords = prob["coordinates"]
    print(f"  Nodes: {n} | Optimal: {optimal}")

    # Per-problem fast algorithm config
    algs = {
        "2-opt": lambda seed: TwoOptSolver(
            max_iterations=2000, first_improvement=True,
            multi_start=True, num_starts=3, random_seed=seed),
        "3-opt": lambda seed: ThreeOptSolver(
            max_iterations=400, first_improvement=True,
            multi_start=True, num_starts=3, random_seed=seed),
        "Or-opt": lambda seed: OrOptSolver(
            max_iterations=800, first_improvement=True,
            multi_start=True, num_starts=3, random_seed=seed),
        "GA": lambda seed: GAOptimizer(
            population_size=60, generations=120, crossover_rate=0.85,
            mutation_rate=0.15, elite_count=2, tournament_size=3,
            max_no_improvement=40, random_seed=seed),
        "PSO": lambda seed: PSOOptimizer(
            swarm_size=25, max_iterations=120,
            max_no_improvement=40, random_seed=seed),
    }

    for algo_name, factory in algs.items():
        print(f"\n  Algorithm: {algo_name}")
        run_results = []
        t_prob_start = time.perf_counter()

        for run in range(NUM_RUNS):
            seed = 1000 + run
            solver = factory(seed)
            r = solver.solve(coords)
            elapsed = r.elapsed_ms

            gap = ((r.tour_length - optimal) / optimal * 100) if optimal else None
            run_results.append({
                "problem": prob_name, "algorithm": algo_name, "run": run + 1,
                "dimension": n, "tour_length": r.tour_length,
                "optimal": optimal, "gap_percent": gap,
                "elapsed_ms": elapsed, "iterations": r.iterations, "seed": seed,
            })
            if (run + 1) % 10 == 0:
                print(f"    {run+1}/{NUM_RUNS} done")

        elapsed_total = (time.perf_counter() - t_prob_start) * 1000
        lengths = [x["tour_length"] for x in run_results]
        times = [x["elapsed_ms"] for x in run_results]
        gaps = [x["gap_percent"] for x in run_results if x["gap_percent"] is not None]

        print(f"    Best: {min(lengths):.2f} | Mean: {sum(lengths)/len(lengths):.2f} (±{stdev(lengths):.2f})")
        print(f"    Time: {sum(times)/len(times):.0f} ms (±{stdev(times):.0f})")
        if gaps:
            print(f"    Gap: {sum(gaps)/len(gaps):.2f}% (±{stdev(gaps):.2f}%)")
        print(f"    Total set time: {elapsed_total/1000:.1f} s")
        results.extend(run_results)

os.makedirs(OUTPUT_DIR, exist_ok=True)
json_path = os.path.join(OUTPUT_DIR, f"tsplib_{timestamp}.json")
with open(json_path, 'w') as f:
    json.dump({"timestamp": timestamp, "num_runs": NUM_RUNS, "results": results}, f, indent=2)

csv_path = os.path.join(OUTPUT_DIR, f"tsplib_{timestamp}.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader(); writer.writerows(results)

print(f"\n{'='*70}\nCOMPLETE\n  JSON: {json_path}\n  CSV:  {csv_path}\n{'='*70}")
