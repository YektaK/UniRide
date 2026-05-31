import math

from uniride_core.algorithms.distance import (
    estimate_travel_time,
    euclidean_distance_2d,
    haversine_distance,
)
from utils.data_loader import DataLoader, euclidean_distance


def test_data_loader_euclidean_matrix_uses_core_distance_helper():
    locations = ["A", "B"]
    coordinates = {
        "A": {"lat": 0.0, "lng": 0.0},
        "B": {"lat": 3.0, "lng": 4.0},
    }

    matrix = DataLoader.build_euclidean_matrix(locations, coordinates)

    assert matrix[0][1] == euclidean_distance_2d((0.0, 0.0), (3.0, 4.0))
    assert matrix[1][0] == matrix[0][1]


def test_data_loader_haversine_matrix_uses_core_distance_and_travel_time():
    locations = ["A", "B"]
    coordinates = {
        "A": {"lat": 41.0, "lng": 29.0},
        "B": {"lat": 41.01, "lng": 29.01},
    }

    matrix = DataLoader.build_haversine_matrix(locations, coordinates, avg_speed_kmh=40.0)
    expected = estimate_travel_time(
        haversine_distance(41.0, 29.0, 41.01, 29.01),
        avg_speed_kmh=40.0,
    )

    assert math.isclose(matrix[0][1], expected)
    assert matrix[1][0] == matrix[0][1]


def test_legacy_euclidean_distance_wrapper_delegates_to_core_helper():
    assert euclidean_distance(0.0, 0.0, 6.0, 8.0) == euclidean_distance_2d(
        (0.0, 0.0),
        (6.0, 8.0),
    )
