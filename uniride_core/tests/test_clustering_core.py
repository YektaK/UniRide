from uniride_core.algorithms.clustering import (
    Point,
    calculate_centroid,
    kmeans_clustering,
    validate_cluster_capacity,
)


def test_core_clustering_centroid_and_capacity():
    points = [Point("S1", 10, 10, "Sw"), Point("S2", 20, 20, "So")]
    cluster = kmeans_clustering(points, k=1)[0]

    assert calculate_centroid(points) == (15.0, 15.0)
    assert cluster.sw_count == 1
    assert cluster.so_count == 1
    assert validate_cluster_capacity(cluster, sw_capacity=1, so_capacity=1)


def test_core_clustering_splits_nearby_groups():
    points = [
        Point("S1", 41.0, 29.0, "Sw"),
        Point("S2", 41.01, 29.01, "Sw"),
        Point("S3", 41.1, 29.1, "So"),
        Point("S4", 41.11, 29.11, "So"),
    ]

    clusters = kmeans_clustering(points, k=2)

    assert len(clusters) == 2
    assert sorted(len(cluster.points) for cluster in clusters) == [2, 2]
