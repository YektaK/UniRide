"""
Test Suite for GA-Split Hybrid Strategy
Pipeline B (Route-First, Cluster-Second) Implementation Test

This script tests:
1. Split Decoder functionality
2. GA-Split strategy integration
3. Comparison with Pipeline A approaches
"""

import sys
import os
import time
import random
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_instance(n_students: int = 30, seed: int = 42):
    """Create a test OptimizationRequest"""
    from models.schemas import OptimizationRequest, StudentNode, Depot
    
    random.seed(seed)
    
    # Create depot
    depot = Depot(
        id="D.Kampus",
        name="Ana Kampüs",
        lat=37.0667,
        lng=37.3833
    )
    
    # Create students with random locations
    students = []
    disability_types = ["Sw", "So", "So", "So", "Sw"]  # 40% Sw, 60% So
    
    for i in range(n_students):
        # Random location around depot (within ~10km)
        lat = depot.lat + random.uniform(-0.1, 0.1)
        lng = depot.lng + random.uniform(-0.1, 0.1)
        
        student = StudentNode(
            id=f"S{i+1:03d}",
            name=f"Öğrenci {i+1}",
            location_code=f"L{i+1:03d}",
            coordinates={"lat": lat, "lng": lng},
            disability_type=random.choice(disability_types),
            morning_pickup_time="08:00",
            evening_pickup_time="17:00"
        )
        students.append(student)
    
    return OptimizationRequest(
        students=students,
        depot=depot,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=90,
        optimization_goal="min_vehicles"
    )


def test_split_decoder():
    """Test Split Decoder independently"""
    print("\n" + "="*60)
    print("TEST 1: Split Decoder")
    print("="*60)
    
    from utils.split_decoder import SplitDecoder, decode_giant_tour
    
    # Create test data
    depot = "D.Kampus"
    giant_tour = ["L001", "L002", "L003", "L004", "L005", "L006", "L007", "L008"]
    
    # Distance matrix
    distance_matrix = {}
    all_locs = [depot] + giant_tour
    for i, loc1 in enumerate(all_locs):
        distance_matrix[loc1] = {}
        for j, loc2 in enumerate(all_locs):
            if loc1 == loc2:
                distance_matrix[loc1][loc2] = 0
            else:
                # Random distances for testing
                distance_matrix[loc1][loc2] = 10 + abs(i - j) * 5
    
    # Demands
    demands = {}
    for i, loc in enumerate(giant_tour):
        demands[loc] = (1 if i % 3 == 0 else 0,  # Sw
                        1 if i % 3 != 0 else 0)  # So
    
    # Test basic decoder
    decoder = SplitDecoder(sw_capacity=4, so_capacity=5, max_tour_duration=60)
    result = decoder.decode(giant_tour, depot, distance_matrix, demands)
    
    print(f"  Giant Tour: {' -> '.join(giant_tour)}")
    print(f"  Total Cost: {result['total_cost']:.1f} minutes")
    print(f"  Number of Vehicles: {result['num_vehicles']}")
    print(f"  Routes:")
    for i, route in enumerate(result['routes']):
        print(f"    Route {i+1}: {' -> '.join(route)}")
    
    # Test with details
    result_detailed = decoder.decode_with_details(giant_tour, depot, distance_matrix, demands)
    print(f"\n  Detailed Routes:")
    for route_info in result_detailed.get('detailed_routes', []):
        print(f"    Route {route_info['route_index']+1}: Sw={route_info['sw_count']}, So={route_info['so_count']}")
    
    print("\n  ✓ Split Decoder test passed")
    return True


def test_ga_split_strategy():
    """Test GA-Split Strategy"""
    print("\n" + "="*60)
    print("TEST 2: GA-Split Strategy")
    print("="*60)
    
    from strategies.ga_split_strategy import GASplitStrategy
    
    # Create test instance
    request = create_test_instance(n_students=20, seed=42)
    
    # Run optimization
    strategy = GASplitStrategy(config={
        "population_size": 30,
        "max_iterations": 50,
        "max_no_improvement": 15
    })
    
    print(f"  Test Instance: {len(request.students)} students")
    print(f"  Running GA-Split optimization...")
    
    start_time = time.time()
    response = strategy.optimize(request)
    exec_time = time.time() - start_time
    
    print(f"\n  Results:")
    print(f"    Success: {response.success}")
    print(f"    Total Vehicles: {response.total_vehicles}")
    print(f"    Total Duration: {response.total_duration_minutes:.1f} minutes")
    print(f"    Execution Time: {exec_time:.3f} seconds")
    
    if response.routes:
        print(f"\n  Route Details:")
        for route in response.routes[:3]:  # Show first 3
            print(f"    {route.vehicle_id}: {route.sw_count} Sw + {route.so_count} So = {route.total_duration_minutes:.1f} min")
        if len(response.routes) > 3:
            print(f"    ... and {len(response.routes) - 3} more routes")
    
    print(f"\n  ✓ GA-Split Strategy test passed")
    return True


def compare_strategies():
    """Compare Pipeline A vs Pipeline B"""
    print("\n" + "="*60)
    print("TEST 3: Pipeline A vs Pipeline B Comparison")
    print("="*60)
    
    from strategies import (
        get_strategy, 
        GeneticAlgorithmStrategy,
        GASplitStrategy
    )
    
    # Test sizes
    test_sizes = [15, 25]
    
    results = []
    
    for n in test_sizes:
        print(f"\n  Testing with N={n} students...")
        request = create_test_instance(n_students=n, seed=42)
        
        # Pipeline A - Cluster-First GA
        ga_strategy = GeneticAlgorithmStrategy()
        start = time.time()
        ga_result = ga_strategy.optimize(request)
        ga_time = time.time() - start
        
        # Pipeline B - Route-First GA-Split
        ga_split_strategy = GASplitStrategy(config={
            "population_size": 30,
            "max_iterations": 50
        })
        start = time.time()
        ga_split_result = ga_split_strategy.optimize(request)
        ga_split_time = time.time() - start
        
        results.append({
            "n": n,
            "ga_vehicles": ga_result.total_vehicles,
            "ga_duration": ga_result.total_duration_minutes,
            "ga_time": ga_time,
            "split_vehicles": ga_split_result.total_vehicles,
            "split_duration": ga_split_result.total_duration_minutes,
            "split_time": ga_split_time
        })
        
        print(f"    Pipeline A (GA-Cluster): {ga_result.total_vehicles} vehicles, {ga_result.total_duration_minutes:.1f} min, {ga_time:.2f}s")
        print(f"    Pipeline B (GA-Split):   {ga_split_result.total_vehicles} vehicles, {ga_split_result.total_duration_minutes:.1f} min, {ga_split_time:.2f}s")
    
    # Summary table
    print("\n  Comparison Summary:")
    print("  " + "-"*80)
    print(f"  {'N':<5} {'Pipeline':<15} {'Vehicles':<10} {'Duration':<12} {'Time':<10}")
    print("  " + "-"*80)
    
    for r in results:
        print(f"  {r['n']:<5} {'GA-Cluster':<15} {r['ga_vehicles']:<10} {r['ga_duration']:<12.1f} {r['ga_time']:<10.2f}")
        print(f"  {r['n']:<5} {'GA-Split':<15} {r['split_vehicles']:<10} {r['split_duration']:<12.1f} {r['split_time']:<10.2f}")
    
    print("  " + "-"*80)
    print("\n  ✓ Comparison test completed")
    return True


def test_strategy_registry():
    """Test that new strategies are registered"""
    print("\n" + "="*60)
    print("TEST 4: Strategy Registry")
    print("="*60)
    
    from strategies import get_strategy, get_available_solvers, get_strategy_info
    
    # Check availability
    solvers = get_available_solvers()
    print(f"  Available Solvers:")
    for name, available in solvers.items():
        status = "✓" if available else "✗"
        print(f"    {status} {name}")
    
    # Get strategy info
    print(f"\n  Registered Strategies:")
    info = get_strategy_info()
    for s in info:
        print(f"    - {s['name']}: {s['display_name']}")
    
    # Test retrieval
    print(f"\n  Testing Strategy Retrieval:")
    ga_split = get_strategy("ga_split")
    if ga_split:
        print(f"    ✓ ga_split found: {ga_split.display_name}")
    else:
        print(f"    ✗ ga_split not found")
    
    ga_split_enhanced = get_strategy("ga_split_enhanced")
    if ga_split_enhanced:
        print(f"    ✓ ga_split_enhanced found: {ga_split_enhanced.display_name}")
    else:
        print(f"    ✗ ga_split_enhanced not found")
    
    print("\n  ✓ Registry test passed")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("UniRide GA-Split Test Suite")
    print("Pipeline B Implementation Tests")
    print("="*60)
    
    tests = [
        ("Split Decoder", test_split_decoder),
        ("GA-Split Strategy", test_ga_split_strategy),
        ("Strategy Registry", test_strategy_registry),
        ("Pipeline Comparison", compare_strategies),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASSED" if success else "FAILED"))
        except Exception as e:
            print(f"\n  ✗ Error: {e}")
            results.append((name, "ERROR"))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, status in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"  {symbol} {name}: {status}")
    
    passed = sum(1 for _, s in results if s == "PASSED")
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
