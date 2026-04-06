"""
Test Suite for Pipeline B Metaheuristic Split Strategies
PSO-Split, HHO-Split, GWO-Split

Compares all Pipeline B strategies against Pipeline A.
"""

import sys
import os
import time
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_request(n_students: int = 25, seed: int = 42):
    """Create test OptimizationRequest"""
    from models.schemas import OptimizationRequest, StudentNode, Depot
    
    random.seed(seed)
    depot = Depot(id="D.Kampus", name="Ana Kampüs", lat=37.0667, lng=37.3833)
    
    students = []
    disability_types = ["Sw", "So", "So", "So", "Sw"]
    
    for i in range(n_students):
        lat = depot.lat + random.uniform(-0.08, 0.08)
        lng = depot.lng + random.uniform(-0.08, 0.08)
        students.append(StudentNode(
            id=f"S{i+1:03d}",
            name=f"Öğrenci {i+1}",
            location_code=f"L{i+1:03d}",
            coordinates={"lat": lat, "lng": lng},
            disability_type=random.choice(disability_types),
            morning_pickup_time="08:00",
            evening_pickup_time="17:00"
        ))
    
    return OptimizationRequest(
        students=students,
        depot=depot,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=90
    )


def test_registry():
    """Test that all strategies are registered"""
    print("\n" + "="*60)
    print("TEST 1: Strategy Registry")
    print("="*60)
    
    from strategies import get_strategy, get_available_solvers, get_strategy_info
    
    # Check availability
    solvers = get_available_solvers()
    print(f"\n  Available Solvers:")
    for name, available in sorted(solvers.items()):
        status = "✓" if available else "✗"
        print(f"    {status} {name}")
    
    # Check Pipeline B strategies
    pipeline_b = ["ga_split", "pso_split", "hho_split", "gwo_split"]
    print(f"\n  Pipeline B Strategies:")
    for name in pipeline_b:
        strategy = get_strategy(name)
        if strategy:
            print(f"    ✓ {name}: {strategy.display_name}")
        else:
            print(f"    ✗ {name}: NOT FOUND")
    
    print("\n  ✓ Registry test passed")
    return True


def test_split_strategies():
    """Test all split strategies"""
    print("\n" + "="*60)
    print("TEST 2: Split Strategy Execution")
    print("="*60)
    
    from strategies import get_strategy
    
    request = create_test_request(n_students=20, seed=42)
    print(f"  Test Instance: {len(request.students)} students")
    
    strategies = ["ga_split", "pso_split", "hho_split", "gwo_split"]
    results = {}
    
    for name in strategies:
        strategy = get_strategy(name)
        if not strategy:
            print(f"\n  {name}: NOT AVAILABLE")
            continue
        
        print(f"\n  Testing {name}...")
        
        try:
            start = time.time()
            response = strategy.optimize(request)
            elapsed = time.time() - start
            
            results[name] = {
                "vehicles": response.total_vehicles,
                "duration": response.total_duration_minutes,
                "time": elapsed,
                "success": response.success
            }
            
            print(f"    Vehicles: {response.total_vehicles}")
            print(f"    Duration: {response.total_duration_minutes:.1f} min")
            print(f"    Time: {elapsed:.2f} s")
            
        except Exception as e:
            print(f"    ERROR: {e}")
            results[name] = {"error": str(e)}
    
    # Summary
    print("\n  " + "-"*50)
    print(f"  {'Strategy':<15} {'Vehicles':<10} {'Duration':<12} {'Time':<10}")
    print("  " + "-"*50)
    for name, res in results.items():
        if "error" not in res:
            print(f"  {name:<15} {res['vehicles']:<10} {res['duration']:<12.1f} {res['time']:<10.2f}")
    
    print("\n  ✓ Split strategies test completed")
    return True


def compare_pipeline_a_vs_b():
    """Compare Pipeline A vs Pipeline B"""
    print("\n" + "="*60)
    print("TEST 3: Pipeline A vs Pipeline B Comparison")
    print("="*60)
    
    from strategies import get_strategy
    
    test_sizes = [15, 25]
    
    for n in test_sizes:
        print(f"\n  Testing with N={n} students...")
        request = create_test_request(n_students=n, seed=42)
        
        results = []
        
        # Pipeline A
        for name in ["pso", "hho", "gwo"]:
            strategy = get_strategy(name)
            if strategy:
                start = time.time()
                resp = strategy.optimize(request)
                elapsed = time.time() - start
                results.append(("A", name, resp.total_vehicles, resp.total_duration_minutes, elapsed))
        
        # Pipeline B
        for name in ["pso_split", "hho_split", "gwo_split"]:
            strategy = get_strategy(name)
            if strategy:
                start = time.time()
                resp = strategy.optimize(request)
                elapsed = time.time() - start
                results.append(("B", name, resp.total_vehicles, resp.total_duration_minutes, elapsed))
        
        # Print comparison
        print(f"\n  N={n} Results:")
        print("  " + "-"*70)
        print(f"  {'Pipeline':<8} {'Strategy':<15} {'Vehicles':<10} {'Duration':<12} {'Time':<10}")
        print("  " + "-"*70)
        
        for pipeline, name, vehicles, duration, elapsed in results:
            print(f"  {pipeline:<8} {name:<15} {vehicles:<10} {duration:<12.1f} {elapsed:<10.2f}")
        
        # Calculate averages
        pipeline_a = [r for r in results if r[0] == "A"]
        pipeline_b = [r for r in results if r[0] == "B"]
        
        if pipeline_a and pipeline_b:
            avg_a_vehicles = sum(r[2] for r in pipeline_a) / len(pipeline_a)
            avg_b_vehicles = sum(r[2] for r in pipeline_b) / len(pipeline_b)
            avg_a_duration = sum(r[3] for r in pipeline_a) / len(pipeline_a)
            avg_b_duration = sum(r[3] for r in pipeline_b) / len(pipeline_b)
            
            print(f"\n  Pipeline A Avg: {avg_a_vehicles:.1f} vehicles, {avg_a_duration:.1f} min")
            print(f"  Pipeline B Avg: {avg_b_vehicles:.1f} vehicles, {avg_b_duration:.1f} min")
            
            if avg_b_vehicles < avg_a_vehicles:
                improvement = (avg_a_vehicles - avg_b_vehicles) / avg_a_vehicles * 100
                print(f"  Pipeline B uses {improvement:.1f}% fewer vehicles ✓")
    
    print("\n  ✓ Comparison test completed")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Pipeline B Metaheuristic Split Strategies Test Suite")
    print("="*60)
    
    tests = [
        ("Registry", test_registry),
        ("Split Strategies", test_split_strategies),
        ("Pipeline Comparison", compare_pipeline_a_vs_b),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASSED" if success else "FAILED"))
        except Exception as e:
            print(f"\n  ✗ Error in {name}: {e}")
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
