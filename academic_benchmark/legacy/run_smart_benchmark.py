#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark - Gelişmiş Versiyon

Özellikler:
- Ctrl+C ile güvenli çıkış (sonuçlar kaybolmaz)
- Her algoritma sonucunda anında kayıt
- Gerçek süre ölçümü ve dinamik tahmin
- Multiprocessing ile paralel çalıştırma
- Progress gösterimi
- Çoklu problem/algoritma seçimi
"""
import sys
import os
import io

# Windows encoding fix — reconfigure() avoids Python 3.14 GC crash
if sys.platform == 'win32' or 'pypy' in sys.implementation.name.lower():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import signal
import time
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from multiprocessing import Pool, cpu_count, Manager
import threading

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

# ============================================================
# GLOBAL DEĞİŞKENLER - Graceful Shutdown için
# ============================================================
_shutdown_requested = False
_current_metadata = None
_current_results = []

# Multiprocessing için
NUM_WORKERS = min(cpu_count(), 4)  # Max 4 worker

def signal_handler(signum, frame):
    """Ctrl+C ile güvenli çıkış - sonuçları kaydeder"""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!]  DURDURMA İSTEĞİ ALINDI!")
    print("[NOTE] Mevcut sonuçlar kaydediliyor, lütfen bekleyin...")
    
    if _current_metadata and _current_results:
        # Metadata kaydet
        save_metadata(METADATA_PATH, _current_metadata)
        
        # CSV yedek
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(HISTORY_DIR, f"interrupted_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_current_results[0].keys())
            writer.writeheader()
            writer.writerows(_current_results)
        print(f"[OK] {len(_current_results)} sonuç kaydedildi: {csv_path}")
    
    print("👋 Güvenli çıkış yapıldı.")
    sys.exit(0)

# Signal handler'ı kaydet
signal.signal(signal.SIGINT, signal_handler)

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

# ============================================================
# SÜRE ÖLÇÜM VE TAHMİN SİSTEMİ
# ============================================================

class DynamicTimeEstimator:
    """Gerçek ölçümlere dayalı dinamik süre tahmini"""
    
    def __init__(self):
        self.measurements = []  # [(dimension, category, algorithm, time_ms), ...]
        self.category_avg = {'small': [], 'medium': [], 'large': []}
        self.algo_avg = {}
    
    def add_measurement(self, dimension: int, category: str, algorithm: str, time_ms: float):
        """Yeni ölçüm ekle"""
        self.measurements.append((dimension, category, algorithm, time_ms))
        self.category_avg[category].append(time_ms)
        
        if algorithm not in self.algo_avg:
            self.algo_avg[algorithm] = []
        self.algo_avg[algorithm].append(time_ms)
    
    def estimate_time(self, dimension: int, category: str, algorithm: str) -> Optional[float]:
        """Tek bir test için süre tahmini (ms)"""
        # Önce aynı algoritma + benzer boyut için ölçüm var mı?
        similar = [(d, t) for d, c, a, t in self.measurements 
                   if a == algorithm and abs(d - dimension) < dimension * 0.3]
        
        if similar:
            # Benzer boyutlardan ortalama
            return sum(t for _, t in similar) / len(similar)
        
        # Algoritma ortalaması var mı?
        if algorithm in self.algo_avg and self.algo_avg[algorithm]:
            algo_time = sum(self.algo_avg[algorithm]) / len(self.algo_avg[algorithm])
            # Boyut çarpanı
            size_factor = dimension / 100  # 100 = referans boyut
            return algo_time * size_factor
        
        # Kategori ortalaması var mı?
        if category in self.category_avg and self.category_avg[category]:
            return sum(self.category_avg[category]) / len(self.category_avg[category])
        
        return None  # Ölçüm yok
    
    def estimate_remaining(self, pending_tests: List[Tuple], num_workers: int = NUM_WORKERS) -> float:
        """Kalan testler için tahmini süre (saniye)"""
        total_ms = 0
        unknown_count = 0
        
        for dimension, category, algorithm in pending_tests:
            est = self.estimate_time(dimension, category, algorithm)
            if est:
                total_ms += est
            else:
                unknown_count += 1
                # Varsayılan değerler (ölçüm yoksa)
                defaults = {'small': 2000, 'medium': 8000, 'large': 30000}
                total_ms += defaults.get(category, 5000)
        
        # Paralel çalıştırma avantajı
        total_ms = total_ms / num_workers
        
        # N_RUNS çarpanı
        total_ms *= N_RUNS
        
        return total_ms / 1000  # saniyeye çevir


def estimate_total_time(problems: List, algorithms: List[str], num_workers: int = NUM_WORKERS) -> float:
    """Tahmini toplam süre hesapla (saniye) - gerçekçi değerler"""
    # Gerçek ölçümlere dayalı daha gerçekçi tahminler (ms cinsinden)
    # Bu değerler gerçek testlerden alınmıştır
    base_times = {
        'small': 2000,    # ~2sn (gerçek)
        'medium': 8000,   # ~8sn (gerçek)
        'large': 30000,   # ~30sn (gerçek)
    }
    
    # Algoritma çarpanları (gerçek ölçümlere göre)
    algo_multipliers = {
        '2-opt': 1.0,
        '3-opt': 3.5,
        'Or-opt': 1.5,
        'Swap': 0.8,
        'Hybrid': 6.0,
    }
    
    total_ms = 0
    for p in problems:
        base = base_times.get(p.category, 5000)
        for alg in algorithms:
            mult = algo_multipliers.get(alg, 2.0)
            total_ms += base * mult
    
    # N_RUNS çarpanı
    total_ms *= N_RUNS
    
    # Paralel çalıştırma avantajı
    total_ms = total_ms / num_workers
    
    return total_ms / 1000  # saniyeye çevir

def make_progress_bar(completed: int, total: int, width: int = 10) -> str:
    """Progress bar oluştur"""
    filled = int((completed / total) * width) if total > 0 else 0
    empty = width - filled
    return "#" * filled + "." * empty

def print_compact_status(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """Compact status görünümü - her problem için bir satır"""
    total_algos = len(all_strat_names)
    
    print("\n" + "=" * 80)
    print("BENCHMARK STATUS OVERVIEW")
    print("=" * 80)
    
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
        print("-" * 80)
        
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
                status = "v COMPLETE"
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
    print("\n" + "-" * 80)
    pct = (total_completed / total_tests * 100) if total_tests > 0 else 0
    print(f"ÖZET: {len(all_problems)} problem | {total_completed}/{total_tests} tamamlandı ({pct:.1f}%)")
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
            
            # Run count (metadata'da yoksa N_RUNS varsay)
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
        "description": "Klasik kenar değiştirme algoritması",
        "complexity": "O(n²)",
        "best_for": "Orta büyüklükte problemler, hızlı sonuç",
        "how_it_works": "Tur üzerindeki iki kenarı kaldırır, yeni iki kenar ekleyerek turu iyileştirir",
        "iterations": 1000,
    },
    "3-opt": {
        "name": "3-opt",
        "description": "Üç kenar değiştirme, yüksek kalite",
        "complexity": "O(n³)",
        "best_for": "Yüksek kalite çözüm, zaman kritik değilse",
        "how_it_works": "Tur üzerindeki üç kenarı kaldırır, 7 farklı yeniden bağlantıyı dener",
        "iterations": 500,
    },
    "Or-opt": {
        "name": "Or-opt",
        "description": "Segment relocation (1-3 düğüm taşıma)",
        "complexity": "O(n²)",
        "best_for": "Kümelenmiş düğümler, 2-opt sonrası fine-tuning",
        "how_it_works": "1-3 düğümlük segmenti turun başka bir noktasına taşır",
        "iterations": 500,
    },
    "Swap": {
        "name": "Swap",
        "description": "İki düğüm yer değiştirme",
        "complexity": "O(n²)",
        "best_for": "Hızlı fine-tuning, basit problemler",
        "how_it_works": "Tur üzerindeki iki düğümün yerini değiştirir",
        "iterations": 1000,
    },
    "Hybrid": {
        "name": "Hybrid",
        "description": "Tüm algoritmaların kombinasyonu",
        "complexity": "O(n³)",
        "best_for": "En iyi kalite, orta/büyük problemler",
        "how_it_works": "Sırayla 2-opt → Or-opt → 3-opt uygular",
        "iterations": 100,
    },
}

def show_algorithms_info():
    """Algoritma bilgileri ekranı"""
    clear_screen()
    print("=" * 70)
    print("          ALGORİTMA KATALOĞU")
    print("=" * 70)
    
    print("\n[LOC] LOCAL SEARCH ALGORİTMALARI:")
    print("-" * 70)
    print(f"{'Algoritma':<10} | {'Karmaşıklık':<10} | {'Açıklama'}")
    print("-" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        print(f"{key:<10} | {info['complexity']:<10} | {info['description']}")
    
    print("\n" + "=" * 70)
    print("DETAYLI BİLGİ")
    print("=" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        print(f"\n[{info['name']}]")
        print(f"  [INFO] Açıklama: {info['description']}")
        print(f"  [TIME] Karmaşıklık: {info['complexity']}")
        print(f"  [TARGET] En İyi Kullanım: {info['best_for']}")
        print(f"  [CONFIG] Çalışma Şekli: {info['how_it_works']}")
        print(f"  [NUM] Varsayılan İterasyon: {info['iterations']}")
    
    print("\n" + "-" * 70)
    print("[TIP] İPUCULAR:")
    print("-" * 70)
    print("  • Küçük problemler (n≤100): 2-opt veya Hybrid önerilir")
    print("  • Orta problemler (100<n≤500): Hybrid en iyi sonucu verir")
    print("  • Büyük problemler (n>500): 2-opt hız, Hybrid kalite için")
    print("  • 3-opt tek başına yavaş ama çok kaliteli sonuç verir")
    print("  • Swap basit ama nadiren en iyi seçimdir")
    
    print("\n" + "-" * 70)
    print("[STATS] PERFORMANS BEKLENTİSİ (GAP %):")
    print("-" * 70)
    print("  • 2-opt: Genellikle %3-10 arası")
    print("  • 3-opt: Genellikle %1-5 arası")
    print("  • Or-opt: Genellikle %2-8 arası")
    print("  • Swap: Genellikle %5-15 arası")
    print("  • Hybrid: Genellikle %0.5-3 arası (en iyi)")
    
    input("\n\nDevam etmek için Enter'a basın...")

def multi_select_problems(all_problems: List, saved_results: Dict = None, all_strat_names: List[str] = None) -> List:
    """Çoklu problem seçimi - alias ve cache desteği ile"""
    print("\n" + "=" * 70)
    print("PROBLEM SEÇİMİ")
    print("=" * 70)
    print("Test etmek istediğiniz problemleri seçin.")
    print("Seçim: numara (1,3,5-8), 'all', veya 'küçük/orta/büyük' alias'ları.")
    print("-" * 70)
    
    # Kategorilere göre grupla
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
    
    # Numaralandırılmış liste oluştur
    idx = 1
    problem_map = {}
    
    # Kategori range'lerini takip et
    category_ranges = {'small': (0, 0), 'medium': (0, 0), 'large': (0, 0)}
    
    for cat_name, cat_label in [('small', 'KÜÇÜK'), ('medium', 'ORTA'), ('large', 'BÜYÜK')]:
        problems = categories[cat_name]
        if not problems:
            continue
        problems.sort(key=lambda x: x.dimension)
        
        start_idx = idx
        print(f"\n[{cat_label} PROBLEMLER]")
        for p in problems:
            # Cache durumunu göster
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
    print("[TIP] Alias'lar: 'k' veya 'küçük' = 1-{}, 'o' veya 'orta' = {}-{}, 'b' veya 'büyük' = {}-{}"
          .format(category_ranges['small'][1], 
                  category_ranges['medium'][0], category_ranges['medium'][1],
                  category_ranges['large'][0], category_ranges['large'][1]))
    print("-" * 70)
    print("Seçiminiz: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    
    # Alias kontrolü
    if user_input in ['all', 'tum', 'tüm', 'hepsi']:
        return all_problems[:]
    elif user_input in ['k', 'kucuk', 'küçük', 'kucuk', 'small']:
        start, end = category_ranges['small']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv KÜÇÜK problemler seçildi ({len(selected)} adet)")
        return selected
    elif user_input in ['o', 'orta', 'medium']:
        start, end = category_ranges['medium']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv ORTA problemler seçildi ({len(selected)} adet)")
        return selected
    elif user_input in ['b', 'buyuk', 'büyük', 'large']:
        start, end = category_ranges['large']
        for i in range(start, end + 1):
            selected.append(problem_map[i])
        print(f"\nv BÜYÜK problemler seçildi ({len(selected)} adet)")
        return selected
    
    # Parse selection (support: 1,3,5-8,10)
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                # Range selection (e.g., 5-8)
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if i in problem_map:
                        selected.append(problem_map[i])
            else:
                # Single selection
                i = int(part)
                if i in problem_map:
                    selected.append(problem_map[i])
    except (ValueError, KeyError):
        print("Geçersiz seçim!")
        return []
    
    if not selected:
        print("Hiçbir problem seçilmedi!")
        return []
    
    # Remove duplicates while preserving order
    seen = set()
    unique_selected = []
    for p in selected:
        if p.name not in seen:
            seen.add(p.name)
            unique_selected.append(p)
    
    print(f"\nv {len(unique_selected)} problem seçildi: {', '.join([p.name for p in unique_selected])}")
    return unique_selected


def multi_select_algorithms(all_strat_names: List[str]) -> List[str]:
    """Çoklu algoritma seçimi"""
    print("\n" + "=" * 70)
    print("ALGORİTMA SEÇİMİ")
    print("=" * 70)
    print("Test etmek istediğiniz algoritmaları seçin.")
    print("Seçim: numara (1,3,5) veya 'all' tümü için.")
    print("-" * 70)
    
    for idx, name in enumerate(all_strat_names, 1):
        info = ALGORITHM_INFO.get(name, {})
        complexity = info.get('complexity', '?')
        print(f"  {idx:>2}. {name:<10} [{complexity}]")
    
    print("\n" + "-" * 70)
    print("Seçiminiz: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    
    if user_input == 'all' or user_input == 'tum' or user_input == 'tüm':
        return all_strat_names[:]
    
    # Parse selection
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if 1 <= i <= len(all_strat_names):
                        selected.append(all_strat_names[i - 1])
            else:
                i = int(part)
                if 1 <= i <= len(all_strat_names):
                    selected.append(all_strat_names[i - 1])
    except (ValueError, IndexError):
        print("Geçersiz seçim!")
        return []
    
    if not selected:
        print("Hiçbir algoritma seçilmedi!")
        return []
    
    # Remove duplicates while preserving order
    seen = set()
    unique_selected = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            unique_selected.append(s)
    
    print(f"\nv {len(unique_selected)} algoritma seçildi: {', '.join(unique_selected)}")
    return unique_selected


def interactive_detail_mode(all_problems: List, saved_results: Dict, all_strat_names: List[str]):
    """İnteraktif detay modu"""
    # Problem lookup dict
    problem_dict = {p.name: p for p in all_problems}
    
    while True:
        print("\n" + "-" * 70)
        print("Detay görmek için problem adı girin (örn: berlin52, eil51)")
        print("Tüm problemleri listelemek için 'list' yazın")
        print("Çıkmak için 'q' veya Enter'a basın")
        print("-" * 70)
        
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


def analyze_cached_tests(problems: List, algorithms: List[str], saved_results: Dict) -> Dict:
    """Cache analizini yap - hangi testler daha önce yapılmış"""
    cached_tests = []  # Daha önce yapılmış testler
    new_tests = []     # Henüz yapılmamış testler
    
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
    """Test öncesi özet göster ve onay al - cache durumu ile
    
    Returns:
        tuple: (continue: bool, skip_cached: bool)
    """
    clear_screen()
    print("=" * 70)
    print("TEST ÖZETİ")
    print("=" * 70)
    
    total_tests = len(problems) * len(algorithms)
    
    # Cache analizi
    cache_info = None
    if saved_results:
        cache_info = analyze_cached_tests(problems, algorithms, saved_results)
    
    print(f"\n[STATS] Test Yapılacak:")
    print(f"   • Problemler: {len(problems)}")
    print(f"   • Algoritmalar: {len(algorithms)} ({', '.join(algorithms)})")
    print(f"   • Her problem {N_RUNS} kez çalıştırılacak")
    print(f"   • Toplam test sayısı: {total_tests}")
    
    # Cache durumu göster
    skip_cached = False
    if cache_info and cache_info['cached_count'] > 0:
        print(f"\n[CACHE] ÖNBELLEK DURUMU:")
        print(f"   • Daha önce yapılmış: {cache_info['cached_count']} test")
        print(f"   • Henüz yapılmamış: {cache_info['new_count']} test")
        print("-" * 70)
        
        if skip_mode == 'ask':
            print("\n[SEARCH] Önbellekteki testler için ne yapmak istersiniz?")
            print("   [S] Atla - Sadece yeni testleri yap (önerilen)")
            print("   [R] Yenile - Tüm testleri baştan yap")
            print("   [A] Arttır - Mevcut sonuçlara yeni koşumlar ekle")
            print("   [Q] Çıkış")
            
            cache_choice = input("\nSeçiminiz: ").strip().upper()
            
            if cache_choice == 'Q':
                return (False, False)
            elif cache_choice == 'S':
                skip_cached = True
                print(f"\nv {cache_info['new_count']} yeni test yapılacak")
            elif cache_choice == 'A':
                # Mevcut sonuçlara ekleme yapılacak
                skip_cached = False
                print(f"\nv Tüm testler yapılacak, mevcut sonuçlar genişletilecek")
            else:  # R veya default
                skip_cached = False
                print(f"\nv Tüm {total_tests} test baştan yapılacak")
    
    # Tahmini süre
    effective_tests = cache_info['new_count'] if skip_cached else total_tests
    estimated_seconds = estimate_total_time(problems, algorithms)
    if skip_cached and cache_info:
        # Sadece yeni testler için süre tahmini
        estimated_seconds = estimated_seconds * (cache_info['new_count'] / total_tests) if total_tests > 0 else 0
    print(f"\n[TIME] Tahmini Süre: ~{format_time(estimated_seconds)}")
    
    # Kategori dağılımı
    cat_counts = {}
    for p in problems:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
    print(f"\n[GRAPH] Kategori Dağılımı:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   • {cat}: {count} problem")
    
    print("\n[!] DİKKAT:")
    print("   • Ctrl+C ile istediğiniz zaman güvenli çıkış yapabilirsiniz")
    print("   • Sonuçlar HER ALGORİTMA sonrası otomatik kaydedilir")
    print("   • Mevcut sonuçlarınız kaybolmaz!")
    
    print("\n[Y] Başla    [Q] Çıkış    [D] Detayları Gör")
    
    choice = input("\nSeçiminiz: ").strip().upper()
    
    if choice == 'Q':
        return (False, skip_cached)
    elif choice == 'D':
        print("\n[LIST] Problemler:")
        for i, p in enumerate(problems, 1):
            cache_mark = ""
            if cache_info:
                p_cached = len([t for t in cache_info['cached'] if t[0] == p.name])
                if p_cached == len(algorithms):
                    cache_mark = " [TAMAM]"
                elif p_cached > 0:
                    cache_mark = f" [{p_cached}/{len(algorithms)}]"
            print(f"   {i:>3}. {p.name:<15} (n={p.dimension:<5}, opt={p.optimal}){cache_mark}")
        input("\nDevam etmek için Enter'a basın...")
        return show_test_summary(problems, algorithms, saved_results, skip_mode)  # Recursive
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
        "timestamp": datetime.now().isoformat()
    }
    
    metadata["results"] = saved_results
    save_metadata(METADATA_PATH, metadata)


# ============================================================
# MULTIPROCESSING WORKER
# ============================================================

def run_single_benchmark_task(args):
    """
    Worker function - tek bir test çalıştırır (multiprocessing için)
    
    Args:
        args: (problem_dict, strat_name, ls_type_value, max_iter, task_id)
    
    Returns:
        dict: Sonuç veya None (cache'den atlandıysa)
    """
    # Worker process'te gerekli tüm import'ları YENİDEN yap
    import sys
    import os
    import time
    
    # Proje yollarını ekle
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "optimizer_api")))
    
    # Şimdi import'ları yap
    from optimizer_api.tests.run_interactive_benchmark_v2 import (
        TSPLIBProblem, 
        run_single_test,
        N_RUNS
    )
    from optimizer_api.utils.local_search import LocalSearchType
    
    # Args'ı unpack et
    problem_dict, strat_name, ls_type_value, max_iter, task_id = args
    
    # Problem dict'ini geri oluştur
    problem = TSPLIBProblem(
        name=problem_dict['name'],
        dimension=problem_dict['dimension'],
        optimal=problem_dict['optimal'],
        coordinates=problem_dict['coordinates'],
        category=problem_dict['category'],
        source=problem_dict.get('source', 'tsplib')
    )
    
    # LocalSearchType'ı string'den al
    ls_type = LocalSearchType(ls_type_value)
    
    # Testi çalıştır
    start_time = time.time()
    run_avg_results = []
    
    for run in range(N_RUNS):
        seed = (run + 1) * 42 + task_id  # Her task için farklı seed
        result = run_single_test(problem, ls_type, seed, max_iter)
        run_avg_results.append(result)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    # İstatistikleri hesapla
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
        "n_runs": N_RUNS,
    }


def run_benchmark_parallel(tasks: List, metadata: Dict, skip_cached: bool, saved_results: Dict, 
                           progress_callback=None) -> List[Dict]:
    """
    Benchmark'ı paralel çalıştır
    
    Args:
        tasks: [(problem_dict, strat_name, ls_type_value, max_iter, task_id), ...]
        metadata: Metadata dict
        skip_cached: Cache'deki testleri atla
        saved_results: Mevcut sonuçlar
        progress_callback: İlerleme callback'i
    
    Returns:
        List[Dict]: Sonuçlar
    """
    results = []
    completed = 0
    total = len(tasks)
    
    # Cache'den atlanacak task'ları belirle
    tasks_to_run = []
    for task in tasks:
        problem_dict, strat_name, _, _, _ = task
        problem_name = problem_dict['name']
        
        if skip_cached and problem_name in saved_results and strat_name in saved_results[problem_name]:
            # Cache'den al
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
                "n_runs": N_RUNS,
                "cached": True,
            })
            completed += 1
        else:
            tasks_to_run.append(task)
    
    if progress_callback:
        progress_callback(completed, total, len(tasks_to_run), "starting")
    
    # Paralel çalıştır
    if tasks_to_run:
        with Pool(processes=NUM_WORKERS) as pool:
            for result in pool.imap_unordered(run_single_benchmark_task, tasks_to_run):
                completed += 1
                results.append(result)
                
                # Incremental save
                if 'cached' not in result:
                    save_incremental_result(result, metadata, result["problem"], result["strategy"])
                
                if progress_callback:
                    progress_callback(completed, total, len(tasks_to_run), "running", result)
    
    return results


def main():
    global _current_metadata, _current_results, _shutdown_requested
    
    metadata = get_latest_metadata(METADATA_PATH)
    algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
    
    # Problemleri yükle
    all_problems = load_problems_smart()
    
    saved_results = metadata.get("results", {})
    all_strat_names = [s[0] for s in STRATEGIES]
    
    while True:
        _shutdown_requested = False
        clear_screen()
        print("=" * 70)
        print("          UNIRIDE SOTA BENCHMARK KONTROL MERKEZİ")
        print("=" * 70)
        
        print("\n[[SEARCH] ALGORİTMA DURUMLARI]")
        any_changed = False
        for algo, status in algo_status.items():
            symbol = "[X]" if status == "DOSYA_YOK" else ("[!]" if status == "DEGISMIS" else ("[*]" if status == "YENI" else "[OK]"))
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
        print("  [E] Özel Seçim: İstediğiniz Problemleri ve Algoritmaları Seçin")
        print("  [S] Detay Modu: Bir Problem İçin Detaylı Sonuçları Görüntüle")
        print("  [H] Algoritma Bilgileri: Algoritmalar Hakkında Detaylı Bilgi")
        print("  [Q] Çıkış")
        
        choice = input("\nSeçiminiz: ").strip().upper()
        
        if choice == 'Q':
            print("Çıkış yapılıyor...")
            break
        elif choice == 'S':
            interactive_detail_mode(all_problems, saved_results, all_strat_names)
            input("\nAna menüye dönmek için Enter'a basın...")
            continue
        elif choice == 'H':
            show_algorithms_info()
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
        elif choice == 'E':
            # Özel seçim modu
            problems_to_run = multi_select_problems(all_problems, saved_results, all_strat_names)
            if not problems_to_run:
                input("Devam etmek için Enter'a basın...")
                continue
            strategies_to_run = multi_select_algorithms(all_strat_names)
            if not strategies_to_run:
                input("Devam etmek için Enter'a basın...")
                continue
        else:
            print("Geçersiz seçim.")
            input("Devam etmek için Enter'a basın...")
            continue
            
        if not problems_to_run:
            print("Test edilecek problem bulunamadı (Her şey tamamlanmış).")
            input("Devam etmek için Enter'a basın...")
            continue
        
        # Test öncesi özet göster - skip_cached desteği ile
        continue_test, skip_cached = show_test_summary(problems_to_run, strategies_to_run, saved_results)
        if not continue_test:
            print("Test iptal edildi.")
            input("Devam etmek için Enter'a basın...")
            continue
        
        # Global değişkenleri ayarla (Ctrl+C için)
        _current_metadata = metadata
        _current_results = []
        
        total_tests = len(problems_to_run) * len(strategies_to_run)
        start_time = time.time()
        
        # Cache info for skip_cached mode
        cache_info = analyze_cached_tests(problems_to_run, strategies_to_run, saved_results) if skip_cached else None
        new_tests_count = cache_info['new_count'] if cache_info else total_tests
        
        print(f"\n[START] TEST BAŞLIYOR...")
        print(f"   [CONFIG] Paralel worker sayısı: {NUM_WORKERS}")
        if skip_cached:
            print(f"   Toplam: {len(problems_to_run)} problem × {len(strategies_to_run)} algoritma")
            print(f"   Önbellekten atlanacak: {cache_info['cached_count']} test")
            print(f"   Yapılacak: {new_tests_count} yeni test")
        else:
            print(f"   Toplam: {len(problems_to_run)} problem × {len(strategies_to_run)} algoritma = {total_tests} test")
        print(f"   Tahmini süre: ~{format_time(estimate_total_time(problems_to_run, strategies_to_run))}")
        print()
        
        # Task listesi oluştur (multiprocessing için)
        tasks = []
        task_id = 0
        for problem in problems_to_run:
            for strat_name, ls_type, max_iter in STRATEGIES:
                if strat_name not in strategies_to_run:
                    continue
                
                # Problem dict'e çevir (pickle için)
                problem_dict = {
                    'name': problem.name,
                    'dimension': problem.dimension,
                    'optimal': problem.optimal,
                    'coordinates': problem.coordinates,
                    'category': problem.category,
                    'source': getattr(problem, 'source', 'tsplib')
                }
                
                tasks.append((problem_dict, strat_name, ls_type.value, max_iter, task_id))
                task_id += 1
        
        # Dinamik süre ölçümü
        time_estimator = DynamicTimeEstimator()
        completed_count = [0]  # Liste kullanıyoruz çünkü closure'da değiştirilebilir olmalı
        results_lock = threading.Lock()
        
        def progress_callback(completed, total, remaining_new, status, result=None):
            """İlerleme callback'i"""
            with results_lock:
                completed_count[0] = completed
                
                if result and 'cached' not in result:
                    # Ölçüm ekle
                    time_estimator.add_measurement(
                        result['dimension'], 
                        result['category'], 
                        result['strategy'],
                        result['elapsed_ms']
                    )
                
                # Progress göster
                elapsed = time.time() - start_time
                
                if status == "starting":
                    print(f"\n⏳ {remaining_new} test paralel çalıştırılacak ({NUM_WORKERS} worker)...\n")
                elif result:
                    # Sonuç yazdır
                    if 'cached' in result:
                        print(f"  [{completed}/{total}] {result['problem']:<12} + {result['strategy']:<8} [ÖNBELLEK] v")
                    else:
                        gap = result['avg_gap']
                        best_gap = result['best_gap']
                        status_icon = "*" if best_gap <= 1 else ("v" if best_gap <= 5 else ("o" if best_gap <= 10 else "x"))
                        elapsed_s = result['elapsed_ms'] / 1000
                        
                        # Kalan süre tahmini
                        remaining_tests = total - completed
                        if completed > 0:
                            avg_time = elapsed / completed
                            remaining_time = avg_time * remaining_tests
                            remaining_str = f" | Kalan: ~{format_time(remaining_time)}"
                        else:
                            remaining_str = ""
                        
                        print(f"  [{completed}/{total}] {result['problem']:<12} + {result['strategy']:<8} "
                              f"GAP: {gap:>6.2f}% (best: {best_gap:>5.2f}%) {status_icon} "
                              f"[{elapsed_s:.1f}sn]{remaining_str}")
        
        # Paralel çalıştır
        try:
            all_results = run_benchmark_parallel(
                tasks, metadata, skip_cached, saved_results, progress_callback
            )
        except KeyboardInterrupt:
            print("\n\n[!] Test durduruldu, sonuçlar kaydedildi...")
            all_results = _current_results
        
        # Sonuçları işle
        _current_results = all_results
        
        # saved_results'ı güncelle
        for result in all_results:
            if 'cached' not in result:
                problem_name = result['problem']
                strat_name = result['strategy']
                
                if problem_name not in saved_results:
                    saved_results[problem_name] = {}
                
                saved_results[problem_name][strat_name] = {
                    "avg_length": result["avg_length"],
                    "avg_gap": result["avg_gap"],
                    "best_gap": result["best_gap"],
                    "avg_time_ms": result["avg_time_ms"],
                    "timestamp": datetime.now().isoformat()
                }
        
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
        
        if _current_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(HISTORY_DIR, f"smart_run_{timestamp}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=_current_results[0].keys())
                writer.writeheader()
                writer.writerows(_current_results)
            
            print_summary_table(_current_results)
            
            total_elapsed = time.time() - start_time
            print(f"\n[OK] Tüm sonuçlar başarıyla 'latest_metadata.json'a işlendi.")
            print(f"[CACHE] Excel/Log yedeği: {csv_path}")
            print(f"[TIME] Toplam süre: {format_time(total_elapsed)}")
            
        input("\nAna menüye dönmek için Enter'a basın...")
        metadata = get_latest_metadata(METADATA_PATH)
        algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
        saved_results = metadata.get("results", {})
        
if __name__ == "__main__":
    main()
