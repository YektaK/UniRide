"""
Hierarchical FCM Threshold Benchmark

This benchmark determines the optimal threshold for switching from standard FCM
to hierarchical FCM clustering. Tests various problem sizes and measures:
- Execution time
- Solution quality (total distance)
- Capacity violation count
- Border point count

Usage:
    cd optimizer_api
    python tests/benchmark_hierarchical_threshold.py

Results will be saved to:
    optimizer_api/tests/benchmark_results/hierarchical_threshold_benchmark_{timestamp}.json

Author: Super Z AI Assistant
Date: 05 Nisan 2026
"""

import sys
import os
import json
import time
import random
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clustering import Point, Cluster, haversine_distance
from utils.clustering_strategies import (
    FuzzyCMeansClusteringStrategy,
    EnhancedFuzzyCMeansStrategy,
    HierarchicalFCMStrategy,
    HierarchicalConfig,
    get_clustering_strategy
)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    n_students: int
    n_vehicles: int
    strategy_name: str
    execution_time_ms: float
    total_distance_km: float
    capacity_violations: int
    sw_violations: int
    so_violations: int
    border_points_high: int
    border_points_medium: int
    border_points_low: int
    clusters_created: int
    avg_cluster_size: float
    std_cluster_size: float


def generate_random_students(n: int, seed: int = 42) -> List[Point]:
    """
    Generate n random student points.
    
    Uses Düzce, Turkey region coordinates as base.
    """
    random.seed(seed)
    
    # Düzce region bounds
    lat_min, lat_max = 40.79, 40.89
    lng_min, lng_max = 31.10, 31.20
    
    students = []
    for i in range(n):
        lat = random.uniform(lat_min, lat_max)
        lng = random.uniform(lng_min, lng_max)
        disability_type = random.choice(["Sw", "Sw", "Sw", "So", "So", "So", "So", "So"])
        
        students.append(Point(
            id=f"S{i+1:04d}",
            lat=lat,
            lng=lng,
            disability_type=disability_type
        ))
    
    return students


def calculate_total_distance(clusters: List[Cluster]) -> float:
    """Calculate total intra-cluster distance (sum of distances from centroid)."""
    total = 0.0
    for cluster in clusters:
        for point in cluster.points:
            dist = haversine_distance(point.lat, point.lng, cluster.centroid[0], cluster.centroid[1])
            total += dist
    
    return total / 1000  # Convert to km


def count_violations(clusters: List[Cluster], sw_capacity: int, so_capacity: int) -> Tuple[int, int, int]:
    """Count capacity violations."""
    total_violations = 0
    sw_violations = 0
    so_violations = 0
    
    for cluster in clusters:
        if cluster.sw_count > sw_capacity:
            total_violations += 1
            sw_violations += 1
        if cluster.so_count > so_capacity:
            total_violations += 1
            so_violations += 1
    
    return total_violations, sw_violations, so_violations


def calculate_cluster_stats(clusters: List[Cluster]) -> Tuple[float, float]:
    """Calculate average and std of cluster sizes."""
    sizes = [len(c.points) for c in clusters]
    if not sizes:
        return 0.0, 0.0
    
    avg = sum(sizes) / len(sizes)
    variance = sum((s - avg) ** 2 for s in sizes) / len(sizes)
    std = math.sqrt(variance)
    
    return avg, std


def run_benchmark_single(
    students: List[Point],
    n_vehicles: int,
    strategy_name: str,
    sw_capacity: int,
    so_capacity: int,
    n_runs: int = 3
) -> BenchmarkResult:
    """Run benchmark for a single strategy."""
    
    # Get strategy using factory
    strategy = get_clustering_strategy(strategy_name, sw_capacity, so_capacity)
    
    times = []
    distances = []
    violations = []
    sw_viols = []
    so_viols = []
    clusters_created = []
    
    for run in range(n_runs):
        start = time.time()
        
        clusters = strategy.cluster_students(students, n_vehicles)
        
        end = time.time()
        
        times.append((end - start) * 1000)  # ms
        distances.append(calculate_total_distance(clusters))
        v, sw, so = count_violations(clusters, sw_capacity, so_capacity)
        violations.append(v)
        sw_viols.append(sw)
        so_viols.append(so)
        clusters_created.append(len(clusters))
    
    # Use average values
    avg_time = sum(times) / len(times)
    avg_distance = sum(distances) / len(distances)
    avg_violations = sum(violations) / len(violations)
    avg_sw = sum(sw_viols) / len(sw_viols)
    avg_so = sum(so_viols) / len(so_viols)
    avg_clusters = sum(clusters_created) / len(clusters_created)
    
    # Cluster stats from last run
    avg_size, std_size = calculate_cluster_stats(clusters)
    
    return BenchmarkResult(
        n_students=len(students),
        n_vehicles=n_vehicles,
        strategy_name=strategy_name,
        execution_time_ms=avg_time,
        total_distance_km=avg_distance,
        capacity_violations=int(avg_violations),
        sw_violations=int(avg_sw),
        so_violations=int(avg_so),
        border_points_high=0,  # Not tracked for basic strategy
        border_points_medium=0,
        border_points_low=0,
        clusters_created=int(avg_clusters),
        avg_cluster_size=avg_size,
        std_cluster_size=std_size
    )


def run_threshold_benchmark(
    problem_sizes: List[int] = None,
    sw_capacity: int = 4,
    so_capacity: int = 5,
    n_runs: int = 3,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Run comprehensive benchmark comparing FCM variants.
    
    Args:
        problem_sizes: List of N values to test
        sw_capacity: SW capacity per vehicle
        so_capacity: SO capacity per vehicle
        n_runs: Number of runs per configuration
        output_dir: Directory to save results
    
    Returns:
        Dict with benchmark results
    """
    if problem_sizes is None:
        problem_sizes = [50, 100, 150, 200, 300, 500]
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "benchmark_results")
    
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    # Strategy names to test
    strategy_names = [
        "fuzzy_cmeans",
        "fuzzy_cmeans_enhanced",
        "hierarchical_fcm",
    ]
    
    print("=" * 80)
    print("HIERARCHICAL FCM THRESHOLD BENCHMARK")
    print("=" * 80)
    print(f"Problem sizes: {problem_sizes}")
    print(f"Capacity: SW={sw_capacity}, SO={so_capacity}")
    print(f"Runs per config: {n_runs}")
    print("=" * 80)
    
    for n in problem_sizes:
        print(f"\n{'='*40}")
        print(f"Testing N = {n} students")
        print(f"{'='*40}")
        
        # Generate students
        students = generate_random_students(n, seed=42)
        
        # Calculate vehicles needed
        sw_count = sum(1 for s in students if s.disability_type == "Sw")
        so_count = sum(1 for s in students if s.disability_type == "So")
        n_vehicles = max(
            math.ceil(sw_count / sw_capacity),
            math.ceil(so_count / so_capacity),
            1
        )
        
        print(f"  Students: {n} (SW: {sw_count}, SO: {so_count})")
        print(f"  Vehicles needed: {n_vehicles}")
        
        for strategy_name in strategy_names:
            print(f"  Running {strategy_name}...", end=" ", flush=True)
            
            result = run_benchmark_single(
                students, n_vehicles, strategy_name,
                sw_capacity, so_capacity, n_runs
            )
            results.append(result)
            
            print(f"Time: {result.execution_time_ms:.1f}ms, "
                  f"Dist: {result.total_distance_km:.2f}km, "
                  f"Violations: {result.capacity_violations}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"hierarchical_threshold_benchmark_{timestamp}.json")
    
    output_data = {
        "metadata": {
            "timestamp": timestamp,
            "problem_sizes": problem_sizes,
            "sw_capacity": sw_capacity,
            "so_capacity": so_capacity,
            "n_runs": n_runs
        },
        "results": [asdict(r) for r in results]
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*80}")
    
    # Print summary
    print("\nSUMMARY:")
    print("-" * 80)
    print(f"{'N':>6} | {'Strategy':>25} | {'Time(ms)':>10} | {'Dist(km)':>10} | {'Viol':>5}")
    print("-" * 80)
    
    for r in results:
        print(f"{r.n_students:>6} | {r.strategy_name:>25} | {r.execution_time_ms:>10.1f} | "
              f"{r.total_distance_km:>10.2f} | {r.capacity_violations:>5}")
    
    # Analyze optimal threshold
    print("\n" + "=" * 80)
    print("THRESHOLD ANALYSIS:")
    print("=" * 80)
    analyze_threshold(results, problem_sizes)
    
    return output_data


def analyze_threshold(results: List[BenchmarkResult], problem_sizes: List[int]):
    """
    Analyze results to determine optimal threshold.
    
    Compares hierarchical vs standard FCM and identifies where
    hierarchical becomes beneficial.
    """
    
    for n in problem_sizes:
        n_results = [r for r in results if r.n_students == n]
        
        standard = next((r for r in n_results if r.strategy_name == "fuzzy_cmeans"), None)
        enhanced = next((r for r in n_results if r.strategy_name == "fuzzy_cmeans_enhanced"), None)
        hier = next((r for r in n_results if r.strategy_name == "hierarchical_fcm"), None)
        
        print(f"\nN = {n}:")
        
        if standard and enhanced:
            time_improvement = (standard.execution_time_ms - enhanced.execution_time_ms) / standard.execution_time_ms * 100
            dist_improvement = (standard.total_distance_km - enhanced.total_distance_km) / standard.total_distance_km * 100
            
            print(f"  Enhanced FCM vs Standard:")
            print(f"    Time: {time_improvement:+.1f}%")
            print(f"    Distance: {dist_improvement:+.1f}%")
            print(f"    Violations: Standard={standard.capacity_violations}, Enhanced={enhanced.capacity_violations}")
        
        if standard and hier:
            time_improvement = (standard.execution_time_ms - hier.execution_time_ms) / standard.execution_time_ms * 100
            dist_improvement = (standard.total_distance_km - hier.total_distance_km) / standard.total_distance_km * 100
            
            print(f"  Hierarchical FCM vs Standard:")
            print(f"    Time: {time_improvement:+.1f}%")
            print(f"    Distance: {dist_improvement:+.1f}%")
            print(f"    Violations: Standard={standard.capacity_violations}, Hierarchical={hier.capacity_violations}")


def main():
    """Main entry point."""
    
    print("\n" + "=" * 80)
    print("FCM CLUSTERING THRESHOLD BENCHMARK")
    print("=" * 80)
    print("""
This benchmark determines the optimal threshold for switching from
standard FCM to hierarchical FCM clustering.

Problem Sizes Tested: 50, 100, 150, 200, 300, 500 students
Strategies Compared:
  - standard_fcm: Basic FCM with hard assignment
  - enhanced_fcm: FCM with border detection and transfer
  - hierarchical_fcm_t50: Two-stage FCM (threshold=50)
  - hierarchical_fcm_t100: Two-stage FCM (threshold=100)
  - hierarchical_fcm_t150: Two-stage FCM (threshold=150)

Output: JSON file with detailed results
""")
    
    # Run benchmark
    run_threshold_benchmark(
        problem_sizes=[50, 100, 150, 200, 300, 500],
        sw_capacity=4,
        so_capacity=5,
        n_runs=3
    )


if __name__ == "__main__":
    main()
