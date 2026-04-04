"""
Hierarchical FCM Threshold Benchmark with TSPLIB Problems

This benchmark determines the optimal threshold for switching from standard FCM
to hierarchical FCM clustering. Uses real TSPLIB problems close to target sizes:
- ~50:  eil51 (51), berlin52 (52), eil76 (76)
- ~100: kroA100 (100), kroB100 (100), kroC100 (100)
- ~150: kroA150 (150), kroB150 (150), pr152 (152)
- ~200: kroA200 (200), kroB200 (200), ts225 (225)
- ~300: pr299 (299), gil262 (262), lin318 (318)
- ~500: d493 (493), pr439 (439), rd400 (400)

For each category, 3 problems are tested to get statistically meaningful results.

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
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
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


# ============================================================
# TSPLIB Configuration
# ============================================================

TSPLIB_DIR = os.path.join(os.path.dirname(__file__), "tsplib_data")

# Problems organized by target size category
# For each category, we select 3 problems closest to target size
TSPLIB_THRESHOLD_PROBLEMS = {
    "~50": [
        # Target: 50 | Actual sizes: 51, 52, 76
        ("eil51", 51, 426),
        ("berlin52", 52, 7542),
        ("eil76", 76, 538),
    ],
    "~100": [
        # Target: 100 | Actual sizes: all exactly 100
        ("kroA100", 100, 21282),
        ("kroB100", 100, 22141),
        ("kroC100", 100, 20749),
    ],
    "~150": [
        # Target: 150 | Actual sizes: 150, 150, 152
        ("kroA150", 150, 26524),
        ("kroB150", 150, 26130),
        ("pr152", 152, 73682),
    ],
    "~200": [
        # Target: 200 | Actual sizes: 200, 200, 225
        ("kroA200", 200, 29368),
        ("kroB200", 200, 29437),
        ("ts225", 225, 126843),
    ],
    "~300": [
        # Target: 300 | Actual sizes: 262, 299, 318
        ("gil262", 262, 2412),
        ("pr299", 299, 48191),
        ("lin318", 318, 42029),
    ],
    "~500": [
        # Target: 500 | Actual sizes: 400, 439, 493
        ("rd400", 400, 15281),
        ("pr439", 439, 107217),
        ("d493", 493, 35002),
    ],
}


@dataclass
class TSPLIBProblem:
    """TSPLIB problem definition for clustering benchmark."""
    name: str
    dimension: int
    optimal: int
    coordinates: List[Tuple[float, float]]
    category: str


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    problem_name: str
    target_size: str
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


def parse_tsplib_file(filepath: str) -> Optional[Dict]:
    """
    Parse TSPLIB .tsp file and extract problem data.
    
    TSPLIB format example:
        NAME: berlin52
        TYPE: TSP
        COMMENT: 52 locations in Berlin
        DIMENSION: 52
        EDGE_WEIGHT_TYPE: EUC_2D
        NODE_COORD_SECTION
        1 565.0 575.0
        2 25.0 185.0
        ...
        EOF
    """
    import re
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata
        name_match = re.search(r'NAME\s*:\s*(\S+)', content, re.IGNORECASE)
        dim_match = re.search(r'DIMENSION\s*:\s*(\d+)', content, re.IGNORECASE)
        
        if not dim_match:
            print(f"    [ERROR] Cannot find DIMENSION in {filepath}")
            return None
        
        name = name_match.group(1) if name_match else os.path.basename(filepath)
        dimension = int(dim_match.group(1))
        
        # Extract coordinates
        coordinates = []
        
        # Find NODE_COORD_SECTION
        coord_section_match = re.search(
            r'NODE_COORD_SECTION\s*\n(.*?)\n?(?:EOF|DISPLAY_DATA_SECTION)',
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if coord_section_match:
            coord_lines = coord_section_match.group(1).strip().split('\n')
            
            for line in coord_lines:
                line = line.strip()
                if not line or line.upper().startswith('EOF'):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        coordinates.append((x, y))
                    except ValueError:
                        continue
        
        if len(coordinates) != dimension:
            print(f"    [WARNING] Coordinate count ({len(coordinates)}) != DIMENSION ({dimension})")
        
        return {
            'name': name.lower(),
            'dimension': dimension,
            'coordinates': coordinates,
        }
    
    except Exception as e:
        print(f"    [ERROR] Failed to parse {filepath}: {e}")
        return None


def load_tsplib_problem(problem_name: str, dimension: int, optimal: int) -> Optional[TSPLIBProblem]:
    """Load a TSPLIB problem from local file."""
    filepath = os.path.join(TSPLIB_DIR, f"{problem_name}.tsp")
    
    if not os.path.exists(filepath):
        print(f"    [ERROR] File not found: {filepath}")
        return None
    
    data = parse_tsplib_file(filepath)
    
    if not data:
        return None
    
    # Determine category based on dimension
    if dimension <= 100:
        category = "small"
    elif dimension <= 500:
        category = "medium"
    else:
        category = "large"
    
    return TSPLIBProblem(
        name=data['name'],
        dimension=data['dimension'],
        optimal=optimal,
        coordinates=data['coordinates'],
        category=category
    )


def tsplib_to_students(problem: TSPLIBProblem) -> List[Point]:
    """
    Convert TSPLIB coordinates to student points.
    
    TSPLIB coordinates are typically in arbitrary units, so we normalize
    them to a reasonable geographic range for clustering.
    
    Also assigns disability types randomly (Sw/So) with a 3:5 ratio
    (matching typical student disability distribution).
    """
    import random
    random.seed(42)  # Reproducibility
    
    if not problem.coordinates:
        return []
    
    # Find coordinate bounds
    xs = [c[0] for c in problem.coordinates]
    ys = [c[1] for c in problem.coordinates]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    # Normalize to Düzce, Turkey region (roughly)
    # This is just for visualization; clustering works on relative distances
    lat_min, lat_max = 40.79, 40.89
    lng_min, lng_max = 31.10, 31.20
    
    students = []
    for i, (x, y) in enumerate(problem.coordinates):
        # Normalize coordinates
        if x_max > x_min:
            lat = lat_min + (x - x_min) / (x_max - x_min) * (lat_max - lat_min)
        else:
            lat = (lat_min + lat_max) / 2
            
        if y_max > y_min:
            lng = lng_min + (y - y_min) / (y_max - y_min) * (lng_max - lng_min)
        else:
            lng = (lng_min + lng_max) / 2
        
        # Assign disability type with 3:5 ratio (Sw:So)
        disability_type = random.choice(["Sw", "Sw", "Sw", "So", "So", "So", "So", "So"])
        
        students.append(Point(
            id=f"{problem.name}_{i+1:04d}",
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
    problem: TSPLIBProblem,
    students: List[Point],
    n_vehicles: int,
    strategy_name: str,
    sw_capacity: int,
    so_capacity: int,
    target_size: str,
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
        problem_name=problem.name,
        target_size=target_size,
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
    sw_capacity: int = 4,
    so_capacity: int = 5,
    n_runs: int = 3,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Run comprehensive benchmark comparing FCM variants on TSPLIB problems.
    
    For each target size category, tests 3 TSPLIB problems close to that size.
    
    Args:
        sw_capacity: SW capacity per vehicle
        so_capacity: SO capacity per vehicle
        n_runs: Number of runs per configuration
        output_dir: Directory to save results
    
    Returns:
        Dict with benchmark results
    """
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
    print("HIERARCHICAL FCM THRESHOLD BENCHMARK (TSPLIB PROBLEMS)")
    print("=" * 80)
    print(f"Target sizes: {list(TSPLIB_THRESHOLD_PROBLEMS.keys())}")
    print(f"Problems per size: 3")
    print(f"Capacity: SW={sw_capacity}, SO={so_capacity}")
    print(f"Runs per config: {n_runs}")
    print("=" * 80)
    
    # Iterate through target size categories
    for target_size, problem_list in TSPLIB_THRESHOLD_PROBLEMS.items():
        print(f"\n{'='*60}")
        print(f"TARGET SIZE: {target_size}")
        print(f"{'='*60}")
        
        for problem_name, dimension, optimal in problem_list:
            print(f"\n  Problem: {problem_name} (n={dimension}, optimal={optimal})")
            
            # Load problem
            problem = load_tsplib_problem(problem_name, dimension, optimal)
            
            if not problem:
                print(f"    [SKIP] Could not load {problem_name}")
                continue
            
            # Convert to students
            students = tsplib_to_students(problem)
            
            if not students:
                print(f"    [SKIP] No students generated")
                continue
            
            # Calculate vehicles needed
            sw_count = sum(1 for s in students if s.disability_type == "Sw")
            so_count = sum(1 for s in students if s.disability_type == "So")
            n_vehicles = max(
                math.ceil(sw_count / sw_capacity),
                math.ceil(so_count / so_capacity),
                1
            )
            
            print(f"    Students: {len(students)} (SW: {sw_count}, SO: {so_count})")
            print(f"    Vehicles needed: {n_vehicles}")
            
            for strategy_name in strategy_names:
                print(f"    Running {strategy_name}...", end=" ", flush=True)
                
                result = run_benchmark_single(
                    problem, students, n_vehicles, strategy_name,
                    sw_capacity, so_capacity, target_size, n_runs
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
            "problem_selection": TSPLIB_THRESHOLD_PROBLEMS,
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
    print("-" * 100)
    print(f"{'Target':>8} | {'Problem':<12} | {'N':>5} | {'Strategy':<22} | {'Time(ms)':>10} | {'Dist(km)':>10} | {'Viol':>5}")
    print("-" * 100)
    
    for r in results:
        print(f"{r.target_size:>8} | {r.problem_name:<12} | {r.n_students:>5} | {r.strategy_name:<22} | "
              f"{r.execution_time_ms:>10.1f} | {r.total_distance_km:>10.2f} | {r.capacity_violations:>5}")
    
    # Analyze optimal threshold
    print("\n" + "=" * 80)
    print("THRESHOLD ANALYSIS:")
    print("=" * 80)
    analyze_threshold(results)
    
    return output_data


def analyze_threshold(results: List[BenchmarkResult], target_sizes: List[str] = None):
    """
    Analyze results to determine optimal threshold.
    
    Compares hierarchical vs standard FCM and identifies where
    hierarchical becomes beneficial.
    """
    if target_sizes is None:
        target_sizes = list(TSPLIB_THRESHOLD_PROBLEMS.keys())
    
    for target in target_sizes:
        target_results = [r for r in results if r.target_size == target]
        
        if not target_results:
            continue
        
        # Get unique problems for this target
        problems = list(set(r.problem_name for r in target_results))
        
        print(f"\n{target}:")
        
        for prob in problems:
            prob_results = [r for r in target_results if r.problem_name == prob]
            
            standard = next((r for r in prob_results if r.strategy_name == "fuzzy_cmeans"), None)
            enhanced = next((r for r in prob_results if r.strategy_name == "fuzzy_cmeans_enhanced"), None)
            hier = next((r for r in prob_results if r.strategy_name == "hierarchical_fcm"), None)
            
            print(f"  {prob} (n={prob_results[0].n_students if prob_results else '?'}):")
            
            if standard and enhanced:
                time_diff = enhanced.execution_time_ms - standard.execution_time_ms
                time_pct = time_diff / standard.execution_time_ms * 100 if standard.execution_time_ms > 0 else 0
                dist_diff = enhanced.total_distance_km - standard.total_distance_km
                dist_pct = dist_diff / standard.total_distance_km * 100 if standard.total_distance_km > 0 else 0
                
                print(f"    Enhanced vs Standard: Time {time_pct:+.1f}%, Distance {dist_pct:+.1f}%")
                print(f"      Violations: Std={standard.capacity_violations}, Enh={enhanced.capacity_violations}")
            
            if standard and hier:
                time_diff = hier.execution_time_ms - standard.execution_time_ms
                time_pct = time_diff / standard.execution_time_ms * 100 if standard.execution_time_ms > 0 else 0
                dist_diff = hier.total_distance_km - standard.total_distance_km
                dist_pct = dist_diff / standard.total_distance_km * 100 if standard.total_distance_km > 0 else 0
                
                print(f"    Hierarchical vs Standard: Time {time_pct:+.1f}%, Distance {dist_pct:+.1f}%")
                print(f"      Violations: Std={standard.capacity_violations}, Hier={hier.capacity_violations}")


def main():
    """Main entry point."""
    
    print("\n" + "=" * 80)
    print("FCM CLUSTERING THRESHOLD BENCHMARK")
    print("=" * 80)
    print("""
This benchmark determines the optimal threshold for switching from
standard FCM to hierarchical FCM clustering using TSPLIB problems.

Problem Selection (3 per target size):
  ~50:  eil51 (51), berlin52 (52), eil76 (76)
  ~100: kroA100 (100), kroB100 (100), kroC100 (100)
  ~150: kroA150 (150), kroB150 (150), pr152 (152)
  ~200: kroA200 (200), kroB200 (200), ts225 (225)
  ~300: gil262 (262), pr299 (299), lin318 (318)
  ~500: rd400 (400), pr439 (439), d493 (493)

Strategies Compared:
  - fuzzy_cmeans: Basic FCM with hard assignment
  - fuzzy_cmeans_enhanced: FCM with border detection and transfer
  - hierarchical_fcm: Two-stage FCM (threshold=100)

Output: JSON file with detailed results
""")
    
    # Run benchmark
    run_threshold_benchmark(
        sw_capacity=4,
        so_capacity=5,
        n_runs=3
    )


if __name__ == "__main__":
    main()
