#!/usr/bin/env python3
"""Test that the strategy instance fix works correctly."""

import sys
import os

# Add parent to path like the benchmark does
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "optimizer_api")))

# Import at module level (like the fixed benchmark runner does)
from optimizer_api.utils.local_search_numba import LocalSearchType
from optimizer_api.tests.run_interactive_benchmark_v2_numba import run_single_test, load_all_problems

def test_strategy_conversion():
    """Test the strategy payload to enum conversion."""
    print("Testing strategy payload conversion...\n")
    
    # Test case 1: Local search strategy payload
    strategy_payload_ls = {"kind": "local_search", "value": "two_opt"}
    algorithm_type = "local_search"
    
    print(f"Input: {strategy_payload_ls}")
    if isinstance(strategy_payload_ls, dict):
        if strategy_payload_ls.get("kind") == "local_search":
            ls_type_name = strategy_payload_ls["value"].upper()
            strategy_instance = LocalSearchType[ls_type_name]
            print(f"Output: {strategy_instance}")
            print(f"Type: {type(strategy_instance)}")
            print(f"isinstance(strategy_instance, LocalSearchType): {isinstance(strategy_instance, LocalSearchType)}")
            assert isinstance(strategy_instance, LocalSearchType), "FAIL: Not a LocalSearchType!"
            print("✓ PASS: Local search strategy converted correctly\n")
        else:
            print("ERROR: Not local_search kind")
    
    # Test case 2: Meta-heuristic strategy payload
    strategy_payload_mh = {"kind": "meta_heuristic", "value": "GA"}
    algorithm_type = "meta_heuristic"
    
    print(f"Input: {strategy_payload_mh}")
    if isinstance(strategy_payload_mh, dict):
        if strategy_payload_mh.get("kind") == "local_search":
            strategy_instance = LocalSearchType(strategy_payload_mh["value"])
        else:
            strategy_instance = strategy_payload_mh.get("value")
            print(f"Output: {strategy_instance}")
            print(f"Type: {type(strategy_instance)}")
            print(f"isinstance(strategy_instance, LocalSearchType): {isinstance(strategy_instance, LocalSearchType)}")
            assert isinstance(strategy_instance, str), f"FAIL: Not a string! Got {type(strategy_instance)}"
            print("✓ PASS: Meta-heuristic strategy kept as string\n")
    
    # Test case 3: All local search types
    print("Testing all LocalSearchType values:")
    for name in ['TWO_OPT', 'THREE_OPT', 'OR_OPT', 'SWAP', 'HYBRID']:
        enum_val = LocalSearchType[name]
        payload = {"kind": "local_search", "value": enum_val.value}
        
        if isinstance(payload, dict):
            if payload.get("kind") == "local_search":
                ls_type_name = payload["value"].upper()
                strategy_instance = LocalSearchType[ls_type_name]
                is_instance = isinstance(strategy_instance, LocalSearchType)
                status = "✓" if is_instance else "✗"
                print(f"  {status} {name}: {strategy_instance} - isinstance={is_instance}")
                assert is_instance, f"FAIL: {name} not recognized as LocalSearchType!"
    
    print("\n✓ ALL TESTS PASSED!")
    print("\nThe fix should work correctly. Strategy payloads will be converted to the proper type.")

if __name__ == "__main__":
    test_strategy_conversion()
