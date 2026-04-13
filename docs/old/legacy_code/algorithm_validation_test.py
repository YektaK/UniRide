#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Algorithm Validation Test Suite

This module tests all local search implementations for:
1. Correctness (vs. known optimal solutions)
2. Convergence behavior
3. Edge cases and error conditions
4. Performance validation
"""

import sys
import os
import numpy as np
from typing import List, Tuple, Dict

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "optimizer_api")))

# Import with Numba cache handling
try:
    from optimizer_api.utils.local_search_numba import (
        LocalSearchType,
        get_local_search,
        _calculate_tour_length_numba,
        _two_opt_improve_numba,
        _swap_improve_numba,
        _three_opt_improve_numba,
        _or_opt_improve_numba,
    )
except Exception as e:
    print(f"Warning: Numba import error: {e}")
    print("Clearing Numba cache and retrying...")
    import shutil
    numbacache = os.path.expanduser("~/.numba_cache") if os.path.exists(os.path.expanduser("~/.numba_cache")) else None
    if numbacache:
        shutil.rmtree(numbacache, ignore_errors=True)
    from optimizer_api.utils.local_search_numba import (
        LocalSearchType,
        get_local_search,
        _calculate_tour_length_numba,
        _two_opt_improve_numba,
        _swap_improve_numba,
        _three_opt_improve_numba,
        _or_opt_improve_numba,
    )


# ==============================================================
# TEST PROBLEMS - Known optimal solutions
# ==============================================================

class TSPTestProblem:
    """Small TSP problem with known optimal solution"""
    
    def __init__(self, name: str, coords: List[Tuple[float, float]], optimal_length: float):
        self.name = name
        self.coords = np.array(coords, dtype=np.float64)
        self.n = len(coords)
        self.optimal_length = optimal_length
        self.dist_matrix = self._compute_distances()
    
    def _compute_distances(self) -> np.ndarray:
        """Compute Euclidean distance matrix"""
        dist = np.zeros((self.n, self.n))
        for i in range(self.n):
            for j in range(self.n):
                if i != j:
                    dx = self.coords[i, 0] - self.coords[j, 0]
                    dy = self.coords[i, 1] - self.coords[j, 1]
                    dist[i, j] = np.sqrt(dx*dx + dy*dy)
        return dist
    
    def tour_length(self, route: np.ndarray) -> float:
        """Calculate tour length for a route"""
        return _calculate_tour_length_numba(route, self.dist_matrix)


# Test problem: 5-city problem (simple)
PROBLEM_5_CITIES = TSPTestProblem(
    name="5-city problem",
    coords=[
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 10.0),
        (0.0, 10.0),
        (5.0, 5.0),
    ],
    optimal_length=40.0  # Estimated: 0->1->2->3->0 or similar
)

# Test problem: Burma14 (well-known TSP instance, optimal = 3323)
BURMA14_COORDS = [
    (16.47, 96.10), (16.47, 94.51), (20.09, 92.54), (22.39, 93.37),
    (25.23, 97.24), (22.00, 96.05), (20.47, 97.02), (17.20, 96.29),
    (16.30, 97.38), (14.05, 98.12), (16.53, 97.38), (21.52, 95.59),
    (19.41, 97.13), (20.09, 94.55)
]

PROBLEM_BURMA14 = TSPTestProblem(
    name="Burma14",
    coords=BURMA14_COORDS,
    optimal_length=3323.0
)


# ==============================================================
# TEST FUNCTIONS
# ==============================================================

def test_2opt_correctness():
    """Test 2-opt for correctness on known problems"""
    print("\n" + "="*70)
    print("TEST 1: 2-OPT CORRECTNESS")
    print("="*70)
    
    for problem in [PROBLEM_5_CITIES, PROBLEM_BURMA14]:
        print(f"\nProblem: {problem.name} (n={problem.n}, optimal={problem.optimal_length})")
        
        # Initial tours to test
        initial_tours = [
            np.arange(problem.n, dtype=np.int64),  # Sequential
            np.array([problem.n-1-i for i in range(problem.n)], dtype=np.int64),  # Reverse
        ]
        
        for idx, initial in enumerate(initial_tours):
            print(f"\n  Initial tour {idx+1}: {initial}")
            initial_length = problem.tour_length(initial)
            print(f"  Initial length: {initial_length:.2f}")
            
            # Apply 2-opt
            improved, final_length = _two_opt_improve_numba(initial, problem.dist_matrix, max_iterations=100, first_improvement=False)
            
            print(f"  Final length: {final_length:.2f}")
            print(f"  Improvement: {initial_length - final_length:.2f} ({100*(initial_length-final_length)/initial_length:.1f}%)")
            print(f"  Gap to optimal: {final_length - problem.optimal_length:.2f} ({100*(final_length-problem.optimal_length)/problem.optimal_length:.1f}%)")
            
            # Verify tour validity
            if len(np.unique(improved)) != problem.n:
                print(f"  ERROR: Tour has duplicate nodes!")
            if not np.array_equal(np.sort(improved), np.arange(problem.n)):
                print(f"  ERROR: Tour missing nodes!")


def test_swap_correctness():
    """Test SWAP for correctness"""
    print("\n" + "="*70)
    print("TEST 2: SWAP CORRECTNESS")
    print("="*70)
    
    for problem in [PROBLEM_5_CITIES, PROBLEM_BURMA14]:
        print(f"\nProblem: {problem.name} (n={problem.n})")
        
        initial = np.arange(problem.n, dtype=np.int64)
        print(f"  Initial tour: {initial}")
        initial_length = problem.tour_length(initial)
        print(f"  Initial length: {initial_length:.2f}")
        
        # Apply SWAP
        improved, final_length = _swap_improve_numba(initial, problem.dist_matrix, max_iterations=100, first_improvement=False)
        
        print(f"  Final length: {final_length:.2f}")
        print(f"  Improvement: {initial_length - final_length:.2f}")
        
        # Check validity
        print(f"  Unique nodes: {len(np.unique(improved))} (should be {problem.n})")
        if len(np.unique(improved)) != problem.n:
            print(f"  ERROR: Tour has duplicate or missing nodes!")
            print(f"    Improved tour: {improved}")


def test_negative_gap():
    """Test for negative gap issue (impossible result)"""
    print("\n" + "="*70)
    print("TEST 3: NEGATIVE GAP DETECTION")
    print("="*70)
    
    problem = PROBLEM_BURMA14
    print(f"\nProblem: {problem.name}")
    print(f"Optimal known length: {problem.optimal_length}")
    
    for algo_name, improve_func, params in [
        ("2-opt", _two_opt_improve_numba, {"max_iterations": 100, "first_improvement": False}),
        ("3-opt", _three_opt_improve_numba, {"max_iterations": 50, "first_improvement": False}),
        ("Swap", _swap_improve_numba, {"max_iterations": 100, "first_improvement": False}),
        ("Or-opt", _or_opt_improve_numba, {"max_iterations": 50, "max_segment_size": 3}),
    ]:
        initial = np.arange(problem.n, dtype=np.int64)
        
        try:
            if algo_name == "Or-opt":
                improved, final_length = improve_func(initial, problem.dist_matrix, **params)
            else:
                improved, final_length = improve_func(initial, problem.dist_matrix, **params)
            
            gap = (final_length - problem.optimal_length) / problem.optimal_length * 100
            print(f"\n{algo_name}:")
            print(f"  Final length: {final_length:.2f}")
            print(f"  Gap to optimal: {gap:.2f}%")
            
            if gap < 0:
                print(f"  ❌ ERROR: NEGATIVE GAP! Better than known optimal!")
            else:
                print(f"  ✓ OK: Positive gap as expected")
                
        except Exception as e:
            print(f"\n{algo_name}:")
            print(f"  ❌ ERROR: {e}")


def test_edge_cases():
    """Test edge cases"""
    print("\n" + "="*70)
    print("TEST 4: EDGE CASES")
    print("="*70)
    
    # Small problems
    for n in [3, 4, 5]:
        coords = [(float(i), 0.0) for i in range(n)]
        problem = TSPTestProblem(f"Linear-{n}", coords, optimal_length=float(2*(n-1)))
        
        print(f"\nLinear problem (n={n}):")
        initial = np.arange(n, dtype=np.int64)
        initial_length = problem.tour_length(initial)
        
        improved, final_length = _two_opt_improve_numba(initial, problem.dist_matrix, max_iterations=10, first_improvement=False)
        
        print(f"  Initial: {initial_length:.2f}")
        print(f"  Final: {final_length:.2f}")
        print(f"  Optimal: {problem.optimal_length:.2f}")
        print(f"  Valid: {len(np.unique(improved)) == n}")


def test_distance_matrix_symmetry():
    """Verify distance matrix symmetry (prerequisite for TSP)"""
    print("\n" + "="*70)
    print("TEST 5: DISTANCE MATRIX PROPERTIES")
    print("="*70)
    
    for problem in [PROBLEM_5_CITIES, PROBLEM_BURMA14]:
        print(f"\n{problem.name}:")
        
        # Check symmetry
        is_symmetric = np.allclose(problem.dist_matrix, problem.dist_matrix.T)
        print(f"  Symmetric: {is_symmetric}")
        
        # Check diagonal
        diagonal_zero = np.allclose(np.diag(problem.dist_matrix), 0)
        print(f"  Diagonal = 0: {diagonal_zero}")
        
        # Check triangle inequality (should hold for Euclidean)
        violations = 0
        for i in range(problem.n):
            for j in range(problem.n):
                for k in range(problem.n):
                    if problem.dist_matrix[i,k] > problem.dist_matrix[i,j] + problem.dist_matrix[j,k] + 1e-6:
                        violations += 1
        
        print(f"  Triangle inequality violations: {violations}")


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" ALGORITHM VALIDATION TEST SUITE")
    print("="*70)
    print(f"Created: April 8, 2026")
    
    try:
        test_2opt_correctness()
        test_swap_correctness()
        test_negative_gap()
        test_edge_cases()
        test_distance_matrix_symmetry()
        
        print("\n" + "="*70)
        print("TEST SUITE COMPLETE")
        print("="*70)
        
    except Exception as e:
        import traceback
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
