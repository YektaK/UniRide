import subprocess
import time
import os

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(result.stdout)
    return result

def main():
    # 1. Tuning Step (Configs 1 to 5)
    print("--- STEP 1: TUNING ---")
    run_cmd("python 2_run_tuning.py 1,2,3,4,5")
    
    # 2. Analyze Tuning
    print("--- STEP 2: ANALYZE TUNING ---")
    run_cmd("python analyze_tuning.py")
    
    # 3. Benchmark Step
    # Problem IDs: berlin52: 2, eil51: 7, kroA100: 10, rd100: 35, st70: 37
    # Model IDs (Assuming fresh DB): 
    # berlin52: 1,2,3 | eil51: 4,5,6 | kroA100: 7,8,9 | rd100: 10,11,12 | st70: 13,14,15
    print("--- STEP 3: BENCHMARKING ---")
    benchmarks = [
        ("1,2,3", "2"),   # berlin52
        ("4,5,6", "7"),   # eil51
        ("7,8,9", "10"),  # kroA100
        ("10,11,12", "35"), # rd100
        ("13,14,15", "37")  # st70
    ]
    
    for models, problem in benchmarks:
        run_cmd(f"python 3_run_benchmark.py {models} {problem} 30")
        
    # 4. Final Analysis
    print("--- STEP 4: FINAL ANALYSIS ---")
    run_cmd("python analyze_benchmark.py")
    
    # 5. Visualize
    print("--- STEP 5: VISUALIZATION ---")
    run_cmd("python 5_visualize.py")
    
    print("--- BATCH PROCESS COMPLETE ---")

if __name__ == '__main__':
    main()
