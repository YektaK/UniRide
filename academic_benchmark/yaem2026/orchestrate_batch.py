import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_cmd(args):
    print(f"Executing: {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, cwd=SCRIPT_DIR, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(result.stdout)
    return result

def main():
    # 1. Tuning Step (Configs 1-5, update based on actual config order)
    print("--- STEP 1: TUNING ---")
    run_cmd([sys.executable, "2_run_tuning.py", "1,2,3,4,5"])
    
    # 2. Analyze Tuning
    print("--- STEP 2: ANALYZE TUNING ---")
    run_cmd([sys.executable, "analyze_tuning.py"])
    
    # 3. Benchmark Step
    # Update model IDs based on actual DB after tuning.
    # Example assumes 9 algorithms (GA, PSO, GWO, GWO-Pure, HHO, HHO-Pure, 2-opt, 3-opt, Or-opt)
    # per problem. Adjust after tuning.
    print("--- STEP 3: BENCHMARKING ---")
    benchmarks = [
        ("1,2,3,4,5,6,7,8,9", "2"),    # berlin52
        ("10,11,12,13,14,15,16,17,18", "7"),   # eil51
        ("19,20,21,22,23,24,25,26,27", "10"),  # kroA100
    ]
    
    for models, problem in benchmarks:
        run_cmd([sys.executable, "3_run_benchmark.py", models, problem, "30"])
        
    # 4. Final Analysis
    print("--- STEP 4: FINAL ANALYSIS ---")
    run_cmd([sys.executable, "analyze_benchmark.py"])
    
    # 5. Visualize
    print("--- STEP 5: VISUALIZATION ---")
    run_cmd([sys.executable, "5_visualize.py"])
    
    print("--- BATCH PROCESS COMPLETE ---")

if __name__ == '__main__':
    main()
