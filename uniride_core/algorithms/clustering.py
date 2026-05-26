"""Core clustering primitives for cluster-first routing pipelines."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from uniride_core.algorithms.distance import haversine_distance


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


def initialize_centroids_kmeans_plus_plus(points: List[Point], k: int) -> List[Tuple[float, float]]:
    if k <= 0 or not points:
        return []

    centroids = []
    first_idx = random.randint(0, len(points) - 1)
    centroids.append((points[first_idx].lat, points[first_idx].lng))

    while len(centroids) < k:
        distances = []
        for point in points:
            min_dist = min(
                haversine_distance(point.lat, point.lng, centroid[0], centroid[1]) ** 2
                for centroid in centroids
            )
            distances.append(min_dist)

        total_dist = sum(distances)
        if total_dist == 0:
            break

        threshold = random.random() * total_dist
        cumulative = 0.0
        for idx, distance in enumerate(distances):
            cumulative += distance
            if cumulative >= threshold:
                centroids.append((points[idx].lat, points[idx].lng))
                break

    return centroids


def kmeans_clustering(points: List[Point], k: int, max_iterations: int = 100) -> List[Cluster]:
    if not points or k <= 0:
        return []

    if k >= len(points):
        return [
            Cluster(
                centroid=(point.lat, point.lng),
                points=[point],
                sw_count=1 if point.disability_type == "Sw" else 0,
                so_count=1 if point.disability_type == "So" else 0,
            )
            for point in points
        ]

    centroids = initialize_centroids_kmeans_plus_plus(points, k)
    prev_assignments = [-1] * len(points)

    for _ in range(max_iterations):
        assignments = []
        for point in points:
            min_idx = 0
            min_dist = float("inf")
            for idx, centroid in enumerate(centroids):
                dist = haversine_distance(point.lat, point.lng, centroid[0], centroid[1])
                if dist < min_dist:
                    min_dist = dist
                    min_idx = idx
            assignments.append(min_idx)

        if assignments == prev_assignments:
            break
        prev_assignments = assignments

        for idx in range(k):
            cluster_points = [points[p_idx] for p_idx in range(len(points)) if assignments[p_idx] == idx]
            if cluster_points:
                centroids[idx] = calculate_centroid(cluster_points)

    clusters = []
    for idx in range(k):
        cluster_points = [points[p_idx] for p_idx in range(len(points)) if prev_assignments[p_idx] == idx]
        if cluster_points:
            clusters.append(
                Cluster(
                    centroid=centroids[idx],
                    points=cluster_points,
                    sw_count=sum(1 for point in cluster_points if point.disability_type == "Sw"),
                    so_count=sum(1 for point in cluster_points if point.disability_type == "So"),
                )
            )
    return clusters


def validate_cluster_capacity(cluster: Cluster, sw_capacity: int, so_capacity: int) -> bool:
    return cluster.sw_count <= sw_capacity and cluster.so_count <= so_capacity


def split_cluster(cluster: Cluster) -> List[Cluster]:
    if len(cluster.points) <= 1:
        return [cluster]
    return kmeans_clustering(cluster.points, 2)


__all__ = [
    "Point",
    "Cluster",
    "calculate_centroid",
    "initialize_centroids_kmeans_plus_plus",
    "kmeans_clustering",
    "validate_cluster_capacity",
    "split_cluster",
]
