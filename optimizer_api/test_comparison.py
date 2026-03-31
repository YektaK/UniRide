"""
Compare GWO with other algorithms
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from models.schemas import OptimizationRequest, StudentNode, LocationNode
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.pso_strategy import PSOStrategy
from strategies.gwo_strategy import GreyWolfOptimizerStrategy as GWOStrategy
from strategies.hho_strategy import HarrisHawksOptimizerStrategy as HHOStrategy
from strategies.greedy_heuristic import GreedyHeuristicStrategy


def create_test_data(num_students: int = 10):
    """Create test data with students around a depot"""
    depot = LocationNode(
        id="D.Kampus",
        lat=37.0667,
        lng=37.3833,
        type="Depot"
    )
    
    students = []
    for i in range(num_students):
        # Create students in a circular pattern around depot
        angle = (2 * 3.14159 * i) / num_students
        radius = 0.05 + (i % 3) * 0.02  # Varying distances
        
        lat = 37.0667 + radius * (i % 2 == 0 and 1 or -1) * 0.5
        lng = 37.3833 + radius * (i % 2 == 0 and -1 or 1) * 0.5
        
        students.append(StudentNode(
            id=f"S{i+1}",
            name=f"Öğrenci {i+1}",
            location_code=f"L{i+1}",
            coordinates={"lat": 37.0667 + (i + 1) * 0.01, 
                        "lng": 37.3833 + (i + 1) * 0.01},
            disability_type="Sw" if i % 3 == 0 else "So"
        ))
    
    return depot, students


def test_algorithm_comparison():
    """Compare all algorithms"""
    print("=" * 70)
    print("ALGORITHM COMPARISON TEST")
    print("=" * 70)
    
    depot, students = create_test_data(num_students=12)
    
    print(f"\nTest Configuration:")
    print(f"  - Depot: {depot.id}")
    print(f"  - Students: {len(students)}")
    print(f"  - SW Capacity: 4")
    print(f"  - SO Capacity: 5")
    print()
    
    # Algorithms to test
    algorithms = [
        ("GA", GeneticAlgorithmStrategy(), {"ga_config": {"population_size": 30, "max_generations": 50}}),
        ("PSO", PSOStrategy(), {"pso_config": {"swarm_size": 30, "max_iterations": 50}}),
        ("GWO", GWOStrategy(), {"gwo_config": {"population_size": 30, "max_iterations": 50}}),
        ("HHO", HHOStrategy(), {"hho_config": {"population_size": 30, "max_iterations": 50}}),
        ("Greedy", GreedyHeuristicStrategy(), {}),
    ]
    
    results = []
    
    for name, strategy, config in algorithms:
        print(f"\nRunning {name} ({strategy.display_name})...")
        
        request = OptimizationRequest(
            algorithm=strategy.name,
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5,
            **config
        )
        
        start = time.time()
        result = strategy.optimize(request)
        elapsed = time.time() - start
        
        results.append({
            "name": name,
            "display_name": strategy.display_name,
            "success": result.success,
            "vehicles": result.total_vehicles,
            "duration": result.total_duration_minutes,
            "exec_time": result.execution_time_seconds
        })
        
        print(f"  ✓ Completed in {result.execution_time_seconds:.4f}s")
    
    # Print comparison table
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)
    
    print(f"\n{'Algorithm':<30} {'Vehicles':>10} {'Duration':>15} {'Time (s)':>12}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['display_name']:<30} {r['vehicles']:>10} {r['duration']:>15.2f} {r['exec_time']:>12.4f}")
    
    # Find best
    best_duration = min(results, key=lambda x: x['duration'])
    fastest = min(results, key=lambda x: x['exec_time'])
    
    print("\n" + "-" * 70)
    print(f"🏆 Best Duration: {best_duration['display_name']} ({best_duration['duration']:.2f} min)")
    print(f"⚡ Fastest: {fastest['display_name']} ({fastest['exec_time']:.4f} s)")


if __name__ == "__main__":
    test_algorithm_comparison()
