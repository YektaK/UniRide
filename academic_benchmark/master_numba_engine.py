#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Master NUMBA Engine — Local Search & Meta-heuristics (GA, PSO, GWO, HHO)
================================================================================

Konsolidasyon FAZ 3 çıktısı. Eski `run_smart_benchmark_numba.py` ve
`run_smart_benchmark_numba_doe.py` dosyalarındaki özellikleri merkezileştirir.

Özellikler:
  - Numba JIT tabanlı algoritma adaptasyonu.
  - ProcessPoolExecutor ile Windows-safe paralelleştirme.
  - Incremental CSV loglama ve Smart Caching.
  - DEFAULT (direkt benchmark) ve TUNING (DoE) modları.

Kullanım:
    python academic_benchmark/master_numba_engine.py
"""

import argparse
import concurrent.futures
import gzip
import io
import itertools
import json
import math
import os

# OpenBLAS / NumPy multiprocessing çökmesini (Memory allocation failed) engellemek için
# her process'in kendi içinde tek thread kullanmasını zorluyoruz.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import random
import re
import signal
import statistics
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from multiprocessing import cpu_count
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

# Windows stdout encoding düzeltmesi
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if os.path.join(_PROJECT_ROOT, "optimizer_api") not in sys.path:
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "optimizer_api"))

try:
    from benchmark_utils import (
        ETATracker,
        TSPLIB_OPTIMALS,
        append_csv_row,
        check_algorithms_status,
        clear_screen,
        format_time,
        generate_combinations,
        get_cpu_info,
        get_file_hash,
        load_metadata,
        log_environment_info,
        multi_select,
        param_signature,
        parse_index_or_all,
        ProblemSelector,
        save_config,
        save_convergence_history,
        save_metadata,
        select_run_count,
        select_worker_count,
        stdev_safe,
        update_algorithm_hashes,
    )
except ModuleNotFoundError:
    from academic_benchmark.benchmark_utils import (
        ETATracker,
        TSPLIB_OPTIMALS,
        append_csv_row,
        check_algorithms_status,
        clear_screen,
        format_time,
        generate_combinations,
        get_cpu_info,
        get_file_hash,
        load_metadata,
        log_environment_info,
        multi_select,
        param_signature,
        parse_index_or_all,
        ProblemSelector,
        save_config,
        save_convergence_history,
        save_metadata,
        select_run_count,
        select_worker_count,
        stdev_safe,
        update_algorithm_hashes,
    )

# Numba modüllerini import edelim
from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
    BENCHMARK_PROFILE as DEFAULT_PROFILE,
    STRATEGIES,
    VALID_BENCHMARK_PROFILES,
    _run_meta_heuristic,
    apply_local_search,
    convert_route_to_indices,
    create_np_distance_matrix,
    create_np_duration_func,
    create_duration_func,
    run_single_test,
)
from optimizer_api.utils.local_search_numba import LocalSearchType

VERSION = "2.0.0"

# TSPLIB veri kaynakları (öncelik sırası)
TSPLIB_ARCHIVE = os.path.join(_ENGINE_DIR, "tsplib_problems", "ALL_tsp.tar.gz")
TSPLIB_DIR_FALLBACK = os.path.join(_ENGINE_DIR, "tsplib_data")

# Çıktı dizinleri
RESULTS_DIR = os.path.join(_ENGINE_DIR, "numba_results")
BENCHMARK_DB = os.path.join(_ENGINE_DIR, "benchmark_db")
METADATA_PATH = os.path.join(BENCHMARK_DB, "master_numba_metadata.json")
DOE_RESULTS_DIR = os.path.join(RESULTS_DIR, "doe_numba")
CONFIGS_DIR = os.path.join(BENCHMARK_DB, "configs_numba")
HISTORIES_DIR = os.path.join(BENCHMARK_DB, "convergence_numba")
HISTORY_DIR = os.path.join(BENCHMARK_DB, "history")

# Hash tracking için izlenen kaynak dosyalar
ALGORITHMS_TO_CHECK: Dict[str, str] = {
    "BenchmarkRunner_NUMBA": os.path.join(_PROJECT_ROOT, "optimizer_api", "tests", "run_interactive_benchmark_v2_numba.py"),
    "GA_Strategy": os.path.join(_PROJECT_ROOT, "optimizer_api", "strategies", "ga_strategy.py"),
    "PSO_Strategy": os.path.join(_PROJECT_ROOT, "optimizer_api", "strategies", "pso_strategy.py"),
    "GWO_Strategy": os.path.join(_PROJECT_ROOT, "optimizer_api", "strategies", "gwo_strategy.py"),
    "HHO_Strategy": os.path.join(_PROJECT_ROOT, "optimizer_api", "strategies", "hho_strategy.py"),
}

DOE_MAX_COMBINATIONS = 50

class EngineMode(Enum):
    DEFAULT = "default"  
    TUNING  = "tuning"   

_shutdown_requested: bool = False
_active_metadata: Optional[Dict[str, Any]] = None
_active_results: List[Dict[str, Any]] = []

def _ensure_dirs() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(BENCHMARK_DB, exist_ok=True)
    os.makedirs(DOE_RESULTS_DIR, exist_ok=True)
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(HISTORIES_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

def _signal_handler(signum, frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] Kapatma sinyali alindi — tamamlanan sonuclar kaydediliyor...")
    if _active_metadata is not None:
        save_metadata(METADATA_PATH, _active_metadata)
        if _active_results:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(HISTORY_DIR, exist_ok=True)
            csv_path = os.path.join(HISTORY_DIR, f"interrupted_numba_{ts}.csv")
            import csv as _csv
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=list(_active_results[0].keys()))
                writer.writeheader()
                writer.writerows(_active_results)
            print(f"[OK] {len(_active_results)} sonuc kaydedildi: {csv_path}")
    sys.exit(130)

signal.signal(signal.SIGINT, _signal_handler)

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 2: TSPLIB Yükleyici ve Strateji Yönetimi
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DOEProblem:
    """Numba Engine için genişletilmiş problem veri modeli."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[float]
    category: str
    source: str = "tsplib"
    is_time_matrix: bool = False
    time_matrix: Optional[List[List[float]]] = None

@dataclass
class StrategySpec:
    """Algoritma profili ve parametre uzayı sarmalayıcısı."""
    name: str
    payload: Any
    default_params: Dict[str, Any]
    algorithm_type: str

def _clean_tsplib_name(raw: str) -> str:
    name = raw.lower().strip()
    for suffix in (".opt.tour", ".opt", ".tsp"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.split("/")[-1].split("\\")[-1]

def _parse_tsplib_text(content: str, name_hint: str = "") -> Optional[Dict[str, Any]]:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    coord_m = re.search(r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)", content, re.DOTALL | re.I)
    if not coord_m:
        return None
    header = content[: coord_m.start()]
    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.I)
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.I)
    name_matches = list(re.finditer(r"^NAME\s*[:\s]\s*(\S+)", header, re.I | re.M))
    
    if not dim_m:
        return None
    
    raw_name = name_matches[-1].group(1) if name_matches else name_hint
    name = _clean_tsplib_name(raw_name) or _clean_tsplib_name(name_hint)
    if not name:
        return None
        
    dimension = int(dim_m.group(1))
    ewt = ewt_m.group(1).upper() if ewt_m else "EUC_2D"
    
    _SUPPORTED_EWT = ("EUC_2D", "EUC_3D", "CEIL_2D", "ATT", "GEO", "GEOM", "NEU_2D")
    if ewt not in _SUPPORTED_EWT:
        return None

    coords = []
    for line in coord_m.group(1).strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                coords.append((float(parts[1]), float(parts[2])))
            except ValueError:
                pass
                
    if not coords:
        return None

    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": ewt,
        "coordinates": coords,
        "optimal": TSPLIB_OPTIMALS.get(name)
    }

def load_problems(size_limit: int = 0) -> List[DOEProblem]:
    """TSPLIB arşivinden veya özel time_matrix JSON'larından problemleri yükler."""
    problems: Dict[str, DOEProblem] = {}

    def _add(p: DOEProblem) -> None:
        problems.setdefault(p.name, p)

    # 1. TSPLIB Tar Arşivi Yüklemesi
    if os.path.exists(TSPLIB_ARCHIVE):
        try:
            with tarfile.open(TSPLIB_ARCHIVE, "r:gz") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    fobj = tar.extractfile(member)
                    if fobj is None:
                        continue
                    try:
                        if name_lower.endswith(".tsp.gz"):
                            content = gzip.decompress(fobj.read()).decode("utf-8", errors="replace")
                        elif name_lower.endswith(".tsp"):
                            content = fobj.read().decode("utf-8", errors="replace")
                        else:
                            continue
                    except Exception:
                        continue
                    pdata = _parse_tsplib_text(content, member.name)
                    if pdata and pdata["dimension"] <= (size_limit if size_limit > 0 else pdata["dimension"]):
                        dim = pdata["dimension"]
                        cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                        _add(DOEProblem(
                            name=pdata["name"], dimension=dim,
                            coordinates=pdata["coordinates"], optimal=pdata["optimal"],
                            category=cat, source="tsplib"
                        ))
        except Exception as e:
            print(f"[UYARI] tar.gz okunamadi: {e}")

    # 2. Arşiv yoksa dizinden fallback
    if not problems and os.path.exists(TSPLIB_DIR_FALLBACK):
        for fname in os.listdir(TSPLIB_DIR_FALLBACK):
            if fname.lower().endswith(".tsp"):
                with open(os.path.join(TSPLIB_DIR_FALLBACK, fname), "r", encoding="utf-8") as f:
                    pdata = _parse_tsplib_text(f.read(), fname)
                    if pdata and pdata["dimension"] <= (size_limit if size_limit > 0 else pdata["dimension"]):
                        dim = pdata["dimension"]
                        cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                        _add(DOEProblem(
                            name=pdata["name"], dimension=dim,
                            coordinates=pdata["coordinates"], optimal=pdata["optimal"],
                            category=cat, source="tsplib"
                        ))

    # 3. Özel Time Matrix JSON'ları
    data_dir = os.path.join(_ENGINE_DIR, "data")
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".json") and f != "tuned_parameters_db.json":
                fpath = os.path.join(data_dir, f)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if "time_matrix" in data:
                        matrix = data["time_matrix"]
                        name = data.get("name", f.replace(".json", ""))
                        dim = len(matrix)
                        cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                        _add(DOEProblem(
                            name=name, dimension=dim, coordinates=[(0.0, 0.0)] * dim,
                            optimal=data.get("optimal"), category=cat, source="time_matrix",
                            is_time_matrix=True, time_matrix=matrix
                        ))
                except Exception:
                    continue

    return sorted(problems.values(), key=lambda p: p.dimension)

def _normalize_strategy_entry(entry: Tuple[Any, ...]) -> StrategySpec:
    name = entry[0]
    payload = entry[1]
    params = entry[2].copy() if len(entry) > 2 and isinstance(entry[2], dict) else {}
    algo_type = str(params.get("algorithm_type", "local_search" if isinstance(payload, LocalSearchType) else "meta_heuristic"))
    return StrategySpec(name=name, payload=payload, default_params=params, algorithm_type=algo_type)

def _all_strategy_specs() -> List[StrategySpec]:
    """Tüm Numba stratejilerini normalize edilmiş spesifikasyonlara dönüştürür.

    Includes both standard STRATEGIES (from benchmark runner) and
    BILDIRI_STRATEGIES (bildiri2026 native solvers, Step 5).
    """
    specs = [_normalize_strategy_entry(entry) for entry in STRATEGIES]
    for name, payload, params in BILDIRI_STRATEGIES:
        specs.append(StrategySpec(
            name=name,
            payload=payload,
            default_params=params,
            algorithm_type="bildiri_meta",
        ))
    return specs

def _build_numba_parameter_space(spec: StrategySpec) -> Dict[str, List[Any]]:
    """DoE için Numba algoritmalarına özel hiperparametre uzayını oluşturur."""
    name = spec.name.upper()
    if name == "GA":
        return {
            "pop_size": [80, 120, 150],
            "generations": [250, 350, 500],
            "mutation_rate": [0.08, 0.12, 0.16],
            "elite_size": [2, 4, 6, 8],  # GOREV 6: 2 eklendi (bildiri2026: 2)
            "crossover_rate": [0.80, 0.85, 0.90],  # GOREV 6: eklendi (bildiri2026: 0.85)
        }
    if name == "PSO":
        return {
            "swarm_size": [50, 80, 120],
            "iterations": [200, 300, 450, 500],  # GOREV 6: 500 eklendi (bildiri2026: 500)
            "w": [0.65, 0.72, 0.80],
            "c1": [1.4, 1.6, 1.9],
            "c2": [1.4, 1.6, 1.9],
            "reinit_interval": [30, 50, 70],  # GOREV 6: eklendi (bildiri2026: 50)
        }
    if name == "GWO":
        return {
            "pack_size": [50, 80, 120],
            "iterations": [200, 300, 450],
        }
    if name == "HHO":
        return {
            "hawks": [50, 80, 120],
            "iterations": [200, 300, 450],
        }
    if name == "B-PSO":
        # bildiri2026 PSOOptimizer DoE parameter space
        return {
            "swarm_size": [30, 50, 80],
            "max_iterations": [300, 500],
            "inertia_weight": [0.729],
            "cognitive_coeff": [1.49445],
            "social_coeff": [1.49445],
            "max_velocity_size": [5, 8],
            "reinit_interval": [30, 50],
            "max_no_improvement": [100],
        }
    if name == "B-GA":
        # bildiri2026 GAOptimizer DoE parameter space
        return {
            "population_size": [80, 100, 150],
            "generations": [300, 500],
            "crossover_rate": [0.80, 0.85, 0.90],
            "mutation_rate": [0.12, 0.15, 0.18],
            "elite_count": [2, 4],
            "tournament_size": [3, 5],
            "max_no_improvement": [100],
        }
    return {
        "max_iterations": [spec.default_params.get("max_iterations", 300)],
    }

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3: Çekirdek Çalıştırıcılar ve Paralel İşleme (Runner & Pool)
# ─────────────────────────────────────────────────────────────────────────────

def run_single_test_with_matrix(
    problem: DOEProblem,
    strategy_instance: Any,
    seed: int,
    params: Dict[str, Any],
    time_matrix: List[List[float]],
) -> Dict[str, Any]:
    """Numba için 'Time Matrix' tabanlı özel problem çözümleyicisi.

    Step 4: Uses create_np_duration_func() backed by a numpy ndarray instead
    of the O(n²) Dict[str, Dict[str, float]] construction.  The numpy closure
    is stable, so _DIST_MATRIX_CACHE in local_search_numba.py gives a cache
    hit on the first improve() call within the same run.
    """
    import numpy as _np
    dimension = problem.dimension
    run_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        run_params = params.copy()
    elif isinstance(params, int):
        run_params = {"max_iterations": params}

    # Step 4: build numpy matrix directly from List[List[float]]
    unique_locs = [f"L{i+1}" for i in range(dimension)]
    np_matrix = _np.array(time_matrix, dtype=_np.float64)
    duration_func = create_np_duration_func(np_matrix, unique_locs)

    indices = list(range(1, dimension + 1))
    random.seed(seed)
    random.shuffle(indices)
    initial_route = [f"L{i}" for i in indices]

    start_time = time.time()
    if isinstance(strategy_instance, LocalSearchType):
        improved_route, _ = apply_local_search(
            initial_route, duration_func, strategy_instance,
            max_iterations=int(run_params.get("max_iterations", 1000)),
        )
        algorithm_type = "local_search"
    else:
        improved_route = _run_meta_heuristic(
            str(strategy_instance), initial_route, duration_func, run_params, seed,
        )
        algorithm_type = "meta_heuristic"
    elapsed = time.time() - start_time

    tour_indices = convert_route_to_indices(improved_route)
    tour_length = 0
    for k in range(len(tour_indices)):
        a = tour_indices[k]
        b = tour_indices[(k + 1) % len(tour_indices)]
        tour_length += time_matrix[a - 1][b - 1]
    tour_length = int(tour_length)

    optimal = getattr(problem, "optimal", None)
    if optimal and optimal > 0:
        gap = ((tour_length - optimal) / optimal) * 100
    else:
        gap = float("nan")

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
        "algorithm_type": algorithm_type,
    }

def _make_problem_dict(problem: DOEProblem) -> Dict[str, Any]:
    """Objeyi ProcessPool üzerinden aktarılabilmesi için dict'e çevirir."""
    d = {
        "name": problem.name,
        "dimension": problem.dimension,
        "optimal": problem.optimal,
        "coordinates": problem.coordinates,
        "category": problem.category,
        "source": problem.source,
        "is_time_matrix": problem.is_time_matrix,
    }
    if problem.is_time_matrix and problem.time_matrix is not None:
        d["time_matrix"] = problem.time_matrix
    return d

def _resolve_strategy_payload(spec: StrategySpec) -> Any:
    return spec.payload

def _evaluate_param_combo(task: Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]) -> Dict[str, Any]:
    """Bir parametre kombinasyonunu belirli run sayısınca test eder."""
    problem_dict, strategy_name, strategy_payload, strategy_params, combo_idx, n_runs = task

    is_time_matrix = problem_dict.get("is_time_matrix", False)
    time_matrix_data = problem_dict.get("time_matrix")
    optimal = problem_dict.get("optimal")

    class _Problem:
        def __init__(self, data: Dict[str, Any]):
            self.name = data["name"]
            self.dimension = data["dimension"]
            self.optimal = data.get("optimal")
            self.coordinates = data.get("coordinates", [])
            self.category = data.get("category", "small")
            self.source = data.get("source", "tsplib")
            self.is_time_matrix = data.get("is_time_matrix", False)
            self.time_matrix = data.get("time_matrix")

    problem = _Problem(problem_dict)
    effective_problem = problem
    if not optimal:
        class _ProblemWithSafeOptimal(_Problem):
            def __init__(self, data: Dict[str, Any]):
                super().__init__(data)
                self.optimal = 1
        effective_problem = _ProblemWithSafeOptimal(problem_dict)

    run_results: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for run_idx in range(n_runs):
        seed = 1000 + combo_idx * 100 + run_idx
        # Step 5: route bildiri2026 strategies through their dedicated adapters
        if str(strategy_payload) in ("BILDIRI_PSO", "BILDIRI_GA"):
            if str(strategy_payload) == "BILDIRI_PSO":
                result = _run_bildiri_pso(problem_dict, seed, strategy_params)
            else:
                result = _run_bildiri_ga(problem_dict, seed, strategy_params)
        elif is_time_matrix and time_matrix_data:
            result = run_single_test_with_matrix(
                effective_problem, strategy_payload, seed, strategy_params, time_matrix_data
            )
        else:
            result = run_single_test(effective_problem, strategy_payload, seed, strategy_params)
            
        if not optimal:
            result = result.copy()
            result["gap"] = float("nan")
        run_results.append(result)
        
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    avg_length = sum(float(r["tour_length"]) for r in run_results) / max(1, len(run_results))
    valid_gaps = [float(r["gap"]) for r in run_results if not math.isnan(float(r["gap"]))]
    avg_gap = sum(valid_gaps) / len(valid_gaps) if valid_gaps else float("nan")
    convergence_profile = [float(r["tour_length"]) for r in run_results]

    return {
        "problem": problem.name,
        "strategy": strategy_name,
        "combo_idx": combo_idx,
        "params": strategy_params,
        "avg_length": avg_length,
        "avg_gap": avg_gap,
        "avg_time_ms": elapsed_ms / max(1, len(run_results)),
        "n_runs": n_runs,
        "per_run_lengths": convergence_profile,
    }

def _run_pool(tasks: List[Tuple], workers: int, on_result=None) -> List[Dict[str, Any]]:
    """Windows-safe ProcessPoolExecutor ile paralel çalıştırma."""
    if not tasks:
        return []
    if workers <= 1:
        results = []
        for i, task in enumerate(tasks):
            result = _evaluate_param_combo(task)
            results.append(result)
            if on_result:
                on_result(i, result, len(tasks))
        return results
        
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {executor.submit(_evaluate_param_combo, t): i for i, t in enumerate(tasks)}
        for future in concurrent.futures.as_completed(future_to_task):
            i = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                if on_result:
                    on_result(i, result, len(tasks))
            except Exception as e:
                t_info = tasks[i]
                print(f"\n[Worker Hata] Problem: {t_info[0]['name']} - Algoritma: {t_info[1]} | Hata: {str(e)}")
                results.append({
                    "problem": t_info[0]['name'],
                    "strategy": t_info[1],
                    "combo_idx": t_info[4],
                    "params": t_info[3],
                    "avg_length": float("inf"),
                    "avg_gap": float("nan"),
                    "avg_time_ms": 0.0,
                    "n_runs": t_info[5],
                    "per_run_lengths": []
                })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3b: bildiri2026 Adapter (Step 5)
# ─────────────────────────────────────────────────────────────────────────────

def _run_bildiri_solver(
    solver_cls,
    solver_kwargs: Dict[str, Any],
    problem_dict: Dict[str, Any],
    seed: int,
) -> Dict[str, Any]:
    """Generic adapter: run a bildiri2026 BaseTSPSolver on a DOEProblem dict.

    bildiri2026 convention:
      - Node 0 = depot (implicit; tour excludes depot)
      - tour: List[int] of 1..n waypoint indices in full_coords/full_tm

    Our convention:
      - No depot; all nodes are waypoints 1..n ("L1".."Ln")
      - coords[i] = node L(i+1), i.e. 0-indexed in the original list.
    """
    import time as _time
    is_tm = problem_dict.get("is_time_matrix", False)
    coords = problem_dict.get("coordinates", [])
    optimal = problem_dict.get("optimal")

    solver = solver_cls(**solver_kwargs, random_seed=seed)

    t0 = _time.perf_counter()

    if is_tm:
        tm = problem_dict["time_matrix"]
        n = len(tm)
        # Insert depot row/col (all zeros) at index 0
        full_tm = [[0.0] * (n + 1) for _ in range(n + 1)]
        for i in range(n):
            for j in range(n):
                full_tm[i + 1][j + 1] = float(tm[i][j])
        result = solver.solve_with_matrix(full_tm)
        tour_nodes = result.tour  # 1-indexed in full_tm (0 = depot)
        tour_length = float(sum(
            tm[tour_nodes[k] - 1][tour_nodes[(k + 1) % len(tour_nodes)] - 1]
            for k in range(len(tour_nodes))
        ))
    else:
        # Prepend dummy depot (0.0, 0.0) so bildiri2026 indices align
        full_coords = [(0.0, 0.0)] + list(coords)
        result = solver.solve(full_coords)
        tour_nodes = result.tour  # 1-indexed in full_coords
        np_dm = create_np_distance_matrix(coords)
        tour_length = float(sum(
            np_dm[tour_nodes[k] - 1, tour_nodes[(k + 1) % len(tour_nodes)] - 1]
            for k in range(len(tour_nodes))
        ))

    elapsed_ms = (_time.perf_counter() - t0) * 1000.0

    if optimal and optimal > 0:
        gap = ((tour_length - optimal) / optimal) * 100.0
    else:
        gap = float("nan")

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed_ms,
        "algorithm_type": "bildiri_meta",
    }


def _run_bildiri_pso(
    problem_dict: Dict[str, Any],
    seed: int,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run bildiri2026 PSOOptimizer on a DOEProblem dict."""
    try:
        from academic_benchmark.bildiri2026.core import PSOOptimizer
    except ModuleNotFoundError:
        from bildiri2026.core import PSOOptimizer  # type: ignore[no-redef]
    p = params or {}
    kwargs = {
        "swarm_size": int(p.get("swarm_size", 50)),
        "max_iterations": int(p.get("max_iterations", 500)),
        "inertia_weight": float(p.get("inertia_weight", 0.729)),
        "cognitive_coeff": float(p.get("cognitive_coeff", 1.49445)),
        "social_coeff": float(p.get("social_coeff", 1.49445)),
        "max_velocity_size": int(p.get("max_velocity_size", 5)),
        "max_no_improvement": int(p.get("max_no_improvement", 100)),
        "reinit_interval": int(p.get("reinit_interval", 50)),
    }
    return _run_bildiri_solver(PSOOptimizer, kwargs, problem_dict, seed)


def _run_bildiri_ga(
    problem_dict: Dict[str, Any],
    seed: int,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run bildiri2026 GAOptimizer on a DOEProblem dict."""
    try:
        from academic_benchmark.bildiri2026.core import GAOptimizer
    except ModuleNotFoundError:
        from bildiri2026.core import GAOptimizer  # type: ignore[no-redef]
    p = params or {}
    kwargs = {
        "population_size": int(p.get("population_size", 100)),
        "generations": int(p.get("generations", 500)),
        "crossover_rate": float(p.get("crossover_rate", 0.85)),
        "mutation_rate": float(p.get("mutation_rate", 0.15)),
        "elite_count": int(p.get("elite_count", 2)),
        "tournament_size": int(p.get("tournament_size", 3)),
        "max_no_improvement": int(p.get("max_no_improvement", 100)),
    }
    return _run_bildiri_solver(GAOptimizer, kwargs, problem_dict, seed)


# Bildiri2026 strateji tanımları — master_numba_engine'e özgü ek stratejiler.
BILDIRI_STRATEGIES: List[Tuple[str, str, Dict[str, Any]]] = [
    ("B-PSO", "BILDIRI_PSO", {
        "swarm_size": 50, "max_iterations": 500,
        "inertia_weight": 0.729, "cognitive_coeff": 1.49445,
        "social_coeff": 1.49445, "max_velocity_size": 5,
        "max_no_improvement": 100, "reinit_interval": 50,
        "algorithm_type": "bildiri_meta",
    }),
    ("B-GA", "BILDIRI_GA", {
        "population_size": 100, "generations": 500,
        "crossover_rate": 0.85, "mutation_rate": 0.15,
        "elite_count": 2, "tournament_size": 3,
        "max_no_improvement": 100,
        "algorithm_type": "bildiri_meta",
    }),
]


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 4: Tuning (DoE), Benchmark ve CLI Menü
# ─────────────────────────────────────────────────────────────────────────────

def _load_tuning_cache() -> set[Tuple[str, str, str]]:
    completed = set()
    csv_path = os.path.join(RESULTS_DIR, "tuning_progress.csv")
    if not os.path.exists(csv_path):
        return completed
    try:
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                completed.add((row["problem"], row["strategy"], row["param_signature"]))
    except Exception:
        pass
    return completed

def _tune_parameters(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    n_runs: int,
    max_combinations: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool,
) -> Dict[str, Dict[str, Any]]:
    completed = _load_tuning_cache()
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})
    tuning_tasks = []

    for problem in problems:
        for spec in specs:
            space = _build_numba_parameter_space(spec)
            combos = generate_combinations(space, max_combinations)
            for combo_idx, combo in enumerate(combos, 1):
                params = spec.default_params.copy()
                params.update(combo)
                params["algorithm_type"] = spec.algorithm_type
                sig = param_signature(params)
                key = (problem.name, spec.name, sig)
                if skip_cached and key in completed:
                    continue
                tuning_tasks.append(
                    (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, combo_idx, n_runs)
                )

    if not tuning_tasks:
        print("[INFO] Tum tuning tasklari onbellekte mevcut.")
        return best_params

    csv_path = os.path.join(RESULTS_DIR, "tuning_progress.csv")
    fields = [
        "timestamp", "problem", "strategy", "combo_idx", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "param_signature", "params_json"
    ]
    
    tracker = ETATracker()
    
    def on_result(idx, result, total):
        problem_name = result["problem"]
        strategy_name = result["strategy"]
        params = result["params"]
        sig = param_signature(params)
        
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": problem_name,
            "strategy": strategy_name,
            "combo_idx": result["combo_idx"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if math.isnan(result["avg_gap"]) else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "param_signature": sig,
            "params_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
        }
        append_csv_row(csv_path, fields, row)
        
        best_key = f"{problem_name}::{strategy_name}"
        current_best = best_params.get(best_key)
        if current_best is None or result["avg_length"] < float(current_best["avg_length"]):
            best_params[best_key] = {
                "problem": problem_name,
                "strategy": strategy_name,
                "avg_length": result["avg_length"],
                "avg_gap": result["avg_gap"],
                "avg_time_ms": result["avg_time_ms"],
                "params": params,
                "per_run_lengths": result.get("per_run_lengths", []),
            }
        
        tracker.record(result.get("avg_time_ms", 0.0) / 1000.0, strategy_name, problem_name)
        remain_sec = tracker.estimate_remaining(total - (idx + 1))
        remain = format_time(remain_sec) if remain_sec is not None else "N/A"
        
        sym = "*" if (result.get("avg_gap") or 100) <= 1 else ("+" if (result.get("avg_gap") or 100) <= 5 else "o")
        print(f"  [{idx+1:>3}/{total}] {problem_name:<12} {strategy_name:<8} "
              f"GAP: {result.get('avg_gap', 0):>6.2f}% {sym} {result.get('avg_time_ms', 0):>7.0f}ms "
              f"[ETA: {remain}]", flush=True)

    _run_pool(tuning_tasks, workers, on_result=on_result)

    metadata["best_params"] = best_params
    with open(os.path.join(RESULTS_DIR, "best_params_numba.json"), "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2, ensure_ascii=False)
    save_metadata(METADATA_PATH, metadata)
    return best_params

def _run_benchmark_with_best(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    best_params: Dict[str, Dict[str, Any]],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    benchmark_tasks = []
    for problem in problems:
        for spec in specs:
            best_key = f"{problem.name}::{spec.name}"
            best_entry = best_params.get(best_key)
            if not best_entry:
                continue
            benchmark_tasks.append(
                (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), best_entry["params"], 1, benchmark_runs)
            )

    return _execute_benchmark_tasks(benchmark_tasks, workers, metadata, "FINAL")

def _run_benchmark_direct(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    benchmark_tasks = []
    for problem in problems:
        for spec in specs:
            # Parametreler için DoE tuning yapılmamış, default kullanılıyor
            params = spec.default_params.copy()
            params["algorithm_type"] = spec.algorithm_type
            benchmark_tasks.append(
                (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, 1, benchmark_runs)
            )

    return _execute_benchmark_tasks(benchmark_tasks, workers, metadata, "BENCH")

def _execute_benchmark_tasks(tasks, workers, metadata, stage_label):
    if not tasks:
        return []
        
    csv_path = os.path.join(RESULTS_DIR, "benchmark_progress.csv")
    fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "result_type", "params_json"]

    tracker = ETATracker()
    rows = []

    def on_result(idx, result, total):
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["strategy"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if math.isnan(result["avg_gap"]) else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "result_type": "aggregate",
            "params_json": json.dumps(result["params"], ensure_ascii=False, sort_keys=True),
        }
        rows.append(row)
        _active_results.append(row)
        append_csv_row(csv_path, fields, row)
        
        tracker.record(result.get("avg_time_ms", 0.0) / 1000.0, result["strategy"], result["problem"])
        remain_sec = tracker.estimate_remaining(total - (idx + 1))
        remain = format_time(remain_sec) if remain_sec is not None else "N/A"
        
        sym = "*" if (result.get("avg_gap") or 100) <= 1 else ("+" if (result.get("avg_gap") or 100) <= 5 else "o")
        print(f"  [{idx+1:>3}/{total}] {result['problem']:<12} {result['strategy']:<8} "
              f"GAP: {result.get('avg_gap', 0):>6.2f}% {sym} {result.get('avg_time_ms', 0):>7.0f}ms "
              f"[{stage_label} ETA: {remain}]", flush=True)

    _run_pool(tasks, workers, on_result=on_result)
    
    metadata["results"] = {f"{row['problem']}::{row['strategy']}": row for row in rows}
    save_metadata(METADATA_PATH, metadata)
    return rows

def _write_summary(rows: List[Dict[str, Any]]) -> None:
    path = os.path.join(RESULTS_DIR, "benchmark_summary.csv")
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "problem": row["problem"],
                "strategy": row["strategy"],
                "avg_length": row["avg_length"],
                "avg_gap": row["avg_gap"],
                "avg_time_ms": row["avg_time_ms"],
                "n_runs": row["n_runs"],
            })


def _select_problems_from_args(args, all_problems, interactive: bool = False):
    selector = ProblemSelector(all_problems)

    if args.select:
        return selector.quick_select(args.select)

    if args.problems:
        wanted = {x.strip().lower() for x in args.problems.split(",") if x.strip()}
        return [p for p in all_problems if p.name.lower() in wanted]

    if args.size_limit:
        return [p for p in all_problems if p.dimension <= args.size_limit]

    if interactive:
        return selector.interactive_select()

    return list(all_problems)

def main() -> int:
    global _active_metadata
    
    _ensure_dirs()
    metadata = load_metadata(METADATA_PATH)
    _active_metadata = metadata

    all_specs = _all_strategy_specs()
    selectable_algos = [spec.name for spec in all_specs]
    
    all_problems = load_problems()
    if not all_problems:
        print("[ERROR] Problem bulunamadi. TSPLIB_DIR veya tar.gz kontrol edin.")
        return 1

    parser = argparse.ArgumentParser(description="UniRide Master NUMBA Engine")
    parser.add_argument("--mode", choices=["default", "tuning"], help="Çalışma modu")
    parser.add_argument("--algos", help="Algoritma listesi (virgülle ayrılmış)")
    parser.add_argument("--problems", help="Problem listesi (virgülle ayrılmış)")
    parser.add_argument("--select", help="Universal problem selection syntax")
    parser.add_argument("--runs", type=int, help="Tekrar sayısı")
    parser.add_argument("--size-limit", type=int, help="Problem boyutu limiti")
    args, _ = parser.parse_known_args()

    if args.mode:
        mode = EngineMode(args.mode)
        algos = args.algos.split(",") if args.algos else selectable_algos
        runs = args.runs or 3
        workers = min(cpu_count(), 6)
        
        selected_problems = _select_problems_from_args(args, all_problems)
            
        selected_specs = [s for s in all_specs if s.name in algos]

        
        print(f"=== NON-INTERACTIVE NUMBA BENCHMARK ({mode.value}) ===")
        if mode == EngineMode.TUNING:
            best = _tune_parameters(selected_problems, selected_specs, runs, DOE_MAX_COMBINATIONS, workers, metadata, skip_cached=True)
            rows = _run_benchmark_with_best(selected_problems, selected_specs, best, runs, workers, metadata)
        else:
            rows = _run_benchmark_direct(selected_problems, selected_specs, runs, workers, metadata)
            
        _write_summary(rows)
        return 0

    while True:
        clear_screen()
        log_environment_info()
        
        status = check_algorithms_status(metadata, ALGORITHMS_TO_CHECK)
        if any(s in ("NEW", "CHANGED") for s in status.values()):
            print("[INFO] Algorithm changes detected — cache invalidated.")
            update_algorithm_hashes(metadata, ALGORITHMS_TO_CHECK)
            save_metadata(METADATA_PATH, metadata)

        print("\n" + "="*80)
        print(f"UniRide Master NUMBA Engine v{VERSION}".center(80))
        print("="*80)
        
        print("\n--- ÇALIŞMA MODLARI ---")
        print("  [1] DEFAULT: Direkt Benchmark (Varsayılan Parametrelerle)")
        print("  [2] TUNING: DoE Grid/Fractional Parametre Taraması (Optimizasyon)")
        print("\n--- DİĞER ---")
        print("  [Q] Çıkış")
        
        choice = input("\nSeçiminiz: ").strip().upper()
        
        if choice == 'Q':
            print("Çıkış yapılıyor...")
            return 0
        if choice not in ('1', '2'):
            continue
            
        mode = EngineMode.DEFAULT if choice == '1' else EngineMode.TUNING

        selected_problems = _select_problems_from_args(args, all_problems, interactive=True)

        if not selected_problems:
            print("Seçilen kriterlere uygun problem bulunamadı.")
            input("Devam etmek için Enter'a basın...")
            continue
            
        selected_names = multi_select(selectable_algos, "ALGORİTMA SEÇİMİ")
        if not selected_names:
            continue
            
        selected_specs = [s for s in all_specs if s.name in selected_names]
        
        workers = select_worker_count()
        runs = select_run_count("BENCHMARK", 3)
        
        clear_screen()
        print("=" * 70)
        print(f"BENCHMARK ÖZETİ - {mode.value.upper()}")
        print("=" * 70)
        print(f"Problemler : {len(selected_problems)} adet")
        print(f"Algoritmalar: {', '.join(selected_names)}")
        print(f"Run Sayısı : {runs}")
        print(f"Worker     : {workers}")
        
        if mode == EngineMode.TUNING:
            print(f"Max Komb.  : {DOE_MAX_COMBINATIONS}")
            
        if input("\nBaşlamak için [Y/y], iptal için herhangi bir tuş: ").strip().upper() != 'Y':
            continue
            
        start_time = time.time()
        
        if mode == EngineMode.TUNING:
            print("\n[1/2] DOE TUNING BAŞLIYOR...")
            best_params = _tune_parameters(selected_problems, selected_specs, runs, DOE_MAX_COMBINATIONS, workers, metadata, skip_cached=True)
            
            save_convergence_history(best_params, HISTORIES_DIR)
            
            print("\n[2/2] EN İYİ PARAMETRELERLE BENCHMARK BAŞLIYOR...")
            rows = _run_benchmark_with_best(selected_problems, selected_specs, best_params, runs, workers, metadata)
        else:
            print("\n[START] DİREKT BENCHMARK BAŞLIYOR...")
            rows = _run_benchmark_direct(selected_problems, selected_specs, runs, workers, metadata)
            
        _write_summary(rows)
        
        elapsed = time.time() - start_time
        print(f"\n[OK] İşlem tamamlandı! Toplam Süre: {format_time(elapsed)}")
        
        print("\n=== SONUÇLAR ===")
        print(f"{'Problem':<15} {'Algoritma':<15} {'Uzunluk':<10} {'Gap %':<10} {'Süre (ms)':<10}")
        print("-" * 65)
        for r in rows:
            gap_str = f"{r['avg_gap']:.2f}" if r['avg_gap'] is not None else "N/A"
            print(f"{r['problem']:<15} {r['strategy']:<15} {r['avg_length']:<10.1f} {gap_str:<10} {r['avg_time_ms']:<10.0f}")
            
        input("\nAna menüye dönmek için Enter'a basın...")

if __name__ == "__main__":
    raise SystemExit(main())
