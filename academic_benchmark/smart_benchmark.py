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

# Windows encoding fix
if sys.platform == 'win32' or 'pypy' in sys.implementation.name.lower():
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
NUM_WORKERS = min(cpu_count(), 4)

def signal_handler(signum, frame):
    """Ctrl+C Graceful Shutdown - Saves results immediately"""
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
                writer = csv.DictWriter(f, fieldnames=list(_current_results[0].keys()))
                writer.writeheader()
                writer.writerows(_current_results)
        print(f"[OK] {len(_current_results)} results saved to: {csv_path}")
    
    print("👋 Graceful shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

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
    
    def estimate_remaining(self, pending_tests: List[Tuple], num_workers: int = NUM_WORKERS, n_runs: int = 1) -> float:
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
        for p in problems:
            cache_status = ""
            if saved_results and all_strat_names:
                p_res = saved_results.get(p.name, {})
                tested = [s for s in all_strat_names if s in p_res]
                if len(tested) == len(all_strat_names):
                    cache_status = " [CACHED]"
                elif tested:
                    cache_status = f" ({len(tested)}/{len(all_strat_names)})"
            
            print(f"  {idx:>2}. {p.name:<12} (n={p.dimension:<5}){cache_status}")
            problem_map[idx] = p
            idx += 1
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
                    
                    dim = int(dim_m.group(1))
                    coords = []
                    for line in coord_m.group(1).strip().splitlines():
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            try: coords.append((float(parts[1]), float(parts[2])))
                            except: pass
                            
                    if coords:
                        opt = TSPLIB_OPTIMALS.get(raw_name)
                        cat = "small" if dim <= 100 else "medium" if dim <= 500 else "large"
                        prob = ProblemInstance(name=raw_name, dimension=dim, coordinates=coords, optimal=opt, category=cat)
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

def generate_run_config(problems: List[ProblemInstance], algorithms: List[str], saved_results: Dict, skip_cached: bool) -> BenchmarkConfig:
    """Phase 2: Decoupled config generation."""
    tasks = []
    n_runs = 3 # Default for now
    
    for p in problems:
        p_res = saved_results.get(p.name, {})
        for a in algorithms:
            if skip_cached and a in p_res:
                continue
            for run_idx in range(1, n_runs + 1):
                seed = 42 + run_idx
                # We can add default parameters here per algorithm if needed
                tasks.append(BenchmarkTask(problem_name=p.name, algorithm=a, run_idx=run_idx, seed=seed))
                
    config = BenchmarkConfig(
        name=f"SmartRun_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        created_at=datetime.now().isoformat(),
        tasks=tasks
    )
    return config

def run_benchmark(config: BenchmarkConfig, all_problems: List[ProblemInstance], saved_results: Dict):
    """Main execution loop reading from a BenchmarkConfig."""
    global _current_results, _current_metadata
    
    if not config.tasks:
        print("\n[INFO] Configuration contains no tasks. Nothing to do.")
        return
        
    print(f"\n[INFO] Executing {len(config.tasks)} tasks from config '{config.name}' across {NUM_WORKERS} workers...")
    
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
    
    with Pool(NUM_WORKERS) as pool:
        for res in pool.imap_unordered(_run_single_task, worker_args):
            if _shutdown_requested: break
            
            _current_results.append(res.__dict__)
            completed += 1
            
            # Print progress
            sys.stdout.write(f"\r[PROGRESS] {completed}/{len(worker_args)} tasks completed. Last: {res.algorithm} on {res.problem} -> Gap: {res.gap_pct if res.gap_pct is not None else 'ERR'}% ")
            sys.stdout.flush()
            
            # Save incremental
            if res.problem not in saved_results:
                saved_results[res.problem] = {}
            saved_results[res.problem][res.algorithm] = res.__dict__
            
    print(f"\n\n[DONE] Benchmark completed in {format_time(time.time() - start_time)}")
    _current_metadata["results"] = saved_results
    save_metadata(METADATA_PATH, _current_metadata)

# ============================================================
# ALGORITHM REGISTRATION (Wrappers)
# ============================================================

@AlgorithmRegistry.register("Dummy-Fast")
def dummy_fast_executor(problem: ProblemInstance, params: Dict, seed: int, run_idx: int) -> RunResult:
    """A dummy algorithm for testing the UX pipeline."""
    start = time.time()
    time.sleep(0.5) # Simulate work
    cost = problem.optimal * 1.05 if problem.optimal else 1000.0
    gap = 5.0 if problem.optimal else None
    
    return RunResult(
        problem=problem.name,
        algorithm="Dummy-Fast",
        run=run_idx,
        seed=seed,
        dimension=problem.dimension,
        optimal=problem.optimal,
        tour_cost=cost,
        gap_pct=gap,
        elapsed_sec=time.time() - start,
        iterations=100
    )

@AlgorithmRegistry.register("Dummy-Slow")
def dummy_slow_executor(problem: ProblemInstance, params: Dict, seed: int, run_idx: int) -> RunResult:
    start = time.time()
    time.sleep(2.0) 
    cost = problem.optimal * 1.01 if problem.optimal else 900.0
    gap = 1.0 if problem.optimal else None
    
    return RunResult(
        problem=problem.name,
        algorithm="Dummy-Slow",
        run=run_idx,
        seed=seed,
        dimension=problem.dimension,
        optimal=problem.optimal,
        tour_cost=cost,
        gap_pct=gap,
        elapsed_sec=time.time() - start,
        iterations=500
    )

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
        run_benchmark(config, all_problems, _current_metadata.get("results", {}))
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
    
    start, skip_cached = show_test_summary(selected_probs, selected_algos, _current_metadata.get("results", {}))
    if not start: return
    
    # Generate the decoupled config
    config = generate_run_config(selected_probs, selected_algos, _current_metadata.get("results", {}), skip_cached)
    
    if mode_choice == '2':
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        config_path = os.path.join(CONFIGS_DIR, "run_config.json")
        with open(config_path, "w") as f:
            f.write(config.to_json())
        print(f"\n✅ Config successfully generated at: {config_path}")
        print("You can edit this JSON file manually and run it using Mode 3.")
    elif mode_choice == '1':
        # Execute immediately
        run_benchmark(config, all_problems, _current_metadata.get("results", {}))
    elif mode_choice == '4':
        # Optuna Mode
        if len(selected_algos) > 1:
            print("[WARNING] Tuning multiple algorithms sequentially. This might take a while.")
        for algo in selected_algos:
            run_optuna_tuning(selected_probs, algo, n_trials=10)

if __name__ == "__main__":
    main()
