"""
Test script for GWO Strategy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schemas import OptimizationRequest, StudentNode, LocationNode
from strategies.gwo_strategy import GWOStrategy


def test_gwo_basic():
    """Test GWO with basic data"""
    print("=" * 60)
    print("GWO Strategy Test")
    print("=" * 60)
    
    # Create test depot
    depot = LocationNode(
        id="D.Kampus",
        lat=37.0667,
        lng=37.3833,
        type="Depot"
    )
    
    # Create test students
    students = [
        StudentNode(id="S1", name="Ahmet", location_code="Sw1", 
                   coordinates={"lat": 37.07, "lng": 37.39}, disability_type="Sw"),
        StudentNode(id="S2", name="Mehmet", location_code="Sw2", 
                   coordinates={"lat": 37.08, "lng": 37.40}, disability_type="Sw"),
        StudentNode(id="S3", name="Ayşe", location_code="So1", 
                   coordinates={"lat": 37.09, "lng": 37.41}, disability_type="So"),
        StudentNode(id="S4", name="Fatma", location_code="So2", 
                   coordinates={"lat": 37.10, "lng": 37.42}, disability_type="So"),
        StudentNode(id="S5", name="Ali", location_code="So3", 
                   coordinates={"lat": 37.11, "lng": 37.43}, disability_type="So"),
    ]
    
    # Create request
    request = OptimizationRequest(
        algorithm="gwo",
        students=students,
        depot=depot,
        max_travel_time=120,
        sw_capacity=4,
        so_capacity=5,
        gwo_config={
            "population_size": 20,
            "max_iterations": 50,
            "seed": 42
        }
    )
    
    # Initialize strategy
    strategy = GWOStrategy()
    
    print(f"\nAlgorithm: {strategy.display_name}")
    print(f"Description: {strategy.description}")
    print(f"Config: {strategy.config}")
    
    # Run optimization
    print("\nRunning optimization...")
    result = strategy.optimize(request)
    
    print("\n" + "-" * 40)
    print("Results:")
    print("-" * 40)
    print(f"Algorithm Used: {result.algorithm_used}")
    print(f"Success: {result.success}")
    print(f"Total Vehicles: {result.total_vehicles}")
    print(f"Total Duration: {result.total_duration_minutes:.2f} minutes")
    print(f"Execution Time: {result.execution_time_seconds:.4f} seconds")
    
    print("\nRoutes:")
    for route in result.routes:
        print(f"\n  {route.vehicle_id}:")
        print(f"    Duration: {route.total_duration_minutes:.2f} min")
        print(f"    SW: {route.sw_count}, SO: {route.so_count}")
        print(f"    Students: {route.student_ids}")
        print(f"    Steps: {len(route.route_details)}")
    
    return result


def test_gwo_small():
    """Test GWO with very small instance"""
    print("\n" + "=" * 60)
    print("GWO Small Instance Test (2 students)")
    print("=" * 60)
    
    depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
    
    students = [
        StudentNode(id="S1", name="Test1", location_code="L1", 
                   coordinates={"lat": 37.07, "lng": 37.39}, disability_type="So"),
        StudentNode(id="S2", name="Test2", location_code="L2", 
                   coordinates={"lat": 37.08, "lng": 37.40}, disability_type="So"),
    ]
    
    request = OptimizationRequest(
        algorithm="gwo",
        students=students,
        depot=depot
    )
    
    strategy = GWOStrategy()
    result = strategy.optimize(request)
    
    print(f"Success: {result.success}")
    print(f"Total Vehicles: {result.total_vehicles}")
    print(f"Total Duration: {result.total_duration_minutes:.2f} min")
    
    return result


def test_gwo_empty():
    """Test GWO with no students"""
    print("\n" + "=" * 60)
    print("GWO Empty Test (no students)")
    print("=" * 60)
    
    depot = LocationNode(id="D.Kampus", lat=37.0667, lng=37.3833, type="Depot")
    
    request = OptimizationRequest(
        algorithm="gwo",
        students=[],
        depot=depot
    )
    
    strategy = GWOStrategy()
    result = strategy.optimize(request)
    
    print(f"Success: {result.success}")
    print(f"Total Vehicles: {result.total_vehicles}")
    
    return result


if __name__ == "__main__":
    try:
        # Run all tests
        test_gwo_empty()
        test_gwo_small()
        result = test_gwo_basic()
        
        print("\n" + "=" * 60)
        print("✅ All GWO tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
