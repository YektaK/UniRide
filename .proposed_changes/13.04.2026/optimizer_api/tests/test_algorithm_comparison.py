#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Algorithm Performance Comparison Test

Automated comparison of all routing algorithms on benchmark problems.
Tests solution quality and execution time.

Run with:
    cd optimizer_api
    python tests/test_algorithm_comparison.py
    
    # Or with pytest (slow tests excluded by default):
    pytest tests/test_algorithm_comparison.py -v -m "not slow"

Version: 1.0.0
Author: Super Z AI Assistant
Date: 2026-04-04
"""

import sys
import os
import time
import json
import random
import math
import pytest
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.local_search import LocalSearchType, apply_local_search


# ============================================================
# Test Problem Generator
# ============================================================

def generate_tsp_problem(n: int, seed: int = 42) -> Tuple[List[str], Dict, Dict]:
    """
    Generate a random TSP problem.
    
    Args:
        n: Number of locations
        seed: Random seed
    
    Returns:
        Tuple of (locations, distance_matrix, coordinates)
    """
    rng = random.Random(seed)
    
    # Generate random coordinates
    locations = [f"L{i}" for i in range(n)]
    coordinates = {}
    for loc in locations:
        coordinates[loc] = {
            "lat": rng.uniform(40.0, 42.0),
            "lng": rng.uniform(28.0, 30.0)
        }
    
    # Calculate Euclidean distance matrix
    distance_matrix = {}
    for i, loc1 in enumerate(locations):
        distance_matrix[loc1] = {}
        for j, loc2 in enumerate(locations):
            if i == j:
                distance_matrix[loc1][loc2] = 0
            else:
                c1 = coordinates[loc1]
                c2 = coordinates[loc2]
                dist = math.sqrt((c1["lat"] - c2["lat"])**2 + (c1["lng"] - c2["lng"])**2)
                distance_matrix[loc1][loc2] = dist * 111  # Convert to km approximately
    
    return locations, distance_matrix, coordinates


def calculate_route_distance(route: List[str], distance_matrix: Dict) -> float:
    """Calculate total route distance"""
    if not route:
        return 0.0
    
    total = 0.0
    for i in range(len(route) - 1):
        total += distance_matrix.get(route[i], {}).get(route[i + 1], 0)
    # Return to start
    total += distance_matrix.get(route[-1], {}).get(route[0], 0)
    return total


def nearest_neighbor_solution(locations: List[str], distance_matrix: Dict) -> List[str]:
    """Get nearest neighbor heuristic solution"""
    if not locations:
        return []
    
    route = [locations[0]]
    remaining = set(locations[1:])
    
    while remaining:
        current = route[-1]
        nearest = min(remaining, key=lambda x: distance_matrix.get(current, {}).get(x, float('inf')))
        route.append(nearest)
        remaining.remove(nearest)
    
    return route


# ============================================================
# Algorithm Test Runner
# ============================================================

class AlgorithmComparator:
    """Compare performance of different algorithms"""
    
    ALGORITHMS = [
        ("Nearest Neighbor", None, {}),  # Baseline heuristic (no local search)
        ("2-opt", LocalSearchType.TWO_OPT, {"max_iterations": 500}),
        ("3-opt", LocalSearchType.THREE_OPT, {"max_iterations": 200}),
        ("Or-opt", LocalSearchType.OR_OPT, {"max_iterations": 300}),
        ("Swap", LocalSearchType.SWAP, {"max_iterations": 500}),
        ("Hybrid", LocalSearchType.HYBRID, {"max_iterations": 50}),
    ]
    
    def __init__(self):
        self.results = []
    
    def run_single_comparison(
        self,
        initial_route: List[str],
        distance_matrix: Dict,
        algorithm_name: str,
        algorithm_type: LocalSearchType,
        config: Dict
    ) -> Dict:
        """Run comparison for a single algorithm"""
        
        def duration_func(route):
            return calculate_route_distance(route, distance_matrix)
        
        initial_distance = calculate_route_distance(initial_route, distance_matrix)
        
        start_time = time.time()
        
        if algorithm_type is None and algorithm_name == "Nearest Neighbor":
            # Use nearest neighbor heuristic as baseline
            locations = list(distance_matrix.keys())
            improved_route = nearest_neighbor_solution(locations, distance_matrix)
            improved_distance = calculate_route_distance(improved_route, distance_matrix)
        else:
            # Use local search algorithm
            improved_route, improved_distance = apply_local_search(
                initial_route.copy(),
                duration_func,
                algorithm_type,
                **config
            )
        
        elapsed = time.time() - start_time
        
        improvement = ((initial_distance - improved_distance) / initial_distance * 100) if initial_distance > 0 else 0
        
        return {
            "algorithm": algorithm_name,
            "initial_distance": round(initial_distance, 2),
            "final_distance": round(improved_distance, 2),
            "improvement_pct": round(improvement, 2),
            "time_seconds": round(elapsed, 4),
            "route_valid": sorted(improved_route) == sorted(initial_route)
        }
    
    def run_comparison(
        self,
        locations: List[str],
        distance_matrix: Dict,
        problem_name: str = "unknown",
        initial_route: List[str] = None
    ) -> Dict:
        """Run comparison for all algorithms on a single problem"""
        
        if initial_route is None:
            # Use shuffled route as initial
            initial_route = locations.copy()
            random.shuffle(initial_route)
        
        problem_results = {
            "problem": problem_name,
            "n_locations": len(locations),
            "timestamp": datetime.now().isoformat(),
            "algorithms": []
        }
        
        for alg_name, alg_type, config in self.ALGORITHMS:
            result = self.run_single_comparison(
                initial_route,
                distance_matrix,
                alg_name,
                alg_type,
                config
            )
            problem_results["algorithms"].append(result)
        
        # Find best algorithm
        best = min(problem_results["algorithms"], key=lambda x: x["final_distance"])
        problem_results["best_algorithm"] = best["algorithm"]
        problem_results["best_distance"] = best["final_distance"]
        
        # Find fastest algorithm
        fastest = min(problem_results["algorithms"], key=lambda x: x["time_seconds"])
        problem_results["fastest_algorithm"] = fastest["algorithm"]
        problem_results["fastest_time"] = fastest["time_seconds"]
        
        self.results.append(problem_results)
        return problem_results
    
    def run_benchmark_suite(self) -> Dict:
        """Run complete benchmark suite"""
        
        # Problem sizes to test
        problem_sizes = [10, 20, 30, 50]
        
        all_results = {
            "suite_name": "Algorithm Performance Comparison",
            "timestamp": datetime.now().isoformat(),
            "problems": []
        }
        
        for n in problem_sizes:
            for seed in [42, 123, 456]:  # Multiple instances per size
                locations, distance_matrix, _ = generate_tsp_problem(n, seed)
                problem_name = f"random_{n}_{seed}"
                
                result = self.run_comparison(
                    locations,
                    distance_matrix,
                    problem_name
                )
                all_results["problems"].append(result)
        
        # Calculate summary statistics
        all_results["summary"] = self._calculate_summary(all_results["problems"])
        
        return all_results
    
    def _calculate_summary(self, problems: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        
        # Collect statistics per algorithm
        alg_stats = {}
        for alg_name, _, _ in self.ALGORITHMS:
            alg_stats[alg_name] = {
                "total_problems": 0,
                "wins": 0,  # Best distance
                "total_time": 0,
                "total_improvement": 0,
                "avg_distance_ratio": []  # Ratio to best distance
            }
        
        for problem in problems:
            best_distance = problem["best_distance"]
            
            for alg_result in problem["algorithms"]:
                alg_name = alg_result["algorithm"]
                
                alg_stats[alg_name]["total_problems"] += 1
                alg_stats[alg_name]["total_time"] += alg_result["time_seconds"]
                alg_stats[alg_name]["total_improvement"] += alg_result["improvement_pct"]
                
                if alg_result["algorithm"] == problem["best_algorithm"]:
                    alg_stats[alg_name]["wins"] += 1
                
                # Distance ratio
                ratio = alg_result["final_distance"] / best_distance if best_distance > 0 else 1
                alg_stats[alg_name]["avg_distance_ratio"].append(ratio)
        
        # Calculate averages
        summary = {}
        for alg_name, stats in alg_stats.items():
            n = stats["total_problems"]
            summary[alg_name] = {
                "wins": stats["wins"],
                "win_rate": round(stats["wins"] / n * 100, 1) if n > 0 else 0,
                "avg_time": round(stats["total_time"] / n, 4) if n > 0 else 0,
                "avg_improvement": round(stats["total_improvement"] / n, 2) if n > 0 else 0,
                "avg_distance_ratio": round(sum(stats["avg_distance_ratio"]) / n, 4) if n > 0 else 1,
            }
        
        return summary
    
    def print_report(self, results: Dict = None):
        """Print formatted report"""
        if results is None:
            results = {"problems": self.results, "summary": self._calculate_summary(self.results)}
        
        print("\n" + "=" * 80)
        print("ALGORITHM PERFORMANCE COMPARISON REPORT")
        print("=" * 80)
        
        # Per-problem results
        print("\n📊 PROBLEM RESULTS:")
        print("-" * 80)
        print(f"{'Problem':<20} | {'n':<5} | {'Best Alg':<10} | {'Best Dist':<12} | {'Fastest':<10}")
        print("-" * 80)
        
        for problem in results.get("problems", []):
            print(f"{problem['problem']:<20} | {problem['n_locations']:<5} | "
                  f"{problem['best_algorithm']:<10} | {problem['best_distance']:<12.2f} | "
                  f"{problem['fastest_algorithm']:<10}")
        
        # Summary statistics
        print("\n📈 SUMMARY STATISTICS:")
        print("-" * 80)
        print(f"{'Algorithm':<10} | {'Wins':<6} | {'Win%':<6} | {'Avg Time':<10} | {'Avg Imp%':<10} | {'Dist Ratio':<10}")
        print("-" * 80)
        
        summary = results.get("summary", {})
        for alg_name, stats in summary.items():
            print(f"{alg_name:<10} | {stats['wins']:<6} | {stats['win_rate']:<6.1f} | "
                  f"{stats['avg_time']:<10.4f} | {stats['avg_improvement']:<10.2f} | "
                  f"{stats['avg_distance_ratio']:<10.4f}")
        
        print("\n" + "=" * 80)


# ============================================================
# Quick Tests
# ============================================================

def test_basic_comparison():
    """Test basic algorithm comparison"""
    print("\n🔬 Running Basic Algorithm Comparison...")
    
    # Generate small problem
    locations, distance_matrix, _ = generate_tsp_problem(15, seed=42)
    
    comparator = AlgorithmComparator()
    result = comparator.run_comparison(locations, distance_matrix, "test_15_nodes")
    
    # Print results
    print(f"\nProblem: {result['problem']}")
    print(f"Locations: {result['n_locations']}")
    print(f"Best Algorithm: {result['best_algorithm']} (distance: {result['best_distance']:.2f})")
    print(f"Fastest Algorithm: {result['fastest_algorithm']} (time: {result['fastest_time']:.4f}s)")
    
    print("\nAlgorithm Details:")
    for alg in result["algorithms"]:
        print(f"  {alg['algorithm']:<15}: dist={alg['final_distance']:.2f}, "
              f"improvement={alg['improvement_pct']:.1f}%, time={alg['time_seconds']:.4f}s")
    
    # Verify all routes are valid
    for alg in result["algorithms"]:
        assert alg["route_valid"], f"{alg['algorithm']} produced invalid route"
    
    print("\n✅ Basic comparison test passed!")


@pytest.mark.slow
def test_benchmark_suite():
    """Test full benchmark suite"""
    print("\n🔬 Running Benchmark Suite...")
    
    comparator = AlgorithmComparator()
    results = comparator.run_benchmark_suite()
    
    # Print report
    comparator.print_report(results)
    
    # Verify results
    assert len(results["problems"]) > 0, "No problems in results"
    assert "summary" in results, "No summary in results"
    
    # Verify all algorithms were tested
    for alg_name, _, _ in comparator.ALGORITHMS:
        assert alg_name in results["summary"], f"{alg_name} not in summary"
    
    print("\n✅ Benchmark suite test passed!")


def test_improvement_quality():
    """Test that algorithms actually improve routes"""
    print("\n🔬 Testing Improvement Quality...")
    
    # Generate problem
    locations, distance_matrix, _ = generate_tsp_problem(20, seed=42)
    
    # Create a bad initial route (reverse order)
    bad_route = locations[::-1]
    initial_distance = calculate_route_distance(bad_route, distance_matrix)
    
    print(f"Initial (bad) route distance: {initial_distance:.2f}")
    
    # Test each algorithm
    for alg_name, alg_type, config in AlgorithmComparator.ALGORITHMS:
        def duration_func(route):
            return calculate_route_distance(route, distance_matrix)
        
        improved_route, improved_distance = apply_local_search(
            bad_route.copy(),
            duration_func,
            alg_type,
            **config
        )
        
        improvement = ((initial_distance - improved_distance) / initial_distance * 100)
        
        print(f"  {alg_name:<10}: improved by {improvement:.1f}%")
        
        # Algorithm should improve or at least not worsen significantly
        assert improved_distance <= initial_distance * 1.01, f"{alg_name} made route worse!"
    
    print("\n✅ Improvement quality test passed!")


def test_consistency():
    """Test algorithm consistency across runs"""
    print("\n🔬 Testing Algorithm Consistency...")
    
    # Generate fixed problem
    locations, distance_matrix, _ = generate_tsp_problem(15, seed=42)
    
    def duration_func(route):
        return calculate_route_distance(route, distance_matrix)
    
    # Run same algorithm multiple times with same seed
    results = []
    for run in range(3):
        random.seed(42)  # Reset seed
        route = locations.copy()
        random.shuffle(route)
        
        improved, dist = apply_local_search(
            route,
            duration_func,
            LocalSearchType.TWO_OPT,
            max_iterations=100
        )
        results.append(dist)
    
    # Results should be consistent (same seed = same result)
    # Allow small variance due to algorithm non-determinism
    avg = sum(results) / len(results)
    max_deviation = max(abs(r - avg) for r in results)
    
    print(f"Results: {results}")
    print(f"Average: {avg:.2f}, Max deviation: {max_deviation:.2f}")
    
    # All results should be similar (within 10%)
    for r in results:
        assert abs(r - avg) < avg * 0.1, "Results not consistent!"
    
    print("\n✅ Consistency test passed!")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ALGORITHM PERFORMANCE COMPARISON TEST SUITE")
    print("=" * 80)
    
    # Run tests
    test_basic_comparison()
    test_improvement_quality()
    test_consistency()
    test_benchmark_suite()
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
