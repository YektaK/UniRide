#!/usr/bin/env python3
"""
Aşama 3: Dirençli Toplu Benchmark (Gece Koşusu)
"""
import os
import sys
import json
import csv
import time
import statistics
from datetime import datetime
import concurrent.futures

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer
import config_manager
import data_manager

FACTORIES = {
    "2-opt": TwoOptSolver,
    "3-opt": ThreeOptSolver,
    "Or-opt": OrOptSolver,
    "GA": GAOptimizer,
    "PSO": PSOOptimizer
}

def load_target_problem(problem_info):
    path = os.path.join(SCRIPT_DIR, problem_info["path_relative"])
    if problem_info["type"] == "time_matrix":
        with open(path, "r") as f:
            data = json.load(f)
        matrix = data["time_matrix"]
        return problem_info["name"], len(matrix), matrix, True
    elif problem_info["type"] == "tsplib":
        from benchmarks.tsplib_benchmark import parse_tsplib
        prob = parse_tsplib(path)
        return problem_info["name"], prob["dimension"], prob["coordinates"], False
    return None, None, None, None

def solve_run(algo_name, params, run_idx, seed, prob_data, is_time_matrix, prob_name, model_id):
    kwargs = params.copy()
    kwargs["random_seed"] = seed
    if "num_starts" in kwargs:
        kwargs["multi_start"] = (kwargs["num_starts"] > 1)
        
    solver = FACTORIES[algo_name](**kwargs)
    
    if is_time_matrix:
        solver._set_time_matrix(prob_data)
        result = solver.solve(solver._coordinates)
    else:
        result = solver.solve(prob_data)
        
    return {
        "problem": prob_name,
        "model_id": model_id,
        "algorithm": algo_name,
        "run": run_idx,
        "duration": result.tour_length,
        "elapsed_ms": result.elapsed_ms,
        "iterations": result.iterations,
        "seed": seed,
        "history": result.history,
    }

def main():
    print("=" * 70)
    print("Aşama 3: Dirençli Toplu Benchmark (Gece Koşusu)")
    print("=" * 70)
    
    # 1. Kayıtlı Parametreleri Seç
    db = config_manager.list_entries()
    if not db:
        print("[HATA] Kayıtlı parametre seti bulunamadı. Önce 2_run_tuning.py çalıştırın.")
        return
        
    print("\n--- Kayıtlı Optimizasyon Modelleri (tuned_parameters_db.json) ---")
    for entry in db:
        algo = entry["algorithm"]
        prob = entry["problem"]
        score = entry["best_mean_length"]
        print(f"  [{entry['id']}] {algo:<8} (Eğitim: {prob:<8}) -> Skor: {score:.2f}")
        
    # Argument support for automation
    if len(sys.argv) > 1:
        ans = sys.argv[1]
    else:
        ans = input("\nÇalıştırılacak Model ID'leri (Örn: 1,3,4 veya 'all'): ").strip()
        
    selected_entries = []
    if ans.lower() == 'all':
        selected_entries = db
    else:
        try:
            ids = [int(x.strip()) for x in ans.split(',')]
            selected_entries = [e for e in db if e['id'] in ids]
        except ValueError:
            print("[HATA] Hatalı ID girişi.")
            return
            
    if not selected_entries:
        print("[HATA] Seçilen ID bulunamadı.")
        return
        
    # Environment Info Logging
    env = config_manager.get_environment_info()
    print(f"[SİSTEM] OS: {env['os']} {env['os_release']} | CPU: {env['cpu']}")
    print(f"[SİSTEM] Python: {env['python']} | Numpy: {env['numpy']} | Numba: {env['numba']}")
    print("-" * 70)

    # 2. Hedef Problemleri Seç
    problems = data_manager.list_local_problems()
    print("\n--- Hedef Problemler ---")
    for idx, p in enumerate(problems, 1):
        print(f"  [{idx}] {p['name']} ({p['type']})")
        
    # Argument support for automation
    if len(sys.argv) > 2:
        p_ans = sys.argv[2]
    else:
        p_ans = input("\nÇalıştırılacak Problem Numaraları (Örn: 1,2 veya 'all'): ").strip()
        
    selected_problems = []
    if p_ans.lower() == 'all':
        selected_problems = problems
    else:
        try:
            p_ids = [int(x.strip()) - 1 for x in p_ans.split(',')]
            selected_problems = [problems[i] for i in p_ids]
        except (ValueError, IndexError):
            print("[HATA] Hatalı problem girişi.")
            return

    # 3. Ayarlar
    # Argument support for automation
    if len(sys.argv) > 3:
        num_runs = int(sys.argv[3])
    else:
        try:
            num_runs = int(input("\nHer algoritma için tekrar sayısı [Varsayılan 30]: ").strip() or "30")
        except ValueError:
            num_runs = 30
        
    max_workers = os.cpu_count() or 4
    
    # 4. Resilience Kurulumu (Append-Only CSV)
    RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    running_csv_path = os.path.join(RESULTS_DIR, f"benchmark_progress_{timestamp}.csv")
    with open(running_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "problem", "model_id", "algorithm", "run_idx", "duration", "elapsed_ms", "seed"])
        
    print(f"\n[BİLGİ] Veriler anlık olarak '{running_csv_path}' dosyasına yazılacaktır.")
    print("        İşlemi istediğiniz zaman iptal edebilirsiniz (Ctrl+C), biten testler kaybolmaz.\n")

    all_results = []
    
    # 5. İç İçe Kuyruk (Problem -> Model)
    for prob_info in selected_problems:
        p_name, p_dim, p_data, is_time = load_target_problem(prob_info)
        print(f"\n{'='*70}")
        print(f"HEDEF PROBLEM: {p_name} (Boyut: {p_dim})")
        print(f"{'='*70}")
        
        for entry in selected_entries:
            algo_name = entry["algorithm"]
            model_id = entry["id"]
            params = entry["parameters"]
            
            print(f"\n  [ Model ID: {model_id} | Algoritma: {algo_name} ] {num_runs} tekrarlı koşu başlatılıyor...")
            
            futures = []
            runs_for_this = []
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                for run in range(num_runs):
                    # Paired seed: model identity never changes a problem/replicate stream.
                    seed = 9000 + run
                    futures.append(executor.submit(solve_run, algo_name, params, run + 1, seed, p_data, is_time, p_name, model_id))
                
                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    runs_for_this.append(res)
                    all_results.append(res)
                    completed += 1
                    
                    # Resilience Save
                    with open(running_csv_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            datetime.now().strftime("%H:%M:%S"),
                            res["problem"], res["model_id"], res["algorithm"], res["run"],
                            round(res["duration"], 2), int(res["elapsed_ms"]), res["seed"]
                        ])
                        
                    if completed % 10 == 0 or completed == num_runs:
                        print(f"    -> {completed}/{num_runs} tamamlandı.")

    # 6. Tüm Koşular Bittiğinde Özet Tablo Çıkarma
    print("\n" + "=" * 90)
    print("TÜM KUYRUK TAMAMLANDI - ÖZET SONUÇLAR")
    print("=" * 90)
    print(f"{'Problem':<15} {'Algoritma':<12} {'Model':<6} {'En İyi':>8} {'En Kötü':>9} {'Ortalama':>10} {'Süre(ms)':>10}")
    print("-" * 90)
    
    summary_path = os.path.join(RESULTS_DIR, f"benchmark_summary_{timestamp}.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Problem", "Algorithm", "ModelID", "Best", "Worst", "Mean", "StdDev", "MeanTimeMS"])
        
        # Group by (Problem, ModelID)
        groups = {}
        for r in all_results:
            key = (r["problem"], r["model_id"], r["algorithm"])
            if key not in groups:
                groups[key] = []
            groups[key].append(r)
            
        for (p_name, m_id, a_name), results in groups.items():
            D = [r["duration"] for r in results]
            T = [r["elapsed_ms"] for r in results]
            best, worst, mean, stdev, mean_ms = min(D), max(D), statistics.mean(D), (statistics.stdev(D) if len(D) > 1 else 0), statistics.mean(T)
            
            print(f"{p_name:<15} {a_name:<12} {m_id:<6} {best:>8.1f} {worst:>9.1f} {mean:>10.1f} {mean_ms:>10.0f}")
            writer.writerow([p_name, a_name, m_id, best, worst, mean, stdev, mean_ms])

    # 7. Yakınsama Eğrileri İçin En İyi Geçmişleri Kaydet (JSON)
    histories_dir = os.path.join(RESULTS_DIR, "histories")
    os.makedirs(histories_dir, exist_ok=True)
    
    best_histories = {}
    for (p_name, m_id, a_name), results in groups.items():
        # En iyi koşuyu bul
        best_run = min(results, key=lambda r: r["duration"])
        if best_run.get("history"):
            key = f"{p_name}_{a_name}_model{m_id}"
            best_histories[key] = {
                "problem": p_name,
                "algorithm": a_name,
                "model_id": m_id,
                "best_duration": best_run["duration"],
                "history": best_run["history"]
            }
    
    if best_histories:
        h_path = os.path.join(histories_dir, f"convergence_{timestamp}.json")
        with open(h_path, "w", encoding="utf-8") as f:
            json.dump(best_histories, f, indent=2)
        print(f"[OK] Yakinsama verileri: {h_path}")

    print(f"\n[OK] Ham veriler: {running_csv_path}")
    print(f"[OK] Ozet tablo: {summary_path}")

if __name__ == "__main__":
    main()
