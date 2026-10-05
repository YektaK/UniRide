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
    # directed savings S(i -> j) = t(i, D) + t(D, j) - t(i, j)
    cheap_ab = _matrix({("A", "B"): 1.0, ("C", "E"): 1.0}, default=10.0)
    assert _clarke_wright_groups(cheap_ab) == [["A", "B"], ["C", "E"]]

    # cheap only in the reverse direction: the better orientation (B -> A) is
    # used, so the same pair is still found
    reversed_ab = _matrix(
        {("A", "B"): 99.0, ("B", "A"): 1.0, ("C", "E"): 1.0}, default=10.0
    )
    assert _clarke_wright_groups(reversed_ab) == [["A", "B"], ["C", "E"]]


def _tour_cost(points, matrix, depot="D"):
    codes = [depot] + [p.location_code for p in points] + [depot]
    return sum(matrix[a][b] for a, b in zip(codes, codes[1:]))


def test_clarke_wright_directed_saving_beats_one_way_saving():
    # D->x = 10 and x->D = 10 for all x. A->B is cheap (9) but B->A is dear (30);
    # C->A is very cheap (1) while A->C costs 15. The old one-way saving
    # t(D,i)+t(D,j)-t(i,j) (i before j in list order) ranks (A,B)=11 first and
    # merges A->B (total 49); the directed saving S(C->A) = 10+10-1 = 19 wins
    # and gives D->C->A->D + D->B->D = 41.
    matrix = _matrix(
        {
            ("A", "B"): 9.0, ("B", "A"): 30.0,
            ("A", "C"): 15.0, ("C", "A"): 1.0,
            ("B", "C"): 20.0, ("C", "B"): 20.0,
        },
        codes=("D", "A", "B", "C"),
        default=10.0,
    )
    points = [_point("1", "A"), _point("2", "B"), _point("3", "C")]
    strategy = get_clustering_strategy("clarke_wright", 10, 10)
    clusters = strategy.cluster_students(points, 2, time_matrix=matrix, depot=DEPOT)

    groups = sorted([p.location_code for p in c.points] for c in clusters)
    assert groups == [["B"], ["C", "A"]]  # route order is C then A
    total = sum(_tour_cost(c.points, matrix) for c in clusters)
    assert total == 41.0
    one_way_choice = [[points[0], points[1]], [points[2]]]
    assert total < sum(_tour_cost(r, matrix) for r in one_way_choice)


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


def _sweep_groups(depot):
    corners = {"P1": (1.0, 1.0), "P2": (1.0, -1.0), "P3": (-1.0, -1.0), "P4": (-1.0, 1.0)}
    points = [
        _point(name, name, lat=lat, lng=lng) for name, (lat, lng) in corners.items()
    ]
    strategy = get_clustering_strategy("sweep", 10, 10)
    kwargs = {} if depot is None else {"depot": depot}
    clusters = strategy.cluster_students(points, 2, **kwargs)
    return sorted(sorted(p.id for p in c.points) for c in clusters)


def test_sweep_pivots_around_the_passed_depot():
    # depot at the origin: polar order P3, P4, P1, P2
    assert _sweep_groups({"id": "D", "lat": 0.0, "lng": 0.0}) == [
        ["P1", "P2"],
        ["P3", "P4"],
    ]
    # depot far north: every point lies south of it, polar order P2, P3, P4, P1
    assert _sweep_groups({"id": "D", "lat": 5.0, "lng": 0.0}) == [
        ["P1", "P4"],
        ["P2", "P3"],
    ]
    # without a depot the historical Dudullu pivot (41.001, 29.177) is used
    assert _sweep_groups(None) == _sweep_groups(
        {"id": "D", "lat": 41.001, "lng": 29.177}
    )
