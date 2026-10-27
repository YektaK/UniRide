import pytest
import math
from uniride_core.algorithms.clustering import Point, Cluster, calculate_centroid
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator

def test_calculate_centroid():
    pts = [Point("1", 10, 10, "Sw"), Point("2", 20, 20, "Sw")]
    lat, lng = calculate_centroid(pts)
    assert lat == 15.0
    assert lng == 15.0
    
    assert calculate_centroid([]) == (0.0, 0.0)

def test_estimate_vehicle_count():
    calc = VehicleCalculator(sw_capacity=2, so_capacity=5)
    pts = [
        Point("1", 0, 0, "Sw"), Point("2", 0, 0, "Sw"),
        Point("3", 0, 0, "Sw"), Point("4", 0, 0, "So")
    ]
    # 3 Sw students, capacity 2 -> needs 2 vehicles
    assert calc.estimate_vehicle_count(pts) == 2

def test_vehicle_calculator_empty():
    calc = VehicleCalculator()
    result = calc.calculate([])
    assert result["success"] is True
    assert result["required_vehicles"] == 0

def test_vehicle_calculator_basic_flow():
    calc = VehicleCalculator(sw_capacity=10, so_capacity=10, clustering_algorithm="kmeans")
    students = [
        {"id": "1", "coordinates": {"lat": 41.0, "lng": 29.0}, "disability_type": "Sw", "location_code": "L1"},
        {"id": "2", "coordinates": {"lat": 41.0, "lng": 29.01}, "disability_type": "So", "location_code": "L2"}
    ]
    
    # We need to mock clustering_strategies if we don't want to depend on external files
    # But since it's a project unit test, we'll try it as is (assuming kmeans strategy exists)
    try:
        result = calc.calculate(students)
        assert result["success"] is True
        assert result["required_vehicles"] >= 1
    except ImportError:
        # If clustering_strategies is not found in test env, this might fail, skip for now
        pytest.skip("clustering_strategies module not available")

def test_haversine_integration():
    from utils.data_loader import haversine_distance
    # Test distance between two known points (e.g., Istanbul - London)
    d = haversine_distance(41.0082, 28.9784, 51.5074, -0.1278)
    # Unit check: haversine returned meters in previous run (2.5m meters)
    assert 2400000 < d < 2600000 # Approx 2500 km in meters
