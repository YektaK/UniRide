#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive TSPLIB Benchmark Runner with Real Coordinates - NUMBA OPTIMIZED VERSION

This is the Numba-optimized version of run_interactive_benchmark_v2.py.
Uses JIT-compiled local search algorithms for 10-50x speedup.

Requirements:
    - numba package: pip install numba
    - numpy package: pip install numpy

Kullanım:
    cd /home/z/my-project/DOURide
    python optimizer_api/tests/run_interactive_benchmark_v2_numba.py
    
VEYA:
    python academic_benchmark/run_smart_benchmark_numba.py
"""

import sys
import os
import json
import csv
import time
import math
import random
import re
from datetime import datetime
from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass, asdict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# NUMBA OPTIMIZED local_search import
from utils.local_search_numba import (
    LocalSearchType,
    apply_local_search,
    NUMBA_AVAILABLE,
)


# ============================================================
# Configuration
# ============================================================

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "benchmark_results_numba")
TSPLIB_DIR = os.path.join(os.path.dirname(__file__), "tsplib_data")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TSPLIB_DIR, exist_ok=True)

# TSPLIB download URL
TSPLIB_BASE_URL = "https://raw.githubusercontent.com/mastqe/tsplib/master/"

# Number of runs per problem
N_RUNS = 3

# Strategies to test (same as original)
STRATEGIES = [
    ("2-opt", LocalSearchType.TWO_OPT, 1000),
    ("3-opt", LocalSearchType.THREE_OPT, 500),
    ("Or-opt", LocalSearchType.OR_OPT, 500),
    ("Swap", LocalSearchType.SWAP, 1000),
    ("Hybrid", LocalSearchType.HYBRID, 100),
]


# ============================================================
# TSPLIB Problem Definition
# ============================================================

@dataclass
class TSPLIBProblem:
    """TSPLIB problem definition"""
    name: str
    dimension: int
    optimal: int
    coordinates: List[Tuple[float, float]]
    category: str  # small, medium, large
    source: str = "tsplib"


# ============================================================
# TSPLIB File Parser and Downloader
# ============================================================

def download_tsplib_file(problem_name: str) -> Optional[str]:
    """Download TSPLIB .tsp file from online repository."""
    filename = f"{problem_name}.tsp"
    filepath = os.path.join(TSPLIB_DIR, filename)
    
    if os.path.exists(filepath):
        print(f"    [CACHE] {filename} already exists")
        return filepath
    
    url = TSPLIB_BASE_URL + filename
    print(f"    [DOWNLOAD] {url}")
    
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"    [SAVED] {filepath}")
        return filepath
    
    except (URLError, HTTPError) as e:
        print(f"    [ERROR] Failed to download {filename}: {e}")
        return None


def parse_tsplib_file(filepath: str) -> Optional[Dict]:
    """Parse TSPLIB .tsp file and extract problem data."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        name_match = re.search(r'NAME\s*:\s*(\S+)', content, re.IGNORECASE)
        dim_match = re.search(r'DIMENSION\s*:\s*(\d+)', content, re.IGNORECASE)
        type_match = re.search(r'TYPE\s*:\s*(\S+)', content, re.IGNORECASE)
        
        if not dim_match:
            print(f"    [ERROR] Cannot find DIMENSION in {filepath}")
            return None
        
        name = name_match.group(1) if name_match else os.path.basename(filepath)
        dimension = int(dim_match.group(1))
        problem_type = type_match.group(1) if type_match else "TSP"
        
        coordinates = []
        
        coord_section_match = re.search(
            r'NODE_COORD_SECTION\s*\n(.*?)\n?(?:EOF|DISPLAY_DATA_SECTION)',
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if coord_section_match:
            coord_lines = coord_section_match.group(1).strip().split('\n')
            
            for line in coord_lines:
                line = line.strip()
                if not line or line.upper().startswith('EOF'):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        coordinates.append((x, y))
                    except ValueError:
                        continue
        
        if len(coordinates) != dimension:
            print(f"    [WARNING] Coordinate count ({len(coordinates)}) != DIMENSION ({dimension})")
        
        return {
            'name': name.lower(),
            'dimension': dimension,
            'coordinates': coordinates,
            'type': problem_type
        }
    
    except Exception as e:
        print(f"    [ERROR] Failed to parse {filepath}: {e}")
        return None


def load_tsplib_problem(problem_name: str, optimal: int, category: str) -> Optional[TSPLIBProblem]:
    """Load TSPLIB problem - download if necessary and parse."""
    filepath = download_tsplib_file(problem_name)
    
    if not filepath:
        return None
    
    data = parse_tsplib_file(filepath)
    
    if not data:
        return None
    
    return TSPLIBProblem(
        name=data['name'],
        dimension=data['dimension'],
        optimal=optimal,
        coordinates=data['coordinates'],
        category=category,
        source="tsplib"
    )


# ============================================================
# Known TSPLIB Optimal Solutions
# ============================================================

TSPLIB_PROBLEMS = {
    "small": [
        ("berlin52", 7542),
        ("eil51", 426),
        ("eil76", 538),
        ("st70", 675),
        ("kroA100", 21282),
        ("kroB100", 22141),
        ("kroC100", 20749),
        ("kroD100", 21294),
        ("kroE100", 22068),
        ("rd100", 7910),
        ("eil101", 629),
        ("lin105", 14379),
        ("pr107", 44303),
        ("pr124", 59030),
        ("pr136", 96772),
        ("pr144", 58537),
        ("pr152", 73682),
    ],
    "medium": [
        ("kroA150", 26524),
        ("kroB150", 26130),
        ("kroA200", 29368),
        ("kroB200", 29437),
        ("pr226", 80369),
        ("pr264", 49135),
        ("pr299", 48191),
        ("ts225", 126843),
        ("gil262", 2412),
        ("pr439", 107217),
        ("a280", 2579),
        ("lin318", 42029),
        ("rd400", 15281),
    ],
    "large": [
        ("d493", 35002),
        ("u724", 41910),
        ("rat783", 8806),
        ("pr1002", 259045),
        ("u1060", 224094),
        ("vm1084", 239297),
        ("pcb1173", 56892),
        ("nrw1379", 56638),
        ("u1432", 152970),
        ("d1655", 62128),
        ("vm1748", 336556),
        ("u1817", 57201),
        ("d2103", 80450),
        ("u2152", 64253),
        ("u2319", 234256),
        ("pr2392", 378032),
    ],
}


# ============================================================
# Distance Functions
# ============================================================

def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def tsplib_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB EUC_2D distance (rounded)"""
    return int(round(euclidean_distance(p1, p2)))


def calculate_tour_length(tour: List[int], coordinates: List[Tuple[float, float]]) -> int:
    """Calculate total tour length using TSPLIB EUC_2D distance."""
    if not tour or not coordinates:
        return 0
    
    n_coords = len(coordinates)
    total = 0
    
    def safe_get_coord(idx: int):
        real_idx = idx - 1 if idx > 0 else idx
        if 0 <= real_idx < n_coords:
            return coordinates[real_idx]
        return None
    
    for i in range(len(tour) - 1):
        p1 = safe_get_coord(tour[i])
        p2 = safe_get_coord(tour[i + 1])
        
        if p1 is None or p2 is None:
            continue
            
        total += tsplib_distance(p1, p2)
    
    p1 = safe_get_coord(tour[-1])
    p2 = safe_get_coord(tour[0])
    
    if p1 is not None and p2 is not None:
        total += tsplib_distance(p1, p2)
    
    return total


def create_distance_matrix(coordinates: List[Tuple[float, float]]) -> Dict[str, Dict[str, float]]:
    """Create distance matrix from coordinates"""
    n = len(coordinates)
    matrix = {}
    
    for i in range(n):
        key_i = f"L{i+1}"
        matrix[key_i] = {}
        for j in range(n):
            key_j = f"L{j+1}"
            if i == j:
                matrix[key_i][key_j] = 0.0
            else:
                matrix[key_i][key_j] = float(tsplib_distance(coordinates[i], coordinates[j]))
    
    return matrix


def create_duration_func(matrix: Dict[str, Dict[str, float]]) -> Callable[[List[str]], float]:
    """Create duration function"""
    def duration_func(route: List[str]) -> float:
        if not route:
            return 0.0
        total = 0.0
        prev = route[0]
        for loc in route[1:]:
            total += matrix.get(prev, {}).get(loc, 0.0)
            prev = loc
        total += matrix.get(prev, {}).get(route[0], 0.0)
        return total
    return duration_func


def convert_route_to_indices(route: List[str]) -> List[int]:
    """Convert string route to integer indices"""
    return [int(loc[1:]) for loc in route]


# ============================================================
# Benchmark Functions
# ============================================================

def run_single_test(
    problem: TSPLIBProblem,
    ls_type: LocalSearchType,
    seed: int,
    max_iterations: int = 500
) -> Dict:
    """Run single test with specific seed - NUMBA OPTIMIZED"""
    coordinates = problem.coordinates
    dimension = problem.dimension
    
    # Create distance matrix
    matrix = create_distance_matrix(coordinates)
    duration_func = create_duration_func(matrix)
    
    # Create initial tour with random permutation
    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    
    initial_route = [f"L{i}" for i in indices]
    
    # Apply local search (NUMBA OPTIMIZED)
    start_time = time.time()
    improved_route, _ = apply_local_search(
        initial_route, duration_func, ls_type, max_iterations=max_iterations
    )
    elapsed = time.time() - start_time
    
    # Calculate tour length
    tour_indices = convert_route_to_indices(improved_route)
    tour_length = calculate_tour_length(tour_indices, coordinates)
    
    gap = ((tour_length - problem.optimal) / problem.optimal) * 100
    
    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
    }


def run_benchmark_for_problem(
    problem: TSPLIBProblem,
    n_runs: int = 3,
    verbose: bool = True
) -> List[Dict]:
    """Run benchmark for a single problem with all strategies"""
    results = []
    
    for strat_name, ls_type, max_iter in STRATEGIES:
        if verbose:
            print(f"    Testing {strat_name}...", end=" ", flush=True)
        
        run_results = []
        for run in range(n_runs):
            seed = (run + 1) * 42
            result = run_single_test(problem, ls_type, seed, max_iter)
            run_results.append(result)
        
        # Calculate averages
        avg_length = sum(r["tour_length"] for r in run_results) / len(run_results)
        avg_gap = sum(r["gap"] for r in run_results) / len(run_results)
        avg_time = sum(r["time_ms"] for r in run_results) / len(run_results)
        
        best_length = min(r["tour_length"] for r in run_results)
        best_gap = min(r["gap"] for r in run_results)
        
        result = {
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
            "n_runs": n_runs,
            "timestamp": datetime.now().isoformat(),
            "numba_optimized": True,
        }
        results.append(result)
        
        if verbose:
            status = "*" if best_gap <= 1 else ("+" if best_gap <= 5 else ("o" if best_gap <= 10 else "x"))
            print(f"avg_gap: {avg_gap:.2f}%, best_gap: {best_gap:.2f}% {status} [{avg_time:.0f}ms]")
    
    return results


def save_results(results: List[Dict], prefix: str = ""):
    """Save results to JSON and CSV files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_file = os.path.join(OUTPUT_DIR, f"{prefix}benchmark_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"    JSON saved: {json_file}")
    
    csv_file = os.path.join(OUTPUT_DIR, f"{prefix}benchmark_{timestamp}.csv")
    if results:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"    CSV saved: {csv_file}")
    
    return json_file, csv_file


def print_summary_table(results: List[Dict]):
    """Print summary table"""
    print("\n" + "="*100)
    print("OZET TABLO (NUMBA OPTIMIZED)")
    print("="*100)
    
    problems = {}
    for r in results:
        prob = r["problem"]
        if prob not in problems:
            problems[prob] = r
    
    print(f"\n{'Problem':<15} | {'Dim':<6} | {'Optimal':<10} | {'Best Strategy':<15} | {'Best Gap':<10} | {'Avg Gap':<10}")
    print("-" * 90)
    
    for prob_name in sorted(problems.keys(), key=lambda x: problems[x]['dimension']):
        r = problems[prob_name]
        prob_results = [x for x in results if x["problem"] == prob_name]
        best = min(prob_results, key=lambda x: x["best_gap"])
        
        status = "*" if best["best_gap"] <= 1 else ("+" if best["best_gap"] <= 5 else ("o" if best["best_gap"] <= 10 else "x"))
        
        print(f"{r['problem']:<15} | {r['dimension']:<6} | {r['optimal']:<10} | {best['strategy']:<15} | {best['best_gap']:>8.2f}% | {best['avg_gap']:>8.2f}% {status}")
    
    print("\n" + "-"*90)
    print("STRATEJI PERFORMANSLARI")
    print("-"*90)
    
    strategy_stats = {}
    for r in results:
        strat = r["strategy"]
        if strat not in strategy_stats:
            strategy_stats[strat] = {"gaps": [], "times": []}
        strategy_stats[strat]["gaps"].append(r["avg_gap"])
        strategy_stats[strat]["times"].append(r["avg_time_ms"])
    
    print(f"\n{'Strategy':<15} | {'Avg Gap':<12} | {'Min Gap':<12} | {'Max Gap':<12} | {'Avg Time (ms)':<15}")
    print("-" * 75)
    
    for strat, stats in sorted(strategy_stats.items(), key=lambda x: sum(x[1]["gaps"])/len(x[1]["gaps"])):
        avg = sum(stats["gaps"]) / len(stats["gaps"])
        min_gap = min(stats["gaps"])
        max_gap = max(stats["gaps"])
        avg_time = sum(stats["times"]) / len(stats["times"])
        print(f"{strat:<15} | {avg:>10.2f}% | {min_gap:>10.2f}% | {max_gap:>10.2f}% | {avg_time:>13.1f}")


def ask_continue() -> bool:
    """Ask user if they want to continue"""
    while True:
        response = input("\nDevam etmek istiyor musunuz? (e/h/q): ").strip().lower()
        if response in ['e', 'evet', 'y', 'yes']:
            return True
        elif response in ['h', 'hayir', 'n', 'no', 'q', 'quit', 'exit']:
            return False
        print("Lutfen 'e' (evet) veya 'h' (hayir) girin.")


def load_all_problems(category: str) -> List[TSPLIBProblem]:
    """Load all problems for a category"""
    problems = []
    
    if category not in TSPLIB_PROBLEMS:
        print(f"[ERROR] Unknown category: {category}")
        return problems
    
    print(f"\n[{category.upper()}] Problemler yukleniyor...")
    
    for problem_name, optimal in TSPLIB_PROBLEMS[category]:
        problem = load_tsplib_problem(problem_name, optimal, category)
        if problem:
            problems.append(problem)
            print(f"    + {problem.name} (n={problem.dimension}, optimal={problem.optimal})")
        else:
            print(f"    - {problem_name} could not be loaded")
    
    return problems


# ============================================================
# Main Interactive Runner
# ============================================================

def run_interactive_benchmark():
    """Run interactive benchmark - NUMBA OPTIMIZED"""
    print("\n" + "="*100)
    print("INTERAKTIF TSPLIB BENCHMARK - NUMBA OPTIMIZED")
    print("="*100)
    
    # Check Numba availability
    if NUMBA_AVAILABLE:
        print("[OK] Numba JIT compiled - 10-50x faster!")
    else:
        print("[WARNING] Numba not available - using pure Python (install: pip install numba)")
    
    total_problems = sum(len(probs) for probs in TSPLIB_PROBLEMS.values())
    print(f"\nToplam Problem: {total_problems}")
    print(f"  - Kucuk (n <= 100): {len(TSPLIB_PROBLEMS['small'])} problem")
    print(f"  - Orta (100 < n <= 500): {len(TSPLIB_PROBLEMS['medium'])} problem")
    print(f"  - Buyuk (500 < n <= 2000): {len(TSPLIB_PROBLEMS['large'])} problem")
    print(f"\nHer problem {N_RUNS} kez test edilecek.")
    print(f"Stratejiler: {', '.join([s[0] for s in STRATEGIES])}")
    print(f"Sonuclar: {OUTPUT_DIR}")
    print(f"TSPLIB verileri: {TSPLIB_DIR}")
    
    all_results = []
    
    print("\n" + "-"*50)
    print("Hangi kategoriden baslamak istiyorsunuz?")
    print("  1. Kucuk (hizli)")
    print("  2. Orta")
    print("  3. Buyuk")
    print("  4. Tumu")
    print("  q. Cikis")
    
    choice = input("\nSeciminiz (1-4/q): ").strip().lower()
    
    if choice == 'q':
        print("Cikis yapiliyor...")
        return
    
    if choice == '1':
        categories_to_run = ['small']
    elif choice == '2':
        categories_to_run = ['medium']
    elif choice == '3':
        categories_to_run = ['large']
    elif choice == '4':
        categories_to_run = ['small', 'medium', 'large']
    else:
        print("Gecersiz secim. Kucuk kategori ile baslaniyor...")
        categories_to_run = ['small']
    
    problems_to_run = []
    for cat in categories_to_run:
        problems_to_run.extend(load_all_problems(cat))
    
    if not problems_to_run:
        print("\n[ERROR] Hicbir problem yuklenemedi!")
        return
    
    print(f"\n{len(problems_to_run)} problem calistirilacak.")
    
    for i, problem in enumerate(problems_to_run, 1):
        print("\n" + "="*100)
        print(f"[{i}/{len(problems_to_run)}] {problem.name.upper()} (n={problem.dimension}, optimal={problem.optimal})")
        print(f"Kategori: {problem.category.upper()}, Kaynak: {problem.source}")
        print("="*100)
        
        results = run_benchmark_for_problem(problem, N_RUNS)
        all_results.extend(results)
        
        save_results(all_results, prefix=f"progress_")
        
        if i < len(problems_to_run):
            if not ask_continue():
                print("\nBenchmark durduruldu.")
                break
    
    if all_results:
        print_summary_table(all_results)
        
        print("\n" + "-"*50)
        print("FINAL SONUCLARI KAYDEDILIYOR...")
        save_results(all_results, prefix="final_")
        
        print("\n" + "="*100)
        print("BENCHMARK TAMAMLANDI (NUMBA OPTIMIZED)")
        print("="*100)


if __name__ == "__main__":
    run_interactive_benchmark()
