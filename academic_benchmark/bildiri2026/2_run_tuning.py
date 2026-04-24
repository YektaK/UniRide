#!/usr/bin/env python3
"""
Aşama 2: Paralel Deney Tasarımı ve Parametre Optimizasyonu (Yüksek Performanslı)
Multi-processing desteği ve kaldığı yerden devam etme (Resume) yeteneği eklendi.
"""
import os
import sys
import json
import csv
import random
import glob
import concurrent.futures
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

def load_existing_progress():
    """Tüm sonuç klasörünü tarayıp biten (config, problem, algorithm, params) kombinasyonlarını döner."""
    completed = set()
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "tuning_progress_*.csv"))
    for f_path in csv_files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Key: (config_file, problem, algorithm, params_compact_json)
                    # Parametreleri normalize etmek için tekrar yükleyip dump ediyoruz
                    p_json = json.dumps(json.loads(row["params"]), sort_keys=True)
                    key = (row["config_file"], row["problem"], row["algorithm"], p_json)
                    completed.add(key)
        except Exception:
            continue
    return completed

def evaluate_combination(algo_name, params, runs_per_combo, prob_data, is_time_matrix, base_seed):
    """Worker fonksiyon: Bir parametre seti için tüm tekrarları çalıştırır."""
    durations = []
    for run in range(runs_per_combo):
        seed = base_seed + run
        solver = FACTORIES[algo_name](params, seed)
        
        if is_time_matrix:
            solver._set_time_matrix(prob_data)
            result = solver.solve(solver._coordinates)
        else:
            result = solver.solve(prob_data)
            
        durations.append(result.tour_length)
        
    mean_len = sum(durations) / len(durations)
    return mean_len

def generate_combinations(params_dict, max_combos, strategy):
    keys = list(params_dict.keys())
    values = [params_dict[k] for k in keys]
    combos = []
    for combo in product(*values):
        combos.append(dict(zip(keys, combo)))
        
    total = len(combos)
    if total > max_combos and strategy == "fractional_fallback":
        random.seed(42)  
        combos = random.sample(combos, max_combos)
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
    return sorted([f for f in os.listdir(CONFIG_DIR) if f.endswith(".json")])

def main():
    print("=" * 70)
    print("Aşama 2: Paralel & Akıllı Parametre Optimizasyonu")
    print("=" * 70)
    
    configs = list_configs()
    if not configs:
        print("[HATA] 'configs/' klasöründe konfigürasyon dosyası bulunamadı.")
        return
        
    print("\n--- Mevcut Konfigürasyonlar ---")
    
    # Environment Info Logging
    env = config_manager.get_environment_info()
    print(f"[SİSTEM] OS: {env['os']} {env['os_release']} | CPU: {env['cpu']}")
    print(f"[SİSTEM] Python: {env['python']} | Numpy: {env['numpy']} | Numba: {env['numba']}")
    print("-" * 70)
    for idx, c in enumerate(configs, 1):
        print(f"  [{idx}] {c}")
        
    sel_input = input("\nÇalıştırılacak config numaralarını girin (Örn: 1,2 veya 'all'): ").strip()
    selected_files = configs if sel_input.lower() == 'all' else []
    if not selected_files:
        try:
            indices = [int(x.strip()) - 1 for x in sel_input.split(',')]
            selected_files = [configs[i] for i in indices]
        except (ValueError, IndexError):
            print("[HATA] Geçersiz seçim."); return

    os.makedirs(RESULTS_DIR, exist_ok=True)
    existing_progress = load_existing_progress()
    if existing_progress:
        print(f"[BİLGİ] Geçmiş kayıtlar tarandı: {len(existing_progress)} adet kombinasyon zaten tamamlanmış.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    running_csv_path = os.path.join(RESULTS_DIR, f"tuning_progress_{timestamp}.csv")
    
    with open(running_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "config_file", "problem", "algorithm", "combo_idx", "mean_duration", "params"])

    max_workers = os.cpu_count() or 4
    print(f"[BİLGİ] {max_workers} çekirdek üzerinden paralel çalışma başlatılıyor.\n")

    for c_file in selected_files:
        c_path = os.path.join(CONFIG_DIR, c_file)
        with open(c_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[HATA] {c_file} JSON formatı bozuk: {e}")
                continue
        
        # Config Validation
        is_valid, msg = config_manager.validate_config(config)
        if not is_valid:
            print(f"[HATA] {c_file} doğrulaması başarısız: {msg}")
            continue
            
        prob_name, prob_dim, prob_data, optimal, is_time_matrix = load_problem(config["problem"])
        print(f"--> KUYRUĞA ALINDI: {c_file} | Problem: {prob_name}")
        
        tuning_sets = config["tuning_settings"]
        runs_per_combo = tuning_sets["runs_per_combination"]
        max_combos = tuning_sets["max_combinations_per_algo"]
        strategy = tuning_sets.get("strategy", "fractional_fallback")
        
        for algo_name, param_ranges in config["algorithms"].items():
            if algo_name not in FACTORIES: continue
                
            all_combos = generate_combinations(param_ranges, max_combos, strategy)
            
            # Filtreleme: Zaten yapılmış olanları çıkar
            to_run = []
            for idx, p in enumerate(all_combos, 1):
                p_json = json.dumps(p, sort_keys=True)
                if (c_file, prob_name, algo_name, p_json) in existing_progress:
                    continue
                to_run.append((idx, p))
            
            skipped = len(all_combos) - len(to_run)
            if skipped > 0:
                print(f"   [{algo_name}] {skipped} kombinasyon geçmiş kayıtlarda bulundu, atlanıyor.")
            
            if not to_run:
                print(f"   [{algo_name}] Tüm kombinasyonlar zaten tamamlanmış.")
                continue

            print(f"   [{algo_name}] {len(to_run)} yeni kombinasyon test ediliyor...")
            
            best_mean = float('inf')
            best_params = None
            completed_count = 0

            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                # {future: (original_idx, params)}
                future_to_combo = {}
                for idx, params in to_run:
                    seed = 5000 + idx * 10
                    f = executor.submit(evaluate_combination, algo_name, params, runs_per_combo, prob_data, is_time_matrix, seed)
                    future_to_combo[f] = (idx, params)

                for future in concurrent.futures.as_completed(future_to_combo):
                    idx, params = future_to_combo[future]
                    try:
                        mean_len = future.result()
                        completed_count += 1
                        
                        # Anlık Kaydet
                        with open(running_csv_path, "a", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                datetime.now().strftime("%H:%M:%S"), c_file, prob_name, algo_name, idx, round(mean_len, 2), json.dumps(params)
                            ])
                        
                        if mean_len < best_mean:
                            best_mean = mean_len
                            best_params = params
                        
                        if completed_count % 5 == 0 or completed_count == len(to_run):
                            gap_str = f" (Gap: %{((best_mean - optimal) / optimal * 100):.2f})" if optimal else ""
                            print(f"      - {algo_name} İlerleme: {completed_count}/{len(to_run)} | En İyi: {best_mean:.2f}{gap_str}")
                            
                    except Exception as e:
                        print(f"      [HATA] Kombinasyon {idx} başarısız: {e}")

            if best_params:
                config_manager.save_to_db({
                    "algorithm": algo_name, "problem": prob_name, "dimension": prob_dim,
                    "runs_per_combination": runs_per_combo, "best_mean_length": best_mean,
                    "parameters": best_params, "search_space_bounds": param_ranges
                })
                print(f"   [OK] {algo_name} bitti. En iyi parametreler DB'ye eklendi.")

    print("\n" + "=" * 70)
    print("TUM ISLEMLER TAMAMLANDI.")
    print(f"Detaylı rapor için: python analyze_tuning.py")

if __name__ == "__main__":
    main()
