import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import GAOptimizer, PSOOptimizer
from benchmarks.tsplib_benchmark import parse_tsplib, TSPLIB_OPTIMALS

prob = parse_tsplib(os.path.join('..', '..', 'optimizer_api', 'tests', 'tsplib_data', 'eil51.tsp'))
coords = prob['coordinates']
opt = TSPLIB_OPTIMALS['eil51']

print('=== GA (Memetic) Test ===')
for seed in [1, 2, 3]:
    ga = GAOptimizer(population_size=60, generations=150, crossover_rate=0.85, mutation_rate=0.15, random_seed=seed)
    res = ga.solve(coords)
    gap = ((res.tour_length - opt) / opt) * 100
    print(f'  Seed {seed}: Length={res.tour_length:.1f}  Gap={gap:.1f}%  Time={res.elapsed_ms:.0f}ms')

print()
print('=== PSO (Memetic) Test ===')
for seed in [1, 2, 3]:
    pso = PSOOptimizer(swarm_size=30, max_iterations=150, random_seed=seed)
    res = pso.solve(coords)
    gap = ((res.tour_length - opt) / opt) * 100
    print(f'  Seed {seed}: Length={res.tour_length:.1f}  Gap={gap:.1f}%  Time={res.elapsed_ms:.0f}ms')
