#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime
from typing import List, Dict

# Proje yollarını entegre et
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "optimizer_api")))

from academic_benchmark.utils_benchmark import get_latest_metadata, save_metadata, check_algorithms_status
from academic_benchmark.dataset_loader import BenchmarkDatasetLoader
from optimizer_api.tests.run_interactive_benchmark import (
    STRATEGIES, 
    run_single_test, 
    print_summary_table,
    N_RUNS
)

METADATA_PATH = os.path.join(os.path.dirname(__file__), "benchmark_db", "latest_metadata.json")
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "benchmark_db", "history")

# Hangi mimari kodların değişimlerini takip edeceğiz?
ALGORITHMS_TO_CHECK = {
    "LocalSearchEngine": "optimizer_api/utils/local_search.py",
    "SplitDecoder": "optimizer_api/utils/split_decoder.py",
    "LinearSplitDecoder": "optimizer_api/utils/linear_split_decoder.py",
    "CVRPTWWrapper": "optimizer_api/strategies/cvrptw_wrapper.py"
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    metadata = get_latest_metadata(METADATA_PATH)
    algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
    
    # Dataset Loader kurulumu
    loader = BenchmarkDatasetLoader(tsplib_folder=os.path.join("optimizer_api", "tests", "tsplib_data"))
    all_problems = loader.load_all_datasets()
    
    saved_results = metadata.get("results", {})
    all_strat_names = [s[0] for s in STRATEGIES]
    
    while True:
        clear_screen()
        print("=" * 70)
        print("          UNIRIDE SOTA BENCHMARK KONTROL MERKEZİ")
        print("=" * 70)
        
        print("\n[🔍 ALGORİTMA DURUMLARI]")
        any_changed = False
        for algo, status in algo_status.items():
            symbol = "❌" if status == "DOSYA_YOK" else ("⚠️" if status == "DEGISMIS" else ("✨" if status == "YENI" else "✅"))
            print(f"  {symbol} {algo:<20} : {status}")
            if status in ["DEGISMIS", "YENI"]:
                any_changed = True
        
        print("\n[📊 VERİSETLERİ / PROBLEMLER]")
        small_missing = []
        medium_missing = []
        large_missing = []
        
        for p in all_problems:
            p_res = saved_results.get(p.name, {})
            tested_strats = list(p_res.keys())
            missing = [s for s in all_strat_names if s not in tested_strats]
            if missing:
                if p.category == "small": small_missing.append(p.name)
                elif p.category == "medium": medium_missing.append(p.name)
                elif p.category == "large": large_missing.append(p.name)
                
        small_total = len([p for p in all_problems if p.category == "small"])
        med_total = len([p for p in all_problems if p.category == "medium"])
        large_total = len([p for p in all_problems if p.category == "large"])
        
        print(f"  1. Küçük TSPLib  ({small_total:<3} Problem) -> [{len(small_missing)} Problemde Eksik Test Var]")
        print(f"  2. Orta TSPLib   ({med_total:<3} Problem) -> [{len(medium_missing)} Problemde Eksik Test Var]")
        print(f"  3. Büyük TSPLib  ({large_total:<3} Problem) -> [{len(large_missing)} Problemde Eksik Test Var]")
        
        print("\n=> NE YAPMAK İSTERSİNİZ?")
        print("  [A] Zorunlu: Değişen/Yeni Kodları Tüm Çözümler İçin Baştan Test Et")
        print("  [B] Eksikleri Tamamla: Sadece Hiç Test Edilmemiş Problem/Stratejileri Çöz")
        print("  [C] Hızlı Mod: Sadece Küçük Problemlerde Tüm Algoritmaları Çalıştır")
        print("  [D] Kapsamlı (Tehlikeli): Her Şeyi (Tüm Kod + Tüm Problemler) Yeniden Test Et")
        print("  [Q] Çıkış")
        
        choice = input("\nSeçiminiz: ").strip().upper()
        
        problems_to_run = []
        strategies_to_run = []
        
        if choice == 'Q':
            print("Çıkış yapılıyor...")
            break
        elif choice == 'A':
            if not any_changed:
                print("Değişen bir kod yok. Önbelleğiniz son kod durumunuzla birebir aynı!")
                input("Devam etmek için Enter'a basın...")
                continue
            problems_to_run = all_problems
            strategies_to_run = all_strat_names
        elif choice == 'B':
            problems_to_run = [p for p in all_problems if p.name in small_missing + medium_missing + large_missing]
            strategies_to_run = all_strat_names 
        elif choice == 'C':
            problems_to_run = [p for p in all_problems if p.category == 'small']
            strategies_to_run = all_strat_names
        elif choice == 'D':
            problems_to_run = all_problems
            strategies_to_run = all_strat_names
        else:
            print("Geçersiz seçim.")
            input("Devam etmek için Enter'a basın...")
            continue
            
        if not problems_to_run:
            print("Test edilecek problem bulunamadı (Her şey tamamlanmış).")
            input("Devam etmek için Enter'a basın...")
            continue
            
        print(f"\n🚀 TEST BAŞLIYOR... Görev Kuyruğu: {len(problems_to_run)} Problem")
        
        all_results_flat = []
        
        for i, problem in enumerate(problems_to_run, 1):
            print(f"\n[{i}/{len(problems_to_run)}] {problem.name.upper()} Test Ediliyor... (Optimum: {problem.optimal})")
            
            p_res = saved_results.get(problem.name, {})
            
            for strat_name, ls_type, max_iter in STRATEGIES:
                if strat_name not in strategies_to_run:
                    continue
                    
                # B Modu: Önbellekte varsa oynamaya gerek yok
                if choice == 'B' and strat_name in p_res:
                    print(f"    - {strat_name:<10} [Önbellekten Geçildi]")
                    
                    # Eski değeri flat listeye yansıt ki tablo kopuk çıkmasın
                    old_data = p_res[strat_name]
                    all_results_flat.append({
                        "problem": problem.name,
                        "dimension": problem.dimension,
                        "category": problem.category,
                        "optimal": problem.optimal,
                        "strategy": strat_name,
                        "avg_length": old_data["avg_length"],
                        "avg_gap": old_data["avg_gap"],
                        "best_length": old_data.get("avg_length", 0), # Simple mock for view
                        "best_gap": old_data["best_gap"],
                        "avg_time_ms": old_data["avg_time_ms"],
                        "n_runs": N_RUNS,
                    })
                    continue
                    
                print(f"    - {strat_name:<10} çalışıyor... ", end="", flush=True)
                
                run_avg_results = []
                for run in range(N_RUNS):
                    seed = (run + 1) * 42
                    result = run_single_test(problem, ls_type, seed, max_iter)
                    run_avg_results.append(result)
                    
                avg_length = sum(r["tour_length"] for r in run_avg_results) / len(run_avg_results)
                avg_gap = sum(r["gap"] for r in run_avg_results) / len(run_avg_results)
                avg_time = sum(r["time_ms"] for r in run_avg_results) / len(run_avg_results)
                best_length = min(r["tour_length"] for r in run_avg_results)
                best_gap = min(r["gap"] for r in run_avg_results)
                
                print(f"Bitti. Ortalama Gap: {avg_gap:.2f}%")
                
                p_res[strat_name] = {
                    "avg_length": avg_length,
                    "avg_gap": avg_gap,
                    "best_gap": best_gap,
                    "avg_time_ms": avg_time,
                    "timestamp": datetime.now().isoformat()
                }
                
                all_results_flat.append({
                    "problem": problem.name,
                    "dimension": problem.dimension,
                    "category": problem.category,
                    "optimal": problem.optimal,
                    "strategy": strat_name,
                    "avg_length": avg_length,
                    "avg_gap": avg_gap,
                    "best_length": best_length,
                    "best_gap": best_gap,
                    "avg_time_ms": avg_time,
                    "n_runs": N_RUNS,
                })
                
            saved_results[problem.name] = p_res
        
        # Test başarılıysa HASH'leri güncelle
        from academic_benchmark.utils_benchmark import get_file_hash
        new_hashes = {}
        for algo, fp in ALGORITHMS_TO_CHECK.items():
            if os.path.exists(fp):
                new_hashes[algo] = get_file_hash(fp)
                
        metadata["file_hashes"] = new_hashes
        metadata["results"] = saved_results
        metadata["last_updated"] = datetime.now().isoformat()
        
        save_metadata(METADATA_PATH, metadata)
        
        import csv
        if all_results_flat:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(HISTORY_DIR, f"smart_run_{timestamp}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_results_flat[0].keys())
                writer.writeheader()
                writer.writerows(all_results_flat)
            
            print_summary_table(all_results_flat)
            print(f"\n✅ Tüm sonuçlar başarıyla 'latest_metadata.json'a işlendi.")
            print(f"📦 Excel/Log yedeği geçmişe alındı: {csv_path}")
            
        input("\nAna menüye dönmek için Enter'a basın...")
        metadata = get_latest_metadata(METADATA_PATH)
        algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
        saved_results = metadata.get("results", {})
        
if __name__ == "__main__":
    main()
