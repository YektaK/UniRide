#!/usr/bin/env python3
"""Simulate running benchmark without interactive prompts."""

import sys
import os
import json

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "optimizer_api")))

from optimizer_api.utils.local_search_numba import LocalSearchType
from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, load_all_problems, STRATEGIES, TSPLIB_PROBLEMS

def test_single_benchmark():
    """Run a single benchmark test to verify fixes work."""
    print("\n=== TESTING SINGLE BENCHMARK CASE ===\n")
    
    # Load ONE problem from "small" category
    all_problems = load_all_problems("small")
    test_problem = all_problems[0] if all_problems else None
    
    if not test_problem:
        print("ERROR: No problems loaded!")
        return False
    
    print(f"Test Problem: {test_problem.name} (dim={test_problem.dimension}, opt={test_problem.optimal})")
    
    # Test with 2-OPT strategy (local search)  
    print("\n[TEST 1] Running 2-OPT (local search strategy)...")
    strat_name, strategy_instance, strategy_params = STRATEGIES[0]  # Should be 2-opt
    
    print(f"  Strategy: {strat_name}")
    print(f"  Strategy instance: {strategy_instance}")
    print(f"  Algorithm type: {strategy_params.get('algorithm_type')}")
    
    try:
        result = run_single_test(test_problem, strategy_instance, seed=42, params=strategy_params)
        print(f"  ✓ SUCCESS!")
        print(f"    Best gap: {result.get('best_gap', 'N/A'):.2f}%")
        print(f"    Time: {result.get('time_ms', 'N/A'):.0f}ms")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test with GA strategy (meta-heuristic)
    print("\n[TEST 2] Running GA (meta-heuristic strategy)...")
    ga_strat = None
    for s in STRATEGIES:
        if s[0] == "GA":
            ga_strat = s
            break
    
    if ga_strat:
        strat_name, strategy_instance, strategy_params = ga_strat
        print(f"  Strategy: {strat_name}")
        print(f"  Strategy instance: {strategy_instance}")
        print(f"  Algorithm type: {strategy_params.get('algorithm_type')}")
        
        try:
            result = run_single_test(test_problem, strategy_instance, seed=42, params=strategy_params)
            print(f"  ✓ SUCCESS!")
            print(f"    Best gap: {result.get('best_gap', 'N/A'):.2f}%")
            print(f"    Time: {result.get('time_ms', 'N/A'):.0f}ms")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n=== ALL TESTS PASSED ===\n")
    return True

if __name__ == "__main__":
    success = test_single_benchmark()
    sys.exit(0 if success else 1)
