#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark - SOTA DOE / PARAMETER OPTIMIZATION

Tek dosyada:
- E2BSO / R2DMA / P-AOEA icin DOE tuning
- cache/resume
- best-parameter benchmark kosusu
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from academic_benchmark.run_smart_benchmark_sota import (
    ALL_ALGOS,
    _NUMBA_AVAILABLE,
    _make_solver_config,
    load_problems,
    make_deterministic_seed,
)
from academic_benchmark.sota_tsp import (
    E2BSO_TSP,
    E2BSOTSPConfig,
    PAOEA_TSP,
    PAOEAConfig,
    R2DMA_TSP,
    R2DMATSPConfig,
)

RESULTS_DIR = os.path.join(SCRIPT_DIR, "benchmark_db", "doe_sota")
CONFIGS_DIR = os.path.join(RESULTS_DIR, "configs")
HISTORIES_DIR = os.path.join(RESULTS_DIR, "histories")
METADATA_PATH = os.path.join(RESULTS_DIR, "latest_metadata_sota_doe.json")
TUNING_PROGRESS_CSV = os.path.join(RESULTS_DIR, "tuning_progress.csv")
BENCHMARK_PROGRESS_CSV = os.path.join(RESULTS_DIR, "benchmark_progress.csv")
BEST_PARAMS_JSON = os.path.join(RESULTS_DIR, "best_params.json")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "benchmark_summary.csv")

ALGORITHMS_TO_CHECK = {
    "E2BSO_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "e2bso_tsp.py"),
    "R2DMA_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "r2dma_tsp.py"),
    "PAOEA_TSP": os.path.join(SCRIPT_DIR, "sota_tsp", "paoea_tsp.py"),
}

PARAM_VALIDATORS = {
    "population_size": (1, 10000, int),
    "max_iterations": (1, 100000, int),
    "genome_population_size": (1, 1000, int),
    "crossover_rate": (0.0, 1.0, float),
    "mutation_rate": (0.0, 1.0, float),
    "gamma": (0.0, 1.0, float),
    "injection_rate": (0.0, 1.0, float),
    "remove_ratio": (0.0, 1.0, float),
    "theta_base": (0.0, 1.0, float),
    "pulse_injection_rate": (0.0, 1.0, float),
}

_shutdown_requested = False
_current_metadata: Optional[Dict[str, Any]] = None
NUM_WORKERS = min(cpu_count(), 4)


@dataclass
class DOEProblem:
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal: Optional[int]
    category: str


@dataclass
class SOTASpec:
    name: str


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    if _current_metadata is not None:
        _save_metadata(_current_metadata)
    sys.exit(130)


signal.signal(signal.SIGINT, _signal_handler)


def _ensure_dirs() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(HISTORIES_DIR, exist_ok=True)


def _file_hash(path: str) -> str:
    import hashlib
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_metadata() -> Dict[str, Any]:
    if not os.path.exists(METADATA_PATH):
        return {"algorithm_hashes": {}, "best_params": {}, "results": {}, "last_updated": ""}
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"algorithm_hashes": {}, "best_params": {}, "results": {}, "last_updated": ""}


def _save_metadata(metadata: Dict[str, Any]) -> None:
    metadata["algorithm_hashes"] = {name: _file_hash(path) for name, path in ALGORITHMS_TO_CHECK.items() if os.path.exists(path)}
    metadata["last_updated"] = datetime.now().isoformat()
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def _wrap_problems(size_limit: int) -> List[DOEProblem]:
    return [
        DOEProblem(
            name=p.name,
            dimension=p.dimension,
            coordinates=p.coordinates,
            optimal=p.optimal,
            category=p.category,
        )
        for p in load_problems(size_limit)
    ]


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


def _select_problem_scope() -> str:
    print("\n[PROBLEM SET] Boyut secin: [1] small [2] medium [3] large [4] all")
    choice = input("Seciminiz [varsayilan: 1]: ").strip()
    return {"1": "small", "2": "medium", "3": "large", "4": "all", "": "small"}.get(choice, "small")


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


def _select_algorithms_numbered(algos: List[str]) -> List[str]:
    print("\n[ALGORITMA SECIMI] Algoritma numaralarini girin (virgulle ayirin veya 'all'):")
    for idx, name in enumerate(algos, 1):
        print(f"   [{idx}] {name}")
    while True:
        raw = input("\nSeciminiz: ").strip()
        if not raw:
            print("  [HATA] Bos giris yapildi, tekrar deneyin")
            continue
        indices = _parse_index_or_all_input(raw, len(algos))
        if indices is None:
            continue
        return [algos[i] for i in indices]


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


def _estimate_total_time(problems: List[DOEProblem], algos: List[str], runs: int, workers: int) -> float:
    base_times = {"small": 0.6, "medium": 1.5, "large": 3.0}
    total = 0.0
    for problem in problems:
        total += base_times.get(problem.category, 1.0) * len(algos) * runs
    return total / max(1, workers)


def _print_banner(problem_count: int, algos: List[str], tuning_runs: int, workers: int, mode_label: str) -> None:
    print("=" * 70)
    print("           UNIRIDE SOTA DOE BENCHMARK")
    print("=" * 70)
    print(f"\n[CONFIG] Problem sayisi: {problem_count}")
    print(f"[CONFIG] Algoritmalar: {', '.join(algos)}")
    print(f"[CONFIG] DOE tekrar: {tuning_runs}")
    print(f"[CONFIG] Worker: {workers}")
    print(f"[CONFIG] Mod: {mode_label}")


def _print_status_overview(problems: List[DOEProblem], algos: List[str], best_params: Dict[str, Dict[str, Any]]) -> None:
    print("\n" + "=" * 80)
    print("DOE STATUS OVERVIEW (SOTA)")
    print("=" * 80)
    categories = {"small": 0, "medium": 0, "large": 0}
    for problem in problems:
        categories[problem.category] = categories.get(problem.category, 0) + 1
    for category, count in categories.items():
        print(f"  {category:<8}: {count} problem")
    tuned = sum(1 for problem in problems for algo in algos if f"{problem.name}::{algo}" in best_params)
    total = len(problems) * len(algos)
    print(f"\n[CACHE] Tuned pairler: {tuned}/{total}")


def _show_test_summary(
    problems: List[DOEProblem],
    algos: List[str],
    best_params: Dict[str, Dict[str, Any]],
    tuning_runs: int,
    benchmark_runs: int,
    workers: int,
    sequential: bool,
    selection_label: str = "",
) -> Tuple[bool, bool]:
    _clear()
    total_pairs = len(problems) * len(algos)
    cached_pairs = sum(1 for problem in problems for algo in algos if f"{problem.name}::{algo}" in best_params)
    new_pairs = total_pairs - cached_pairs
    print("=" * 70)
    print("TEST OZETI (SOTA DOE)")
    print("=" * 70)
    if selection_label:
        print(f"\n[SECIM] {selection_label}")
    print("\n[STATS] Test Yapilacak:")
    print(f"   * Problemler: {len(problems)}")
    for p in problems:
        print(f"      - {p.name} (n={p.dimension}, {p.category})")
    print(f"   * Algoritmalar: {len(algos)} ({', '.join(algos)})")
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
    estimate = _estimate_total_time(problems, algos, tuning_runs + benchmark_runs, workers)
    print(f"\n[TIME] Tahmini Sure: ~{_format_time(estimate if (new_pairs if skip_cached else total_pairs) else 0)}")
    print("\n[!] DIKKAT:")
    print("   * Ctrl+C ile istediginiz zaman guvenli cikis yapabilirsiniz")
    print("   * Sonuclar her asamada otomatik kaydedilir")
    print("\n[Y] Basla    [Q] Cikis")
    ch = input("\nSeciminiz: ").strip().upper()
    return (ch == "Y"), skip_cached


def _print_progress_line(completed: int, total: int, result: Dict[str, Any], stage: str) -> None:
    gap_val = result.get("avg_gap")
    sym = "*" if gap_val is not None and not math.isnan(gap_val) and gap_val <= 1 else (
        "+" if gap_val is not None and not math.isnan(gap_val) and gap_val <= 5 else "o"
    )
    gap_text = "N/A" if gap_val is None or math.isnan(gap_val) else f"{gap_val:>6.2f}%"
    print(
        f"  [{completed:>3}/{total}] {result['problem']:<12} {result['strategy']:<12} "
        f"GAP: {gap_text:>7} {sym} {result.get('avg_time_ms', 0):>7.0f}ms [{stage}]",
        flush=True,
    )


def _show_detail_mode(problems: List[DOEProblem], best_params: Dict[str, Dict[str, Any]], algos: List[str]) -> None:
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
    for algo in algos:
        entry = best_params.get(f"{problem.name}::{algo}")
        if not entry:
            print(f"   - {algo:<12}: kayit yok")
            continue
        gap = entry["avg_gap"]
        gap_str = "n/a" if gap is None or math.isnan(gap) else f"{gap:.3f}%"
        print(f"   - {algo:<12}: avg={entry['avg_length']:.3f}, gap={gap_str}, time={entry['avg_time_ms']:.1f}ms")


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


def _build_sota_parameter_space(algo_name: str) -> Dict[str, List[Any]]:
    if algo_name == "E2BSO-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "gamma": [0.15, 0.20, 0.30],
            "injection_rate": [0.08, 0.12, 0.18],
            "remove_ratio": [0.10, 0.15, 0.20],
        }
    if algo_name == "R2DMA-TSP":
        return {
            "population_size": [24, 36, 48],
            "max_iterations": [200, 320, 450],
            "theta_base": [0.15, 0.25, 0.35],
            "remove_ratio": [0.10, 0.15, 0.20],
            "pulse_injection_rate": [0.05, 0.10, 0.15],
        }
    return {
        "population_size": [24, 36, 48],
        "max_iterations": [200, 320, 450],
        "genome_population_size": [8, 12, 16],
        "crossover_rate": [0.75, 0.85, 0.95],
        "mutation_rate": [0.10, 0.18, 0.26],
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


def _make_solver(algo_name: str, params: Dict[str, Any]):
    seed = int(params["seed"])
    cfg = params.copy()
    cfg.pop("seed", None)
    if algo_name == "E2BSO-TSP":
        return E2BSO_TSP(E2BSOTSPConfig(seed=seed, **cfg))
    if algo_name == "R2DMA-TSP":
        return R2DMA_TSP(R2DMATSPConfig(seed=seed, **cfg))
    if algo_name == "P-AOEA-TSP":
        return PAOEA_TSP(PAOEAConfig(seed=seed, **cfg))
    raise ValueError(f"Unknown algo: {algo_name}")


def _evaluate_sota_combo(task: Tuple[Dict[str, Any], str, Dict[str, Any], int, int]) -> Dict[str, Any]:
    problem_dict, algo_name, params, combo_idx, n_runs = task
    coordinates = problem_dict["coordinates"]
    optimal = problem_dict["optimal"]
    n_nodes = problem_dict["dimension"]

    costs: List[float] = []
    times_sec: List[float] = []
    for run_idx in range(n_runs):
        seed = make_deterministic_seed(problem_dict["name"], algo_name, run_idx, combo_idx, 5000)
        run_params = params.copy()
        run_params["seed"] = seed
        solver = _make_solver(algo_name, run_params)
        t0 = time.perf_counter()
        result = solver.solve(coordinates)
        elapsed = time.perf_counter() - t0
        costs.append(float(result.tour_length))
        times_sec.append(elapsed)

    avg_cost = sum(costs) / len(costs)
    avg_gap = ((avg_cost - optimal) / optimal * 100.0) if optimal else math.nan
    return {
        "problem": problem_dict["name"],
        "strategy": algo_name,
        "combo_idx": combo_idx,
        "params": params,
        "avg_length": avg_cost,
        "avg_gap": avg_gap,
        "avg_time_ms": (sum(times_sec) / len(times_sec)) * 1000.0,
        "n_runs": n_runs,
        "dimension": n_nodes,
    }


def _run_pool(tasks: List[Tuple], workers: int, on_result=None) -> List[Dict[str, Any]]:
    if not tasks:
        return []
    if workers <= 1:
        results = []
        for i, task in enumerate(tasks):
            result = _evaluate_sota_combo(task)
            results.append(result)
            if on_result:
                on_result(i, result, len(tasks))
        return results
    results = []
    with Pool(processes=workers) as pool:
        for i, result in enumerate(pool.imap_unordered(_evaluate_sota_combo, tasks)):
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
    specs: List[SOTASpec],
    n_runs: int,
    max_combinations: int,
    workers: int,
    metadata: Dict[str, Any],
    skip_cached: bool,
    edited_spaces: Optional[Dict[str, Dict[str, List[Any]]]] = None,
) -> Dict[str, Dict[str, Any]]:
    completed = _load_tuning_cache()
    best_params: Dict[str, Dict[str, Any]] = metadata.get("best_params", {})
    tasks: List[Tuple[Dict[str, Any], str, Dict[str, Any], int, int]] = []

    for problem in problems:
        for spec in specs:
            defaults = _make_solver_config(spec.name, problem.dimension, _NUMBA_AVAILABLE)
            space = edited_spaces.get(spec.name) if edited_spaces and spec.name in edited_spaces else _build_sota_parameter_space(spec.name)
            combos = _generate_combinations(space, max_combinations)
            for combo_idx, combo in enumerate(combos, 1):
                params = defaults.copy()
                params.update(combo)
                sig = _param_signature(params)
                if skip_cached and (problem.name, spec.name, sig) in completed:
                    continue
                tasks.append(({
                    "name": problem.name,
                    "dimension": problem.dimension,
                    "coordinates": problem.coordinates,
                    "optimal": problem.optimal,
                    "category": problem.category,
                }, spec.name, params, combo_idx, n_runs))

    results = _run_pool(tasks, workers)
    tuning_fields = [
        "timestamp", "problem", "strategy", "combo_idx", "avg_length", "avg_gap", "avg_time_ms", "n_runs", "param_signature", "params_json"
    ]
    total_results = len(results)
    for idx, result in enumerate(results, 1):
        sig = _param_signature(result["params"])
        row = {
            "timestamp": datetime.now().isoformat(),
            "problem": result["problem"],
            "strategy": result["strategy"],
            "combo_idx": result["combo_idx"],
            "avg_length": round(result["avg_length"], 4),
            "avg_gap": None if math.isnan(result["avg_gap"]) else round(result["avg_gap"], 6),
            "avg_time_ms": round(result["avg_time_ms"], 4),
            "n_runs": result["n_runs"],
            "param_signature": sig,
            "params_json": json.dumps(result["params"], ensure_ascii=False, sort_keys=True),
        }
        _append_csv_row(TUNING_PROGRESS_CSV, tuning_fields, row)
        best_key = f"{result['problem']}::{result['strategy']}"
        current_best = best_params.get(best_key)
        if current_best is None or result["avg_length"] < float(current_best["avg_length"]):
            best_params[best_key] = {
                "problem": result["problem"],
                "strategy": result["strategy"],
                "avg_length": result["avg_length"],
                "avg_gap": result["avg_gap"],
                "avg_time_ms": result["avg_time_ms"],
                "params": result["params"],
                "convergence_profile": [result["avg_length"]],
            }
            _print_progress_line(idx, total_results, result, "TUNE")

    metadata["best_params"] = best_params
    with open(BEST_PARAMS_JSON, "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2, ensure_ascii=False)
    _save_metadata(metadata)
    return best_params


def _run_benchmark_with_best(
    problems: List[DOEProblem],
    specs: List[SOTASpec],
    best_params: Dict[str, Dict[str, Any]],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    tasks: List[Tuple[Dict[str, Any], str, Dict[str, Any], int, int]] = []
    for problem in problems:
        for spec in specs:
            best_key = f"{problem.name}::{spec.name}"
            best_entry = best_params.get(best_key)
            if not best_entry:
                continue
            tasks.append(({
                "name": problem.name,
                "dimension": problem.dimension,
                "coordinates": problem.coordinates,
                "optimal": problem.optimal,
                "category": problem.category,
            }, spec.name, best_entry["params"], 1, benchmark_runs))

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
        _print_progress_line(idx, total_results, result, "FINAL")

    metadata["results"] = {f"{row['problem']}::{row['strategy']}": row for row in rows}
    _save_metadata(metadata)
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


def _input_params_for_pair(
    problem_name: str,
    algo_name: str,
    default_params: Dict[str, Any],
    saved_params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    base = saved_params.copy() if saved_params else default_params.copy()
    source = "BEST" if saved_params else "DEFAULT"
    print(f"\n  [{problem_name} x {algo_name}] Parametreler ({source}):")
    result: Dict[str, Any] = {}
    for key, val in base.items():
        if key == "seed":
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
    algos: List[str],
    best_params: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    collected: Dict[str, Dict[str, Any]] = {}
    for problem in problems:
        for algo_name in algos:
            best_key = f"{problem.name}::{algo_name}"
            saved = best_params.get(best_key)
            saved_p = saved.get("params") if saved else None
            defaults = _make_solver_config(algo_name, problem.dimension, _NUMBA_AVAILABLE)
            params = _input_params_for_pair(problem.name, algo_name, defaults, saved_p)
            collected[best_key] = params
    return collected


def _run_benchmark_direct(
    problems: List[DOEProblem],
    algos: List[str],
    param_map: Dict[str, Dict[str, Any]],
    benchmark_runs: int,
    workers: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    tasks: List[Tuple[Dict[str, Any], str, Dict[str, Any], int, int]] = []
    for problem in problems:
        for algo_name in algos:
            key = f"{problem.name}::{algo_name}"
            params = param_map.get(key)
            if not params:
                continue
            tasks.append(({
                "name": problem.name,
                "dimension": problem.dimension,
                "coordinates": problem.coordinates,
                "optimal": problem.optimal,
                "category": problem.category,
            }, algo_name, params, 1, benchmark_runs))

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
    _save_metadata(metadata)
    return rows


def _validate_config(config: Dict, all_problems: List[DOEProblem], algos: List[str]) -> Tuple[bool, str]:
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
    selected_algos: List[str],
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

    all_problems_full = _wrap_problems(99999)
    problem_indices = []
    for p in selected_problems:
        for idx, ap in enumerate(all_problems_full):
            if ap.name == p.name:
                problem_indices.append(idx + 1)
                break

    algo_indices = []
    for name in selected_algos:
        for idx, aname in enumerate(ALL_ALGOS):
            if aname == name:
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


def _load_config(filepath: str, all_problems: List[DOEProblem], algos: List[str]) -> Optional[Dict[str, Any]]:
    if not os.path.exists(filepath):
        print(f"[HATA] Config dosyasi bulunamadi: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] Config JSON hatasi: {e}")
        return None

    ok, msg = _validate_config(config, all_problems, algos)
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
        description="UniRide SOTA DOE Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", help="Config dosyasi yolu")
    parser.add_argument("--problem", help="Problem secimi (isim veya class)")
    parser.add_argument("--algo", help="Algoritma secimi")
    parser.add_argument("--tune-runs", type=int, help="DOE tuning tekrar sayisi")
    parser.add_argument("--benchmark-runs", type=int, help="Benchmark tekrar sayisi")
    parser.add_argument("--workers", type=int, help="Worker sayisi")
    parser.add_argument("--mode", choices=["S", "P"], help="S=Sirali, P=Paralel")
    parser.add_argument("--save-config", help="Secimleri config olarak kaydet")
    parser.add_argument("--fractional-fallback", action="store_true")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--size-limit", type=int, default=500, help="Maks dugum sayisi")

    args, _ = parser.parse_known_args()
    if len(sys.argv) <= 1:
        return None
    return vars(args)


def main() -> int:
    global NUM_WORKERS, _current_metadata

    _ensure_dirs()
    metadata = _load_metadata()
    _current_metadata = metadata

    cli_args = _parse_cli_args()

    try:
        size_limit = int(input("Maksimum dugum sayisi [varsayilan: 500]: ").strip() or "500") if not cli_args else cli_args.get("size_limit", 500)
    except ValueError:
        size_limit = 500
    all_problems = _wrap_problems(size_limit)
    if not all_problems:
        print("[ERROR] Problem bulunamadi")
        return 1

    while True:
        _clear()
        _log_environment_info()

        _print_status_overview(all_problems, ALL_ALGOS, metadata.get("best_params", {}))

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
            _show_detail_mode(all_problems, metadata.get("best_params", {}), ALL_ALGOS)
            input("\nAna menuye donmek icin Enter'a basin...")
            continue

        if choice not in {"A", "B", "C", "D", "E", "F", "G"}:
            print("Gecersiz secim.")
            input("Devam etmek icin Enter'a basin...")
            continue

        selected_algos = ALL_ALGOS[:]
        selected_problems = all_problems[:]
        skip_cached = False
        selection_label = ""

        if choice == "A":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_algos = _select_algorithms_numbered(ALL_ALGOS)
            selection_label = f"Mod: A (Tum pairleri DOE tune) | Kapsam: {scope_label}"

        elif choice == "B":
            skip_cached = True
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_algos = _select_algorithms_numbered(ALL_ALGOS)
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
            selected_algos = _select_algorithms_numbered(ALL_ALGOS)
            selection_label = f"Mod: D (Kapsamli yeniden calistirma) | Kapsam: {scope_label}"

        elif choice == "E":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_algos = _select_algorithms_numbered(ALL_ALGOS)
            selection_label = f"Mod: E (Ozel secim) | Kapsam: {scope_label}"

        elif choice == "F":
            selected_problems, scope_label = _select_problem_mode_and_scope(all_problems)
            if not selected_problems:
                input("Devam etmek icin Enter'a basin...")
                continue
            selected_algos = _select_algorithms_numbered(ALL_ALGOS)
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
            cfg = _load_config(cfg_path, all_problems, ALL_ALGOS)
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
            algo_indices = [i - 1 for i in algo_sel.get("selection", []) if 0 <= i - 1 < len(ALL_ALGOS)]
            selected_algos = [ALL_ALGOS[i] for i in algo_indices]
            selection_label = f"Mod: G (Config: {configs[int(raw) - 1]})"
            print(f"\n[CONFIG] Config yuklendi: {configs[int(raw) - 1]}")
            print(f"   Problemler: {len(selected_problems)}, Algoritmalar: {len(selected_algos)}")

        if not selected_algos:
            print("[ERROR] Algoritma secilmedi.")
            input("Devam etmek icin Enter'a basin...")
            continue

        specs = [SOTASpec(name=name) for name in selected_algos]

        edited_spaces: Dict[str, Dict[str, List[Any]]] = {}
        if choice in {"A", "B", "C", "D", "E", "G"}:
            for spec in specs:
                space = _build_sota_parameter_space(spec.name)
                edited = _edit_param_space(space, spec.name)
                edited_spaces[spec.name] = edited

        if choice == "F":
            mode_sequential = _select_mode()
            benchmark_runs = _select_run_count("BENCHMARK", 5)
            NUM_WORKERS = 1
            if not mode_sequential:
                NUM_WORKERS = _select_worker_count()

            print("\n[PARAM] Her problem x algoritma icin parametreleri girin.")
            print("        Kayitli best parametre varsa gosterilir, Enter ile kabul edebilirsiniz.")
            param_map = _collect_benchmark_params(selected_problems, selected_algos, metadata.get("best_params", {}))

            _clear()
            print("=" * 70)
            print("BENCHMARK OZETI (DOE TUNING YOK)")
            print("=" * 70)
            print(f"\n[SECIM] {selection_label}")
            print(f"\n[STATS] Problemler: {len(selected_problems)}")
            for p in selected_problems:
                print(f"   - {p.name} (n={p.dimension}, {p.category})")
            print(f"[STATS] Algoritmalar: {len(selected_algos)} ({', '.join(selected_algos)})")
            print(f"[STATS] Benchmark run: {benchmark_runs}")
            print(f"[STATS] Mod: {'Sirali' if mode_sequential else f'Paralel ({NUM_WORKERS} worker)'}")
            print(f"\n[PARAM] Parametreler:")
            for key, params in param_map.items():
                display = {k: v for k, v in params.items() if k != "seed"}
                print(f"   {key}: {display}")
            print(f"\n[TIME] Tahmini Sure: ~{_format_time(_estimate_total_time(selected_problems, selected_algos, benchmark_runs, NUM_WORKERS))}")
            print("\n[Y] Basla    [Q] Cikis")
            ch = input("\nSeciminiz: ").strip().upper()
            if ch != "Y":
                input("Devam etmek icin Enter'a basin...")
                continue

            start_time = time.time()
            worker_count = 1 if mode_sequential else NUM_WORKERS
            print("\n[START] DIREKT BENCHMARK BASLIYOR (SOTA)...")
            benchmark_rows = _run_benchmark_direct(selected_problems, selected_algos, param_map, benchmark_runs, worker_count, metadata)
            _write_summary(benchmark_rows)

            elapsed = time.time() - start_time
            print(f"\n[OK] Benchmark tamamlandi! Sure: {_format_time(elapsed)}")
            if benchmark_rows:
                for row in benchmark_rows:
                    gap = "n/a" if row["avg_gap"] is None else f"{row['avg_gap']:.3f}%"
                    print(f"  - {row['problem']} / {row['strategy']}: cost={row['avg_length']:.3f}, gap={gap}, time={row['avg_time_ms']:.1f} ms")
            print(f"\n[SAVED] Benchmark CSV: {BENCHMARK_PROGRESS_CSV}")
            print(f"[SAVED] Summary: {SUMMARY_CSV}")
            input("\nAna menuye donmek icin Enter'a basin...")
            continue

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
            selected_algos,
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
        print("\n[START] DOE TUNE BASLIYOR (SOTA)...")
        print(f"   [CONFIG] Paralel worker sayisi: {NUM_WORKERS}")
        print(f"   [CONFIG] DOE tuning tekrar: {tuning_runs}")
        print(f"   [CONFIG] Maks kombinasyon: {max_combinations}")
        print(f"   Tahmini sure: ~{_format_time(_estimate_total_time(selected_problems, selected_algos, tuning_runs, NUM_WORKERS))}")

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
            cfg_path = _save_config(selected_problems, selected_algos, {
                "size_limit": size_limit,
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
            if benchmark_rows:
                grouped: Dict[str, List[float]] = {}
                for row in benchmark_rows:
                    grouped.setdefault(row["strategy"], []).append(float(row["avg_gap"]) if row["avg_gap"] is not None else float("nan"))
                for row in benchmark_rows:
                    gap = "n/a" if row["avg_gap"] is None else f"{row['avg_gap']:.3f}%"
                    print(f"  - {row['problem']} / {row['strategy']}: cost={row['avg_length']:.3f}, gap={gap}, time={row['avg_time_ms']:.1f} ms")
                ranked = []
                for algo, gaps in grouped.items():
                    valid = [gap for gap in gaps if not math.isnan(gap)]
                    if valid:
                        ranked.append((algo, statistics.mean(valid)))
                ranked.sort(key=lambda item: item[1])
                if ranked:
                    print("\n[OVERALL RANKING]")
                    for pos, (algo, avg_gap) in enumerate(ranked, 1):
                        print(f"  {pos}. {algo:<12} avg gap={avg_gap:.3f}%")
            print(f"[SAVED] Benchmark CSV: {BENCHMARK_PROGRESS_CSV}")
            print(f"[SAVED] Summary: {SUMMARY_CSV}")
        else:
            print("\n[OK] Sadece DOE tuning tamamlandi.")
            print("[INFO] Benchmark calistirmak icin ana menuunden [F] secenegini kullanabilirsiniz.")

        input("\nAna menuye donmek icin Enter'a basin...")


if __name__ == "__main__":
    raise SystemExit(main())
