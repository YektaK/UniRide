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

# v2 kullan - gerçek TSPLIB dosyalarını indirir
try:
    from optimizer_api.tests.run_interactive_benchmark_v2 import (
        STRATEGIES, 
        run_single_test, 
        print_summary_table,
        N_RUNS,
        load_all_problems,
        TSPLIB_PROBLEMS
    )
    USE_V2 = True
    print("[INFO] run_interactive_benchmark_v2 kullanılıyor (gerçek TSPLIB koordinatları)")
except ImportError as e:
    print(f"[WARNING] v2 yüklenemedi: {e}, v1 kullanılıyor")
    from optimizer_api.tests.run_interactive_benchmark import (
        STRATEGIES, 
        run_single_test, 
        print_summary_table,
        N_RUNS
    )
    USE_V2 = False

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

def load_problems_smart():
    """Problemleri akıllı şekilde yükle - v2 öncelikli"""
    all_problems = []
    
    if USE_V2:
        # v2 kullan - gerçek TSPLIB dosyalarını indirir
        print("\n[INFO] TSPLIB problemleri yükleniyor (gerçek koordinatlar)...")
        for category in ['small', 'medium', 'large']:
            probs = load_all_problems(category)
            all_problems.extend(probs)
    else:
        # v1 fallback
        loader = BenchmarkDatasetLoader(tsplib_folder=os.path.join("optimizer_api", "tests", "tsplib_data"))
        all_problems = loader.load_all_datasets()
    
    return all_problems

def format_time(seconds: float) -> str:
    """Saniyeyi okunabilir Türkçe formata çevir"""
    if seconds < 60:
        return f"{seconds:.1f}sn"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}dk {secs}sn"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}sa {minutes}dk"

def make_progress_bar(completed: int, total: int, width: int = 10) -> str:
    """Progress bar oluştur"""
    filled = int((completed / total) * width) if total > 0 else 0
    empty = width - filled
    return "█" * filled + "░" * empty

def print_compact_status(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """Compact status görünümü - her problem için bir satır"""
    total_algos = len(all_strat_names)
    
    print("\n" + "═" * 80)
    print("BENCHMARK STATUS OVERVIEW")
    print("═" * 80)
    
    # Kategorilere göre grupla ve sırala
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
    
    total_completed = 0
    total_tests = 0
    
    for cat_name, cat_label in [('small', 'KÜÇÜK'), ('medium', 'ORTA'), ('large', 'BÜYÜK')]:
        problems = categories[cat_name]
        if not problems:
            continue
            
        print(f"\n[{cat_label} PROBLEMLER]")
        print("─" * 80)
        
        # Boyuta göre sırala
        problems.sort(key=lambda x: x.dimension)
        
        for p in problems:
            p_res = saved_results.get(p.name, {})
            tested_strats = list(p_res.keys())
            completed = len([s for s in tested_strats if s in all_strat_names])
            missing = [s for s in all_strat_names if s not in tested_strats]
            
            total_completed += completed
            total_tests += total_algos
            
            # Progress bar
            bar = make_progress_bar(completed, total_algos)
            
            # Status
            if completed == total_algos:
                status = "✓ COMPLETE"
                missing_str = ""
            else:
                status = ""
                # Missing algoritmaları kısalt (3'ten fazlaysa ...)
                if len(missing) <= 3:
                    missing_str = f"Missing: {', '.join(missing)}"
                else:
                    missing_str = f"Missing: {', '.join(missing[:3])}... (+{len(missing)-3})"
            
            # Satır yazdır
            line = f"{p.name:<12} (n={p.dimension:<4}) : [{bar}] {completed:>2}/{total_algos}"
            if status:
                line += f" {status}"
            elif missing_str:
                line += f" | {missing_str}"
            
            print(line)
    
    # Özet
    print("\n" + "─" * 80)
    pct = (total_completed / total_tests * 100) if total_tests > 0 else 0
    print(f"ÖZET: {len(all_problems)} problem | {total_completed}/{total_tests} tamamlandı ({pct:.1f}%)")
    print("═" * 80)

def print_problem_detail(problem, p_res: Dict, all_strat_names: List[str]):
    """Tek problem için detaylı görünüm"""
    print("\n" + "─" * 70)
    print(f"{problem.name} (n={problem.dimension}, optimal={problem.optimal})")
    print("─" * 70)
    
    for strat_name in all_strat_names:
        if strat_name in p_res:
            data = p_res[strat_name]
            best_gap = data.get("best_gap", 0)
            avg_gap = data.get("avg_gap", 0)
            avg_time = data.get("avg_time_ms", 0)
            
            # Run count (metadata'da yoksa N_RUNS varsay)
            n_runs = data.get("n_runs", N_RUNS)
            
            print(f"  ✓ {strat_name:<12} : {n_runs}/{N_RUNS} runs | "
                  f"Best GAP: {best_gap:>6.2f}% | Avg GAP: {avg_gap:>6.2f}% | "
                  f"Avg Time: {avg_time:>7.1f}ms")
        else:
            print(f"  ✗ {strat_name:<12} : 0/{N_RUNS} runs | MISSING")
    
    print("─" * 70)

def interactive_detail_mode(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """İnteraktif detay modu"""
    # Problem lookup dict
    problem_dict = {p.name: p for p in all_problems}
    
    while True:
        print("\n" + "─" * 70)
        print("Detay görmek için problem adı girin (örn: berlin52, eil51)")
        print("Tüm problemleri listelemek için 'list' yazın")
        print("Çıkmak için 'q' veya Enter'a basın")
        print("─" * 70)
        
        user_input = input("> ").strip().lower()
        
        if not user_input or user_input == 'q':
            print("Detay modundan çıkılıyor...")
            break
        
        if user_input == 'list':
            print("\nMevcut problemler:")
            for p in sorted(all_problems, key=lambda x: x.dimension):
                print(f"  {p.name:<12} (n={p.dimension:<5}, cat={p.category})")
            continue
        
        if user_input in problem_dict:
            problem = problem_dict[user_input]
            p_res = saved_results.get(problem.name, {})
            print_problem_detail(problem, p_res, all_strat_names)
        else:
            # Yakın eşleşme ara
            matches = [p.name for p in all_problems if user_input in p.name]
            if matches:
                print(f"'{user_input}' bulunamadı. Benzer problemler: {', '.join(matches[:5])}")
            else:
                print(f"'{user_input}' adlı problem bulunamadı. 'list' yazarak tüm problemleri görebilirsiniz.")

def main():
    metadata = get_latest_metadata(METADATA_PATH)
    algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
    
    # Problemleri yükle
    all_problems = load_problems_smart()
    
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
        
        # Compact Status View
        print_compact_status(all_problems, saved_results, all_strat_names)
        
        print("\n=> NE YAPMAK İSTERSİNİZ?")
        print("  [A] Zorunlu: Değişen/Yeni Kodları Tüm Çözümler İçin Baştan Test Et")
        print("  [B] Eksikleri Tamamla: Sadece Hiç Test Edilmemiş Problem/Stratejileri Çöz")
        print("  [C] Hızlı Mod: Sadece Küçük Problemlerde Tüm Algoritmaları Çalıştır")
        print("  [D] Kapsamlı (Tehlikeli): Her Şeyi (Tüm Kod + Tüm Problemler) Yeniden Test Et")
        print("  [S] Detay Modu: Bir Problem İçin Detaylı Sonuçları Görüntüle")
        print("  [Q] Çıkış")
        
        choice = input("\nSeçiminiz: ").strip().upper()
        
        if choice == 'Q':
            print("Çıkış yapılıyor...")
            break
        elif choice == 'S':
            interactive_detail_mode(all_problems, saved_results, all_strat_names)
            input("\nAna menüye dönmek için Enter'a basın...")
            continue
        
        problems_to_run = []
        strategies_to_run = []
        
        if choice == 'A':
            if not any_changed:
                print("Değişen bir kod yok. Önbelleğiniz son kod durumunuzla birebir aynı!")
                input("Devam etmek için Enter'a basın...")
                continue
            problems_to_run = all_problems
            strategies_to_run = all_strat_names
        elif choice == 'B':
            # Eksik olan problemleri bul
            for p in all_problems:
                p_res = saved_results.get(p.name, {})
                missing = [s for s in all_strat_names if s not in p_res]
                if missing:
                    problems_to_run.append(p)
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
