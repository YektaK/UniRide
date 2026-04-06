"""
Test script for Local Search Module

Tests:
1. Two-opt basic functionality
2. Integration with strategies (GWO, HHO, GA, PSO)
3. Performance comparison
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.local_search import (
    TwoOpt, ThreeOpt, OrOpt, HybridLocalSearch,
    apply_local_search, LocalSearchType, create_cost_function
)


def test_two_opt_basic():
    """Test basic 2-opt functionality"""
    print("=" * 60)
    print("Test 1: Basic 2-opt Functionality")
    print("=" * 60)
    
    # Create a simple route with known optimal solution
    # Points: A -> B -> C -> D (optimal is A -> B -> C -> D if distances are symmetric)
    route = ["A", "C", "B", "D"]
    
    # Create cost matrix (symmetric)
    time_matrix = {
        "DEPOT": {"A": 5, "C": 15, "B": 25, "D": 35},
        "A": {"DEPOT": 5, "C": 10, "B": 20, "D": 30},
        "C": {"DEPOT": 15, "A": 10, "B": 10, "D": 20},
        "B": {"DEPOT": 25, "A": 20, "C": 10, "D": 10},
        "D": {"DEPOT": 35, "A": 30, "C": 20, "B": 10}
    }
    
    coordinates = {
        "DEPOT": {"lat": 0, "lng": 0},
        "A": {"lat": 1, "lng": 0},
        "C": {"lat": 2, "lng": 1},
        "B": {"lat": 2, "lng": 0},
        "D": {"lat": 3, "lng": 0}
    }
    
    # Create cost function
    cost_function = create_cost_function("DEPOT", time_matrix, coordinates)
    
    # Test original route cost
    original_cost = cost_function(route)
    print(f"Original route: {route}")
    print(f"Original cost: {original_cost}")
    
    # Apply 2-opt
    improved_route, improved_cost = TwoOpt.improve(
        route, cost_function, max_iterations=20
    )
    
    print(f"Improved route: {improved_route}")
    print(f"Improved cost: {improved_cost}")
    print(f"Improvement: {original_cost - improved_cost} ({((original_cost - improved_cost) / original_cost * 100):.1f}%)")
    
    assert improved_cost <= original_cost, "2-opt should not worsen the solution"
    print("\n✓ Test 1 PASSED\n")


def test_two_opt_swap():
    """Test 2-opt swap operation"""
    print("=" * 60)
    print("Test 2: 2-opt Swap Operation")
    print("=" * 60)
    
    route = ["A", "B", "C", "D", "E", "F"]
    
    # 2-opt swap: reverse segment between indices i and j
    # For i=1, j=4: reverse segment [i+1:j+1] = [B, C, D, E] indices 1-4
    # Actually: route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
    # = route[:2] + route[2:5][::-1] + route[5:]
    # = ['A', 'B'] + ['E', 'D', 'C'] + ['F']
    new_route = TwoOpt._two_opt_swap(route, 1, 4)
    
    print(f"Original: {route}")
    print(f"After swap(1, 4): {new_route}")
    
    # Corrected expected: reverse indices 2-4 (C, D, E -> E, D, C)
    expected = ["A", "B", "E", "D", "C", "F"]
    assert new_route == expected, f"Expected {expected}, got {new_route}"
    print(f"Expected: {expected}")
    print("\n✓ Test 2 PASSED\n")


def test_local_search_types():
    """Test different local search types"""
    print("=" * 60)
    print("Test 3: Different Local Search Types")
    print("=" * 60)
    
    route = ["A", "D", "B", "C", "E"]
    
    time_matrix = {
        "DEPOT": {"A": 10, "D": 20, "B": 15, "C": 25, "E": 30},
        "A": {"DEPOT": 10, "D": 15, "B": 10, "C": 20, "E": 25},
        "D": {"DEPOT": 20, "A": 15, "B": 15, "C": 10, "E": 20},
        "B": {"DEPOT": 15, "A": 10, "D": 15, "C": 10, "E": 15},
        "C": {"DEPOT": 25, "A": 20, "D": 10, "B": 10, "E": 10},
        "E": {"DEPOT": 30, "A": 25, "D": 20, "B": 15, "C": 10}
    }
    
    coordinates = {loc: {"lat": i, "lng": i} for i, loc in enumerate(["DEPOT"] + route)}
    
    for search_type in [LocalSearchType.TWO_OPT, LocalSearchType.OR_OPT, LocalSearchType.HYBRID]:
        improved_route, improved_cost = apply_local_search(
            route=route,
            depot="DEPOT",
            time_matrix=time_matrix,
            coordinates=coordinates,
            search_type=search_type,
            max_iterations=10
        )
        print(f"{search_type.value}: {improved_route} (cost: {improved_cost})")
    
    print("\n✓ Test 3 PASSED\n")


def test_strategy_imports():
    """Test that all strategies can import local_search module"""
    print("=" * 60)
    print("Test 4: Strategy Imports")
    print("=" * 60)
    
    try:
        from strategies.gwo_strategy import GWOStrategy
        print("✓ GWO Strategy imported successfully")
        
        from strategies.hho_strategy import HHOStrategy
        print("✓ HHO Strategy imported successfully")
        
        from strategies.ga_strategy import GeneticAlgorithmStrategy
        print("✓ GA Strategy imported successfully")
        
        from strategies.pso_strategy import PSOStrategy
        print("✓ PSO Strategy imported successfully")
        
        print("\n✓ Test 4 PASSED\n")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        raise


def test_local_search_in_strategies():
    """Test that local search methods work in strategies"""
    print("=" * 60)
    print("Test 5: Local Search Methods in Strategies")
    print("=" * 60)
    
    from strategies.gwo_strategy import GWOStrategy
    from strategies.hho_strategy import HHOStrategy
    from strategies.ga_strategy import GeneticAlgorithmStrategy
    from strategies.pso_strategy import PSOStrategy
    
    # Create test data
    route = ["A", "C", "B", "D"]
    time_matrix = {
        "DEPOT": {"A": 5, "C": 15, "B": 25, "D": 35},
        "A": {"DEPOT": 5, "C": 10, "B": 20, "D": 30},
        "C": {"DEPOT": 15, "A": 10, "B": 10, "D": 20},
        "B": {"DEPOT": 25, "A": 20, "C": 10, "D": 10},
        "D": {"DEPOT": 35, "A": 30, "C": 20, "B": 10}
    }
    coordinates = {loc: {"lat": i, "lng": i} for i, loc in enumerate(["DEPOT", "A", "B", "C", "D"])}
    
    # Test GWO (uses max_attempts parameter)
    gwo = GWOStrategy()
    gwo_route, gwo_cost = gwo._local_search(route, "DEPOT", time_matrix, coordinates, max_attempts=10)
    print(f"GWO local search: {gwo_route} (cost: {gwo_cost})")
    
    # Test HHO (uses max_attempts parameter)
    hho = HHOStrategy()
    hho_route, hho_cost = hho._local_search(route, "DEPOT", time_matrix, coordinates, max_attempts=10)
    print(f"HHO local search: {hho_route} (cost: {hho_cost})")
    
    # Test GA (uses max_iterations parameter)
    ga = GeneticAlgorithmStrategy()
    ga_route, ga_cost = ga._local_search(route, "DEPOT", time_matrix, coordinates, max_iterations=10)
    print(f"GA local search: {ga_route} (cost: {ga_cost})")
    
    # Test PSO (uses max_iterations parameter)
    pso = PSOStrategy()
    pso_route, pso_cost = pso._local_search(route, "DEPOT", time_matrix, coordinates, max_iterations=10)
    print(f"PSO local search: {pso_route} (cost: {pso_cost})")
    
    # All should return same or better cost
    original_cost = 5 + 10 + 10 + 10 + 35  # DEPOT->A + A->C + C->B + B->D + D->DEPOT
    print(f"\nOriginal cost: {original_cost}")
    
    assert gwo_cost <= original_cost, "GWO should improve or maintain cost"
    assert hho_cost <= original_cost, "HHO should improve or maintain cost"
    assert ga_cost <= original_cost, "GA should improve or maintain cost"
    assert pso_cost <= original_cost, "PSO should improve or maintain cost"
    
    print("\n✓ Test 5 PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("LOCAL SEARCH MODULE TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_two_opt_basic()
        test_two_opt_swap()
        test_local_search_types()
        test_strategy_imports()
        test_local_search_in_strategies()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
