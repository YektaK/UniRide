#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart SOTA Benchmark — E²BSO / R²DMA / P-AOEA

Alternative to run_sota_benchmark.py modelled on the run_smart_benchmark_numba.py
style with:
  - Smart metadata-based caching  (skip already-completed runs)
  - Hash tracking for algorithm source files (auto-invalidate cache)
  - Interactive menu (problem/algorithm multi-select, fast/full modes)
  - Incremental JSON save after every completed task
  - Multiprocessing Pool (parallel) or sequential mode
  - ETA estimation based on completed timings
  - Graceful Ctrl+C — all completed results are saved
  - Reads TSPLIB problems from tsplib_problems/ALL_tsp.tar.gz
    (no separate tsplib_data/ directory required)

Usage:
    cd <repo_root>
    python academic_benchmark/run_smart_benchmark_sota.py
    python academic_benchmark/run_smart_benchmark_sota.py --non-interactive --problems berlin52,eil51
    python academic_benchmark/run_smart_benchmark_sota.py --runs 5 --size-limit 300
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import signal
import statistics
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

VERSION = "1.0.0"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# TSPLIB archive (contains individual .tsp.gz files)
TSPLIB_ARCHIVE = os.path.join(SCRIPT_DIR, "tsplib_problems", "ALL_tsp.tar.gz")
# Fallback: plain .tsp files in tsplib_data/ (run_sota_benchmark.py convention)
TSPLIB_DIR_FALLBACK = os.path.join(SCRIPT_DIR, "tsplib_data")

RESULTS_DIR = os.path.join(SCRIPT_DIR, "sota_results")
BENCHMARK_DB = os.path.join(SCRIPT_DIR, "benchmark_db")
METADATA_PATH = os.path.join(BENCHMARK_DB, "latest_metadata_sota.json")
HISTORY_DIR = os.path.join(BENCHMARK_DB, "history")

ALL_ALGOS = ["E2BSO-TSP", "R2DMA-TSP", "P-AOEA-TSP"]

# Worker pool limits
_MAX_RECOMMENDED_WORKERS = 16

# Adaptive solver config bounds (Numba-enabled)
_NUMBA_POP_MIN = 20
_NUMBA_POP_MAX = 60
_NUMBA_POP_DIV = 2      # population_size = n // _NUMBA_POP_DIV clamped
_NUMBA_ITER_MIN = 200
_NUMBA_ITER_MAX = 500
_NUMBA_ITER_FACTOR = 5  # max_iterations = n * factor clamped
# Python-fallback (no Numba) — smaller budgets to avoid 85-second runs
_PY_POP_MIN = 15
_PY_POP_MAX = 35
_PY_POP_DIV = 3
_PY_ITER_MIN = 100
_PY_ITER_MAX = 250
_PY_ITER_FACTOR = 3

# Source files to hash-track for cache invalidation
ALGORITHMS_TO_CHECK: Dict[str, str] = {
    "E2BSO_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "e2bso_tsp.py"),
    "R2DMA_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "r2dma_tsp.py"),
    "PAOEA_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "paoea_tsp.py"),
    "LSEngine": os.path.join(SCRIPT_DIR, "sota_tsp", "ls_engine.py"),
    "RepairOps": os.path.join(SCRIPT_DIR, "sota_tsp", "repair_ops.py"),
    "DestroyOps": os.path.join(SCRIPT_DIR, "sota_tsp", "destroy_ops.py"),
}

# Known TSPLIB optimal values
TSPLIB_OPTIMALS: Dict[str, int] = {
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroa100": 21282, "krob100": 22141, "kroc100": 20749, "krod100": 21294,
    "kroe100": 22068, "eil101": 629, "pr107": 44303, "pr124": 59030,
    "bier127": 118282, "ch130": 6110, "ch150": 6528, "kroa150": 26524,
    "krob150": 26130, "pr152": 73682, "u159": 42080, "rat195": 2323,
    "d198": 15780, "kroa200": 29368, "krob200": 29437, "ts225": 126643,
    "tsp225": 3916, "pr226": 80369, "gil262": 2378, "pr264": 49135,
    "a280": 2579, "pr299": 48191, "lin318": 42029, "rd400": 15281,
    "fl417": 11861, "pr439": 107217, "pcb442": 50778, "d493": 35002,
    "u574": 36905, "rat575": 6773, "p654": 34643, "d657": 48912,
    "u724": 41910, "rat783": 8806, "pr1002": 259045, "u1060": 224094,
    "vm1084": 239297, "pcb1173": 56892, "d1291": 50801, "rl1304": 252948,
    "rl1323": 270199, "nrw1379": 56638, "fl1400": 20127, "u1432": 152970,
    "fl1577": 22249, "d1655": 62128, "vm1748": 336556, "u1817": 57201,
    "rl1889": 316536, "d2103": 80450, "u2152": 64253, "u2319": 234256,
    "pr2392": 378032, "pcb3038": 137694, "fl3795": 28772, "fnl4461": 182566,
    "lin105": 14379, "rd100": 7910, "pr136": 96772, "pr144": 58537,
    "att48": 10628, "att532": 27686, "burma14": 3323, "bayg29": 1610,
    "bays29": 2020, "brazil58": 25395, "dantzig42": 699, "gr17": 2085,
    "gr21": 2707, "gr24": 1272, "gr48": 5046, "gr96": 55209,
    "gr120": 6942, "gr137": 69853, "gr202": 40160, "gr229": 134602,
    "gr431": 171414, "gr666": 294358, "hk48": 11461, "swiss42": 1273,
    "ulysses16": 6859, "ulysses22": 7013,
}


# ── Graceful shutdown ─────────────────────────────────────────────────────────

_shutdown_requested = False
_current_metadata: Optional[Dict] = None
_current_results: List[Dict] = []


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] Shutdown requested — saving completed results...")
    if _current_metadata and _current_results:
        _save_metadata(METADATA_PATH, _current_metadata)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(HISTORY_DIR, exist_ok=True)
        csv_path = os.path.join(HISTORY_DIR, f"interrupted_sota_{ts}.csv")
        if _current_results:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(_current_results[0].keys()))
                writer.writeheader()
                writer.writerows(_current_results)
            print(f"[OK] {len(_current_results)} result(s) saved to {csv_path}")
    sys.exit(130)


signal.signal(signal.SIGINT, _signal_handler)


# ── Metadata / caching helpers ────────────────────────────────────────────────

def _get_file_hash(filepath: str) -> str:
    import hashlib
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_latest_metadata(path: str) -> Dict[str, Any]:
    default: Dict[str, Any] = {
        "algorithm_hashes": {}, "file_hashes": {},
        "results": {}, "last_updated": "",
    }
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        # Keep both hash key names in sync
        fh = data.get("file_hashes", {})
        ah = data.get("algorithm_hashes", {})
        merged = {**fh, **ah}
        return {
            "algorithm_hashes": merged,
            "file_hashes": merged,
            "results": data.get("results", {}),
            "last_updated": data.get("last_updated", ""),
        }
    except Exception:
        return default


def _save_metadata(path: str, data: Dict[str, Any]):
    fh = data.get("file_hashes", {})
    ah = data.get("algorithm_hashes", {})
    merged = {**fh, **ah}
    data["file_hashes"] = merged
    data["algorithm_hashes"] = merged
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _update_algorithm_hashes(metadata: Dict[str, Any]):
    hashes = {k: _get_file_hash(v) for k, v in ALGORITHMS_TO_CHECK.items()}
    metadata["algorithm_hashes"] = hashes
    metadata["file_hashes"] = hashes


def _check_algorithms_status(metadata: Dict[str, Any]) -> Dict[str, str]:
    saved = metadata.get("algorithm_hashes") or metadata.get("file_hashes", {})
    status: Dict[str, str] = {}
    for name, path in ALGORITHMS_TO_CHECK.items():
        if not os.path.exists(path):
            status[name] = "FILE_MISSING"
        else:
            cur = _get_file_hash(path)
            if name not in saved:
                status[name] = "NEW"
            elif saved[name] != cur:
                status[name] = "CHANGED"
            else:
                status[name] = "CURRENT"
    return status


# ── TSPLIB loader ─────────────────────────────────────────────────────────────

@dataclass
class TSPProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[int]
    category: str  # small / medium / large


def _clean_tsplib_name(raw: str) -> str:
    """Normalize a TSPLIB problem name: lowercase, strip extensions and suffixes."""
    name = raw.lower().strip()
    for suffix in (".opt.tour", ".opt", ".tsp"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    # strip path separators
    name = name.split("/")[-1].split("\\")[-1]
    return name


def _parse_tsplib_text(content: str, name_hint: str = "") -> Optional[Dict[str, Any]]:
    """Parse TSPLIB text (handles CRLF, concatenated opt+tsp blocks).
    Returns a dict or None if the problem cannot be used."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # An archive entry may contain an opt-tour block followed by the TSP block.
    # Find the NODE_COORD_SECTION block first, then back-scan for its NAME/DIMENSION.
    coord_m = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)",
        content, re.DOTALL | re.I,
    )
    if not coord_m:
        return None

    # Use the portion of the file up-to and including that block
    block_start = content.rfind("\n", 0, coord_m.start())
    header_section = content[:coord_m.start()]

    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header_section, re.I)
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header_section, re.I)
    # Pick the LAST NAME in the header (handles concatenated blocks)
    name_matches = list(re.finditer(r"^NAME\s*[:\s]\s*(\S+)", header_section, re.I | re.M))
    if not dim_m:
        return None

    raw_name = name_matches[-1].group(1) if name_matches else name_hint
    name = _clean_tsplib_name(raw_name) or _clean_tsplib_name(name_hint)
    if not name:
        return None
    dimension = int(dim_m.group(1))
    ewt = ewt_m.group(1).upper() if ewt_m else "EUC_2D"
    # We support all coordinate-based types (distance accuracy varies but OK for benchmarking)
    supported = ("EUC_2D", "EUC_3D", "CEIL_2D", "ATT", "GEO", "GEOM", "NEU_2D")
    if ewt not in supported:
        return None  # EXPLICIT matrix etc. — skip

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
        "name": name, "dimension": dimension,
        "edge_weight_type": ewt, "coordinates": coords,
        "optimal": TSPLIB_OPTIMALS.get(name),
    }


def _category(n: int) -> str:
    if n <= 100:
        return "small"
    if n <= 500:
        return "medium"
    return "large"


def load_problems(size_limit: int = 500) -> List[TSPProblem]:
    """
    Load TSPLIB problems up to *size_limit* nodes.

    Source priority:
      1. tsplib_problems/ALL_tsp.tar.gz  (each entry is a .tsp.gz file)
      2. tsplib_data/*.tsp                (plain files, fallback)
    """
    problems: Dict[str, TSPProblem] = {}

    # ── Source 1: ALL_tsp.tar.gz ──────────────────────────────────────────────
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
            print(f"  [WARN] Failed to read archive: {exc}")

    # ── Source 2: tsplib_data/*.tsp (fallback) ────────────────────────────────
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
                problems.setdefault(p.name, p)  # archive takes precedence

    return sorted(problems.values(), key=lambda p: p.dimension)


# ── Numba detection ───────────────────────────────────────────────────────────

def _detect_numba() -> bool:
    try:
        _ab_dir = os.path.join(SCRIPT_DIR, "bildiri2026")
        if os.path.isdir(_ab_dir) and _ab_dir not in sys.path:
            sys.path.insert(0, _ab_dir)
        from core import numba_accel as _nb  # type: ignore
        return bool(_nb.NUMBA_AVAILABLE)
    except Exception:
        return False


_NUMBA_AVAILABLE = _detect_numba()


def make_deterministic_seed(problem_name: str, algo_name: str, run_idx: int, algo_idx: int, seed_base: int) -> int:
    """Create reproducible cross-process seed using hashlib (stable across runs)."""
    raw = f"{problem_name}|{algo_name}|{run_idx}|{algo_idx}|{seed_base}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    # Keep seed in signed 32-bit positive range for broad RNG compatibility.
    return int(digest[:8], 16) & 0x7FFFFFFF


# ── Adaptive solver config ────────────────────────────────────────────────────

def _make_solver_config(algo_name: str, n: int, numba_ok: bool) -> Dict[str, Any]:
    if numba_ok:
        ls_limit = 0.5
        pop = max(_NUMBA_POP_MIN, min(_NUMBA_POP_MAX, n // _NUMBA_POP_DIV))
        max_iter = max(_NUMBA_ITER_MIN, min(_NUMBA_ITER_MAX, n * _NUMBA_ITER_FACTOR))
    else:
        ls_limit = max(0.02, min(0.12, 0.003 * n))
        pop = max(_PY_POP_MIN, min(_PY_POP_MAX, n // _PY_POP_DIV))
        max_iter = max(_PY_ITER_MIN, min(_PY_ITER_MAX, n * _PY_ITER_FACTOR))

    configs: Dict[str, Dict[str, Any]] = {
        "E2BSO-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
            "ls_intensity_normal": "light",
            "ls_intensity_compress": "moderate",
        },
        "R2DMA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
        },
        "P-AOEA-TSP": {
            "population_size": pop,
            "max_iterations": max_iter,
            "ls_time_limit": ls_limit,
        },
    }
    return configs.get(algo_name, {})


# ── Worker function (module-level for multiprocessing pickling) ───────────────

def _run_solver_task(args: Tuple) -> Dict[str, Any]:
    """Run a single (problem, algo, seed) task. Safe for multiprocessing."""
    algo_name, coordinates, seed, run_idx, n_nodes, optimal, numba_ok = args
    try:
        _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from academic_benchmark.sota_tsp import (
            E2BSO_TSP, R2DMA_TSP, PAOEA_TSP,
            E2BSOTSPConfig, R2DMATSPConfig, PAOEAConfig,
        )
    except Exception as exc:
        return {"error": f"Import failed: {exc}", "algorithm": algo_name}

    cfg = _make_solver_config(algo_name, n_nodes, numba_ok)

    def _build(seed_val: int):
        if algo_name == "E2BSO-TSP":
            return E2BSO_TSP(E2BSOTSPConfig(seed=seed_val, **cfg))
        if algo_name == "R2DMA-TSP":
            return R2DMA_TSP(R2DMATSPConfig(seed=seed_val, **cfg))
        if algo_name == "P-AOEA-TSP":
            return PAOEA_TSP(PAOEAConfig(seed=seed_val, **cfg))
        return None

    solver = _build(seed)
    if solver is None:
        return {"error": f"Unknown algorithm: {algo_name}", "algorithm": algo_name}

    try:
        t0 = time.perf_counter()
        result = solver.solve(coordinates)
        elapsed = time.perf_counter() - t0
    except Exception as exc:
        import traceback
        return {
            "error": f"{algo_name} crashed: {exc}\n{traceback.format_exc()}",
            "algorithm": algo_name,
        }

    gap = float("nan")
    if optimal and optimal > 0:
        gap = (result.tour_length - optimal) / optimal * 100.0

    return {
        "algorithm": algo_name,
        "run": run_idx + 1,
        "seed": seed,
        "dimension": n_nodes,
        "optimal": optimal,
        "tour_cost": int(result.tour_length),
        "gap_pct": round(gap, 4) if not math.isnan(gap) else None,
        "elapsed_sec": round(elapsed, 3),
        "iterations": result.iterations,
    }


# ── CPU helper ────────────────────────────────────────────────────────────────

def _get_cpu_info() -> Dict[str, Any]:
    try:
        import psutil
        physical = psutil.cpu_count(logical=False) or cpu_count()
        logical = psutil.cpu_count(logical=True) or cpu_count()
    except ImportError:
        physical = cpu_count()
        logical = cpu_count()
    smt = logical > physical
    recommended = physical if smt else max(1, physical - 1)
    recommended = min(recommended, _MAX_RECOMMENDED_WORKERS)
    import platform
    return {
        "physical": physical,
        "logical": logical,
        "smt": smt,
        "recommended": recommended,
        "platform": platform.processor() or platform.machine(),
    }


def _select_worker_count() -> int:
    info = _get_cpu_info()
    rec = info["recommended"]
    print("\n" + "=" * 60)
    print("[CPU] ISLEMCI BILGILERI")
    print("=" * 60)
    print(f"   Platform      : {info['platform']}")
    print(f"   Fiziksel Cekirdek : {info['physical']}")
    print(f"   Mantiksal Cekirdek: {info['logical']}")
    print(f"\n[ONERI] Optimal worker sayisi: {rec}")
    if info["smt"]:
        print("   - CPU-bound islemler icin fiziksel cekirdek sayisi optimal")
    else:
        print("   - Sistem kaynaklarini korumak icin bir cekirdek bos birakiliyor")
    print("\n[SECIM] Worker sayisi belirleyin:")
    print(f"   [1] {rec} (Onerilen - Otomatik)")
    print(f"   [2] {min(info['logical'], 8)} (Standart - maks 8)")
    print(f"   [3] {min(info['logical'], _MAX_RECOMMENDED_WORKERS)} (Yuksek performans)")
    print(f"   [4] {info['logical']} (Maksimum)")
    print("   [C] Custom - Kendiniz girin")
    print(f"   [Enter] Varsayilan: {min(cpu_count(), 4)}")
    choice = input("\nSeciminiz: ").strip().upper()
    if choice in ("", "1"):
        return rec
    if choice == "2":
        return min(info["logical"], 8)
    if choice == "3":
        return min(info["logical"], _MAX_RECOMMENDED_WORKERS)
    if choice == "4":
        return info["logical"]
    if choice == "C":
        try:
            v = int(input(f"   Worker sayisi (1-{info['logical']}): ").strip())
            return max(1, min(v, info["logical"]))
        except ValueError:
            return rec
    return min(cpu_count(), 4)


# ── ETA / timing ─────────────────────────────────────────────────────────────

class _ETATracker:
    def __init__(self):
        self._times: List[float] = []
        self._by_algo: Dict[str, List[float]] = {}
        self._by_cat: Dict[str, List[float]] = {}

    def record(self, elapsed: float, algo: str = "", cat: str = ""):
        self._times.append(elapsed)
        if algo:
            self._by_algo.setdefault(algo, []).append(elapsed)
        if cat:
            self._by_cat.setdefault(cat, []).append(elapsed)

    def estimate_remaining(self, tasks_left: int) -> Optional[float]:
        if not self._times:
            return None
        avg = sum(self._times) / len(self._times)
        return avg * tasks_left

    def estimate_for(self, algo: str, cat: str) -> Optional[float]:
        if algo in self._by_algo:
            vals = self._by_algo[algo]
            return sum(vals) / len(vals)
        if cat in self._by_cat:
            vals = self._by_cat[cat]
            return sum(vals) / len(vals)
        if self._times:
            return sum(self._times) / len(self._times)
        return None


def _fmt_time(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m = int(s // 60)
    return f"{m}m{int(s % 60):02d}s"


def _gap_str(gap: Optional[float]) -> str:
    if gap is None or (isinstance(gap, float) and math.isnan(gap)):
        return "  N/A "
    return f"{gap:.2f}%"


def _make_bar(done: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "." * width
    filled = int(done / total * width)
    return "#" * filled + "." * (width - filled)


def _stdev(vals: List[float]) -> float:
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


# ── Incremental save ──────────────────────────────────────────────────────────

def _save_incremental(result: Dict, metadata: Dict):
    """Save a single run-level result into the cached metadata."""
    pname = result["problem"]
    algo = result["algorithm"]
    saved = metadata.setdefault("results", {})
    p_saved = saved.setdefault(pname, {})
    a_saved = p_saved.setdefault(algo, {
        "costs": [], "gaps": [], "times_sec": [],
        "best_cost": None, "best_gap": None,
        "avg_cost": None, "avg_gap": None, "avg_time_sec": None,
        "n_runs": 0, "timestamp": "",
    })
    a_saved["costs"].append(result["tour_cost"])
    if result["gap_pct"] is not None:
        a_saved["gaps"].append(result["gap_pct"])
    a_saved["times_sec"].append(result["elapsed_sec"])
    a_saved["n_runs"] = len(a_saved["costs"])
    a_saved["best_cost"] = min(a_saved["costs"])
    a_saved["best_gap"] = min(a_saved["gaps"]) if a_saved["gaps"] else None
    a_saved["avg_cost"] = statistics.mean(a_saved["costs"])
    a_saved["avg_gap"] = statistics.mean(a_saved["gaps"]) if a_saved["gaps"] else None
    a_saved["avg_time_sec"] = statistics.mean(a_saved["times_sec"])
    a_saved["timestamp"] = datetime.now().isoformat()
    metadata["last_updated"] = datetime.now().isoformat()
    _update_algorithm_hashes(metadata)
    _save_metadata(METADATA_PATH, metadata)


# ── UI helpers ────────────────────────────────────────────────────────────────

def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _print_banner(n_problems: int, algos: List[str], runs: int, workers: int, sequential: bool):
    W = 64
    mode = "sequential" if sequential else f"{workers} workers"
    numba_tag = "ACTIVE" if _NUMBA_AVAILABLE else "inactive (slower)"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n" + "=" * W)
    print(f"  SMART SOTA BENCHMARK v{VERSION}  —  {ts}")
    print(f"  E2BSO  ·  R2DMA  ·  P-AOEA  (TSP-native TSPLIB)")
    print("=" * W)
    print(f"  Numba   : {numba_tag}")
    print(f"  Mode    : {mode}")
    print(f"  Problems: {n_problems}  |  Algos: {len(algos)}  |  Runs: {runs}")
    print("=" * W)


def _print_status_overview(problems: List[TSPProblem], saved: Dict, algos: List[str]):
    print("\n" + "=" * 72)
    print("  BENCHMARK STATUS")
    print("=" * 72)
    by_cat: Dict[str, List[TSPProblem]] = {}
    for p in problems:
        by_cat.setdefault(p.category, []).append(p)

    total_done = 0
    total_cells = 0

    for cat_key, cat_label in [("small", "SMALL"), ("medium", "MEDIUM"), ("large", "LARGE")]:
        cat_probs = sorted(by_cat.get(cat_key, []), key=lambda x: x.dimension)
        if not cat_probs:
            continue
        print(f"\n  [{cat_label}]")
        for p in cat_probs:
            p_res = saved.get(p.name, {})
            done_algos = [a for a in algos if a in p_res and p_res[a].get("n_runs", 0) > 0]
            done = len(done_algos)
            total_cells += len(algos)
            total_done += done
            bar = _make_bar(done, len(algos))
            opt_str = str(p.optimal) if p.optimal else "N/A"
            status = "✓" if done == len(algos) else " "
            missing = [a for a in algos if a not in done_algos]
            miss_str = "" if done == len(algos) else f"  missing: {', '.join(missing)}"
            print(f"  {status} {p.name:<14} n={p.dimension:<5} opt={opt_str:<8} [{bar}] {done}/{len(algos)}{miss_str}")

    pct = total_done / total_cells * 100 if total_cells > 0 else 0
    print(f"\n  Total: {total_done}/{total_cells} ({pct:.1f}%)")
    print("=" * 72)


def _print_algo_status(algo_status: Dict[str, str]):
    print("\n  [ALGORITHM FILE STATUS]")
    any_changed = False
    for name, st in algo_status.items():
        sym = "[X]" if st == "FILE_MISSING" else ("[!]" if st == "CHANGED" else ("[*]" if st == "NEW" else "[OK]"))
        print(f"  {sym} {name:<20}: {st}")
        if st in ("CHANGED", "NEW"):
            any_changed = True
    return any_changed


def _multi_select_problems(all_problems: List[TSPProblem], saved: Dict, algos: List[str]) -> List[TSPProblem]:
    print("\n" + "=" * 70)
    print("  PROBLEM SELECTION")
    print("=" * 70)
    print("  Enter: numbers (1,3,5-8), 'all', 'small', 'medium', 'large'")
    print("-" * 70)

    by_cat: Dict[str, List[TSPProblem]] = {}
    for p in all_problems:
        by_cat.setdefault(p.category, []).append(p)

    idx = 1
    pmap: Dict[int, TSPProblem] = {}
    cat_ranges: Dict[str, Tuple[int, int]] = {}

    for cat_key, cat_label in [("small", "SMALL"), ("medium", "MEDIUM"), ("large", "LARGE")]:
        cat_list = sorted(by_cat.get(cat_key, []), key=lambda x: x.dimension)
        if not cat_list:
            continue
        print(f"\n  [{cat_label}]")
        start = idx
        for p in cat_list:
            p_res = saved.get(p.name, {})
            done = len([a for a in algos if a in p_res and p_res[a].get("n_runs", 0) > 0])
            status = " ✓" if done == len(algos) else (f" ({done}/{len(algos)})" if done else "")
            print(f"    {idx:>3}. {p.name:<14} n={p.dimension:<5}{status}")
            pmap[idx] = p
            idx += 1
        cat_ranges[cat_key] = (start, idx - 1)

    print("-" * 70)
    raw = input("  Selection: ").strip().lower()

    if raw in ("all", ""):
        return all_problems[:]
    for alias, key in [("small", "small"), ("s", "small"), ("medium", "medium"), ("m", "medium"),
                        ("large", "large"), ("l", "large")]:
        if raw == alias and key in cat_ranges:
            s, e = cat_ranges[key]
            sel = [pmap[i] for i in range(s, e + 1)]
            print(f"  → {len(sel)} {key} problems selected.")
            return sel

    selected: List[TSPProblem] = []
    seen: set = set()
    try:
        for part in raw.replace(" ", "").split(","):
            if "-" in part:
                lo, hi = part.split("-", 1)
                for i in range(int(lo), int(hi) + 1):
                    if i in pmap and pmap[i].name not in seen:
                        selected.append(pmap[i])
                        seen.add(pmap[i].name)
            else:
                i = int(part)
                if i in pmap and pmap[i].name not in seen:
                    selected.append(pmap[i])
                    seen.add(pmap[i].name)
    except (ValueError, KeyError):
        print("  Invalid selection.")
        return []

    print(f"  → {len(selected)} problem(s) selected.")
    return selected


def _multi_select_algos(all_algos: List[str]) -> List[str]:
    print("\n" + "=" * 70)
    print("  ALGORITHM SELECTION")
    print("=" * 70)
    amap: Dict[str, str] = {}
    for i, a in enumerate(all_algos, 1):
        print(f"    {i}. {a}")
        amap[str(i)] = a
        amap[a.lower()] = a

    print("-" * 70)
    raw = input("  Selection (all / numbers / names): ").strip().lower()
    if raw in ("all", "", "a"):
        return all_algos[:]

    selected: List[str] = []
    seen: set = set()
    for part in raw.replace(" ", "").split(","):
        if part in amap:
            a = amap[part]
            if a not in seen:
                selected.append(a)
                seen.add(a)
        else:
            # try partial name match
            matches = [a for a in all_algos if part in a.lower()]
            for a in matches:
                if a not in seen:
                    selected.append(a)
                    seen.add(a)
    if not selected:
        print("  No algorithms selected.")
        return []
    print(f"  → Selected: {', '.join(selected)}")
    return selected


def _show_test_summary(problems: List[TSPProblem], algos: List[str],
                        saved: Dict, runs: int, workers: int,
                        sequential: bool) -> Tuple[bool, bool]:
    """Show pre-run summary and ask for confirmation.
    Returns (proceed, skip_cached)."""
    _clear()
    total = len(problems) * len(algos) * runs
    cached_items = sum(
        1 for p in problems for a in algos
        if a in saved.get(p.name, {}) and saved[p.name][a].get("n_runs", 0) >= runs
    )
    total_pairs = len(problems) * len(algos)
    new_items = total_pairs - cached_items

    print("=" * 70)
    print("TEST OZETI (SOTA)")
    print("=" * 70)

    print(f"\n[STATS] Test Yapilacak:")
    print(f"   * Problemler: {len(problems)}")
    print(f"   * Algoritmalar: {len(algos)} ({', '.join(algos)})")
    print(f"   * Her problem {runs} kez calistirilacak")
    print(f"   * Toplam test sayisi: {total}")
    print(f"   * Calistirma modu: {'Sirali (Sequential)' if sequential else f'Paralel ({workers} worker)'}")

    if _NUMBA_AVAILABLE:
        print(f"\n[NUMBA] JIT Optimization: ENABLED")
    else:
        print(f"\n[NUMBA] JIT Optimization: DISABLED (python fallback)")

    skip_cached = False
    if cached_items:
        print(f"\n[CACHE] ONBELLEK DURUMU:")
        print(f"   * Daha once yapilmis: {cached_items} problem×algoritma")
        print(f"   * Henuz yapilmamis: {new_items} problem×algoritma")
        print("-" * 70)

        print("\n[SEARCH] Onbellekteki testler icin ne yapmak istersiniz?")
        print("   [S] Atla - Sadece yeni testleri yap (onerilen)")
        print("   [R] Yenile - Tum testleri bastan yap")
        print("   [Q] Cikis")
        ch = input("\nSeciminiz: ").strip().upper()
        if ch == "Q":
            return False, False
        if ch == "S":
            skip_cached = True
            print(f"\n√ {new_items} yeni problem×algoritma calistirilacak")
        else:
            print(f"\n√ Tum {total_pairs} problem×algoritma bastan yapilacak")

    effective_pairs = new_items if skip_cached else total_pairs
    estimated_seconds = 0.0
    if effective_pairs > 0:
        # rough estimate: average completed elapsed time if available, otherwise simple heuristic
        historical_times = []
        for p in problems:
            for a in algos:
                prev = saved.get(p.name, {}).get(a)
                if prev and prev.get("avg_time_sec"):
                    historical_times.append(float(prev["avg_time_sec"]))
        if historical_times:
            estimated_seconds = (sum(historical_times) / len(historical_times)) * effective_pairs * runs
        else:
            estimated_seconds = effective_pairs * runs * (0.6 if _NUMBA_AVAILABLE else 1.5)
        if not sequential and workers > 0:
            estimated_seconds /= workers
    print(f"\n[TIME] Tahmini Sure: ~{_fmt_time(estimated_seconds)}")

    cat_counts: Dict[str, int] = {}
    for p in problems:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
    print(f"\n[GRAPH] Kategori Dagilimi:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   * {cat}: {count} problem")

    print("\n[!] DIKKAT:")
    print("   * Ctrl+C ile istediginiz zaman guvenli cikis yapabilirsiniz")
    print("   * Sonuclar her run sonrasi otomatik kaydedilir")

    print("\n[Y] Basla    [Q] Cikis    [D] Detaylari Gor")
    ch = input("\nSeciminiz: ").strip().upper()
    if ch == "Q":
        return False, skip_cached
    elif ch == "D":
        print("\n[LIST] Problemler:")
        for i, p in enumerate(problems, 1):
            print(f"   {i:>3}. {p.name:<15} (n={p.dimension:<5}, opt={p.optimal})")
        input("\nDevam etmek icin Enter'a basin...")
        return _show_test_summary(problems, algos, saved, runs, workers, sequential)
    elif ch == "Y":
        return True, skip_cached
    else:
        return _show_test_summary(problems, algos, saved, runs, workers, sequential)

    return True, skip_cached


def _print_result_line(completed: int, total: int, res: Dict, eta: Optional[float]):
    gap_val = res.get("gap_pct")
    sym = "*" if gap_val is not None and gap_val <= 1 else ("+" if gap_val is not None and gap_val <= 5 else "o")
    cached = "[CACHED]" if res.get("cached") else ""
    eta_str = f" ETA: {_fmt_time(eta)}" if eta else ""
    gap_text = f"{gap_val:>6.2f}%" if gap_val is not None else "   N/A "
    print(
        f"  [{completed:>3}/{total}] {res['problem']:<12} {res['algorithm']:<12} "
        f"GAP: {gap_text} {sym} {res['elapsed_sec'] * 1000:>7.0f}ms {cached}{eta_str}",
        flush=True,
    )


# ── Final summary ─────────────────────────────────────────────────────────────

def _print_final_summary(all_results: List[Dict], problems: List[TSPProblem],
                          algos: List[str], t_total: float,
                          out_dir: str, ts: str):
    W = 84
    problems_by_name = {p.name: p for p in problems}

    lines = [
        "=" * W,
        f"  SMART SOTA BENCHMARK RESULTS v{VERSION}",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Total: {_fmt_time(t_total)}  |  {len(all_results)} runs",
        "=" * W, "",
    ]

    col_h = f"{'Algorithm':<14}|{'Best':>8}|{'Mean':>10}|{'StdDev':>8}|{'Gap(B)':>9}|{'Gap(A)':>9}|{'Time':>8}"
    sep_top = "+" + "-" * (W - 2) + "+"
    sep_mid = "|" + "-" * (W - 2) + "|"

    # Per-problem tables
    for pname in sorted(set(r["problem"] for r in all_results)):
        pinfo = problems_by_name.get(pname)
        opt = pinfo.optimal if pinfo else None
        opt_str = str(opt) if opt else "N/A"
        dim = pinfo.dimension if pinfo else "?"
        lines.append(sep_top)
        header_txt = f"| {pname} (n={dim}, optimal={opt_str})"
        lines.append(header_txt + " " * max(1, W - len(header_txt) - 1) + "|")
        lines.append(f"| {col_h} |")
        lines.append(sep_mid)
        p_results = [r for r in all_results if r["problem"] == pname]
        best_overall = min(r["tour_cost"] for r in p_results)
        for algo in algos:
            rs = [r for r in p_results if r["algorithm"] == algo]
            if not rs:
                continue
            costs = [r["tour_cost"] for r in rs]
            gaps = [r["gap_pct"] for r in rs if r.get("gap_pct") is not None]
            times = [r["elapsed_sec"] for r in rs]
            star = "*" if min(costs) <= best_overall else " "
            bg = min(gaps) if gaps else None
            ag = statistics.mean(gaps) if gaps else None
            lines.append(
                f"|{star}{algo:<13}|{min(costs):>8}|{statistics.mean(costs):>10.1f}"
                f"|{_stdev(costs):>8.1f}|{_gap_str(bg):>9}|{_gap_str(ag):>9}"
                f"|{statistics.mean(times):>7.2f}s|"
            )
        lines.append(sep_top)
        lines.append("")

    # Overall ranking
    ranking: Dict[str, List[float]] = {a: [] for a in algos}
    for r in all_results:
        if r.get("gap_pct") is not None:
            ranking[r["algorithm"]].append(r["gap_pct"])
    ranked = [(a, statistics.mean(g)) for a, g in ranking.items() if g]
    ranked.sort(key=lambda x: x[1])
    if ranked:
        lines += ["", "  OVERALL RANKING (avg gap over problems with known optimal)", "-" * 52]
        for pos, (algo, avg_gap) in enumerate(ranked, 1):
            best_gap = min(ranking[algo])
            lines.append(f"  {pos}. {algo:<16} avg={avg_gap:.2f}%  best={best_gap:.2f}%")
        lines.append("")

    text = "\n".join(lines)
    print("\n" + text)

    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, f"smart_sota_summary_{ts}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Summary : {txt_path}")

    json_path = os.path.join(out_dir, f"smart_sota_results_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": VERSION, "timestamp": ts,
            "total_time_sec": t_total, "algorithms": algos,
            "numba_available": _NUMBA_AVAILABLE,
            "problems": sorted(set(r["problem"] for r in all_results)),
            "results": all_results,
        }, f, indent=2)
    print(f"  JSON    : {json_path}")

    csv_path = os.path.join(out_dir, f"smart_sota_results_{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        headers = ["problem", "algorithm", "run", "seed", "dimension",
                   "optimal", "tour_cost", "gap_pct", "elapsed_sec", "iterations"]
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)
    print(f"  CSV     : {csv_path}")


# ── Core benchmark loop ───────────────────────────────────────────────────────

def _run_benchmark(
    problems: List[TSPProblem],
    algos: List[str],
    runs: int,
    seeds_base: int,
    skip_cached: bool,
    saved: Dict,
    metadata: Dict,
    workers: int,
    sequential: bool,
) -> List[Dict]:
    """Build task list and run, with incremental saves and progress output."""
    global _current_results

    tasks: List[Tuple] = []
    for ai, algo in enumerate(algos):
        for p in problems:
            # Determine how many runs already cached
            cached_runs = 0
            if skip_cached:
                ar = saved.get(p.name, {}).get(algo, {})
                cached_runs = ar.get("n_runs", 0)
            for run_idx in range(cached_runs, runs):
                seed = make_deterministic_seed(p.name, algo, run_idx, ai, seeds_base)
                tasks.append((
                    algo, p.coordinates, seed, run_idx,
                    p.dimension, p.optimal, _NUMBA_AVAILABLE,
                    p.name,  # extra tag (stripped before passing to worker)
                ))

    # Strip the extra pname tag before passing to worker
    worker_tasks = [t[:7] for t in tasks]
    pname_map = {i: t[7] for i, t in enumerate(tasks)}

    total = len(tasks)
    if total == 0:
        print("[PROGRESS] 0/0 cached, 0 to compute")
        print("  Nothing to run — all results already cached.")
        return []

    total_pairs = len(problems) * len(algos)
    cached_pairs = 0
    if skip_cached:
        for p in problems:
            for a in algos:
                ar = saved.get(p.name, {}).get(a, {})
                if ar.get("n_runs", 0) >= runs:
                    cached_pairs += 1
    print(f"[PROGRESS] {cached_pairs}/{total_pairs} cached, {total} to compute")

    all_results: List[Dict] = []
    eta = _ETATracker()
    completed = 0

    def _process(res: Dict, task_idx: int):
        nonlocal completed
        res["problem"] = pname_map[task_idx]
        all_results.append(res)
        _current_results.append(res)
        completed += 1
        eta.record(res["elapsed_sec"], res["algorithm"], "")
        remaining_eta = eta.estimate_remaining(total - completed)
        _print_result_line(completed, total, res, remaining_eta)
        _save_incremental(res, metadata)

    if sequential or sys.platform == "win32":
        for i, (task, wtask) in enumerate(zip(tasks, worker_tasks)):
            if _shutdown_requested:
                break
            res = _run_solver_task(wtask)
            if "error" in res:
                print(f"  ERROR: {res['error'][:120]}")
                continue
            _process(res, i)
    else:
        # Use ordered imap so task index stays aligned with pname_map
        with Pool(processes=workers) as pool:
            for i, res in enumerate(pool.imap(_run_solver_task, worker_tasks)):
                if _shutdown_requested:
                    break
                if "error" in res:
                    print(f"  ERROR: {res['error'][:120]}")
                    continue
                _process(res, i)

    return all_results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    global _current_metadata, _current_results, _shutdown_requested

    parser = argparse.ArgumentParser(description=f"Smart SOTA Benchmark v{VERSION}")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Skip interactive menus; use CLI args directly")
    parser.add_argument("--parallel", action="store_true",
                        help="Use multiprocessing Pool (default: sequential on Windows)")
    parser.add_argument("--problems", type=str, default=None,
                        help="Comma-separated problem names")
    parser.add_argument("--algorithms", type=str, default=None,
                        help="Comma-separated algorithm names")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--size-limit", type=int, default=300,
                        help="Max problem size (n) to include (default: 300)")
    parser.add_argument("--re-run", action="store_true",
                        help="Ignore cache and re-run all selected tests")
    args = parser.parse_args()

    SEED_BASE = 1000
    use_sequential = not args.parallel  # sequential by default; --parallel enables Pool
    cpu = os.cpu_count() or 1
    workers = args.workers if args.workers else min(cpu, 4)
    runs = args.runs

    # ── Load metadata & check algorithm hash status ──────────────────────────
    metadata = _get_latest_metadata(METADATA_PATH)
    algo_status = _check_algorithms_status(metadata)
    saved = metadata.get("results", {})
    _current_metadata = metadata

    # ── Load problems ────────────────────────────────────────────────────────
    print("  Loading TSPLIB problems from archive…", end="", flush=True)
    all_problems = load_problems(args.size_limit)
    print(f" {len(all_problems)} loaded.")

    if not all_problems:
        print(f"  No problems found. Expected archive at:\n    {TSPLIB_ARCHIVE}")
        return 1

    all_algo_names = ALL_ALGOS[:]

    # ── Non-interactive (CLI) mode ───────────────────────────────────────────
    if args.non_interactive:
        selected_problems = all_problems
        if args.problems:
            names = {n.strip().lower() for n in args.problems.split(",")}
            selected_problems = [p for p in all_problems if p.name in names]
        selected_algos = all_algo_names[:]
        if args.algorithms:
            names_a = {a.strip() for a in args.algorithms.split(",")}
            selected_algos = [a for a in all_algo_names if a in names_a]

        if not selected_problems:
            print("  No matching problems.")
            return 1
        if not selected_algos:
            print("  No matching algorithms.")
            return 1

        _print_banner(len(selected_problems), selected_algos, runs, workers, use_sequential)
        t0_total = time.perf_counter()
        results = _run_benchmark(
            selected_problems, selected_algos, runs, SEED_BASE,
            not args.re_run, saved, metadata, workers, use_sequential,
        )
        t_total = time.perf_counter() - t0_total
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if results:
            _print_final_summary(results, selected_problems, selected_algos, t_total, RESULTS_DIR, ts)
        return 0

    # ── Interactive mode ─────────────────────────────────────────────────────
    while True:
        _shutdown_requested = False
        _clear()

        _print_banner(len(all_problems), all_algo_names, runs, workers, use_sequential)
        any_changed = _print_algo_status(algo_status)
        _print_status_overview(all_problems, saved, all_algo_names)

        print("\n  MAIN MENU")
        print("  ─────────────────────────────────────────────────────────")
        print("  [A]  Force re-run: re-test all changed/new algorithm files")
        print("  [B]  Complete missing: only run untested problem×algo pairs")
        print("  [C]  Quick mode: small problems only, all algorithms")
        print("  [D]  Full run: all problems and algorithms (overwrite cache)")
        print("  [E]  Custom: select problems and algorithms manually")
        print("  [S]  Status detail: view cached results for a specific problem")
        print("  [Q]  Quit")
        print("  ─────────────────────────────────────────────────────────")
        choice = input("\n  Choice: ").strip().upper()

        if choice == "Q":
            print("  Exiting.")
            break

        if choice == "S":
            _interactive_detail(all_problems, saved, all_algo_names)
            input("\n  Press Enter to return to main menu…")
            continue

        if choice == "H":
            _show_algorithm_info()
            input("\n  Press Enter to return to main menu…")
            continue

        # Determine problem/algo lists
        selected_problems: List[TSPProblem] = []
        selected_algos: List[str] = []
        skip_cached = True

        if choice == "A":
            if not any_changed:
                print("  No changed algorithm files detected. Cache is current.")
                input("  Press Enter…")
                continue
            selected_problems = all_problems[:]
            selected_algos = all_algo_names[:]
            skip_cached = False

        elif choice == "B":
            for p in all_problems:
                p_res = saved.get(p.name, {})
                missing = [a for a in all_algo_names if a not in p_res or p_res[a].get("n_runs", 0) == 0]
                if missing:
                    selected_problems.append(p)
            selected_algos = all_algo_names[:]
            if not selected_problems:
                print("  Nothing missing — all combinations already cached.")
                input("  Press Enter…")
                continue

        elif choice == "C":
            selected_problems = [p for p in all_problems if p.category == "small"]
            selected_algos = all_algo_names[:]

        elif choice == "D":
            selected_problems = all_problems[:]
            selected_algos = all_algo_names[:]
            skip_cached = False

        elif choice == "E":
            selected_problems = _multi_select_problems(all_problems, saved, all_algo_names)
            if not selected_problems:
                input("  Press Enter…")
                continue
            selected_algos = _multi_select_algos(all_algo_names)
            if not selected_algos:
                input("  Press Enter…")
                continue

        else:
            print("  Invalid choice.")
            input("  Press Enter…")
            continue

        if not selected_problems:
            print("  No problems to run.")
            input("  Press Enter…")
            continue

        # ── Run count / worker selection ─────────────────────────────────
        print(f"\n[RUNS] CALISTIRMA SAYISI SECIN:")
        print(f"   Varsayilan: {runs}")
        print("   [3] 3 run (hizli test)")
        print("   [5] 5 run (standart)")
        print("   [10] 10 run (detayli)")
        print("   [Enter] Varsayilan kullan")
        ri = input("\nSeciminiz: ").strip()
        if ri.isdigit() and int(ri) >= 1:
            runs = int(ri)
        print(f"   -> {runs} run secildi")

        workers = _select_worker_count()
        print(f"\n[OK] {workers} worker kullanilacak")

        total_tests = len(selected_problems) * len(selected_algos)
        print(f"\n[START] TEST BASLIYOR (SOTA)...")
        print(f"   [CONFIG] Paralel worker sayisi: {workers}")
        print(f"   [CONFIG] Her problem {runs} kez calistirilacak")
        if skip_cached:
            print(f"   Toplam: {len(selected_problems)} problem x {len(selected_algos)} algoritma")
        else:
            print(f"   Toplam: {len(selected_problems)} problem x {len(selected_algos)} algoritma = {total_tests} test")

        print("\n[MODE] CALISTIRMA MODU SECIN:")
        print("   [S] Sirali (Sequential) - Anlik progress gosterimi (onerilen)")
        print("   [P] Paralel - Daha hizli ama toplu sonuc")
        print(f"   [Enter] Mevcut mod: {'S' if use_sequential else 'P'}")
        mode_choice = input("\nSeciminiz [S/P]: ").strip().upper()
        if mode_choice == "S":
            use_sequential = True
        elif mode_choice == "P":
            use_sequential = False

        if use_sequential:
            print("\n[MODE] Sirali mod secildi - her sonuc aninda gorunecek")
        else:
            print(f"\n[MODE] Paralel mod secildi - {workers} worker")

        # ── Confirm ───────────────────────────────────────────────────────
        proceed, skip_cached = _show_test_summary(
            selected_problems, selected_algos, saved, runs, workers, use_sequential
        )
        if not proceed:
            print("  Cancelled.")
            input("  Press Enter…")
            continue

        # ── Execute ───────────────────────────────────────────────────────
        _current_results = []
        t0_total = time.perf_counter()
        results = _run_benchmark(
            selected_problems, selected_algos, runs, SEED_BASE,
            skip_cached, saved, metadata, workers, use_sequential,
        )
        t_total = time.perf_counter() - t0_total

        if results:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            _print_final_summary(results, selected_problems, selected_algos, t_total, RESULTS_DIR, ts)

        # Refresh saved after run
        saved = metadata.get("results", {})
        algo_status = _check_algorithms_status(metadata)

        if _shutdown_requested:
            print("\n  Interrupted. Partial results saved.")
            return 130

        input("\n  Press Enter to return to main menu…")

    return 0


# ── Per-problem detail viewer ─────────────────────────────────────────────────

def _interactive_detail(all_problems: List[TSPProblem], saved: Dict, algos: List[str]):
    pdict = {p.name: p for p in all_problems}
    print("\n  Enter a problem name (e.g. berlin52) or 'list'. Empty = exit.")
    while True:
        raw = input("  > ").strip().lower()
        if not raw:
            break
        if raw == "list":
            for p in sorted(all_problems, key=lambda x: x.dimension):
                print(f"    {p.name:<14} n={p.dimension:<5} opt={p.optimal or 'N/A'}")
            continue
        if raw in pdict:
            p = pdict[raw]
            p_res = saved.get(p.name, {})
            print(f"\n  {p.name} (n={p.dimension}, optimal={p.optimal or 'N/A'})")
            print("  " + "-" * 68)
            for algo in algos:
                if algo in p_res:
                    d = p_res[algo]
                    bg = _gap_str(d.get("best_gap"))
                    ag = _gap_str(d.get("avg_gap"))
                    at = d.get("avg_time_sec", 0)
                    print(f"  ✓ {algo:<14} {d.get('n_runs', '?'):>2} runs | "
                          f"best_cost={d.get('best_cost', '?'):>8}  "
                          f"gap(B)={bg}  gap(A)={ag}  "
                          f"avg_time={at:.3f}s")
                else:
                    print(f"  ✗ {algo:<14} not cached")
        else:
            matches = [p.name for p in all_problems if raw in p.name]
            if matches:
                print(f"  Not found. Similar: {', '.join(matches[:5])}")
            else:
                print(f"  '{raw}' not found. Type 'list' to see all problems.")


# ── Algorithm info ────────────────────────────────────────────────────────────

def _show_algorithm_info():
    _clear()
    print("=" * 70)
    print("  SOTA ALGORITHM CATALOGUE")
    print("=" * 70)
    info = {
        "E2BSO-TSP": {
            "full_name": "Enhanced Entropy-Balanced Swarm Optimization",
            "complexity": "O(pop × iter × n²)",
            "features": ["Edge-entropy diversity measure", "LAHC acceptance", "ALNS destroy/repair",
                         "3-phase adaptive (INJECT / NORMAL / COMPRESS)"],
        },
        "R2DMA-TSP": {
            "full_name": "Resonance-Reinforced Destroy-and-Merge Algorithm",
            "complexity": "O(pop × iter × n²)",
            "features": ["6-dim resonance metric", "OX crossover", "SA acceptance",
                         "Diversity pulse injection", "Adaptive θ threshold"],
        },
        "P-AOEA-TSP": {
            "full_name": "Production Adaptive Operator Evolution Algorithm",
            "complexity": "O(pop × iter × n²)",
            "features": ["Operator genome evolution", "SA / LAHC / RTR acceptance",
                         "Adaptive destroy intensity", "Tournament selection"],
        },
    }
    for name, d in info.items():
        print(f"\n  [{name}]  {d['full_name']}")
        print(f"    Complexity : {d['complexity']}")
        print(f"    Features:")
        for f in d["features"]:
            print(f"      · {f}")
    print("\n  Numba status: " + ("ENABLED — 10-50× speedup" if _NUMBA_AVAILABLE else "disabled (install numba)"))


if __name__ == "__main__":
    sys.exit(main())
