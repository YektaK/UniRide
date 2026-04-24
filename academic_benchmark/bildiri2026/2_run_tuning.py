#!/usr/bin/env python3
"""
Aşama 2: Dirençli Deney Tasarımı ve Parametre Optimizasyonu (Gece Koşusu)
"""
import os
import sys
import json
import csv
import random
from itertools import product
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import TwoOptSolver, ThreeOptSolver, OrOptSolver, GAOptimizer, PSOOptimizer
from benchmarks.tsplib_benchmark import parse_tsplib, TSPLIB_OPTIMALS
import config_manager
import data_manager

CONFIG_DIR = os.path.join(SCRIPT_DIR, "configs")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

FACTORIES = {
    "2-opt": lambda p, s: TwoOptSolver(
        max_iterations=p["max_iterations"],
        first_improvement=p["first_improvement"],
        multi_start=(p.get("num_starts", 1) > 1),
        num_starts=p.get("num_starts", 1),
        random_seed=s),
    "3-opt": lambda p, s: ThreeOptSolver(
        max_iterations=p["max_iterations"],
        first_improvement=p["first_improvement"],
        multi_start=(p.get("num_starts", 1) > 1),
        num_starts=p.get("num_starts", 1),
        random_seed=s),
    "Or-opt": lambda p, s: OrOptSolver(
        max_iterations=p["max_iterations"],
        max_segment_size=p["max_segment_size"],
        multi_start=(p.get("num_starts", 1) > 1),
        num_starts=p.get("num_starts", 1),
        random_seed=s),
    "GA": lambda p, s: GAOptimizer(
        population_size=p["population_size"],
        generations=p["generations"],
        crossover_rate=p["crossover_rate"],
        mutation_rate=p["mutation_rate"],
        elite_count=p["elite_count"],
        random_seed=s),
    "PSO": lambda p, s: PSOOptimizer(
        swarm_size=p["swarm_size"],
        max_iterations=p["max_iterations"],
        inertia_weight=p["inertia_weight"],
        cognitive_coeff=p["cognitive_coeff"],
        random_seed=s)
}

def generate_combinations(params_dict, max_combos, strategy):
    keys = list(params_dict.keys())
    values = [params_dict[k] for k in keys]
    combos = []
    for combo in product(*values):
        combos.append(dict(zip(keys, combo)))
        
    total = len(combos)
    if total > max_combos and strategy == "fractional_fallback":
        print(f"    [MOD] Kısmi (Fractional) Arama: {total} olası kombinasyondan rastgele {max_combos} adet seçiliyor.")
        random.seed(42)  
        combos = random.sample(combos, max_combos)
    else:
        print(f"    [MOD] Tam Grid Arama: Toplam {total} kombinasyon denenecek.")
        
    return combos

def load_problem(problem_config):
    prob_type = problem_config.get("type", "tsplib")
    path = os.path.join(SCRIPT_DIR, problem_config["path_relative"])
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Problem dosyası bulunamadı: {path}")
        
    if prob_type == "tsplib":
        name = problem_config["name"]
        prob = parse_tsplib(path)
        optimal = TSPLIB_OPTIMALS.get(name, None)
        return name, prob["dimension"], prob["coordinates"], optimal, False
        
    elif prob_type == "time_matrix":
        name = problem_config["name"]
        with open(path, "r") as f:
            data = json.load(f)
        matrix = data["time_matrix"]
        return name, len(matrix), matrix, None, True
    
    raise ValueError(f"Bilinmeyen problem tipi: {prob_type}")

def list_configs():
    if not os.path.exists(CONFIG_DIR):
        return []
    return [f for f in os.listdir(CONFIG_DIR) if f.endswith(".json")]

def main():
    print("=" * 70)
    print("Aşama 2: Dirençli Parametre Optimizasyonu")
    print("=" * 70)
    
    configs = list_configs()
    if not configs:
        print("[HATA] 'configs/' klasöründe konfigürasyon dosyası bulunamadı.")
        print("Lütfen önce 'python 1_generate_config.py' çalıştırın.")
        return
        
    print("\n--- Mevcut Konfigürasyonlar ---")
    for idx, c in enumerate(configs, 1):
        print(f"  [{idx}] {c}")
        
    sel_input = input("\nÇalıştırılacak config numaralarını girin (Örn: 1,2 veya tümü için 'all'): ").strip()
    selected_files = []
    
    if sel_input.lower() == 'all':
        selected_files = configs
    else:
        try:
            indices = [int(x.strip()) - 1 for x in sel_input.split(',')]
            for i in indices:
                selected_files.append(configs[i])
        except (ValueError, IndexError):
            print("[HATA] Geçersiz seçim.")
            return

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    running_csv_path = os.path.join(RESULTS_DIR, f"tuning_progress_{timestamp}.csv")
    
    # Create the incremental progress file header
    with open(running_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "config_file", "problem", "algorithm", "combo_idx", "mean_duration", "params"])

    print(f"\n[BİLGİ] Anlık ilerleme '{running_csv_path}' dosyasına 'append' moduyla yazılacaktır.")
    print("        Elektrik kesilirse veya işlem iptal edilirse, biten tüm veriler burada kalacaktır.\n")

    for c_file in selected_files:
        c_path = os.path.join(CONFIG_DIR, c_file)
        print(f"\n{'='*70}")
        print(f"--> KUYRUK İŞLENİYOR: {c_file}")
        print(f"{'='*70}")
        
        with open(c_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        prob_name, prob_dim, prob_data, optimal, is_time_matrix = load_problem(config["problem"])
        print(f"Hedef Problem: {prob_name} (Boyut: {prob_dim})")
        if optimal:
            print(f"Bilinen Optimum: {optimal}")
            
        tuning_sets = config["tuning_settings"]
        runs_per_combo = tuning_sets["runs_per_combination"]
        max_combos = tuning_sets["max_combinations_per_algo"]
        strategy = tuning_sets.get("strategy", "fractional_fallback")
        
        algorithms = config["algorithms"]
        
        for algo_name, param_ranges in algorithms.items():
            if algo_name not in FACTORIES:
                continue
                
            print(f"\n--- Algoritma: {algo_name} ---")
            combos = generate_combinations(param_ranges, max_combos, strategy)
            
            best_mean = float('inf')
            best_params = None
            
            for idx, params in enumerate(combos, 1):
                durations = []
                for run in range(runs_per_combo):
                    seed = 5000 + idx * 10 + run
                    solver = FACTORIES[algo_name](params, seed)
                    
                    if is_time_matrix:
                        solver._set_time_matrix(prob_data)
                        result = solver.solve(solver._coordinates)
                    else:
                        result = solver.solve(prob_data)
                        
                    durations.append(result.tour_length)
                    
                mean_len = sum(durations) / len(durations)
                
                # Resilient Save per combo
                with open(running_csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.now().strftime("%H:%M:%S"), c_file, prob_name, algo_name, idx, round(mean_len, 2), json.dumps(params)
                    ])
                
                if mean_len < best_mean:
                    best_mean = mean_len
                    best_params = params
                    
                if idx % 10 == 0 or idx == len(combos):
                    gap_str = ""
                    if optimal:
                        gap_pct = ((best_mean - optimal) / optimal) * 100
                        gap_str = f" (Gap: %{gap_pct:.2f})"
                    print(f"      [{idx}/{len(combos)}] Şu ana kadarki en iyi: {best_mean:.2f}{gap_str}")
                    
            gap_str = ""
            if optimal:
                gap_pct = ((best_mean - optimal) / optimal) * 100
                gap_str = f" (Gap: %{gap_pct:.2f})"
            print(f"    [✓] {algo_name} tamamlandı. En iyi sonuç: {best_mean:.2f}{gap_str}")
            
            # Kalıcı Veritabanı Kaydı (Her algoritma bitiminde)
            entry = {
                "algorithm": algo_name,
                "problem": prob_name,
                "dimension": prob_dim,
                "runs_per_combination": runs_per_combo,
                "best_mean_length": best_mean,
                "parameters": best_params,
                "search_space_bounds": param_ranges
            }
            entry_id = config_manager.save_to_db(entry)
            print(f"    -> Parametreler DB'ye kaydedildi (ID: {entry_id})")

    print("\n" + "=" * 70)
    print("TÜM KUYRUK BAŞARIYLA TAMAMLANDI.")
    print("Artık Aşama 3'e geçebilirsiniz:")
    print("    python 3_run_benchmark.py")

if __name__ == "__main__":
    main()
