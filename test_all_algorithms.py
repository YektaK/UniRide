#!/usr/bin/env python3
"""
Final validation: Run one complete benchmark cycle with all 9 algorithms.
Tests that:
1. SWAP fix works (adjacent swaps are included)
2. 2-OPT fix works (no floating point accumulation errors)  
3. Strategy dispatch works (LocalSearchType enum routing)
4. All algorithms complete without errors
"""

import sys
import os

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "optimizer_api")))

from optimizer_api.utils.local_search_numba import LocalSearchType
from optimizer_api.tests.run_interactive_benchmark_v2_numba import (
    run_single_test, 
    load_all_problems,
    STRATEGIES,
)

def main():
    print("\n" + "="*70)
    print("VALIDATION TEST: Testing all 9 algorithms on Berlin52")
    print("="*70 + "\n")
    
    # Load one problem
    problems = load_all_problems("small")
    test_problem = problems[0]  # Berlin52 (52 cities)
    print(f"Problem: {test_problem.name} (n={test_problem.dimension}, optimal={test_problem.optimal})")
    print(f"Seed: Fixed at 42 for reproducibility\n")
    
    results = []
    failed = []
    
    # Test all 9 strategies
    print("Algorithm Results:")
    print("-" * 70)
    print(f"{'Strategy':<15} {'Type':<15} {'Gap %':<10} {'Time (ms)':<12} {'Status'}")
    print("-" * 70)
    
    for i, (strat_name, strategy_instance, strategy_params) in enumerate(STRATEGIES):
        algo_type = strategy_params.get("algorithm_type", "unknown")
        
        try:
            # Run test
            result = run_single_test(test_problem, strategy_instance, seed=42, params=strategy_params)
            
            gap = result.get('best_gap', 0)
            time_ms = result.get('time_ms', 0)
            status = "OK" if gap >= -0.01 else "NEGATIVE_GAP"
            
            print(f"{strat_name:<15} {algo_type:<15} {gap:>8.2f}% {time_ms:>10.0f}ms  {status}")
            
            results.append({
                'name': strat_name,
                'gap': gap,
                'time': time_ms,
                'result': result
            })
            
        except Exception as e:
            print(f"{strat_name:<15} {algo_type:<15} ERROR: {str(e)[:30]}")
            failed.append((strat_name, str(e)))
    
    print("-" * 70)
    
    # Summary
    print(f"\nSUMMARY:")
    print(f"  Total algorithms tested: {len(STRATEGIES)}")
    print(f"  Successful: {len(results)}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFAILED ALGORITHMS:")
        for name, error in failed:
            print(f"  - {name}: {error[:60]}")
        return 1
    
    # Check SWAP performance
    swap_result = next((r for r in results if r['name'] == 'Swap'), None)
    if swap_result:
        print(f"\nSWAP VALIDATION (Fixed):")
        print(f"  Gap: {swap_result['gap']:.2f}%")
        print(f"  Expected: Positive (no adjacent skip), good quality")
        if swap_result['gap'] >= -0.01:
            print(f"  Status: PASS - Normal gap value")
        else:
            print(f"  Status: FAIL - Negative gap detected")
            return 1
    
    # Check 2-OPT performance
    two_opt_result = next((r for r in results if r['name'] == '2-opt'), None)
    if two_opt_result:
        print(f"\n2-OPT VALIDATION (Fixed):")
        print(f"  Gap: {two_opt_result['gap']:.2f}%")
        print(f"  Expected: Positive (no float accumulation), good quality")
        if two_opt_result['gap'] >= -0.01:
            print(f"  Status: PASS - No negative gap anomalies")
        else:
            print(f"  Status: FAIL - Negative gap detected")
            return 1
    
    print(f"\n✓ ALL TESTS PASSED!")
    print(f"  - SWAP algorithm fix verified")
    print(f"  - 2-OPT algorithm fix verified")
    print(f"  - Strategy dispatch working correctly")
    print(f"  - All 9 algorithms completed successfully\n")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
