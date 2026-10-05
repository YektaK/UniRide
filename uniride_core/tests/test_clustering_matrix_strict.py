"""k-medoids and Clarke-Wright cluster on the authoritative matrix, never haversine.

Owner requirement 2026-10-05: all operational travel times come from the stored
``time_matrix``. A missing pair is an error (``MissingTravelTimeError``); there
is no haversine stand-in.
"""

import pytest

from uniride_core.algorithms.clustering import (
    MissingTravelTimeError,
    Point,
    matrix_travel_time,
)
from uniride_core.algorithms.clustering_strategies import get_clustering_strategy
from uniride_core.algorithms.clustering_strategies import k_medoids
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator


def _point(pid, code, lat=41.0, lng=29.0, kind="So"):
    return Point(id=pid, lat=lat, lng=lng, disability_type=kind, location_code=code)


DEPOT = {"id": "D", "lat": 41.0, "lng": 29.0}


def _matrix(arcs, codes=("D", "A", "B", "C", "E"), default=20.0):
    """Directed matrix keyed by location code; ``arcs`` overrides (origin, dest)."""
    out = {a: {b: (0.0 if a == b else default) for b in codes} for a in codes}
    for (a, b), value in arcs.items():
        out[a][b] = value
    return out


def test_matrix_travel_time_is_directed_and_strict():
    matrix = _matrix({("A", "B"): 1.0, ("B", "A"): 9.0})
    a, b = _point("1", "A"), _point("2", "B")
    assert matrix_travel_time(a, b, matrix) == 1.0
    assert matrix_travel_time(b, a, matrix) == 9.0
    # students at one stop are 0 apart
    assert matrix_travel_time(_point("3", "A"), a, {}) == 0.0
    with pytest.raises(MissingTravelTimeError):
        matrix_travel_time(a, _point("4", "Z"), matrix)
    with pytest.raises(MissingTravelTimeError):
        matrix_travel_time(a, b, {})


def _clarke_wright_groups(matrix):
    # identical coordinates: a haversine stand-in would see every pair as equal
    points = [_point(str(i), code) for i, code in enumerate("ABCE", start=1)]
    strategy = get_clustering_strategy("clarke_wright", 10, 10)
    clusters = strategy.cluster_students(
        points, 2, time_matrix=matrix, depot=DEPOT
    )
    return sorted(sorted(p.location_code for p in c.points) for c in clusters)


def test_clarke_wright_uses_the_directed_matrix_values():
    # savings S(i, j) = t(D, i) + t(D, j) - t(i, j) with i before j in the list
    cheap_ab = _matrix({("A", "B"): 1.0, ("C", "E"): 1.0}, default=10.0)
    assert _clarke_wright_groups(cheap_ab) == [["A", "B"], ["C", "E"]]

    # the same pair is expensive in the listed direction (cheap only reversed)
    reversed_ab = _matrix(
        {("A", "B"): 99.0, ("B", "A"): 1.0, ("C", "E"): 1.0}, default=10.0
    )
    assert _clarke_wright_groups(reversed_ab) != [["A", "B"], ["C", "E"]]


def test_clarke_wright_missing_pair_raises_instead_of_haversine():
    matrix = _matrix({}, codes=("D", "A", "B", "C"))  # "E" is missing
    points = [_point(str(i), code) for i, code in enumerate("ABCE", start=1)]
    strategy = get_clustering_strategy("clarke_wright", 10, 10)
    with pytest.raises(MissingTravelTimeError):
        strategy.cluster_students(points, 2, time_matrix=matrix, depot=DEPOT)


def test_clarke_wright_without_any_matrix_raises():
    points = [_point("1", "A"), _point("2", "B")]
    strategy = get_clustering_strategy("clarke_wright", 10, 10)
    with pytest.raises(MissingTravelTimeError):
        strategy.cluster_students(points, 1, depot=DEPOT)


def test_k_medoids_assigns_by_directed_matrix_time(monkeypatch):
    # A and B share coordinates, C is far away: haversine would put B with A.
    a = _point("1", "A", lat=41.0, lng=29.0)
    b = _point("2", "B", lat=41.0, lng=29.0)
    c = _point("3", "C", lat=42.0, lng=30.0)
    matrix = _matrix({("A", "B"): 100.0, ("C", "B"): 1.0}, codes=("A", "B", "C"))
    monkeypatch.setattr(k_medoids, "initialize_medoids", lambda points, k: [a, c])

    clusters = k_medoids.k_medoids_clustering_core([a, b, c], 2, matrix)

    groups = sorted(sorted(p.location_code for p in cl.points) for cl in clusters)
    assert groups == [["A"], ["B", "C"]]


def test_k_medoids_missing_pair_raises_instead_of_haversine():
    points = [_point("1", "A"), _point("2", "B"), _point("3", "C")]
    matrix = _matrix({}, codes=("A", "B"))  # "C" is missing
    strategy = get_clustering_strategy("k_medoids", 10, 10)
    with pytest.raises(MissingTravelTimeError):
        strategy.cluster_students(points, 2, time_matrix=matrix)


def test_vehicle_calculator_hands_the_matrix_and_depot_to_clustering():
    students = [
        {"id": str(i), "name": code, "location_code": code,
         "coordinates": {"lat": 41.0, "lng": 29.0}, "disability_type": "So"}
        for i, code in enumerate("ABCE", start=1)
    ]
    calculator = VehicleCalculator(
        sw_capacity=10, so_capacity=2, clustering_algorithm="clarke_wright"
    )
    matrix = _matrix({("A", "B"): 1.0, ("C", "E"): 1.0}, default=10.0)

    result = calculator.calculate(students, None, time_matrix=matrix, depot=DEPOT)

    groups = sorted(
        sorted(s["location_code"] for s in a["students"]) for a in result["assignments"]
    )
    assert groups == [["A", "B"], ["C", "E"]]

    with pytest.raises(MissingTravelTimeError):
        calculator.calculate(students, None)  # no matrix: no haversine stand-in
