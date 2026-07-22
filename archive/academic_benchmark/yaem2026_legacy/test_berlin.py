import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.gwo_solver import GWOOptimizer, PureGWOOptimizer
from core.hho_solver import HHOOptimizer, PureHHOOptimizer

def load_berlin52():
    # Known optimal for berlin52 is 7542
    import tsplib95
    problem = tsplib95.load('c:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/data/tsplib/berlin52.tsp')
    coords = [(problem.node_coords[k][0], problem.node_coords[k][1]) for k in problem.get_nodes()]
    return coords

def main():
    coords = load_berlin52()
    
    solvers = [
        PureGWOOptimizer(pack_size=50, max_iterations=250),
        GWOOptimizer(pack_size=50, max_iterations=250),
        PureHHOOptimizer(hawks=50, max_iterations=250),
        HHOOptimizer(hawks=50, max_iterations=250)
    ]
    
    for solver in solvers:
        res = solver.solve(coords)
        gap = (res.tour_length - 7542) / 7542 * 100
        print(f"{solver.name}: {res.tour_length} (Gap: {gap:.2f}%)")

if __name__ == '__main__':
    main()
