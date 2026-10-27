"""H12 review round 1: the seed must be *threaded*, not merely defaulted.

``resolve_rng(None)`` returns a fixed ``Random(42)``, so cutting a thread keeps results
reproducible; these tests therefore pin that the caller's generator really arrives
(seed sensitivity, identity spies, global-state checks)."""

import random

import pytest

from uniride_core.algorithms.clustering import Cluster, Point
from uniride_core.algorithms.clustering_strategies import (
    _CLUSTERING_STRATEGIES,
    SUPPORTED_CLUSTERING_ALGORITHMS,
    fuzzy_cmeans_enhanced as enhanced_module,
    get_clustering_strategy,
    hierarchical_fcm as hierarchical_module,
)
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator


def _points(n=40, layout_seed=2026):
    layout = random.Random(layout_seed)
    return [
        Point(
            f"s{i}",
            40.9 + layout.random() * 0.1,
            29.0 + layout.random() * 0.1,
            "Sw" if i % 5 == 0 else "So",
            f"L{i}",
        )
        for i in range(n)
    ]


def _partition(clusters):
    return frozenset(frozenset(p.id for p in c.points) for c in clusters)


def _students(points):
    return [
        {
            "id": p.id,
            "location_code": p.location_code,
            "coordinates": {"lat": p.lat, "lng": p.lng},
            "disability_type": p.disability_type,
        }
        for p in points
    ]


# ---------------------------------------------------------------- (a) VehicleCalculator


def test_vehicle_calculator_partition_depends_on_the_rng_it_is_given():
    points = _points()

    def partition(seed):
        result = VehicleCalculator(4, 5, 120, "kmeans", rng=random.Random(seed)).calculate(_students(points))
        return frozenset(frozenset(s["id"] for s in a["students"]) for a in result["assignments"])

    assert len({partition(seed) for seed in range(8)}) > 1


# ---------------------------------------------------------------- (c) enhanced FCM / hierarchical


@pytest.mark.parametrize(
    "name,n,extra",
    [
        ("fuzzy_cmeans_enhanced", 40, {}),
        ("hierarchical_fcm", 40, {}),  # N <= threshold: single stage
        ("hierarchical_fcm", 120, {}),  # N > 50: regional + vehicle stages
    ],
    ids=["enhanced-40", "hierarchical-single-stage-40", "hierarchical-two-stage-120"],
)
def test_enhanced_and_hierarchical_partition_depends_on_the_strategy_rng(name, n, extra):
    points = _points(n)
    k = 8 if n == 40 else 16

    def partition(seed):
        strategy = get_clustering_strategy(name, 4, 5, rng=random.Random(seed), **extra)
        return _partition(strategy.cluster_students(points, k))

    assert len({partition(seed) for seed in range(8)}) > 1
    assert partition(3) == partition(3)


def _spy_core(monkeypatch, module):
    seen = []
    original = module.enhanced_fuzzy_c_means_core

    def spy(*args, **kwargs):
        seen.append(kwargs.get("rng"))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "enhanced_fuzzy_c_means_core", spy)
    return seen


def _over_capacity_cluster(n=6):
    pts = _points(n)
    return Cluster(centroid=(40.95, 29.05), points=pts, sw_count=0, so_count=n)


def test_enhanced_strategy_passes_its_rng_to_the_core(monkeypatch):
    seen = _spy_core(monkeypatch, enhanced_module)
    strategy = get_clustering_strategy("fuzzy_cmeans_enhanced", 4, 5, rng=random.Random(11))
    strategy.cluster_students(_points(30), 6)
    assert seen and all(rng is strategy.rng for rng in seen)


def test_enhanced_split_cluster_passes_its_rng_to_the_core(monkeypatch):
    seen = _spy_core(monkeypatch, enhanced_module)
    strategy = get_clustering_strategy("fuzzy_cmeans_enhanced", 4, 5, rng=random.Random(11))
    strategy._split_cluster(_over_capacity_cluster())
    assert len(seen) == 1 and seen[0] is strategy.rng


@pytest.mark.parametrize("n,k", [(30, 6), (120, 16)], ids=["single-stage", "two-stage"])
def test_hierarchical_every_stage_shares_the_strategy_rng(monkeypatch, n, k):
    seen = _spy_core(monkeypatch, hierarchical_module)
    strategy = get_clustering_strategy("hierarchical_fcm", 4, 5, rng=random.Random(11))
    strategy.cluster_students(_points(n), k)
    assert seen and all(rng is strategy.rng for rng in seen)
    if n > 50:
        assert len(seen) > 1  # regional stage plus at least one vehicle stage


def test_hierarchical_split_cluster_passes_its_rng_to_the_core(monkeypatch):
    seen = _spy_core(monkeypatch, hierarchical_module)
    strategy = get_clustering_strategy("hierarchical_fcm", 4, 5, rng=random.Random(11))
    strategy._split_cluster(_over_capacity_cluster())
    assert len(seen) == 1 and seen[0] is strategy.rng


def test_hierarchical_without_rng_shares_one_generator_across_stages(monkeypatch):
    seen = _spy_core(monkeypatch, hierarchical_module)
    hierarchical_module.hierarchical_fcm_clustering(_points(120), 16)
    assert len(seen) > 1
    assert all(isinstance(rng, random.Random) for rng in seen)
    assert len({id(rng) for rng in seen}) == 1


# Section (d) "legacy primitives" was removed in MT6F-03 together with the dead
# kmeans_clustering / split_cluster / initialize_centroids_kmeans_plus_plus code (audit L3-f).


# ---------------------------------------------------------------- polish (1): one source of truth


def test_allowlist_is_derived_from_the_factory_dict():
    assert SUPPORTED_CLUSTERING_ALGORITHMS == tuple(_CLUSTERING_STRATEGIES)
    for name, cls in _CLUSTERING_STRATEGIES.items():
        assert type(get_clustering_strategy(name)) is cls
