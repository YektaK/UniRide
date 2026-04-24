#!/usr/bin/env python3
"""
Parameter Optimization Experiment Design - Bildiri 2026

Akademik parametre optimizasyonu deney tasarımı.
Problem: eil51 (n=51, optimum=426)
Her parametre seti: 10 bagimsiz calistirma
Cikti: parametre hassasiyet analizi + Taguchi L8 + ANOVA
"""

import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import json, csv, math, time
from datetime import datetime
from itertools import product
from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer
from benchmarks.tsplib_benchmark import parse_tsplib, TSPLIB_OPTIMALS

# DATA_DIR relative to SCRIPT_DIR so script works from any CWD
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "..", "optimizer_api", "tests", "tsplib_data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Problem
PROBLEM = "eil51"
OPTIMAL = TSPLIB_OPTIMALS[PROBLEM]
path = os.path.join(DATA_DIR, f"{PROBLEM}.tsp")
prob = parse_tsplib(path)
coords = prob["coordinates"]
print(f"Problem: {PROBLEM} | Nodes: {prob['dimension']} | Optimal: {OPTIMAL}")
print("="*70)

# ============================================================
# 1. PARAMETRE KOMBINASYONLARI
# ============================================================

# 2-opt parametreleri
PARAMS_2OPT = {
    "max_iterations": [500, 1000, 2000],
    "first_improvement": [True, False],
    "num_starts": [1, 3, 5, 10],
}

# 3-opt parametreleri
PARAMS_3OPT = {
    "max_iterations": [200, 400, 800],
    "first_improvement": [True, False],
    "num_starts": [1, 3, 5],
}

# Or-opt parametreleri
PARAMS_OROPT = {
    "max_iterations": [300, 600, 1000],
    "max_segment_size": [1, 2, 3],
    "num_starts": [1, 3, 5],
}

# GA parametreleri
PARAMS_GA = {
    "population_size": [40, 80, 120],
    "generations": [100, 200],
    "crossover_rate": [0.75, 0.85, 0.95],
    "mutation_rate": [0.05, 0.15, 0.25],
    "elite_count": [1, 2, 3],
}

# PSO parametreleri
PARAMS_PSO = {
    "swarm_size": [20, 40, 60],
    "max_iterations": [100, 200, 300],
    "inertia_weight": [0.6, 0.729, 0.9],
    "cognitive_coeff": [1.0, 1.49445, 2.0],
}

# Toplam kombinasyon sinirlari (her algoritma icin max 27)
LIMITS = {"2-opt": 24, "3-opt": 18, "Or-opt": 18, "GA": 27, "PSO": 18}

def generate_combinations(params, limit):
    """Generate all combinations up to limit."""
    keys = list(params.keys())
    values = [params[k] for k in keys]
    combos = []
    for combo in product(*values):
        combos.append(dict(zip(keys, combo)))
    return combos[:limit]

# ============================================================
# 2. DENEV TASARIMI - ILK ETAP (Sistematik Tarama)
# ============================================================

results = []

experiments = [
    ("2-opt", PARAMS_2OPT, lambda p, s: TwoOptSolver(
        max_iterations=p["max_iterations"],
        first_improvement=p["first_improvement"],
        multi_start=(p["num_starts"] > 1),
        num_starts=p["num_starts"],
        random_seed=s)),
    ("3-opt", PARAMS_3OPT, lambda p, s: ThreeOptSolver(
        max_iterations=p["max_iterations"],
        first_improvement=p["first_improvement"],
        multi_start=(p["num_starts"] > 1),
        num_starts=p["num_starts"],
        random_seed=s)),
    ("Or-opt", PARAMS_OROPT, lambda p, s: OrOptSolver(
        max_iterations=p["max_iterations"],
        max_segment_size=p["max_segment_size"],
        multi_start=(p["num_starts"] > 1),
        num_starts=p["num_starts"],
        random_seed=s)),
]

for algo_name, param_dict, factory in experiments:
    combos = generate_combinations(param_dict, LIMITS[algo_name])
    print(f"\n{'='*70}")
    print(f"Algorithm: {algo_name} | Combinations: {len(combos)} | Runs each: 10")
    print(f"{'='*70}")

    best_mean = float('inf')
    best_params = None

    for idx, params in enumerate(combos, 1):
        runs = []
        durations = []
        for run in range(10):
            seed = 3000 + idx * 10 + run
            solver = factory(params, seed)
            start = time.perf_counter()
            result = solver.solve(coords)
            elapsed = (time.perf_counter() - start) * 1000
            gap = ((result.tour_length - OPTIMAL) / OPTIMAL) * 100
            runs.append({
                "algorithm": algo_name,
                "combo_id": idx,
                "params": json.dumps(params),
                "run": run + 1,
                "tour_length": result.tour_length,
                "gap_percent": gap,
                "elapsed_ms": elapsed,
                "iterations": result.iterations,
                "seed": seed,
            })
            durations.append(result.tour_length)

        mean_len = sum(durations) / len(durations)
        std_len = (sum((x - mean_len)**2 for x in durations) / (len(durations)-1))**0.5 if len(durations) > 1 else 0

        if mean_len < best_mean:
            best_mean = mean_len
            best_params = params

        results.extend(runs)

        if idx % 5 == 0 or idx == len(combos):
            print(f"  [{idx}/{len(combos)}] Best mean so far: {best_mean:.2f}")

    print(f"\n  BEST PARAMS for {algo_name}:")
    for k, v in best_params.items():
        print(f"    {k}: {v}")
    print(f"    Mean tour length: {best_mean:.2f} (gap: {((best_mean-OPTIMAL)/OPTIMAL*100):.2f}%)")

# ============================================================
# 3. METASEZGISELLER (GA ve PSO)
# ============================================================

meta_experiments = [
    ("GA", PARAMS_GA, lambda p, s: GAOptimizer(
        population_size=p["population_size"],
        generations=p["generations"],
        crossover_rate=p["crossover_rate"],
        mutation_rate=p["mutation_rate"],
        elite_count=p["elite_count"],
        random_seed=s)),
    ("PSO", PARAMS_PSO, lambda p, s: PSOOptimizer(
        swarm_size=p["swarm_size"],
        max_iterations=p["max_iterations"],
        inertia_weight=p["inertia_weight"],
        random_seed=s)),
]

for algo_name, param_dict, factory in meta_experiments:
    combos = generate_combinations(param_dict, LIMITS[algo_name])
    print(f"\n{'='*70}")
    print(f"Algorithm: {algo_name} | Combinations: {len(combos)} | Runs each: 10")
    print(f"{'='*70}")

    best_mean = float('inf')
    best_params = None

    for idx, params in enumerate(combos, 1):
        runs = []
        durations = []
        for run in range(10):
            seed = 4000 + idx * 10 + run
            solver = factory(params, seed)
            start = time.perf_counter()
            result = solver.solve(coords)
            elapsed = (time.perf_counter() - start) * 1000
            gap = ((result.tour_length - OPTIMAL) / OPTIMAL) * 100
            runs.append({
                "algorithm": algo_name,
                "combo_id": idx,
                "params": json.dumps(params),
                "run": run + 1,
                "tour_length": result.tour_length,
                "gap_percent": gap,
                "elapsed_ms": elapsed,
                "iterations": result.iterations,
                "seed": seed,
            })
            durations.append(result.tour_length)

        mean_len = sum(durations) / len(durations)
        if mean_len < best_mean:
            best_mean = mean_len
            best_params = params
        results.extend(runs)

        if idx % 5 == 0 or idx == len(combos):
            print(f"  [{idx}/{len(combos)}] Best mean so far: {best_mean:.2f}")

    print(f"\n  BEST PARAMS for {algo_name}:")
    for k, v in best_params.items():
        print(f"    {k}: {v}")
    print(f"    Mean tour length: {best_mean:.2f}")

# ============================================================
# 4. KAYDET
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
json_path = os.path.join(OUTPUT_DIR, f"param_opt_{timestamp}.json")
with open(json_path, 'w') as f:
    json.dump({"problem": PROBLEM, "optimal": OPTIMAL, "num_runs_per_combo": 10,
               "results": results, "timestamp": timestamp}, f, indent=2)

csv_path = os.path.join(OUTPUT_DIR, f"param_opt_{timestamp}.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\n{'='*70}")
print("COMPLETE")
print(f"  Total combos tested: {len(set((r['algorithm'], r['combo_id']) for r in results))}")
print(f"  Total runs: {len(results)}")
print(f"  JSON: {json_path}")
print(f"  CSV:  {csv_path}")
print(f"{'='*70}")
