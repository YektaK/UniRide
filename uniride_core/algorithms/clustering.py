"""Core clustering primitives for cluster-first routing pipelines."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

# Seed used when a caller supplies no generator. Clustering never touches the
# process-global ``random`` state (audit H12): a missing rng becomes a local,
# deterministic ``random.Random(DEFAULT_CLUSTERING_SEED)``.
DEFAULT_CLUSTERING_SEED = 42


def resolve_rng(rng: random.Random | None = None) -> random.Random:
    """Return ``rng`` or a fresh local generator; never the global state."""
    return rng if rng is not None else random.Random(DEFAULT_CLUSTERING_SEED)


class MissingTravelTimeError(LookupError):
    """A clustering step needs a travel time the stored matrix does not hold.

    Operational clustering (k-medoids, Clarke-Wright) must use the authoritative
    ``time_matrix``; there is no haversine or other stand-in (owner requirement
    2026-10-05).
    """


def matrix_travel_time(p1: "Point", p2: "Point", time_matrix: Mapping[str, Mapping[str, float]]) -> float:
    """Directed travel time between two points from a matrix keyed by location code.

    Points sharing a stop (same non-empty ``location_code``) are 0 minutes apart.
    Any other pair absent from ``time_matrix`` raises ``MissingTravelTimeError``.
    """
    if p1.location_code and p1.location_code == p2.location_code:
        return 0.0
    try:
        return float(time_matrix[p1.location_code][p2.location_code])
    except (KeyError, TypeError):
        raise MissingTravelTimeError(
            f"No travel time {p1.location_code!r} -> {p2.location_code!r} in the matrix"
        ) from None


@dataclass
class Point:
    """Geographic point with student capacity category metadata."""
    id: str
    lat: float
    lng: float
    disability_type: str
    location_code: str = ""


@dataclass
class Cluster:
    """Cluster of student points."""
    centroid: Tuple[float, float]
    points: List[Point]
    sw_count: int
    so_count: int


def calculate_centroid(points: List[Point]) -> Tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    return (
        sum(point.lat for point in points) / len(points),
        sum(point.lng for point in points) / len(points),
    )


def validate_cluster_capacity(cluster: Cluster, sw_capacity: int, so_capacity: int) -> bool:
    return cluster.sw_count <= sw_capacity and cluster.so_count <= so_capacity


__all__ = [
    "DEFAULT_CLUSTERING_SEED",
    "resolve_rng",
    "MissingTravelTimeError",
    "matrix_travel_time",
    "Point",
    "Cluster",
    "calculate_centroid",
    "validate_cluster_capacity",
]
