from uniride_core.algorithms.clustering import (
    Cluster,
    Point,
    calculate_centroid,
    validate_cluster_capacity,
)


def test_core_clustering_centroid_and_capacity():
    points = [Point("S1", 10, 10, "Sw"), Point("S2", 20, 20, "So")]
    # MT6F-03: the cluster is built by hand; the dead k-means primitive that used
    # to produce it was removed (audit L3-f).
    cluster = Cluster(centroid=calculate_centroid(points), points=points, sw_count=1, so_count=1)

    assert calculate_centroid(points) == (15.0, 15.0)
    assert cluster.sw_count == 1
    assert cluster.so_count == 1
    assert validate_cluster_capacity(cluster, sw_capacity=1, so_capacity=1)
    assert not validate_cluster_capacity(cluster, sw_capacity=0, so_capacity=1)
