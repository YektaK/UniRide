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

# Windows stdout encoding düzeltmesi — reconfigure() avoids Python 3.14 GC crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
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

from academic_benchmark.param_db import (
    save_entry as _param_db_save,
    get_best_for as _param_db_get_best,
    list_entries as _param_db_list,
    analyze_patterns as _param_db_analyze,
    delete_entry as _param_db_delete,
    set_db_path as _param_db_set,
)
try:
    from academic_benchmark.engine_core import AlgorithmRegistry as _AlgoReg
    _HAS_NUMBA_REGISTRY = True
except ImportError:
    _AlgoReg = None
    _HAS_NUMBA_REGISTRY = False

try:
    from academic_benchmark.benchmark_utils import (
        save_tuning_params_and_solution as _save_best_solution,
    )
except ImportError:
    def _save_best_solution(*a, **kw):
        return -1

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

# --- DB cache integration ---
try:
    from tsplib_manager import (
        get_distance_matrix as _dm_from_cache,
        get_all_problems    as _problems_from_db,
        is_db_populated     as _db_ready,
    )
except ImportError:
    try:
        from academic_benchmark.tsplib_manager import (
            get_distance_matrix as _dm_from_cache,
            get_all_problems    as _problems_from_db,
            is_db_populated     as _db_ready,
        )
    except ImportError:
        _dm_from_cache   = lambda name, **kw: None
        _problems_from_db = lambda **kw: []
        _db_ready        = lambda **kw: False

TSPLIB_DB = os.path.join(_ENGINE_DIR, "tsplib_data", "tsplib.db")

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
    # --- DB fast path ---
    if _db_ready(TSPLIB_DB):
        rows = _problems_from_db(db_path=TSPLIB_DB,
                                 max_dim=size_limit if size_limit > 0 else 99999)
        if rows:
            out = []
            for r in rows:
                dim = r["dimension"]
                cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                out.append(DOEProblem(
                    name=r["name"], dimension=dim, coordinates=r["coordinates"],
                    optimal=r["optimal"], category=cat, source="tsplib"
                ))
            # Append time_matrix JSON problems (existing logic)
            data_dir = os.path.join(_ENGINE_DIR, "data")
            if os.path.exists(data_dir):
                for f in os.listdir(data_dir):
                    if f.endswith(".json") and f != "tuned_parameters_db.json":
                        try:
                            with open(os.path.join(data_dir, f), encoding="utf-8") as fh:
                                data = json.load(fh)
                            if "time_matrix" in data:
                                matrix = data["time_matrix"]
                                name = data.get("name", f.replace(".json", ""))
                                dim = len(matrix)
                                cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                                out.append(DOEProblem(
                                    name=name, dimension=dim,
                                    coordinates=[(0.0, 0.0)] * dim,
                                    optimal=data.get("optimal"), category=cat,
                                    source="time_matrix", is_time_matrix=True,
                                    time_matrix=matrix
                                ))
                        except Exception:
                            continue
            return sorted(out, key=lambda p: p.dimension)
    # --- END DB fast path: fall through to tar.gz logic below ---
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
    if name == "3-OPT-BOUNDED":
        return {
            "max_iterations": [300, 500, 1000],
            "first_improvement": [True, False],
            "window": [8, 12, 20, 50],
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

    # Load correct distance matrix from TSPLib DB cache for non-time-matrix problems.
    # This is CRITICAL: run_single_test falls back to create_np_distance_matrix
    # which only does EUC_2D, producing wrong distances for GEO/ATT/etc problems
    # (e.g. burma14 GEO optimal=3323km would be ~30 using EUC_2D on lat/lon).
    dist_matrix_np = None
    if not is_time_matrix:
        problem_name = problem_dict.get("name", "")
        if problem_name:
            try:
                db_matrix = _dm_from_cache(problem_name, TSPLIB_DB)
                if db_matrix is not None:
                    dist_matrix_np = db_matrix
            except Exception:
                pass

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
            result = run_single_test(effective_problem, strategy_payload, seed, strategy_params,
                                     dist_matrix=dist_matrix_np)
            
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
        np_dm = _dm_from_cache(problem_dict.get("name", ""), db_path=TSPLIB_DB)
        if np_dm is None:
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


# ── DOE Config Management ─────────────────────────────────────────────────────

def _edit_param_space_interactive(spec: StrategySpec) -> Dict[str, List[Any]]:
    """Interactively edit the parameter space for a given strategy spec.

    Delegates to benchmark_utils.edit_param_space for validation logic,
    returning the (possibly edited) space dict.
    """
    space = _build_numba_parameter_space(spec)
    print(f"\n[PARAM] {spec.name} parametre uzayini duzenleyin (Enter = kabul):")
    # Show guidance for 3-opt-bounded window parameter
    if spec.name.upper() == "3-OPT-BOUNDED" and "window" in space:
        print("  [INFO] 3-opt pencere boyutu (window) önerileri:")
        print("    - Simetrik TSP (EUC_2D, ATT): 5-20")
        print("    - Asimetrik TSP (ATSP): 20-50")
        print("    - Varsayilan: 12 (karisik is yükleri için dengeli)")
    result: Dict[str, List[Any]] = {}
    for key, vals in space.items():
        print(f"  {key} = {vals}")
        raw = input(f"    Yeni degerler (virgul) [{','.join(str(v) for v in vals)}]: ").strip()
        if not raw:
            result[key] = vals
            continue
        parts = [x.strip() for x in raw.split(",")]
        new_vals: List[Any] = []
        sample_type = type(vals[0]) if vals else str
        valid = True
        for p in parts:
            if not p:
                continue
            v = validate_param_value(key, p, sample_type)
            if v is None:
                valid = False
                break
            new_vals.append(v)
        if valid and new_vals:
            result[key] = new_vals
        else:
            print(f"    [!] Gecersiz, mevcut korunuyor: {vals}")
            result[key] = vals
    return result


def _validate_tuning_config(config: Dict, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Tuple[bool, str]:
    if not isinstance(config, dict):
        return False, "Config bir dict olmali"
    if config.get("version", 0) != 1:
        return False, f"Desteklenmeyen config versiyonu: {config.get('version')}"
    for section in ("problems", "algorithms", "settings"):
        if section not in config:
            return False, f"{section} alani eksik"
    return True, "OK"


def _save_tuning_config(
    selected_problems: List[DOEProblem],
    selected_specs: List[StrategySpec],
    runs: int,
    workers: int,
    param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    scope_parts = [p.name for p in selected_problems[:3]]
    if len(selected_problems) > 3:
        scope_parts.append(f"and{len(selected_problems)-3}more")
    scope_str = "_".join(scope_parts) if scope_parts else "custom"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{scope_str}.json"
    filepath = os.path.join(CONFIGS_DIR, filename)

    all_problems_full = load_problems()
    problem_indices = []
    for p in selected_problems:
        for idx, ap in enumerate(all_problems_full):
            if ap.name == p.name:
                problem_indices.append(idx + 1)
                break
    all_specs_full = _all_strategy_specs()
    algo_indices = []
    for s in selected_specs:
        for idx, spec in enumerate(all_specs_full):
            if spec.name == s.name:
                algo_indices.append(idx + 1)
                break

    config = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "problems": {"mode": "index", "selection": problem_indices},
        "algorithms": {"selection": algo_indices},
        "settings": {"runs": runs, "workers": workers},
    }
    if param_overrides:
        config["param_overrides"] = param_overrides
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return filepath


def _load_tuning_config(filepath: str, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Optional[Dict[str, Any]]:
    if not os.path.exists(filepath):
        print(f"[HATA] Config dosyasi bulunamadi: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] Config JSON hatasi: {e}")
        return None
    ok, msg = _validate_tuning_config(config, all_problems, all_specs)
    if not ok:
        print(f"[HATA] Config dogrulama basarisiz: {msg}")
        return None
    return config


def _list_tuning_configs() -> List[str]:
    if not os.path.exists(CONFIGS_DIR):
        return []
    return sorted([f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")])


def _resolve_tuning_config(
    cfg: Dict[str, Any],
    all_problems: List[DOEProblem],
    all_specs: List[StrategySpec],
) -> Tuple[List[DOEProblem], List[StrategySpec], Dict[str, Any]]:
    prob_sel = cfg["problems"]
    algo_sel = cfg["algorithms"]
    settings = cfg.get("settings", {})
    if prob_sel.get("mode") == "index":
        indices = [i - 1 for i in prob_sel.get("selection", []) if 0 <= i - 1 < len(all_problems)]
        selected_problems = [all_problems[i] for i in indices]
    else:
        selected_problems = list(all_problems)
    algo_indices = [i - 1 for i in algo_sel.get("selection", []) if 0 <= i - 1 < len(all_specs)]
    selected_specs = [all_specs[i] for i in algo_indices]
    return selected_problems, selected_specs, settings


# ── Tuning Engine ─────────────────────────────────────────────────────────────

def _tune_parameters(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    n_runs: int,
    max_combinations: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool,
    use_fractional: bool = False,
    param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    completed = _load_tuning_cache()
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})
    tuning_tasks = []

    for problem in problems:
        for spec in specs:
            space = _build_numba_parameter_space(spec)
            # Merge any runtime param_overrides for this algorithm
            if param_overrides and spec.name in param_overrides:
                for key, vals in param_overrides[spec.name].items():
                    if key in space:
                        space[key] = vals
            strategy = "fractional_fallback" if use_fractional else "sequential"
            combos = generate_combinations(space, max_combinations, strategy=strategy)
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

    print(f"\n[START] NUMBA TUNING Mod Basliyor ({len(tuning_tasks)} kombinasyon, {workers} worker)...")

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
    fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "result_type", "params_json", "gap_type"]

    tracker = ETATracker()
    rows = []

    def on_result(idx, result, total):
        optimal = result.get("optimal")
        gap_type_val = "optimal" if (optimal and optimal > 0) else "unknown"
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
            "gap_type": gap_type_val,
        }
        rows.append(row)
        _active_results.append(row)
        append_csv_row(csv_path, fields, row)
        
        tracker.record(result.get("avg_time_ms", 0.0) / 1000.0, result["strategy"], result["problem"])
        remain_sec = tracker.estimate_remaining(total - (idx + 1))
        remain = format_time(remain_sec) if remain_sec is not None else "N/A"
        
        sym = "*" if (result.get("avg_gap") or 100) <= 1 else ("+" if (result.get("avg_gap") or 100) <= 5 else "o")
        sys.stdout.write(f"\r  [{idx+1:>3}/{total}] {result['problem']:<12} {result['strategy']:<8} "
                         f"GAP: {result.get('avg_gap', 0):>6.2f}% {sym} {result.get('avg_time_ms', 0):>7.0f}ms "
                         f"[{stage_label} ETA: {remain:<9}]")
        sys.stdout.flush()

    _run_pool(tasks, workers, on_result=on_result)
    print()
    
    metadata["results"] = {f"{row['problem']}::{row['strategy']}": row for row in rows}
    save_metadata(METADATA_PATH, metadata)
    return rows

def _write_summary(rows: List[Dict[str, Any]]) -> None:
    path = os.path.join(RESULTS_DIR, "benchmark_summary.csv")
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "gap_type"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "problem": row["problem"],
                "strategy": row["strategy"],
                "avg_length": row["avg_length"],
                "avg_gap": row["avg_gap"],
                "avg_time_ms": row["avg_time_ms"],
                "n_runs": row["n_runs"],
                "gap_type": row.get("gap_type", "unknown"),
            })


def _run_interactive_tuning_flow(
    selected_problems: List[DOEProblem],
    selected_specs: List[StrategySpec],
    runs: int,
    workers: int,
    metadata: Dict[str, Any],
    use_fractional: bool = False,
    param_overrides: Optional[Dict[str, List[Any]]] = None,
    all_problems: Optional[List[DOEProblem]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Tuning flow: tune, save to param DB, optionally benchmark on different problems.
    Returns best_params dict."""
    mode_raw = input("Tuning modu: [G]rid search / [B]ayesian (Optuna) [G]: ").strip().upper()
    use_bayesian = (mode_raw == 'B')

    if use_bayesian:
        _run_optuna_tuning_flow(selected_problems, selected_specs, runs, workers, metadata,
                                param_overrides=param_overrides)
        # For bayesian, best params handled inside; return metadata defaults
        best_params = metadata.get("best_params", {})
    else:
        print("\n[START] NUMBA TUNING Mod Basliyor...")
        best_params = _tune_parameters(
            selected_problems, selected_specs, runs, DOE_MAX_COMBINATIONS, workers, metadata,
            skip_cached=True, use_fractional=use_fractional, param_overrides=param_overrides,
        )
        save_convergence_history(best_params, HISTORIES_DIR)

    # Save best params to persistent parameter DB
    saved = _save_best_to_param_db(best_params, selected_problems, selected_specs)
    print(f"[PARAM_DB] {saved} parametre seti kaydedildi.")

    cfg_path = _save_tuning_config(selected_problems, selected_specs, runs, workers,
                                   param_overrides=param_overrides)
    print(f"[CONFIG] Tuning config kaydedildi: {cfg_path}")

    # Ask whether to run benchmark (possibly on different problems)
    bm_raw = input("\nBenchmark da kosmak ister misiniz? [E/H]: ").strip().upper()
    if bm_raw != 'E':
        print(f"\n[OK] Tuning tamamlandi! (Benchmark atlandi)")
        return best_params

    # Select benchmark problems (can differ from training)
    if all_problems:
        print("\nBenchmark icin problem secimi (Egitim problemlerinden farkli olabilir):")
        bm_probs = _select_benchmark_problems_interactive(all_problems)
    else:
        bm_probs = selected_problems

    if not bm_probs:
        bm_probs = selected_problems

    bm_runs_raw = input(f"Benchmark tekrar sayisi [varsayilan {runs}]: ").strip()
    bm_runs = int(bm_runs_raw) if bm_runs_raw.isdigit() else runs

    print(f"\n[2/2] EN IYI PARAMETRELERLE BENCHMARK BASLIYOR ({len(bm_probs)} problem)...")
    rows = _run_benchmark_with_best(bm_probs, selected_specs, best_params, bm_runs, workers, metadata)
    _write_summary(rows)

    print(f"\n[OK] Tuning + Benchmark tamamlandi!")
    print("\n=== SONUÇLAR (En Iyi Parametrelerle) ===")
    print(f"{'Problem':<15} {'Algoritma':<15} {'Uzunluk':<10} {'Gap %':<10} {'Sure (ms)':<10}")
    print("-" * 65)
    for r in rows:
        gap_str = f"{r['avg_gap']:.2f}" if r['avg_gap'] is not None else "N/A"
        print(f"{r['problem']:<15} {r['strategy']:<15} {r['avg_length']:<10.1f} {gap_str:<10} {r['avg_time_ms']:<10.0f}")

    return best_params


# ── Optuna Bayesian Tuning ────────────────────────────────────────────────────

def _build_optuna_search_space(spec: StrategySpec, trial: Any) -> Dict[str, Any]:
    """Map parameter space to Optuna suggest_* calls."""
    params = {}
    name = spec.name.upper()
    if name == "GA":
        params["pop_size"] = trial.suggest_int("pop_size", 80, 150)
        params["generations"] = trial.suggest_int("generations", 200, 500)
        params["mutation_rate"] = trial.suggest_float("mutation_rate", 0.05, 0.20)
        params["elite_size"] = trial.suggest_int("elite_size", 2, 8)
        params["crossover_rate"] = trial.suggest_float("crossover_rate", 0.75, 0.95)
    elif name == "PSO":
        params["swarm_size"] = trial.suggest_int("swarm_size", 30, 120)
        params["iterations"] = trial.suggest_int("iterations", 200, 500)
        params["w"] = trial.suggest_float("w", 0.4, 0.9)
        params["c1"] = trial.suggest_float("c1", 1.0, 2.5)
        params["c2"] = trial.suggest_float("c2", 1.0, 2.5)
    elif name == "GWO":
        params["pack_size"] = trial.suggest_int("pack_size", 20, 120)
        params["iterations"] = trial.suggest_int("iterations", 200, 500)
    elif name == "HHO":
        params["hawks"] = trial.suggest_int("hawks", 20, 120)
        params["iterations"] = trial.suggest_int("iterations", 200, 500)
    elif name == "B-PSO":
        params["swarm_size"] = trial.suggest_int("swarm_size", 20, 80)
        params["max_iterations"] = trial.suggest_int("max_iterations", 200, 500)
        params["inertia_weight"] = trial.suggest_float("inertia_weight", 0.4, 0.9)
        params["cognitive_coeff"] = trial.suggest_float("cognitive_coeff", 1.0, 2.5)
        params["social_coeff"] = trial.suggest_float("social_coeff", 1.0, 2.5)
        params["max_velocity_size"] = trial.suggest_int("max_velocity_size", 3, 10)
    elif name == "B-GA":
        params["population_size"] = trial.suggest_int("population_size", 50, 150)
        params["generations"] = trial.suggest_int("generations", 200, 500)
        params["crossover_rate"] = trial.suggest_float("crossover_rate", 0.75, 0.95)
        params["mutation_rate"] = trial.suggest_float("mutation_rate", 0.05, 0.25)
        params["elite_count"] = trial.suggest_int("elite_count", 1, 6)
        params["tournament_size"] = trial.suggest_int("tournament_size", 2, 6)
    else:
        params["max_iterations"] = trial.suggest_int("max_iterations", 100, 1000)
    return params


def _optuna_objective(
    trial: Any,
    problem: DOEProblem,
    spec: StrategySpec,
    n_runs: int,
) -> float:
    params = spec.default_params.copy()
    params.update(_build_optuna_search_space(spec, trial))
    params["algorithm_type"] = spec.algorithm_type

    task = (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, 1, n_runs)
    try:
        result = _evaluate_param_combo(task)
        avg_gap = result.get("avg_gap")
        if avg_gap is None or math.isnan(avg_gap):
            return float("inf")
        return float(avg_gap)
    except Exception:
        return float("inf")


def _run_optuna_tuning_flow(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    n_runs: int,
    workers: int,
    metadata: Dict[str, Any],
    param_overrides: Optional[Dict[str, List[Any]]] = None,
) -> None:
    import optuna

    for problem in problems:
        for spec in specs:
            print(f"\n[OPTUNA] {problem.name} / {spec.name} — basliyor...")
            study = optuna.create_study(
                direction="minimize",
                study_name=f"{problem.name}_{spec.name}",
                sampler=optuna.samplers.TPESampler(seed=42),
            )

            def make_objective(p, s):
                def objective(trial):
                    return _optuna_objective(trial, p, s, n_runs)
                return objective

            study.optimize(make_objective(problem, spec), n_trials=DOE_MAX_COMBINATIONS)

            print(f"\n[OPTUNA] {problem.name} / {spec.name} — En iyi gap: {study.best_value:.2f}%")
            print(f"  En iyi parametreler: {study.best_params}")

    print("\n[OPTUNA] Tum tuning tamamlandi.")


# ── Param DB Integration ──────────────────────────────────────────────────────

def _save_best_to_param_db(
    best_params: Dict[str, Dict[str, Any]],
    problems: List[DOEProblem],
    specs: List[StrategySpec],
) -> int:
    """Save best tuning results to the persistent parameter database.
    Also saves to the tsplib.db best_solutions table for cross-engine queries.
    Returns number of entries saved.
    """
    saved = 0
    problem_map = {p.name: p for p in problems}
    for key, entry in best_params.items():
        parts = key.split("::", 1)
        if len(parts) != 2:
            continue
        prob_name, algo_name = parts
        prob = problem_map.get(prob_name)
        if not prob:
            continue
        params = entry.get("params", {})
        best_score = entry.get("avg_length", float("inf"))
        gap = entry.get("avg_gap", float("nan"))
        runs = entry.get("n_runs", 0) or entry.get("completed", 0)
        if not runs:
            runs = 3
        # Save to param_db (legacy)
        _param_db_save(
            problem=prob_name,
            algorithm=algo_name,
            params=params,
            best_score=best_score,
            gap=gap if not math.isnan(gap) else 0.0,
            runs=runs,
            dimension=prob.dimension,
            category=prob.category,
        )
        # Save to best_solutions table (cross-engine)
        _save_best_solution(
            problem_name=prob_name,
            algorithm=algo_name,
            params=params,
            tour=[],
            tour_length=float(best_score),
            gap=float(gap) if not math.isnan(gap) else 0.0,
            db_path=TSPLIB_DB,
        )
        saved += 1
    return saved


def _manual_param_entry_interactive(specs: List[StrategySpec]) -> Dict[str, Dict[str, Any]]:
    """Interactive manual parameter entry like bildiri2026 Stage 1.
    Shows defaults → asks for edits.
    Returns {spec.name: {param_key: value, ...}, ...}
    """
    result: Dict[str, Dict[str, Any]] = {}
    print("\n" + "=" * 70)
    print("MANUEL PARAMETRE GIRISI")
    print("Her parametre icin varsayilan deger gosterilir.")
    print("Degistirmek istemiyorsaniz [ENTER] tusuna basin.")
    print("=" * 70)
    for spec in specs:
        print(f"\n--- {spec.name} ---")
        manual_params = {}
        space = _build_numba_parameter_space(spec)
        current_params = spec.default_params.copy()
        # Show guidance for 3-opt-bounded window parameter
        if spec.name.upper() == "3-OPT-BOUNDED" and "window" in space:
            print("  [INFO] 3-opt pencere boyutu (window) önerileri:")
            print("    - Simetrik TSP (EUC_2D, ATT): 5-20")
            print("    - Asimetrik TSP (ATSP): 20-50")
            print("    - Varsayilan: 12 (karisik is yükleri için dengeli)")
        print(f"  Varsayilan parametreler: {current_params}")
        edit_raw = input("  Bu algoritma icin parametreleri degistirmek ister misiniz? [e/H]: ").strip().upper()
        if edit_raw != 'E':
            result[spec.name] = current_params
            continue
        # Show each param from the space and let user enter a single value
        for key, vals in space.items():
            default_val = vals[0] if vals else current_params.get(key)
            raw = input(f"  {key} (oneri: {default_val}) = ").strip()
            if raw:
                try:
                    if isinstance(default_val, bool):
                        manual_params[key] = raw.lower() in ('true', 't', '1', 'e', 'evet')
                    elif isinstance(default_val, int):
                        manual_params[key] = int(raw)
                    elif isinstance(default_val, float):
                        manual_params[key] = float(raw)
                    else:
                        manual_params[key] = raw
                except ValueError:
                    print(f"    [!] Gecersiz deger, varsayilan ({default_val}) kullanildi.")
                    manual_params[key] = default_val
            else:
                manual_params[key] = default_val
        # Also allow setting params not in the space (algorithm_type etc.)
        for key in current_params:
            if key not in manual_params:
                manual_params[key] = current_params[key]
        result[spec.name] = manual_params
    return result


def _run_benchmark_with_params(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    custom_params: Dict[str, Dict[str, Any]],
    runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run benchmark with explicitly provided parameters.
    custom_params: {spec.name: {param_key: value, ...}}
    """
    benchmark_tasks = []
    for problem in problems:
        for spec in specs:
            params = spec.default_params.copy()
            # Merge custom params if available
            if spec.name in custom_params:
                params.update(custom_params[spec.name])
            params["algorithm_type"] = spec.algorithm_type
            benchmark_tasks.append(
                (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, 1, runs)
            )
    return _execute_benchmark_tasks(benchmark_tasks, workers, metadata, "BENCH")


def _load_params_from_db_interactive(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
) -> Dict[str, Dict[str, Any]]:
    """Interactive selection: for each (problem, algorithm) pair, load best params from DB.
    Returns {spec.name: {param_key: value, ...}} merging defaults with loaded values.
    """
    db_entries = _param_db_list()
    if not db_entries:
        print("[INFO] Parametre DB'sinde kayit bulunamadi. Varsayilan parametreler kullanilacak.")
        return {}

    print("\n" + "=" * 70)
    print("PARAMETRE DB'DEN YUKLEME")
    print("=" * 70)
    for prob in problems:
        for spec in specs:
            best = _param_db_get_best(prob.name, spec.name)
            if best:
                print(f"  {prob.name} / {spec.name}: best_score={best['best_score']:.1f}, params={best['params']}")
            else:
                print(f"  {prob.name} / {spec.name}: (DB'de kayit yok, varsayilan kullanilacak)")

    raw = input("\nDB'deki parametreleri kullanmak icin [E], kendi girmek icin [M], varsayilan icin [D]: ").strip().upper()
    if raw == 'E':
        result: Dict[str, Dict[str, Any]] = {}
        for prob in problems:
            for spec in specs:
                best = _param_db_get_best(prob.name, spec.name)
                if best:
                    result[spec.name] = best["params"]
                else:
                    result[spec.name] = spec.default_params.copy()
                    result[spec.name]["algorithm_type"] = spec.algorithm_type
        return result
    elif raw == 'M':
        return _manual_param_entry_interactive(specs)
    else:
        result = {}
        for spec in specs:
            params = spec.default_params.copy()
            params["algorithm_type"] = spec.algorithm_type
            result[spec.name] = params
        return result


def _select_benchmark_problems_interactive(all_problems: List[DOEProblem]) -> List[DOEProblem]:
    """Interactive problem selection for benchmark (can differ from tuning problems)."""
    selector = ProblemSelector(all_problems)
    return selector.interactive_select()


# ── AlgorithmRegistry Registration ─────────────────────────────────────────────

def _make_numba_executor(spec_name: str, spec_payload: Any):
    """Create AlgorithmRegistry-compatible executor for a numba strategy."""
    def executor(problem, params, seed, run_idx):
        from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, TSPLIBProblem
        tsp_prob = TSPLIBProblem(
            name=problem.name, dimension=problem.dimension,
            optimal=problem.optimal or 0,
            coordinates=problem.coordinates,
            category=getattr(problem, 'category', 'small'),
            source=getattr(problem, 'source', 'tsplib'),
        )
        if hasattr(problem, 'dist_matrix') and problem.dist_matrix is not None:
            result = run_single_test(tsp_prob, spec_payload, seed, params, dist_matrix=problem.dist_matrix)
        else:
            matrix = _dm_from_cache(problem.name, TSPLIB_DB)
            result = run_single_test(tsp_prob, spec_payload, seed, params, dist_matrix=matrix)
        # Tour validation: ensure permutation is valid
        tour = result.get("tour", [])
        n = problem.dimension
        if tour and len(tour) == n:
            assert len(set(tour)) == n, f"[{spec_name}] Invalid tour: duplicate nodes in {tour}"
            assert min(tour) == 0, f"[{spec_name}] Invalid tour: min node {min(tour)} != 0"
            assert max(tour) == n - 1, f"[{spec_name}] Invalid tour: max node {max(tour)} != {n-1}"
        from academic_benchmark.engine_core import RunResult
        return RunResult(
            problem=problem.name, algorithm=spec_name,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=int(result["tour_length"]),
            gap_pct=result.get("gap"), elapsed_sec=result.get("time_ms", 0) / 1000.0,
            iterations=result.get("iterations", 0),
            tour=tour if tour else None,
        )
    executor.__name__ = f"numba_{spec_name.lower().replace('-', '_')}_executor"
    return executor

def _make_numba_warmup_fn(strategy_payload):
    """Create a warmup function that JIT-compiles Numba kernels on a small problem."""
    def warmup_fn(probe_problem):
        try:
            from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, TSPLIBProblem
            tsp_prob = TSPLIBProblem(
                name=probe_problem.name, dimension=probe_problem.dimension,
                optimal=probe_problem.optimal or 0,
                coordinates=probe_problem.coordinates,
                category=getattr(probe_problem, 'category', 'small'),
                source=getattr(probe_problem, 'source', 'tsplib'),
            )
            run_single_test(tsp_prob, strategy_payload, 42, {"max_iterations": 1})
        except Exception:
            pass
    warmup_fn.__name__ = f"numba_{strategy_payload}_warmup"
    return warmup_fn

if _HAS_NUMBA_REGISTRY:
    for _sname, _spayload, _sparams in STRATEGIES:
        _algoname = f"Numba-{_sname}"
        _AlgoReg.register(_algoname)(_make_numba_executor(_algoname, _spayload))
        _spec = _normalize_strategy_entry((_sname, _spayload, _sparams))
        _AlgoReg.register_param_space(_algoname)(lambda s=_spec: _build_numba_parameter_space(s))
        _AlgoReg.register_warmup(_algoname)(_make_numba_warmup_fn(_spayload))
    for _sname, _spayload, _sparams in BILDIRI_STRATEGIES:
        _AlgoReg.register(_sname)(_make_numba_executor(_sname, _spayload))
        _spec = StrategySpec(name=_sname, payload=_spayload, default_params=_sparams, algorithm_type="bildiri_meta")
        _AlgoReg.register_param_space(_sname)(lambda s=_spec: _build_numba_parameter_space(s))
        _AlgoReg.register_warmup(_sname)(_make_numba_warmup_fn(_spayload))


def _param_db_menu() -> None:
    """Sub-menu for parameter database management."""
    while True:
        clear_screen()
        print("\n" + "="*60)
        print("PARAMETRE DB YONETIMI".center(60))
        print("="*60)
        print("  [1] Kayitli parametreleri listele")
        print("  [2] Analiz (problem boyutuna gore ortak parametreler)")
        print("  [3] Kayit sil")
        print("  [Q] Ana menuye don")
        choice = input("\nSeciminiz: ").strip().upper()

        if choice == 'Q':
            break
        elif choice == '1':
            entries = _param_db_list()
            if not entries:
                print("[INFO] Parametre DB'si bos.")
            else:
                print(f"\n{'ID':>3} {'Tarih':<20} {'Problem':<12} {'Algoritma':<8} {'Skor':<10} {'Gap%':<8} {'Boyut':<6}")
                print("-" * 70)
                for e in entries:
                    gap_str = f"{e.get('gap', 0):.2f}" if e.get('gap') is not None else "N/A"
                    print(f"{e['id']:>3} {e.get('timestamp', '?'):<20} {e['problem']:<12} {e['algorithm']:<8} {e.get('best_score', 0):<10.1f} {gap_str:<8} {e.get('dimension', 0):<6}")
            input("\nDevam icin Enter...")
        elif choice == '2':
            analysis = _param_db_analyze()
            print(f"\n{analysis}")
            input("\nDevam icin Enter...")
        elif choice == '3':
            raw = input("Silmek istediginiz kayit ID'si: ").strip()
            if raw.isdigit():
                if _param_db_delete(int(raw)):
                    print("[OK] Kayit silindi.")
                else:
                    print("[HATA] Kayit bulunamadi.")
            input("Devam icin Enter...")


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
    _param_db_set(os.path.join(BENCHMARK_DB, "param_db.json"))
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
    parser.add_argument("--config", help="Config dosyasi yolu (DOE ayarlarini yukler)")
    parser.add_argument("--fractional-fallback", action="store_true", help="Fractional fallback stratejisi")
    parser.add_argument("--edit-params", action="store_true", help="Tuning öncesi parametre uzayini duzenle")
    args, _ = parser.parse_known_args()

    # If --config is provided, load tuning config and route to tuning mode
    if args.config:
        cfg = _load_tuning_config(args.config, all_problems, all_specs)
        if not cfg:
            return 1
        selected_problems, selected_specs, settings = _resolve_tuning_config(cfg, all_problems, all_specs)
        mode = EngineMode.TUNING
        runs = settings.get("runs", args.runs or 3)
        workers = settings.get("workers", min(cpu_count(), 6))
        print(f"=== CONFIG MODE: {args.config} ===")
        print(f"   Problemler: {len(selected_problems)}, Algoritmalar: {len(selected_specs)}, Runs: {runs}")
        best = _tune_parameters(selected_problems, selected_specs, runs, DOE_MAX_COMBINATIONS, workers, metadata,
                                skip_cached=True, use_fractional=args.fractional_fallback)
        save_convergence_history(best, HISTORIES_DIR)
        rows = _run_benchmark_with_best(selected_problems, selected_specs, best, runs, workers, metadata)
        _write_summary(rows)
        return 0

    if args.mode:
        mode = EngineMode(args.mode)
        algos = args.algos.split(",") if args.algos else selectable_algos
        runs = args.runs or 3
        workers = min(cpu_count(), 6)
        
        selected_problems = _select_problems_from_args(args, all_problems)
            
        selected_specs = [s for s in all_specs if s.name in algos]

        
        print(f"=== NON-INTERACTIVE NUMBA BENCHMARK ({mode.value}) ===")
        if mode == EngineMode.TUNING:
            # Optionally edit parameter spaces before tuning
            param_overrides = None
            if args.edit_params:
                param_overrides = {}
                for spec in selected_specs:
                    edited = _edit_param_space_interactive(spec)
                    param_overrides[spec.name] = edited
            best = _tune_parameters(selected_problems, selected_specs, runs, DOE_MAX_COMBINATIONS, workers, metadata,
                                    skip_cached=True, use_fractional=args.fractional_fallback,
                                    param_overrides=param_overrides)
            save_convergence_history(best, HISTORIES_DIR)
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
        
        print("\n--- CALISMA MODLARI ---")
        print("  [1] PARAMETRE TUNING (DOE/Bayesian)")
        print("      -> Tuning yap, en iyi parametreleri DB'ye kaydet")
        print("      -> Sonra farkli problemlerde benchmark kos (istege bagli)")
        print("  [2] BENCHMARK")
        print("      -> Secilen problemlerde, istedigin parametrelerle kos")
        print("      -> Kaynak: [DB'den en iyi] / [Manuel] / [Varsayilan]")
        print("  [3] HIZLI BENCHMARK (Varsayilan parametrelerle, eski DEFAULT)")
        print("\n--- YAPILANDIRMA & ARAÇLAR ---")
        print("  [4] Config Yukle (Kaydedilmis DOE ayarlarini yukle)")
        print("  [5] Parametre DB Araclari (Listele, Analiz, Sil)")
        print("\n--- DIGER ---")
        print("  [D] DASHBOARD (Streamlit ile Sonuclari Gorsellestir)")
        print("  [Q] Cikis")
        
        choice = input("\nSeçiminiz: ").strip().upper()
        
        if choice == 'Q':
            print("Cikis yapiliyor...")
            return 0
        if choice == 'D':
            import subprocess
            print("\nDashboard aciliyor... Tarayicinizda http://localhost:8501 adresine gidin.")
            print("Durdurmak icin Ctrl+C basin.")
            try:
                subprocess.run(["streamlit", "run", str(Path(__file__).resolve().parent / "dashboard.py")])
            except KeyboardInterrupt:
                print("\nDashboard kapatildi.")
            input("Devam etmek icin Enter...")
            continue

        # ── 4: Load Config ────────────────────────────────────────────────
        if choice == '4':
            configs = _list_tuning_configs()
            if not configs:
                print("[HATA] Kayitli config dosyasi bulunamadi.")
                input("Devam etmek icin Enter'a basin...")
                continue
            print("\n--- Mevcut Config Dosyalari ---")
            for idx, c in enumerate(configs, 1):
                print(f"  [{idx}] {c}")
            raw = input("\nSeciminiz: ").strip()
            if not raw.isdigit() or int(raw) < 1 or int(raw) > len(configs):
                print("[HATA] Gecersiz secim.")
                input("Devam etmek icin Enter'a basin...")
                continue
            cfg_path = os.path.join(CONFIGS_DIR, configs[int(raw) - 1])
            cfg = _load_tuning_config(cfg_path, all_problems, all_specs)
            if not cfg:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_problems, selected_specs, settings = _resolve_tuning_config(cfg, all_problems, all_specs)
            runs = settings.get("runs", 3)
            workers = settings.get("workers", min(cpu_count(), 6))
            print(f"\n[CONFIG] Config yuklendi: {configs[int(raw) - 1]}")
            print(f"   Problemler: {len(selected_problems)}, Algoritmalar: {len(selected_specs)}")
            print(f"   Runs: {runs}, Workers: {workers}")

            _run_interactive_tuning_flow(selected_problems, selected_specs, runs, workers, metadata,
                                         all_problems=all_problems)
            continue

        # ── 5: Param DB Tools ─────────────────────────────────────────────
        if choice == '5':
            _param_db_menu()
            continue

        if choice not in ('1', '2', '3'):
            continue

        # ── Common: Problem + Algorithm Selection ─────────────────────────
        if choice == '1':
            print("\n[1] PARAMETRE TUNING")
            print("Egitim problemlerini secin (tuning bu problemler uzerinde yapilacak):")
        elif choice == '2':
            print("\n[2] BENCHMARK")
            print("Benchmark yapilacak problemleri secin:")
        else:
            print("\n[3] HIZLI BENCHMARK (Varsayilan Parametrelerle)")
            print("Benchmark yapilacak problemleri secin:")

        selected_problems = _select_problems_from_args(args, all_problems, interactive=True)

        if not selected_problems:
            print("Secilen kriterlere uygun problem bulunamadi.")
            input("Devam etmek icin Enter'a basin...")
            continue

        selected_names = multi_select(selectable_algos, "ALGORITMA SECIMI")
        if not selected_names:
            continue

        selected_specs = [s for s in all_specs if s.name in selected_names]

        workers = select_worker_count()
        runs = select_run_count("BENCHMARK", 3)

        # ── Choice 1: Tuning Flow ─────────────────────────────────────────
        if choice == '1':
            use_fractional = False
            param_overrides = None
            frac_raw = input("Fractional fallback kullanilsin mi? (full factorial yerine random ornekleme) [e/H]: ").strip().upper()
            use_fractional = (frac_raw == 'E')
            edit_raw = input("Parametre uzayini duzenlemek ister misiniz? [e/H]: ").strip().upper()
            if edit_raw == 'E':
                param_overrides = {}
                for spec in selected_specs:
                    edited = _edit_param_space_interactive(spec)
                    param_overrides[spec.name] = edited

            clear_screen()
            print("=" * 70)
            print("TUNING OZETI")
            print("=" * 70)
            print(f"Egitim Problemleri : {len(selected_problems)} adet")
            print(f"Algoritmalar       : {', '.join(selected_names)}")
            print(f"Run Sayisi         : {runs}")
            print(f"Worker             : {workers}")
            print(f"Max Komb.          : {DOE_MAX_COMBINATIONS}")
            print(f"Strateji           : {'Fractional' if use_fractional else 'Sequential'}")
            if param_overrides:
                print(f"Param. Ed.         : {' '.join(param_overrides.keys())}")

            if input("\nBaslamak icin [Y/y]: ").strip().upper() != 'Y':
                continue

            start_time = time.time()
            _run_interactive_tuning_flow(
                selected_problems, selected_specs, runs, workers, metadata,
                use_fractional=use_fractional, param_overrides=param_overrides,
                all_problems=all_problems,
            )
            elapsed = time.time() - start_time
            print(f"\n[OK] Toplam sure: {format_time(elapsed)}")
            input("\nDevam etmek icin Enter'a basin...")
            continue

        # ── Choice 2: Benchmark with Param Source Selection ───────────────
        if choice == '2':
            print("\nParametre Kaynagi Secimi:")
            print("  [B] En iyi parametreleri DB'den yukle")
            print("  [M] Manuel parametre girisi (bildiri2026 stili)")
            print("  [D] Varsayilan parametreler")
            ps_raw = input("Seciminiz [B/M/D]: ").strip().upper()

            custom_params = None
            if ps_raw == 'B':
                custom_params = _load_params_from_db_interactive(selected_problems, selected_specs)
            elif ps_raw == 'M':
                custom_params = _manual_param_entry_interactive(selected_specs)

            clear_screen()
            print("=" * 70)
            print("BENCHMARK OZETI")
            print("=" * 70)
            print(f"Problemler : {len(selected_problems)} adet")
            print(f"Algoritmalar: {', '.join(selected_names)}")
            print(f"Run Sayisi : {runs}")
            print(f"Worker     : {workers}")
            print(f"Parametre  : {'DB yuklendi' if ps_raw == 'B' else 'Manuel' if ps_raw == 'M' else 'Varsayilan'}")

            if input("\nBaslamak icin [Y/y]: ").strip().upper() != 'Y':
                continue

            start_time = time.time()
            print("\n[START] BENCHMARK BASLIYOR...")
            if custom_params is not None:
                rows = _run_benchmark_with_params(selected_problems, selected_specs, custom_params, runs, workers, metadata)
            else:
                rows = _run_benchmark_direct(selected_problems, selected_specs, runs, workers, metadata)
            _write_summary(rows)

            elapsed = time.time() - start_time
            print(f"\n[OK] Islem tamamlandi! Toplam Sure: {format_time(elapsed)}")
            print("\n=== SONUCLAR ===")
            print(f"{'Problem':<15} {'Algoritma':<15} {'Uzunluk':<10} {'Gap %':<10} {'Sure (ms)':<10}")
            print("-" * 65)
            for r in rows:
                gap_str = f"{r['avg_gap']:.2f}" if r['avg_gap'] is not None else "N/A"
                print(f"{r['problem']:<15} {r['strategy']:<15} {r['avg_length']:<10.1f} {gap_str:<10} {r['avg_time_ms']:<10.0f}")

            input("\nDevam etmek icin Enter'a basin...")
            continue

        # ── Choice 3: Quick Default Benchmark (old DEFAULT) ───────────────
        if choice == '3':
            clear_screen()
            print("=" * 70)
            print("HIZLI BENCHMARK OZETI - VARSAYILAN PARAMETRELER")
            print("=" * 70)
            print(f"Problemler : {len(selected_problems)} adet")
            print(f"Algoritmalar: {', '.join(selected_names)}")
            print(f"Run Sayisi : {runs}")
            print(f"Worker     : {workers}")

            if input("\nBaslamak icin [Y/y], iptal icin herhangi bir tus: ").strip().upper() != 'Y':
                continue

            start_time = time.time()
            print("\n[START] DIREKT BENCHMARK BASLIYOR...")
            rows = _run_benchmark_direct(selected_problems, selected_specs, runs, workers, metadata)
            _write_summary(rows)

            elapsed = time.time() - start_time
            print(f"\n[OK] Islem tamamlandi! Toplam Sure: {format_time(elapsed)}")
            print("\n=== SONUCLAR ===")
            print(f"{'Problem':<15} {'Algoritma':<15} {'Uzunluk':<10} {'Gap %':<10} {'Sure (ms)':<10}")
            print("-" * 65)
            for r in rows:
                gap_str = f"{r['avg_gap']:.2f}" if r['avg_gap'] is not None else "N/A"
                print(f"{r['problem']:<15} {r['strategy']:<15} {r['avg_length']:<10.1f} {gap_str:<10} {r['avg_time_ms']:<10.0f}")

            input("\nAna menuye donmek icin Enter'a basin...")
            continue

        # Fallback (should not reach here)
        input("Devam etmek icin Enter'a basin...")

if __name__ == "__main__":
    raise SystemExit(main())
