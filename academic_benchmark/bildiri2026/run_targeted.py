import os
import sys
import json
import csv
import statistics
from datetime import datetime
import concurrent.futures

SCRIPT_DIR = os.path.dirname(os.path.abspath('3_run_benchmark.py'))
sys.path.insert(0, SCRIPT_DIR)
from core import ThreeOptSolver, OrOptSolver
from benchmarks.tsplib_benchmark import parse_tsplib

def solve_run(algo_name, params, run_idx, seed, prob_data, prob_name, model_id):
    kwargs = params.copy()
    kwargs['random_seed'] = seed
    if 'num_starts' in kwargs:
        kwargs['multi_start'] = (kwargs['num_starts'] > 1)
        
    solver = ThreeOptSolver(**kwargs) if algo_name == '3-opt' else OrOptSolver(**kwargs)
    result = solver.solve(prob_data)
        
    return {
        'problem': prob_name, 'model_id': model_id, 'algorithm': algo_name, 'run': run_idx,
        'duration': result.tour_length, 'elapsed_ms': result.elapsed_ms, 'seed': seed
    }

def main():
    print('Ozel Benchmark Baslatiliyor...')
    target_problems = ['eil51', 'berlin52', 'st70', 'kroA100', 'rd100']

    with open('data/tuned_parameters_db.json', 'r') as f:
        db = json.load(f)

    target_models = [m for m in db if m['algorithm'] in ['3-opt', 'Or-opt']]

    RESULTS_DIR = os.path.join(SCRIPT_DIR, 'results')
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_path = os.path.join(RESULTS_DIR, f'target_summary_{timestamp}.csv')

    with open(summary_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Problem', 'Algorithm', 'ModelID', 'Best', 'Worst', 'Mean', 'StdDev', 'MeanTimeMS'])

    for p_name in target_problems:
        p_path = os.path.join(SCRIPT_DIR, f'data/tsplib/{p_name}.tsp')
        prob = parse_tsplib(p_path)
        p_data = prob['coordinates']
        
        for entry in target_models:
            if entry['problem'] != p_name:
                continue
                
            m_id = entry['id']
            algo_name = entry['algorithm']
            params = entry['parameters']
            
            print(f'Running {algo_name} on {p_name}...')
            futures = []
            model_results = []
            with concurrent.futures.ProcessPoolExecutor() as executor:
                for run in range(30):
                    seed = 9000 + run + m_id * 100
                    futures.append(executor.submit(solve_run, algo_name, params, run + 1, seed, p_data, p_name, m_id))
                
                for f in concurrent.futures.as_completed(futures):
                    model_results.append(f.result())
                    
            D = [r['duration'] for r in model_results]
            T = [r['elapsed_ms'] for r in model_results]
            best, worst, mean, stdev, mean_ms = min(D), max(D), statistics.mean(D), (statistics.stdev(D) if len(D)>1 else 0), statistics.mean(T)
            print(f'{p_name} | {algo_name} | Mean: {mean:.1f} | Std: {stdev:.1f} | Time: {mean_ms:.0f}ms')
            
            with open(summary_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([p_name, algo_name, m_id, best, worst, mean, stdev, mean_ms])

    print(f'Bitti! Sonuclar: {summary_path}')

if __name__ == '__main__':
    main()
