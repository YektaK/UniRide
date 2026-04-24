#!/usr/bin/env python3
"""
29-öğrenci Time Matrix Benchmark - Optimize Parametreler
Bildiri 2026 - PARALEL ÇALIŞTIRMA VERSİYONU
"""
import sys, os, json, csv, time, statistics
from datetime import datetime
import concurrent.futures

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
# Worker Function
# ============================================================
def solve_run(algo_name, run_idx, seed):
    factory = algorithms[algo_name]
    solver = factory(seed)
    # Using time matrix directly
    solver._set_time_matrix(time_matrix)
    
    # We pass empty coordinates to base solver, it will use distance/time matrix directly
    result = solver.solve(solver._coordinates)
    
    actual = tour_duration(result.tour)
    return {
        "algorithm": algo_name,
        "run": run_idx,
        "duration": actual,
        "elapsed_ms": result.elapsed_ms,
        "iterations": result.iterations,
        "tour": result.tour,
        "seed": seed,
    }

# ============================================================
# 30 Bağımsız Çalıştırma (Çok Çekirdekli Paralel Yürütme)
# ============================================================
def main():
    NUM_RUNS = 30
    all_results = []
    summaries = []

    # Number of workers (use available CPU cores)
    max_workers = os.cpu_count() or 4
    print(f"Başlatılıyor: Toplam {max_workers} çekirdek kullanılarak paralel çalıştırma.")

    for algo_name in algorithms.keys():
        print(f"\n{'-' * 70}")
        print(f"[{algo_name}] paralel olarak başlatılıyor...")
        print(f"{'-' * 70}")
        
        runs = []
        futures = []
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            for run in range(NUM_RUNS):
                seed = 3000 + run
                futures.append(executor.submit(solve_run, algo_name, run + 1, seed))
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                runs.append(future.result())
                completed += 1
                if completed % 10 == 0:
                    print(f"  [{completed}/{NUM_RUNS}] tamamlandı")
                    
        # Sort runs by run index to maintain order
        runs.sort(key=lambda x: x["run"])
        
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
    json_path = os.path.join(OUTPUT_DIR, f"student_matrix_parallel_{timestamp}.json")
    with open(json_path, 'w') as f:
        json.dump({"timestamp": timestamp, "n_students": n_students,
                   "num_runs": NUM_RUNS, "results": all_results,
                   "summaries": summaries}, f, indent=2)

    # CSV (raw)
    csv_path = os.path.join(OUTPUT_DIR, f"student_matrix_parallel_{timestamp}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["algorithm", "run", "duration", "elapsed_ms", "iterations", "seed"])
        writer.writeheader()
        for r in all_results:
            writer.writerow({k: r[k] for k in ["algorithm", "run", "duration", "elapsed_ms", "iterations", "seed"]})

    # CSV (summary)
    summary_path = os.path.join(OUTPUT_DIR, f"student_matrix_parallel_summary_{timestamp}.csv")
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
    print("SONUÇ KARŞILAŞTIRMA TABLOSU (29 öğrenci, n=30 düğüm, Kampüs = D.Kampus) - PARALEL YÜRÜTME")
    print("=" * 100)
    print(f"{'Algoritma':<12} {'En İyi':>8} {'En Kötü':>9} {'Ortalama':>10} {'St. Sapma':>10} {'Medyan':>8} {'Q25':>7} {'Q75':>7} {'Süre (ms)':>10}")
    print("-" * 100)
    for s in sorted(summaries, key=lambda x: x["mean"]):
        print(f"{s['algorithm']:<12} {s['best']:>8.1f} {s['worst']:>9.1f} {s['mean']:>10.1f} {s['stdev']:>10.2f} {s['median']:>8.1f} {s['q25']:>7.1f} {s['q75']:>7.1f} {s['mean_time_ms']:>10.0f}")

    print(f"\n[✓] JSON: {json_path}")
    print(f"[✓] CSV (ham): {csv_path}")
    print(f"[✓] CSV (özet): {summary_path}")

if __name__ == "__main__":
    main()
