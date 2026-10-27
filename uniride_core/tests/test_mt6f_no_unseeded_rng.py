"""MT6F-06 (audit L10-c, L10-d): no unseeded generator, no dormant random order.

A missing seed resolves to the repository default 42 in the two core matrix
engines and the effective seed is reported in the result. The dormant
``use_random_order`` / ``self.rng`` pair is gone from both ``HybridLocalSearch``
copies. ``tsp_matrix_metaheuristics`` (study path) is deliberately untouched.
"""

from __future__ import annotations

import inspect
import random
from types import SimpleNamespace

import numpy as np
import pytest

from uniride_core.algorithms import fcm_split_engine, local_search, local_search_numba
from uniride_core.algorithms import tsp_meta_matrix_engine
from uniride_core.algorithms.fcm_split_engine import FCMSplitMatrixEngine
from uniride_core.algorithms.tsp_meta_matrix_engine import TSPMetaMatrixEngine

REAL_RANDOM = random.Random


def _identity_solver(waypoints, duration_func, rng, cfg):
    route = list(waypoints)
    return route, float(duration_func(route))


def _matrix(n: int) -> np.ndarray:
    coords = [(float(i % 4), float(i // 4)) for i in range(n)]
    dm = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dm[i, j] = abs(coords[i][0] - coords[j][0]) + abs(coords[i][1] - coords[j][1])
    return dm


def _coords(n: int):
    return [(float(i % 4), float(i // 4)) for i in range(n)]


def _record_random(monkeypatch, module):
    seen = []

    def recorder(*args, **kwargs):
        seen.append((args, kwargs))
        return REAL_RANDOM(*args, **kwargs)

    # Replace the module's ``random`` name only; the global module stays intact.
    monkeypatch.setattr(module, "random", SimpleNamespace(Random=recorder))
    return seen


def _args_of(seen):
    return [args[0] if args else kwargs.get("x") for args, kwargs in seen]


def test_tsp_meta_matrix_engine_missing_seed_resolves_to_42(monkeypatch):
    seen = _record_random(monkeypatch, tsp_meta_matrix_engine)
    engine = TSPMetaMatrixEngine("T", _identity_solver)
    result = engine.optimize_permutation(_matrix(6), {"problem_type": "tsp"}, seed=None)
    assert seen, "engine never constructed a generator"
    assert all(arg is not None for arg in _args_of(seen))
    assert _args_of(seen) == [42]
    assert result.seed == 42


def test_tsp_meta_matrix_engine_integer_seed_is_unchanged(monkeypatch):
    seen = _record_random(monkeypatch, tsp_meta_matrix_engine)
    engine = TSPMetaMatrixEngine("T", _identity_solver)
    result = engine.optimize_permutation(_matrix(6), {"problem_type": "tsp"}, seed=0)
    assert _args_of(seen) == [0]
    assert result.seed == 0


@pytest.mark.parametrize(
    "n,cfg_extra",
    [
        (2, {}),  # <= 2 nodes: early return
        (6, {}),  # one cluster: solve the whole tour
        (16, {"fcm_clusters": 3, "fcm_min_cluster_size": 4}),  # cluster path
    ],
)
def test_fcm_split_engine_missing_seed_resolves_to_42(monkeypatch, n, cfg_extra):
    seen = _record_random(monkeypatch, fcm_split_engine)
    engine = FCMSplitMatrixEngine("F", _identity_solver)
    cfg = {"problem_type": "tsp", "coordinates": _coords(n), **cfg_extra}
    result = engine.optimize_permutation(_matrix(n), cfg, seed=None)
    assert seen, "engine never constructed a generator"
    assert all(arg is not None for arg in _args_of(seen))
    assert set(_args_of(seen)) == {42}
    assert result.seed == 42


def test_fcm_split_engine_cluster_path_builds_both_generators_from_42(monkeypatch):
    seen = _record_random(monkeypatch, fcm_split_engine)
    engine = FCMSplitMatrixEngine("F", _identity_solver)
    cfg = {"problem_type": "tsp", "coordinates": _coords(16), "fcm_clusters": 3}
    engine.optimize_permutation(_matrix(16), cfg, seed=None)
    assert _args_of(seen) == [42, 42]  # solver rng and clustering rng


def test_fcm_split_engine_integer_seed_is_unchanged(monkeypatch):
    seen = _record_random(monkeypatch, fcm_split_engine)
    engine = FCMSplitMatrixEngine("F", _identity_solver)
    cfg = {"problem_type": "tsp", "coordinates": _coords(16), "fcm_clusters": 3}
    result = engine.optimize_permutation(_matrix(16), cfg, seed=7)
    assert set(_args_of(seen)) == {7}
    assert result.seed == 7


def test_missing_seed_runs_are_reproducible():
    cfg = {"problem_type": "tsp", "coordinates": _coords(16), "fcm_clusters": 3}
    first = FCMSplitMatrixEngine("F", _identity_solver).optimize_permutation(_matrix(16), cfg, seed=None)
    second = FCMSplitMatrixEngine("F", _identity_solver).optimize_permutation(_matrix(16), cfg, seed=None)
    explicit = FCMSplitMatrixEngine("F", _identity_solver).optimize_permutation(_matrix(16), cfg, seed=42)
    assert first.permutation == second.permutation == explicit.permutation


@pytest.mark.parametrize("module", [local_search, local_search_numba], ids=["local_search", "local_search_numba"])
def test_hybrid_local_search_has_no_dormant_random_order(module):
    cls = module.HybridLocalSearch
    assert "use_random_order" not in inspect.signature(cls.__init__).parameters
    instance = cls(max_iterations=1)
    assert not hasattr(instance, "use_random_order")
    assert not hasattr(instance, "rng")
    with pytest.raises(TypeError):
        cls(use_random_order=True)
