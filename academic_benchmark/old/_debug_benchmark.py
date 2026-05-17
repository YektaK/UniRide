"""Debug: compare monkey-patched vs clean dist_matrix results."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, STRATEGIES, create_np_distance_matrix
from academic_benchmark.tsplib_manager import get_distance_matrix, get_all_problems

# Load eil51 from DB
dm = get_distance_matrix("eil51")
probs = get_all_problems(max_dim=99999)
coords = None; opt = None
for p in probs:
    if p["name"] == "eil51":
        coords = p["coordinates"]
        opt = p["optimal"]
        break

print(f"eil51: dim={len(coords)}, opt={opt}")
print(f"DB matrix shape: {len(dm)}x{len(dm[0])}")

class MockProblem:
    def __init__(self):
        self.name = "eil51"
        self.dimension = len(coords)
        self.coordinates = coords
        self.optimal = opt
        self.category = "small"
        self.source = "tsplib"
        self.is_time_matrix = False
        self.time_matrix = None
        self.dist_matrix = dm

p = MockProblem()
dm_np = np.array(dm, dtype=np.float64)

# Test each strategy
for idx, (name, payload, params) in enumerate(STRATEGIES):
    # 1. With precomputed matrix (clean path)
    res1 = run_single_test(p, payload, 42, params, dist_matrix=dm_np)
    
    # 2. Without matrix (coordinates-based, backward compat)
    res2 = run_single_test(p, payload, 42, params)
    
    match = "MATCH" if abs(res1["tour_length"] - res2["tour_length"]) <= 1 else "DIFF"
    print(f"{name:12s} | matrix={res1['tour_length']:>5d} gap={res1['gap']:>6.2f}% | coords={res2['tour_length']:>5d} gap={res2['gap']:>6.2f}% | {match}")
