#!/usr/bin/env python3
"""
29-öğrenci Time Matrix Benchmark - Optimize Parametreler
Bildiri 2026
"""
import sys, os, json, csv, time, statistics
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer

# ============================================================
# Veri Yükleme
# ============================================================
with open(os.path.join(SCRIPT_DIR, 'data', 'student_matrix.json')) as f:
    data = json.load(f)

time_matrix = data['time_matrix']
n = len(time_matrix)
n_students = n - 1
locations = data['locations']
print(f"Problem: {n_students} öğrenci | Toplam düğüm: {n} | Kampüs: {locations[0]}")
print("=" * 70)

def tour_duration(tour):
    total = 0.0
    nodes = [0] + list(tour) + [0]
    for i in range(len(nodes) - 1):
        total += time_matrix[nodes[i]][nodes[i + 1]]
    return total

# ============================================================
# Optimize Edilmiş Parametreler (eil51 parametre tarama sonuçları)
# ============================================================
algorithms = {
    "2-opt": lambda seed: TwoOptSolver(
        max_iterations=500, first_improvement=True,
        multi_start=True, num_starts=10, random_seed=seed),
    "3-opt": lambda seed: ThreeOptSolver(
        max_iterations=400, first_improvement=True,
        multi_start=True, num_starts=5, random_seed=seed),
    "Or-opt": lambda seed: OrOptSolver(
        max_iterations=300, max_segment_size=3,
        multi_start=True, num_starts=3, random_seed=seed),
    "GA": lambda seed: GAOptimizer(
        population_size=40, generations=100, crossover_rate=0.75,
        mutation_rate=0.25, elite_count=3, random_seed=seed),
    "PSO": lambda seed: PSOOptimizer(
        swarm_size=20, max_iterations=100,
        inertia_weight=0.9, cognitive_coeff=1.49445, random_seed=seed),
}

# ============================================================
# 30 Bağımsız Çalıştırma
# ============================================================
NUM_RUNS = 30
all_results = []
summaries = []

for algo_name, factory in algorithms.items():
    print(f"\n{'─' * 70}")
    print(f"[{algo_name}] başlatılıyor...")
    print(f"{'─' * 70}")
    runs = []
    for run in range(NUM_RUNS):
        seed = 3000 + run
        solver = factory(seed)
        solver._set_time_matrix(time_matrix)
        result = solver.solve(solver._coordinates)
        actual = tour_duration(result.tour)
        runs.append({
            "algorithm": algo_name,
            "run": run + 1,
            "duration": actual,
            "elapsed_ms": result.elapsed_ms,
            "iterations": result.iterations,
            "tour": result.tour,
            "seed": seed,
        })
        if (run + 1) % 10 == 0:
            print(f"  [{run + 1}/{NUM_RUNS}] çalıştırıldı")

    D = [r["duration"] for r in runs]
    T = [r["elapsed_ms"] for r in runs]
    all_results.extend(runs)

    summary = {
        "algorithm": algo_name,
        "best": min(D),
        "worst": max(D),
        "mean": statistics.mean(D),
        "stdev": statistics.stdev(D) if len(D) > 1 else 0,
        "median": statistics.median(D),
        "q25": statistics.quantiles(D, n=4)[0] if len(D) > 1 else D[0],
        "q75": statistics.quantiles(D, n=4)[2] if len(D) > 1 else D[0],
        "mean_time_ms": statistics.mean(T),
    }
    summaries.append(summary)

    print(f"\n  En iyi  : {summary['best']:.1f} dk")
    print(f"  En kötü : {summary['worst']:.1f} dk")
    print(f"  Ortalama: {summary['mean']:.1f} (±{summary['stdev']:.2f}) dk")
    print(f"  Medyan  : {summary['median']:.1f} dk")
    print(f"  Süre    : {summary['mean_time_ms']:.0f} ms/run")

# ============================================================
# Kaydet
# ============================================================
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# JSON
json_path = os.path.join(OUTPUT_DIR, f"student_matrix_{timestamp}.json")
with open(json_path, 'w') as f:
    json.dump({"timestamp": timestamp, "n_students": n_students,
               "num_runs": NUM_RUNS, "results": all_results,
               "summaries": summaries}, f, indent=2)

# CSV (raw)
csv_path = os.path.join(OUTPUT_DIR, f"student_matrix_{timestamp}.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["algorithm", "run", "duration", "elapsed_ms", "iterations", "seed"])
    writer.writeheader()
    for r in all_results:
        writer.writerow({k: r[k] for k in ["algorithm", "run", "duration", "elapsed_ms", "iterations", "seed"]})

# CSV (summary)
summary_path = os.path.join(OUTPUT_DIR, f"student_matrix_summary_{timestamp}.csv")
with open(summary_path, 'w', newline='') as f:
    if summaries:
        writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
        writer.writeheader()
        for s in summaries:
            writer.writerow(s)

# ============================================================
# Karşılaştırma Tablosu
# ============================================================
print("\n" + "=" * 100)
print("SONUÇ KARŞILAŞTIRMA TABLOSU (29 öğrenci, n=30 düğüm, Kampüs = D.Kampus)")
print("=" * 100)
print(f"{'Algoritma':<12} {'En İyi':>8} {'En Kötü':>9} {'Ortalama':>10} {'St. Sapma':>10} {'Medyan':>8} {'Q25':>7} {'Q75':>7} {'Süre (ms)':>10}")
print("-" * 100)
for s in sorted(summaries, key=lambda x: x["mean"]):
    print(f"{s['algorithm']:<12} {s['best']:>8.1f} {s['worst']:>9.1f} {s['mean']:>10.1f} {s['stdev']:>10.2f} {s['median']:>8.1f} {s['q25']:>7.1f} {s['q75']:>7.1f} {s['mean_time_ms']:>10.0f}")

print(f"\n[✓] JSON: {json_path}")
print(f"[✓] CSV (ham): {csv_path}")
print(f"[✓] CSV (özet): {summary_path}")
