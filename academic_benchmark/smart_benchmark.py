import sys
import os
import io
import time
import json
import signal
import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from multiprocessing import Pool, cpu_count
import math

# Windows encoding fix — use reconfigure() to avoid the Python 3.14 GC crash
# caused by TextIOWrapper closing the underlying buffer.
if sys.platform == 'win32' or 'pypy' in sys.implementation.name.lower():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from academic_benchmark.engine_core import ProblemInstance, RunResult, AlgorithmRegistry, BenchmarkTask, BenchmarkConfig
from academic_benchmark.benchmark_utils import (
    load_metadata, 
    save_metadata, 
    get_cpu_info,
    format_time
)

# Set up paths
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_DB = os.path.join(_ENGINE_DIR, "benchmark_db")
METADATA_PATH = os.path.join(BENCHMARK_DB, "smart_metadata.json")
HISTORY_DIR = os.path.join(BENCHMARK_DB, "history")
RESULTS_DIR = os.path.join(_ENGINE_DIR, "results")

CONFIGS_DIR = os.path.join(BENCHMARK_DB, "configs")

# Ensure dirs exist
os.makedirs(BENCHMARK_DB, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CONFIGS_DIR, exist_ok=True)

# Global State for Graceful Shutdown
_shutdown_requested = False
_current_metadata = None
_current_results = []
# NUM_WORKERS will be selected dynamically

def signal_handler(signum, frame):
    """Ignore Ctrl+C so user can copy text. Use Ctrl+X or Ctrl+Q to stop."""
    pass

signal.signal(signal.SIGINT, signal_handler)

def graceful_shutdown():
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n[!]  STOP REQUEST RECEIVED!")
    print("[NOTE] Saving current results, please wait...")
    
    if _current_metadata and _current_results:
        save_metadata(METADATA_PATH, _current_metadata)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(HISTORY_DIR, f"interrupted_smart_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if _current_results:
                import csv
                writer = csv.DictWriter(f, fieldnames=list(_current_results[0].keys()))
                writer.writeheader()
                writer.writerows(_current_results)
        print(f"[OK] {len(_current_results)} results saved to: {csv_path}")
    
    print("👋 Graceful shutdown complete.")
    sys.exit(0)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ============================================================
# DYNAMIC TIME ESTIMATOR (Legacy Restoration)
# ============================================================

class DynamicTimeEstimator:
    """Dynamic ETA based on real measurements from past runs."""
    
    def __init__(self):
        self.measurements = [] 
        self.category_avg = {'small': [], 'medium': [], 'large': []}
        self.algo_avg = {}
    
    def add_measurement(self, dimension: int, category: str, algorithm: str, time_ms: float):
        self.measurements.append((dimension, category, algorithm, time_ms))
        if category in self.category_avg:
            self.category_avg[category].append(time_ms)
        
        if algorithm not in self.algo_avg:
            self.algo_avg[algorithm] = []
        self.algo_avg[algorithm].append(time_ms)
    
    def estimate_time(self, dimension: int, category: str, algorithm: str) -> Optional[float]:
        # Similar size + same algorithm?
        similar = [(d, t) for d, c, a, t in self.measurements 
                   if a == algorithm and abs(d - dimension) < dimension * 0.3]
        
        if similar:
            return sum(t for _, t in similar) / len(similar)
        
        # Algorithm average?
        if algorithm in self.algo_avg and self.algo_avg[algorithm]:
            algo_time = sum(self.algo_avg[algorithm]) / len(self.algo_avg[algorithm])
            size_factor = dimension / 100
            return algo_time * size_factor
        
        # Category average?
        if category in self.category_avg and self.category_avg[category]:
            return sum(self.category_avg[category]) / len(self.category_avg[category])
        
        return None
    
    def estimate_remaining(self, pending_tests: List[Tuple], num_workers: int = 4, n_runs: int = 1) -> float:
        total_ms = 0
        for dimension, category, algorithm in pending_tests:
            est = self.estimate_time(dimension, category, algorithm)
            if est:
                total_ms += est
            else:
                defaults = {'small': 2000, 'medium': 8000, 'large': 30000}
                total_ms += defaults.get(category, 5000)
        
        total_ms = total_ms / num_workers
        total_ms *= n_runs
        return total_ms / 1000

# ============================================================
# INTERACTIVE CLI MENUS (Legacy Restoration)
# ============================================================

def multi_select_problems(all_problems: List[ProblemInstance], saved_results: Dict = None, all_strat_names: List[str] = None) -> List[ProblemInstance]:
    print("\n" + "=" * 70)
    print("PROBLEM SELECTION")
    print("=" * 70)
    print("Select problems to benchmark.")
    print("Selection: numbers (1,3,5-8), 'all', or 'small/medium/large' aliases.")
    print("-" * 70)
    
    categories = {'small': [], 'medium': [], 'large': []}
    for p in all_problems:
        if p.category in categories:
            categories[p.category].append(p)
            
    idx = 1
    problem_map = {}
    category_ranges = {'small': (0, 0), 'medium': (0, 0), 'large': (0, 0)}
    
    for cat_name, cat_label in [('small', 'SMALL'), ('medium', 'MEDIUM'), ('large', 'LARGE')]:
        problems = categories[cat_name]
        if not problems: continue
        problems.sort(key=lambda x: x.dimension)
        
        start_idx = idx
        print(f"\n[{cat_label} PROBLEMS]")
        
        # Format as 3-column table
        col_count = 3
        rows = [problems[i:i + col_count] for i in range(0, len(problems), col_count)]
        
        for row in rows:
            line_str = ""
            for p in row:
                cache_status = ""
                if saved_results and all_strat_names:
                    p_res = saved_results.get(p.name, {})
                    tested = [s for s in all_strat_names if s in p_res]
                    if len(tested) == len(all_strat_names):
                        cache_status = "[C]" # Cached
                    elif tested:
                        cache_status = f"[{len(tested)}/{len(all_strat_names)}]"
                
                # Format each cell
                cell = f"{idx:>2}. {p.name:<8} (n={p.dimension:<5}) {cache_status:<5}"
                line_str += f"{cell:<35}"
                problem_map[idx] = p
                idx += 1
            print(line_str)
            
        category_ranges[cat_name] = (start_idx, idx - 1)
        
    print("\n" + "-" * 70)
    print("Selection: ", end="")
    user_input = input().strip().lower()
    
    selected = []
    if user_input in ['all', 'tum']:
        return all_problems[:]
    elif user_input in ['small', 'k']:
        start, end = category_ranges['small']
        selected = [problem_map[i] for i in range(start, end + 1)]
        return selected
    elif user_input in ['medium', 'o']:
        start, end = category_ranges['medium']
        selected = [problem_map[i] for i in range(start, end + 1)]
        return selected
    elif user_input in ['large', 'b']:
        start, end = category_ranges['large']
        selected = [problem_map[i] for i in range(start, end + 1)]
        return selected
        
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if i in problem_map: selected.append(problem_map[i])
            else:
                i = int(part)
                if i in problem_map: selected.append(problem_map[i])
    except:
        print("Invalid selection.")
        return []
        
    seen = set()
    unique_selected = []
    for p in selected:
        if p.name not in seen:
            seen.add(p.name)
            unique_selected.append(p)
            
    print(f"\n✅ {len(unique_selected)} problems selected.")
    return unique_selected


def multi_select_algorithms(all_strat_names: List[str]) -> List[str]:
    print("\n" + "=" * 70)
    print("ALGORITHM SELECTION")
    print("=" * 70)
    
    for idx, name in enumerate(all_strat_names, 1):
        print(f"  {idx:>2}. {name}")
        
    print("-" * 70)
    print("Selection (e.g. 1,2,5 or 'all'): ", end="")
    user_input = input().strip().lower()
    
    selected = []
    if user_input == 'all':
        return all_strat_names[:]
        
    try:
        parts = user_input.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if 1 <= i <= len(all_strat_names):
                        selected.append(all_strat_names[i - 1])
            else:
                i = int(part)
                if 1 <= i <= len(all_strat_names):
                    selected.append(all_strat_names[i - 1])
    except:
        print("Invalid selection.")
        return []
        
    seen = set()
    unique_selected = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            unique_selected.append(s)
            
    print(f"\n✅ {len(unique_selected)} algorithms selected.")
    return unique_selected

def load_problems() -> List[ProblemInstance]:
    """Temporary loader, will be integrated with universal loader."""
    # We will expand this to full TSPLIB loading in the next task.
    print("[INFO] Loading problems from TSPLIB archive...")
    
    # Porting from master_sota_engine.py
    import tarfile, gzip, re
    from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS
    TSPLIB_ARCHIVE = os.path.join(_ENGINE_DIR, "tsplib_problems", "ALL_tsp.tar.gz")
    
    problems = []
    if os.path.exists(TSPLIB_ARCHIVE):
        try:
            with tarfile.open(TSPLIB_ARCHIVE, "r:gz") as tar:
                for member in tar.getmembers():
                    if not member.name.endswith(".tsp.gz"): continue
                    raw_name = os.path.basename(member.name).replace(".tsp.gz", "").lower()
                    fobj = tar.extractfile(member)
                    if not fobj: continue
                    text = gzip.decompress(fobj.read()).decode("latin-1")
                    
                    # Parse
                    coord_m = re.search(r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)", text, re.DOTALL | re.I)
                    if not coord_m: continue
                    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", text, re.I)
                    if not dim_m: continue
                    
                    type_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\w+)", text, re.I)
                    ew_type = type_m.group(1).upper() if type_m else "EUC_2D"
                    
                    dim = int(dim_m.group(1))
                    coords = []
                    for line in coord_m.group(1).strip().splitlines():
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            try: coords.append((float(parts[1]), float(parts[2])))
                            except: pass
                            
                    if coords:
                        import math
                        def geo_dist(p1, p2):
                            deg1_x = math.trunc(p1[0]); min1_x = p1[0] - deg1_x; rad1_x = math.pi * (deg1_x + 5.0 * min1_x / 3.0) / 180.0
                            deg1_y = math.trunc(p1[1]); min1_y = p1[1] - deg1_y; rad1_y = math.pi * (deg1_y + 5.0 * min1_y / 3.0) / 180.0
                            deg2_x = math.trunc(p2[0]); min2_x = p2[0] - deg2_x; rad2_x = math.pi * (deg2_x + 5.0 * min2_x / 3.0) / 180.0
                            deg2_y = math.trunc(p2[1]); min2_y = p2[1] - deg2_y; rad2_y = math.pi * (deg2_y + 5.0 * min2_y / 3.0) / 180.0
                            q1 = math.cos(rad1_y - rad2_y); q2 = math.cos(rad1_x - rad2_x); q3 = math.cos(rad1_x + rad2_x)
                            return int(6378.388 * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)
                            
                        def att_dist(p1, p2):
                            rij = math.sqrt(((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) / 10.0)
                            tij = int(round(rij))
                            return tij + 1 if tij < rij else tij

                        dist_matrix = []
                        for i in range(len(coords)):
                            row = []
                            for j in range(len(coords)):
                                if i == j:
                                    row.append(0.0)
                                else:
                                    if ew_type == "GEO": row.append(float(geo_dist(coords[i], coords[j])))
                                    elif ew_type == "ATT": row.append(float(att_dist(coords[i], coords[j])))
                                    elif ew_type == "CEIL_2D": row.append(float(math.ceil(math.hypot(coords[i][0]-coords[j][0], coords[i][1]-coords[j][1]))))
                                    else: row.append(float(int(round(math.hypot(coords[i][0]-coords[j][0], coords[i][1]-coords[j][1])))))
                            dist_matrix.append(row)
                            
                        opt = TSPLIB_OPTIMALS.get(raw_name)
                        cat = "small" if dim <= 100 else "medium" if dim <= 500 else "large"
                        prob = ProblemInstance(name=raw_name, dimension=dim, coordinates=coords, optimal=opt, category=cat, dist_matrix=dist_matrix)
                        problems.append(prob)
        except Exception as e:
            print(f"[ERROR] Failed to load tar: {e}")
            
    return sorted(problems, key=lambda p: p.dimension)

def show_test_summary(problems: List[ProblemInstance], algorithms: List[str], saved_results: Dict) -> Tuple[bool, bool]:
    clear_screen()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len(problems) * len(algorithms)
    
    # Cache analysis
    cached = 0
    for p in problems:
        p_res = saved_results.get(p.name, {})
        for a in algorithms:
            if a in p_res: cached += 1
            
    print(f"   • Problems: {len(problems)}")
    print(f"   • Algorithms: {len(algorithms)}")
    print(f"   • Total tests (per run): {total_tests}")
    
    skip_cached = False
    if cached > 0:
        print(f"\n[CACHE] {cached} tests already exist in DB.")
        print("   [S] Skip cached (Run only new tests)")
        print("   [R] Re-run all (Overwrite)")
        choice = input("Choice [S/R]: ").strip().upper()
        if choice == 'S': skip_cached = True
        
    print("\n[Y] Start    [Q] Quit")
    choice = input("Choice: ").strip().upper()
    return (choice == 'Y', skip_cached)

def main():
    global _current_metadata
    _current_metadata = load_metadata(METADATA_PATH)
    
    clear_screen()
    print("=" * 70)
    print(" 🎓 UNIRIDE SMART BENCHMARK ENGINE")
    print("=" * 70)
    
    # 1. Load Problems
    all_problems = load_problems()
    if not all_problems:
        print("[ERROR] No TSPLIB problems found.")
        return
        
    # 2. Select Problems
    selected_probs = multi_select_problems(all_problems, _current_metadata.get("results", {}), AlgorithmRegistry.list_algorithms())
    if not selected_probs: return
    
    # 3. Select Algorithms
    all_algos = AlgorithmRegistry.list_algorithms()
    if not all_algos:
        print("[WARNING] No algorithms registered yet. Please add them to AlgorithmRegistry.")
        return
    selected_algos = multi_select_algorithms(all_algos)
    if not selected_algos: return
    
    # 4. Confirm Summary
    start, skip_cached = show_test_summary(selected_probs, selected_algos, _current_metadata.get("results", {}))
    if not start: return
    
def _run_single_task(args):
    """Worker task for multiprocessing."""
    task, problem = args
    executor = AlgorithmRegistry.get_executor(task.algorithm)
    try:
        result = executor(problem, task.params, task.seed, task.run_idx)
        return result
    except Exception as e:
        return RunResult(
            problem=task.problem_name,
            algorithm=task.algorithm,
            run=task.run_idx,
            seed=task.seed,
            dimension=problem.dimension if problem else 0,
            optimal=problem.optimal if problem else None,
            tour_cost=float('inf'),
            gap_pct=None,
            elapsed_sec=0.0,
            error=str(e)
        )

def generate_run_config(problems: List[ProblemInstance], algorithms: List[str], saved_results: Dict, skip_cached: bool, n_runs: int, custom_params: Dict = None) -> BenchmarkConfig:
    """Phase 2: Decoupled config generation."""
    tasks = []
    
    for p in problems:
        p_res = saved_results.get(p.name, {})
        for a in algorithms:
            if skip_cached and a in p_res:
                continue
            for run_idx in range(1, n_runs + 1):
                seed = 42 + run_idx
                params = custom_params.copy() if custom_params else {}
                tasks.append(BenchmarkTask(problem_name=p.name, algorithm=a, run_idx=run_idx, seed=seed, params=params))
                
    config = BenchmarkConfig(
        name=f"SmartRun_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        created_at=datetime.now().isoformat(),
        tasks=tasks
    )
    return config

def run_benchmark(config: BenchmarkConfig, all_problems: List[ProblemInstance], saved_results: Dict, num_workers: int = 4):
    """Main execution loop reading from a BenchmarkConfig."""
    global _current_results, _current_metadata
    
    if not config.tasks:
        print("\n[INFO] Configuration contains no tasks. Nothing to do.")
        return
        
    print(f"\n[INFO] Executing {len(config.tasks)} tasks from config '{config.name}' across {num_workers} workers...")
    
    # Map problem names to instances for fast lookup
    prob_dict = {p.name: p for p in all_problems}
    
    # Package args for workers
    worker_args = []
    for task in config.tasks:
        if task.problem_name in prob_dict:
            prob = prob_dict[task.problem_name]
            # Lazy prepare matrices
            if prob.dist_matrix is None and prob.coordinates:
                print(f"[INFO] Preparing KNN/Distance matrices for {prob.name}...")
                prob.prepare_matrices(k=20)
            worker_args.append((task, prob))
        else:
            print(f"[WARNING] Problem {task.problem_name} not loaded. Skipping task.")
    
    # Task 3.1: Numba Multiprocessing Warmup Phase (Lock fix)
    unique_algos = list(set([t.algorithm for t in config.tasks]))
    burma = prob_dict.get("burma14")
    if burma and unique_algos:
        print("\n[WARMUP] Sequentially compiling Numba kernels to prevent multiprocessing lock contention...")
        for algo in unique_algos:
            executor = AlgorithmRegistry.get_executor(algo)
            try:
                sys.stdout.write(f"\r  - Warming up {algo}... ")
                sys.stdout.flush()
                # Run 1 iteration of the algorithm to compile Numba cache
                executor(burma, {"max_iterations": 1}, 42, 1)
            except Exception:
                pass
        print("\r[WARMUP] Complete! Cache is safely locked.         ")
        
    completed = 0
    start_time = time.time()
    
    print("\n[INFO] Press Ctrl+X or Ctrl+Q to safely stop the benchmark and save progress.")
    
    with Pool(num_workers) as pool:
        for res in pool.imap_unordered(_run_single_task, worker_args):
            # Non-blocking keyboard check for Windows
            if sys.platform == 'win32':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # \x18 is Ctrl+X, \x11 is Ctrl+Q
                    if key in (b'\x18', b'\x11', b'q', b'x'):
                        _shutdown_requested = True
            
            if _shutdown_requested: 
                graceful_shutdown()
                break
            
            _current_results.append(res.__dict__)
            completed += 1
            
            # Print progress
            gap_str = f"{res.gap_pct:.4f}%" if res.gap_pct is not None else "ERR"
            msg = f"[PROGRESS] {completed}/{len(worker_args)} tasks completed. Last: {res.algorithm} on {res.problem} -> Gap: {gap_str}"
            sys.stdout.write(f"\r{msg:<110}")
            sys.stdout.flush()
            
            # Save incremental
            if res.problem not in saved_results:
                saved_results[res.problem] = {}
            saved_results[res.problem][res.algorithm] = res.__dict__
            
    total_time = time.time() - start_time
    print(f"\n\n[DONE] Benchmark completed in {format_time(total_time)}")
    _current_metadata["results"] = saved_results
    save_metadata(METADATA_PATH, _current_metadata)
    
    # 4. Final Summary Table
    print("\n" + "=" * 80)
    print(" BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Problem':<15} {'Algorithm':<15} {'Length':<12} {'Gap %':<10} {'Süre (ms)':<12}")
    print("-" * 80)
    for res in _current_results:
        gap_str = f"{res.get('gap_pct'):.2f}" if res.get('gap_pct') is not None else "N/A"
        cost_str = f"{res.get('tour_cost'):.1f}" if res.get('tour_cost') is not None else "N/A"
        time_str = f"{res.get('elapsed_sec', 0)*1000:.0f}"
        print(f"{res.get('problem', ''):<15} {res.get('algorithm', ''):<15} {cost_str:<12} {gap_str:<10} {time_str:<12}")
    print("=" * 80)

# ============================================================
# ALGORITHM REGISTRATION (Wrappers)
# ============================================================

# Removed Dummy algorithms

def run_optuna_tuning(problems: List[ProblemInstance], algorithm: str, n_trials: int = 20):
    """Phase 4.1: Optuna Bayesian Optimization Integration."""
    try:
        import optuna
    except ImportError:
        print("[ERROR] Optuna is not installed. Please run `pip install optuna`.")
        return
        
    print(f"\n[OPTUNA] Starting Bayesian Optimization for {algorithm} across {len(problems)} problems. Trials: {n_trials}")
    executor = AlgorithmRegistry.get_executor(algorithm)
    
    def objective(trial):
        # Define search space generically (algorithms can define their own later, this is a proof of concept)
        params = {
            "pop_size": trial.suggest_int("pop_size", 50, 200),
            "max_iterations": trial.suggest_int("max_iterations", 100, 500, step=50),
            "mutation_rate": trial.suggest_float("mutation_rate", 0.01, 0.2)
        }
        
        total_gap = 0.0
        valid_runs = 0
        
        for p in problems:
            # Lazy prepare matrices
            if p.dist_matrix is None and p.coordinates:
                p.prepare_matrices(k=20)
                
            try:
                res = executor(p, params, 42, 1) # Single run for tuning speed
                if res.gap_pct is not None:
                    total_gap += res.gap_pct
                    valid_runs += 1
            except Exception as e:
                pass
                
        if valid_runs == 0:
            raise optuna.TrialPruned()
            
        return total_gap / valid_runs

    study = optuna.create_study(direction="minimize", study_name=f"{algorithm}_tuning")
    study.optimize(objective, n_trials=n_trials)
    
    print("\n[OPTUNA DONE] Best Parameters:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
    print(f"  Best Avg Gap: {study.best_value:.2f}%")

# Automatically register all NUMBA strategies
try:
    from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, STRATEGIES
    
    for strat_name, strategy_payload, default_params in STRATEGIES:
        # Using a closure to capture strat_name and spec properly
        def make_numba_executor(payload, name, default_p):
            def _numba_executor(problem: ProblemInstance, params: Dict, seed: int, run_idx: int) -> RunResult:
                start = time.time()
                # Run the legacy Numba engine adapter
                class MockProblem:
                    def __init__(self, p):
                        self.name = p.name
                        self.dimension = p.dimension
                        self.coordinates = p.coordinates
                        self.optimal = p.optimal
                        self.category = p.category
                        self.source = p.source
                        self.is_time_matrix = p.is_time_matrix
                        self.time_matrix = p.time_matrix
                
                # Merge parameters
                merged_params = default_p.copy()
                merged_params.update(params)
                
                # Check if it's the specific bildiri2026 strings that master_numba_engine uses
                import optimizer_api.tests.run_interactive_benchmark_v2_numba as bench_v2
                
                orig_create = bench_v2.create_np_distance_matrix
                orig_calc = bench_v2.calculate_tour_length
                
                def patched_create(coords):
                    import numpy as np
                    return np.array(problem.dist_matrix, dtype=np.float64)
                    
                def patched_calc(tour, coords):
                    if not tour: return 0
                    total = 0.0
                    for i in range(len(tour)):
                        idx1, idx2 = tour[i], tour[(i + 1) % len(tour)]
                        # Handling "L{i}" string format used by legacy engine
                        if isinstance(idx1, str) and idx1.startswith("L"): idx1 = int(idx1[1:])
                        if isinstance(idx2, str) and idx2.startswith("L"): idx2 = int(idx2[1:])
                        # Fallback for 1-based indices
                        if isinstance(idx1, int) and idx1 >= problem.dimension: idx1 -= 1
                        if isinstance(idx2, int) and idx2 >= problem.dimension: idx2 -= 1
                        total += problem.dist_matrix[idx1][idx2]
                    return int(total)
                
                bench_v2.create_np_distance_matrix = patched_create
                bench_v2.calculate_tour_length = patched_calc
                
                try:
                    raw_res = run_single_test(MockProblem(problem), payload, seed, merged_params)
                finally:
                    bench_v2.create_np_distance_matrix = orig_create
                    bench_v2.calculate_tour_length = orig_calc
                
                # Extract iterations and convergence
                iters = merged_params.get("iterations", merged_params.get("max_iterations", 100))
                
                return RunResult(
                    problem=problem.name,
                    algorithm=name,
                    run=run_idx,
                    seed=seed,
                    dimension=problem.dimension,
                    optimal=problem.optimal,
                    tour_cost=float(raw_res["tour_length"]),
                    gap_pct=float(raw_res["gap"]) if "gap" in raw_res and not math.isnan(float(raw_res["gap"])) else None,
                    elapsed_sec=time.time() - start,
                    iterations=iters,
                    convergence_profile=raw_res.get("convergence_profile", []),
                    evaluations=0 
                )
            return _numba_executor
            
        AlgorithmRegistry.register(f"Numba-{strat_name}")(make_numba_executor(strategy_payload, f"Numba-{strat_name}", default_params))
        print(f"[REGISTRY] Auto-registered Numba-{strat_name}")
except ImportError as e:
    print(f"[WARNING] Could not load Numba strategies: {e}")

# Automatically register SOTA strategies
try:
    from academic_benchmark.sota_tsp import (
        E2BSO_TSP, R2DMA_TSP, PAOEA_TSP,
        E2BSOTSPConfig, R2DMATSPConfig, PAOEAConfig,
    )
    
    SOTA_ALGORITHMS = {
        "SOTA-E2BSO": (E2BSO_TSP, E2BSOTSPConfig),
        "SOTA-R2DMA": (R2DMA_TSP, R2DMATSPConfig),
        "SOTA-PAOEA": (PAOEA_TSP, PAOEAConfig),
    }

    for algo_name, (solver_class, config_class) in SOTA_ALGORITHMS.items():
        def make_sota_executor(s_class, c_class, name):
            def _sota_executor(problem: ProblemInstance, params: Dict, seed: int, run_idx: int) -> RunResult:
                start = time.time()
                
                cfg = params.copy()
                cfg["seed"] = seed
                
                # Apply dynamic limits based on problem size (porting from master_sota_engine)
                n = problem.dimension
                if "population_size" not in cfg:
                    cfg["population_size"] = max(20, min(60, n // 2))
                if "max_iterations" not in cfg:
                    cfg["max_iterations"] = max(200, min(500, n * 5))
                    
                # We dynamically subclass to inject the true TSPLIB distance matrix (GEO/ATT support)
                # overriding the default Euclidean-only `_set_problem` in BaseTSPSolver
                class PatchedSolver(s_class):
                    def _set_problem(self, coords):
                        self._coordinates = coords
                        self._n = len(coords)
                        self._dist_matrix = problem.dist_matrix
                        
                        try:
                            import numpy as np
                            self._dist_matrix_np = np.array(self._dist_matrix, dtype=np.float64)
                        except ImportError:
                            self._dist_matrix_np = None

                solver = PatchedSolver(c_class(**cfg))
                result = solver.solve(problem.coordinates)
                
                return RunResult(
                    problem=problem.name,
                    algorithm=name,
                    run=run_idx,
                    seed=seed,
                    dimension=problem.dimension,
                    optimal=problem.optimal,
                    tour_cost=float(result.tour_length),
                    gap_pct=float((result.tour_length - problem.optimal) / problem.optimal * 100.0) if problem.optimal else None,
                    elapsed_sec=time.time() - start,
                    iterations=getattr(result, "iterations", cfg.get("max_iterations", 0)),
                    evaluations=0 
                )
            return _sota_executor
            
        AlgorithmRegistry.register(algo_name)(make_sota_executor(solver_class, config_class, algo_name))
        print(f"[REGISTRY] Auto-registered {algo_name}")
except ImportError as e:
    print(f"[WARNING] Could not load SOTA strategies: {e}")

def main():
    global _current_metadata
    _current_metadata = load_metadata(METADATA_PATH)
    
    clear_screen()
    print("=" * 70)
    print(" 🎓 UNIRIDE SMART BENCHMARK ENGINE")
    print("=" * 70)
    
    # 1. Load Problems
    all_problems = load_problems()
    if not all_problems:
        print("[ERROR] No TSPLIB problems found.")
        return
        
    # Main Menu (Phase 2 Config Options)
    print("\n[MENU] Choose execution mode:")
    print("  1. Interactive Benchmark (Generate & Run immediately)")
    print("  2. Generate Config Only (Create run_config.json)")
    print("  3. Run from Config (Execute existing run_config.json)")
    print("  4. Optuna Parameter Tuning (Bayesian Optimization)")
    print("  Q. Quit")
    
    mode_choice = input("Choice: ").strip().lower()
    if mode_choice == 'q': return
    
    if mode_choice == '3':
        config_path = os.path.join(CONFIGS_DIR, "run_config.json")
        if not os.path.exists(config_path):
            print(f"[ERROR] Config not found at {config_path}")
            return
        with open(config_path, "r") as f:
            config = BenchmarkConfig.from_json(f.read())
            
        print("\n" + "=" * 70)
        num_workers_str = input(f"Enter number of worker processes (default {min(cpu_count(), 6)}): ").strip()
        num_workers = int(num_workers_str) if num_workers_str.isdigit() else min(cpu_count(), 6)
        
        run_benchmark(config, all_problems, _current_metadata.get("results", {}), num_workers=num_workers)
        return
    
    # Otherwise, need problem/algo selection
    selected_probs = multi_select_problems(all_problems, _current_metadata.get("results", {}), AlgorithmRegistry.list_algorithms())
    if not selected_probs: return
    
    all_algos = AlgorithmRegistry.list_algorithms()
    if not all_algos:
        print("[WARNING] No algorithms registered.")
        return
    selected_algos = multi_select_algorithms(all_algos)
    if not selected_algos: return
    
    # Ask for flexibility parameters before summary
    print("\n" + "=" * 70)
    print("EXECUTION PARAMETERS")
    print("=" * 70)
    n_runs_str = input("Enter number of statistical runs per test (default 3): ").strip()
    n_runs = int(n_runs_str) if n_runs_str.isdigit() else 3
    
    num_workers_str = input(f"Enter number of worker processes (default {min(cpu_count(), 6)}): ").strip()
    num_workers = int(num_workers_str) if num_workers_str.isdigit() else min(cpu_count(), 6)
    
    custom_params = {}
    custom_params_str = input("Enter custom algorithm parameters as JSON (or press Enter to skip): ").strip()
    if custom_params_str:
        try:
            custom_params = json.loads(custom_params_str)
        except Exception as e:
            print(f"[WARNING] Invalid JSON parameters: {e}. Ignoring custom params.")
    
    start, skip_cached = show_test_summary(selected_probs, selected_algos, _current_metadata.get("results", {}))
    if not start: return
    
    # Generate the decoupled config
    config = generate_run_config(selected_probs, selected_algos, _current_metadata.get("results", {}), skip_cached, n_runs, custom_params)
    
    if mode_choice == '2':
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        config_path = os.path.join(CONFIGS_DIR, "run_config.json")
        with open(config_path, "w") as f:
            f.write(config.to_json())
        print(f"\n✅ Config successfully generated at: {config_path}")
        print("You can edit this JSON file manually and run it using Mode 3.")
    elif mode_choice == '1':
        # Execute immediately — also persist the config so custom params survive interruptions
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        config_path = os.path.join(CONFIGS_DIR, "run_config.json")
        with open(config_path, "w") as f:
            f.write(config.to_json())
        print(f"\n[INFO] Config saved to {config_path} for resume (Mode 3).")
        run_benchmark(config, all_problems, _current_metadata.get("results", {}), num_workers=num_workers)
    elif mode_choice == '4':
        # Optuna Mode
        if len(selected_algos) > 1:
            print("[WARNING] Tuning multiple algorithms sequentially. This might take a while.")
        for algo in selected_algos:
            run_optuna_tuning(selected_probs, algo, n_trials=10)

if __name__ == "__main__":
    main()
