#!/usr/bin/env python3
"""
Aşama 2: Paralel Deney Tasarımı ve Parametre Optimizasyonu — YAEM 2026
"""
import os
import sys
import json
import csv
import random
import optuna
import glob
import concurrent.futures
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import (TwoOptSolver, ThreeOptSolver, OrOptSolver,
                  GAOptimizer, PSOOptimizer,
                  GWOOptimizer, PureGWOOptimizer, GWO_LKH_Optimizer, GWO_ALNS_Optimizer,
                  HHOOptimizer, PureHHOOptimizer, HHO_LKH_Optimizer, HHO_ALNS_Optimizer)
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
        random_seed=s),
    "GWO-2opt": lambda p, s: GWOOptimizer(
        pack_size=p["pack_size"],
        max_iterations=p["max_iterations"],
        initial_a=p["initial_a"],
        exploration_rate=p["exploration_rate"],
        max_no_improvement=p.get("max_no_improvement", 75),
        polish_interval=p.get("polish_interval", 25),
        polish_iters=p.get("polish_iters", 10),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
    "GWO-Pure": lambda p, s: PureGWOOptimizer(
        pack_size=p["pack_size"],
        max_iterations=p["max_iterations"],
        initial_a=p["initial_a"],
        exploration_rate=p["exploration_rate"],
        max_no_improvement=p.get("max_no_improvement", 75),
        random_seed=s),
    "HHO-2opt": lambda p, s: HHOOptimizer(
        hawks=p["hawks"],
        max_iterations=p["max_iterations"],
        initial_energy=p["initial_energy"],
        jump_probability=p["jump_probability"],
        max_no_improvement=p.get("max_no_improvement", 75),
        dive_count=p.get("dive_count", 3),
        levy_scale=p.get("levy_scale", 0.3),
        polish_interval=p.get("polish_interval", 25),
        polish_iters=p.get("polish_iters", 10),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
    "HHO-Pure": lambda p, s: PureHHOOptimizer(
        hawks=p["hawks"],
        max_iterations=p["max_iterations"],
        initial_energy=p["initial_energy"],
        jump_probability=p["jump_probability"],
        max_no_improvement=p.get("max_no_improvement", 75),
        dive_count=p.get("dive_count", 3),
        levy_scale=p.get("levy_scale", 0.3),
        random_seed=s),
    "GWO-LKH": lambda p, s: GWO_LKH_Optimizer(
        pack_size=p["pack_size"],
        max_iterations=p["max_iterations"],
        initial_a=p["initial_a"],
        exploration_rate=p["exploration_rate"],
        max_no_improvement=p.get("max_no_improvement", 75),
        polish_interval=p.get("polish_interval", 25),
        polish_iters=p.get("polish_iters", 10),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
    "GWO-ALNS": lambda p, s: GWO_ALNS_Optimizer(
        pack_size=p["pack_size"],
        max_iterations=p["max_iterations"],
        initial_a=p["initial_a"],
        exploration_rate=p["exploration_rate"],
        max_no_improvement=p.get("max_no_improvement", 75),
        polish_interval=p.get("polish_interval", 25),
        alns_iterations=p.get("alns_iterations", 50),
        alns_remove_ratio=p.get("alns_remove_ratio", 0.15),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
    "HHO-LKH": lambda p, s: HHO_LKH_Optimizer(
        hawks=p["hawks"],
        max_iterations=p["max_iterations"],
        initial_energy=p["initial_energy"],
        jump_probability=p["jump_probability"],
        max_no_improvement=p.get("max_no_improvement", 75),
        dive_count=p.get("dive_count", 3),
        levy_scale=p.get("levy_scale", 0.3),
        polish_interval=p.get("polish_interval", 25),
        polish_iters=p.get("polish_iters", 10),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
    "HHO-ALNS": lambda p, s: HHO_ALNS_Optimizer(
        hawks=p["hawks"],
        max_iterations=p["max_iterations"],
        initial_energy=p["initial_energy"],
        jump_probability=p["jump_probability"],
        max_no_improvement=p.get("max_no_improvement", 75),
        dive_count=p.get("dive_count", 3),
        levy_scale=p.get("levy_scale", 0.3),
        polish_interval=p.get("polish_interval", 25),
        alns_iterations=p.get("alns_iterations", 50),
        alns_remove_ratio=p.get("alns_remove_ratio", 0.15),
        final_polish_iters=p.get("final_polish_iters", 300),
        random_seed=s),
}

def load_existing_progress():
    completed = set()
    csv_files = glob.glob(os.path.join(RESULTS_DIR, "tuning_progress_*.csv"))
    for f_path in csv_files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    p_json = json.dumps(json.loads(row["params"]), sort_keys=True)
                    key = (row["config_file"], row["problem"], row["algorithm"], p_json)
                    completed.add(key)
        except Exception:
            continue
    return completed

def evaluate_combination(algo_name, params, runs_per_combo, prob_data, is_time_matrix, base_seed, max_workers):
    durations = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for run in range(runs_per_combo):
            seed = base_seed + run
            futures.append(executor.submit(_eval_worker, algo_name, params, seed, prob_data, is_time_matrix))
            
        for f in concurrent.futures.as_completed(futures):
            durations.append(f.result())
            
    mean_len = sum(durations) / len(durations)
    return mean_len

def _eval_worker(algo_name, params, seed, prob_data, is_time_matrix):
    solver = FACTORIES[algo_name](params, seed)
    if is_time_matrix:
        solver._set_time_matrix(prob_data)
        result = solver.solve(solver._coordinates)
    else:
        result = solver.solve(prob_data)
    return result.tour_length


def load_problem(problem_config):
    prob_type = problem_config.get("type", "tsplib")
    path = os.path.join(SCRIPT_DIR, problem_config["path_relative"])
    if not os.path.exists(path):
        raise FileNotFoundError(f"Problem dosyası bulunamadı: {path}")
    if prob_type == "tsplib":
        name = problem_config["name"]
        prob = parse_tsplib(path)
        optimal = TSPLIB_OPTIMALS.get(name.lower(), None)
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
    print("Aşama 2: YAEM 2026 — Paralel & Akıllı Parametre Optimizasyonu")
    print("=" * 70)
    
    configs = list_configs()
    if not configs:
        print("[HATA] 'configs/' klasöründe konfigürasyon dosyası bulunamadı.")
        return
        
    print("\n--- Mevcut Konfigürasyonlar ---")
    env = config_manager.get_environment_info()
    print(f"[SİSTEM] OS: {env['os']} {env['os_release']} | CPU: {env['cpu']}")
    print(f"[SİSTEM] Python: {env['python']} | Numpy: {env['numpy']} | Numba: {env['numba']}")
    print("-" * 70)
    for idx, c in enumerate(configs, 1):
        print(f"  [{idx}] {c}")
        
    if len(sys.argv) > 1:
        sel_input = sys.argv[1]
    else:
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
        
        is_valid, msg = config_manager.validate_config(config)
        if not is_valid:
            print(f"[HATA] {c_file} doğrulaması başarısız: {msg}")
            continue
            
        prob_name, prob_dim, prob_data, optimal, is_time_matrix = load_problem(config["problem"])
        print(f"--> KUYRUĞA ALINDI: {c_file} | Problem: {prob_name}")
        
        tuning_sets = config["tuning_settings"]
        runs_per_combo = tuning_sets["runs_per_combination"]
        max_combos = tuning_sets["max_combinations_per_algo"]
        
        for algo_name, param_ranges in config["algorithms"].items():
            if algo_name not in FACTORIES: continue
            
            # Check if already fully tuned in DB
            already_tuned = False
            for row in existing_progress:
                # If we have any records for this config+prob+algo, we can optionally skip or count trials.
                pass
            
            print(f"   [{algo_name}] Optuna TPE ile {max_combos} deneme (Trial) başlatılıyor...")
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
            
            completed_count = [0]
            
            def objective(trial):
                params = {}
                for k, v in param_ranges.items():
                    # If it's a list, Optuna will suggest categorical (grid-like)
                    if isinstance(v, list) and len(v) > 0:
                        params[k] = trial.suggest_categorical(k, v)
                    else:
                        params[k] = v
                
                idx = trial.number + 1
                seed = 5000 + idx * 10
                
                # Evaluate parameter set with ProcessPoolExecutor over the runs
                mean_len = evaluate_combination(algo_name, params, runs_per_combo, prob_data, is_time_matrix, seed, max_workers)
                
                completed_count[0] += 1
                with open(running_csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.now().strftime("%H:%M:%S"), c_file, prob_name, algo_name, idx, round(mean_len, 2), json.dumps(params)
                    ])
                
                # Terminal output
                try:
                    best_so_far = study.best_value
                except ValueError:
                    best_so_far = mean_len
                current_best = min(best_so_far, mean_len)
                
                if completed_count[0] % 5 == 0 or completed_count[0] == max_combos:
                    gap_str = f" (Gap: %{((current_best - optimal) / optimal * 100):.2f})" if optimal else ""
                    print(f"      - {algo_name} İlerleme: {completed_count[0]}/{max_combos} | En İyi: {current_best:.2f}{gap_str}")
                    
                return mean_len
            
            study.optimize(objective, n_trials=max_combos)
            
            best_params = study.best_params
            best_mean = study.best_value
            
            # Combine missing static parameters to best_params
            for k, v in param_ranges.items():
                if k not in best_params:
                    best_params[k] = v[0] if isinstance(v, list) else v
            
            config_manager.save_to_db({
                "algorithm": algo_name, "problem": prob_name, "dimension": prob_dim,
                "runs_per_combination": runs_per_combo, "best_mean_length": best_mean,
                "parameters": best_params, "search_space_bounds": param_ranges
            })
            print(f"   [OK] {algo_name} bitti. Optuna en iyi parametreleri DB'ye eklendi.")

    print("\n" + "=" * 70)
    print("TUM ISLEMLER TAMAMLANDI.")
    print(f"Detaylı rapor için: python analyze_tuning.py")

if __name__ == "__main__":
    main()
