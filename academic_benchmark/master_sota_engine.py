#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Master SOTA Engine — E²BSO / R²DMA / P-AOEA
=====================================================

Konsolidasyon FAZ 2 çıktısı. 6 legacy dosyadan alınan en iyi özellikler:
  - run_sota_benchmark.py       → Temiz worker, box-drawing summary, ETATracker
  - run_smart_benchmark_sota.py → tar.gz loader, hash tracking, smart cache, CLI
  - run_smart_benchmark_sota_doe.py → DoE tuning motor, parametre uzayı

İki mod:
  DEFAULT  — Adaptif sabit parametrelerle direkt benchmark
  TUNING   — DoE Grid/Fractional parametre tarama → en iyi parametrelerle run

Kullanım:
    python academic_benchmark/master_sota_engine.py
    python academic_benchmark/master_sota_engine.py --mode default --problems berlin52,eil51 --runs 5
    python academic_benchmark/master_sota_engine.py --mode tuning --algos E2BSO-TSP --size-limit 100
"""

# ── Standart kütüphaneler ─────────────────────────────────────────────────────
import argparse
import concurrent.futures
import csv
import json
import gzip

import io
import math
import os

# OpenBLAS / NumPy multiprocessing çökmesini engellemek için
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

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
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from pathlib import Path

# Windows stdout encoding düzeltmesi — reconfigure() avoids Python 3.14 GC crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Proje root'unu Python path'e ekle (import academic_benchmark.sota_tsp için)
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── benchmark_utils import ────────────────────────────────────────────────────
try:
    from benchmark_utils import (
        ETATracker,
        TSPLIB_OPTIMALS,
        append_csv_row,
        check_algorithms_status,
        clear_screen as _clear,
        compute_population_diversity,
        format_time,
        generate_combinations,
        get_cpu_info,
        get_file_hash,
        load_metadata,
        log_environment_info as _log_environment_info,
        make_deterministic_seed,
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
        resolve_dist_matrix as _resolve_dist_matrix,
        save_tuning_params_and_solution as _save_best_solution,
        load_best_params as _load_best_params,
        get_bsf_tracker,
        compute_gap,
    )
except ModuleNotFoundError:
    from academic_benchmark.benchmark_utils import (
        ETATracker,
        TSPLIB_OPTIMALS,
        append_csv_row,
        check_algorithms_status,
        clear_screen as _clear,
        compute_population_diversity,
        format_time,
        generate_combinations,
        get_cpu_info,
        get_file_hash,
        load_metadata,
        log_environment_info as _log_environment_info,
        make_deterministic_seed,
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
        resolve_dist_matrix as _resolve_dist_matrix,
        save_tuning_params_and_solution as _save_best_solution,
        load_best_params as _load_best_params,
        get_bsf_tracker,
        compute_gap,
    )

try:
    from academic_benchmark.engine_core import AlgorithmRegistry as _AlgoReg
    _HAS_REGISTRY = True
except ImportError:
    _AlgoReg = None
    _HAS_REGISTRY = False

from academic_benchmark.param_db import (
    save_entry as _param_db_save,
    get_best_for as _param_db_get_best,
    list_entries as _param_db_list,
    analyze_patterns as _param_db_analyze,
    delete_entry as _param_db_delete,
    set_db_path as _param_db_set,
)

# ── Versiyon ve yollar ────────────────────────────────────────────────────────

VERSION = "2.0.0"

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

# TSPLIB veri kaynakları (öncelik sırası)
TSPLIB_ARCHIVE = os.path.join(_ENGINE_DIR, "tsplib_problems", "ALL_tsp.tar.gz")
TSPLIB_DIR_FALLBACK = os.path.join(_ENGINE_DIR, "tsplib_data")

# Çıktı dizinleri
RESULTS_DIR = os.path.join(_ENGINE_DIR, "sota_results")
BENCHMARK_DB = os.path.join(_ENGINE_DIR, "benchmark_db")
METADATA_PATH = os.path.join(BENCHMARK_DB, "master_sota_metadata.json")
DOE_RESULTS_DIR = os.path.join(RESULTS_DIR, "doe_sota")
CONFIGS_DIR = os.path.join(BENCHMARK_DB, "configs_sota")
HISTORIES_DIR = os.path.join(BENCHMARK_DB, "convergence_sota")
HISTORY_DIR = os.path.join(BENCHMARK_DB, "history")

# ── Engine sabitleri ──────────────────────────────────────────────────────────

ALL_ALGOS: List[str] = ["E2BSO-TSP", "E2BSO-TSP-CPSO", "R2DMA-TSP", "P-AOEA-TSP", "CGO-TSP", "RUN-TSP"]

# Numba aktifken adaptif bütçe sınırları
_NUMBA_POP_MIN, _NUMBA_POP_MAX, _NUMBA_POP_DIV = 20, 60, 2
_NUMBA_ITER_MIN, _NUMBA_ITER_MAX, _NUMBA_ITER_FACTOR = 200, 500, 5

# Numba yoksa (pure Python) daha küçük bütçeler
_PY_POP_MIN, _PY_POP_MAX, _PY_POP_DIV = 15, 35, 3
_PY_ITER_MIN, _PY_ITER_MAX, _PY_ITER_FACTOR = 100, 250, 3

# Hash tracking için izlenen kaynak dosyalar
ALGORITHMS_TO_CHECK: Dict[str, str] = {
    "E2BSO_TSP": os.path.join(_ENGINE_DIR, "sota_tsp", "e2bso_tsp.py"),
    "R2DMA_TSP": os.path.join(_ENGINE_DIR, "sota_tsp", "r2dma_tsp.py"),
    "PAOEA_TSP": os.path.join(_ENGINE_DIR, "sota_tsp", "paoea_tsp.py"),
    "CGO_TSP": os.path.join(_ENGINE_DIR, "sota_tsp", "cgo_tsp.py"),
    "RUN_TSP": os.path.join(_ENGINE_DIR, "sota_tsp", "run_tsp.py"),
    "LSEngine":  os.path.join(_ENGINE_DIR, "sota_tsp", "ls_engine.py"),
    "RepairOps": os.path.join(_ENGINE_DIR, "sota_tsp", "repair_ops.py"),
    "DestroyOps": os.path.join(_ENGINE_DIR, "sota_tsp", "destroy_ops.py"),
}

# DoE parametre taraması için maksimum kombinasyon sayısı
DOE_MAX_COMBINATIONS = 50

# ── Engine modu ───────────────────────────────────────────────────────────────

class EngineMode(Enum):
    DEFAULT = "default"  # Adaptif sabit parametrelerle doğrudan benchmark
    TUNING  = "tuning"   # DoE parametre tarama → en iyi parametrelerle benchmark


# ── Global shutdown state ─────────────────────────────────────────────────────

_shutdown_requested: bool = False
_active_metadata: Optional[Dict[str, Any]] = None
_active_results: List[Dict[str, Any]] = []


# ── Dizin ve Yol Fonksiyonları ──────────────────────────────────────────────────

def _ensure_dirs() -> None:
    """Gerekli çıktı dizinlerini oluşturur."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(BENCHMARK_DB, exist_ok=True)
    os.makedirs(DOE_RESULTS_DIR, exist_ok=True)
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(HISTORIES_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)


def _ab_path(filename: str) -> str:
    """Benchmark veritabanı klasörü içinde yol oluşturur."""
    return os.path.join(BENCHMARK_DB, filename)


def _signal_handler(signum, frame) -> None:
    """Ctrl+C yakalanırsa tamamlanan sonuçları kaydet ve çık."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] Kapatma sinyali alindi — tamamlanan sonuclar kaydediliyor...")
    if _active_metadata is not None:
        save_metadata(METADATA_PATH, _active_metadata)
        if _active_results:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(HISTORY_DIR, exist_ok=True)
            csv_path = os.path.join(HISTORY_DIR, f"interrupted_sota_{ts}.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(_active_results[0].keys()))
                writer.writeheader()
                writer.writerows(_active_results)
            print(f"[OK] {len(_active_results)} sonuc kaydedildi: {csv_path}")
    sys.exit(130)


signal.signal(signal.SIGINT, _signal_handler)


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 1: TSPLIB Loader
# Kaynak: run_smart_benchmark_sota.py (tar.gz + fallback)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TSPProblem:
    """Tek bir TSPLIB problem örneğini temsil eder."""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[int]
    category: str  # small / medium / large


def _clean_tsplib_name(raw: str) -> str:
    """TSPLIB problem adını normalize eder: lowercase, uzantı ve suffix kaldırır."""
    name = raw.lower().strip()
    for suffix in (".opt.tour", ".opt", ".tsp"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    # Dizin ayraçlarından temizle
    name = name.split("/")[-1].split("\\")[-1]
    return name


def _parse_tsplib_text(content: str, name_hint: str = "") -> Optional[Dict[str, Any]]:
    """
    TSPLIB metin içeriğini parse eder (CRLF, birleşik opt+tsp blokları dahil).

    Desteklenen EDGE_WEIGHT_TYPE: EUC_2D, EUC_3D, CEIL_2D, ATT, GEO, GEOM, NEU_2D
    Döndürür: {'name', 'dimension', 'edge_weight_type', 'coordinates', 'optimal'}
    veya None (desteklenmeyen/bozuk dosya).
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # NODE_COORD_SECTION bloğunu bul
    coord_m = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)",
        content, re.DOTALL | re.I,
    )
    if not coord_m:
        return None

    header_section = content[: coord_m.start()]

    dim_m  = re.search(r"DIMENSION\s*[:\s]\s*(\d+)",  header_section, re.I)
    ewt_m  = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header_section, re.I)
    # Birleşik arşiv bloklarında son NAME satırını al
    name_matches = list(re.finditer(r"^NAME\s*[:\s]\s*(\S+)", header_section, re.I | re.M))

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
        return None  # Explicit matrix vb. — atla

    coords: List[Tuple[float, float]] = []
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
        "optimal": TSPLIB_OPTIMALS.get(name),
    }


def _category(n: int) -> str:
    """Problem boyutuna göre small/medium/large döner."""
    if n <= 100:
        return "small"
    if n <= 500:
        return "medium"
    return "large"


def load_problems(size_limit: int = 500) -> List[TSPProblem]:
    """
    TSPLIB problemlerini yükler (boyut <= size_limit).

    Kaynak önceliği:
      1. tsplib_problems/ALL_tsp.tar.gz  (.tsp.gz girdileri)
      2. tsplib_data/*.tsp               (düz dosyalar, fallback)
    """
    # --- DB fast path ---
    if _db_ready(TSPLIB_DB):
        rows = _problems_from_db(db_path=TSPLIB_DB,
                                 max_dim=size_limit if size_limit > 0 else 99999)
        if rows:
            return sorted([
                TSPProblem(
                    name=r["name"], dimension=r["dimension"],
                    coordinates=r["coordinates"], optimal=r["optimal"],
                    category=r["category"]
                )
                for r in rows
            ], key=lambda p: p.dimension)
    # --- END DB fast path ---
    problems: Dict[str, TSPProblem] = {}

    # ── Kaynak 1: ALL_tsp.tar.gz ──────────────────────────────────────────────
    if os.path.exists(TSPLIB_ARCHIVE):
        try:
            with tarfile.open(TSPLIB_ARCHIVE, "r:gz") as tar:
                for member in tar.getmembers():
                    if not member.name.endswith(".tsp.gz"):
                        continue
                    raw_name = os.path.basename(member.name).replace(".tsp.gz", "").lower()
                    fobj = tar.extractfile(member)
                    if fobj is None:
                        continue
                    try:
                        text = gzip.decompress(fobj.read()).decode("latin-1")
                    except Exception:
                        continue
                    info = _parse_tsplib_text(text, raw_name)
                    if info and info["dimension"] <= size_limit:
                        p = TSPProblem(
                            name=info["name"],
                            dimension=info["dimension"],
                            coordinates=info["coordinates"],
                            optimal=info["optimal"],
                            category=_category(info["dimension"]),
                        )
                        problems[p.name] = p
        except Exception as exc:
            print(f"  [UYARI] Arsiv okunamadi: {exc}")

    # ── Kaynak 2: tsplib_data/*.tsp (fallback) ────────────────────────────────
    if os.path.isdir(TSPLIB_DIR_FALLBACK):
        for fname in sorted(os.listdir(TSPLIB_DIR_FALLBACK)):
            if not fname.endswith(".tsp"):
                continue
            path = os.path.join(TSPLIB_DIR_FALLBACK, fname)
            try:
                with open(path, "r", errors="replace") as f:
                    text = f.read()
            except Exception:
                continue
            info = _parse_tsplib_text(text, fname.replace(".tsp", ""))
            if info and info["dimension"] <= size_limit:
                p = TSPProblem(
                    name=info["name"],
                    dimension=info["dimension"],
                    coordinates=info["coordinates"],
                    optimal=info["optimal"],
                    category=_category(info["dimension"]),
                )
                # Arşiv önceliği — fallback sadece eksik olanları ekler
                problems.setdefault(p.name, p)

    return sorted(problems.values(), key=lambda p: p.dimension)


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 2: Numba Tespiti ve Adaptif Config
# ─────────────────────────────────────────────────────────────────────────────

def _detect_numba() -> bool:
    """Numba'nin aktif olup olmadigini tespit eder."""
    try:
        # bildiri2026/core/numba_accel.py kontrolu
        _ab_dir = os.path.join(_PROJECT_ROOT, "academic_benchmark", "bildiri2026")
        if os.path.isdir(_ab_dir) and _ab_dir not in sys.path:
            sys.path.insert(0, _ab_dir)
        from core import numba_accel as _nb  # type: ignore
        return bool(_nb.NUMBA_AVAILABLE)
    except Exception:
        return False


_NUMBA_AVAILABLE = _detect_numba()


def _make_solver_config(algo_name: str, n: int, numba_ok: bool) -> Dict[str, Any]:
    """Problem boyutuna ve Numba durumuna gore dinamik algoritma butceleri olusturur."""
    if numba_ok:
        ls_limit = 0.5
        pop = max(_NUMBA_POP_MIN, min(_NUMBA_POP_MAX, n // _NUMBA_POP_DIV))
        max_iter = max(_NUMBA_ITER_MIN, min(_NUMBA_ITER_MAX, n * _NUMBA_ITER_FACTOR))
    else:
        ls_limit = max(0.02, min(0.12, 0.003 * n))
        pop = max(_PY_POP_MIN, min(_PY_POP_MAX, n // _PY_POP_DIV))
        max_iter = max(_PY_ITER_MIN, min(_PY_ITER_MAX, n * _PY_ITER_FACTOR))

    # Timeout default: n × 5 seconds (e.g. 100-city → 500s, 500-city → 2500s)
    time_limit_default = max(60.0, n * 5.0)

    configs: Dict[str, Dict[str, Any]] = {
        "E2BSO-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "ls_intensity_normal": "light",
            "ls_intensity_compress": "moderate",
            "time_limit": time_limit_default,
        },
        "E2BSO-TSP-CPSO": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "ls_intensity_normal": "light",
            "ls_intensity_compress": "moderate",
            "time_limit": time_limit_default,
        },
        "R2DMA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "time_limit": time_limit_default,
        },
        "P-AOEA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "time_limit": time_limit_default,
        },
        "CGO-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "time_limit": time_limit_default,
        },
        "RUN-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "time_limit": time_limit_default,
        },
    }
    return configs.get(algo_name, {})


def _build_sota_parameter_space(algo_name: str) -> Dict[str, List[Any]]:
    """DoE modunda Grid Search icin test edilecek parametre uzaylari."""
    if algo_name == "E2BSO-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "gamma": [0.15, 0.20, 0.30],
            "injection_rate": [0.08, 0.12, 0.18],
            "remove_ratio": [0.10, 0.15, 0.20],
            "time_limit": [300.0, 600.0, 1200.0],
        }
    if algo_name == "E2BSO-TSP-CPSO":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "gamma": [0.15, 0.20, 0.30],
            "injection_rate": [0.08, 0.12, 0.18],
            "remove_ratio": [0.10, 0.15, 0.20],
            "c1": [1.0, 1.5, 2.0],
            "c2": [1.0, 1.5, 2.0],
            "inertia": [0.5, 0.7, 0.9],
            "time_limit": [300.0, 600.0, 1200.0],
        }
    if algo_name == "R2DMA-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "theta_base": [0.15, 0.25, 0.35],
            "remove_ratio": [0.10, 0.15, 0.20],
            "pulse_injection_rate": [0.05, 0.10, 0.15],
            "time_limit": [300.0, 600.0, 1200.0],
        }
    if algo_name == "CGO-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "chaos_rate": [3.80, 3.90, 3.99],
            "seed_length_ratio": [0.15, 0.25, 0.35],
            "time_limit": [300.0, 600.0, 1200.0],
        }
    if algo_name == "RUN-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "beta": [0.3, 0.5, 0.7],
            "esq_probability": [0.1, 0.2, 0.3],
            "time_limit": [300.0, 600.0, 1200.0],
        }
    return {
        "population_size": [24, 36, 48],
        "max_iterations": [200, 320, 450],
        "genome_population_size": [8, 12, 16],
        "crossover_rate": [0.75, 0.85, 0.95],
        "mutation_rate": [0.10, 0.18, 0.26],
        "time_limit": [300.0, 600.0, 1200.0],
    }


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3: Worker ve Solver Factory (Multiprocessing-safe)
# ─────────────────────────────────────────────────────────────────────────────

def _make_solver(algo_name: str, params: Dict[str, Any]):
    """Parametrelere gore SOTA solver instance dondurur."""
    try:
        from sota_tsp import (
            E2BSO_TSP, E2BSO_TSP_CPSO, R2DMA_TSP, PAOEA_TSP, CGO_TSP, RUN_TSP,
            E2BSOTSPConfig, E2BSOCPSPConfig, R2DMATSPConfig, PAOEAConfig, CGOConfig, RUNConfig,
        )
    except ImportError:
        # Fallback if _PROJECT_ROOT wasn't attached in worker
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from academic_benchmark.sota_tsp import (
            E2BSO_TSP, E2BSO_TSP_CPSO, R2DMA_TSP, PAOEA_TSP, CGO_TSP, RUN_TSP,
            E2BSOTSPConfig, E2BSOCPSPConfig, R2DMATSPConfig, PAOEAConfig, CGOConfig, RUNConfig,
        )

    seed = int(params.get("seed", 42))
    cfg = params.copy()
    cfg.pop("seed", None)
    
    if algo_name == "E2BSO-TSP":
        return E2BSO_TSP(E2BSOTSPConfig(seed=seed, **cfg))
    if algo_name == "E2BSO-TSP-CPSO":
        return E2BSO_TSP_CPSO(E2BSOCPSPConfig(seed=seed, **cfg))
    if algo_name == "R2DMA-TSP":
        return R2DMA_TSP(R2DMATSPConfig(seed=seed, **cfg))
    if algo_name == "P-AOEA-TSP":
        return PAOEA_TSP(PAOEAConfig(seed=seed, **cfg))
    if algo_name == "CGO-TSP":
        return CGO_TSP(CGOConfig(seed=seed, **cfg))
    if algo_name == "RUN-TSP":
        return RUN_TSP(RUNConfig(seed=seed, **cfg))
    raise ValueError(f"Bilinmeyen algoritma: {algo_name}")


def _run_solver_task(args: Tuple) -> Dict[str, Any]:
    """Tek bir DEFAULT (problem, algo, seed) benchmark isini calistirir."""
    algo_name, coordinates, seed, run_idx, n_nodes, optimal, numba_ok, problem_name = args
    
    cfg = _make_solver_config(algo_name, n_nodes, numba_ok)
    cfg["seed"] = seed

    try:
        solver = _make_solver(algo_name, cfg)
    except Exception as exc:
        return {"error": f"Import/Init failed: {exc}", "algorithm": algo_name, "problem": problem_name}

    try:
        t0 = time.perf_counter()
        matrix = _dm_from_cache(problem_name, TSPLIB_DB)
        if matrix is not None and len(matrix) == len(coordinates):
            solver.set_dist_matrix(matrix)
        result = solver.solve(coordinates)
        elapsed = time.perf_counter() - t0
    except Exception as exc:
        import traceback
        return {
            "error": f"{algo_name} crashed: {exc}\n{traceback.format_exc()}",
            "algorithm": algo_name,
            "problem": problem_name,
        }

    # Tour validation: ensure permutation is valid
    tour = getattr(result, "tour", [])
    if tour and len(tour) == n_nodes:
        assert len(set(tour)) == n_nodes, f"[{algo_name}/{problem_name}] Invalid tour: duplicate nodes"
        assert min(tour) == 0, f"[{algo_name}/{problem_name}] Invalid tour: min node {min(tour)} != 0"
        assert max(tour) == n_nodes - 1, f"[{algo_name}/{problem_name}] Invalid tour: max node {max(tour)} != {n_nodes-1}"

    # Update BSF tracker and compute gap (optimal or BSF fallback)
    bsf = get_bsf_tracker()
    bsf.update(problem_name, result.tour_length)
    gap_pct, gap_type = compute_gap(problem_name, result.tour_length, optimal)

    return {
        "problem": problem_name,
        "algorithm": algo_name,
        "run": run_idx + 1,
        "seed": seed,
        "dimension": n_nodes,
        "optimal": optimal,
        "tour_cost": int(result.tour_length),
        "gap_pct": round(gap_pct, 4) if not math.isnan(gap_pct) else None,
        "gap_type": gap_type,
        "elapsed_sec": round(elapsed, 3),
        "iterations": getattr(result, "iterations", 0),
        "tour": tour,
    }


def _evaluate_sota_combo(task: Tuple[Dict[str, Any], str, Dict[str, Any], int, int]) -> Dict[str, Any]:
    """TUNING modunda bir parametre setini test eder (n_runs ortalamasi)."""
    problem_dict, algo_name, params, combo_idx, n_runs = task
    coordinates = problem_dict["coordinates"]
    optimal = problem_dict["optimal"]
    n_nodes = problem_dict["dimension"]

    costs: List[float] = []
    times_sec: List[float] = []
    cached_matrix = _dm_from_cache(problem_dict["name"], TSPLIB_DB)
    if cached_matrix is not None and len(cached_matrix) != n_nodes:
        cached_matrix = None
    for run_idx in range(n_runs):
        seed = make_deterministic_seed(problem_dict["name"], algo_name, run_idx, combo_idx, 5000)
        run_params = params.copy()
        run_params["seed"] = seed

        try:
            solver = _make_solver(algo_name, run_params)
            if cached_matrix is not None:
                solver.set_dist_matrix(cached_matrix)
            t0 = time.perf_counter()
            result = solver.solve(coordinates)
            elapsed = time.perf_counter() - t0
            costs.append(float(result.tour_length))
            times_sec.append(elapsed)
        except Exception as exc:
            import traceback
            print(f"  [WARN] {algo_name} run {run_idx} failed for {problem_dict['name']}: {exc}")
            traceback.print_exc()
            continue


    if not costs:
        avg_cost = float("inf")
        avg_gap = float("nan")
        avg_time = 0.0
    else:
        avg_cost = sum(costs) / len(costs)
        avg_gap = ((avg_cost - optimal) / optimal * 100.0) if (optimal is not None and optimal > 0) else float("nan")
        avg_time = sum(times_sec) / len(times_sec)

    return {
        "problem": problem_dict["name"],
        "strategy": algo_name,
        "combo_idx": combo_idx,
        "params": params,
        "avg_length": avg_cost,
        "avg_gap": avg_gap,
        "avg_time_ms": avg_time * 1000.0,
        "n_runs": len(costs),
        "dimension": n_nodes,
        "convergence_profile": costs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 4: Smart Cache ve Veri Kaydetme
# ─────────────────────────────────────────────────────────────────────────────

def _save_incremental(result: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """Tek bir DEFAULT benchmark sonucunu JSON metadata'ya ekler."""
    if "error" in result:
        return
        
    pname = result["problem"]
    algo = result["algorithm"]
    saved = metadata.setdefault("results", {})
    p_saved = saved.setdefault(pname, {})
    a_saved = p_saved.setdefault(algo, {
        "costs": [], "gaps": [], "times_sec": [],
        "best_cost": None, "best_gap": None,
        "avg_cost": None, "avg_gap": None, "avg_time_sec": None,
        "n_runs": 0, "timestamp": "", "gap_type": "unknown",
    })
    
    a_saved["costs"].append(result["tour_cost"])
    if result["gap_pct"] is not None:
        a_saved["gaps"].append(result["gap_pct"])
    a_saved["times_sec"].append(result["elapsed_sec"])
    a_saved["gap_type"] = result.get("gap_type", "unknown")
    
    a_saved["n_runs"] = len(a_saved["costs"])
    a_saved["best_cost"] = min(a_saved["costs"])
    a_saved["best_gap"] = min(a_saved["gaps"]) if a_saved["gaps"] else None
    a_saved["avg_cost"] = statistics.mean(a_saved["costs"])
    a_saved["avg_gap"] = statistics.mean(a_saved["gaps"]) if a_saved["gaps"] else None
    a_saved["avg_time_sec"] = statistics.mean(a_saved["times_sec"])
    a_saved["timestamp"] = datetime.now().isoformat()
    
    metadata["last_updated"] = datetime.now().isoformat()
    update_algorithm_hashes(metadata, ALGORITHMS_TO_CHECK)
    save_metadata(METADATA_PATH, metadata)

    # --- benchmark_progress.csv LOGLAMA (Numba motoruyla ayni) ---
    progress_path = os.path.join(RESULTS_DIR, "benchmark_progress.csv")
    file_exists = os.path.isfile(progress_path)
    
    with open(progress_path, "a", newline="", encoding="utf-8") as f:
        fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "result_type", "params_json", "gap_type"]
        writer = csv.DictWriter(f, fieldnames=fields)
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["algorithm"],
            "avg_length": result["tour_cost"],
            "avg_gap": result["gap_pct"],
            "avg_time_ms": result["elapsed_sec"] * 1000.0,
            "n_runs": 1,
            "result_type": "raw",
            "params_json": json.dumps(result.get("params", {}), ensure_ascii=False),
            "gap_type": result.get("gap_type", "unknown")
        })



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 5: Motor Mantığı (Engine Logic)
# ─────────────────────────────────────────────────────────────────────────────

def _run_pool(tasks: List[Tuple], workers: int, func: callable) -> List[Dict[str, Any]]:
    """Gorevleri sirali veya paralel olarak isler."""
    if not tasks:
        return []
        
    results = []
    if workers <= 1:
        for i, task in enumerate(tasks):
            res = func(task)
            results.append(res)
    else:
        # Windows-safe executor (ProcessPoolExecutor)
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            for res in executor.map(func, tasks):
                results.append(res)
    return results


def _print_progress_line(idx: int, total: int, result: Dict[str, Any], stage: str) -> None:
    gap_val = result.get("gap_pct") if "gap_pct" in result else result.get("avg_gap")
    sym = "*" if gap_val is not None and not math.isnan(gap_val) and gap_val <= 1 else (
        "+" if gap_val is not None and not math.isnan(gap_val) and gap_val <= 5 else "o"
    )
    gap_text = "N/A" if gap_val is None or math.isnan(gap_val) else f"{gap_val:>6.2f}%"
    pname = result.get("problem", "unk")
    algo = result.get("algorithm") if "algorithm" in result else result.get("strategy")
    
    time_ms = result.get("elapsed_sec", 0) * 1000.0
    if "avg_time_ms" in result:
        time_ms = result["avg_time_ms"]
        
    print(
        f"  [{idx:>3}/{total}] {pname:<12} {algo:<12} "
        f"GAP: {gap_text:>7} {sym} {time_ms:>7.0f}ms [{stage}]",
        flush=True,
    )




def _run_engine_default(
    problems: List[TSPProblem], 
    algos: List[str], 
    n_runs: int, 
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool = False
) -> List[Dict[str, Any]]:
    """Standart benchmarking (Tune edilmemis varsayilan parametrelerle)."""
    tasks = []
    total_runs = len(problems) * len(algos) * n_runs
    completed = 0
    
    for problem in problems:
        for algo in algos:
            p_saved = metadata.get("results", {}).get(problem.name, {}).get(algo, {})
            saved_runs = p_saved.get("n_runs", 0)
            
            if skip_cached and saved_runs >= n_runs:
                completed += n_runs
                continue
                
            runs_to_do = n_runs
            if skip_cached:
                runs_to_do = max(0, n_runs - saved_runs)
                completed += saved_runs
                
            for run_idx in range(runs_to_do):
                global_run_idx = saved_runs + run_idx
                seed = make_deterministic_seed(problem.name, algo, global_run_idx, 0, 5000)
                tasks.append((
                    algo, problem.coordinates, seed, global_run_idx,
                    problem.dimension, problem.optimal, _NUMBA_AVAILABLE, problem.name
                ))
    
    if not tasks:
        print("[CACHE] Tum gorevler onbellekte mevcut.")
        return []
        
    results = []
    print(f"\n[START] DEFAULT Mod Basliyor ({len(tasks)} gorev, {workers} worker)...")
    
    if workers <= 1:
        for task in tasks:
            res = _run_solver_task(task)
            results.append(res)
            _active_results.append(res)
            completed += 1
            _save_incremental(res, metadata)
            _print_progress_line(completed, total_runs, res, "BENCH")
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(_run_solver_task, task): task for task in tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                res = future.result()
                results.append(res)
                _active_results.append(res)
                completed += 1
                _save_incremental(res, metadata)
                _print_progress_line(completed, total_runs, res, "BENCH")

    # Sonuclari agrege et (Problem + Algo bazinda)
    aggregated = {}
    for r in results:
        if "error" in r: continue
        key = (r["problem"], r["algorithm"])
        if key not in aggregated:
            aggregated[key] = {
                "problem": r["problem"],
                "strategy": r["algorithm"],
                "costs": [], "gaps": [], "times": []
            }
        aggregated[key]["costs"].append(r["tour_cost"])
        if r["gap_pct"] is not None:
            aggregated[key]["gaps"].append(r["gap_pct"])
        aggregated[key]["times"].append(r["elapsed_sec"])
        
    final_rows = []
    for key, data in aggregated.items():
        n = len(data["costs"])
        if n == 0: continue
        row = {
            "problem": data["problem"],
            "strategy": data["strategy"],
            "avg_length": sum(data["costs"]) / n,
            "avg_gap": sum(data["gaps"]) / len(data["gaps"]) if data["gaps"] else None,
            "avg_time_ms": (sum(data["times"]) / n) * 1000.0,
            "n_runs": n
        }
        final_rows.append(row)
        
    return final_rows




def _run_engine_tuning(
    problems: List[TSPProblem], algos: List[str], n_runs: int,
    max_combos: int, workers: int, metadata: Dict[str, Any],
    skip_cached: bool = False
) -> Dict[str, Any]:
    """DoE modu: grid/fractional kombinasyonları bütçe ile tarar."""
    _ensure_dirs()
    best_params: Dict[str, Any] = {}
    tuning_csv = os.path.join(DOE_RESULTS_DIR, "tuning_progress.csv")
    completed_tuning: set = set()

    if os.path.exists(tuning_csv):
        try:
            with open(tuning_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    completed_tuning.add((row["problem"], row["strategy"], row["param_signature"]))
        except Exception:
            pass

    tasks = []
    for problem in problems:
        for algo in algos:
            defaults = _make_solver_config(algo, problem.dimension, _NUMBA_AVAILABLE)
            space = _build_sota_parameter_space(algo)
            combos = generate_combinations(space, max_combos)
            
            for combo_idx, combo in enumerate(combos, 1):
                params = defaults.copy()
                params.update(combo)
                sig = param_signature(params)
                
                if skip_cached and (problem.name, algo, sig) in completed_tuning:
                    continue
                    
                problem_dict = {
                    "name": problem.name,
                    "dimension": problem.dimension,
                    "coordinates": problem.coordinates,
                    "optimal": problem.optimal,
                }
                tasks.append((problem_dict, algo, params, combo_idx, n_runs))

    if not tasks:
        print("[CACHE] Tum tuning gorevleri onbellekte mevcut.")
        return best_params

    print(f"\n[START] TUNING Mod Basliyor ({len(tasks)} kombinasyon, {workers} worker)...")

    tuning_fields = [
        "timestamp", "problem", "strategy", "combo_idx", "avg_length", "avg_gap",
        "avg_time_ms", "n_runs", "param_signature", "params_json"
    ]

    def _save_tuning_result(res: Dict[str, Any]):
        sig = param_signature(res["params"])
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": res["problem"],
            "strategy": res["strategy"],
            "combo_idx": res["combo_idx"],
            "avg_length": round(res["avg_length"], 4),
            "avg_gap": None if math.isnan(res["avg_gap"]) else round(res["avg_gap"], 6),
            "avg_time_ms": round(res["avg_time_ms"], 4),
            "n_runs": res["n_runs"],
            "param_signature": sig,
            "params_json": json.dumps(res["params"], ensure_ascii=False, sort_keys=True),
        }

        exists = os.path.exists(tuning_csv)
        with open(tuning_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=tuning_fields)
            if not exists:
                writer.writeheader()
            writer.writerow(row)

        best_key = f"{res['problem']}::{res['strategy']}"
        current_best = best_params.get(best_key)
        if current_best is None or res["avg_length"] < float(current_best["avg_length"]):
            best_params[best_key] = {
                "problem": res["problem"],
                "strategy": res["strategy"],
                "avg_length": res["avg_length"],
                "avg_gap": res["avg_gap"],
                "avg_time_ms": res["avg_time_ms"],
                "params": res["params"],
                "convergence_profile": res.get("convergence_profile", []),
            }

        metadata["best_params"] = best_params
        save_metadata(METADATA_PATH, metadata)

    completed = 0
    total_tasks = len(tasks)

    if workers <= 1:
        for task in tasks:
            res = _evaluate_sota_combo(task)
            _save_tuning_result(res)
            completed += 1
            _print_progress_line(completed, total_tasks, res, "TUNE")
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(_evaluate_sota_combo, task): task for task in tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                res = future.result()
                _save_tuning_result(res)
                completed += 1
                _print_progress_line(completed, total_tasks, res, "TUNE")

    return best_params


# ── Optuna Bayesian Optimization for SOTA ─────────────────────────────────────

def _build_sota_optuna_space(algo_name: str, trial: Any) -> Dict[str, Any]:
    """Map SOTA parameter space to Optuna suggest_* calls."""
    params = {}
    if algo_name == "E2BSO-TSP":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["gamma"] = trial.suggest_float("gamma", 0.10, 0.35)
        params["injection_rate"] = trial.suggest_float("injection_rate", 0.05, 0.25)
        params["remove_ratio"] = trial.suggest_float("remove_ratio", 0.05, 0.25)
    elif algo_name == "E2BSO-TSP-CPSO":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["gamma"] = trial.suggest_float("gamma", 0.10, 0.35)
        params["injection_rate"] = trial.suggest_float("injection_rate", 0.05, 0.25)
        params["remove_ratio"] = trial.suggest_float("remove_ratio", 0.05, 0.25)
        params["c1"] = trial.suggest_float("c1", 0.5, 2.5)
        params["c2"] = trial.suggest_float("c2", 0.5, 2.5)
        params["inertia"] = trial.suggest_float("inertia", 0.3, 0.95)
    elif algo_name == "R2DMA-TSP":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["theta_base"] = trial.suggest_float("theta_base", 0.10, 0.40)
        params["remove_ratio"] = trial.suggest_float("remove_ratio", 0.05, 0.25)
        params["pulse_injection_rate"] = trial.suggest_float("pulse_injection_rate", 0.02, 0.20)
    elif algo_name == "P-AOEA-TSP":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["genome_population_size"] = trial.suggest_int("genome_population_size", 6, 20)
        params["crossover_rate"] = trial.suggest_float("crossover_rate", 0.60, 0.99)
        params["mutation_rate"] = trial.suggest_float("mutation_rate", 0.05, 0.30)
    elif algo_name == "CGO-TSP":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["chaos_rate"] = trial.suggest_float("chaos_rate", 3.57, 4.0)
        params["seed_length_ratio"] = trial.suggest_float("seed_length_ratio", 0.10, 0.40)
    elif algo_name == "RUN-TSP":
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
        params["beta"] = trial.suggest_float("beta", 0.1, 0.9)
        params["esq_probability"] = trial.suggest_float("esq_probability", 0.05, 0.40)
    else:
        params["population_size"] = trial.suggest_int("population_size", 20, 60)
        params["max_iterations"] = trial.suggest_int("max_iterations", 150, 500)
    return params


def _sota_optuna_objective(
    trial: Any,
    problem: 'TSPProblem',
    algo_name: str,
    n_runs: int,
) -> float:
    """Optuna objective function for SOTA algorithms."""
    defaults = _make_solver_config(algo_name, problem.dimension, _NUMBA_AVAILABLE)
    params = defaults.copy()
    params.update(_build_sota_optuna_space(algo_name, trial))

    costs: List[float] = []
    for run_idx in range(n_runs):
        seed = make_deterministic_seed(problem.name, algo_name, run_idx, trial.number, 5000)
        run_params = params.copy()
        run_params["seed"] = seed
        try:
            solver = _make_solver(algo_name, run_params)
            matrix = _dm_from_cache(problem.name, TSPLIB_DB)
            if matrix is not None and len(matrix) == problem.dimension:
                solver.set_dist_matrix(matrix)
            result = solver.solve(problem.coordinates)
            costs.append(float(result.tour_length))
        except Exception:
            return float("inf")

    if not costs:
        return float("inf")
    avg_cost = sum(costs) / len(costs)
    optimal = problem.optimal
    if optimal and optimal > 0:
        return ((avg_cost - optimal) / optimal) * 100.0
    return avg_cost


def _run_sota_optuna_tuning(
    problems: List['TSPProblem'],
    algos: List[str],
    n_runs: int,
    n_trials: int,
    workers: int,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Run Optuna Bayesian optimization for SOTA algorithms."""
    import optuna

    best_params: Dict[str, Any] = {}

    for problem in problems:
        for algo in algos:
            print(f"\n[OPTUNA] {problem.name} / {algo} — basliyor ({n_trials} trials)...")
            study = optuna.create_study(
                direction="minimize",
                study_name=f"{problem.name}_{algo}",
                sampler=optuna.samplers.TPESampler(seed=42),
            )

            def make_objective(p, a, n):
                def objective(trial):
                    return _sota_optuna_objective(trial, p, a, n)
                return objective

            study.optimize(make_objective(problem, algo, n_runs), n_trials=n_trials, show_progress_bar=False)

            print(f"\n[OPTUNA] {problem.name} / {algo} — En iyi gap: {study.best_value:.2f}%")
            print(f"  En iyi parametreler: {study.best_params}")

            key = f"{problem.name}::{algo}"
            defaults = _make_solver_config(algo, problem.dimension, _NUMBA_AVAILABLE)
            best_params[key] = {
                "params": {**defaults, **study.best_params},
                "objective_value": study.best_value,
                "avg_gap": study.best_value,
                "avg_length": None,
                "n_runs": n_runs,
            }

    print("\n[OPTUNA] SOTA tuning tamamlandi.")
    metadata["best_params"] = best_params
    return best_params


def _save_best_solutions_post_tuning(best_params, problems, algos):
    """Save tuning best params to best_solutions table in DB."""
    saved = 0
    prob_map = {p.name: p for p in problems}
    for key, entry in best_params.items():
        parts = key.split("::", 1)
        if len(parts) != 2:
            continue
        prob_name, algo_name = parts
        prob = prob_map.get(prob_name)
        if not prob:
            continue
        _save_best_solution(
            problem_name=prob_name,
            algorithm=algo_name,
            params=entry.get("params", {}),
            tour=[],
            tour_length=float(entry.get("avg_length", 0)),
            gap=float(entry.get("avg_gap", 0)) if not math.isnan(entry.get("avg_gap", float("nan"))) else 0.0,
            db_path=TSPLIB_DB,
        )
        saved += 1
    if saved:
        print(f"[PARAM_DB] {saved} parametre seti best_solutions tablosuna kaydedildi.")


# ── Param DB Integration (Feature Parity with Numba Engine) ───────────────────

def _save_best_to_param_db(
    best_params: Dict[str, Dict[str, Any]],
    problems: List[TSPProblem],
    algos: List[str],
) -> int:
    """Save best tuning results to persistent parameter database.
    Also saves to tsplib.db best_solutions table for cross-engine queries.
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
        runs = entry.get("n_runs", 3)
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


def _edit_param_space_interactive(algo_name: str) -> Dict[str, List[Any]]:
    """Interactively edit the parameter space for a SOTA algorithm."""
    space = _build_sota_parameter_space(algo_name)
    print(f"\n[PARAM] {algo_name} parametre uzayini duzenleyin (Enter = kabul):")
    # Show guidance for time_limit parameter
    if "time_limit" in space:
        print("  [INFO] Zaman asimi (time_limit) önerileri:")
        print("    - Varsayilan: n × 5 saniye (örn: 100-sehir → 500s)")
        print("    - Kucuk problemler (n<50): 60-300s")
        print("    - Orta problemler (50≤n<200): 300-1200s")
        print("    - Buyuk problemler (n≥200): 1200-3600s")
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
            try:
                if sample_type == int:
                    new_vals.append(int(p))
                elif sample_type == float:
                    new_vals.append(float(p))
                else:
                    new_vals.append(p)
            except ValueError:
                valid = False
                break
        if valid and new_vals:
            result[key] = new_vals
        else:
            print(f"    [!] Gecersiz, mevcut korunuyor: {vals}")
            result[key] = vals
    return result


def _manual_param_entry_interactive(algos: List[str]) -> Dict[str, Dict[str, Any]]:
    """Interactive manual parameter entry like bildiri2026 Stage 1.
    Shows defaults → asks for edits.
    Returns {algo_name: {param_key: value, ...}, ...}
    """
    result: Dict[str, Dict[str, Any]] = {}
    print("\n" + "=" * 70)
    print("MANUEL PARAMETRE GIRISI (SOTA)")
    print("Her parametre icin varsayilan deger gosterilir.")
    print("Degistirmek istemiyorsaniz [ENTER] tusuna basin.")
    print("=" * 70)
    for algo_name in algos:
        print(f"\n--- {algo_name} ---")
        defaults = _make_solver_config(algo_name, 100, _NUMBA_AVAILABLE)
        space = _build_sota_parameter_space(algo_name)
        current_params = defaults.copy()
        # Show guidance for time_limit parameter
        if "time_limit" in current_params:
            n_hint = 100
            suggested = max(60.0, n_hint * 5.0)
            print(f"  [INFO] Zaman asimi (time_limit) önerileri:")
            print(f"    - Varsayilan: n × 5 saniye (n={n_hint} → {suggested:.0f}s)")
            print(f"    - Kucuk problemler (n<50): 60-300s")
            print(f"    - Orta problemler (50≤n<200): 300-1200s")
            print(f"    - Buyuk problemler (n≥200): 1200-3600s")
        print(f"  Varsayilan parametreler: {current_params}")
        edit_raw = input("  Bu algoritma icin parametreleri degistirmek ister misiniz? [e/H]: ").strip().upper()
        if edit_raw != 'E':
            result[algo_name] = current_params
            continue
        manual_params = {}
        for key, vals in space.items():
            default_val = vals[0] if vals else current_params.get(key)
            raw = input(f"  {key} (oneri: {default_val}) = ").strip()
            if raw:
                try:
                    if isinstance(default_val, float):
                        manual_params[key] = float(raw)
                    elif isinstance(default_val, int):
                        manual_params[key] = int(raw)
                    else:
                        manual_params[key] = raw
                except ValueError:
                    print(f"    [!] Gecersiz deger, varsayilan ({default_val}) kullanildi.")
                    manual_params[key] = default_val
            else:
                manual_params[key] = default_val
        for key in current_params:
            if key not in manual_params:
                manual_params[key] = current_params[key]
        result[algo_name] = manual_params
    return result


def _load_params_from_db_interactive(
    problems: List[TSPProblem],
    algos: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Interactive selection: for each (problem, algorithm) pair, load best params from DB.
    Returns {f"{prob.name}::{algo_name}": {param_key: value, ...}}.

    NOTE (2026-05-19): Key format changed from {algo: params} to per-problem keys.
    Previously, multi-problem DB loads silently overwrote params (last problem won).
    See IMPLEMENTATION_PLAN_2026-05-19.md § H-04 for migration details.
    """
    db_entries = _param_db_list()
    if not db_entries:
        print("[INFO] Parametre DB'sinde kayit bulunamadi. Varsayilan parametreler kullanilacak.")
        return {}

    print("\n" + "=" * 70)
    print("PARAMETRE DB'DEN YUKLEME (SOTA)")
    print("=" * 70)
    for prob in problems:
        for algo in algos:
            best = _param_db_get_best(prob.name, algo)
            if best:
                print(f"  {prob.name} / {algo}: best_score={best['best_score']:.1f}, params={best['params']}")
            else:
                print(f"  {prob.name} / {algo}: (DB'de kayit yok, varsayilan kullanilacak)")

    raw = input("\nDB'deki parametreleri kullanmak icin [E], manuel girmek icin [M], varsayilan icin [D]: ").strip().upper()
    if raw == 'E':
        result: Dict[str, Dict[str, Any]] = {}
        for prob in problems:
            for algo in algos:
                best = _param_db_get_best(prob.name, algo)
                key = f"{prob.name}::{algo}"
                if best:
                    result[key] = best["params"]
                else:
                    result[key] = _make_solver_config(algo, prob.dimension, _NUMBA_AVAILABLE)
        return result
    elif raw == 'M':
        return _manual_param_entry_interactive(algos)
    else:
        result = {}
        for prob in problems:
            for algo in algos:
                key = f"{prob.name}::{algo}"
                result[key] = _make_solver_config(algo, prob.dimension, _NUMBA_AVAILABLE)
        return result


def _run_engine_with_params(
    problems: List[TSPProblem],
    algos: List[str],
    custom_params: Dict[str, Dict[str, Any]],
    n_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run benchmark with explicitly provided parameters.
    custom_params: {f"{prob.name}::{algo_name}": {param_key: value, ...}}
    Falls back to {algo_name: params} for backward compat with pre-2026-05-19 metadata.
    """
    tasks = []
    total_runs = len(problems) * len(algos) * n_runs
    completed = 0

    for problem in problems:
        for algo in algos:
            p_saved = metadata.get("results", {}).get(problem.name, {}).get(algo, {})
            saved_runs = p_saved.get("n_runs", 0)
            runs_to_do = n_runs
            completed += saved_runs

            per_problem_key = f"{problem.name}::{algo}"
            legacy_key = algo

            for run_idx in range(runs_to_do):
                global_run_idx = saved_runs + run_idx
                seed = make_deterministic_seed(problem.name, algo, global_run_idx, 0, 5000)
                if per_problem_key in custom_params:
                    params = custom_params[per_problem_key].copy()
                elif legacy_key in custom_params:
                    params = custom_params[legacy_key].copy()
                else:
                    params = _make_solver_config(algo, problem.dimension, _NUMBA_AVAILABLE).copy()
                params["seed"] = seed
                tasks.append((
                    algo, problem.coordinates, seed, global_run_idx,
                    problem.dimension, problem.optimal, _NUMBA_AVAILABLE, problem.name
                ))

    if not tasks:
        print("[CACHE] Tum gorevler onbellekte mevcut.")
        return []

    results = []
    print(f"\n[START] Benchmark with Custom Params ({len(tasks)} gorev, {workers} worker)...")

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {executor.submit(_run_solver_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            res = future.result()
            results.append(res)
            _active_results.append(res)
            completed += 1
            _save_incremental(res, metadata)
            _print_progress_line(completed, total_runs, res, "BENCH")

    aggregated = {}
    for r in results:
        if "error" in r:
            continue
        key = (r["problem"], r["algorithm"])
        if key not in aggregated:
            aggregated[key] = {"problem": r["problem"], "strategy": r["algorithm"], "costs": [], "gaps": [], "times": []}
        aggregated[key]["costs"].append(r["tour_cost"])
        if r["gap_pct"] is not None:
            aggregated[key]["gaps"].append(r["gap_pct"])
        aggregated[key]["times"].append(r["elapsed_sec"])

    final_rows = []
    for key, data in aggregated.items():
        n = len(data["costs"])
        if n == 0:
            continue
        row = {
            "problem": data["problem"],
            "strategy": data["strategy"],
            "avg_length": sum(data["costs"]) / n,
            "avg_gap": sum(data["gaps"]) / len(data["gaps"]) if data["gaps"] else None,
            "avg_time_ms": (sum(data["times"]) / n) * 1000.0,
            "n_runs": n,
        }
        final_rows.append(row)

    return final_rows


def _param_db_menu() -> None:
    """Sub-menu for parameter database management."""
    while True:
        _clear()
        print("\n" + "=" * 60)
        print("PARAMETRE DB YONETIMI (SOTA)".center(60))
        print("=" * 60)
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
                print(f"\n{'ID':>3} {'Tarih':<20} {'Problem':<12} {'Algoritma':<12} {'Skor':<10} {'Gap%':<8} {'Boyut':<6}")
                print("-" * 72)
                for e in entries:
                    gap_str = f"{e.get('gap', 0):.2f}" if e.get('gap') is not None else "N/A"
                    print(f"{e['id']:>3} {e.get('timestamp', '?'):<20} {e['problem']:<12} {e['algorithm']:<12} {e.get('best_score', 0):<10.1f} {gap_str:<8} {e.get('dimension', 0):<6}")
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


# ── AlgorithmRegistry Registration ─────────────────────────────────────────────

def _make_sota_executor(algo_name: str):
    """Create an AlgorithmRegistry-compatible executor for a SOTA solver.
    Signature: (problem, params, seed, run_idx) -> result dict.
    """
    def executor(problem, params, seed, run_idx):
        run_params = params.copy()
        run_params["seed"] = seed
        solver = _make_solver(algo_name, run_params)
        matrix = _dm_from_cache(problem.name, TSPLIB_DB)
        n = problem.dimension
        if matrix is not None and len(matrix) == n and all(len(r) == n for r in matrix):
            solver.set_dist_matrix(matrix)
        t0 = time.perf_counter()
        result = solver.solve(problem.coordinates)
        elapsed = time.perf_counter() - t0
        # Tour validation: ensure permutation is valid
        tour = getattr(result, "tour", [])
        if tour and len(tour) == n:
            assert len(set(tour)) == n, f"[{algo_name}] Invalid tour: duplicate nodes"
            assert min(tour) == 0, f"[{algo_name}] Invalid tour: min node {min(tour)} != 0"
            assert max(tour) == n - 1, f"[{algo_name}] Invalid tour: max node {max(tour)} != {n-1}"
        gap_pct, gap_type = compute_gap(problem.name, result.tour_length, problem.optimal)
        from academic_benchmark.engine_core import RunResult
        return RunResult(
            problem=problem.name, algorithm=algo_name,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=int(result.tour_length),
            gap_pct=round(gap_pct, 4) if not math.isnan(gap_pct) else None,
            elapsed_sec=round(elapsed, 3),
            iterations=result.iterations,
            tour=tour,
        )
    executor.__name__ = f"sota_{algo_name.lower().replace('-', '_')}_executor"
    return executor

if _HAS_REGISTRY:
    for algo in ALL_ALGOS:
        algo_name = f"SOTA-{algo}"
        _AlgoReg.register(algo_name)(_make_sota_executor(algo))
        _AlgoReg.register_param_space(algo_name)(lambda a=algo: _build_sota_parameter_space(a))

# ── Interaktif Menü ve Main ───────────────────────────────────────────────────

def _clear() -> None:
    if sys.stdin.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    else:
        print("\n" * 3)


def _log_environment_info() -> None:
    import platform
    print(f"[ENV] OS: {platform.system()} {platform.release()}")
    print(f"[ENV] Python: {sys.version.split()[0]}")
    try:
        import numpy
        print(f"[ENV] NumPy: {numpy.__version__}")
    except ImportError:
        print("[ENV] NumPy: N/A")
    try:
        import numba
        print(f"[ENV] Numba: {numba.__version__}")
    except ImportError:
        print("[ENV] Numba: N/A")
    print(f"[ENV] CPU: {cpu_count()} cores")


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


def _select_algorithms() -> List[str]:
    print("\n[ALGORITMA SECIMI]")
    algos = list(ALL_ALGOS)
    for idx, name in enumerate(algos, 1):
        print(f"   [{idx}] {name}")
    raw = input("\nSeciminiz (virgul) / Enter=all: ").strip()
    
    if not raw:
        return algos
        
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(algos):
                selected.append(algos[idx])
    return selected if selected else algos


def _main_loop() -> int:
    _ensure_dirs()
    metadata = load_metadata(METADATA_PATH)
    
    parser = argparse.ArgumentParser(description="UniRide Master SOTA Engine")
    parser.add_argument("--mode", choices=["default", "tuning"], help="Calisma modu")
    parser.add_argument("--algos", help="Algoritma listesi (virgulle ayrilmis)")
    parser.add_argument("--problems", help="Problem listesi (virgulle ayrilmis)")
    parser.add_argument("--select", help="Universal problem selection syntax")
    parser.add_argument("--runs", type=int, help="Tekrar sayisi")
    parser.add_argument("--size-limit", type=int, help="Problem boyutu limiti")
    parser.add_argument("--workers", type=int, help="Paralel worker sayisi")
    args, _ = parser.parse_known_args()

    size_limit = args.size_limit if args.size_limit else 2500
    all_problems = load_problems(size_limit=size_limit)
    if not all_problems:
        print("[HATA] Gecerli TSPLIB problemi bulunamadi!")
        return 1
        
    if args.mode:
        selected_problems = all_problems
        selected_problems = _select_problems_from_args(args, all_problems)
            
        selected_algos = args.algos.split(",") if args.algos else list(ALL_ALGOS)
        runs = args.runs or 5
        workers = args.workers or min(4, cpu_count())

        
        if args.mode == "default":
            rows = _run_engine_default(selected_problems, selected_algos, runs, workers, metadata, skip_cached=True)
        else:
            best_params = _run_engine_tuning(selected_problems, selected_algos, runs, 12, workers, metadata, skip_cached=True)
            _save_best_solutions_post_tuning(best_params, selected_problems, selected_algos)
            
        # SOTA summary dosyasini yaz (TUM GECMISI DAHIL ET)
        summary_path = os.path.join(RESULTS_DIR, "benchmark_summary.csv")
        
        # Metadata'daki tum sonuclari topla
        all_rows = []
        res_data = metadata.get("results", {})
        for pname, algos in res_data.items():
            for algo_name, stats in algos.items():
                all_rows.append({
                    "problem": pname,
                    "strategy": algo_name,
                    "avg_length": stats.get("avg_cost"),
                    "avg_gap": stats.get("avg_gap"),
                    "avg_time_ms": stats.get("avg_time_sec", 0) * 1000.0,
                    "n_runs": stats.get("n_runs"),
                    "gap_type": stats.get("gap_type", "unknown")
                })

        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            fields = ["problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "gap_type"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in all_rows:
                writer.writerow({k: r.get(k) for k in fields})
        
        print(f"\n[TAMAM] Ozet rapor olusturuldu (Toplam {len(all_rows)} algoritma/problem): {summary_path}")
        return 0



    while True:
        _clear()
        _log_environment_info()
        print("=" * 70)
        print("           UNIRIDE MASTER SOTA ENGINE")
        print("=" * 70)
        print("\n--- MODLAR ---")
        print("  [1] DEFAULT (Standart/Best Parametrelerle Calistir)")
        print("  [2] TUNING  (DoE ile Parametre Optimizasyonu Yap)")
        print("\n--- DIGER ---")
        print("  [D] DASHBOARD (Streamlit ile Sonuclari Gorsellestir)")
        print("  [Q] Cikis")
        
        choice = input("\nSeciminiz: ").strip().upper()
        if choice == "Q":
            print("Cikis yapiliyor...")
            return 0
        if choice == "D":
            import subprocess
            print("\nDashboard aciliyor... Tarayicinizda http://localhost:8501 adresine gidin.")
            print("Durdurmak icin Ctrl+C basin.")
            try:
                subprocess.run(["streamlit", "run", str(Path(__file__).resolve().parent / "dashboard.py")])
            except KeyboardInterrupt:
                print("\nDashboard kapatildi.")
            input("Devam etmek icin Enter...")
            continue
            
        if choice not in {"1", "2"}:
            print("Gecersiz secim.")
            input("Devam etmek icin Enter...")
            continue
            
        if not selected_problems:
            print("[UYARI] Problem seçilmedi.")
            input("Devam etmek icin Enter...")
            continue

        selected_problems = _select_problems_from_args(args, all_problems, interactive=True)
        if not selected_problems:
            print("[UYARI] Problem seçilmedi.")
            input("Devam etmek icin Enter...")
            continue
            
        selected_algos = _select_algorithms()
        
        try:
            workers_input = input(f"Worker sayisi [varsayilan: {min(4, cpu_count())}]: ").strip()
            workers = int(workers_input) if workers_input else min(4, cpu_count())
        except ValueError:
            workers = 1
            
        if choice == "1":
            try:
                runs = int(input("Tekrar sayisi [varsayilan: 5]: ").strip() or "5")
            except ValueError:
                runs = 5
                
            skip = input("Onbellekte olanlari atla? [E/h]: ").strip().upper() != "H"
            
            _run_engine_default(
                problems=selected_problems,
                algos=selected_algos,
                n_runs=runs,
                workers=workers,
                metadata=metadata,
                skip_cached=skip
            )
            
        elif choice == "2":
            try:
                runs = int(input("Combo basi tekrar [varsayilan: 3]: ").strip() or "3")
                max_combos = int(input("Maks kombinasyon [varsayilan: 12]: ").strip() or "12")
            except ValueError:
                runs = 3
                max_combos = 12
                
            skip = input("Onbellekte olanlari atla? [E/h]: ").strip().upper() != "H"
            
            best_params = _run_engine_tuning(
                problems=selected_problems,
                algos=selected_algos,
                n_runs=runs,
                max_combos=max_combos,
                workers=workers,
                metadata=metadata,
                skip_cached=skip
            )
            _save_best_solutions_post_tuning(best_params, selected_problems, selected_algos)
            
        input("\nIslem tamamlandi. Menuye donmek icin Enter...")


if __name__ == "__main__":
    sys.exit(_main_loop())
