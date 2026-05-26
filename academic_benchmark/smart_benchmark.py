import os
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRide Smart Benchmark Engine — Unified Cross-Engine Orchestrator
===================================================================

Single entry point for DOE tuning, benchmarking, and parameter management
across both Numba and SOTA algorithm engines.

Usage:
    python academic_benchmark/smart_benchmark.py
"""

import sys
import os
import io
import time
import json
import signal
import csv
import concurrent.futures
import math
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor

from uniride_core.algorithms._platform import fix_windows_encoding
fix_windows_encoding()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from academic_benchmark.engine_core import ProblemInstance, RunResult, AlgorithmRegistry, BenchmarkTask, BenchmarkConfig
from academic_benchmark.benchmark_utils import (
    load_metadata, save_metadata, get_cpu_info, format_time,
    save_tuning_params_and_solution as _save_best_solution,
    ProblemSelector, ETATracker, multi_select, select_worker_count,
    select_run_count, generate_combinations, edit_param_space,
    clear_screen, param_signature, TSPLIB_OPTIMALS,
)

# Import engine library functions
# NOTE: master_numba_engine.py was consolidated into cli_engine.py during refactoring.
# All Numba engine functions are now sourced from cli_engine.
from academic_benchmark.cli_engine import (
    _all_strategy_specs as _numba_specs,
    _tune_parameters as _numba_tune,
    _run_benchmark_with_best as _numba_bench_best,
    _run_benchmark_direct as _numba_bench_direct,
    _run_benchmark_with_params as _numba_bench_params,
    _manual_param_entry_interactive as _numba_manual_params,
    _load_params_from_db_interactive as _numba_load_db_params,
    _save_best_to_param_db as _numba_save_db,
    _edit_param_space_interactive as _numba_edit_space,
    _select_benchmark_problems_interactive as _numba_select_bench_probs,
    DOE_MAX_COMBINATIONS as _NUMBA_MAX_COMBOS,
    load_problems as _numba_load_problems,
    DOEProblem,
)

# SOTA engine functions — re-implemented in sota_engine.py
# Sources SOTA solvers from uniride_core.algorithms.sota_tsp/
from academic_benchmark.sota_engine import (
    run_engine_tuning as _sota_tune,
    run_engine_default as _sota_bench_default,
    run_engine_with_params as _sota_bench_params,
    _manual_param_entry_interactive as _sota_manual_params,
    _load_params_from_db_interactive as _sota_load_db_params,
    _save_best_to_param_db as _sota_save_db,
    _edit_param_space_interactive as _sota_edit_space,
    _param_db_menu as _sota_param_db_menu,
    load_problems as _sota_load_problems,
    run_sota_optuna_tuning as _run_sota_optuna_tuning,
    TSPProblem,
    ALL_ALGOS as _SOTA_ALL_ALGOS,
)

# DB cache integration
try:
    from tsplib_manager import (
        get_distance_matrix as _dm_from_cache,
        get_all_problems as _problems_from_db,
        is_db_populated as _db_ready,
        save_best_solution as _db_save_best,
        get_best_solution as _db_get_best,
        problem_row_to_instance as _problem_row_to_instance,
    )
except ImportError:
    try:
        from academic_benchmark.tsplib_manager import (
            get_distance_matrix as _dm_from_cache,
            get_all_problems as _problems_from_db,
            is_db_populated as _db_ready,
            save_best_solution as _db_save_best,
            get_best_solution as _db_get_best,
            problem_row_to_instance as _problem_row_to_instance,
        )
    except ImportError:
        _dm_from_cache = lambda name, **kw: None
        _problems_from_db = lambda **kw: []
        _db_ready = lambda **kw: False
        _db_save_best = lambda *a, **kw: -1
        _db_get_best = lambda *a, **kw: None
        _problem_row_to_instance = None

TSPLIB_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tsplib_data", "tsplib.db")

# Paths
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_DB = os.path.join(_ENGINE_DIR, "benchmark_db")
METADATA_PATH = os.path.join(BENCHMARK_DB, "smart_metadata.json")
HISTORY_DIR = os.path.join(BENCHMARK_DB, "history")
RESULTS_DIR = os.path.join(_ENGINE_DIR, "results")
CONFIGS_DIR = os.path.join(BENCHMARK_DB, "configs")

os.makedirs(BENCHMARK_DB, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CONFIGS_DIR, exist_ok=True)

# Param DB path
_PARAM_DB_PATH = os.path.join(BENCHMARK_DB, "param_db.json")
try:
    from academic_benchmark.param_db import set_db_path as _param_db_set_path
    _param_db_set_path(_PARAM_DB_PATH)
except ImportError:
    pass

# Global State
_shutdown_requested = False
_current_metadata = None
_current_results = []

_previous_sigint_handler = signal.getsignal(signal.SIGINT)

def signal_handler(signum, frame):
    graceful_shutdown()
    if callable(_previous_sigint_handler):
        _previous_sigint_handler(signum, frame)

signal.signal(signal.SIGINT, signal_handler)

def graceful_shutdown():
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!] STOP REQUESTED!")
    print("[NOTE] Saving current results, please wait...")
    if _current_metadata and _current_results:
        save_metadata(METADATA_PATH, _current_metadata)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(HISTORY_DIR, f"interrupted_smart_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if _current_results:
                writer = csv.DictWriter(f, fieldnames=list(_current_results[0].keys()))
                writer.writeheader()
                writer.writerows(_current_results)
        print(f"[OK] {len(_current_results)} results saved to: {csv_path}")
    print("Graceful shutdown complete.")
    sys.exit(0)

def _check_interrupt_key():
    """Check for Ctrl+Q / Ctrl+X / q / x without blocking.
    Cross-platform: msvcrt on Windows, select+termios on Unix.
    Ctrl+C is intentionally NOT checked here (safe for copy-paste).
    Graceful degradation: returns False if stdin unavailable (CI, piped input).
    """
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            return key in (b'\x18', b'\x11', b'q', b'x', b'Q', b'X')
    else:
        try:
            import select, termios, tty
            if not sys.stdin.isatty():
                return False
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    ch = sys.stdin.read(1)
                    return ch in ('\x11', '\x18', 'q', 'x', 'Q', 'X')
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (ImportError, OSError, AttributeError):
            pass
    return False

# ── Problem Loading ──────────────────────────────────────────────────────────

def load_problems() -> List[ProblemInstance]:
    """Load problems from SQLite DB cache (unified for both engines)."""
    if _db_ready(TSPLIB_DB):
        rows = _problems_from_db(db_path=TSPLIB_DB, max_dim=99999)
        if rows:
            print(f"[INFO] Loaded {len(rows)} problems from DB cache.")
            problems = []
            for r in rows:
                if _problem_row_to_instance is not None:
                    prob = _problem_row_to_instance(r)
                else:
                    prob = ProblemInstance(
                        name=r["name"], dimension=r["dimension"],
                        coordinates=r["coordinates"], optimal=r["optimal"],
                        category=r["category"], source=r.get("source", "tsplib"),
                        problem_type=str(r.get("problem_type", "tsp")).lower(),
                    )
                problems.append(prob)
            return sorted(problems, key=lambda p: p.dimension)

    print("[INFO] DB not available. Loading from Numba engine (tar.gz fallback)...")
    numba_probs = _numba_load_problems()
    problems = [ProblemInstance(
        name=p.name, dimension=p.dimension, coordinates=p.coordinates,
        optimal=p.optimal, category=p.category, source=p.source,
        is_time_matrix=p.is_time_matrix, time_matrix=p.time_matrix,
    ) for p in numba_probs]
    return sorted(problems, key=lambda p: p.dimension)

# ── Warmup ───────────────────────────────────────────────────────────────────

def run_warmup(algorithms: List[str], all_problems: List[ProblemInstance]):
    """Warmup Numba JIT kernels via AlgorithmRegistry. SOTA engines are no-op."""
    burma = next((p for p in all_problems if p.name == "burma14"), None)
    if not burma:
        return
    numba_algos = [a for a in algorithms if a.startswith("Numba-") or a in ("B-PSO", "B-GA")]
    if not numba_algos:
        return
    print("\n[WARMUP] Compiling Numba JIT kernels sequentially...")
    for algo in numba_algos:
        try:
            sys.stdout.write(f"  - {algo}... ")
            sys.stdout.flush()
            AlgorithmRegistry.warmup(algo, burma)
            sys.stdout.write("OK\n")
            sys.stdout.flush()
        except Exception:
            sys.stdout.write("SKIP\n")
            sys.stdout.flush()
    print("[WARMUP] Complete.")

# ── Tuning Orchestrator ──────────────────────────────────────────────────────

class TuningOrchestrator:
    """Unified DOE/Bayesian tuning across Numba and SOTA engines."""

    def __init__(self, problems, algorithms, n_runs, max_combos, workers,
                 use_fractional=False, use_bayesian=False, param_overrides=None):
        self.problems = problems
        self.algorithms = algorithms
        self.n_runs = n_runs
        self.max_combos = max_combos
        self.workers = workers
        self.use_fractional = use_fractional
        self.use_bayesian = use_bayesian
        self.param_overrides = param_overrides or {}
        self.best_params = {}

    def _count_combinations(self, algo_name, spec=None):
        """Estimate number of parameter combinations for an algorithm."""
        if self.use_bayesian:
            return 0  # Bayesian doesn't use grid combos
        if spec:
            from academic_benchmark.cli_engine import _build_numba_parameter_space
            space = _build_numba_parameter_space(spec)
            if self.param_overrides and spec.name in self.param_overrides:
                for key, vals in self.param_overrides[spec.name].items():
                    if key in space:
                        space[key] = vals
            combos = generate_combinations(space, self.max_combos,
                                           strategy="fractional_fallback" if self.use_fractional else "sequential")
            return len(combos)
        else:
            from academic_benchmark.sota_engine import _build_sota_parameter_space
            space = _build_sota_parameter_space(algo_name)
            combos = generate_combinations(space, self.max_combos)
            return len(combos)

    def _print_pre_run_summary(self, numba_algos, sota_algos):
        """Print summary of planned runs before starting."""
        print("\n" + "=" * 70)
        print("CALISMA PLANI — Oncesi Ozet")
        print("=" * 70)
        print(f"  Problemler           : {', '.join(p.name for p in self.problems)}")
        print(f"  Worker Sayisi        : {self.workers}")
        if self.use_bayesian:
            print(f"  Trial Sayisi         : {self.max_combos} (Optuna TPE)")
        else:
            print(f"  Tekrar Sayisi        : {self.n_runs}")
            print(f"  Strateji             : {'Fractional' if self.use_fractional else 'Full Factorial'}")
        print(f"  Mod                  : {'Bayesian' if self.use_bayesian else 'Grid Search'}")
        print()

        total_tasks = 0
        if numba_algos:
            print("  [NUMBA Engine]")
            all_specs = _numba_specs()
            for algo in numba_algos:
                spec = next((s for s in all_specs if f"Numba-{s.name}" == algo or s.name == algo), None)
                combos = self._count_combinations(algo, spec) if spec else 0
                if self.use_bayesian:
                    tasks = self.max_combos  # Optuna trials
                    label = f"    {algo:<25}"
                    print(f"{label} {tasks:>4} trial × {len(self.problems)} problem = {tasks * len(self.problems):>6} task")
                    total_tasks += tasks * len(self.problems)
                else:
                    tasks = combos * len(self.problems) * self.n_runs
                    total_tasks += tasks
                    label = f"    {algo:<25}"
                    print(f"{label} {combos:>4} kombinasyon × {len(self.problems)} problem × {self.n_runs} run = {tasks:>6} task")
            print()

        if sota_algos:
            print("  [SOTA Engine]")
            for algo in sota_algos:
                clean = algo.replace("SOTA-", "")
                combos = self._count_combinations(clean)
                if self.use_bayesian:
                    tasks = self.max_combos  # Optuna trials
                    label = f"    {algo:<25}"
                    print(f"{label} {tasks:>4} trial × {len(self.problems)} problem = {tasks * len(self.problems):>6} task")
                    total_tasks += tasks * len(self.problems)
                else:
                    tasks = combos * len(self.problems) * self.n_runs
                    total_tasks += tasks
                    label = f"    {algo:<25}"
                    print(f"{label} {combos:>4} kombinasyon × {len(self.problems)} problem × {self.n_runs} run = {tasks:>6} task")
            print()

        print(f"  TOPLAM TASK          : {total_tasks}")
        est_time = total_tasks * 2  # rough 2s per task estimate
        if est_time > 3600:
            print(f"  Tahmini Sure       : ~{est_time // 3600} saat")
        elif est_time > 60:
            print(f"  Tahmini Sure       : ~{est_time // 60} dakika")
        else:
            print(f"  Tahmini Sure       : ~{est_time} saniye")
        print("=" * 70)

    def run(self) -> Dict[str, Dict[str, Any]]:
        numba_algos = [a for a in self.algorithms if a.startswith("Numba-") or a in ("B-PSO", "B-GA")]
        sota_algos = [a for a in self.algorithms if a.startswith("SOTA-")]

        # Print pre-run summary
        self._print_pre_run_summary(numba_algos, sota_algos)
        if input("\nBaslamak icin [Y/y]: ").strip().upper() != 'Y':
            print("Iptal edildi.")
            return self.best_params

        # Warmup Numba JIT before tuning
        if numba_algos:
            run_warmup(numba_algos, self.problems)

        if numba_algos:
            print("\n" + "=" * 70)
            print("[PHASE 1/2] NUMBA ENGINE TUNING")
            print(f"  Algoritmalar: {', '.join(numba_algos)}")
            print("=" * 70)
            self._run_numba_tuning(numba_algos)

        if sota_algos:
            if numba_algos:
                print("\n" + "=" * 70)
            else:
                print("\n" + "=" * 70)
            print("[PHASE 2/2] SOTA ENGINE TUNING")
            print(f"  Algoritmalar: {', '.join(sota_algos)}")
            print("=" * 70)
            self._run_sota_tuning(sota_algos)

        return self.best_params

    def _run_numba_tuning(self, algos):
        all_specs = _numba_specs()
        selected_specs = [s for s in all_specs if f"Numba-{s.name}" in algos or s.name in algos]
        if not selected_specs:
            return

        prob_instances = [DOEProblem(
            name=p.name, dimension=p.dimension, coordinates=p.coordinates,
            optimal=p.optimal, category=p.category, source=p.source,
            is_time_matrix=getattr(p, 'is_time_matrix', False),
            time_matrix=getattr(p, 'time_matrix', None),
        ) for p in self.problems]

        if self.use_bayesian:
            from academic_benchmark.cli_engine import _run_optuna_tuning_flow
            metadata = {"best_params": {}}
            _run_optuna_tuning_flow(prob_instances, selected_specs, self.n_runs, self.workers, metadata,
                                    param_overrides=self.param_overrides)
            self.best_params.update(metadata.get("best_params", {}))
        else:
            metadata = {"best_params": {}}
            best = _numba_tune(
                prob_instances, selected_specs, self.n_runs, _NUMBA_MAX_COMBOS, self.workers,
                metadata, skip_cached=True, use_fractional=self.use_fractional,
                param_overrides=self.param_overrides,
            )
            self.best_params.update(best)

    def _run_sota_tuning(self, algos):
        clean_algos = [a.replace("SOTA-", "") for a in algos]
        prob_instances = [TSPProblem(
            name=p.name, dimension=p.dimension, coordinates=p.coordinates,
            optimal=p.optimal, category=p.category,
        ) for p in self.problems]

        metadata = {"best_params": {}}
        if self.use_bayesian:
            _run_sota_optuna_tuning(
                prob_instances, clean_algos, self.n_runs, self.max_combos,
                self.workers, metadata,
            )
        else:
            _sota_tune(
                prob_instances, clean_algos, self.n_runs, self.max_combos, self.workers,
                metadata, skip_cached=True,
            )
        self.best_params.update(metadata.get("best_params", {}))

# ── Unified Benchmark Runner ─────────────────────────────────────────────────

def _run_single_task(args):
    """Worker task for ProcessPoolExecutor."""
    task, problem = args
    executor = AlgorithmRegistry.get_executor(task.algorithm)
    try:
        result = executor(problem, task.params, task.seed, task.run_idx)
        return result
    except Exception as e:
        return RunResult(
            problem=task.problem_name, algorithm=task.algorithm,
            run=task.run_idx, seed=task.seed,
            dimension=problem.dimension if problem else 0,
            optimal=problem.optimal if problem else None,
            tour_cost=float('inf'), gap_pct=None, elapsed_sec=0.0, error=str(e),
        )

def run_unified_benchmark(problems, algorithms, param_source, n_runs, workers, metadata, skip_cached=False):
    """Run benchmark with params from DB, manual entry, or defaults.

    param_source: 'db', 'manual', or 'default'
    """
    global _current_results, _current_metadata, _shutdown_requested

    # Resolve params per (problem, algorithm) pair
    algo_params = {}
    for p in problems:
        for algo in algorithms:
            key = f"{p.name}::{algo}"
            if param_source == 'db':
                best = _db_get_best(p.name, algo, TSPLIB_DB)
                algo_params[key] = best["params"] if best else {}
            else:
                algo_params[key] = {}

    # Build tasks
    prob_dict = {p.name: p for p in problems}
    tasks = []
    for p in problems:
        dm = None
        if p.dist_matrix is None:
            dm = _dm_from_cache(p.name, db_path=TSPLIB_DB)
            if dm is not None:
                p.dist_matrix = dm.astype(np.float64).tolist()
        if p.dist_matrix is None and p.coordinates:
            p.prepare_matrices(k=20)

        for algo in algorithms:
            for run_idx in range(1, n_runs + 1):
                seed = 42 + run_idx
                params = algo_params.get(f"{p.name}::{algo}", {}).copy()
                tasks.append(BenchmarkTask(
                    problem_name=p.name, algorithm=algo,
                    run_idx=run_idx, seed=seed, params=params,
                ))

    # Warmup
    run_warmup(algorithms, problems)

    # Execute
    worker_args = []
    for task in tasks:
        if task.problem_name in prob_dict:
            worker_args.append((task, prob_dict[task.problem_name]))

    print(f"\n[INFO] Executing {len(worker_args)} tasks across {workers} workers...")
    print("[INFO] Press Ctrl+X or Ctrl+Q to safely stop.")

    completed = 0
    start_time = time.time()
    saved_results = metadata.get("results", {})
    run_id = f"smart-benchmark-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        from academic_benchmark.tsplib_manager import save_benchmark_run
        save_benchmark_run(
            run_id,
            source="academic_smart",
            status="running",
            settings={"param_source": param_source, "tasks": len(worker_args), "workers": workers},
            db_path=TSPLIB_DB,
        )
    except Exception:
        pass

    with ProcessPoolExecutor(max_workers=workers) as executor:
        fut_maps = {executor.submit(_run_single_task, wa): wa for wa in worker_args}
        for future in concurrent.futures.as_completed(fut_maps):
            try:
                res = future.result()
            except Exception as exc:
                print(f"\n[ERROR] Task failed: {exc}")
                continue

            if _check_interrupt_key():
                _shutdown_requested = True

            if _shutdown_requested:
                graceful_shutdown()
                break

            _current_results.append(res.__dict__)
            completed += 1

            if getattr(res, 'error', None):
                print(f"\n[ERROR] {res.algorithm} on {res.problem}: {res.error}")

            gap_str = f"{res.gap_pct:.4f}%" if res.gap_pct is not None else "ERR"
            msg = f"[PROGRESS] {completed}/{len(worker_args)} | {res.algorithm} on {res.problem} -> Gap: {gap_str}"
            sys.stdout.write(f"\r{msg:<110}")
            sys.stdout.flush()

            if res.problem not in saved_results:
                saved_results[res.problem] = {}
            saved_results[res.problem][res.algorithm] = res.__dict__
            try:
                from academic_benchmark.tsplib_manager import save_benchmark_result
                save_benchmark_result(
                    run_id,
                    {
                        "problem": res.problem,
                        "algorithm": res.algorithm,
                        "run_number": res.run,
                        "problem_type": getattr(res, "problem_type", "tsp"),
                        "matrix_kind": getattr(res, "matrix_kind", "distance"),
                        "objective_cost": getattr(res, "objective_cost", res.tour_cost),
                        "tour_cost": res.tour_cost,
                        "gap": res.gap_pct,
                        "elapsed_ms": res.elapsed_sec * 1000,
                        "tour": res.tour,
                        "routes": getattr(res, "routes", None),
                        "route_loads": getattr(res, "route_loads", None),
                        "route_costs": getattr(res, "route_costs", None),
                        "num_vehicles": getattr(res, "num_vehicles", None),
                        "capacity_violations": getattr(res, "capacity_violations", 0),
                        "tw_violations": getattr(res, "tw_violations", 0),
                        "params": {"seed": res.seed},
                        "metadata": {"param_source": param_source},
                    },
                    db_path=TSPLIB_DB,
                )
            except Exception:
                pass

            if res.tour_cost > 0:
                _save_best_solution(
                    problem_name=res.problem, algorithm=res.algorithm,
                    params={"seed": res.seed}, tour=res.tour or [],
                    tour_length=float(res.tour_cost),
                    gap=float(res.gap_pct) if res.gap_pct is not None else 0.0,
                    db_path=TSPLIB_DB,
                )

    total_time = time.time() - start_time
    print(f"\n\n[DONE] Completed in {format_time(total_time)}")
    try:
        from academic_benchmark.tsplib_manager import save_benchmark_run
        save_benchmark_run(
            run_id,
            source="academic_smart",
            status="completed",
            settings={"param_source": param_source, "tasks": len(worker_args), "workers": workers},
            metadata={"results": completed, "elapsed_seconds": total_time},
            db_path=TSPLIB_DB,
        )
    except Exception:
        pass
    _current_metadata["results"] = saved_results
    save_metadata(METADATA_PATH, _current_metadata)

    # Summary
    print("\n" + "=" * 80)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Problem':<15} {'Algorithm':<20} {'Length':<12} {'Gap %':<10} {'Time (ms)':<12}")
    print("-" * 80)
    for res in _current_results:
        gap_str = f"{res.get('gap_pct'):.2f}" if res.get('gap_pct') is not None else "N/A"
        cost_str = f"{res.get('tour_cost'):.1f}" if res.get('tour_cost') is not None else "N/A"
        time_str = f"{res.get('elapsed_sec', 0)*1000:.0f}"
        print(f"{res.get('problem', ''):<15} {res.get('algorithm', ''):<20} {cost_str:<12} {gap_str:<10} {time_str:<12}")
    print("=" * 80)

# ── Menu Functions ───────────────────────────────────────────────────────────

def _menu_tuning(all_problems, metadata):
    """[1] PARAMETER TUNING (DOE/Bayesian)"""
    print("\n" + "=" * 70)
    print("[1] PARAMETRE TUNING (DOE/Bayesian)")
    print("=" * 70)

    # Select training problems
    print("\nEgitim problemlerini secin (tuning bu problemler uzerinde yapilacak):")
    selector = ProblemSelector(all_problems, title="EGITIM PROBLEMLERI")
    train_problems = selector.interactive_select()
    if not train_problems:
        print("Problem secilmedi.")
        return

    # Select algorithms
    all_algos = AlgorithmRegistry.list_algorithms()
    print("\n" + "-" * 60)
    print("ALGORITMA NOTLARI:")
    print("  B-PSO  : Bildiri2026 PSO — Discrete swap-sequence velocity,")
    print("           memetic 2-opt, Clerc constriction, periodic re-init")
    print("  B-GA   : Bildiri2026 GA  — Tournament selection, elite preserve,")
    print("           dedicated TSP crossover, built-in 2-opt polishing")
    print("  Numba-GA/PSO : Classical meta-heuristics with Numba JIT")
    print("-" * 60)
    selected_algos = multi_select(all_algos, "ALGORITMA SECIMI")
    if not selected_algos:
        return

    # Edit param spaces (optional)
    param_overrides = {}
    edit_raw = input("\nParametre uzaylarini duzenlemek ister misiniz? [e/H]: ").strip().upper()
    if edit_raw == 'E':
        for algo in selected_algos:
            space = AlgorithmRegistry.get_param_space(algo)
            if space:
                print(f"\n--- {algo} ---")
                edited = edit_param_space(space, algo)
                param_overrides[algo] = edited

    # Configure
    runs = select_run_count("TUNING", 3)
    workers = select_worker_count()
    print("\nTuning stratejisi:")
    print("  [G] Grid Search       — Tests every combo, picks best tested")
    print("  [F] Fractional        — Random subsample of grid (faster)")
    print("  [B] Bayesian (Optuna) — TPE surrogate model, finds optima between tested points")
    strat_raw = input("\nSeciminiz [G]: ").strip().upper()
    use_fractional = (strat_raw == 'F')
    use_bayesian = (strat_raw == 'B')
    max_combos = _NUMBA_MAX_COMBOS

    # Confirm
    print("\n" + "=" * 70)
    print("TUNING OZETI")
    print("=" * 70)
    print(f"  Egitim Problemleri : {len(train_problems)} adet")
    print(f"  Algoritmalar       : {', '.join(selected_algos)}")
    print(f"  Run Sayisi         : {runs}")
    print(f"  Worker             : {workers}")
    print(f"  Max Komb./Trial    : {max_combos}")
    if use_bayesian:
        print(f"  Mod                : Bayesian (Optuna TPE)")
    elif use_fractional:
        print(f"  Mod                : Fractional (random subsample)")
    else:
        print(f"  Mod                : Grid Search (full factorial)")
    # Confirmation moved to orchestrator.run() which shows detailed run plan

    # Run
    start = time.time()
    orchestrator = TuningOrchestrator(
        train_problems, selected_algos, runs, max_combos, workers,
        use_fractional=use_fractional, use_bayesian=use_bayesian,
        param_overrides=param_overrides,
    )
    best_params = orchestrator.run()
    if not best_params and not any(a.startswith("Numba-") or a.startswith("SOTA-") or a in ("B-PSO", "B-GA") for a in selected_algos):
        return

    # Save to DB
    numba_algos = [a for a in selected_algos if a.startswith("Numba-") or a in ("B-PSO", "B-GA")]
    sota_algos = [a for a in selected_algos if a.startswith("SOTA-")]
    if numba_algos:
        from academic_benchmark.cli_engine import DOEProblem as DP
        numba_probs = [DP(name=p.name, dimension=p.dimension, coordinates=p.coordinates,
                          optimal=p.optimal, category=p.category) for p in train_problems]
        numba_specs = [s for s in _numba_specs() if f"Numba-{s.name}" in numba_algos or s.name in numba_algos]
        saved = _numba_save_db(best_params, numba_probs, numba_specs)
        print(f"[PARAM_DB] {saved} numba parametre seti kaydedildi.")
    if sota_algos:
        from academic_benchmark.sota_engine import TSPProblem as SP
        sota_probs = [SP(name=p.name, dimension=p.dimension, coordinates=p.coordinates,
                         optimal=p.optimal, category=p.category) for p in train_problems]
        clean_sota = [a.replace("SOTA-", "") for a in sota_algos]
        saved = _sota_save_db(best_params, sota_probs, clean_sota)
        print(f"[PARAM_DB] {saved} sota parametre seti kaydedildi.")

    elapsed = time.time() - start
    print(f"\n[OK] Tuning tamamlandi! Toplam sure: {format_time(elapsed)}")
    input("\nDevam icin Enter...")

    # Ask whether to benchmark
    bm_raw = input("\nBenchmark da kosmak ister misiniz? [E/H]: ").strip().upper()
    if bm_raw == 'E':
        _menu_tune_and_benchmark(all_problems, metadata, train_problems, selected_algos, best_params)

def _menu_tune_and_benchmark(all_problems, metadata, train_problems=None, selected_algos=None, best_params=None):
    """[2] TUNE + BENCHMARK"""
    if train_problems is None:
        print("\n" + "=" * 70)
        print("[2] TUNE + BENCHMARK")
        print("=" * 70)
        selector = ProblemSelector(all_problems, title="EGITIM PROBLEMLERI")
        train_problems = selector.interactive_select()
        if not train_problems:
            return
        all_algos = AlgorithmRegistry.list_algorithms()
        selected_algos = multi_select(all_algos, "ALGORITMA SECIMI")
        if not selected_algos:
            return
        runs = select_run_count("TUNING", 3)
        workers = select_worker_count()
        max_combos = _NUMBA_MAX_COMBOS
        orchestrator = TuningOrchestrator(train_problems, selected_algos, runs, max_combos, workers)
        best_params = orchestrator.run()

    # Select benchmark problems (can differ from training)
    print("\nBenchmark icin problem secimi (Egitim problemlerinden farkli olabilir):")
    selector = ProblemSelector(all_problems, title="BENCHMARK PROBLEMLERI")
    bench_problems = selector.interactive_select()
    if not bench_problems:
        bench_problems = train_problems

    bm_runs = select_run_count("BENCHMARK", 3)
    bm_workers = select_worker_count()

    print(f"\n[2/2] EN IYI PARAMETRELERLE BENCHMARK ({len(bench_problems)} problem)...")
    run_unified_benchmark(bench_problems, selected_algos, 'default', bm_runs, bm_workers, metadata)
    input("\nDevam icin Enter...")

def _menu_benchmark_only(all_problems, metadata):
    """[3] BENCHMARK ONLY"""
    print("\n" + "=" * 70)
    print("[3] BENCHMARK ONLY")
    print("=" * 70)

    selector = ProblemSelector(all_problems, title="BENCHMARK PROBLEMLERI")
    problems = selector.interactive_select()
    if not problems:
        return

    all_algos = AlgorithmRegistry.list_algorithms()
    algos = multi_select(all_algos, "ALGORITMA SECIMI")
    if not algos:
        return

    print("\nParametre Kaynagi Secimi:")
    print("  [B] En iyi parametreleri DB'den yukle")
    print("  [M] Manuel parametre girisi (bildiri2026 stili)")
    print("  [D] Varsayilan parametreler")
    ps_raw = input("Seciminiz [B/M/D]: ").strip().upper()

    if ps_raw == 'B':
        numba_algos = [a for a in algos if a.startswith("Numba-") or a in ("B-PSO", "B-GA")]
        sota_algos = [a for a in algos if a.startswith("SOTA-")]
        if numba_algos:
            from academic_benchmark.cli_engine import DOEProblem as DP
            numba_probs = [DP(name=p.name, dimension=p.dimension, coordinates=p.coordinates,
                              optimal=p.optimal, category=p.category) for p in problems]
            numba_specs = [s for s in _numba_specs() if f"Numba-{s.name}" in numba_algos or s.name in numba_algos]
            _numba_load_db_params(numba_probs, numba_specs)
        if sota_algos:
            from academic_benchmark.sota_engine import TSPProblem as SP
            sota_probs = [SP(name=p.name, dimension=p.dimension, coordinates=p.coordinates,
                             optimal=p.optimal, category=p.category) for p in problems]
            clean_sota = [a.replace("SOTA-", "") for a in sota_algos]
            _sota_load_db_params(sota_probs, clean_sota)
    elif ps_raw == 'M':
        numba_algos = [a for a in algos if a.startswith("Numba-") or a in ("B-PSO", "B-GA")]
        sota_algos = [a for a in algos if a.startswith("SOTA-")]
        if numba_algos:
            numba_specs = [s for s in _numba_specs() if f"Numba-{s.name}" in numba_algos or s.name in numba_algos]
            _numba_manual_params(numba_specs)
        if sota_algos:
            clean_sota = [a.replace("SOTA-", "") for a in sota_algos]
            _sota_manual_params(clean_sota)

    runs = select_run_count("BENCHMARK", 3)
    workers = select_worker_count()

    # Confirm
    print("\n" + "=" * 70)
    print("BENCHMARK OZETI")
    print("=" * 70)
    print(f"  Problemler  : {len(problems)} adet")
    print(f"  Algoritmalar: {', '.join(algos)}")
    print(f"  Run Sayisi  : {runs}")
    print(f"  Worker      : {workers}")
    print(f"  Parametre   : {'DB' if ps_raw == 'B' else 'Manuel' if ps_raw == 'M' else 'Varsayilan'}")
    if input("\nBaslamak icin [Y/y]: ").strip().upper() != 'Y':
        return

    param_map = {'B': 'db', 'M': 'manual', 'D': 'default'}
    param_source = param_map.get(ps_raw, 'default')
    run_unified_benchmark(problems, algos, param_source, runs, workers, metadata)
    input("\nDevam icin Enter...")

def _menu_load_config(all_problems, metadata):
    """[4] LOAD CONFIG"""
    configs = sorted([f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")]) if os.path.exists(CONFIGS_DIR) else []
    if not configs:
        print("[HATA] Kayitli config dosyasi bulunamadi.")
        input("Devam icin Enter...")
        return

    print("\n--- Mevcut Config Dosyalari ---")
    for idx, c in enumerate(configs, 1):
        print(f"  [{idx}] {c}")
    raw = input("\nSeciminiz: ").strip()
    if not raw.isdigit() or int(raw) < 1 or int(raw) > len(configs):
        print("[HATA] Gecersiz secim.")
        input("Devam icin Enter...")
        return

    cfg_path = os.path.join(CONFIGS_DIR, configs[int(raw) - 1])
    with open(cfg_path, "r") as f:
        config = BenchmarkConfig.from_json(f.read())

    workers = select_worker_count()
    run_benchmark(config, all_problems, metadata.get("results", {}), workers)
    input("\nDevam icin Enter...")

def _menu_param_db():
    """[5] PARAMETER DB MANAGEMENT"""
    from academic_benchmark.param_db import (
        list_entries as _list, analyze_patterns as _analyze, delete_entry as _delete,
    )
    while True:
        clear_screen()
        print("\n" + "=" * 60)
        print("PARAMETRE DB YONETIMI".center(60))
        print("=" * 60)
        print("  [1] Kayitli parametreleri listele")
        print("  [2] Analiz (problem boyutuna gore ortak parametreler)")
        print("  [3] Kayit sil")
        print("  [4] SOTA engine DB yonetimi")
        print("  [Q] Ana menuye don")
        choice = input("\nSeciminiz: ").strip().upper()

        if choice == 'Q':
            break
        elif choice == '1':
            entries = _list()
            if not entries:
                print("[INFO] Parametre DB'si bos.")
            else:
                print(f"\n{'ID':>3} {'Tarih':<20} {'Problem':<12} {'Algoritma':<12} {'Skor':<10} {'Gap%':<8} {'Boyut':<6}")
                print("-" * 72)
                for e in entries:
                    gap_str = f"{e.get('gap', 0):.2f}" if e.get('gap') is not None else "N/A"
                    score = e.get('best_score', 0)
                    score_str = f"{score:<10.1f}" if isinstance(score, (int, float)) and not math.isinf(score) else f"{str(score):<10}"
                    print(f"{e['id']:>3} {e.get('timestamp', '?'):<20} {e['problem']:<12} {e['algorithm']:<12} {score_str} {gap_str:<8} {e.get('dimension', 0):<6}")
            input("\nDevam icin Enter...")
        elif choice == '2':
            analysis = _analyze()
            print(f"\n{analysis}")
            input("\nDevam icin Enter...")
        elif choice == '3':
            raw = input("Silmek istediginiz kayit ID'si: ").strip()
            if raw.isdigit():
                if _delete(int(raw)):
                    print("[OK] Kayit silindi.")
                else:
                    print("[HATA] Kayit bulunamadi.")
            input("Devam icin Enter...")
        elif choice == '4':
            _sota_param_db_menu()

# ── Legacy Benchmark Runner (for config loading) ─────────────────────────────

def run_benchmark(config: BenchmarkConfig, all_problems: List[ProblemInstance], saved_results: Dict, num_workers: int = 4):
    """Execute benchmark from a BenchmarkConfig (legacy compatibility)."""
    global _current_results, _current_metadata, _shutdown_requested
    if not config.tasks:
        print("\n[INFO] Configuration contains no tasks.")
        return

    print(f"\n[INFO] Executing {len(config.tasks)} tasks across {num_workers} workers...")
    prob_dict = {p.name: p for p in all_problems}
    worker_args = []
    for task in config.tasks:
        if task.problem_name in prob_dict:
            prob = prob_dict[task.problem_name]
            if prob.dist_matrix is None:
                dm_np = _dm_from_cache(prob.name, db_path=TSPLIB_DB)
                if dm_np is not None:
                    prob.dist_matrix = dm_np.astype(np.float64).tolist()
            if prob.dist_matrix is None and prob.coordinates:
                prob.prepare_matrices(k=20)
            worker_args.append((task, prob))

    run_warmup(list(set(t.algorithm for t in config.tasks)), all_problems)

    completed = 0
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        fut_maps = {executor.submit(_run_single_task, wa): wa for wa in worker_args}
        for future in concurrent.futures.as_completed(fut_maps):
            try:
                res = future.result()
            except Exception as exc:
                print(f"\n[ERROR] Task failed: {exc}")
                continue
            if _check_interrupt_key():
                _shutdown_requested = True
            if _shutdown_requested:
                graceful_shutdown()
                break
            _current_results.append(res.__dict__)
            completed += 1
            if getattr(res, 'error', None):
                print(f"\n[ERROR] {res.algorithm} on {res.problem}: {res.error}")
            gap_str = f"{res.gap_pct:.4f}%" if res.gap_pct is not None else "ERR"
            msg = f"[PROGRESS] {completed}/{len(worker_args)} | {res.algorithm} on {res.problem} -> Gap: {gap_str}"
            sys.stdout.write(f"\r{msg:<110}")
            sys.stdout.flush()
            if res.problem not in saved_results:
                saved_results[res.problem] = {}
            saved_results[res.problem][res.algorithm] = res.__dict__
            if res.tour_cost > 0:
                _save_best_solution(
                    problem_name=res.problem, algorithm=res.algorithm,
                    params={"seed": res.seed}, tour=res.tour or [],
                    tour_length=float(res.tour_cost),
                    gap=float(res.gap_pct) if res.gap_pct is not None else 0.0,
                    db_path=TSPLIB_DB,
                )

    total_time = time.time() - start_time
    print(f"\n\n[DONE] Completed in {format_time(total_time)}")
    _current_metadata["results"] = saved_results
    save_metadata(METADATA_PATH, _current_metadata)

    print("\n" + "=" * 80)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Problem':<15} {'Algorithm':<20} {'Length':<12} {'Gap %':<10} {'Time (ms)':<12}")
    print("-" * 80)
    for res in _current_results:
        gap_str = f"{res.get('gap_pct'):.2f}" if res.get('gap_pct') is not None else "N/A"
        cost_str = f"{res.get('tour_cost'):.1f}" if res.get('tour_cost') is not None else "N/A"
        time_str = f"{res.get('elapsed_sec', 0)*1000:.0f}"
        print(f"{res.get('problem', ''):<15} {res.get('algorithm', ''):<20} {cost_str:<12} {gap_str:<10} {time_str:<12}")
    print("=" * 80)

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global _current_metadata
    _current_metadata = load_metadata(METADATA_PATH)

    clear_screen()
    print("=" * 70)
    print(" UNIRIDE SMART BENCHMARK ENGINE")
    print("=" * 70)

    all_problems = load_problems()
    if not all_problems:
        print("[ERROR] No TSPLIB problems found.")
        return

    all_algos = AlgorithmRegistry.list_algorithms()
    if not all_algos:
        print("[WARNING] No algorithms registered.")
        return

    while True:
        clear_screen()
        print("=" * 70)
        print(" UNIRIDE SMART BENCHMARK ENGINE".center(70))
        print("=" * 70)
        print(f"\n  Kayitli Algoritmalar: {len(all_algos)}")
        print(f"  Yuklu Problemler   : {len(all_problems)}")

        print("\n--- CALISMA MODLARI ---")
        print("  [1] PARAMETRE TUNING (DOE/Bayesian)")
        print("      -> Secilen problemler uzerinde parametre optimizasyonu")
        print("      -> En iyi parametreler DB'ye kaydedilir")
        print("  [2] TUNE + BENCHMARK")
        print("      -> Once tuning yap, sonra farkli problemlerde benchmark kos")
        print("  [3] BENCHMARK ONLY")
        print("      -> Secilen problemlerde, istedigin parametrelerle kos")
        print("      -> Kaynak: [DB'den en iyi] / [Manuel] / [Varsayilan]")

        print("\n--- YAPILANDIRMA & ARAÇLAR ---")
        print("  [4] Config Yukle (Kaydedilmis config dosyasini calistir)")
        print("  [5] Parametre DB Yonetimi (Listele, Analiz, Sil)")

        print("\n--- DIGER ---")
        print("  [D] DASHBOARD (Streamlit ile Sonuclari Gorsellestir)")
        print("  [Q] Cikis")

        choice = input("\nSeciminiz: ").strip().upper()

        if choice == 'Q':
            print("Cikis yapiliyor...")
            return
        if choice == 'D':
            import subprocess
            from pathlib import Path
            print("\nDashboard aciliyor... Tarayicinizda http://localhost:8501 adresine gidin.")
            print("Durdurmak icin Ctrl+C basin.")
            try:
                subprocess.run(["streamlit", "run", str(Path(__file__).resolve().parent / "dashboard.py")])
            except KeyboardInterrupt:
                print("\nDashboard kapatildi.")
            input("Devam etmek icin Enter...")
            continue
        elif choice == '1':
            _menu_tuning(all_problems, _current_metadata)
        elif choice == '2':
            _menu_tune_and_benchmark(all_problems, _current_metadata)
        elif choice == '3':
            _menu_benchmark_only(all_problems, _current_metadata)
        elif choice == '4':
            _menu_load_config(all_problems, _current_metadata)
        elif choice == '5':
            _menu_param_db()

if __name__ == "__main__":
    main()
