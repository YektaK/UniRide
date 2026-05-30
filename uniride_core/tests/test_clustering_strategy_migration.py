from uniride_core.algorithms.clustering import Point
from uniride_core.algorithms.clustering_strategies import (
    ClarkeWrightClusteringStrategy,
    FuzzyCMeansClusteringStrategy,
    KMeansClusteringStrategy,
    KMedoidsClusteringStrategy,
    SweepClusteringStrategy,
    get_clustering_strategy,
)
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator


def _points():
    return [
        Point("s1", 40.0, 29.0, "Sw", "A"),
        Point("s2", 40.001, 29.001, "So", "B"),
        Point("s3", 40.002, 29.002, "So", "C"),
        Point("s4", 40.003, 29.003, "Sw", "D"),
    ]


def test_core_clustering_strategy_factory_exports_all_families():
    assert isinstance(get_clustering_strategy("kmeans"), KMeansClusteringStrategy)
    assert isinstance(get_clustering_strategy("fuzzy_cmeans"), FuzzyCMeansClusteringStrategy)
    assert isinstance(get_clustering_strategy("k_medoids"), KMedoidsClusteringStrategy)
    assert isinstance(get_clustering_strategy("sweep"), SweepClusteringStrategy)
    assert isinstance(get_clustering_strategy("clarke_wright"), ClarkeWrightClusteringStrategy)


def test_core_vehicle_calculator_assigns_students_with_sweep():
    students = [
        {
            "id": point.id,
            "location_code": point.location_code,
            "coordinates": {"lat": point.lat, "lng": point.lng},
            "disability_type": point.disability_type,
        }
        for point in _points()
    ]
    result = VehicleCalculator(
        sw_capacity=1,
        so_capacity=2,
        max_tour_time=60,
        clustering_algorithm="sweep",
    ).calculate(students)

    assert result["success"] is True
    assert result["required_vehicles"] >= 2
    assert sum(len(assignment["students"]) for assignment in result["assignments"]) == len(students)
