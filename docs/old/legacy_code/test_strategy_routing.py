#!/usr/bin/env python3
"""Quick test: Verify strategy routing fix without full benchmark."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "optimizer_api")))

from optimizer_api.utils.local_search_numba import LocalSearchType

print("\n=== STRATEGY ROUTING TEST ===\n")

# Test 1: Import consistency
print("[TEST 1] Import consistency")
from optimizer_api.tests.run_interactive_benchmark_v2_numba import LocalSearchType as LS_V2
print(f"  run_interactive_benchmark_v2_numba.LocalSearchType is local_search_numba.LocalSearchType: {LocalSearchType is LS_V2}")
assert LocalSearchType is LS_V2, "FAIL: Different LocalSearchType classes!"
print("  PASS: Same LocalSearchType class\n")

# Test 2: Strategy payload conversion (local search)
print("[TEST 2] Strategy payload conversion - Local Search")
payload_ls = {"kind": "local_search", "value": "two_opt"}
ls_type_name = payload_ls["value"].upper()
strategy_instance = LocalSearchType[ls_type_name]
print(f"  Input: {payload_ls}")
print(f"  Output: {strategy_instance}")
print(f"  isinstance(strategy_instance, LocalSearchType): {isinstance(strategy_instance, LocalSearchType)}")
assert isinstance(strategy_instance, LocalSearchType), "FAIL: Not LocalSearchType!"
print("  PASS: Local search payload converted correctly\n")

# Test 3: Strategy dispatch test (isinstance check)
print("[TEST 3] Strategy dispatch routing")
# Simulate run_single_test logic
test_enum = LocalSearchType.TWO_OPT
print(f"  Input strategy: {test_enum} (type: {type(test_enum).__name__})")
if isinstance(test_enum, LocalSearchType):
    print(f"  Result: Would route to LOCAL_SEARCH branch (apply_local_search)")
    route = "local_search"
else:
    print(f"  Result: Would route to META_HEURISTIC branch (_run_meta_heuristic) - ERROR!")
    route = "meta_heuristic"

assert isinstance(test_enum, LocalSearchType), f"FAIL: isinstance check failed! Would use {route} branch"
print("  PASS: Correct routing to local_search branch\n")

# Test 4: All local search types
print("[TEST 4] All LocalSearchType enum values")
for attr_name in ['TWO_OPT', 'THREE_OPT', 'OR_OPT', 'SWAP', 'HYBRID']:
    enum_val = getattr(LocalSearchType, attr_name)
    correct = isinstance(enum_val, LocalSearchType)
    status = "OK" if correct else "FAIL"
    print(f"  {attr_name}: isinstance={correct} [{status}]")
    assert correct, f"FAIL: {attr_name} not recognized as LocalSearchType!"

print("\n=== ALL TESTS PASSED ===")
print("Strategy routing is working correctly.")
print("SWAP and 2-OPT fixes can now run through the full benchmark.\n")
