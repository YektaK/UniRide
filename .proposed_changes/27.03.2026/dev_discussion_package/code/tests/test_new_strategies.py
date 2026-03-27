"""
Test Script for VROOM and PyVRP Strategies
Run this to verify the new strategies are working correctly.

Usage:
    cd dev_discussion_package/code
    python -m tests.test_new_strategies
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import OptimizationRequest, StudentNode, LocationNode
from strategies import (
    get_strategy,
    get_available_solvers,
    get_recommended_strategy,
    STRATEGY_REGISTRY
)


def create_test_request():
    """Create a test request with sample students"""
    
    students = [
        StudentNode(
            id="s1",
            name="Ali Yılmaz",
            location_code="Sw1",
            coordinates={"lat": 40.850, "lng": 31.160},
            disability_type="Sw"
        ),
        StudentNode(
            id="s2",
            name="Ayşe Demir",
            location_code="Sw2",
            coordinates={"lat": 40.840, "lng": 31.150},
            disability_type="Sw"
        ),
        StudentNode(
            id="s3",
            name="Mehmet Kaya",
            location_code="So1",
            coordinates={"lat": 40.830, "lng": 31.140},
            disability_type="So"
        ),
        StudentNode(
            id="s4",
            name="Fatma Öz",
            location_code="So2",
            coordinates={"lat": 40.820, "lng": 31.130},
            disability_type="So"
        ),
        StudentNode(
            id="s5",
            name="Ahmet Can",
            location_code="Sw3",
            coordinates={"lat": 40.860, "lng": 31.170},
            disability_type="Sw"
        ),
        StudentNode(
            id="s6",
            name="Zeynep Ak",
            location_code="So3",
            coordinates={"lat": 40.810, "lng": 31.120},
            disability_type="So"
        ),
    ]
    
    depot = LocationNode(
        id="D.Kampus",
        lat=40.841,
        lng=31.148,
        type="depot"
    )
    
    return OptimizationRequest(
        algorithm="pyvrp",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5
    )


def test_registry():
    """Test strategy registry"""
    print("\n" + "=" * 60)
    print("STRATEGY REGISTRY TEST")
    print("=" * 60)
    
    print("\nAvailable Solvers:")
    solvers = get_available_solvers()
    for solver, available in solvers.items():
        status = "✅" if available else "❌"
        print(f"  {status} {solver}")
    
    print("\nRegistered Strategies:")
    for name in sorted(STRATEGY_REGISTRY.keys()):
        strategy = STRATEGY_REGISTRY[name]
        if strategy:
            print(f"  - {name}: {strategy.display_name}")
    
    print("\nRecommendation Tests:")
    for n in [10, 30, 100, 300]:
        for priority in ["speed", "quality", "balanced"]:
            rec = get_recommended_strategy(n, priority)
            print(f"  N={n:3d}, priority={priority:8s} → {rec}")


def test_vroom():
    """Test VROOM strategy"""
    print("\n" + "=" * 60)
    print("VROOM STRATEGY TEST")
    print("=" * 60)
    
    strategy = get_strategy("vroom")
    if strategy is None:
        print("❌ VROOM strategy not available")
        print("   Install with: pip install pyvroom")
        return
    
    request = create_test_request()
    request.algorithm = "vroom"
    
    print(f"\nTesting with {len(request.students)} students...")
    result = strategy.optimize(request)
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Algorithm: {result.algorithm_used}")
    print(f"  Total Vehicles: {result.total_vehicles}")
    print(f"  Total Duration: {result.total_duration_minutes:.2f} minutes")
    print(f"  Execution Time: {result.execution_time_seconds:.4f} seconds")
    
    if result.error_message:
        print(f"  Error: {result.error_message}")
    
    if result.routes:
        print(f"\nRoutes:")
        for route in result.routes:
            print(f"  - {route.vehicle_id}: Sw={route.sw_count}, So={route.so_count}")
            print(f"    Duration: {route.total_duration_minutes:.2f} min")
            print(f"    Students: {route.student_ids}")


def test_pyvrp():
    """Test PyVRP strategy"""
    print("\n" + "=" * 60)
    print("PYVRP STRATEGY TEST")
    print("=" * 60)
    
    strategy = get_strategy("pyvrp")
    if strategy is None:
        print("❌ PyVRP strategy not available")
        print("   Install with: pip install pyvrp")
        return
    
    request = create_test_request()
    request.algorithm = "pyvrp"
    
    print(f"\nTesting with {len(request.students)} students...")
    result = strategy.optimize(request)
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Algorithm: {result.algorithm_used}")
    print(f"  Total Vehicles: {result.total_vehicles}")
    print(f"  Total Duration: {result.total_duration_minutes:.2f} minutes")
    print(f"  Execution Time: {result.execution_time_seconds:.4f} seconds")
    
    if result.error_message:
        print(f"  Error: {result.error_message}")
    
    if result.routes:
        print(f"\nRoutes:")
        for route in result.routes:
            print(f"  - {route.vehicle_id}: Sw={route.sw_count}, So={route.so_count}")
            print(f"    Duration: {route.total_duration_minutes:.2f} min")
            print(f"    Students: {route.student_ids}")


def test_ortools_baseline():
    """Test OR-Tools as baseline"""
    print("\n" + "=" * 60)
    print("OR-TOOLS BASELINE TEST")
    print("=" * 60)
    
    strategy = get_strategy("ortools_cvrp")
    if strategy is None:
        print("❌ OR-Tools strategy not available")
        return
    
    request = create_test_request()
    request.algorithm = "ortools_cvrp"
    
    print(f"\nTesting with {len(request.students)} students...")
    result = strategy.optimize(request)
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Algorithm: {result.algorithm_used}")
    print(f"  Total Vehicles: {result.total_vehicles}")
    print(f"  Total Duration: {result.total_duration_minutes:.2f} minutes")
    print(f"  Execution Time: {result.execution_time_seconds:.4f} seconds")
    
    if result.error_message:
        print(f"  Error: {result.error_message}")
    
    if result.routes:
        print(f"\nRoutes:")
        for route in result.routes:
            print(f"  - {route.vehicle_id}: Sw={route.sw_count}, So={route.so_count}")


def compare_all():
    """Compare all available strategies"""
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)
    
    request = create_test_request()
    
    strategies_to_test = [
        "ortools_cvrp",
        "vroom",
        "vroom_fallback",
        "pyvrp",
        "pyvrp_alt",
    ]
    
    results = []
    
    for name in strategies_to_test:
        strategy = get_strategy(name)
        if strategy is None:
            print(f"\n❌ {name}: Not available")
            continue
        
        print(f"\n⏳ Testing {name}...")
        
        try:
            request.algorithm = name
            result = strategy.optimize(request)
            
            results.append({
                "name": name,
                "success": result.success,
                "vehicles": result.total_vehicles,
                "duration": result.total_duration_minutes,
                "time": result.execution_time_seconds,
                "error": result.error_message
            })
            
            if result.success:
                print(f"   ✅ Vehicles: {result.total_vehicles}, Duration: {result.total_duration_minutes:.2f} min, Time: {result.execution_time_seconds:.4f}s")
            else:
                print(f"   ❌ Error: {result.error_message}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })
    
    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(f"\n{'Strategy':<20} {'Success':<8} {'Vehicles':<10} {'Duration':<12} {'Exec Time':<12}")
    print("-" * 62)
    
    for r in results:
        if r["success"]:
            print(f"{r['name']:<20} {'✅':<8} {r['vehicles']:<10} {r['duration']:<12.2f} {r['time']:<12.4f}")
        else:
            print(f"{r['name']:<20} {'❌':<8} {'-':<10} {'-':<12} {'-':<12}")
    
    # Best performer
    successful = [r for r in results if r["success"]]
    if successful:
        best_duration = min(successful, key=lambda x: x["duration"])
        fastest = min(successful, key=lambda x: x["time"])
        print(f"\n🏆 Best Duration: {best_duration['name']} ({best_duration['duration']:.2f} min)")
        print(f"⚡ Fastest: {fastest['name']} ({fastest['time']:.4f} s)")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("UniRide VROOM & PyVRP Strategy Tests")
    print("=" * 60)
    
    # Run all tests
    test_registry()
    test_ortools_baseline()
    test_vroom()
    test_pyvrp()
    compare_all()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
