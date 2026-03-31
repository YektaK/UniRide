"""
Test Suite for UniRide Optimizer API
Tests all optimization strategies independently
"""

import sys
import os
import time
import json
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    LocationNode, StudentNode, VehicleRoute
)


def create_test_students(n: int = 10) -> List[StudentNode]:
    """Create test student data"""
    students = []

    # Sample location codes around Düzce University
    locations = [
        ("Sw1", "Sw", 40.8412, 31.1456),
        ("Sw2", "Sw", 40.8398, 31.1489),
        ("Sw3", "Sw", 40.8425, 31.1512),
        ("Sw4", "Sw", 40.8378, 31.1434),
        ("So1", "So", 40.8401, 31.1501),
        ("So2", "So", 40.8389, 31.1467),
        ("So3", "So", 40.8418, 31.1523),
        ("So4", "So", 40.8395, 31.1445),
        ("So5", "So", 40.8432, 31.1478),
        ("So6", "So", 40.8382, 31.1498),
        ("Sw5", "Sw", 40.8408, 31.1432),
        ("So7", "So", 40.8421, 31.1489),
    ]

    for i in range(min(n, len(locations))):
        loc_code, dis_type, lat, lng = locations[i]
        students.append(StudentNode(
            id=f"student_{i+1}",
            name=f"Öğrenci {i+1}",
            location_code=loc_code,
            coordinates={"lat": lat, "lng": lng},
            disability_type=dis_type
        ))

    return students


def create_depot() -> LocationNode:
    """Create depot location (D.Kampus)"""
    return LocationNode(
        id="D.Kampus",
        lat=40.8410,
        lng=31.1478,
        type="depot"
    )


def print_route(route: VehicleRoute):
    """Pretty print a vehicle route"""
    print(f"\n  {route.vehicle_id}:")
    print(f"    Toplam Süre: {route.total_duration_minutes:.1f} dk")
    print(f"    Sw: {route.sw_count}, So: {route.so_count}")
    print(f"    Öğrenci Sayısı: {len(route.student_ids)}")
    print(f"    Rota: ", end="")
    for step in route.route_details:
        print(f"{step.location1}→{step.location2}", end=" ")
    print()


def test_ga_strategy():
    """Test Genetic Algorithm Strategy"""
    print("\n" + "="*60)
    print("TESTING: Genetic Algorithm Strategy")
    print("="*60)

    from strategies.ga_strategy import GeneticAlgorithmStrategy

    strategy = GeneticAlgorithmStrategy()
    students = create_test_students(8)
    depot = create_depot()

    request = OptimizationRequest(
        algorithm="genetic_algorithm",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5,
        ga_config={
            "population_size": 30,
            "max_iterations": 50
        }
    )

    print(f"\nÖğrenci Sayısı: {len(students)}")
    print(f"Sw: {sum(1 for s in students if s.disability_type == 'Sw')}")
    print(f"So: {sum(1 for s in students if s.disability_type == 'So')}")

    start_time = time.time()
    result = strategy.optimize(request)
    elapsed = time.time() - start_time

    print(f"\nSonuç:")
    print(f"  Başarılı: {result.success}")
    print(f"  Toplam Araç: {result.total_vehicles}")
    print(f"  Toplam Süre: {result.total_duration_minutes:.1f} dk")
    print(f"  Çalışma Süresi: {elapsed:.3f} saniye")

    for route in result.routes:
        print_route(route)

    return result


def test_pso_strategy():
    """Test PSO Strategy"""
    print("\n" + "="*60)
    print("TESTING: PSO Strategy")
    print("="*60)

    from strategies.pso_strategy import PSOStrategy

    strategy = PSOStrategy()
    students = create_test_students(8)
    depot = create_depot()

    request = OptimizationRequest(
        algorithm="pso",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5,
        pso_config={
            "swarm_size": 20,
            "max_iterations": 50
        }
    )

    print(f"\nÖğrenci Sayısı: {len(students)}")

    start_time = time.time()
    result = strategy.optimize(request)
    elapsed = time.time() - start_time

    print(f"\nSonuç:")
    print(f"  Başarılı: {result.success}")
    print(f"  Toplam Araç: {result.total_vehicles}")
    print(f"  Toplam Süre: {result.total_duration_minutes:.1f} dk")
    print(f"  Çalışma Süresi: {elapsed:.3f} saniye")

    for route in result.routes:
        print_route(route)

    return result


def test_greedy_strategy():
    """Test Greedy Strategy"""
    print("\n" + "="*60)
    print("TESTING: Greedy Strategy")
    print("="*60)

    from strategies.greedy_heuristic import GreedyHeuristicStrategy

    strategy = GreedyHeuristicStrategy()
    students = create_test_students(8)
    depot = create_depot()

    request = OptimizationRequest(
        algorithm="greedy",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5
    )

    start_time = time.time()
    result = strategy.optimize(request)
    elapsed = time.time() - start_time

    print(f"\nSonuç:")
    print(f"  Başarılı: {result.success}")
    print(f"  Toplam Araç: {result.total_vehicles}")
    print(f"  Toplam Süre: {result.total_duration_minutes:.1f} dk")
    print(f"  Çalışma Süresi: {elapsed:.3f} saniye")

    for route in result.routes:
        print_route(route)

    return result


def test_permutation_strategy():
    """Test Permutation TSP Strategy"""
    print("\n" + "="*60)
    print("TESTING: Permutation TSP Strategy (Optimal for n≤10)")
    print("="*60)

    from strategies.permutation_tsp import PermutationTSPStrategy

    strategy = PermutationTSPStrategy()
    students = create_test_students(6)  # Small for permutation
    depot = create_depot()

    request = OptimizationRequest(
        algorithm="permutation_tsp",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5
    )

    start_time = time.time()
    result = strategy.optimize(request)
    elapsed = time.time() - start_time

    print(f"\nSonuç:")
    print(f"  Başarılı: {result.success}")
    print(f"  Toplam Araç: {result.total_vehicles}")
    print(f"  Toplam Süre: {result.total_duration_minutes:.1f} dk")
    print(f"  Çalışma Süresi: {elapsed:.3f} saniye")

    for route in result.routes:
        print_route(route)

    return result


def compare_all_strategies():
    """Compare all strategies on the same problem"""
    print("\n" + "="*60)
    print("COMPARING ALL STRATEGIES")
    print("="*60)

    from strategies import STRATEGY_REGISTRY

    students = create_test_students(8)
    depot = create_depot()

    print(f"\nTest Verisi:")
    print(f"  Öğrenci Sayısı: {len(students)}")
    print(f"  Sw: {sum(1 for s in students if s.disability_type == 'Sw')}")
    print(f"  So: {sum(1 for s in students if s.disability_type == 'So')}")

    results = {}

    # Test each unique strategy
    tested = set()
    for name, strategy in STRATEGY_REGISTRY.items():
        if strategy.name in tested:
            continue
        tested.add(strategy.name)

        request = OptimizationRequest(
            algorithm=strategy.name,
            students=students,
            depot=depot,
            max_travel_time=120,
            sw_capacity=4,
            so_capacity=5
        )

        try:
            start_time = time.time()
            result = strategy.optimize(request)
            elapsed = time.time() - start_time

            results[strategy.name] = {
                "success": result.success,
                "vehicles": result.total_vehicles,
                "duration": result.total_duration_minutes,
                "time": elapsed,
                "error": result.error_message
            }
        except Exception as e:
            results[strategy.name] = {
                "success": False,
                "vehicles": 0,
                "duration": 0,
                "time": 0,
                "error": str(e)
            }

    # Print comparison table
    print("\n" + "-"*80)
    print(f"{'Algoritma':<25} {'Araç':<8} {'Süre (dk)':<12} {'Zaman (sn)':<12} {'Durum':<10}")
    print("-"*80)

    for name, r in results.items():
        status = "BASARILI" if r["success"] else "HATA"
        duration = f"{r['duration']:.1f}" if r["success"] else "-"
        time_str = f"{r['time']:.3f}" if r["success"] else "-"
        vehicles = str(r["vehicles"]) if r["success"] else "-"
        print(f"{name:<25} {vehicles:<8} {duration:<12} {time_str:<12} {status:<10}")

    print("-"*80)

    # Find best
    successful = {k: v for k, v in results.items() if v["success"]}
    if successful:
        best_duration = min(successful.items(), key=lambda x: x[1]["duration"])
        fastest = min(successful.items(), key=lambda x: x[1]["time"])

        print(f"\nEn Kısa Rota: {best_duration[0]} ({best_duration[1]['duration']:.1f} dk)")
        print(f"En Hızlı Algoritma: {fastest[0]} ({fastest[1]['time']:.3f} sn)")

    return results


def test_vehicle_calculator():
    """Test K-Means clustering and vehicle assignment"""
    print("\n" + "="*60)
    print("TESTING: Vehicle Calculator (K-Means Clustering)")
    print("="*60)

    from utils.clustering import VehicleCalculator, Point

    students = []
    for i, s in enumerate(create_test_students(12)):
        coords = s.coordinates or {"lat": 0, "lng": 0}
        students.append({
            "id": s.id,
            "name": s.name,
            "location_code": s.location_code,
            "coordinates": coords,
            "disability_type": s.disability_type
        })

    calculator = VehicleCalculator(
        sw_capacity=4,
        so_capacity=5,
        max_tour_time=120
    )

    print(f"\nÖğrenci Sayısı: {len(students)}")

    result = calculator.calculate(students)

    print(f"\nSonuç:")
    print(f"  Başarılı: {result['success']}")
    print(f"  Gerekli Araç: {result['required_vehicles']}")
    print(f"  Toplam Süre: {result['total_duration']:.1f} dk")
    print(f"  Mesaj: {result['message']}")

    print(f"\nAraç Atamaları:")
    for a in result["assignments"]:
        print(f"  Araç {a['vehicle_index']}: {len(a['students'])} öğrenci, "
              f"Sw: {a['sw_count']}, So: {a['so_count']}, "
              f"Süre: {a['total_duration']:.1f} dk")

    return result


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UniRide Optimizer API - Test Suite")
    print("="*60)

    try:
        # Test individual strategies
        test_greedy_strategy()
        test_permutation_strategy()
        test_ga_strategy()
        test_pso_strategy()

        # Test vehicle calculator
        test_vehicle_calculator()

        # Compare all
        compare_all_strategies()

        print("\n" + "="*60)
        print("TÜM TESTLER TAMAMLANDI")
        print("="*60)

    except Exception as e:
        import traceback
        print(f"\nTEST HATASI: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
