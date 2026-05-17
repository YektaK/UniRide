import sys, os, math, json, sqlite3
sys.path.insert(0, '.')

from academic_benchmark.tsplib_manager import get_distance_matrix, get_all_problems
import numpy as np

dm = get_distance_matrix('pr76')
print('DB pr76 shape:', dm.shape, 'dtype:', dm.dtype)
print('DB[0,1] =', dm[0,1], '  DB[0,75] =', dm[0,75])

probs = get_all_problems()
p = next(x for x in probs if x['name'] == 'pr76')
coords = p['coordinates']
c0 = coords[0]
c75 = coords[75]
manual = int(round(math.hypot(c0[0]-c75[0], c0[1]-c75[1])))
print('Manual EUC_2D[0,75]:', manual, '  Match:', dm[0,75] == manual)

from academic_benchmark.benchmark_utils import TSPLIB_OPTIMALS
print('Optimal pr76:', TSPLIB_OPTIMALS.get('pr76'))

conn = sqlite3.connect(os.path.join('academic_benchmark', 'tsplib_data', 'tsplib.db'))
row = conn.execute("SELECT tour_nodes FROM opt_tours WHERE problem_name='pr76'").fetchone()
if row:
    tour = json.loads(row[0])
    total = sum(dm[tour[i]-1, tour[(i+1)%len(tour)]-1] for i in range(len(tour)))
    print('Opt tour verified from DB:', int(total))
else:
    print('No opt tour in DB')

conn.close()

# Verify patched_calc logic
def patched_calc(tour, dist_matrix):
    if not tour: return 0
    total = 0.0
    for i in range(len(tour)):
        idx1, idx2 = tour[i], tour[(i+1) % len(tour)]
        idx1 = idx1 - 1
        idx2 = idx2 - 1
        total += dist_matrix[idx1][idx2]
    return int(total)

print('Test random tour cost:', patched_calc([1,5,10,20,30,40,50,60,70,76], dm.tolist()))