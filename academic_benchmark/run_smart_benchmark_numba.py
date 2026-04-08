#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark - NUMBA OPTIMIZED VERSION

Özellikler:
- Numba JIT compilation ile 10-50x hız artışı
- Ctrl+C ile güvenli çıkış (sonuçlar kaybolmaz)
- Her algoritma sonucunda anında kayıt
- Gerçek süre ölçümü ve dinamik tahmin
- Multiprocessing ile paralel çalıştırma
- Progress gösterimi
- Çoklu problem/algoritma seçimi

Gereksinimler:
    pip install numba numpy

Kullanım:
    cd /home/z/my-project/DOURide
    python academic_benchmark/run_smart_benchmark_numba.py
"""
import sys
import os
import io

# Windows encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import signal
import time
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from multiprocessing import Pool, cpu_count, Manager
import threading

# Proje yollarını entegre et
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "optimizer_api")))

from academic_benchmark.utils_benchmark import get_latest_metadata, save_metadata, check_algorithms_status, get_file_hash
from academic_benchmark.dataset_loader import BenchmarkDatasetLoader

# NUMBA OPTIMIZED v2 kullan
try:
    from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
        STRATEGIES, 
        run_single_test, 
        print_summary_table,
        load_all_problems,
        TSPLIB_PROBLEMS,
        NUMBA_AVAILABLE,
    )
    # N_RUNS default degeri
    DEFAULT_N_RUNS = 3
    N_RUNS = DEFAULT_N_RUNS  # Global degisken, kullanicidan alinacak
    USE_V2 = True
    if NUMBA_AVAILABLE:
        print("[INFO] NUMBA JIT ENABLED - 10-50x speedup!")
    else:
        print("[WARNING] Numba not available. Install with: pip install numba")
except ImportError as e:
    print(f"[WARNING] Numba v2 yüklenemedi: {e}")
    # Fallback to non-Numba version
    try:
        from optimizer_api.tests.run_interactive_benchmark_v2 import (
            STRATEGIES, 
            run_single_test, 
            print_summary_table,
            load_all_problems,
            TSPLIB_PROBLEMS
        )
        DEFAULT_N_RUNS = 3
        N_RUNS = DEFAULT_N_RUNS
        USE_V2 = True
        NUMBA_AVAILABLE = False
        print("[INFO] Using non-Numba fallback version")
    except ImportError as e2:
        print(f"[ERROR] Benchmark modules not found: {e2}")
        sys.exit(1)

METADATA_PATH = os.path.join(os.path.dirname(__file__), "benchmark_db", "latest_metadata_numba.json")
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "benchmark_db", "history")

# Hangi mimari kodların değişimlerini takip edeceğiz?
# Scriptin bulunduğu dizine göre ayarlanmış yol
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

ALGORITHMS_TO_CHECK = {
    "LocalSearchEngine_NUMBA": os.path.join(PROJECT_ROOT, "optimizer_api", "utils", "local_search_numba.py"),
    "GA_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "ga_strategy.py"),
    "PSO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "pso_strategy.py"),
    "GWO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "gwo_strategy.py"),
    "HHO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "hho_strategy.py"),
}

# ============================================================
# GLOBAL DEĞİŞKENLER - Graceful Shutdown için
# ============================================================
_shutdown_requested = False
_current_metadata = None
_current_results = []

# Multiprocessing için - başlangıç değeri, kullanıcı tarafından değiştirilecek
NUM_WORKERS = min(cpu_count(), 4)

def get_cpu_info() -> dict:
    """CPU bilgilerini topla ve optimal worker sayısı öner"""
    import platform
    
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or cpu_count()
        logical_cores = psutil.cpu_count(logical=True) or cpu_count()
        has_smt = logical_cores > physical_cores
    except ImportError:
        physical_cores = cpu_count()
        logical_cores = cpu_count()
        has_smt = False
    
    # CPU-bound task'ler için optimal worker sayısı
    # NUMBA JIT ile çalışan kod CPU-intensive olduğu için
    # fiziksel çekirdek sayısı veya biraz daha az optimal
    if has_smt:
        # Hyperthreading/SMT varsa fiziksel çekirdek sayısı optimal
        recommended = physical_cores
    else:
        # Yoksa biraz daha az kullan (sistem için yer aç)
        recommended = max(1, physical_cores - 1)
    
    # Maksimum sınır (aşırı kaynak kullanımını önle)
    recommended = min(recommended, 16)
    
    return {
        'physical_cores': physical_cores,
        'logical_cores': logical_cores,
        'has_smt': has_smt,
        'recommended_workers': recommended,
        'platform': platform.processor() or platform.machine()
    }

def select_worker_count() -> int:
    """Kullanıcıdan worker sayısını al veya otomatik öner"""
    cpu_info = get_cpu_info()
    
    print("\n" + "="*60)
    print("[CPU] ISLEMCI BILGILERI")
    print("="*60)
    print(f"   Platform      : {cpu_info['platform']}")
    print(f"   Fiziksel Cekirdek : {cpu_info['physical_cores']}")
    print(f"   Mantiksal Cekirdek: {cpu_info['logical_cores']}")
    if cpu_info['has_smt']:
        print(f"   SMT/Hyperthreading: Aktif")
    print()
    
    recommended = cpu_info['recommended_workers']
    print(f"[ONERI] Optimal worker sayisi: {recommended}")
    print("   - CPU-bound islemler icin fiziksel cekirdek sayisi optimal")
    print("   - NUMBA JIT zaten cok hizli, fazla worker overhead yaratabilir")
    print()
    print("[SECIM] Worker sayisi belirleyin:")
    print(f"   [1] {recommended} (Onerilen - Otomatik)")
    print(f"   [2] {min(cpu_info['logical_cores'], 8)} (Standart - maks 8)")
    print(f"   [3] {min(cpu_info['logical_cores'], 12)} (Yuksek performans)")
    print(f"   [4] {min(cpu_info['logical_cores'], 16)} (Maksimum)")
    print("   [C] Custom - Kendiniz girin")
    print(f"   [Enter] Varsayilan: {min(cpu_count(), 4)}")
    
    choice = input("\nSeciminiz: ").strip().upper()
    
    if choice == '' or choice == '1':
        return recommended
    elif choice == '2':
        return min(cpu_info['logical_cores'], 8)
    elif choice == '3':
        return min(cpu_info['logical_cores'], 12)
    elif choice == '4':
        return min(cpu_info['logical_cores'], 16)
    elif choice == 'C':
        try:
            custom = int(input(f"   Worker sayisi (1-{cpu_info['logical_cores']}): ").strip())
            return max(1, min(custom, cpu_info['logical_cores']))
        except ValueError:
            print("   Gecersiz giris, onerilen kullanilacak")
            return recommended
    else:
        return min(cpu_count(), 4)

def signal_handler(signum, frame):
    """Ctrl+C ile güvenli çıkış - sonuçları kaydeder"""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] DURDURMA ISTEĞI ALINDI!")
    print("[NOTE] Mevcut sonuçlar kaydediliyor, lütfen bekleyin...")
    
    if _current_metadata and _current_results:
        save_metadata(METADATA_PATH, _current_metadata)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(HISTORY_DIR, f"interrupted_numba_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_current_results[0].keys())
            writer.writeheader()
            writer.writerows(_current_results)
        print(f"[OK] {len(_current_results)} sonuç kaydedildi: {csv_path}")
    
    print("Güvenli çıkış yapıldı.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_problems_smart():
    """Problemleri akıllı şekilde yükle - v2 öncelikli"""
    all_problems = []
    
    if USE_V2:
        print("\n[INFO] TSPLIB problemleri yükleniyor (gerçek koordinatlar, NUMBA)...")
        for category in ['small', 'medium', 'large']:
            probs = load_all_problems(category)
            all_problems.extend(probs)
    else:
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


def update_algorithm_hashes(metadata: Dict[str, Any]):
    """Track current algorithm hashes with backward compatibility fields."""
    hashes = {}
    for algo_name, filepath in ALGORITHMS_TO_CHECK.items():
        if os.path.exists(filepath):
            hashes[algo_name] = get_file_hash(filepath)
    metadata["algorithm_hashes"] = hashes
    metadata["file_hashes"] = hashes


def get_algorithm_type(strat_name: str, params: Optional[Dict[str, Any]] = None) -> str:
    if params and "algorithm_type" in params:
        return str(params["algorithm_type"])
    if strat_name in {"GA", "PSO", "GWO", "HHO"}:
        return "meta_heuristic"
    return "local_search"


def normalize_strategy_entry(entry: Tuple[Any, ...]) -> Tuple[str, Any, Dict[str, Any]]:
    """Normalize strategy tuple from benchmark module."""
    if len(entry) < 2:
        raise ValueError(f"Invalid strategy entry: {entry}")
    if len(entry) >= 3 and isinstance(entry[2], dict):
        return entry[0], entry[1], entry[2].copy()
    # Backward compatibility: (name, LocalSearchType, max_iterations)
    max_iterations = entry[2] if len(entry) > 2 else 1000
    return entry[0], entry[1], {"max_iterations": int(max_iterations), "algorithm_type": "local_search"}

# ============================================================
# SÜRE ÖLÇÜM VE TAHMİN SİSTEMİ (Numba için optimize edilmiş)
# ============================================================

class DynamicTimeEstimator:
    """Gerçek ölçümlere dayalı dinamik süre tahmini"""
    
    def __init__(self):
        self.measurements = []
        self.category_avg = {'small': [], 'medium': [], 'large': []}
        self.algo_avg = {}
    
    def add_measurement(self, dimension: int, category: str, algorithm: str, time_ms: float):
        self.measurements.append((dimension, category, algorithm, time_ms))
        self.category_avg[category].append(time_ms)
        
        if algorithm not in self.algo_avg:
            self.algo_avg[algorithm] = []
        self.algo_avg[algorithm].append(time_ms)
    
    def estimate_time(self, dimension: int, category: str, algorithm: str) -> Optional[float]:
        similar = [(d, t) for d, c, a, t in self.measurements 
                   if a == algorithm and abs(d - dimension) < dimension * 0.3]
        
        if similar:
            return sum(t for _, t in similar) / len(similar)
        
        if algorithm in self.algo_avg and self.algo_avg[algorithm]:
            algo_time = sum(self.algo_avg[algorithm]) / len(self.algo_avg[algorithm])
            size_factor = dimension / 100
            return algo_time * size_factor
        
        if category in self.category_avg and self.category_avg[category]:
            return sum(self.category_avg[category]) / len(self.category_avg[category])
        
        return None
    
    def estimate_remaining(self, pending_tests: List[Tuple], num_workers: int = NUM_WORKERS) -> float:
        total_ms = 0
        unknown_count = 0
        
        for dimension, category, algorithm in pending_tests:
            est = self.estimate_time(dimension, category, algorithm)
            if est:
                total_ms += est
            else:
                unknown_count += 1
                # Numba optimized defaults (much faster)
                defaults = {'small': 300, 'medium': 1500, 'large': 8000}
                total_ms += defaults.get(category, 1000)
        
        total_ms = total_ms / num_workers
        total_ms *= N_RUNS
        
        return total_ms / 1000


def estimate_total_time(problems: List, algorithms: List[str], num_workers: int = NUM_WORKERS) -> float:
    """Tahmini toplam süre hesapla (saniye) - NUMBA OPTIMIZED (much faster)"""
    # Numba optimized base times (10-50x faster than pure Python)
    base_times = {
        'small': 300,    # ~0.3sn (NUMBA)
        'medium': 1500,  # ~1.5sn (NUMBA)
        'large': 8000,   # ~8sn (NUMBA)
    }
    
    algo_multipliers = {
        '2-opt': 1.0,
        '3-opt': 2.5,    # Reduced due to Numba
        'Or-opt': 1.2,
        'Swap': 0.6,
        'Hybrid': 4.0,   # Reduced due to Numba
    }
    
    total_ms = 0
    for p in problems:
        base = base_times.get(p.category, 1000)
        for alg in algorithms:
            mult = algo_multipliers.get(alg, 1.5)
            total_ms += base * mult
    
    total_ms *= N_RUNS
    total_ms = total_ms / num_workers
    
    return total_ms / 1000

def make_progress_bar(completed: int, total: int, width: int = 10) -> str:
    filled = int((completed / total) * width) if total > 0 else 0
    empty = width - filled
    return "#" * filled + "." * empty

def print_compact_status(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """Compact status görünümü"""
    total_algos = len(all_strat_names)
    
    print("\n" + "=" * 80)
    print("BENCHMARK STATUS OVERVIEW (NUMBA OPTIMIZED)")
    print("=" * 80)
    
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
    
    total_completed = 0
    total_tests = 0
    
    for cat_name, cat_label in [('small', 'KUCUK'), ('medium', 'ORTA'), ('large', 'BUYUK')]:
        problems = categories[cat_name]
        if not problems:
            continue
            
        print(f"\n[{cat_label} PROBLEMLER]")
        print("-" * 80)
        
        problems.sort(key=lambda x: x.dimension)
        
        for p in problems:
            p_res = saved_results.get(p.name, {})
            tested_strats = list(p_res.keys())
            completed = len([s for s in tested_strats if s in all_strat_names])
            missing = [s for s in all_strat_names if s not in tested_strats]
            
            total_completed += completed
            total_tests += total_algos
            
            bar = make_progress_bar(completed, total_algos)
            
            if completed == total_algos:
                status = "v COMPLETE"
                missing_str = ""
            else:
                status = ""
                if len(missing) <= 3:
                    missing_str = f"Missing: {', '.join(missing)}"
                else:
                    missing_str = f"Missing: {', '.join(missing[:3])}... (+{len(missing)-3})"
            
            line = f"{p.name:<12} (n={p.dimension:<4}) : [{bar}] {completed:>2}/{total_algos}"
            if status:
                line += f" {status}"
            elif missing_str:
                line += f" | {missing_str}"
            
            print(line)
    
    print("\n" + "-" * 80)
    pct = (total_completed / total_tests * 100) if total_tests > 0 else 0
    print(f"OZET: {len(all_problems)} problem | {total_completed}/{total_tests} tamamlandi ({pct:.1f}%)")
    print("=" * 80)

def print_problem_detail(problem, p_res: Dict, all_strat_names: List[str]):
    """Tek problem için detaylı görünüm"""
    print("\n" + "-" * 70)
    print(f"{problem.name} (n={problem.dimension}, optimal={problem.optimal})")
    print("-" * 70)
    
    for strat_name in all_strat_names:
        if strat_name in p_res:
            data = p_res[strat_name]
            best_gap = data.get("best_gap", 0)
            avg_gap = data.get("avg_gap", 0)
            avg_time = data.get("avg_time_ms", 0)
            n_runs = data.get("n_runs", N_RUNS)
            
            print(f"  v {strat_name:<12} : {n_runs}/{N_RUNS} runs | "
                  f"Best GAP: {best_gap:>6.2f}% | Avg GAP: {avg_gap:>6.2f}% | "
                  f"Avg Time: {avg_time:>7.1f}ms")
        else:
            print(f"  x {strat_name:<12} : 0/{N_RUNS} runs | MISSING")
    
    print("-" * 70)

# ============================================================
# ALGORİTMA BİLGİLERİ
# ============================================================

ALGORITHM_INFO = {
    "2-opt": {
        "name": "2-opt",
        "type": "local_search",
        "description": "Klasik kenar degistirme algoritmasi (NUMBA)",
        "complexity": "O(n^2)",
        "best_for": "Orta buyuklukte problemler, hizli sonuc",
        "how_it_works": "Tur uzerindeki iki kenari kaldirir, yeni iki kenar ekleyerek turu iyilestirir",
        "iterations": 2000,
    },
    "3-opt": {
        "name": "3-opt",
        "type": "local_search",
        "description": "Uc kenar degistirme, yuksek kalite (NUMBA)",
        "complexity": "O(n^3)",
        "best_for": "Yuksek kalite cozum, zaman kritik degilse",
        "how_it_works": "Tur uzerindeki uc kenari kaldirir, 7 farkli yeniden baglantiyi dener",
        "iterations": 200,
    },
    "Or-opt": {
        "name": "Or-opt",
        "type": "local_search",
        "description": "Segment relocation (1-3 dugum tasima) (NUMBA)",
        "complexity": "O(n^2)",
        "best_for": "Kumelenmis dugumler, 2-opt sonrasi fine-tuning",
        "how_it_works": "1-3 dugumluk segmenti turun baska bir noktasina tasir",
        "iterations": 1000,
    },
    "Swap": {
        "name": "Swap",
        "type": "local_search",
        "description": "Iki dugum yer degistirme (NUMBA)",
        "complexity": "O(n^2)",
        "best_for": "Hizli fine-tuning, basit problemler",
        "how_it_works": "Tur uzerindeki iki dugumun yerini degistirir",
        "iterations": 5000,
    },
    "Hybrid": {
        "name": "Hybrid",
        "type": "local_search",
        "description": "Tum algoritmalarin kombinasyonu (NUMBA)",
        "complexity": "O(n^3)",
        "best_for": "En iyi kalite, orta/buyuk problemler",
        "how_it_works": "Sirayla 2-opt -> Or-opt -> 3-opt uygular",
        "iterations": 5,
    },
    "GA": {
        "name": "GA",
        "type": "meta_heuristic",
        "description": "Genetic Algorithm",
        "complexity": "O(pop x gen x n)",
        "best_for": "Global arama, farkli rota adaylari",
        "how_it_works": "Populasyon tabanli secilim, caprazlama ve mutasyon",
        "parameters": "pop_size=50, generations=100",
    },
    "PSO": {
        "name": "PSO",
        "type": "meta_heuristic",
        "description": "Particle Swarm Optimization",
        "complexity": "O(swarm x iter x n)",
        "best_for": "Hizli yakinlama ve denge",
        "how_it_works": "Parcaciklar pbest/gbest'e yonelerek permutasyon gunceller",
        "parameters": "swarm_size=30, iterations=100",
    },
    "GWO": {
        "name": "GWO",
        "type": "meta_heuristic",
        "description": "Grey Wolf Optimizer",
        "complexity": "O(pack x iter x n)",
        "best_for": "Kesif/somuru dengesi",
        "how_it_works": "Alpha/Beta/Delta rehberliginde rota iyilestirme",
        "parameters": "pack_size=30, iterations=100",
    },
    "HHO": {
        "name": "HHO",
        "type": "meta_heuristic",
        "description": "Harris Hawks Optimization",
        "complexity": "O(hawks x iter x n)",
        "best_for": "Saldiri-kacis tabanli adaptif arama",
        "how_it_works": "Enerji modeline gore yakinlasma ve rastgele ataklar",
        "parameters": "hawks=30, iterations=100",
    },
}

def show_algorithms_info():
    """Algoritma bilgileri ekranı"""
    clear_screen()
    print("=" * 70)
    print("          ALGORITMA KATALOGU (NUMBA OPTIMIZED)")
    print("=" * 70)
    
    print("\n[LOC] LOCAL SEARCH ALGORITMALARI:")
    print("-" * 70)
    print(f"{'Algoritma':<10} | {'Tur':<14} | {'Karmasiklik':<16} | {'Aciklama'}")
    print("-" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        if info.get("type") == "local_search":
            print(f"{key:<10} | {info.get('type', '-'):<14} | {info['complexity']:<16} | {info['description']}")

    print("\n[META] META-HEURISTIC ALGORITMALARI:")
    print("-" * 70)
    print(f"{'Algoritma':<10} | {'Tur':<14} | {'Karmasiklik':<16} | {'Aciklama'}")
    print("-" * 70)
    for key, info in ALGORITHM_INFO.items():
        if info.get("type") == "meta_heuristic":
            print(f"{key:<10} | {info.get('type', '-'):<14} | {info['complexity']:<16} | {info['description']}")
    
    print("\n" + "=" * 70)
    print("DETAYLI BILGI")
    print("=" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        print(f"\n[{info['name']}]")
        print(f"  [TYPE] Tur: {info.get('type', '-')}")
        print(f"  [INFO] Aciklama: {info['description']}")
        print(f"  [TIME] Karmasiklik: {info['complexity']}")
        print(f"  [TARGET] En Iyi Kullanim: {info['best_for']}")
        print(f"  [CONFIG] Calisma Sekli: {info['how_it_works']}")
        if "iterations" in info:
            print(f"  [NUM] Varsayilan Iterasyon: {info['iterations']}")
        if "parameters" in info:
            print(f"  [PARAM] Varsayilan Parametreler: {info['parameters']}")
    
    print("\n" + "-" * 70)
    print("[TIP] IPUCULAR:")
    print("-" * 70)
    print("  * NUMBA JIT: 10-50x hizlanma!")
    print("  * Kucuk problemler (n<=100): 2-opt veya Hybrid onerilir")
    print("  * Orta problemler (100<n<=500): Hybrid en iyi sonucu verir")
    print("  * Buyuk problemler (n>500): 2-opt hiz, Hybrid kalite icin")
    
    print("\n" + "-" * 70)
    print("[STATS] PERFORMANS BEKLENTISI (GAP %):")
    print("-" * 70)
    print("  * 2-opt: Genellikle %3-10 arasi")
    print("  * 3-opt: Genellikle %1-5 arasi")
    print("  * Or-opt: Genellikle %2-8 arasi")
    print("  * Swap: Genellikle %5-15 arasi")
    print("  * Hybrid: Genellikle %0.5-3 arasi (en iyi)")
    print("  * GA/PSO/GWO/HHO: Problem boyutuna gore genelde %1-6 arasi")
    
    input("\n\nDevam etmek icin Enter'a basin...")

def multi_select_problems(all_problems: List, saved_results: Dict = None, all_strat_names: List[str] = None) -> List:
    """Çoklu problem seçimi"""
    print("\n" + "=" * 70)
    print("PROBLEM SECIMI")
    print("=" * 70)
    print("Test etmek istediginiz problemleri secin.")
    print("Secim: numara (1,3,5-8), 'all', veya 'kucuk/orta/buyuk' alias'lari.")
    print("-" * 70)
    
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
    
    idx = 1
    problem_map = {}
    category_ranges = {'small': (0, 0), 'medium': (0, 0), 'large': (0, 0)}
    
    for cat_name, cat_label in [('small', 'KUCUK'), ('medium', 'ORTA'), ('large', 'BUYUK')]:
        problems = categories[cat_name]
        if not problems:
            continue
        problems.sort(key=lambda x: x.dimension)
        
        start_idx = idx
        print(f"\n[{cat_label} PROBLEMLER]")
        for p in problems:
            cache_status = ""
            if saved_results and all_strat_names:
                p_res = saved_results.get(p.name, {})
                tested = [s for s in all_strat_names if s in p_res]
                if len(tested) == len(all_strat_names):
                    cache_status = " v"
                elif tested:
                    cache_status = f" ({len(tested)}/{len(all_strat_names)})"
            
            print(f"  {idx:>2}. {p.name:<12} (n={p.dimension:<5}){cache_status}")
            problem_map[idx] = p
            idx += 1
        end_idx = idx - 1
        category_ranges[cat_name] = (start_idx, end_idx)
    
    print("\n" + "-" * 70)
    print("[TIP] Alias'lar: 'k' veya 'kucuk' = 1-{}, 'o' veya 'orta' = {}-{}, 'b' veya 'buyuk' = {}-{}"
          .format(category_ranges['small'][1], 
                  category_ranges['medium'][0], category_ranges['medium'][1],
                  category_ranges['large'][0], category_ranges['large'][1]))
    print("-" * 70)
    print("Seciminiz: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    
    if user_input in ['all', 'tum', 'tüm', 'hepsi']:
        return all_problems[:]
    elif user_input in ['k', 'kucuk', 'küçük', 'small']:
        start, end = category_ranges['small']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv KUCUK problemler secildi ({len(selected)} adet)")
        return selected
    elif user_input in ['o', 'orta', 'medium']:
        start, end = category_ranges['medium']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv ORTA problemler secildi ({len(selected)} adet)")
        return selected
    elif user_input in ['b', 'buyuk', 'büyük', 'large']:
        start, end = category_ranges['large']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv BUYUK problemler secildi ({len(selected)} adet)")
        return selected
    
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if i in problem_map:
                        selected.append(problem_map[i])
            else:
                i = int(part)
                if i in problem_map:
                    selected.append(problem_map[i])
    except (ValueError, KeyError):
        print("Gecersiz secim!")
        return []
    
    if not selected:
        print("Hicbir problem secilmedi!")
        return []
    
    seen = set()
    unique_selected = []
    for p in selected:
        if p.name not in seen:
            seen.add(p.name)
            unique_selected.append(p)
    
    print(f"\nv {len(unique_selected)} problem secildi: {', '.join([p.name for p in unique_selected])}")
    return unique_selected


def multi_select_algorithms(all_strat_names: List[str]) -> List[str]:
    """Çoklu algoritma seçimi"""
    print("\n" + "=" * 70)
    print("ALGORITMA SECIMI")
    print("=" * 70)
    print("Test etmek istediginiz algoritmalari secin.")
    print("Secim: numara (1,3,5), isim (GA,Hybrid), veya karisik (1,GA).")
    print("-" * 70)
    
    algo_map = {}
    for idx, name in enumerate(all_strat_names, 1):
        info = ALGORITHM_INFO.get(name, {})
        complexity = info.get('complexity', '?')
        algo_type = info.get('type', '?')
        print(f"  {idx:>2}. {name:<10} [{algo_type:<14}] [{complexity}]")
        algo_map[str(idx)] = name
        algo_map[name.lower()] = name
    
    print("\n" + "-" * 70)
    print("Alias: all | local | meta (sota alias'i da meta gibi davranir)")
    print("Seciminiz: ", end="")
    user_input = input().strip().lower()
    
    if user_input in {'all', 'tum', 'tüm'}:
        return all_strat_names[:]
    if user_input in {'local', 'ls'}:
        return [n for n in all_strat_names if get_algorithm_type(n, ALGORITHM_INFO.get(n, {})) == "local_search"]
    if user_input in {'meta', 'sota'}:
        return [n for n in all_strat_names if get_algorithm_type(n, ALGORITHM_INFO.get(n, {})) == "meta_heuristic"]
    
    selected = []
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    key = str(i)
                    if key in algo_map:
                        selected.append(algo_map[key])
            else:
                if part in algo_map:
                    selected.append(algo_map[part])
    except (ValueError, IndexError, KeyError):
        print("Gecersiz secim!")
        return []
    
    if not selected:
        print("Hicbir algoritma secilmedi!")
        return []
    
    seen = set()
    unique_selected = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            unique_selected.append(s)
    
    print(f"\nv {len(unique_selected)} algoritma secildi: {', '.join(unique_selected)}")
    return unique_selected


def interactive_detail_mode(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """İnteraktif detay modu"""
    problem_dict = {p.name: p for p in all_problems}
    
    while True:
        print("\n" + "-" * 70)
        print("Detay gormek icin problem adi girin (orn: berlin52, eil51)")
        print("Tum problemleri listelemek icin 'list' yazin")
        print("Cikmak icin 'q' veya Enter'a basin")
        print("-" * 70)
        
        user_input = input("> ").strip().lower()
        
        if not user_input or user_input == 'q':
            print("Detay modundan cikiliyor...")
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
            matches = [p.name for p in all_problems if user_input in p.name]
            if matches:
                print(f"'{user_input}' bulunamadi. Benzer problemler: {', '.join(matches[:5])}")
            else:
                print(f"'{user_input}' adli problem bulunamadi. 'list' yazarak tum problemleri gorebilirsiniz.")


def analyze_cached_tests(problems: List, algorithms: List[str], saved_results: Dict) -> Dict:
    """Cache analizini yap"""
    cached_tests = []
    new_tests = []
    
    for p in problems:
        p_res = saved_results.get(p.name, {})
        for alg in algorithms:
            if alg in p_res:
                cached_tests.append((p.name, alg, p_res[alg]))
            else:
                new_tests.append((p.name, alg))
    
    return {
        'cached': cached_tests,
        'new': new_tests,
        'total': len(problems) * len(algorithms),
        'cached_count': len(cached_tests),
        'new_count': len(new_tests)
    }


def show_test_summary(problems: List, algorithms: List[str], saved_results: Dict = None, skip_mode: str = 'ask') -> tuple:
    """Test öncesi özet göster ve onay al"""
    clear_screen()
    print("=" * 70)
    print("TEST OZETI (NUMBA OPTIMIZED)")
    print("=" * 70)
    
    total_tests = len(problems) * len(algorithms)
    
    cache_info = None
    if saved_results:
        cache_info = analyze_cached_tests(problems, algorithms, saved_results)
    
    print(f"\n[STATS] Test Yapilacak:")
    print(f"   * Problemler: {len(problems)}")
    print(f"   * Algoritmalar: {len(algorithms)} ({', '.join(algorithms)})")
    print(f"   * Her problem {N_RUNS} kez calistirilacak")
    print(f"   * Toplam test sayisi: {total_tests}")
    
    if NUMBA_AVAILABLE:
        print(f"\n[NUMBA] JIT Optimization: ENABLED (10-50x speedup)")
    else:
        print(f"\n[NUMBA] JIT Optimization: DISABLED (install numba for speedup)")
    
    skip_cached = False
    if cache_info and cache_info['cached_count'] > 0:
        print(f"\n[CACHE] ONBELLEK DURUMU:")
        print(f"   * Daha once yapilmis: {cache_info['cached_count']} test")
        print(f"   * Henuz yapilmamis: {cache_info['new_count']} test")
        print("-" * 70)
        
        if skip_mode == 'ask':
            print("\n[SEARCH] Onbellekteki testler icin ne yapmak istersiniz?")
            print("   [S] Atla - Sadece yeni testleri yap (onerilen)")
            print("   [R] Yenile - Tum testleri bastan yap")
            print("   [Q] Cikis")
            
            cache_choice = input("\nSeciminiz: ").strip().upper()
            
            if cache_choice == 'Q':
                return (False, False)
            elif cache_choice == 'S':
                skip_cached = True
                print(f"\nv {cache_info['new_count']} yeni test yapilacak")
            else:
                skip_cached = False
                print(f"\nv Tum {total_tests} test bastan yapilacak")
    
    effective_tests = cache_info['new_count'] if skip_cached else total_tests
    estimated_seconds = estimate_total_time(problems, algorithms)
    if skip_cached and cache_info:
        estimated_seconds = estimated_seconds * (cache_info['new_count'] / total_tests) if total_tests > 0 else 0
    print(f"\n[TIME] Tahmini Sure: ~{format_time(estimated_seconds)}")
    
    cat_counts = {}
    for p in problems:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
    print(f"\n[GRAPH] Kategori Dagilimi:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   * {cat}: {count} problem")
    
    print("\n[!] DIKKAT:")
    print("   * Ctrl+C ile istediginiz zaman guvenli cikis yapabilirsiniz")
    print("   * Sonuclar HER ALGORITMA sonrasi otomatik kaydedilir")
    
    print("\n[Y] Basla    [Q] Cikis    [D] Detaylari Gor")
    
    choice = input("\nSeciminiz: ").strip().upper()
    
    if choice == 'Q':
        return (False, skip_cached)
    elif choice == 'D':
        print("\n[LIST] Problemler:")
        for i, p in enumerate(problems, 1):
            print(f"   {i:>3}. {p.name:<15} (n={p.dimension:<5}, opt={p.optimal})")
        input("\nDevam etmek icin Enter'a basin...")
        return show_test_summary(problems, algorithms, saved_results, skip_mode)
    elif choice == 'Y':
        return (True, skip_cached)
    else:
        return show_test_summary(problems, algorithms, saved_results, skip_mode)


def save_incremental_result(result: Dict, metadata: Dict, problem_name: str, strat_name: str):
    """Her algoritma sonucunu anında kaydet"""
    saved_results = metadata.get("results", {})
    
    if problem_name not in saved_results:
        saved_results[problem_name] = {}
    
    saved_results[problem_name][strat_name] = {
        "avg_length": result["avg_length"],
        "avg_gap": result["avg_gap"],
        "best_gap": result["best_gap"],
        "avg_time_ms": result["avg_time_ms"],
        "n_runs": result.get("n_runs", 3),
        "algorithm_type": result.get("algorithm_type", get_algorithm_type(strat_name)),
        "timestamp": datetime.now().isoformat()
    }
    
    metadata["results"] = saved_results
    metadata["last_updated"] = datetime.now().isoformat()
    update_algorithm_hashes(metadata)
    save_metadata(METADATA_PATH, metadata)


# ============================================================
# MULTIPROCESSING WORKER
# ============================================================

def run_single_benchmark_task(args):
    """Worker function - tek bir test calistirir (multiprocessing icin)"""
    import sys
    import os
    import time
    
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "optimizer_api")))
    
    # NUMBA versiyonunu import et
    from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
        TSPLIBProblem, 
        run_single_test,
    )
    from optimizer_api.utils.local_search_numba import LocalSearchType
    
    # args: (problem_dict, strat_name, strategy_payload, strategy_params, task_id, n_runs)
    if len(args) == 6:
        problem_dict, strat_name, strategy_payload, strategy_params, task_id, n_runs = args
    else:
        # Backward compatibility
        problem_dict, strat_name, ls_type_value, max_iter, task_id = args
        strategy_payload = {"kind": "local_search", "value": ls_type_value}
        strategy_params = {"max_iterations": int(max_iter), "algorithm_type": "local_search"}
        n_runs = 3
    
    if not isinstance(strategy_params, dict):
        if isinstance(strategy_params, int):
            strategy_params = {"max_iterations": strategy_params, "algorithm_type": "local_search"}
        else:
            strategy_params = {"algorithm_type": get_algorithm_type(strat_name)}
    
    problem = TSPLIBProblem(
        name=problem_dict['name'],
        dimension=problem_dict['dimension'],
        optimal=problem_dict['optimal'],
        coordinates=problem_dict['coordinates'],
        category=problem_dict['category'],
        source=problem_dict.get('source', 'tsplib')
    )
    
    if isinstance(strategy_payload, dict):
        if strategy_payload.get("kind") == "local_search":
            strategy_instance = LocalSearchType(strategy_payload["value"])
        else:
            strategy_instance = strategy_payload.get("value")
    else:
        strategy_instance = LocalSearchType(strategy_payload)
    algorithm_type = strategy_params.get("algorithm_type", get_algorithm_type(strat_name))
    
    start_time = time.time()
    run_avg_results = []
    
    for run in range(n_runs):
        seed = (run + 1) * 42 + task_id
        result = run_single_test(problem, strategy_instance, seed, strategy_params)
        run_avg_results.append(result)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    avg_length = sum(r["tour_length"] for r in run_avg_results) / len(run_avg_results)
    avg_gap = sum(r["gap"] for r in run_avg_results) / len(run_avg_results)
    avg_time = sum(r["time_ms"] for r in run_avg_results) / len(run_avg_results)
    best_length = min(r["tour_length"] for r in run_avg_results)
    best_gap = min(r["gap"] for r in run_avg_results)
    
    return {
        "task_id": task_id,
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
        "elapsed_ms": elapsed_ms,
        "n_runs": n_runs,
        "algorithm_type": run_avg_results[0].get("algorithm_type", algorithm_type),
        "numba_optimized": True,
    }


def run_benchmark_sequential(tasks: List, metadata: Dict, skip_cached: bool, saved_results: Dict,
                              progress_callback=None) -> List[Dict]:
    """Benchmark'i sirayla calistir (anlik progress gosterimi icin)"""
    results = []
    completed = 0
    total = len(tasks)
    
    tasks_to_run = []
    for task in tasks:
        problem_dict = task[0]
        strat_name = task[1]
        problem_name = problem_dict['name']
        
        if skip_cached and problem_name in saved_results and strat_name in saved_results[problem_name]:
            old_data = saved_results[problem_name][strat_name]
            results.append({
                "task_id": task[4],
                "problem": problem_name,
                "dimension": problem_dict['dimension'],
                "category": problem_dict['category'],
                "optimal": problem_dict['optimal'],
                "strategy": strat_name,
                "avg_length": old_data["avg_length"],
                "avg_gap": old_data["avg_gap"],
                "best_length": old_data.get("avg_length", 0),
                "best_gap": old_data["best_gap"],
                "avg_time_ms": old_data["avg_time_ms"],
                "elapsed_ms": 0,
                "n_runs": old_data.get("n_runs", 3),
                "algorithm_type": old_data.get("algorithm_type", get_algorithm_type(strat_name)),
                "cached": True,
                "numba_optimized": True,
            })
            completed += 1
            if progress_callback:
                progress_callback(completed, total, 0, "running", results[-1])
        else:
            tasks_to_run.append(task)
    
    if progress_callback and tasks_to_run:
        progress_callback(completed, total, len(tasks_to_run), "starting")
    
    for task in tasks_to_run:
        result = run_single_benchmark_task(task)
        completed += 1
        results.append(result)
        
        save_incremental_result(result, metadata, result["problem"], result["strategy"])
        
        if progress_callback:
            progress_callback(completed, total, len(tasks_to_run) - (completed - len(tasks_to_run)), "running", result)
    
    return results


def run_benchmark_parallel(tasks: List, metadata: Dict, skip_cached: bool, saved_results: Dict, 
                           progress_callback=None) -> List[Dict]:
    """Benchmark'i paralel calistir"""
    results = []
    completed = 0
    total = len(tasks)
    
    tasks_to_run = []
    for task in tasks:
        # 6 elemanlı yeni tuple desteği
        problem_dict = task[0]
        strat_name = task[1]
        problem_name = problem_dict['name']
        
        if skip_cached and problem_name in saved_results and strat_name in saved_results[problem_name]:
            old_data = saved_results[problem_name][strat_name]
            results.append({
                "task_id": task[4],
                "problem": problem_name,
                "dimension": problem_dict['dimension'],
                "category": problem_dict['category'],
                "optimal": problem_dict['optimal'],
                "strategy": strat_name,
                "avg_length": old_data["avg_length"],
                "avg_gap": old_data["avg_gap"],
                "best_length": old_data.get("avg_length", 0),
                "best_gap": old_data["best_gap"],
                "avg_time_ms": old_data["avg_time_ms"],
                "elapsed_ms": 0,
                "n_runs": old_data.get("n_runs", 3),
                "algorithm_type": old_data.get("algorithm_type", get_algorithm_type(strat_name)),
                "cached": True,
                "numba_optimized": True,
            })
            completed += 1
        else:
            tasks_to_run.append(task)
    
    if progress_callback:
        progress_callback(completed, total, len(tasks_to_run), "starting")
    
    if tasks_to_run:
        with Pool(processes=NUM_WORKERS) as pool:
            for result in pool.imap_unordered(run_single_benchmark_task, tasks_to_run):
                completed += 1
                results.append(result)
                
                if 'cached' not in result:
                    save_incremental_result(result, metadata, result["problem"], result["strategy"])
                
                if progress_callback:
                    progress_callback(completed, total, len(tasks_to_run), "running", result)
    
    return results


def main():
    global _current_metadata, _current_results, _shutdown_requested
    
    metadata = get_latest_metadata(METADATA_PATH)
    algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
    
    all_problems = load_problems_smart()
    
    saved_results = metadata.get("results", {})
    all_strat_names = [s[0] for s in STRATEGIES]
    
    while True:
        _shutdown_requested = False
        clear_screen()
        print("=" * 70)
        print("          UNIRIDE SOTA BENCHMARK - NUMBA OPTIMIZED")
        print("=" * 70)
        
        print("\n[[SEARCH] ALGORITMA DURUMLARI]")
        any_changed = False
        for algo, status in algo_status.items():
            symbol = "[X]" if status == "DOSYA_YOK" else ("[!]" if status == "DEGISMIS" else ("[*]" if status == "YENI" else "[OK]"))
            print(f"  {symbol} {algo:<20} : {status}")
            if status in ["DEGISMIS", "YENI"]:
                any_changed = True
        
        print_compact_status(all_problems, saved_results, all_strat_names)
        
        print("\n=> NE YAPMAK ISTERSINIZ?")
        print("  [A] Zorunlu: Degisen/Yeni Kodlari Tum Cozumler Icin Bastan Test Et")
        print("  [B] Eksikleri Tamamla: Sadece Hic Test Edilmemis Problem/Stratejileri Coz")
        print("  [C] Hizli Mod: Sadece Kucuk Problemlerde Tum Algoritmalari Calistir")
        print("  [D] Kapsamli: Her Seyi (Tum Kod + Tum Problemler) Yeniden Test Et")
        print("  [E] Ozel Secim: Istediginiz Problemleri ve Algoritmalari Secin")
        print("  [S] Detay Modu: Bir Problem Icin Detayli Sonuclari Goruntule")
        print("  [H] Algoritma Bilgileri: Algoritmalar Hakkinda Detayli Bilgi")
        print("  [Q] Cikis")
        
        choice = input("\nSeciminiz: ").strip().upper()
        
        if choice == 'Q':
            print("Cikis yapiliyor...")
            break
        elif choice == 'S':
            interactive_detail_mode(all_problems, saved_results, all_strat_names)
            input("\nAna menuye donmek icin Enter'a basin...")
            continue
        elif choice == 'H':
            show_algorithms_info()
            continue
        
        problems_to_run = []
        strategies_to_run = []
        
        if choice == 'A':
            if not any_changed:
                print("Degisen bir kod yok. Onbelleginiz son kod durumunuzla birebir ayni!")
                input("Devam etmek icin Enter'a basin...")
                continue
            problems_to_run = all_problems
            strategies_to_run = all_strat_names
        elif choice == 'B':
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
        elif choice == 'E':
            problems_to_run = multi_select_problems(all_problems, saved_results, all_strat_names)
            if not problems_to_run:
                input("Devam etmek icin Enter'a basin...")
                continue
            strategies_to_run = multi_select_algorithms(all_strat_names)
            if not strategies_to_run:
                input("Devam etmek icin Enter'a basin...")
                continue
        else:
            print("Gecersiz secim.")
            input("Devam etmek icin Enter'a basin...")
            continue
            
        if not problems_to_run:
            print("Test edilecek problem bulunamadi (Her sey tamamlanmis).")
            input("Devam etmek icin Enter'a basin...")
            continue
        
        continue_test, skip_cached = show_test_summary(problems_to_run, strategies_to_run, saved_results)
        if not continue_test:
            print("Test iptal edildi.")
            input("Devam etmek icin Enter'a basin...")
            continue
        
        _current_metadata = metadata
        _current_results = []
        
        # Calistirma sayisi secimi
        global N_RUNS
        print(f"\n[RUNS] CALISTIRMA SAYISI SECIN:")
        print(f"   Varsayilan: {DEFAULT_N_RUNS}")
        print("   [3] 3 run (hizli test)")
        print("   [5] 5 run (standart)")
        print("   [10] 10 run (detayli)")
        print("   [Enter] Varsayilan kullan")
        runs_input = input("\nSeciminiz: ").strip()
        
        if runs_input == '':
            N_RUNS = DEFAULT_N_RUNS
        elif runs_input.isdigit() and int(runs_input) >= 1:
            N_RUNS = int(runs_input)
        else:
            N_RUNS = DEFAULT_N_RUNS
        
        print(f"   -> {N_RUNS} run secildi")
        
        # Worker sayisi secimi
        global NUM_WORKERS
        NUM_WORKERS = select_worker_count()
        print(f"\n[OK] {NUM_WORKERS} worker kullanilacak")
        
        total_tests = len(problems_to_run) * len(strategies_to_run)
        start_time = time.time()
        
        cache_info = analyze_cached_tests(problems_to_run, strategies_to_run, saved_results) if skip_cached else None
        new_tests_count = cache_info['new_count'] if cache_info else total_tests
        
        print(f"\n[START] TEST BASLIYOR (NUMBA OPTIMIZED)...")
        print(f"   [CONFIG] Paralel worker sayisi: {NUM_WORKERS}")
        print(f"   [CONFIG] Her problem {N_RUNS} kez calistirilacak")
        if skip_cached:
            print(f"   Toplam: {len(problems_to_run)} problem x {len(strategies_to_run)} algoritma")
            print(f"   Onbellekten atlanacak: {cache_info['cached_count']} test")
            print(f"   Yapilacak: {new_tests_count} yeni test")
        else:
            print(f"   Toplam: {len(problems_to_run)} problem x {len(strategies_to_run)} algoritma = {total_tests} test")
        print(f"   Tahmini sure: ~{format_time(estimate_total_time(problems_to_run, strategies_to_run))}")
        print()
        
        # Task listesi olustur
        tasks = []
        task_id = 0
        for problem in problems_to_run:
            problem_dict = {
                'name': problem.name,
                'dimension': problem.dimension,
                'optimal': problem.optimal,
                'coordinates': problem.coordinates,
                'category': problem.category,
                'source': problem.source,
            }
            
            for strategy_entry in STRATEGIES:
                strat_name, strategy_instance, strategy_params = normalize_strategy_entry(strategy_entry)
                if strat_name in strategies_to_run:
                    if hasattr(strategy_instance, "value"):
                        strategy_payload = {"kind": "local_search", "value": strategy_instance.value}
                    else:
                        strategy_payload = {"kind": "meta_heuristic", "value": str(strategy_instance)}
                    tasks.append((problem_dict, strat_name, strategy_payload, strategy_params, task_id, N_RUNS))
                    task_id += 1
        
        # Progress callback - her sonuc aninda gosterilir
        def progress_callback(completed, total, remaining, status, result=None):
            if status == "starting":
                print(f"[PROGRESS] {completed}/{total} cached, {remaining} to compute", flush=True)
            elif result:
                sym = "*" if result.get('best_gap', 100) <= 1 else ("+" if result.get('best_gap', 100) <= 5 else "o")
                cached = "[CACHED]" if result.get('cached') else ""
                print(f"  [{completed:>3}/{total}] {result['problem']:<12} {result['strategy']:<8} "
                      f"GAP: {result['best_gap']:>6.2f}% {sym} {result['avg_time_ms']:>7.0f}ms {cached}", flush=True)
        
        # Calistirma modu secimi
        print("\n[MODE] CALISTIRMA MODU SECIN:")
        print("   [S] Sirali (Sequential) - Anlik progress gosterimi (onerilen)")
        print("   [P] Paralel - Daha hizli ama toplu sonuc")
        mode_choice = input("\nSeciminiz [S/P]: ").strip().upper()
        use_sequential = mode_choice != 'P'
        
        if use_sequential:
            print("\n[MODE] Sirali mod secildi - her sonuc aninda gorunecek")
        else:
            print(f"\n[MODE] Paralel mod secildi - {NUM_WORKERS} worker")
        
        # Run benchmark
        if use_sequential:
            results = run_benchmark_sequential(tasks, metadata, skip_cached, saved_results, progress_callback)
        else:
            results = run_benchmark_parallel(tasks, metadata, skip_cached, saved_results, progress_callback)
        
        # Save final results
        _current_results = results
        
        elapsed = time.time() - start_time
        print(f"\n[OK] Benchmark tamamlandi! Sure: {format_time(elapsed)}")
        
        # Show summary
        if results:
            print_summary_table(results)
            
            # Save final
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(HISTORY_DIR, f"final_numba_{timestamp}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            print(f"\n[SAVED] Final results: {csv_path}")
        
        input("\nAna menuye donmek icin Enter'a basin...")


if __name__ == "__main__":
    main()
