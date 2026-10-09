"""C3 regression: a local-search run must only ever see its own problem's matrix.

Audit finding C3 (docs/ULTIMATE_AUDIT_2026-10-01_CLAUDE_OPUS_5_5.md): the
numba local-search matrix cache was keyed by ``id(duration_func)``.  CPython
recycles ``id()`` values once a function is garbage-collected, so a later,
different problem of the same size could receive an earlier problem's matrix.

The tests below observe behaviour only: the matrix handed to the search kernel
and the tour that comes out.  They do not look at any cache structure.
"""
from __future__ import annotations

import gc
import random

import numpy as np
import pytest

from uniride_core.algorithms import local_search_numba as lsn
from uniride_core.algorithms.local_search_numba import LocalSearchType, apply_local_search
from uniride_core.algorithms.numba_utils import create_np_duration_func

N = 14  # canonical 3-opt is pure Python; keep it small
ROUNDS = 8

# Search kernel (module attribute) that receives the matrix, per search type.
_KERNELS = {
    LocalSearchType.TWO_OPT: "_two_opt_improve_numba",
    LocalSearchType.OR_OPT: "_or_opt_improve_numba",
    LocalSearchType.THREE_OPT: "improve_three_opt",
}


def _make_matrix(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pts = rng.random((N, 2)) * 1000.0
    return np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))


def _initial_route(seed: int) -> list:
    idx = list(range(1, N + 1))
    random.Random(seed).shuffle(idx)
    return [f"L{i}" for i in idx]


def _tour_length(route, matrix) -> float:
    ids = [int(loc[1:]) - 1 for loc in route]
    return float(sum(matrix[ids[k], ids[(k + 1) % len(ids)]] for k in range(len(ids))))


def _solve(matrix, ls_type, seed, seen):
    """One run exactly as the live callers do it: matrix wrapped in a fresh duration func."""
    locs = [f"L{i + 1}" for i in range(N)]
    func = create_np_duration_func(matrix, locs)
    route, _ = apply_local_search(_initial_route(seed), func, ls_type, max_iterations=30)
    return route


@pytest.mark.parametrize("ls_type", list(_KERNELS))
def test_each_run_uses_its_own_matrix_after_gc(monkeypatch, ls_type):
    matrices = {name: _make_matrix(s) for name, s in (("A", 1), ("B", 2), ("C", 3))}
    seeds = {"A": 11, "B": 12, "C": 13}

    # Reference: identical runs while every duration func stays alive, so no
    # address can be recycled between them.
    alive = []
    reference = {}
    for name, matrix in matrices.items():
        func = create_np_duration_func(matrix, [f"L{i + 1}" for i in range(N)])
        alive.append(func)
        route, _ = apply_local_search(_initial_route(seeds[name]), func, ls_type, max_iterations=30)
        reference[name] = _tour_length(route, matrix)

    # Observe the (matrix, route) pair that each search kernel actually receives.
    kernel_name = _KERNELS[ls_type]
    real_kernel = getattr(lsn, kernel_name)
    observed = []

    def spy(route_arg, matrix_arg, *args, **kwargs):
        observed.append((list(route_arg), np.array(matrix_arg, copy=True)))
        return real_kernel(route_arg, matrix_arg, *args, **kwargs)

    monkeypatch.setattr(lsn, kernel_name, spy)

    for _ in range(ROUNDS):
        for name, matrix in matrices.items():
            del observed[:]
            route = _solve(matrix, ls_type, seeds[name], observed)
            gc.collect()  # frees the duration func so its address can be reused

            assert observed, "search kernel was never called"
            kernel_route, kernel_matrix = observed[0]
            labels = [int(loc[1:]) - 1 for loc in _initial_route(seeds[name])]
            assert np.array_equal(
                kernel_matrix[np.ix_(kernel_route, kernel_route)],
                matrix[np.ix_(labels, labels)],
            ), f"problem {name}: kernel received another problem's matrix"
            assert _tour_length(route, matrix) == pytest.approx(reference[name], abs=1e-6), (
                f"problem {name}: result differs from the clean run"
            )


def test_non_matrix_duration_func_uses_its_own_arcs_after_gc():
    """Fallback path (no prebuilt matrix): distinct plain functions never alias."""
    matrices = [_make_matrix(s) for s in (4, 5)]
    locs = [f"L{i + 1}" for i in range(N)]
    index = {loc: i for i, loc in enumerate(locs)}

    def plain_func_for(matrix):
        # Closed-cycle cost, deliberately without the prebuilt-matrix attributes.
        def duration(route):
            ids = [index[loc] for loc in route]
            return float(sum(matrix[ids[k], ids[(k + 1) % len(ids)]] for k in range(len(ids))))
        return duration

    # Reference runs keep their duration funcs alive so no address is recycled.
    alive = []
    reference = []
    for matrix in matrices:
        ref_func = create_np_duration_func(matrix, locs)
        alive.append(ref_func)
        ref_route, _ = apply_local_search(
            _initial_route(7), ref_func, LocalSearchType.TWO_OPT, max_iterations=100
        )
        reference.append(_tour_length(ref_route, matrix))

    for _ in range(ROUNDS):
        for matrix, expected in zip(matrices, reference):
            func = plain_func_for(matrix)
            route, _ = apply_local_search(
                _initial_route(7), func, LocalSearchType.TWO_OPT, max_iterations=100
            )
            assert _tour_length(route, matrix) == pytest.approx(expected, abs=1e-6)
            del func
            gc.collect()
