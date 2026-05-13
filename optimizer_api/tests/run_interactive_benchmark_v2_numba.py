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
from typing import List, Dict, Tuple, Callable, Optional, Any, Union
from dataclasses import dataclass, asdict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# NUMBA OPTIMIZED local_search import - use consistent absolute paths
from optimizer_api.utils.local_search_numba import (
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

# Benchmark profile: quality-first is the default for paper-grade runs.
# Set BENCHMARK_PROFILE=baseline to compare against the more conservative setup.
BENCHMARK_PROFILE = os.environ.get("BENCHMARK_PROFILE", "quality_first").strip().lower()
VALID_BENCHMARK_PROFILES = {"baseline", "quality_first", "bildiri_aligned"}

# ============================================================
# STRATEGIES - Local Search + Meta-Heuristic
# ============================================================
LOCAL_SEARCH_STRATEGIES = [
    ("2-opt", LocalSearchType.TWO_OPT, {"max_iterations": 3000, "algorithm_type": "local_search"}),
    ("3-opt", LocalSearchType.THREE_OPT, {"max_iterations": 400, "algorithm_type": "local_search"}),
    ("Or-opt", LocalSearchType.OR_OPT, {"max_iterations": 1500, "algorithm_type": "local_search"}),
    ("Swap", LocalSearchType.SWAP, {"max_iterations": 8000, "algorithm_type": "local_search"}),
    ("Hybrid", LocalSearchType.HYBRID, {"max_iterations": 10, "algorithm_type": "local_search"}),
]

META_HEURISTIC_STRATEGIES = [
    ("GA", "GA", {"pop_size": 120, "generations": 300, "mutation_rate": 0.12, "elite_size": 6, "algorithm_type": "meta_heuristic"}),
    ("PSO", "PSO", {"swarm_size": 80, "iterations": 250, "w": 0.72, "c1": 1.6, "c2": 1.6, "algorithm_type": "meta_heuristic"}),
    ("GWO", "GWO", {"pack_size": 80, "iterations": 250, "algorithm_type": "meta_heuristic"}),
    ("HHO", "HHO", {"hawks": 80, "iterations": 250, "algorithm_type": "meta_heuristic"}),
]

STRATEGIES = LOCAL_SEARCH_STRATEGIES + META_HEURISTIC_STRATEGIES


def _current_benchmark_profile() -> str:
    if BENCHMARK_PROFILE not in VALID_BENCHMARK_PROFILES:
        return "quality_first"
    return BENCHMARK_PROFILE


def _tune_meta_params(strategy_name: str, params: Dict[str, Any], n_nodes: int) -> Dict[str, Any]:
    tuned = params.copy()
    profile = _current_benchmark_profile()
    n = max(1, int(n_nodes))

    # GOREV 5: Profile bypass modu - bildiri_aligned parametreleri degistirmez
    if profile == "bildiri_aligned":
        return tuned

    def _cap(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, value))

    if strategy_name.upper() == "GA":
        pop_size = int(tuned.get("pop_size", 120))
        generations = int(tuned.get("generations", 300))
        mutation_rate = float(tuned.get("mutation_rate", 0.12))
        elite_size = int(tuned.get("elite_size", 6))

        if profile == "quality_first":
            pop_size = int(pop_size * 0.7)
            generations = int(generations * 1.15)
            mutation_rate = min(0.18, mutation_rate + 0.02)
            elite_size = max(4, int(pop_size * 0.07))
        else:
            pop_size = int(pop_size * 1.0)
            generations = int(generations * 1.0)
            elite_size = max(6, int(pop_size * 0.06))

        tuned["pop_size"] = _cap(pop_size, 60 if n <= 100 else 80, 150 if n <= 500 else 180)
        tuned["generations"] = _cap(generations, 200 if n <= 100 else 250, 500 if n <= 100 else 700 if n <= 500 else 900)
        tuned["mutation_rate"] = mutation_rate
        tuned["elite_size"] = elite_size

    elif strategy_name.upper() == "PSO":
        swarm_size = int(tuned.get("swarm_size", 80))
        iterations = int(tuned.get("iterations", 250))
        if profile == "quality_first":
            swarm_size = int(swarm_size * 0.75)
            iterations = int(iterations * 1.20)
        else:
            swarm_size = int(swarm_size * 1.0)
            iterations = int(iterations * 1.0)
        tuned["swarm_size"] = _cap(swarm_size, 40 if n <= 100 else 50, 120 if n <= 500 else 160)
        tuned["iterations"] = _cap(iterations, 150 if n <= 100 else 200, 450 if n <= 100 else 650 if n <= 500 else 850)

    elif strategy_name.upper() == "GWO":
        pack_size = int(tuned.get("pack_size", 80))
        iterations = int(tuned.get("iterations", 250))
        if profile == "quality_first":
            pack_size = int(pack_size * 0.75)
            iterations = int(iterations * 1.20)
        tuned["pack_size"] = _cap(pack_size, 40 if n <= 100 else 50, 120 if n <= 500 else 160)
        tuned["iterations"] = _cap(iterations, 150 if n <= 100 else 200, 450 if n <= 100 else 650 if n <= 500 else 850)

    elif strategy_name.upper() == "HHO":
        hawks = int(tuned.get("hawks", 80))
        iterations = int(tuned.get("iterations", 250))
        if profile == "quality_first":
            hawks = int(hawks * 0.75)
            iterations = int(iterations * 1.20)
        tuned["hawks"] = _cap(hawks, 40 if n <= 100 else 50, 120 if n <= 500 else 160)
        tuned["iterations"] = _cap(iterations, 150 if n <= 100 else 200, 450 if n <= 100 else 650 if n <= 500 else 850)

    return tuned


def _refine_route(route: List[str], duration_func: Callable[[List[str]], float], profile: str) -> Tuple[List[str], float]:
    if profile == "baseline":
        ls_type = LocalSearchType.TWO_OPT
        max_iterations = 50
    else:
        ls_type = LocalSearchType.TWO_OPT
        max_iterations = 300

    try:
        refined_route, refined_cost = apply_local_search(
            route,
            duration_func,
            ls_type,
            max_iterations=max_iterations,
        )
    except TypeError:
        refined_route, refined_cost = apply_local_search(route, duration_func, ls_type)

    return refined_route, refined_cost

# Discrete-move scaling for permutation update operators.
# We keep only a small portion of swaps per step to avoid route destruction.
MOVE_SCALE = 0.1


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
    """Create duration function backed by string dict (legacy — use create_np_duration_func for performance)."""
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


import numpy as _np


def create_np_distance_matrix(coordinates: List[Tuple[float, float]]) -> '_np.ndarray':
    """Build an (n, n) float64 numpy distance matrix using TSPLIB EUC_2D rounding.

    Avoids the O(n²) string-key dict allocations of create_distance_matrix().
    The returned array is the canonical form expected by Numba JIT kernels.
    """
    n = len(coordinates)
    dm = _np.zeros((n, n), dtype=_np.float64)
    for i in range(n):
        xi, yi = coordinates[i]
        for j in range(i + 1, n):
            xj, yj = coordinates[j]
            d = float(int(round(_np.hypot(xi - xj, yi - yj))))
            dm[i, j] = d
            dm[j, i] = d
    return dm


def create_np_duration_func(
    dist_matrix_np: '_np.ndarray',
    unique_locs: List[str],
) -> Callable[[List[str]], float]:
    """Create a duration function backed by a numpy distance matrix.

    The closure uses O(1) integer-index lookups instead of nested dict.get().
    The function object itself is stable (same identity for the same problem),
    so the _DIST_MATRIX_CACHE in local_search_numba.py hits on first use
    and never rebuilds the matrix.

    Args:
        dist_matrix_np: (n, n) float64 array from create_np_distance_matrix()
        unique_locs: ordered list of location strings, e.g. ["L1", "L2", ...]
    """
    index_map: Dict[str, int] = {loc: i for i, loc in enumerate(unique_locs)}
    _dm = dist_matrix_np  # local ref to avoid global lookup in closure

    def duration_func(route: List[str]) -> float:
        if not route:
            return 0.0
        try:
            total = 0.0
            prev_idx = index_map[route[0]]
            for loc in route[1:]:
                curr_idx = index_map[loc]
                total += _dm[prev_idx, curr_idx]
                prev_idx = curr_idx
            total += _dm[prev_idx, index_map[route[0]]]
            return total
        except KeyError:
            # Fallback: unknown location — return 0
            return 0.0

    # Attach metadata so _build_or_get_dist_matrix can reuse the prebuilt matrix.
    # This avoids a second O(n²) matrix reconstruction inside local_search_numba.
    duration_func._np_dist_matrix = dist_matrix_np  # type: ignore[attr-defined]
    duration_func._np_unique_locs = unique_locs      # type: ignore[attr-defined]
    return duration_func


def convert_route_to_indices(route: List[str]) -> List[int]:
    """Convert string route to integer indices"""
    return [int(loc[1:]) for loc in route]


def _route_cost(route: List[str], duration_func: Callable[[List[str]], float]) -> float:
    return duration_func(route)


def _random_swap(route: List[str], rng: random.Random) -> List[str]:
    if len(route) < 2:
        return route[:]
    i, j = rng.sample(range(len(route)), 2)
    r = route[:]
    r[i], r[j] = r[j], r[i]
    return r


def _ordered_crossover(parent_a: List[str], parent_b: List[str], rng: random.Random) -> List[str]:
    n = len(parent_a)
    i, j = sorted(rng.sample(range(n), 2))
    child = [None] * n
    child[i:j] = parent_a[i:j]
    child_set = set(child[i:j])
    fill = [g for g in parent_b if g not in child_set]
    k = 0
    for idx in range(n):
        if child[idx] is None:
            child[idx] = fill[k]
            k += 1
    return child


def _apply_2opt_to_route(
    route: List[str],
    duration_func: Callable[[List[str]], float],
    max_iter: int = 10,
) -> List[str]:
    """Memetic initialization icin 2-opt iyilestirme."""
    try:
        improved, _ = apply_local_search(
            route, duration_func, LocalSearchType.TWO_OPT,
            max_iterations=max_iter,
        )
        return improved
    except Exception:
        return route


def _tournament_select(scored: List[Tuple], rng: random.Random, k: int = 3) -> List[str]:
    """Tournament selection: pick the best of k random candidates."""
    candidates = rng.sample(scored, min(k, len(scored)))
    return min(candidates, key=lambda x: x[1])[0]


def _run_ga(initial_route: List[str], duration_func: Callable[[List[str]], float], params: Dict[str, Any], seed: int) -> List[str]:
    rng = random.Random(seed)
    pop_size = int(params.get("pop_size", 50))
    generations = int(params.get("generations", 100))
    mutation_rate = float(params.get("mutation_rate", 0.1))
    elite_size = max(1, int(params.get("elite_size", 4)))
    crossover_rate = float(params.get("crossover_rate", 0.85))
    max_no_improvement = int(params.get("max_no_improvement", 50))

    population = []
    for _ in range(pop_size):
        candidate = initial_route[:]
        rng.shuffle(candidate)
        # Memetic 2-opt initialization (Bildiri2026 ile uyumlu)
        candidate = _apply_2opt_to_route(candidate, duration_func, max_iter=10)
        population.append(candidate)

    if population:
        population[0] = _apply_2opt_to_route(initial_route[:], duration_func, max_iter=10)

    best_cost = float('inf')
    no_improve_count = 0

    for _ in range(generations):
        scored = sorted(((route, _route_cost(route, duration_func)) for route in population), key=lambda x: x[1])
        elites = [r[:] for r, _ in scored[:elite_size]]
        next_pop = elites[:]

        # Track best for early stop
        gen_best = scored[0][1]
        if gen_best < best_cost:
            best_cost = gen_best
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= max_no_improvement:
            break

        while len(next_pop) < pop_size:
            # Tournament selection k=3 (bildiri2026 uyumlu)
            parent_a = _tournament_select(scored, rng, k=3)
            parent_b = _tournament_select(scored, rng, k=3)
            if rng.random() < crossover_rate:
                child = _ordered_crossover(parent_a, parent_b, rng)
            else:
                child = parent_a[:]
            if rng.random() < mutation_rate:
                # Balanced swap/inversion mutation 50/50 (bildiri2026 _mutate)
                if rng.random() < 0.5:
                    child = _random_swap(child, rng)
                else:
                    i, j = sorted(rng.sample(range(len(child)), 2))
                    child[i:j + 1] = list(reversed(child[i:j + 1]))
            next_pop.append(child)

        population = next_pop

    return min(population, key=lambda r: _route_cost(r, duration_func))


def _towards_route(current: List[str], target: List[str], rng: random.Random, strength: float = 0.5) -> List[str]:
    if not current:
        return current[:]
    route = current[:]
    index_of = {v: i for i, v in enumerate(route)}
    # MOVE_SCALE limits per-step disruption so we keep guided convergence stable.
    moves = max(1, int(len(route) * strength * MOVE_SCALE))
    target_index = {gene: idx for idx, gene in enumerate(target)}
    for _ in range(moves):
        gene = rng.choice(target)
        target_idx = target_index[gene]
        curr_idx = index_of.get(gene, target_idx)
        if curr_idx != target_idx:
            swap_gene = route[target_idx]
            route[curr_idx], route[target_idx] = route[target_idx], route[curr_idx]
            index_of[gene] = target_idx
            index_of[swap_gene] = curr_idx
    return route


# ---------------------------------------------------------------
# Swap-sequence PSO velocity helpers (bildiri2026 pattern)
# ---------------------------------------------------------------

def _diff_swaps_str(current: List[str], target: List[str]) -> List[Tuple[int, int]]:
    """Return swap list that transforms `current` into `target` (string route version).

    Deterministic walk: left-to-right, find target[i] in tail of temp, swap into i.
    Mirrors bildiri2026 PSOOptimizer._diff_swaps but works on List[str].
    """
    swaps: List[Tuple[int, int]] = []
    temp = current[:]
    for i in range(len(target)):
        if temp[i] != target[i]:
            try:
                j = temp.index(target[i], i)
            except ValueError:
                continue
            temp[i], temp[j] = temp[j], temp[i]
            swaps.append((i, j))
    return swaps


def _apply_swaps_str(position: List[str], swaps: List[Tuple[int, int]]) -> List[str]:
    """Apply swap sequence deterministically to a string-route."""
    pos = position[:]
    for i, j in swaps:
        if 0 <= i < len(pos) and 0 <= j < len(pos):
            pos[i], pos[j] = pos[j], pos[i]
    return pos


def _combine_velocities_str(
    inertia_v: List[Tuple[int, int]],
    cog_v: List[Tuple[int, int]],
    soc_v: List[Tuple[int, int]],
    rng: random.Random,
    w: float,
    c1: float,
    c2: float,
    max_vel: int,
) -> List[Tuple[int, int]]:
    """Clerc-style probabilistic combination (bildiri2026 _combine_velocities)."""
    new_v: List[Tuple[int, int]] = []
    for swap in inertia_v:
        if rng.random() < w:
            new_v.append(swap)
    for swap in cog_v:
        if rng.random() < c1 / 3.0:
            new_v.append(swap)
    for swap in soc_v:
        if rng.random() < c2 / 3.0:
            new_v.append(swap)
    if len(new_v) > max_vel:
        new_v = rng.sample(new_v, max_vel)
    return new_v


def _run_pso(initial_route: List[str], duration_func: Callable[[List[str]], float], params: Dict[str, Any], seed: int) -> List[str]:
    """Swap-sequence PSO — bildiri2026 pattern (Step 7)."""
    rng = random.Random(seed)
    swarm_size = int(params.get("swarm_size", 30))
    iterations = int(params.get("iterations", 100))
    w = float(params.get("w", 0.729))
    c1 = float(params.get("c1", 1.49445))
    c2 = float(params.get("c2", 1.49445))
    max_vel = int(params.get("max_velocity_size", 5))
    reinit_interval = int(params.get("reinit_interval", 50))

    swarm = []
    for _ in range(swarm_size):
        route = initial_route[:]
        rng.shuffle(route)
        # Memetic 2-opt initialization (Bildiri2026 ile uyumlu)
        route = _apply_2opt_to_route(route, duration_func, max_iter=30)
        swarm.append({"route": route, "best": route[:], "best_cost": _route_cost(route, duration_func),
                      "velocity": []})

    if swarm:
        init_opt = _apply_2opt_to_route(initial_route[:], duration_func, max_iter=30)
        swarm[0]["route"] = init_opt
        swarm[0]["best"] = init_opt[:]
        swarm[0]["best_cost"] = _route_cost(init_opt, duration_func)

    gbest = min(swarm, key=lambda p: p["best_cost"])["best"][:]
    n = len(initial_route)

    for it in range(iterations):
        for particle in swarm:
            cog_v = _diff_swaps_str(particle["route"], particle["best"])
            soc_v = _diff_swaps_str(particle["route"], gbest)
            new_vel = _combine_velocities_str(
                particle["velocity"], cog_v, soc_v, rng, w, c1, c2, max_vel
            )
            new_route = _apply_swaps_str(particle["route"], new_vel)

            cost = _route_cost(new_route, duration_func)
            particle["route"] = new_route
            particle["velocity"] = new_vel
            if cost < particle["best_cost"]:
                particle["best"] = new_route[:]
                particle["best_cost"] = cost

        gbest = min(swarm, key=lambda p: p["best_cost"])["best"][:]

        # Periyodik re-initialization (Bildiri2026 ile uyumlu)
        if it > 0 and it % reinit_interval == 0:
            for particle in swarm:
                if rng.random() < 0.9:
                    pos = particle["best"][:]
                    for _ in range(rng.randint(1, 3)):
                        a, b = rng.sample(range(n), 2)
                        pos[a], pos[b] = pos[b], pos[a]
                else:
                    pos = gbest[:]
                    rng.shuffle(pos)
                pos = _apply_2opt_to_route(pos, duration_func, max_iter=30)
                cost = _route_cost(pos, duration_func)
                particle["route"] = pos
                particle["velocity"] = []
                if cost < particle["best_cost"]:
                    particle["best"] = pos[:]
                    particle["best_cost"] = cost
                if cost < _route_cost(gbest, duration_func):
                    gbest = pos[:]
            gbest = min(swarm, key=lambda p: p["best_cost"])["best"][:]

    return gbest


def _run_gwo(initial_route: List[str], duration_func: Callable[[List[str]], float], params: Dict[str, Any], seed: int) -> List[str]:
    """Grey Wolf Optimizer — Mirjalili et al. (2014) uyumlu TSP adaptasyonu.

    Temel mekanizmalar:
    - a parametresi 2→0 lineer azalır (keşif-sömürü dengesi)
    - A vektörü: |A|>1 → keşif (uzak arama), |A|<1 → sömürü (yakın arama)
    - C vektörü: rastgele ağırlık [0,2]
    - α, β, δ hiyerarşisi ile pozisyon güncelleme
    """
    rng = random.Random(seed)
    pack_size = max(3, int(params.get("pack_size", 30)))
    iterations = int(params.get("iterations", 100))

    pack = []
    for _ in range(pack_size):
        route = initial_route[:]
        rng.shuffle(route)
        # Memetic 2-opt initialization (GOREV 7)
        route = _apply_2opt_to_route(route, duration_func, max_iter=10)
        pack.append(route)

    if pack:
        init_opt = _apply_2opt_to_route(initial_route[:], duration_func, max_iter=10)
        pack[0] = init_opt

    for it in range(iterations):
        scored = sorted(((r, _route_cost(r, duration_func)) for r in pack), key=lambda x: x[1])
        alpha = scored[0][0]
        beta = scored[min(1, len(scored) - 1)][0]
        delta = scored[min(2, len(scored) - 1)][0]

        # Periyodik memetic refinement (her 10 iterasyonda) - GWO_HHO_FIX_PLAN
        if it > 0 and it % 10 == 0:
            alpha = _apply_2opt_to_route(alpha, duration_func, max_iter=20)
            beta = _apply_2opt_to_route(beta, duration_func, max_iter=20)
            delta = _apply_2opt_to_route(delta, duration_func, max_iter=20)

        # a parametresi: 2'den 0'a lineer azalma (Mirjalili Eq. 3.3)
        a = 2.0 * (1.0 - it / max(1, iterations))

        new_pack = [alpha[:], beta[:], delta[:]]
        while len(new_pack) < pack_size:
            wolf = rng.choice(pack)[:]

            # Her lider için güncelleme (Mirjalili Eq. 3.5-3.7)
            # Discrete GWO-TSP: swap-sequence position update (bildiri2026 PSO pattern)
            for leader in [alpha, beta, delta]:
                r1 = rng.random()
                r2 = rng.random()
                A = 2.0 * a * r1 - a        # |A|>1 → keşif, |A|<1 → sömürü
                C = 2.0 * r2                 # rastgele ağırlık [0, 2]

                if abs(A) > 1.0:
                    # Keşif: rastgele pak üyesine doğru swap-sequence hareketi
                    target = rng.choice(pack)
                    swaps = _diff_swaps_str(wolf, target)
                    # |A| ∈ [1,2] → küçük prob ile keşif
                    prob = min(0.5, abs(A) / 6.0)
                    selected = [s for s in swaps if rng.random() < prob]
                    wolf = _apply_swaps_str(wolf, selected)
                else:
                    # Sömürü: lider farkının C/3 olasılıklı örneklenmesi
                    # Mirrors bildiri2026 PSO _combine_velocities social term (c/3)
                    swaps = _diff_swaps_str(wolf, leader)
                    prob = min(0.9, abs(C) / 3.0)  # C ∈ [0,2] → prob ∈ [0, 0.67]
                    selected = [s for s in swaps if rng.random() < prob]
                    wolf = _apply_swaps_str(wolf, selected)

            # Düşük olasılıkla rastgele swap (çeşitlilik)
            if rng.random() < 0.3 * a / 2.0:
                wolf = _random_swap(wolf, rng)

            new_pack.append(wolf)
        pack = new_pack

    # Final 300-iter 2-opt polishing (bildiri2026 uyumlu)
    best_route = min(pack, key=lambda r: _route_cost(r, duration_func))
    return _apply_2opt_to_route(best_route, duration_func, max_iter=300)


def _levy_flight(route: List[str], rng: random.Random, scale: float = 0.3) -> List[str]:
    """Lévy flight mutasyonu — uzun atlama ile lokal optimumdan kaçış.

    Mantega's Lévy distribution (beta=1.5) kullanılarak swap sayısı belirlenir.
    Heidari et al. (2019) HHO Eq. 4.8 uyumlu.
    """
    n = len(route)
    if n < 2:
        return route[:]
    beta = 1.5
    sigma_num = math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
    sigma_den = math.gamma((1 + beta) / 2) * beta * (2 ** ((beta - 1) / 2))
    sigma = (sigma_num / sigma_den) ** (1 / beta)
    u = rng.gauss(0, sigma)
    v = rng.gauss(0, 1)
    step = u / (abs(v) ** (1 / beta))
    num_swaps = max(1, min(int(abs(step) * scale * n), n // 2))
    result = route[:]
    for _ in range(num_swaps):
        i, j = rng.sample(range(n), 2)
        result[i], result[j] = result[j], result[i]
    return result


def _hho_move_towards(
    hawk: List[str],
    target: List[str],
    rng: random.Random,
    intensity: float,
    max_vel: int = 15,
) -> List[str]:
    """Discrete HHO position update toward `target` using swap-sequence.

    Maps the continuous HHO update X(t+1) = Prey - E·|...| to the permutation
    domain via swap-sequence (bildiri2026 PSO pattern):
    - Compute full swap sequence: current → target
    - Sample each swap with probability proportional to intensity
    - intensity ∈ [0, 2] → prob = min(0.9, intensity/2) ∈ [0, 0.9]
    """
    swaps = _diff_swaps_str(hawk, target)
    if not swaps:
        return hawk[:]
    prob = min(0.9, intensity / 2.0)
    selected = [s for s in swaps if rng.random() < prob]
    if len(selected) > max_vel:
        selected = rng.sample(selected, max_vel)
    return _apply_swaps_str(hawk, selected)


def _run_hho(initial_route: List[str], duration_func: Callable[[List[str]], float], params: Dict[str, Any], seed: int) -> List[str]:
    """Harris Hawks Optimization — Heidari et al. (2019) uyumlu TSP adaptasyonu.

    Temel mekanizmalar:
    - Kaçış enerjisi: E = 2·E₀·(1-t/T), E₀ ∈ [-1,1]
    - Keşif fazı: |E| ≥ 1 — rastgele konumlanma
    - Sömürü fazı: 4 strateji (soft/hard besiege, with/without rapid dives)
    - Lévy flight: uzun atlama ile lokal optimumdan kaçış (Mantegna 1994, β=1.5)
    - r (kaçış olasılığı): strateji seçimi

    Discrete position update: _hho_move_towards (swap-sequence, bildiri2026 uyumlu)
    """
    rng = random.Random(seed)
    hawks = int(params.get("hawks", 30))
    iterations = int(params.get("iterations", 100))

    population = []
    for _ in range(hawks):
        route = initial_route[:]
        rng.shuffle(route)
        route = _apply_2opt_to_route(route, duration_func, max_iter=10)
        population.append(route)

    if population:
        init_opt = _apply_2opt_to_route(initial_route[:], duration_func, max_iter=10)
        population[0] = init_opt

    best = min(population, key=lambda r: _route_cost(r, duration_func))
    best = best[:]
    best_cost = _route_cost(best, duration_func)

    for it in range(iterations):
        # Kaçış enerjisi: E₀ rastgele [-1,1], E lineer azalır (Heidari Eq. 4.1)
        E0 = 2 * rng.random() - 1
        E = 2 * E0 * (1 - it / max(1, iterations))

        updated = [best[:]]
        while len(updated) < hawks:
            hawk = rng.choice(population)[:]
            hawk_cost = _route_cost(hawk, duration_func)
            r = rng.random()  # Kaçış olasılığı

            if abs(E) >= 1:
                # ═══ KEŞİF FAZI ═══ (|E| ≥ 1)
                if rng.random() < 0.5:
                    # Rastgele bir şahine doğru swap-sequence hareketi
                    random_hawk = rng.choice(population)
                    intensity = rng.random() * 1.0  # küçük adım
                    hawk = _hho_move_towards(hawk, random_hawk, rng, intensity)
                else:
                    # Lévy flight ile rastgele keşif (Mantegna, doğru)
                    hawk = _levy_flight(hawk, rng, scale=0.3)
            else:
                # ═══ SÖMÜRÜ FAZI ═══ (|E| < 1)
                if r >= 0.5:
                    if abs(E) >= 0.5:
                        # Soft besiege: X(t+1) = ΔX - E·|J·Prey - X(t)|
                        J = 2 * (1 - rng.random())
                        intensity = abs(E * J)
                        hawk = _hho_move_towards(hawk, best, rng, intensity)
                    else:
                        # Hard besiege: X(t+1) = Prey - E·|Prey - X(t)|
                        hawk = _hho_move_towards(hawk, best, rng, abs(E))
                else:
                    if abs(E) >= 0.5:
                        # Soft besiege + progressive rapid dives (Lévy)
                        best_dive = hawk[:]
                        best_dive_cost = hawk_cost
                        for _ in range(3):
                            intensity = abs(E) * rng.random()
                            candidate = _hho_move_towards(hawk, best, rng, intensity)
                            candidate = _levy_flight(candidate, rng, scale=0.3)
                            candidate_cost = _route_cost(candidate, duration_func)
                            if candidate_cost < best_dive_cost:
                                best_dive = candidate
                                best_dive_cost = candidate_cost
                        hawk = best_dive
                    else:
                        # Hard besiege + progressive rapid dives (Lévy)
                        hawk = _hho_move_towards(hawk, best, rng, abs(E))
                        hawk = _levy_flight(hawk, rng, scale=0.2)

            # Değerlendir ve güncelle
            new_cost = _route_cost(hawk, duration_func)
            if new_cost < hawk_cost:
                updated.append(hawk)
            else:
                updated.append(hawk[:])

            # Av (en iyi çözüm) güncelle
            if new_cost < best_cost:
                best = hawk[:]
                best_cost = new_cost

        # Periyodik memetic refinement (her 10 iterasyonda)
        if it > 0 and it % 10 == 0:
            best = _apply_2opt_to_route(best, duration_func, max_iter=20)
            best_cost = _route_cost(best, duration_func)

        population = updated

    # Final 300-iter 2-opt polishing (bildiri2026 uyumlu)
    return _apply_2opt_to_route(best, duration_func, max_iter=300)


def _run_meta_heuristic(
    strategy_name: str,
    initial_route: List[str],
    duration_func: Callable[[List[str]], float],
    params: Dict[str, Any],
    seed: int,
) -> List[str]:
    tuned_params = _tune_meta_params(strategy_name, params, len(initial_route))
    upper = strategy_name.upper()
    if upper == "GA":
        route = _run_ga(initial_route, duration_func, tuned_params, seed)
    elif upper == "PSO":
        route = _run_pso(initial_route, duration_func, tuned_params, seed)
    elif upper == "GWO":
        route = _run_gwo(initial_route, duration_func, tuned_params, seed)
    elif upper == "HHO":
        route = _run_hho(initial_route, duration_func, tuned_params, seed)
    else:
        raise ValueError(f"Unknown meta-heuristic strategy: {strategy_name}")

    # Step 9: Final aggressive 2-opt polishing — always-on, 300 iter (matching bildiri2026).
    # bildiri2026 applies 300-iter 2-opt specifically to the best solution after the
    # metaheuristic completes; this replicates that behaviour regardless of profile.
    polished_route, polished_cost = apply_local_search(
        route, duration_func, LocalSearchType.TWO_OPT, max_iterations=300
    )
    if polished_cost < _route_cost(route, duration_func):
        return polished_route
    return route


# ============================================================
# Benchmark Functions
# ============================================================

def run_single_test(
    problem: TSPLIBProblem,
    strategy_instance: Union[LocalSearchType, str],
    seed: int,
    params: Union[Dict[str, Any], int, None] = None
) -> Dict:
    """Run single test with specific seed for local-search or meta-heuristic.

    Step 4: Uses create_np_distance_matrix + create_np_duration_func to avoid
    the O(n^2) Dict string-key allocation of create_distance_matrix() on every
    single test run.  The numpy-backed duration_func also benefits from the
    _DIST_MATRIX_CACHE in local_search_numba.py (no second matrix rebuild).
    """
    coordinates = problem.coordinates
    dimension = problem.dimension
    run_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        run_params = params.copy()
    elif isinstance(params, int):
        run_params = {"max_iterations": params}

    # Step 4: numpy-backed distance matrix (replaces O(n²) dict creation)
    unique_locs = [f"L{i+1}" for i in range(dimension)]
    np_matrix = create_np_distance_matrix(coordinates)
    duration_func = create_np_duration_func(np_matrix, unique_locs)

    # Create initial tour with random permutation
    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    initial_route = [f"L{i}" for i in indices]

    # Apply selected optimization strategy
    start_time = time.time()
    if isinstance(strategy_instance, LocalSearchType):
        improved_route, _ = apply_local_search(
            initial_route,
            duration_func,
            strategy_instance,
            max_iterations=int(run_params.get("max_iterations", 1000)),
        )
        algorithm_type = "local_search"
    else:
        improved_route = _run_meta_heuristic(
            str(strategy_instance),
            initial_route,
            duration_func,
            run_params,
            seed,
        )
        algorithm_type = "meta_heuristic"
    elapsed = time.time() - start_time

    # Calculate tour length
    tour_indices = convert_route_to_indices(improved_route)
    tour_length = calculate_tour_length(tour_indices, coordinates)

    gap = ((tour_length - problem.optimal) / problem.optimal) * 100

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
        "algorithm_type": algorithm_type,
    }


def run_benchmark_for_problem(
    problem: TSPLIBProblem,
    n_runs: int = 3,
    verbose: bool = True
) -> List[Dict]:
    """Run benchmark for a single problem with all strategies"""
    results = []
    
    for strat_name, strategy_instance, strategy_params in STRATEGIES:
        if verbose:
            print(f"    Testing {strat_name}...", end=" ", flush=True)
        
        run_results = []
        for run in range(n_runs):
            seed = (run + 1) * 42
            result = run_single_test(problem, strategy_instance, seed, strategy_params)
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
            "algorithm_type": strategy_params.get("algorithm_type", "local_search"),
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
