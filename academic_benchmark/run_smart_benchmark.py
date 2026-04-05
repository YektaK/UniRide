#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark - Geliştirilmiş Versiyon

Özellikler:
- İnteraktif algoritma seçimi
- İnteraktif problem seçimi
- Ctrl+C ile güvenli çıkış (sonuçlar kaybolmaz)
- Her test sonrası otomatik kayıt
- Progress gösterimi ve tahmini süre
- Mevcut algoritmaların listesi

Kullanım:
    cd UniRide/academic_benchmark
    python run_smart_benchmark.py

Not: Bu script proje kök dizininden çalıştırılmalı veya academic_benchmark klasöründen.
"""

import sys
import os
import json
import signal
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# ============================================================
# YOL AYARLARI - Her iki senaryo için de çalışsın
# ============================================================

# Script'in bulunduğu dizin
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Proje kök dizini (academic_benchmark'ın bir üstü)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# optimizer_api dizini
OPTIMIZER_API_DIR = os.path.join(PROJECT_ROOT, "optimizer_api")

# Python path'e ekle
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, OPTIMIZER_API_DIR)

# Metadata yolları
METADATA_PATH = os.path.join(SCRIPT_DIR, "benchmark_db", "latest_metadata.json")
HISTORY_DIR = os.path.join(SCRIPT_DIR, "benchmark_db", "history")

# ============================================================
# GLOBAL DEĞİŞKENLER
# ============================================================

# Graceful shutdown için
_shutdown_requested = False
_current_results = []
_current_metadata = {}

# ============================================================
# SIGNAL HANDLER - Ctrl+C için güvenli çıkış
# ============================================================

def signal_handler(signum, frame):
    """Ctrl+C ile güvenli çıkış - sonuçları kaydeder"""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n⚠️  DURDURMA İSTEĞİ ALINDI!")
    print("📝 Sonuçlar kaydediliyor, lütfen bekleyin...")
    
    if _current_results:
        _save_results(_current_results, _current_metadata)
        print("✅ Sonuçlar kaydedildi!")
    
    print("👋 Güvenli çıkış yapıldı.")
    sys.exit(0)

# Signal handler'ı kaydet
signal.signal(signal.SIGINT, signal_handler)

# ============================================================
# ALGORİTMA TANIMLARI
# ============================================================

@dataclass
class AlgorithmInfo:
    """Algoritma bilgileri"""
    key: str
    display_name: str
    description: str
    complexity: str
    best_for: str
    default_iterations: int
    is_sota: bool = False

# Mevcut algoritmalar
AVAILABLE_ALGORITHMS = {
    # Local Search Methods
    "2-opt": AlgorithmInfo(
        key="2-opt",
        display_name="2-opt",
        description="Klasik kenar değiştirme algoritması",
        complexity="O(n²)",
        best_for="Orta büyüklükte problemler",
        default_iterations=1000
    ),
    "3-opt": AlgorithmInfo(
        key="3-opt",
        display_name="3-opt",
        description="Üç kenar değiştirme, yüksek kalite",
        complexity="O(n³)",
        best_for="Yüksek kalite, zaman kritik değil",
        default_iterations=500
    ),
    "Or-opt": AlgorithmInfo(
        key="Or-opt",
        display_name="Or-opt",
        description="Segment relocation (1-3 müşteri taşıma)",
        complexity="O(n²)",
        best_for="Kümelenmiş müşteriler",
        default_iterations=500
    ),
    "Swap": AlgorithmInfo(
        key="Swap",
        display_name="Swap",
        description="İki müşteri yer değiştirme",
        complexity="O(n²)",
        best_for="Hızlı fine-tuning",
        default_iterations=1000
    ),
    "Hybrid": AlgorithmInfo(
        key="Hybrid",
        display_name="Hybrid",
        description="Tüm algoritmaların kombinasyonu",
        complexity="O(n³)",
        best_for="En iyi kalite, orta/büyük problemler",
        default_iterations=100
    ),
    # SOTA Solvers
    "OR-Tools": AlgorithmInfo(
        key="OR-Tools",
        display_name="OR-Tools (SOTA)",
        description="Google OR-Tools Guided Local Search",
        complexity="Yapılandırılabilir",
        best_for="Endüstri standardı, hızlı ve kaliteli",
        default_iterations=30,
        is_sota=True
    ),
    "PyVRP": AlgorithmInfo(
        key="PyVRP",
        display_name="PyVRP (SOTA)",
        description="DIMACS 2021 Kazananı Hybrid Genetic Search",
        complexity="Yapılandırılabilir",
        best_for="En yüksek kalite, akademik benchmark",
        default_iterations=30,
        is_sota=True
    ),
}

# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def clear_screen():
    """Ekranı temizle"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title: str):
    """Başlık yazdır"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_separator():
    """Ayırıcı çizgi"""
    print("-" * 70)

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

# ============================================================
# MODÜL İTHALATI
# ============================================================

def import_modules():
    """Gerekli modülleri ithal et"""
    global STRATEGIES, N_RUNS, TSPLIB_PROBLEMS, LocalSearchType
    global run_single_test, load_all_problems, run_ortools_tsp, run_pyvrp_tsp
    global get_latest_metadata, save_metadata
    
    try:
        from academic_benchmark.utils_benchmark import get_latest_metadata as _get_metadata, save_metadata as _save_metadata
        get_latest_metadata = _get_metadata
        save_metadata = _save_metadata
    except ImportError:
        # Fallback
        def get_latest_metadata(path):
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            return {"file_hashes": {}, "results": {}, "last_updated": ""}
        
        def save_metadata(path, data):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
    
    try:
        from optimizer_api.tests.run_interactive_benchmark_v2 import (
            STRATEGIES as _STRATEGIES,
            N_RUNS as _N_RUNS,
            TSPLIB_PROBLEMS as _TSPLIB_PROBLEMS,
            run_single_test as _run_single_test,
            load_all_problems as _load_all_problems,
            run_ortools_tsp as _run_ortools,
            run_pyvrp_tsp as _run_pyvrp,
        )
        from optimizer_api.utils.local_search import LocalSearchType as _LocalSearchType
        
        STRATEGIES = _STRATEGIES
        N_RUNS = _N_RUNS
        TSPLIB_PROBLEMS = _TSPLIB_PROBLEMS
        run_single_test = _run_single_test
        load_all_problems = _load_all_problems
        run_ortools_tsp = _run_ortools
        run_pyvrp_tsp = _run_pyvrp
        LocalSearchType = _LocalSearchType
        
        return True
    except ImportError as e:
        print(f"\n❌ Modül yükleme hatası: {e}")
        print(f"   Proje kökü: {PROJECT_ROOT}")
        print(f"   Optimizer API: {OPTIMIZER_API_DIR}")
        print(f"   Bu dizinler Python path'inde mi?")
        return False

# ============================================================
# SONUÇ KAYDETME
# ============================================================

def _save_results(results: List[Dict], metadata: Dict):
    """Sonuçları dosyaya kaydet"""
    os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    # Metadata güncelle
    save_metadata(METADATA_PATH, metadata)
    
    # CSV yedek
    if results:
        import csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(HISTORY_DIR, f"benchmark_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

# ============================================================
# EKRANLAR
# ============================================================

def show_algorithms_screen():
    """Algoritma listesi ekranı"""
    clear_screen()
    print_header("MÜKEMMEL ALGORİTMA KATALOĞU")
    
    print("\n📍 LOCAL SEARCH ALGORİTMALARI:")
    print_separator()
    print(f"{'Kod':<10} | {'Ad':<15} | {'Karmaşıklık':<12} | {'En İyi Kullanım'}")
    print("-" * 70)
    
    for key, algo in AVAILABLE_ALGORITHMS.items():
        if not algo.is_sota:
            print(f"{key:<10} | {algo.display_name:<15} | {algo.complexity:<12} | {algo.best_for}")
    
    print("\n🏆 SOTA (STATE-OF-THE-ART) ÇÖZÜCÜLER:")
    print_separator()
    print(f"{'Kod':<10} | {'Ad':<20} | {'Açıklama'}")
    print("-" * 70)
    
    for key, algo in AVAILABLE_ALGORITHMS.items():
        if algo.is_sota:
            status = "✅ Kurulu" if key == "OR-Tools" else ("⚠️ Kurulum Gerekli" if key == "PyVRP" else "❌ Yok")
            print(f"{key:<10} | {algo.display_name:<20} | {algo.description} [{status}]")
    
    print("\n💡 İpucu: Algoritma seçiminde birden fazla girebilirsiniz (örn: 1,3,5 veya 2-opt,Hybrid)")
    input("\nDevam etmek için Enter'a basın...")

def select_algorithms() -> List[str]:
    """Algoritma seçimi"""
    clear_screen()
    print_header("ALGORİTMA SEÇİMİ")
    
    print("\nMevcut Algoritmalar:")
    print_separator()
    
    algo_list = list(AVAILABLE_ALGORITHMS.items())
    for i, (key, algo) in enumerate(algo_list, 1):
        sota_tag = " [SOTA]" if algo.is_sota else ""
        print(f"  {i:>2}. {key:<12} - {algo.description}{sota_tag}")
    
    print("\nSeçim Seçenekleri:")
    print("  • Tek algoritma: 1 veya 2-opt")
    print("  • Birden fazla: 1,3,5 veya 2-opt,Hybrid,OR-Tools")
    print("  • Tüm Local Search: local")
    print("  • Tüm SOTA: sota")
    print("  • Hepsi: all")
    
    choice = input("\nSeçiminiz: ").strip()
    
    selected = []
    
    if choice.lower() == 'all' or choice.lower() == 'hepsi':
        selected = list(AVAILABLE_ALGORITHMS.keys())
    elif choice.lower() == 'local':
        selected = [k for k, v in AVAILABLE_ALGORITHMS.items() if not v.is_sota]
    elif choice.lower() == 'sota':
        selected = [k for k, v in AVAILABLE_ALGORITHMS.items() if v.is_sota]
    else:
        # Parse selection
        parts = [p.strip() for p in choice.split(',')]
        for part in parts:
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(algo_list):
                    selected.append(algo_list[idx][0])
            elif part in AVAILABLE_ALGORITHMS:
                selected.append(part)
    
    if selected:
        print(f"\n✅ Seçilen algoritmalar: {', '.join(selected)}")
    else:
        print("\n⚠️ Geçersiz seçim, varsayılan: Hybrid")
        selected = ["Hybrid"]
    
    input("\nDevam etmek için Enter'a basın...")
    return selected

def select_problems(all_problems: List) -> Tuple[List, str]:
    """Problem seçimi"""
    clear_screen()
    print_header("PROBLEM SEÇİMİ")
    
    # Kategorilere ayır
    small = [p for p in all_problems if p.category == 'small']
    medium = [p for p in all_problems if p.category == 'medium']
    large = [p for p in all_problems if p.category == 'large']
    
    print(f"\nMevcut Problemler:")
    print_separator()
    print(f"  1. Küçük (n ≤ 100)     : {len(small)} problem")
    print(f"  2. Orta (100 < n ≤ 500): {len(medium)} problem")
    print(f"  3. Büyük (n > 500)     : {len(large)} problem")
    
    print("\nSeçim Seçenekleri:")
    print("  • Tek kategori: 1, 2 veya 3")
    print("  • Birden fazla kategori: 1,2 veya 1,3")
    print("  • Özel problem: berlin52, kroA100 (problem adları)")
    print("  • Hızlı test: quick (ilk 3 küçük problem)")
    print("  • Hepsi: all")
    
    choice = input("\nSeçiminiz: ").strip().lower()
    
    selected = []
    mode = "custom"
    
    if choice == 'all' or choice == 'hepsi':
        selected = all_problems
        mode = "all"
    elif choice == 'quick' or choice == 'hızlı':
        selected = small[:3] if small else []
        mode = "quick"
    elif choice in ['1', 'small', 'küçük']:
        selected = small
        mode = "small"
    elif choice in ['2', 'medium', 'orta']:
        selected = medium
        mode = "medium"
    elif choice in ['3', 'large', 'büyük']:
        selected = large
        mode = "large"
    else:
        # Parse selection
        parts = [p.strip() for p in choice.split(',')]
        for part in parts:
            if part == '1':
                selected.extend(small)
            elif part == '2':
                selected.extend(medium)
            elif part == '3':
                selected.extend(large)
            else:
                # Try to find by name
                found = [p for p in all_problems if p.name.lower() == part.lower()]
                selected.extend(found)
    
    if selected:
        print(f"\n✅ Seçilen: {len(selected)} problem")
        # Kategori dağılımı
        cat_counts = {}
        for p in selected:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        for cat, count in sorted(cat_counts.items()):
            print(f"   - {cat}: {count} problem")
    else:
        print("\n⚠️ Geçersiz seçim, hızlı test modu kullanılacak")
        selected = small[:3] if small else []
        mode = "quick"
    
    input("\nDevam etmek için Enter'a basın...")
    return selected, mode

def show_summary_before_run(problems: List, algorithms: List[str]):
    """Test öncesi özet"""
    clear_screen()
    print_header("TEST ÖZETİ")
    
    total_tests = len(problems) * len(algorithms)
    
    print(f"\n📊 Test Yapılacak:")
    print(f"   • Problemler: {len(problems)}")
    print(f"   • Algoritmalar: {len(algorithms)} ({', '.join(algorithms)})")
    print(f"   • Toplam test: {total_tests}")
    
    # Tahmini süre
    avg_time_per_test = 3  # saniye
    if any(a in algorithms for a in ['3-opt', 'Hybrid']):
        avg_time_per_test = 5
    if any(a in algorithms for a in ['OR-Tools', 'PyVRP']):
        avg_time_per_test = 30  # SOTA solvers daha uzun
    
    estimated_time = total_tests * avg_time_per_test * N_RUNS / 60  # dakika
    
    print(f"\n⏱️ Tahmini Süre: ~{estimated_time:.0f} dakika")
    
    print("\n⚠️ DİKKAT:")
    print("   • Test sırasında Ctrl+C ile güvenli çıkış yapabilirsiniz")
    print("   • Sonuçlar her problem sonrası otomatik kaydedilir")
    print("   • Laptop kapatırsanız sonuçlar kaybolabilir!")
    
    print("\n[Y] Başla    [Q] Çıkış    [D] Detayları Gör")
    
    choice = input("\nSeçiminiz: ").strip().upper()
    
    if choice == 'Q':
        print("Çıkış yapılıyor...")
        sys.exit(0)
    elif choice == 'D':
        print("\n📋 Problemler:")
        for i, p in enumerate(problems, 1):
            print(f"   {i:>3}. {p.name:<15} (n={p.dimension:<5}, opt={p.optimal})")
        input("\nDevam etmek için Enter'a basın...")
        return show_summary_before_run(problems, algorithms)  # Recursive
    elif choice == 'Y':
        return True
    else:
        return show_summary_before_run(problems, algorithms)

# ============================================================
# TEST ÇALIŞTIRICI
# ============================================================

def run_tests(problems: List, algorithms: List[str], metadata: Dict) -> List[Dict]:
    """Testleri çalıştır"""
    global _shutdown_requested, _current_results, _current_metadata
    
    _current_metadata = metadata
    _current_results = []
    
    saved_results = metadata.get("results", {})
    
    total_tests = len(problems) * len(algorithms)
    completed_tests = 0
    start_time = time.time()
    
    # Strategy map oluştur
    strategy_map = {}
    for strat_name, ls_type, max_iter in STRATEGIES:
        strategy_map[strat_name] = (ls_type, max_iter)
    
    for prob_idx, problem in enumerate(problems, 1):
        if _shutdown_requested:
            break
        
        print(f"\n{'='*70}")
        print(f"[{prob_idx}/{len(problems)}] {problem.name.upper()} (n={problem.dimension}, opt={problem.optimal})")
        print(f"{'='*70}")
        
        p_res = saved_results.get(problem.name, {})
        
        for alg_idx, alg_name in enumerate(algorithms, 1):
            if _shutdown_requested:
                break
            
            # Progress
            completed_tests += 1
            elapsed = time.time() - start_time
            if completed_tests > 1:
                avg_time = elapsed / (completed_tests - 1)
                remaining = avg_time * (total_tests - completed_tests)
                progress = completed_tests / total_tests * 100
                print(f"\n[{alg_idx}/{len(algorithms)}] {alg_name} ({progress:.0f}% tamamlandı, ~{format_time(remaining)} kaldı)")
            else:
                print(f"\n[{alg_idx}/{len(algorithms)}] {alg_name}")
            
            # Önbellek kontrolü
            if alg_name in p_res and not isinstance(alg_name, str) and alg_name not in ['OR-Tools', 'PyVRP']:
                print(f"   ⏭️ Önbellekten atlanıyor (önceki sonuç var)")
                old_data = p_res[alg_name]
                _current_results.append({
                    "problem": problem.name,
                    "dimension": problem.dimension,
                    "category": problem.category,
                    "optimal": problem.optimal,
                    "strategy": alg_name,
                    "avg_length": old_data["avg_length"],
                    "avg_gap": old_data["avg_gap"],
                    "best_gap": old_data["best_gap"],
                    "avg_time_ms": old_data["avg_time_ms"],
                    "n_runs": N_RUNS,
                    "timestamp": datetime.now().isoformat()
                })
                continue
            
            # Test çalıştır
            try:
                if alg_name == "OR-Tools":
                    # OR-Tools
                    print(f"   🔄 OR-Tools çalışıyor...", end="", flush=True)
                    tour, tour_length, elapsed_time = run_ortools_tsp(problem.coordinates, 30)
                    
                    if tour_length > 0:
                        gap = ((tour_length - problem.optimal) / problem.optimal) * 100
                        result = {
                            "problem": problem.name,
                            "dimension": problem.dimension,
                            "category": problem.category,
                            "optimal": problem.optimal,
                            "strategy": alg_name,
                            "avg_length": tour_length,
                            "avg_gap": gap,
                            "best_gap": gap,
                            "avg_time_ms": elapsed_time * 1000,
                            "n_runs": 1,
                            "timestamp": datetime.now().isoformat()
                        }
                        print(f" ✅ Gap: {gap:.2f}%")
                    else:
                        print(" ❌ Çözüm bulunamadı")
                        continue
                        
                elif alg_name == "PyVRP":
                    # PyVRP
                    print(f"   🔄 PyVRP çalışıyor...", end="", flush=True)
                    try:
                        tour, tour_length, elapsed_time = run_pyvrp_tsp(problem.coordinates, 30)
                        
                        if tour_length > 0:
                            gap = ((tour_length - problem.optimal) / problem.optimal) * 100
                            result = {
                                "problem": problem.name,
                                "dimension": problem.dimension,
                                "category": problem.category,
                                "optimal": problem.optimal,
                                "strategy": alg_name,
                                "avg_length": tour_length,
                                "avg_gap": gap,
                                "best_gap": gap,
                                "avg_time_ms": elapsed_time * 1000,
                                "n_runs": 1,
                                "timestamp": datetime.now().isoformat()
                            }
                            print(f" ✅ Gap: {gap:.2f}%")
                        else:
                            print(" ❌ Çözüm bulunamadı")
                            continue
                    except ImportError:
                        print(" ⚠️ PyVRP kurulu değil")
                        continue
                    except Exception as e:
                        print(f" ❌ Hata: {e}")
                        continue
                        
                else:
                    # Local Search
                    if alg_name not in strategy_map:
                        print(f"   ⚠️ Algoritma tanımlı değil: {alg_name}")
                        continue
                    
                    ls_type, max_iter = strategy_map[alg_name]
                    print(f"   🔄 {alg_name} çalışıyor ({N_RUNS} run)...", end="", flush=True)
                    
                    run_results = []
                    for run in range(N_RUNS):
                        seed = (run + 1) * 42
                        r = run_single_test(problem, ls_type, seed, max_iter)
                        run_results.append(r)
                    
                    avg_length = sum(r["tour_length"] for r in run_results) / len(run_results)
                    avg_gap = sum(r["gap"] for r in run_results) / len(run_results)
                    avg_time = sum(r["time_ms"] for r in run_results) / len(run_results)
                    best_gap = min(r["gap"] for r in run_results)
                    
                    result = {
                        "problem": problem.name,
                        "dimension": problem.dimension,
                        "category": problem.category,
                        "optimal": problem.optimal,
                        "strategy": alg_name,
                        "avg_length": avg_length,
                        "avg_gap": avg_gap,
                        "best_gap": best_gap,
                        "avg_time_ms": avg_time,
                        "n_runs": N_RUNS,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    status = "⭐" if best_gap <= 1 else ("✅" if best_gap <= 5 else ("⚠️" if best_gap <= 10 else "❌"))
                    print(f" {status} Gap: {avg_gap:.2f}% (best: {best_gap:.2f}%)")
                
                # Sonucu kaydet
                _current_results.append(result)
                p_res[alg_name] = {
                    "avg_length": result["avg_length"],
                    "avg_gap": result["avg_gap"],
                    "best_gap": result["best_gap"],
                    "avg_time_ms": result["avg_time_ms"],
                    "timestamp": result["timestamp"]
                }
                
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                continue
        
        # Her problem sonrası kaydet
        saved_results[problem.name] = p_res
        metadata["results"] = saved_results
        metadata["last_updated"] = datetime.now().isoformat()
        _save_results(_current_results, metadata)
        print(f"\n   💾 Sonuçlar kaydedildi!")
    
    return _current_results

# ============================================================
# ANA MENÜ
# ============================================================

def main_menu(all_problems: List, metadata: Dict) -> bool:
    """Ana menü"""
    clear_screen()
    print_header("UNIRIDE SOTA BENCHMARK KONTROL MERKEZİ")
    
    saved_results = metadata.get("results", {})
    
    # Özet istatistikler
    total_tests = sum(len(r) for r in saved_results.values())
    total_problems = len(saved_results)
    
    print(f"\n📊 VERİTABANI DURUMU:")
    print(f"   • Test edilmiş problem: {total_problems}")
    print(f"   • Toplam test sayısı: {total_tests}")
    if metadata.get("last_updated"):
        print(f"   • Son güncelleme: {metadata['last_updated']}")
    
    print(f"\n🎯 HIZLI ERİŞİM:")
    print(f"   1. 📋 Algoritma Kataloğunu Gör")
    print(f"   2. 🚀 Hızlı Test (3 küçük problem, Hybrid)")
    print(f"   3. ⚙️ Özel Test (Algoritma + Problem Seç)")
    print(f"   4. 📊 Sonuçları Görüntüle")
    print(f"   5. 🗑️ Önbelleği Temizle")
    print(f"   Q. 🚪 Çıkış")
    
    choice = input("\nSeçiminiz: ").strip().upper()
    
    if choice == 'Q':
        return False
    elif choice == '1':
        show_algorithms_screen()
    elif choice == '2':
        # Hızlı test
        algorithms = ["Hybrid"]
        problems = [p for p in all_problems if p.category == 'small'][:3]
        if problems and show_summary_before_run(problems, algorithms):
            results = run_tests(problems, algorithms, metadata)
            if results:
                show_results_screen(results)
    elif choice == '3':
        # Özel test
        algorithms = select_algorithms()
        problems, mode = select_problems(all_problems)
        if problems and show_summary_before_run(problems, algorithms):
            results = run_tests(problems, algorithms, metadata)
            if results:
                show_results_screen(results)
    elif choice == '4':
        show_stored_results(saved_results)
    elif choice == '5':
        clear_cache()
    
    return True

def show_results_screen(results: List[Dict]):
    """Sonuçları göster"""
    clear_screen()
    print_header("TEST SONUÇLARI")
    
    if not results:
        print("\nHenüz sonuç yok.")
        input("\nDevam etmek için Enter'a basın...")
        return
    
    # Özet tablo
    print("\n📊 ÖZET TABLO:")
    print("-" * 90)
    print(f"{'Problem':<15} | {'n':<6} | {'Algoritma':<12} | {'Gap':<10} | {'Best Gap':<10} | {'Süre (ms)':<10}")
    print("-" * 90)
    
    # Her problem için en iyi sonucu bul
    problems = {}
    for r in results:
        key = r["problem"]
        if key not in problems or r["avg_gap"] < problems[key]["avg_gap"]:
            problems[key] = r
    
    for name, r in sorted(problems.items(), key=lambda x: x[1]['dimension']):
        status = "⭐" if r["best_gap"] <= 1 else ("✅" if r["best_gap"] <= 5 else ("⚠️" if r["best_gap"] <= 10 else "❌"))
        print(f"{r['problem']:<15} | {r['dimension']:<6} | {r['strategy']:<12} | {r['avg_gap']:>8.2f}% | {r['best_gap']:>8.2f}% | {r['avg_time_ms']:>8.0f} {status}")
    
    # Algoritma performansı
    print("\n📈 ALGORİTMA PERFORMANSI:")
    print("-" * 70)
    
    algo_stats = {}
    for r in results:
        strat = r["strategy"]
        if strat not in algo_stats:
            algo_stats[strat] = {"gaps": [], "times": []}
        algo_stats[strat]["gaps"].append(r["avg_gap"])
        algo_stats[strat]["times"].append(r["avg_time_ms"])
    
    print(f"{'Algoritma':<15} | {'Ort Gap':<12} | {'Min Gap':<12} | {'Ort Süre (ms)':<15}")
    print("-" * 60)
    
    for strat, stats in sorted(algo_stats.items(), key=lambda x: sum(x[1]["gaps"])/len(x[1]["gaps"])):
        avg = sum(stats["gaps"]) / len(stats["gaps"])
        min_gap = min(stats["gaps"])
        avg_time = sum(stats["times"]) / len(stats["times"])
        print(f"{strat:<15} | {avg:>10.2f}% | {min_gap:>10.2f}% | {avg_time:>13.0f}")
    
    input("\n\nAna menüye dönmek için Enter'a basın...")

def show_stored_results(saved_results: Dict):
    """Kayıtlı sonuçları göster"""
    clear_screen()
    print_header("KAYITLI SONUÇLAR")
    
    if not saved_results:
        print("\nHenüz kayıtlı sonuç yok.")
        input("\nDevam etmek için Enter'a basın...")
        return
    
    print(f"\nKayıtlı Problemler: {len(saved_results)}")
    print("-" * 50)
    
    for prob_name, results in sorted(saved_results.items()):
        algos = list(results.keys())
        best = min(algos, key=lambda x: results[x]["avg_gap"])
        best_gap = results[best]["avg_gap"]
        print(f"  {prob_name:<20} | {len(algos)} algoritma | En iyi: {best} ({best_gap:.2f}%)")
    
    input("\n\nDevam etmek için Enter'a basın...")

def clear_cache():
    """Önbelleği temizle"""
    clear_screen()
    print_header("ÖNBELLEK TEMİZLEME")
    
    print("\n⚠️ DİKKAT: Bu işlem tüm kayıtlı sonuçları silecek!")
    choice = input("\nEmin misiniz? (evet/hayır): ").strip().lower()
    
    if choice in ['evet', 'e', 'yes', 'y']:
        if os.path.exists(METADATA_PATH):
            os.remove(METADATA_PATH)
            print("\n✅ Önbellek temizlendi!")
        else:
            print("\nÖnbellek zaten boş.")
    else:
        print("\nİşlem iptal edildi.")
    
    input("\nDevam etmek için Enter'a basın...")

# ============================================================
# ANA FONKSİYON
# ============================================================

def main():
    """Ana fonksiyon"""
    print("\n🔄 Modüller yükleniyor...")
    
    if not import_modules():
        print("\n❌ Modül yükleme başarısız. Lütfen proje dizininden çalıştırın:")
        print(f"   cd {PROJECT_ROOT}")
        print("   python academic_benchmark/run_smart_benchmark.py")
        sys.exit(1)
    
    print(f"✅ Modüller yüklendi!")
    print(f"   Proje kökü: {PROJECT_ROOT}")
    print(f"   Algoritma sayısı: {len(AVAILABLE_ALGORITHMS)}")
    
    # Problemleri yükle
    print("\n🔄 TSPLIB problemleri yükleniyor...")
    all_problems = []
    
    for category in ['small', 'medium', 'large']:
        probs = load_all_problems(category)
        all_problems.extend(probs)
        print(f"   {category}: {len(probs)} problem")
    
    print(f"✅ Toplam {len(all_problems)} problem yüklendi!")
    
    # Metadata yükle
    metadata = get_latest_metadata(METADATA_PATH)
    
    # Ana döngü
    while main_menu(all_problems, metadata):
        metadata = get_latest_metadata(METADATA_PATH)
    
    print("\n👋 Hoşça kalın!")

if __name__ == "__main__":
    main()
