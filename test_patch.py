import sys, os, time, random
sys.path.insert(0, '.')

_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academic_benchmark")
TSPLIB_DB = os.path.join(_ENGINE_DIR, "tsplib_data", "tsplib.db")

from academic_benchmark.tsplib_manager import get_distance_matrix, get_all_problems
from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS
from academic_benchmark.engine_core import ProblemInstance
import numpy as np

probs = get_all_problems()
pdata = next(x for x in probs if x['name'] == 'pr76')
prob = ProblemInstance(name='pr76', dimension=76, coordinates=pdata['coordinates'],
                        optimal=TSPLIB_OPTIMALS.get('pr76'), category='medium', source='tsplib')

dm_np = get_distance_matrix('pr76', db_path=TSPLIB_DB)
prob.dist_matrix = dm_np.astype(np.float64).tolist()

class MockProblem:
    def __init__(self, p):
        self.name = p.name; self.dimension = p.dimension; self.coordinates = p.coordinates
        self.optimal = p.optimal; self.category = p.category; self.source = p.source
        self.is_time_matrix = p.is_time_matrix; self.time_matrix = p.time_matrix

import optimizer_api.tests.run_interactive_benchmark_v2_numba as bench_v2
from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, LocalSearchType
from optimizer_api.utils import local_search_numba

orig_create = bench_v2.create_np_distance_matrix
orig_calc = bench_v2.calculate_tour_length
orig_build = local_search_numba._build_or_get_dist_matrix

def patched_create(coords):
    import numpy as np
    return np.array(prob.dist_matrix, dtype=np.float64)

def patched_calc(tour, coords):
    if not tour: return 0
    total = 0.0
    for i in range(len(tour)):
        idx1, idx2 = tour[i], tour[(i + 1) % len(tour)]
        if isinstance(idx1, str) and idx1.startswith("L"): idx1 = int(idx1[1:]) - 1
        elif isinstance(idx1, int): idx1 = idx1 - 1
        if isinstance(idx2, str) and idx2.startswith("L"): idx2 = int(idx2[1:]) - 1
        elif isinstance(idx2, int): idx2 = idx2 - 1
        total += prob.dist_matrix[idx1][idx2]
    return int(total)

def patched_build(route, duration_func):
    import numpy as np
    src_map = {loc: i for i, loc in enumerate(duration_func._np_unique_locs)}
    unique_locs = list(dict.fromkeys(route))
    index_map = {loc: i for i, loc in enumerate(unique_locs)}
    n = len(unique_locs)
    prebuilt_dm = duration_func._np_dist_matrix
    dm = np.zeros((n, n), dtype=np.float64)
    for i, loc_i in enumerate(unique_locs):
        src_i = src_map.get(loc_i, i)
        for j, loc_j in enumerate(unique_locs):
            src_j = src_map.get(loc_j, j)
            dm[i, j] = prebuilt_dm[src_i, src_j]
    return (index_map, dm, unique_locs)

bench_v2.create_np_distance_matrix = patched_create
bench_v2.calculate_tour_length = patched_calc
local_search_numba._build_or_get_dist_matrix = patched_build

# Test multiple seeds - does different initial tour help 2-opt?
print('Testing 2-opt with multiple random seeds:')
best_tl, best_gap = float('inf'), 100.0
for seed in [42, 1, 2, 3, 5, 10, 100, 123, 456, 789]:
    mock = MockProblem(prob)
    result = run_single_test(mock, LocalSearchType.TWO_OPT, seed, {'max_iterations': 5000})
    gap = result['gap']
    tl = result['tour_length']
    if gap < best_gap:
        best_gap = gap
        best_tl = tl
    print(f'  seed={seed:3d}: tour_length={tl:.0f}  gap={gap:.4f}%')

print(f'\nBest from 10 seeds: tour_length={best_tl:.0f}  gap={best_gap:.4f}%')
print(f'Optimal: 108159, Best possible gap: {((best_tl-108159)/108159)*100:.4f}%')

bench_v2.create_np_distance_matrix = orig_create
bench_v2.calculate_tour_length = orig_calc
local_search_numba._build_or_get_dist_matrix = orig_build