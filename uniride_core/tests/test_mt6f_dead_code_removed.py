"""MT6F-03 (audit L3-f, L3-g): dead k-means copies and the dead numba 3-opt copy are gone.

Plan: docs/superpowers/plans/2026-10-27-mt6-followup-sota-common-shims-l3-l10.md, item MT6F-03.
The live k-means is ``clustering_strategies/kmeans.py``; the canonical 3-opt is
``uniride_core.algorithms.three_opt`` (CANONICAL_THREE_OPT_DESIGN.md).
"""

import pytest

from uniride_core.algorithms import clustering, local_search_numba


@pytest.mark.parametrize(
    "name",
    ["kmeans_clustering", "initialize_centroids_kmeans_plus_plus", "split_cluster"],
)
def test_legacy_kmeans_primitives_are_removed_from_clustering(name):
    assert not hasattr(clustering, name)
    assert name not in clustering.__all__


@pytest.mark.parametrize(
    "name",
    ["Point", "Cluster", "calculate_centroid", "resolve_rng", "validate_cluster_capacity"],
)
def test_live_clustering_helpers_stay(name):
    assert hasattr(clustering, name)
    assert name in clustering.__all__


@pytest.mark.parametrize("name", ["_three_opt_improve_numba", "_three_opt_cases_numba"])
def test_dead_numba_three_opt_copy_is_removed(name):
    assert not hasattr(local_search_numba, name)
