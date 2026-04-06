#!/usr/bin/env python3
"""
UniRide Test Suite - Comprehensive Test Runner
===============================================

Bu script tüm testleri çalıştırır ve karşılaştırma sonuçları üretir.

Kullanım:
    python run_all_tests.py              # Tüm testleri çalıştır
    python run_all_tests.py --quick      # Hızlı test (sadece unit)
    python run_all_tests.py --compare    # Algoritma karşılaştırması
    python run_all_tests.py --exact      # Exact çözüm ile karşılaştırma

Gereksinimler:
    pip install pytest pandas openpyxl

Dış Solver Kurulumu (Opsiyonel):
    pip install ortools pyvrp
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_unit_tests():
    """Run all unit tests with pytest"""
    import subprocess
    
    print("\n" + "=" * 70)
    print("UNIT TESTS")
    print("=" * 70)
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         "test_strategies.py", 
         "test_gwo.py", 
         "test_hho.py", 
         "test_comparison.py",
         "test_split_strategies.py",
         "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print("ERRORS:")
        print(result.stderr)
    
    return result.returncode == 0


def run_algorithm_comparison():
    """Run algorithm comparison with real distance matrix"""
    print("\n" + "=" * 70)
    print("ALGORITHM COMPARISON (Real Distance Matrix)")
    print("=" * 70)
    
    try:
        import pandas as pd
        from itertools import permutations
        import math
        
        from models.schemas import OptimizationRequest, StudentNode, LocationNode
        from strategies.greedy_heuristic import GreedyHeuristicStrategy
        from strategies.ga_split_strategy import GASplitStrategy, GAEnhancedSplitStrategy
        from strategies.gwo_split_strategy import GWOSplitStrategy
        from strategies.hho_split_strategy import HHOSplitStrategy
        from strategies.pso_split_strategy import PSOSplitStrategy
        
        # Load distance matrix
        data_path = Path(__file__).parent.parent.parent / "Veri.xlsx"
        if not data_path.exists():
            # Try alternative paths
            alt_paths = [
                Path("/home/z/my-project/upload/uniride-current/Veri.xlsx"),
                Path("Veri.xlsx"),
            ]
            for p in alt_paths:
                if p.exists():
                    data_path = p
                    break
        
        if not data_path.exists():
            print(f"ERROR: Veri.xlsx not found!")
            print(f"Please copy Veri.xlsx to: {Path(__file__).parent}")
            return False
        
        xlsx = pd.ExcelFile(data_path)
        time_df = pd.read_excel(xlsx, sheet_name='Time')
        
        locations = time_df['Konumlar'].tolist()
        distance_matrix = {}
        for i, loc in enumerate(locations):
            distance_matrix[loc] = {}
            for j, loc2 in enumerate(locations):
                distance_matrix[loc][loc2] = int(time_df.iloc[i, j+1])
        
        print(f"Distance Matrix: {len(locations)} locations loaded")
        
        # Test configurations
        test_configs = [
            {"name": "Small (9 students)", "sw": ["Sw1","Sw2","Sw3","Sw4"], "so": ["So1","So2","So3","So4","So5"]},
            {"name": "Full (28 students)", "sw": [f"Sw{i}" for i in range(1,10)], "so": [f"So{i}" for i in range(1,20)]},
        ]
        
        strategies = [
            ("Greedy", GreedyHeuristicStrategy()),
            ("GA-Split", GASplitStrategy()),
            ("GA-Enhanced", GAEnhancedSplitStrategy()),
            ("GWO-Split", GWOSplitStrategy()),
            ("HHO-Split", HHOSplitStrategy()),
            ("PSO-Split", PSOSplitStrategy()),
        ]
        
        for config in test_configs:
            print(f"\n--- {config['name']} ---")
            
            students = [StudentNode(id=s, name=s, location_code=s, coordinates={"lat":0,"lng":0}, disability_type="Sw") for s in config["sw"]]
            students += [StudentNode(id=s, name=s, location_code=s, coordinates={"lat":0,"lng":0}, disability_type="So") for s in config["so"]]
            
            depot = LocationNode(id="D.Kampus", lat=0, lng=0, type="Depot")
            
            print(f"{'Algorithm':<25} {'Vehicles':<10} {'Duration':<12} {'Time (s)':<10}")
            print("-" * 60)
            
            results = []
            for name, strategy in strategies:
                try:
                    request = OptimizationRequest(
                        algorithm=strategy.name, students=students, depot=depot,
                        max_travel_time=120, sw_capacity=4, so_capacity=5
                    )
                    
                    start = time.time()
                    result = strategy.optimize(request)
                    elapsed = time.time() - start
                    
                    # Calculate real duration
                    total = 0
                    for route in result.routes:
                        prev = "D.Kampus"
                        for step in route.route_details:
                            nxt = step.location2
                            if prev in distance_matrix and nxt in distance_matrix.get(prev, {}):
                                total += distance_matrix[prev][nxt]
                            prev = nxt
                    
                    print(f"{strategy.display_name:<25} {result.total_vehicles:<10} {total:<12} {elapsed:<10.4f}")
                    results.append({"name": name, "veh": result.total_vehicles, "dur": total, "time": elapsed})
                except Exception as e:
                    print(f"{name:<25} ERROR: {str(e)[:40]}")
            
            if results:
                best = min(results, key=lambda x: x["dur"])
                print(f"\nBest: {best['name']} ({best['dur']} dk, {best['veh']} vehicles)")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_exact_comparison():
    """Run exact solution comparison for small instances"""
    print("\n" + "=" * 70)
    print("EXACT vs HEURISTIC COMPARISON")
    print("=" * 70)
    
    try:
        import pandas as pd
        from itertools import permutations
        import math
        
        from models.schemas import OptimizationRequest, StudentNode, LocationNode
        from strategies.greedy_heuristic import GreedyHeuristicStrategy
        from strategies.ga_split_strategy import GASplitStrategy
        from strategies.gwo_split_strategy import GWOSplitStrategy
        
        # Load distance matrix
        data_path = Path(__file__).parent.parent.parent / "Veri.xlsx"
        if not data_path.exists():
            alt_paths = [Path("/home/z/my-project/upload/uniride-current/Veri.xlsx"), Path("Veri.xlsx")]
            for p in alt_paths:
                if p.exists():
                    data_path = p
                    break
        
        if not data_path.exists():
            print(f"ERROR: Veri.xlsx not found!")
            return False
        
        xlsx = pd.ExcelFile(data_path)
        time_df = pd.read_excel(xlsx, sheet_name='Time')
        locations = time_df['Konumlar'].tolist()
        distance_matrix = {}
        for i, loc in enumerate(locations):
            distance_matrix[loc] = {}
            for j, loc2 in enumerate(locations):
                distance_matrix[loc][loc2] = int(time_df.iloc[i, j+1])
        
        # Small instance for exact solution
        sw_students = ["Sw1", "Sw2", "Sw3", "Sw4"]
        so_students = ["So1", "So2", "So3", "So4", "So5"]
        all_students = sw_students + so_students
        
        print(f"Test: {len(all_students)} students")
        print(f"Evaluating {math.factorial(len(all_students)):,} permutations for EXACT solution...")
        
        # Exact solution (brute force)
        start = time.time()
        best_tour, best_dur = None, float('inf')
        sw_set, so_set = set(sw_students), set(so_students)
        
        for perm in permutations(all_students):
            sw_c = sum(1 for s in perm if s in sw_set)
            so_c = sum(1 for s in perm if s in so_set)
            if sw_c <= 4 and so_c <= 5:
                d = distance_matrix['D.Kampus'][perm[0]]
                for i in range(len(perm)-1):
                    d += distance_matrix[perm[i]][perm[i+1]]
                d += distance_matrix[perm[-1]]['D.Kampus']
                if d < best_dur:
                    best_dur = d
                    best_tour = list(perm)
        
        exact_time = time.time() - start
        
        print(f"\nEXACT OPTIMAL: {best_dur} dk")
        print(f"Tour: {' -> '.join(best_tour)}")
        print(f"Time: {exact_time:.4f}s")
        
        # Heuristic comparison
        print("\n--- Heuristic Comparison ---")
        
        students = [StudentNode(id=s, name=s, location_code=s, coordinates={"lat":0,"lng":0}, disability_type="Sw") for s in sw_students]
        students += [StudentNode(id=s, name=s, location_code=s, coordinates={"lat":0,"lng":0}, disability_type="So") for s in so_students]
        depot = LocationNode(id="D.Kampus", lat=0, lng=0, type="Depot")
        
        heuristics = [
            ("Greedy", GreedyHeuristicStrategy()),
            ("GA-Split", GASplitStrategy()),
            ("GWO-Split", GWOSplitStrategy()),
        ]
        
        print(f"{'Algorithm':<25} {'Duration':<12} {'Gap %':<10} {'Time (s)':<10}")
        print("-" * 60)
        
        for name, strategy in heuristics:
            request = OptimizationRequest(algorithm=strategy.name, students=students, depot=depot,
                                         max_travel_time=120, sw_capacity=4, so_capacity=5)
            t0 = time.time()
            result = strategy.optimize(request)
            elapsed = time.time() - t0
            
            total = 0
            for route in result.routes:
                prev = "D.Kampus"
                for step in route.route_details:
                    nxt = step.location2
                    if prev in distance_matrix and nxt in distance_matrix.get(prev, {}):
                        total += distance_matrix[prev][nxt]
                    prev = nxt
            
            gap = (total - best_dur) / best_dur * 100
            print(f"{strategy.display_name:<25} {total:<12} {gap:<10.1f} {elapsed:<10.4f}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="UniRide Test Suite")
    parser.add_argument("--quick", action="store_true", help="Quick test (unit tests only)")
    parser.add_argument("--compare", action="store_true", help="Algorithm comparison")
    parser.add_argument("--exact", action="store_true", help="Exact vs heuristic comparison")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("UniRide CVRPTW - Test Suite")
    print("=" * 70)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}")
    
    success = True
    
    if args.all or (not args.quick and not args.compare and not args.exact):
        # Default: run all
        success = run_unit_tests() and success
        success = run_algorithm_comparison() and success
    elif args.quick:
        success = run_unit_tests()
    elif args.compare:
        success = run_algorithm_comparison()
    elif args.exact:
        success = run_exact_comparison()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
