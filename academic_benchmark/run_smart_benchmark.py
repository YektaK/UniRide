#!/usr/bin/env python3
"""
UniRide Smart Benchmark - Gelişmiş Versiyon

Özellikler:
- Ctrl+C ile güvenli çıkış (sonuçlar kaybolmaz)
- Her algoritma sonucunda anında kayıt
- Tahmini süre hesaplaması
- Progress gösterimi
- Çoklu problem/algoritma seçimi
"""
import sys
import os
import json
import signal
import time
import csv
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

# ============================================================
# GLOBAL DEĞİŞKENLER - Graceful Shutdown için
# ============================================================
_shutdown_requested = False
_current_metadata = None
_current_results = []

def signal_handler(signum, frame):
    """Ctrl+C ile güvenli çıkış - sonuçları kaydeder"""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n⚠️  DURDURMA İSTEĞİ ALINDI!")
    print("📝 Mevcut sonuçlar kaydediliyor, lütfen bekleyin...")
    
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
        print(f"✅ {len(_current_results)} sonuç kaydedildi: {csv_path}")
    
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

def estimate_total_time(problems: List, algorithms: List[str]) -> float:
    """Tahmini toplam süre hesapla (saniye)"""
    # Ortalama süre tahminleri (saniye) - problem boyutuna göre
    # Bu değerler empirik olarak belirlenmiştir
    base_times = {
        'small': 0.5,    # Küçük problemler hızlı
        'medium': 2.0,   # Orta problemler
        'large': 10.0,   # Büyük problemler yavaş
    }
    
    # Algoritma çarpanları
    algo_multipliers = {
        '2-opt': 1.0,
        '3-opt': 3.0,
        'Or-opt': 1.5,
        'Swap': 1.0,
        'Hybrid': 5.0,
    }
    
    total_time = 0
    for p in problems:
        base = base_times.get(p.category, 2.0)
        for alg in algorithms:
            mult = algo_multipliers.get(alg, 2.0)
            total_time += base * mult * N_RUNS
    
    return total_time

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
    print("═" * 70)
    print("          ALGORİTMA KATALOĞU")
    print("═" * 70)
    
    print("\n📍 LOCAL SEARCH ALGORİTMALARI:")
    print("─" * 70)
    print(f"{'Algoritma':<10} | {'Karmaşıklık':<10} | {'Açıklama'}")
    print("─" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        print(f"{key:<10} | {info['complexity']:<10} | {info['description']}")
    
    print("\n" + "═" * 70)
    print("DETAYLI BİLGİ")
    print("═" * 70)
    
    for key, info in ALGORITHM_INFO.items():
        print(f"\n[{info['name']}]")
        print(f"  📖 Açıklama: {info['description']}")
        print(f"  ⏱️ Karmaşıklık: {info['complexity']}")
        print(f"  🎯 En İyi Kullanım: {info['best_for']}")
        print(f"  🔧 Çalışma Şekli: {info['how_it_works']}")
        print(f"  🔢 Varsayılan İterasyon: {info['iterations']}")
    
    print("\n" + "─" * 70)
    print("💡 İPUCULAR:")
    print("─" * 70)
    print("  • Küçük problemler (n≤100): 2-opt veya Hybrid önerilir")
    print("  • Orta problemler (100<n≤500): Hybrid en iyi sonucu verir")
    print("  • Büyük problemler (n>500): 2-opt hız, Hybrid kalite için")
    print("  • 3-opt tek başına yavaş ama çok kaliteli sonuç verir")
    print("  • Swap basit ama nadiren en iyi seçimdir")
    
    print("\n" + "─" * 70)
    print("📊 PERFORMANS BEKLENTİSİ (GAP %):")
    print("─" * 70)
    print("  • 2-opt: Genellikle %3-10 arası")
    print("  • 3-opt: Genellikle %1-5 arası")
    print("  • Or-opt: Genellikle %2-8 arası")
    print("  • Swap: Genellikle %5-15 arası")
    print("  • Hybrid: Genellikle %0.5-3 arası (en iyi)")
    
    input("\n\nDevam etmek için Enter'a basın...")

def multi_select_problems(all_problems: List) -> List:
    """Çoklu problem seçimi"""
    print("\n" + "═" * 70)
    print("PROBLEM SEÇİMİ")
    print("═" * 70)
    print("Test etmek istediğiniz problemleri seçin.")
    print("Birden fazla seçim için virgülle ayırın (örn: 1,3,5-8) veya 'all' tümü için.")
    print("─" * 70)
    
    # Kategorilere göre grupla
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
    
    # Numaralandırılmış liste oluştur
    idx = 1
    problem_map = {}
    
    for cat_name, cat_label in [('small', 'KÜÇÜK'), ('medium', 'ORTA'), ('large', 'BÜYÜK')]:
        problems = categories[cat_name]
        if not problems:
            continue
        problems.sort(key=lambda x: x.dimension)
        
        print(f"\n[{cat_label} PROBLEMLER]")
        for p in problems:
            print(f"  {idx:>2}. {p.name:<12} (n={p.dimension:<5})")
            problem_map[idx] = p
            idx += 1
    
    print("\n─" * 70)
    print("Seçiminiz: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    
    if user_input == 'all' or user_input == 'tum' or user_input == 'tüm':
        return all_problems[:]
    
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
    
    print(f"\n✓ {len(unique_selected)} problem seçildi: {', '.join([p.name for p in unique_selected])}")
    return unique_selected


def multi_select_algorithms(all_strat_names: List[str]) -> List[str]:
    """Çoklu algoritma seçimi"""
    print("\n" + "═" * 70)
    print("ALGORİTMA SEÇİMİ")
    print("═" * 70)
    print("Test etmek istediğiniz algoritmaları seçin.")
    print("Birden fazla seçim için virgülle ayırın (örn: 1,3,5) veya 'all' tümü için.")
    print("─" * 70)
    
    for idx, name in enumerate(all_strat_names, 1):
        print(f"  {idx:>2}. {name}")
    
    print("\n─" * 70)
    print("Seçiminiz: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    
    if user_input == 'all' or user_input == 'tum' or user_input == 'tüm':
        return all_strat_names[:]
    
    # Parse selection
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
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
    
    print(f"\n✓ {len(unique_selected)} algoritma seçildi: {', '.join(unique_selected)}")
    return unique_selected


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


def show_test_summary(problems: List, algorithms: List[str]) -> bool:
    """Test öncesi özet göster ve onay al"""
    clear_screen()
    print("═" * 70)
    print("TEST ÖZETİ")
    print("═" * 70)
    
    total_tests = len(problems) * len(algorithms)
    
    print(f"\n📊 Test Yapılacak:")
    print(f"   • Problemler: {len(problems)}")
    print(f"   • Algoritmalar: {len(algorithms)} ({', '.join(algorithms)})")
    print(f"   • Her problem {N_RUNS} kez çalıştırılacak")
    print(f"   • Toplam test sayısı: {total_tests}")
    
    # Tahmini süre
    estimated_seconds = estimate_total_time(problems, algorithms)
    print(f"\n⏱️ Tahmini Süre: ~{format_time(estimated_seconds)}")
    
    # Kategori dağılımı
    cat_counts = {}
    for p in problems:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
    print(f"\n📈 Kategori Dağılımı:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   • {cat}: {count} problem")
    
    print("\n⚠️ DİKKAT:")
    print("   • Ctrl+C ile istediğiniz zaman güvenli çıkış yapabilirsiniz")
    print("   • Sonuçlar HER ALGORİTMA sonrası otomatik kaydedilir")
    print("   • Mevcut sonuçlarınız kaybolmaz!")
    
    print("\n[Y] Başla    [Q] Çıkış    [D] Detayları Gör")
    
    choice = input("\nSeçiminiz: ").strip().upper()
    
    if choice == 'Q':
        return False
    elif choice == 'D':
        print("\n📋 Problemler:")
        for i, p in enumerate(problems, 1):
            print(f"   {i:>3}. {p.name:<15} (n={p.dimension:<5}, opt={p.optimal})")
        input("\nDevam etmek için Enter'a basın...")
        return show_test_summary(problems, algorithms)  # Recursive
    elif choice == 'Y':
        return True
    else:
        return show_test_summary(problems, algorithms)


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
            problems_to_run = multi_select_problems(all_problems)
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
        
        # Test öncesi özet göster
        if not show_test_summary(problems_to_run, strategies_to_run):
            print("Test iptal edildi.")
            input("Devam etmek için Enter'a basın...")
            continue
        
        # Global değişkenleri ayarla (Ctrl+C için)
        _current_metadata = metadata
        _current_results = []
        
        total_tests = len(problems_to_run) * len(strategies_to_run)
        completed_tests = 0
        start_time = time.time()
        
        print(f"\n🚀 TEST BAŞLIYOR...")
        print(f"   Toplam: {len(problems_to_run)} problem × {len(strategies_to_run)} algoritma = {total_tests} test")
        print(f"   Tahmini süre: ~{format_time(estimate_total_time(problems_to_run, strategies_to_run))}")
        print()
        
        for prob_idx, problem in enumerate(problems_to_run, 1):
            if _shutdown_requested:
                break
                
            print(f"\n{'═'*70}")
            print(f"[{prob_idx}/{len(problems_to_run)}] {problem.name.upper()} (n={problem.dimension}, opt={problem.optimal})")
            print(f"{'═'*70}")
            
            p_res = saved_results.get(problem.name, {})
            
            for strat_idx, (strat_name, ls_type, max_iter) in enumerate(STRATEGIES):
                if _shutdown_requested:
                    break
                    
                if strat_name not in strategies_to_run:
                    continue
                    
                completed_tests += 1
                
                # Progress göster
                elapsed = time.time() - start_time
                if completed_tests > 1:
                    avg_time_per_test = elapsed / (completed_tests - 1)
                    remaining = (total_tests - completed_tests + 1) * avg_time_per_test
                    progress_str = f" | Kalan: ~{format_time(remaining)}"
                else:
                    progress_str = ""
                
                print(f"  [{completed_tests}/{total_tests}] {strat_name:<10} ", end="", flush=True)
                    
                # B Modu: Önbellekte varsa oynamaya gerek yok
                if choice == 'B' and strat_name in p_res:
                    print(f"[ÖNBELLEK] ✓")
                    
                    # Eski değeri flat listeye yansıt ki tablo kopuk çıkmasın
                    old_data = p_res[strat_name]
                    _current_results.append({
                        "problem": problem.name,
                        "dimension": problem.dimension,
                        "category": problem.category,
                        "optimal": problem.optimal,
                        "strategy": strat_name,
                        "avg_length": old_data["avg_length"],
                        "avg_gap": old_data["avg_gap"],
                        "best_length": old_data.get("avg_length", 0),
                        "best_gap": old_data["best_gap"],
                        "avg_time_ms": old_data["avg_time_ms"],
                        "n_runs": N_RUNS,
                    })
                    continue
                
                print(f"çalışıyor...{progress_str}", end="", flush=True)
                
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
                
                # Sonucu yazdır
                status = "★" if best_gap <= 1 else ("✓" if best_gap <= 5 else ("○" if best_gap <= 10 else "✗"))
                print(f"\r  [{completed_tests}/{total_tests}] {strat_name:<10} GAP: {avg_gap:>6.2f}% (best: {best_gap:>6.2f}%) {status}")
                
                # Sonucu oluştur
                result_entry = {
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
                }
                
                # ANINDA KAYDET - Her algoritma sonucunda
                save_incremental_result(result_entry, metadata, problem.name, strat_name)
                _current_results.append(result_entry)
                
                # saved_results'ı güncelle
                p_res[strat_name] = {
                    "avg_length": avg_length,
                    "avg_gap": avg_gap,
                    "best_gap": best_gap,
                    "avg_time_ms": avg_time,
                    "timestamp": datetime.now().isoformat()
                }
                
            saved_results[problem.name] = p_res
            
            if _shutdown_requested:
                break
        
        if _shutdown_requested:
            print("\n⚠️ Test kullanıcı tarafından durduruldu.")
            input("Ana menüye dönmek için Enter'a basın...")
            metadata = get_latest_metadata(METADATA_PATH)
            algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
            saved_results = metadata.get("results", {})
            continue
        
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
            print(f"\n✅ Tüm sonuçlar başarıyla 'latest_metadata.json'a işlendi.")
            print(f"📦 Excel/Log yedeği: {csv_path}")
            print(f"⏱️ Toplam süre: {format_time(total_elapsed)}")
            
        input("\nAna menüye dönmek için Enter'a basın...")
        metadata = get_latest_metadata(METADATA_PATH)
        algo_status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
        saved_results = metadata.get("results", {})
        
if __name__ == "__main__":
    main()
