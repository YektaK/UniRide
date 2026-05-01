#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark - NUMBA DOE / PARAMETER OPTIMIZATION

Tek dosyada:
- deney tasarimi / parametre taramasi
- resume/caching
- tuned benchmark kosusu
- Numba benchmark runtime ile uyumlu profil secimi
"""

import argparse
import csv
import io
import itertools
import json
import math
import os
import platform
import random
import statistics
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "optimizer_api"))

from academic_benchmark.dataset_loader import BenchmarkDatasetLoader
from academic_benchmark.utils_benchmark import get_file_hash, save_metadata
from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
    BENCHMARK_PROFILE as DEFAULT_PROFILE,
    STRATEGIES,
    VALID_BENCHMARK_PROFILES,
    _run_meta_heuristic,
    apply_local_search,
    convert_route_to_indices,
    create_duration_func,
    print_summary_table,
    run_single_test,
)
from optimizer_api.utils.local_search_numba import LocalSearchType

RESULTS_DIR = os.path.join(SCRIPT_DIR, "benchmark_db", "doe_numba")
CONFIGS_DIR = os.path.join(RESULTS_DIR, "configs")
HISTORIES_DIR = os.path.join(RESULTS_DIR, "histories")
METADATA_PATH = os.path.join(RESULTS_DIR, "latest_metadata_numba_doe.json")
TUNING_PROGRESS_CSV = os.path.join(RESULTS_DIR, "tuning_progress.csv")
BENCHMARK_PROGRESS_CSV = os.path.join(RESULTS_DIR, "benchmark_progress.csv")
BEST_PARAMS_JSON = os.path.join(RESULTS_DIR, "best_params.json")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "benchmark_summary.csv")

ALGORITHMS_TO_CHECK = {
    "BenchmarkRunner_NUMBA": os.path.join(PROJECT_ROOT, "optimizer_api", "tests", "run_interactive_benchmark_v2_numba.py"),
    "GA_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "ga_strategy.py"),
    "PSO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "pso_strategy.py"),
    "GWO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "gwo_strategy.py"),
    "HHO_Strategy": os.path.join(PROJECT_ROOT, "optimizer_api", "strategies", "hho_strategy.py"),
}

PARAM_VALIDATORS = {
    "pop_size": (1, 10000, int),
    "swarm_size": (1, 10000, int),
    "hawks": (1, 10000, int),
    "pack_size": (1, 10000, int),
    "generations": (1, 100000, int),
    "iterations": (1, 100000, int),
    "max_iterations": (1, 100000, int),
    "mutation_rate": (0.0, 1.0, float),
    "elite_size": (1, 100, int),
    "w": (0.0, 2.0, float),
    "c1": (0.0, 5.0, float),
    "c2": (0.0, 5.0, float),
}

_shutdown_requested = False
_current_metadata: Optional[Dict[str, Any]] = None
_current_rows: List[Dict[str, Any]] = []
NUM_WORKERS = min(cpu_count(), 4)
BENCHMARK_PROFILE = DEFAULT_PROFILE if DEFAULT_PROFILE in VALID_BENCHMARK_PROFILES else "quality_first"


@dataclass
class DOEProblem:
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
    name: str
    payload: Any
    default_params: Dict[str, Any]
    algorithm_type: str


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    if _current_metadata is not None:
        _persist_metadata(_current_metadata)
    sys.exit(130)


signal.signal(signal.SIGINT, _signal_handler)


def _ensure_dirs() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(HISTORIES_DIR, exist_ok=True)


def _load_metadata() -> Dict[str, Any]:
    if not os.path.exists(METADATA_PATH):
        return {"algorithm_hashes": {}, "results": {}, "best_params": {}, "last_updated": ""}
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"algorithm_hashes": {}, "results": {}, "best_params": {}, "last_updated": ""}


def _persist_metadata(metadata: Dict[str, Any]) -> None:
    metadata["last_updated"] = datetime.now().isoformat()
    metadata["algorithm_hashes"] = {name: get_file_hash(path) for name, path in ALGORITHMS_TO_CHECK.items() if os.path.exists(path)}
    save_metadata(METADATA_PATH, metadata)


def run_single_test_with_matrix(
    problem,
    strategy_instance,
    seed: int,
    params,
    time_matrix: List[List[float]],
) -> Dict[str, Any]:
    dimension = problem.dimension
    run_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        run_params = params.copy()
    elif isinstance(params, int):
        run_params = {"max_iterations": params}

    matrix: Dict[str, Dict[str, float]] = {}
    for i in range(dimension):
        key_i = f"L{i+1}"
        matrix[key_i] = {}
        for j in range(dimension):
            matrix[key_i][f"L{j+1}"] = float(time_matrix[i][j])

    duration_func = create_duration_func(matrix)
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
    gap = ((tour_length - optimal) / optimal) * 100 if optimal else float("nan")

    return {
        "tour_length": tour_length,
        "gap": gap,
        "time_ms": elapsed * 1000,
        "algorithm_type": algorithm_type,
    }


def _normalize_strategy_entry(entry: Tuple[Any, ...]) -> StrategySpec:
    name = entry[0]
    payload = entry[1]
    params = entry[2].copy() if len(entry) > 2 and isinstance(entry[2], dict) else {}
    algorithm_type = str(params.get("algorithm_type", "local_search" if isinstance(payload, LocalSearchType) else "meta_heuristic"))
    return StrategySpec(name=name, payload=payload, default_params=params, algorithm_type=algorithm_type)


def _all_strategy_specs() -> List[StrategySpec]:
    return [_normalize_strategy_entry(entry) for entry in STRATEGIES]


def _load_problems(size_mode: str) -> List[DOEProblem]:
    loader = BenchmarkDatasetLoader(tsplib_folder=os.path.join("optimizer_api", "tests", "tsplib_data"))
    raw = loader.load_all_datasets()
    categories = {
        "small": {"small"},
        "medium": {"medium"},
        "large": {"large"},
        "all": {"small", "medium", "large"},
    }
    allowed = categories.get(size_mode, {"small", "medium", "large"})
    problems: List[DOEProblem] = []
    for problem in raw:
        if problem.category not in allowed:
            continue
        problems.append(
            DOEProblem(
                name=problem.name,
                dimension=problem.dimension,
                coordinates=problem.coordinates,
                optimal=problem.optimal,
                category=problem.category,
                source=getattr(problem, "source", "tsplib"),
            )
        )
    return problems


def _load_problems_unified(size_mode: str = "all") -> List[DOEProblem]:
    problems = _load_problems(size_mode)
    data_dir = os.path.join(SCRIPT_DIR, "data")
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".json") and f != "tuned_parameters_db.json":
                fpath = os.path.join(data_dir, f)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if "time_matrix" not in data:
                        continue
                    matrix = data["time_matrix"]
                    name = data.get("name", f.replace(".json", ""))
                    dim = len(matrix)
                    optimal = data.get("optimal")
                    cat = "small" if dim <= 100 else ("medium" if dim <= 500 else "large")
                    if size_mode != "all" and cat != size_mode:
                        continue
                    problems.append(DOEProblem(
                        name=name, dimension=dim, coordinates=[(0.0, 0.0)] * dim,
                        optimal=optimal, category=cat, source="time_matrix",
                        is_time_matrix=True, time_matrix=matrix,
                    ))
                except Exception:
                    continue
    return problems


def _select_benchmark_profile(current_profile: str) -> str:
    current = (current_profile or "quality_first").strip().lower()
    if current not in VALID_BENCHMARK_PROFILES:
        current = "quality_first"
    print("\n[PROFILE] Benchmark profili secin:")
    print("   [1] quality_first")
    print("   [2] baseline")
    choice = input(f"Seciminiz [varsayilan: {current}]: ").strip().lower()
    if choice in {"2", "baseline", "b"}:
        return "baseline"
    return "quality_first" if choice in {"", "1", "quality_first", "q"} else current


def _select_worker_count() -> int:
    logical = cpu_count()
    recommended = max(1, min(logical, 8))
    raw = input(f"Worker sayisi [varsayilan: {recommended}]: ").strip()
    if not raw:
        return recommended
    try:
        return max(1, min(int(raw), logical))
    except ValueError:
        return recommended


def _clear() -> None:
    if sys.stdin.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    else:
        print("\n" * 3)


def _log_environment_info() -> None:
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


def _format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}sn"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}dk {secs}sn"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}sa {minutes}dk"


def _estimate_total_time(problems: List[DOEProblem], strategies: List[str], runs: int, workers: int) -> float:
    base_times = {"small": 0.3, "medium": 1.5, "large": 8.0}
    total = 0.0
    for problem in problems:
        total += base_times.get(problem.category, 1.0) * len(strategies) * runs
    return total / max(1, workers)


def _print_banner(problem_count: int, strategy_names: List[str], tuning_runs: int, workers: int, mode_label: str) -> None:
    print("=" * 70)
    print("        UNIRIDE NUMBA DOE BENCHMARK")
    print("=" * 70)
    print(f"\n[CONFIG] Profil: {BENCHMARK_PROFILE}")
    print(f"[CONFIG] Problem sayisi: {problem_count}")
    print(f"[CONFIG] Algoritmalar: {', '.join(strategy_names)}")
    print(f"[CONFIG] DOE tekrar: {tuning_runs}")
    print(f"[CONFIG] Worker: {workers}")
    print(f"[CONFIG] Mod: {mode_label}")


def _print_status_overview(problems: List[DOEProblem], strategy_names: List[str], best_params: Dict[str, Dict[str, Any]]) -> None:
    print("\n" + "=" * 80)
    print("DOE STATUS OVERVIEW")
    print("=" * 80)
    categories = {"small": 0, "medium": 0, "large": 0}
    for problem in problems:
        categories[problem.category] = categories.get(problem.category, 0) + 1
    for category, count in categories.items():
        print(f"  {category:<8}: {count} problem")
    tuned = sum(1 for problem in problems for strategy in strategy_names if f"{problem.name}::{strategy}" in best_params)
    total = len(problems) * len(strategy_names)
    print(f"\n[CACHE] Tuned pairler: {tuned}/{total}")


def _show_test_summary(
    problems: List[DOEProblem],
    strategy_names: List[str],
    best_params: Dict[str, Dict[str, Any]],
    tuning_runs: int,
    benchmark_runs: int,
    workers: int,
    sequential: bool,
    selection_label: str = "",
) -> Tuple[bool, bool]:
    _clear()
    total_pairs = len(problems) * len(strategy_names)
    cached_pairs = sum(1 for problem in problems for strategy in strategy_names if f"{problem.name}::{strategy}" in best_params)
    new_pairs = total_pairs - cached_pairs
    print("=" * 70)
    print("TEST OZETI (NUMBA DOE)")
    print("=" * 70)
    if selection_label:
        print(f"\n[SECIM] {selection_label}")
    print("\n[STATS] Test Yapilacak:")
    print(f"   * Problemler: {len(problems)}")
    for p in problems:
        print(f"      - {p.name} (n={p.dimension}, {p.category})")
    print(f"   * Algoritmalar: {len(strategy_names)} ({', '.join(strategy_names)})")
    print(f"   * DOE tuning run: {tuning_runs}")
    print(f"   * Final benchmark run: {benchmark_runs}")
    print(f"   * Calistirma modu: {'Sirali (Sequential)' if sequential else f'Paralel ({workers} worker)'}")
    skip_cached = False
    if cached_pairs:
        print("\n[CACHE] ONBELLEK DURUMU:")
        print(f"   * Daha once tune edilmis: {cached_pairs} problem×algoritma")
        print(f"   * Henuz tune edilmemis: {new_pairs} problem×algoritma")
        print("\n[SEARCH] Onbellekteki tune sonuclari icin ne yapmak istersiniz?")
        print("   [S] Atla - Sadece yeni pairleri tune et (onerilen)")
        print("   [R] Yenile - Tum tune islerini bastan yap")
        print("   [Q] Cikis")
        ch = input("\nSeciminiz: ").strip().upper()
        if ch == "Q":
            return False, False
        if ch == "S":
            skip_cached = True
    effective_pairs = new_pairs if skip_cached else total_pairs
    estimate = _estimate_total_time(problems, strategy_names, tuning_runs + benchmark_runs, workers)
    print(f"\n[TIME] Tahmini Sure: ~{_format_time(estimate if effective_pairs else 0)}")
    print("\n[!] DIKKAT:")
    print("   * Ctrl+C ile istediginiz zaman guvenli cikis yapabilirsiniz")
    print("   * Sonuclar her asamada otomatik kaydedilir")
    print("\n[Y] Basla    [Q] Cikis")
    ch = input("\nSeciminiz: ").strip().upper()
    return (ch == "Y"), skip_cached


def _print_progress_line(completed: int, total: int, result: Dict[str, Any], stage: str, cached: bool = False) -> None:
    sym = "*" if result.get("avg_gap", 100) <= 1 else ("+" if result.get("avg_gap", 100) <= 5 else "o")
    cached_text = "[CACHED]" if cached else ""
    print(
        f"  [{completed:>3}/{total}] {result['problem']:<12} {result['strategy']:<8} "
        f"GAP: {result.get('avg_gap', 0):>6.2f}% {sym} {result.get('avg_time_ms', 0):>7.0f}ms "
        f"[{stage}] {cached_text}",
        flush=True,
    )


def _show_detail_mode(problems: List[DOEProblem], best_params: Dict[str, Dict[str, Any]], strategy_names: List[str]) -> None:
    print("\n[DETAIL] Problem secin:")
    for idx, problem in enumerate(problems, 1):
        print(f"   [{idx}] {problem.name} (n={problem.dimension}, {problem.category})")
    raw = input("\nSeciminiz: ").strip()
    if not raw.isdigit():
        return
    idx = int(raw) - 1
    if idx < 0 or idx >= len(problems):
        return
    problem = problems[idx]
    print(f"\n[DETAIL] {problem.name}")
    for strategy in strategy_names:
        entry = best_params.get(f"{problem.name}::{strategy}")
        if not entry:
            print(f"   - {strategy:<8} : kayit yok")
            continue
        print(f"   - {strategy:<8} : avg={entry['avg_length']:.3f}, gap={entry['avg_gap']:.3f}%, time={entry['avg_time_ms']:.1f}ms")


def _select_run_count(label: str, default_value: int, allow_zero: bool = False) -> int:
    print(f"\n[RUNS] {label} CALISTIRMA SAYISI SECIN:")
    print(f"   Varsayilan: {default_value}")
    if allow_zero:
        print("   [0] 0 run (atla)")
    print("   [3] 3 run (hizli test)")
    print("   [5] 5 run (standart)")
    print("   [10] 10 run (detayli)")
    print("   [Enter] Varsayilan kullan")
    raw = input("\nSeciminiz: ").strip()
    if not raw:
        return default_value
    if raw.isdigit():
        val = int(raw)
        if val == 0 and allow_zero:
            return 0
        if val >= 1:
            return val
    return default_value


def _select_mode() -> bool:
    print("\n[MODE] CALISTIRMA MODU SECIN:")
    print("   [S] Sirali (Sequential) - Anlik progress gosterimi (onerilen)")
    print("   [P] Paralel - Daha hizli ama toplu sonuc")
    mode_choice = input("\nSeciminiz [S/P]: ").strip().upper()
    return mode_choice != "P"


def _select_problem_scope() -> str:
    print("\n[PROBLEM SET] Boyut secin: [1] small [2] medium [3] large [4] all")
    choice = input("Seciminiz [varsayilan: 1]: ").strip()
    return {"1": "small", "2": "medium", "3": "large", "4": "all", "": "small"}.get(choice, "small")


def _multi_select(items: Sequence[str], title: str) -> List[str]:
    print(f"\n[{title}]")
    for idx, item in enumerate(items, 1):
        print(f"   [{idx}] {item}")
    raw = input("Secimler (virgul) / Enter=all: ").strip()
    if not raw:
        return list(items)
    selected: List[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx])
                continue
        matches = [item for item in items if part.lower() in item.lower()]
        selected.extend(matches)
    seen = set()
    return [item for item in selected if not (item in seen or seen.add(item))]


def _parse_index_or_all_input(raw: str, item_count: int) -> Optional[List[int]]:
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(item_count))
    indices: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            print(f"  [HATA] Gecersiz giris: '{part}' - sayi veya 'all' bekleniyor")
            return None
        idx = int(part) - 1
        if idx < 0 or idx >= item_count:
            print(f"  [HATA] {part} aralik disi (1-{item_count} arasi olmali)")
            return None
        indices.append(idx)
    if not indices:
        print("  [HATA] Bos secim yapildi")
        return None
    seen: set = set()
    return [i for i in indices if not (i in seen or seen.add(i))]


def _select_problems_by_index(problems: List[DOEProblem]) -> Optional[List[DOEProblem]]:
    print("\n[PROBLEM SECIMI] Problem numaralarini girin (virgulle ayirin veya 'all'):")
    for idx, problem in enumerate(problems, 1):
        print(f"   [{idx}] {problem.name} (n={problem.dimension}, {problem.category})")
    raw = input("\nSeciminiz: ").strip()
    if not raw:
        print("  [HATA] Bos giris yapildi")
        return None
    indices = _parse_index_or_all_input(raw, len(problems))
    if indices is None:
        return None
    return [problems[i] for i in indices]


def _select_problem_mode_and_scope(all_problems: List[DOEProblem]) -> Tuple[List[DOEProblem], str]:
    print("\n[PROBLEM SECIM MODU]")
    print("   [1] Sinif bazli (small/medium/large/all)")
    print("   [2] Numara bazli (problem listesinden sec)")
    mode = input("Seciminiz [varsayilan: 1]: ").strip()
    if mode == "2":
        selected = _select_problems_by_index(all_problems)
        if selected is None:
            return [], "index"
        return selected, "index"
    scope = _select_problem_scope()
    filtered = [p for p in all_problems if p.category in ({scope} if scope != "all" else {"small", "medium", "large"})]
    return filtered, f"class:{scope}"


def _select_algorithms_numbered(all_specs: List[StrategySpec]) -> List[str]:
    names = [spec.name for spec in all_specs]
    print("\n[ALGORITMA SECIMI] Algoritma numaralarini girin (virgulle ayirin veya 'all'):")
    for idx, name in enumerate(names, 1):
        print(f"   [{idx}] {name}")
    while True:
        raw = input("\nSeciminiz: ").strip()
        if not raw:
            print("  [HATA] Bos giris yapildi, tekrar deneyin")
            continue
        indices = _parse_index_or_all_input(raw, len(names))
        if indices is None:
            continue
        return [names[i] for i in indices]


def _validate_param_value(key: str, raw: str, expected_type: type) -> Optional[Any]:
    validator = PARAM_VALIDATORS.get(key)
    try:
        if expected_type == bool:
            val = raw.lower() in ("true", "1", "t", "evet", "e")
        elif expected_type == float:
            val = float(raw)
        elif expected_type == int:
            val = int(raw)
        else:
            val = raw
        if validator:
            vmin, vmax, _ = validator
            if val < vmin or val > vmax:
                print(f"    [!] {key} aralik disi [{vmin}, {vmax}]: {val}")
                return None
        return val
    except ValueError:
        print(f"    [!] {key} icin gecersiz deger: {raw}")
        return None


def _edit_param_space(space: Dict[str, List[Any]], algo_name: str) -> Dict[str, List[Any]]:
    print(f"\n[PARAM] {algo_name} parametre uzayini duzenleyin (Enter = kabul):")
    result: Dict[str, List[Any]] = {}
    for key, vals in space.items():
        print(f"  {key} = {vals}")
        raw = input(f"    Yeni degerler (virgul) [{vals}]: ").strip()
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
            v = _validate_param_value(key, p, sample_type)
            if v is None:
                valid = False
                break
            new_vals.append(v)
        if valid and new_vals:
            result[key] = new_vals
        else:
            print(f"    [!] Gecersiz giris, mevcut degerler korunuyor: {vals}")
            result[key] = vals
    return result


def _input_params_for_pair(
    problem_name: str,
    algo_name: str,
    spec: StrategySpec,
    saved_params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base = saved_params.copy() if saved_params else spec.default_params.copy()
    source = "BEST" if saved_params else "DEFAULT"
    print(f"\n  [{problem_name} x {algo_name}] Parametreler ({source}):")
    result: Dict[str, Any] = {}
    for key, val in base.items():
        if key == "algorithm_type":
            result[key] = val
            continue
        raw = input(f"    {key} [{val}]: ").strip()
        if not raw:
            result[key] = val
            continue
        try:
            if isinstance(val, float):
                result[key] = float(raw)
            elif isinstance(val, int):
                result[key] = int(raw)
            elif isinstance(val, bool):
                result[key] = raw.lower() in ("true", "1", "t", "evet", "e")
            else:
                result[key] = raw
        except ValueError:
            print(f"      [!] Gecersiz deger, varsayilan kullaniliyor: {val}")
            result[key] = val
    return result


def _collect_benchmark_params(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    best_params: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    collected: Dict[str, Dict[str, Any]] = {}
    for problem in problems:
        for spec in specs:
            best_key = f"{problem.name}::{spec.name}"
            saved = best_params.get(best_key)
            saved_p = saved.get("params") if saved else None
            params = _input_params_for_pair(problem.name, spec.name, spec, saved_p)
            collected[best_key] = params
    return collected


def _run_benchmark_direct(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    param_map: Dict[str, Dict[str, Any]],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    tasks: List[Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]] = []
    for problem in problems:
        for spec in specs:
            key = f"{problem.name}::{spec.name}"
            params = param_map.get(key)
            if not params:
                continue
            tasks.append((_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, 1, benchmark_runs))

    results = _run_pool(tasks, workers)
    rows: List[Dict[str, Any]] = []
    fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "params_json"]
    total_results = len(results)
    for idx, result in enumerate(results, 1):
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["strategy"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if math.isnan(result["avg_gap"]) else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "params_json": json.dumps(result["params"], ensure_ascii=False, sort_keys=True),
        }
        rows.append(row)
        _append_csv_row(BENCHMARK_PROGRESS_CSV, fields, row)
        _print_progress_line(idx, total_results, result, "BENCH")

    metadata["results"] = {f"{row['problem']}::{row['strategy']}": row for row in rows}
    _persist_metadata(metadata)
    return rows


def _build_numba_parameter_space(spec: StrategySpec) -> Dict[str, List[Any]]:
    name = spec.name.upper()
    if name == "GA":
        return {
            "pop_size": [80, 120, 150],
            "generations": [250, 350, 500],
            "mutation_rate": [0.08, 0.12, 0.16],
            "elite_size": [4, 6, 8],
        }
    if name == "PSO":
        return {
            "swarm_size": [50, 80, 120],
            "iterations": [200, 300, 450],
            "w": [0.65, 0.72, 0.80],
            "c1": [1.4, 1.6, 1.9],
            "c2": [1.4, 1.6, 1.9],
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
    return {
        "max_iterations": [spec.default_params.get("max_iterations", 300)],
    }


def _param_product(space: Dict[str, List[Any]]) -> Iterable[Dict[str, Any]]:
    keys = list(space.keys())
    for values in itertools.product(*(space[key] for key in keys)):
        yield dict(zip(keys, values))


def _generate_combinations(space: Dict[str, List[Any]], max_combinations: int,
                           strategy: str = "sequential", random_seed: int = 42) -> List[Dict[str, Any]]:
    keys = list(space.keys())
    combos = [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]
    if len(combos) > max_combinations and strategy == "fractional_fallback":
        random.seed(random_seed)
        combos = random.sample(combos, max_combinations)
    else:
        combos = combos[:max_combinations]
    return combos


def _param_signature(params: Dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, ensure_ascii=False)


def _make_problem_dict(problem: DOEProblem) -> Dict[str, Any]:
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
    if isinstance(spec.payload, LocalSearchType):
        return spec.payload
    return spec.payload


def _evaluate_param_combo(task: Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]) -> Dict[str, Any]:
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
    if not getattr(problem, "optimal", None):
        class _ProblemWithSafeOptimal(_Problem):
            def __init__(self, data: Dict[str, Any]):
                super().__init__(data)
                self.optimal = 1
        effective_problem = _ProblemWithSafeOptimal(problem_dict)

    run_results: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for run_idx in range(n_runs):
        seed = 1000 + combo_idx * 100 + run_idx
        if is_time_matrix and time_matrix_data:
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
        "convergence_profile": convergence_profile,
    }


def _run_pool(tasks: List[Tuple], workers: int, on_result=None) -> List[Dict[str, Any]]:
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
    with Pool(processes=workers) as pool:
        for i, result in enumerate(pool.imap_unordered(_evaluate_param_combo, tasks)):
            results.append(result)
            if on_result:
                on_result(i, result, len(tasks))
    return results


def _append_csv_row(path: str, fieldnames: Sequence[str], row: Dict[str, Any]) -> None:
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _load_tuning_cache() -> set[Tuple[str, str, str]]:
    completed: set[Tuple[str, str, str]] = set()
    if not os.path.exists(TUNING_PROGRESS_CSV):
        return completed
    try:
        with open(TUNING_PROGRESS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                completed.add((row["problem"], row["strategy"], row["param_signature"]))
    except Exception:
        return completed
    return completed


def _tune_parameters(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    n_runs: int,
    max_combinations: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool,
    edited_spaces: Optional[Dict[str, Dict[str, List[Any]]]] = None,
) -> Dict[str, Dict[str, Any]]:
    completed = _load_tuning_cache()
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})
    tuning_tasks: List[Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]] = []

    for problem in problems:
        for spec in specs:
            space = edited_spaces.get(spec.name) if edited_spaces and spec.name in edited_spaces else _build_numba_parameter_space(spec)
            combos = _generate_combinations(space, max_combinations)
            for combo_idx, combo in enumerate(combos, 1):
                params = spec.default_params.copy()
                params.update(combo)
                params["algorithm_type"] = spec.algorithm_type
                sig = _param_signature(params)
                key = (problem.name, spec.name, sig)
                if skip_cached and key in completed:
                    continue
                tuning_tasks.append((_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), params, combo_idx, n_runs))

    results = _run_pool(tuning_tasks, workers)
    tuning_fields = [
        "timestamp", "problem", "strategy", "combo_idx", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "param_signature", "params_json"
    ]
    total_results = len(results)
    for idx, result in enumerate(results, 1):
        problem_name = result["problem"]
        strategy_name = result["strategy"]
        params = result["params"]
        sig = _param_signature(params)
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
        _append_csv_row(TUNING_PROGRESS_CSV, tuning_fields, row)
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
                "convergence_profile": result.get("convergence_profile", []),
            }
            _print_progress_line(idx, total_results, result, "TUNE")

    metadata["best_params"] = best_params
    with open(BEST_PARAMS_JSON, "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2, ensure_ascii=False)
    _persist_metadata(metadata)
    return best_params


def _run_benchmark_with_best(
    problems: List[DOEProblem],
    specs: List[StrategySpec],
    best_params: Dict[str, Dict[str, Any]],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    benchmark_tasks: List[Tuple[Dict[str, Any], str, Any, Dict[str, Any], int, int]] = []
    for problem in problems:
        for spec in specs:
            best_key = f"{problem.name}::{spec.name}"
            best_entry = best_params.get(best_key)
            if not best_entry:
                continue
            benchmark_tasks.append(
                (_make_problem_dict(problem), spec.name, _resolve_strategy_payload(spec), best_entry["params"], 1, benchmark_runs)
            )

    results = _run_pool(benchmark_tasks, workers)
    rows: List[Dict[str, Any]] = []
    fields = ["timestamp", "problem", "strategy", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "params_json"]
    total_results = len(results)
    for idx, result in enumerate(results, 1):
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["strategy"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if math.isnan(result["avg_gap"]) else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "params_json": json.dumps(result["params"], ensure_ascii=False, sort_keys=True),
        }
        rows.append(row)
        _append_csv_row(BENCHMARK_PROGRESS_CSV, fields, row)
        _print_progress_line(idx, total_results, result, "FINAL")

    metadata["results"] = {f"{row['problem']}::{row['strategy']}": row for row in rows}
    _persist_metadata(metadata)
    return rows


def _write_summary(rows: List[Dict[str, Any]]) -> None:
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
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


def _validate_config(config: Dict, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Tuple[bool, str]:
    if not isinstance(config, dict):
        return False, "Config bir dict olmali"
    if "version" not in config:
        return False, "version alani eksik"
    if config.get("version", 0) != 1:
        return False, f"Desteklenmeyen config versiyonu: {config.get('version')}"
    if "problems" not in config:
        return False, "problems alani eksik"
    if "algorithms" not in config:
        return False, "algorithms alani eksik"
    if "settings" not in config:
        return False, "settings alani eksik"
    return True, "OK"


def _list_configs() -> List[str]:
    if not os.path.exists(CONFIGS_DIR):
        return []
    return sorted([f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")])


def _save_config(
    selected_problems: List[DOEProblem],
    selected_names: List[str],
    settings: Dict[str, Any],
    param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    scope_parts = []
    for p in selected_problems[:3]:
        scope_parts.append(p.name)
    if len(selected_problems) > 3:
        scope_parts.append(f"and{len(selected_problems)-3}more")
    scope_str = "_".join(scope_parts) if scope_parts else "custom"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{scope_str}.json"
    filepath = os.path.join(CONFIGS_DIR, filename)

    all_problems_full = _load_problems_unified("all")
    problem_indices = []
    for p in selected_problems:
        for idx, ap in enumerate(all_problems_full):
            if ap.name == p.name:
                problem_indices.append(idx + 1)
                break

    all_specs_full = _all_strategy_specs()
    algo_indices = []
    for name in selected_names:
        for idx, spec in enumerate(all_specs_full):
            if spec.name == name:
                algo_indices.append(idx + 1)
                break

    config = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "problems": {"mode": "index", "selection": problem_indices},
        "algorithms": {"selection": algo_indices},
        "settings": settings,
    }
    if param_overrides:
        config["param_overrides"] = param_overrides

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return filepath


def _load_config(filepath: str, all_problems: List[DOEProblem], all_specs: List[StrategySpec]) -> Optional[Dict[str, Any]]:
    if not os.path.exists(filepath):
        print(f"[HATA] Config dosyasi bulunamadi: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] Config JSON hatasi: {e}")
        return None

    ok, msg = _validate_config(config, all_problems, all_specs)
    if not ok:
        print(f"[HATA] Config dogrulama basarisiz: {msg}")
        return None
    return config


def _save_convergence_history(best_params: Dict[str, Dict[str, Any]]) -> None:
    histories: Dict[str, Any] = {}
    for key, entry in best_params.items():
        profile = entry.get("convergence_profile")
        if profile:
            histories[key] = {
                "problem": entry.get("problem"),
                "strategy": entry.get("strategy"),
                "avg_length": entry.get("avg_length"),
                "avg_gap": entry.get("avg_gap"),
                "convergence_profile": profile,
            }
    if histories:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h_path = os.path.join(HISTORIES_DIR, f"convergence_{ts}.json")
        with open(h_path, "w", encoding="utf-8") as f:
            json.dump(histories, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Yakinsama gecmisi: {h_path}")


def _parse_cli_args() -> Optional[Dict[str, Any]]:
    parser = argparse.ArgumentParser(
        description="UniRide NUMBA DOE Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", help="Config dosyasi yolu")
    parser.add_argument("--problem", help="Problem secimi (isim: berlin52,eil51 veya class: small)")
    parser.add_argument("--algo", help="Algoritma secimi (isim: GA,PSO veya all)")
    parser.add_argument("--tune-runs", type=int, help="DOE tuning tekrar sayisi")
    parser.add_argument("--benchmark-runs", type=int, help="Benchmark tekrar sayisi")
    parser.add_argument("--workers", type=int, help="Worker sayisi")
    parser.add_argument("--mode", choices=["S", "P"], help="S=Sirali, P=Paralel")
    parser.add_argument("--profile", choices=["quality_first", "baseline"], help="Benchmark profili")
    parser.add_argument("--save-config", help="Secimleri config olarak kaydet")
    parser.add_argument("--fractional-fallback", action="store_true", help="Fractional fallback stratejisi")
    parser.add_argument("--random-seed", type=int, default=42, help="Fractional fallback seed")

    args, _ = parser.parse_known_args()
    if len(sys.argv) <= 1:
        return None
    return vars(args)


def main() -> int:
    global NUM_WORKERS, BENCHMARK_PROFILE, _current_metadata

    _ensure_dirs()
    metadata = _load_metadata()
    _current_metadata = metadata

    all_specs = _all_strategy_specs()
    selectable = [spec.name for spec in all_specs]
    all_problems = _load_problems_unified("all")
    if not all_problems:
        print("[ERROR] Problem bulunamadi")
        return 1

    while True:
        _clear()
        _log_environment_info()

        _print_status_overview(all_problems, selectable, metadata.get("best_params", {}))

        print("\n--- TUNING (DOE) ---")
        print("  [A] Tam DOE Tune: Tum secili pairleri bastan tune et")
        print("  [B] Eksikleri Tamamla: Sadece hic tune edilmemis pairleri calistir")
        print("  [C] Hizli Mod: Kucuk problem seti ile tum algoritmalar")
        print("  [D] Kapsamli: Secili scope icin her seyi yeniden calistir")
        print("  [E] Ozel Secim: Istediginiz problem ve algoritmalari numara ile secin")
        print("\n--- BENCHMARK ---")
        print("  [F] Direkt Benchmark: DOE tuning yapmadan kayitli/varsayilan parametrelerle calistir")
        print("\n--- CONFIG ---")
        print("  [G] Config Yükle: Kayitli config dosyasindan calistir")
        print("\n--- DIGER ---")
        print("  [S] Detay Modu: Bir problem icin DOE kayitlarini gor")
        print("  [Q] Cikis")
        choice = input("\nSeciminiz: ").strip().upper()
        if choice == "Q":
            print("Cikis yapiliyor...")
            return 0

        if choice == "S":
            _show_detail_mode(all_problems, metadata.get("best_params", {}), selectable)
            input("\nAna menuye donmek icin Enter'a basin...")
            continue

        if choice not in {"A", "B", "C", "D", "E", "F", "G"}:
            print("Gecersiz secim.")
            input("Devam etmek icin Enter'a basin...")
            continue

        selected_names = selectable[:]
        selected_problems = all_problems[:]
        skip_cached = False
        selection_label = ""

        if choice == "A":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_names = _select_algorithms_numbered(all_specs)
            selection_label = f"Mod: A (Tum pairleri DOE tune) | Kapsam: {scope_label}"

        elif choice == "B":
            skip_cached = True
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_names = _select_algorithms_numbered(all_specs)
            selection_label = f"Mod: B (Eksikleri tamamla) | Kapsam: {scope_label}"

        elif choice == "C":
            selected_problems = [p for p in all_problems if p.category == "small"]
            print(f"\n[HIZLI MOD] Kucuk problem seti kullaniliyor: {len(selected_problems)} problem")
            for p in selected_problems:
                print(f"   - {p.name} (n={p.dimension})")
            selection_label = "Mod: C (Hizli - small problemler + tum algoritmalar)"

        elif choice == "D":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_names = _select_algorithms_numbered(all_specs)
            selection_label = f"Mod: D (Kapsamli yeniden calistirma) | Kapsam: {scope_label}"

        elif choice == "E":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_names = _select_algorithms_numbered(all_specs)
            selection_label = f"Mod: E (Ozel secim) | Kapsam: {scope_label}"

        elif choice == "F":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_names = _select_algorithms_numbered(all_specs)
            selection_label = f"Mod: F (Direkt Benchmark) | Kapsam: {scope_label}"

        elif choice == "G":
            configs = _list_configs()
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
            cfg = _load_config(cfg_path, all_problems, all_specs)
            if not cfg:
                input("Devam etmek icin Enter'a basin...")
                continue
            prob_sel = cfg["problems"]
            algo_sel = cfg["algorithms"]
            settings = cfg.get("settings", {})
            if prob_sel.get("mode") == "index":
                indices = [i - 1 for i in prob_sel.get("selection", []) if 0 <= i - 1 < len(all_problems)]
                selected_problems = [all_problems[i] for i in indices]
            else:
                selected_problems = all_problems[:]
            algo_indices = [i - 1 for i in algo_sel.get("selection", []) if 0 <= i - 1 < len(all_specs)]
            selected_names = [all_specs[i].name for i in algo_indices]
            selection_label = f"Mod: G (Config: {configs[int(raw) - 1]})"
            print(f"\n[CONFIG] Config yuklendi: {configs[int(raw) - 1]}")
            print(f"   Problemler: {len(selected_problems)}, Algoritmalar: {len(selected_names)}")

        if not selected_names:
            print("[ERROR] Algoritma secilmedi.")
            input("Devam etmek icin Enter'a basin...")
            continue

        specs = [spec for spec in all_specs if spec.name in selected_names]

        edited_spaces: Dict[str, Dict[str, List[Any]]] = {}
        if choice in {"A", "B", "C", "D", "E", "G"}:
            for spec in specs:
                space = _build_numba_parameter_space(spec)
                edited = _edit_param_space(space, spec.name)
                edited_spaces[spec.name] = edited

        if choice == "F":
            BENCHMARK_PROFILE = _select_benchmark_profile(BENCHMARK_PROFILE)
            os.environ["BENCHMARK_PROFILE"] = BENCHMARK_PROFILE
            mode_sequential = _select_mode()
            benchmark_runs = _select_run_count("BENCHMARK", 5)
            NUM_WORKERS = 1
            if not mode_sequential:
                NUM_WORKERS = _select_worker_count()

            print("\n[PARAM] Her problem x algoritma icin parametreleri girin.")
            print("        Kayitli best parametre varsa gosterilir, Enter ile kabul edebilirsiniz.")
            print("        Kayitli yoksa varsayilan degerler gosterilir.")
            param_map = _collect_benchmark_params(selected_problems, specs, metadata.get("best_params", {}))

            _clear()
            print("=" * 70)
            print("BENCHMARK OZETI (DOE TUNING YOK)")
            print("=" * 70)
            print(f"\n[SECIM] {selection_label}")
            print(f"\n[STATS] Problemler: {len(selected_problems)}")
            for p in selected_problems:
                print(f"   - {p.name} (n={p.dimension}, {p.category})")
            print(f"[STATS] Algoritmalar: {len(selected_names)} ({', '.join(selected_names)})")
            print(f"[STATS] Benchmark run: {benchmark_runs}")
            print(f"[STATS] Mod: {'Sirali' if mode_sequential else f'Paralel ({NUM_WORKERS} worker)'}")
            print(f"\n[PARAM] Parametreler:")
            for key, params in param_map.items():
                display = {k: v for k, v in params.items() if k != "algorithm_type"}
                print(f"   {key}: {display}")
            print(f"\n[TIME] Tahmini Sure: ~{_format_time(_estimate_total_time(selected_problems, selected_names, benchmark_runs, NUM_WORKERS))}")
            print("\n[Y] Basla    [Q] Cikis")
            ch = input("\nSeciminiz: ").strip().upper()
            if ch != "Y":
                input("Devam etmek icin Enter'a basin...")
                continue

            start_time = time.time()
            worker_count = 1 if mode_sequential else NUM_WORKERS
            print("\n[START] DIREKT BENCHMARK BASLIYOR (NUMBA)...")
            benchmark_rows = _run_benchmark_direct(selected_problems, specs, param_map, benchmark_runs, worker_count, metadata)
            _write_summary(benchmark_rows)

            elapsed = time.time() - start_time
            print(f"\n[OK] Benchmark tamamlandi! Sure: {_format_time(elapsed)}")
            table_rows = [
                {
                    "problem": row["problem"],
                    "dimension": next((p.dimension for p in selected_problems if p.name == row["problem"]), 0),
                    "optimal": next((p.optimal for p in selected_problems if p.name == row["problem"]), None),
                    "strategy": row["strategy"],
                    "tour_length": row["avg_length"],
                    "best_gap": row["avg_gap"],
                    "gap": row["avg_gap"],
                    "avg_gap": row["avg_gap"],
                    "time_ms": row["avg_time_ms"],
                    "avg_time_ms": row["avg_time_ms"],
                }
                for row in benchmark_rows
            ]
            if table_rows:
                print_summary_table(table_rows)
            print(f"\n[SAVED] Benchmark CSV: {BENCHMARK_PROGRESS_CSV}")
            print(f"[SAVED] Summary: {SUMMARY_CSV}")
            input("\nAna menuye donmek icin Enter'a basin...")
            continue

        BENCHMARK_PROFILE = _select_benchmark_profile(BENCHMARK_PROFILE)
        os.environ["BENCHMARK_PROFILE"] = BENCHMARK_PROFILE
        mode_sequential = _select_mode()
        tuning_runs = _select_run_count("DOE TUNING", 3)
        try:
            max_combinations = int(input("\n[DOE] Algoritma basi max kombinasyon [varsayilan: 12]: ").strip() or "12")
        except ValueError:
            max_combinations = 12

        NUM_WORKERS = 1
        if not mode_sequential:
            NUM_WORKERS = _select_worker_count()

        proceed, summary_skip_cached = _show_test_summary(
            selected_problems,
            selected_names,
            metadata.get("best_params", {}),
            tuning_runs,
            0,
            NUM_WORKERS,
            mode_sequential,
            selection_label,
        )
        if not proceed:
            input("Devam etmek icin Enter'a basin...")
            continue
        skip_cached = skip_cached or summary_skip_cached

        start_time = time.time()
        print("\n[START] DOE TUNE BASLIYOR (NUMBA)...")
        print(f"   [CONFIG] Benchmark profili: {BENCHMARK_PROFILE}")
        print(f"   [CONFIG] Paralel worker sayisi: {NUM_WORKERS}")
        print(f"   [CONFIG] DOE tuning tekrar: {tuning_runs}")
        print(f"   [CONFIG] Maks kombinasyon: {max_combinations}")
        print(f"   Tahmini sure: ~{_format_time(_estimate_total_time(selected_problems, selected_names, tuning_runs, NUM_WORKERS))}")

        worker_count = 1 if mode_sequential else NUM_WORKERS
        best_params = _tune_parameters(selected_problems, specs, tuning_runs, max_combinations, worker_count, metadata, skip_cached, edited_spaces=edited_spaces if edited_spaces else None)

        _save_convergence_history(best_params)

        tuning_elapsed = time.time() - start_time
        print(f"\n[OK] DOE tuning tamamlandi! Sure: {_format_time(tuning_elapsed)}")
        if best_params:
            print(f"[SAVED] Best params: {BEST_PARAMS_JSON}")
        print(f"[SAVED] Tuning CSV: {TUNING_PROGRESS_CSV}")

        save_choice = input("\nAyarlari config olarak kaydetmek ister misiniz? [E/H]: ").strip().upper()
        if save_choice == "E":
            cfg_path = _save_config(selected_problems, selected_names, {
                "profile": BENCHMARK_PROFILE,
                "mode": "S" if mode_sequential else "P",
                "tuning_runs": tuning_runs,
                "max_combinations": max_combinations,
                "workers": NUM_WORKERS,
            }, edited_spaces if edited_spaces else None)
            print(f"[SAVED] Config: {cfg_path}")

        print("\n=> Best parametrelerle benchmark calistirmak ister misiniz?")
        print("  [E] Evet - Benchmark calistir")
        print("  [H] Hayir - Sadece tuning sonuclari yeterli")
        bench_choice = input("\nSeciminiz [E/H]: ").strip().upper()

        benchmark_rows: List[Dict[str, Any]] = []
        if bench_choice == "E":
            benchmark_runs = _select_run_count("BENCHMARK", 5)
            print(f"\n[START] BENCHMARK BASLIYOR ({benchmark_runs} run)...")
            benchmark_rows = _run_benchmark_with_best(selected_problems, specs, best_params, benchmark_runs, worker_count, metadata)
            _write_summary(benchmark_rows)

            elapsed = time.time() - start_time
            print(f"\n[OK] DOE + Benchmark tamamlandi! Sure: {_format_time(elapsed)}")
            table_rows = [
                {
                    "problem": row["problem"],
                    "dimension": next((p.dimension for p in selected_problems if p.name == row["problem"]), 0),
                    "optimal": next((p.optimal for p in selected_problems if p.name == row["problem"]), None),
                    "strategy": row["strategy"],
                    "tour_length": row["avg_length"],
                    "best_gap": row["avg_gap"],
                    "gap": row["avg_gap"],
                    "avg_gap": row["avg_gap"],
                    "time_ms": row["avg_time_ms"],
                    "avg_time_ms": row["avg_time_ms"],
                }
                for row in benchmark_rows
            ]
            if table_rows:
                print_summary_table(table_rows)
            print(f"[SAVED] Benchmark CSV: {BENCHMARK_PROGRESS_CSV}")
            print(f"[SAVED] Summary: {SUMMARY_CSV}")
        else:
            print("\n[OK] Sadece DOE tuning tamamlandi.")
            print("[INFO] Benchmark calistirmak icin ana menuunden [F] secenegini kullanabilirsiniz.")

        input("\nAna menuye donmek icin Enter'a basin...")


if __name__ == "__main__":
    raise SystemExit(main())
