"""
Distance calculation utilities — Single source of truth.

Consolidates all distance functions that were previously duplicated across:
  - legacy API haversine helpers
  - legacy API data loading helpers
  - uniride_core/algorithms/tsplib_parser.py
  - uniride_core/algorithms/numba_utils.py (create_np_distance_matrix)
  - uniride_core/algorithms/sota_tsp/base_solver.py (static euclidean_distance)

Usage:
    from uniride_core.algorithms.distance import (
        haversine_distance,
        euclidean_distance_2d,
        tsplib_euc_2d_distance,
        tsplib_ceil_2d_distance,
        tsplib_att_distance,
        tsplib_geo_distance,
        tsplib_distance_by_type,
        estimate_travel_time,
        create_np_distance_matrix,
    )
"""

import math
from typing import List, Tuple

__all__ = [
    "haversine_distance",
    "euclidean_distance_2d",
    "tsplib_euc_2d_distance",
    "tsplib_ceil_2d_distance",
    "tsplib_att_distance",
    "tsplib_geo_distance",
    "tsplib_distance_by_type",
    "estimate_travel_time",
    "create_np_distance_matrix",
]


# ── Haversine (real-world geographic) ────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two geographic points in meters.

    Use this for real-world lat/lng coordinates, NOT for TSPLIB abstract X-Y.
    """
    R = 6371000  # Earth radius in meters
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ── Euclidean (abstract coordinates) ─────────────────────────────────────────

def euclidean_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Raw Euclidean distance between two 2D points (abstract coordinates)."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# ── TSPLIB distance functions ─────────────────────────────────────────────────

def tsplib_euc_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB EUC_2D: NINT(Euclidean distance) — rounds to nearest integer."""
    return int(round(euclidean_distance_2d(p1, p2)))


def tsplib_ceil_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB CEIL_2D: ceiling of Euclidean distance."""
    return int(math.ceil(euclidean_distance_2d(p1, p2) - 1e-9))


def tsplib_att_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB ATT: pseudo-Euclidean distance for ATT TSP instances."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    rij = math.sqrt((dx * dx + dy * dy) / 10.0)
    tij = int(round(rij))
    if tij < rij:
        return tij + 1
    return tij


def tsplib_geo_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB GEO: great-circle distance on a sphere (lat/lng in degrees)."""
    from math import pi, cos, sin, acos, floor

    def to_rad(deg: float) -> float:
        return deg * pi / 180.0

    lat1, lon1 = to_rad(p1[0]), to_rad(p1[1])
    lat2, lon2 = to_rad(p2[0]), to_rad(p2[1])
    q1 = cos(lon1 - lon2)
    q2 = cos(lat1 - lat2)
    q3 = cos(lat1 + lat2)
    d = acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1e-9
    return int(floor(d))


def tsplib_distance_by_type(
    edge_weight_type: str,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
) -> int:
    """Dispatch to the correct TSPLIB distance function by type."""
    dispatch = {
        "EUC_2D": tsplib_euc_2d_distance,
        "EUC_3D": tsplib_euc_2d_distance,  # simplified; 3D variant omitted
        "CEIL_2D": tsplib_ceil_2d_distance,
        "ATT": tsplib_att_distance,
        "GEO": tsplib_geo_distance,
        "GEOM": tsplib_geo_distance,
    }
    fn = dispatch.get(edge_weight_type.upper())
    if fn is None:
        raise ValueError(f"Unsupported EDGE_WEIGHT_TYPE: {edge_weight_type}")
    return fn(p1, p2)


# ── Travel time estimation ────────────────────────────────────────────────────

def estimate_travel_time(distance_meters: float, avg_speed_kmh: float = 40.0) -> float:
    """Estimate travel time in minutes from distance in meters."""
    return (distance_meters / 1000) / avg_speed_kmh * 60


# ── NumPy distance matrix ─────────────────────────────────────────────────────

def create_np_distance_matrix(coordinates: List[Tuple[float, float]]) -> "np.ndarray":
    """Build an NxN numpy distance matrix from 2D coordinates (TSPLIB NINT semantics)."""
    import numpy as np

    n = len(coordinates)
    dm = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        xi, yi = coordinates[i]
        for j in range(i + 1, n):
            xj, yj = coordinates[j]
            d = float(int(round(math.hypot(xi - xj, yi - yj))))
            dm[i, j] = d
            dm[j, i] = d
    return dm
