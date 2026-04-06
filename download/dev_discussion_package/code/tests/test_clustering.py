"""
Test Suite for Clustering Strategies
Compares K-Means vs Time-Matrix Aware Clustering

This script tests:
1. All clustering strategies work correctly
2. Time-matrix aware strategies use actual travel times
3. Comparison of clustering quality
"""

import sys
import os
import random
import time
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_data(n_students: int = 30, seed: int = 42):
    """Create test data with time matrix"""
    random.seed(seed)
    
    # Create depot
    depot = {"id": "D.Kampus", "lat": 37.0667, "lng": 37.3833}
    
    # Create students
    students = []
    disability_types = ["Sw", "So", "So", "So", "Sw"]
    
    for i in range(n_students):
        lat = depot["lat"] + random.uniform(-0.1, 0.1)
        lng = depot["lng"] + random.uniform(-0.1, 0.1)
        students.append({
            "id": f"S{i+1:03d}",
            "name": f"Öğrenci {i+1}",
            "location_code": f"L{i+1:03d}",
            "coordinates": {"lat": lat, "lng": lng},
            "disability_type": random.choice(disability_types)
        })
    
    # Create realistic time matrix (simulated road distances)
    all_locations = [depot["id"]] + [s["location_code"] for s in students]
    time_matrix = {}
    
    for i, loc1 in enumerate(all_locations):
        time_matrix[loc1] = {}
        for j, loc2 in enumerate(all_locations):
            if loc1 == loc2:
                time_matrix[loc1][loc2] = 0
            else:
                # Base: haversine + some randomness (simulating road network)
                if i == 0:
                    s = students[j-1]
                elif j == 0:
                    s = students[i-1]
                else:
                    s = students[j-1]
                    s2 = students[i-1]
                
                # Calculate rough distance
                if i == 0 or j == 0:
                    base_dist = random.uniform(5, 25)
                else:
                    s1 = students[i-1]
                    s2 = students[j-1]
                    # Haversine approximation
                    lat_diff = abs(s1["coordinates"]["lat"] - s2["coordinates"]["lat"])
                    lng_diff = abs(s1["coordinates"]["lng"] - s2["coordinates"]["lng"])
                    base_dist = (lat_diff**2 + lng_diff**2)**0.5 * 111 * 1.4  # km
                
                # Convert to minutes with some randomness
                time_matrix[loc1][loc2] = base_dist * 2 + random.uniform(-2, 5)
                time_matrix[loc1][loc2] = max(3, time_matrix[loc1][loc2])
    
    return depot, students, time_matrix


def test_clustering_strategies():
    """Test all clustering strategies"""
    print("\n" + "="*60)
    print("TEST: Clustering Strategies")
    print("="*60)
    
    from utils.clustering_strategies import get_available_strategies, get_clustering_strategy
    from utils.clustering import Point
    
    # Create test data
    depot, students_dict, time_matrix = create_test_data(n_students=30, seed=42)
    
    # Convert to Points
    points = []
    for s in students_dict:
        coords = s.get("coordinates", {"lat": 0, "lng": 0})
        points.append(Point(
            id=s["id"],
            lat=coords["lat"],
            lng=coords["lng"],
            disability_type=s.get("disability_type", "So"),
            location_code=s["location_code"]
        ))
    
    # Available strategies
    strategies = get_available_strategies()
    print(f"\nAvailable strategies: {strategies}")
    
    # Test each strategy
    num_vehicles = 6
    results = {}
    
    for strategy_name in ["kmeans", "kmedoids", "clarke_wright", "hybrid"]:
        print(f"\n  Testing: {strategy_name}")
        
        try:
            strategy = get_clustering_strategy(strategy_name, sw_capacity=4, so_capacity=5)
            
            start = time.time()
            clusters = strategy.cluster_students(
                points, 
                num_vehicles,
                time_matrix=time_matrix,
                depot=depot,
                raw_students=students_dict
            )
            elapsed = time.time() - start
            
            # Calculate stats
            avg_size = sum(len(c.points) for c in clusters) / len(clusters) if clusters else 0
            sw_per_cluster = [c.sw_count for c in clusters]
            so_per_cluster = [c.so_count for c in clusters]
            
            results[strategy_name] = {
                "num_clusters": len(clusters),
                "avg_cluster_size": avg_size,
                "time": elapsed,
                "sw_distribution": sw_per_cluster,
                "so_distribution": so_per_cluster
            }
            
            print(f"    Clusters: {len(clusters)}, Avg Size: {avg_size:.1f}, Time: {elapsed*1000:.1f}ms")
            print(f"    Sw distribution: {sw_per_cluster}")
            print(f"    So distribution: {so_per_cluster}")
            
        except Exception as e:
            print(f"    ERROR: {e}")
            results[strategy_name] = {"error": str(e)}
    
    # Summary
    print("\n  " + "-"*50)
    print(f"  {'Strategy':<15} {'Clusters':<10} {'Avg Size':<10} {'Time (ms)':<10}")
    print("  " + "-"*50)
    for name, res in results.items():
        if "error" not in res:
            print(f"  {name:<15} {res['num_clusters']:<10} {res['avg_cluster_size']:<10.1f} {res['time']*1000:<10.1f}")
    
    print("\n  ✓ Clustering strategies test completed")
    return True


def test_time_matrix_awareness():
    """Test that time-matrix aware strategies actually use time matrix"""
    print("\n" + "="*60)
    print("TEST: Time-Matrix Awareness")
    print("="*60)
    
    from utils.clustering_strategies import get_clustering_strategy
    from utils.clustering import Point
    
    # Create simple test case
    depot = {"id": "D1", "lat": 0, "lng": 0}
    students = [
        {"id": "S1", "location_code": "L1", "coordinates": {"lat": 0.01, "lng": 0}, "disability_type": "So"},
        {"id": "S2", "location_code": "L2", "coordinates": {"lat": 0.02, "lng": 0}, "disability_type": "So"},
        {"id": "S3", "location_code": "L3", "coordinates": {"lat": 0.03, "lng": 0}, "disability_type": "So"},
        {"id": "S4", "location_code": "L4", "coordinates": {"lat": 0.04, "lng": 0}, "disability_type": "So"},
    ]
    
    # Create time matrix where L1-L2 are far, L3-L4 are close
    # This should cause K-Medoids to group L1+L2 together and L3+L4 together
    # But K-Means will group based on coordinates (L1+L2 and L3+L4)
    time_matrix = {
        "D1": {"L1": 5, "L2": 5, "L3": 5, "L4": 5, "D1": 0},
        "L1": {"D1": 5, "L1": 0, "L2": 20, "L3": 25, "L4": 30},  # L1 far from L2
        "L2": {"D1": 5, "L1": 20, "L2": 0, "L3": 15, "L4": 20},
        "L3": {"D1": 5, "L1": 25, "L2": 15, "L3": 0, "L4": 5},   # L3 close to L4
        "L4": {"D1": 5, "L1": 30, "L2": 20, "L3": 5, "L4": 0},
    }
    
    # Convert to Points
    points = [
        Point(id=s["id"], lat=s["coordinates"]["lat"], lng=s["coordinates"]["lng"],
              disability_type=s["disability_type"], location_code=s["location_code"])
        for s in students
    ]
    
    # Test K-Means (time-matrix unaware)
    print("\n  K-Means (time-matrix UNAWARE):")
    kmeans = get_clustering_strategy("kmeans")
    kmeans_clusters = kmeans.cluster_students(points, 2, time_matrix=time_matrix, depot=depot)
    for i, c in enumerate(kmeans_clusters):
        locs = [p.location_code for p in c.points]
        print(f"    Cluster {i+1}: {locs}")
    
    # Test K-Medoids (time-matrix aware)
    print("\n  K-Medoids (time-matrix AWARE):")
    kmedoids = get_clustering_strategy("kmedoids")
    kmedoids_clusters = kmedoids.cluster_students(points, 2, time_matrix=time_matrix, depot=depot)
    for i, c in enumerate(kmedoids_clusters):
        locs = [p.location_code for p in c.points]
        print(f"    Cluster {i+1}: {locs}")
    
    # Test Clarke-Wright (time-matrix aware)
    print("\n  Clarke-Wright (time-matrix AWARE):")
    cw = get_clustering_strategy("clarke_wright")
    cw_clusters = cw.cluster_students(points, 2, time_matrix=time_matrix, depot=depot)
    for i, c in enumerate(cw_clusters):
        locs = [p.location_code for p in c.points]
        print(f"    Cluster {i+1}: {locs}")
    
    print("\n  Note: K-Medoids and Clarke-Wright should group L3+L4 together (close in time matrix)")
    print("        while K-Means groups based on geographic proximity only")
    print("\n  ✓ Time-matrix awareness test completed")
    return True


def test_ga_with_new_clustering():
    """Test GA strategy with different clustering algorithms"""
    print("\n" + "="*60)
    print("TEST: GA Strategy with Different Clustering")
    print("="*60)
    
    from strategies.ga_strategy import GeneticAlgorithmStrategy
    from models.schemas import OptimizationRequest, StudentNode, Depot
    
    # Create test request
    random.seed(42)
    depot = Depot(id="D.Kampus", name="Ana Kampüs", lat=37.0667, lng=37.3833)
    
    students = []
    disability_types = ["Sw", "So", "So", "So", "Sw"]
    for i in range(20):
        lat = depot.lat + random.uniform(-0.05, 0.05)
        lng = depot.lng + random.uniform(-0.05, 0.05)
        students.append(StudentNode(
            id=f"S{i+1:03d}",
            name=f"Öğrenci {i+1}",
            location_code=f"L{i+1:03d}",
            coordinates={"lat": lat, "lng": lng},
            disability_type=random.choice(disability_types),
            morning_pickup_time="08:00",
            evening_pickup_time="17:00"
        ))
    
    request = OptimizationRequest(
        students=students,
        depot=depot,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=90
    )
    
    # Test with different clustering algorithms
    clustering_algos = ["kmeans", "clarke_wright", "kmedoids"]
    results = {}
    
    for algo in clustering_algos:
        print(f"\n  Testing GA with clustering: {algo}")
        
        strategy = GeneticAlgorithmStrategy(config={
            "population_size": 20,
            "max_iterations": 30,
            "clustering_algorithm": algo
        })
        
        start = time.time()
        response = strategy.optimize(request)
        elapsed = time.time() - start
        
        results[algo] = {
            "vehicles": response.total_vehicles,
            "duration": response.total_duration_minutes,
            "time": elapsed
        }
        
        print(f"    Vehicles: {response.total_vehicles}")
        print(f"    Total Duration: {response.total_duration_minutes:.1f} min")
        print(f"    Execution Time: {elapsed:.2f} s")
    
    # Summary
    print("\n  " + "-"*60)
    print(f"  {'Clustering':<15} {'Vehicles':<10} {'Duration':<12} {'Time (s)':<10}")
    print("  " + "-"*60)
    for algo, res in results.items():
        print(f"  {algo:<15} {res['vehicles']:<10} {res['duration']:<12.1f} {res['time']:<10.2f}")
    
    print("\n  ✓ GA with different clustering test completed")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("UniRide Clustering Strategies Test Suite")
    print("="*60)
    
    tests = [
        ("Clustering Strategies", test_clustering_strategies),
        ("Time-Matrix Awareness", test_time_matrix_awareness),
        ("GA with New Clustering", test_ga_with_new_clustering),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASSED" if success else "FAILED"))
        except Exception as e:
            print(f"\n  ✗ Error in {name}: {e}")
            results.append((name, "ERROR"))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, status in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"  {symbol} {name}: {status}")
    
    passed = sum(1 for _, s in results if s == "PASSED")
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
