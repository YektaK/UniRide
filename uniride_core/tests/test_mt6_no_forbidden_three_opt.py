"""MT6-02 (audit H10): the SOTA final polish uses the canonical 3-opt only.

The old Numba kernel (``numba_accel._three_opt_improve_atsp_numba`` / ``nb_three_opt`` /
``_build_3opt_candidate``) is non-canonical (``CANONICAL_THREE_OPT_DESIGN.md``): it only
reverses/keeps segments in place, admits adjacent cuts and reverses on asymmetric matrices.
It must not be reachable from the SOTA solvers or the production adapter, with or without
Numba. ``ls_engine.improve_3opt`` must be ``improve_three_opt`` on the same input.
"""
from __future__ import annotations

import random

import pytest

from uniride_core.algorithms import numba_accel
from uniride_core.algorithms.sota_tsp import ls_engine
from uniride_core.algorithms.sota_tsp.e2bso_tsp import (
    E2BSO_TSP,
    E2BSO_TSP_CPSO,
    E2BSOCPSPConfig,
    E2BSOTSPConfig,
)
from uniride_core.algorithms.sota_tsp.paoea_tsp import PAOEA_TSP, PAOEAConfig
from uniride_core.algorithms.sota_tsp.r2dma_tsp import R2DMA_TSP, R2DMATSPConfig
from uniride_core.algorithms.three_opt import improve_three_opt

FORBIDDEN = ("_three_opt_improve_atsp_numba", "nb_three_opt", "_build_3opt_candidate")


@pytest.fixture
def kernel_spy(monkeypatch):
    """Record every call into the forbidden kernel and fail loudly (stubs, never the real JIT code)."""
    calls: list[str] = []

    def stub(name):
        def spy(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"forbidden non-canonical 3-opt kernel reached: {name}")

        monkeypatch.setattr(numba_accel, name, spy)

    for name in FORBIDDEN:
        stub(name)
    return calls


def _matrix(n: int, seed: int, *, symmetric: bool) -> list[list[float]]:
    rng = random.Random(seed)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if symmetric and j < i:
                m[i][j] = m[j][i]
            else:
                m[i][j] = float(rng.randint(1, 60))
    return m


def _tiny(cfg_cls, **extra):
    return cfg_cls(population_size=6, max_iterations=3, seed=7, **extra)


SOLVERS = [
    ("E2BSO", E2BSO_TSP, lambda: _tiny(E2BSOTSPConfig)),
    ("E2BSO-CPSO", E2BSO_TSP_CPSO, lambda: _tiny(E2BSOCPSPConfig)),
    ("R2DMA", R2DMA_TSP, lambda: _tiny(R2DMATSPConfig)),
    ("P-AOEA", PAOEA_TSP, lambda: _tiny(PAOEAConfig)),
]


# (a) reachability spy ----------------------------------------------------------------------


@pytest.mark.parametrize("label,solver_cls,make_cfg", SOLVERS, ids=[s[0] for s in SOLVERS])
def test_solver_final_polish_never_reaches_the_forbidden_kernel(
    label, solver_cls, make_cfg, kernel_spy
):
    matrix = _matrix(12, 3, symmetric=False)
    result = solver_cls(make_cfg()).solve_with_matrix(matrix)
    assert sorted(result.tour) == list(range(12))
    assert kernel_spy == []


@pytest.mark.parametrize("label,solver_cls,make_cfg", SOLVERS, ids=[s[0] for s in SOLVERS])
def test_production_adapter_never_reaches_the_forbidden_kernel(
    label, solver_cls, make_cfg, kernel_spy
):
    from uniride_core.adapters.sota_tsp_strategy_adapter import (
        solve_student_order_with_sota_tsp,
    )

    students = [f"S{i}" for i in range(1, 9)]
    ids = ["D", *students]
    rng = random.Random(11)
    durations = {(a, b): float(rng.randint(1, 30)) for a in ids for b in ids if a != b}

    outcome = solve_student_order_with_sota_tsp(
        students, "D", lambda a, b: durations[(a, b)], solver_cls, make_cfg()
    )
    assert outcome.fallback_reason is None
    assert sorted(outcome.order) == sorted(students)
    assert kernel_spy == []


# (b) the 3-opt layer is improve_three_opt --------------------------------------------------


@pytest.mark.parametrize("symmetric", [False, True], ids=["asymmetric", "symmetric"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_improve_3opt_equals_canonical_improve_three_opt(symmetric, seed):
    np = pytest.importorskip("numpy")
    n = 14
    matrix = _matrix(n, seed, symmetric=symmetric)
    tour = list(range(n))
    random.Random(seed).shuffle(tour)

    expected = improve_three_opt(tour, matrix, max_iterations=50, window=12)

    for dm_np in (np.array(matrix, dtype=np.float64), None):
        route, cost = ls_engine.improve_3opt(tour, matrix, dm_np, 50, 12)
        assert route == expected.route
        assert cost == pytest.approx(expected.cost)


def test_improve_3opt_actually_improves_a_bad_tour():
    n = 14
    matrix = _matrix(n, 5, symmetric=False)
    tour = list(range(n))
    random.Random(5).shuffle(tour)
    start = ls_engine._tour_cost(tour, matrix)
    route, cost = ls_engine.improve_3opt(tour, matrix, None, 50, 12)
    assert sorted(route) == list(range(n))
    assert cost < start
    assert cost == pytest.approx(ls_engine._tour_cost(route, matrix))


# (c) Numba unavailable: no reverse-middle fallback -----------------------------------------


@pytest.mark.parametrize("symmetric", [False, True], ids=["asymmetric", "symmetric"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_improve_3opt_without_numba_is_canonical_too(monkeypatch, symmetric, seed):
    monkeypatch.setattr(ls_engine, "_NUMBA_OK", False)
    n = 14
    matrix = _matrix(n, seed, symmetric=symmetric)
    tour = list(range(n))
    random.Random(seed).shuffle(tour)

    expected = improve_three_opt(tour, matrix, max_iterations=50, window=12)
    route, cost = ls_engine.improve_3opt(tour, matrix, None, 50, 12)

    assert route == expected.route
    assert cost == pytest.approx(expected.cost)


def test_improve_3opt_tiny_tours_are_returned_unchanged():
    matrix = _matrix(5, 1, symmetric=False)
    tour = [0, 1, 2, 3, 4]
    route, cost = ls_engine.improve_3opt(tour, matrix, None, 50, 12)
    assert route == tour
    assert cost == pytest.approx(ls_engine._tour_cost(tour, matrix))


# Permutation contract: improve_three_opt validates its input (three_opt.py _validate_problem),
# so every tour that reaches the polish of a SOTA solver must be a permutation of 0..n-1. ---


@pytest.mark.parametrize("label,solver_cls,make_cfg", SOLVERS, ids=[s[0] for s in SOLVERS])
@pytest.mark.parametrize("n,symmetric", [(7, True), (12, False), (20, True), (20, False)])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_tour_reaching_the_3opt_layer_is_a_full_permutation(
    monkeypatch, label, solver_cls, make_cfg, n, symmetric, seed
):
    seen: list[list[int]] = []
    real = ls_engine.improve_three_opt

    def recording(route, matrix, **kwargs):
        seen.append(list(route))
        assert sorted(route) == list(range(len(matrix)))
        return real(route, matrix, **kwargs)

    monkeypatch.setattr(ls_engine, "improve_three_opt", recording)
    cfg = make_cfg()
    cfg.seed = seed
    result = solver_cls(cfg).solve_with_matrix(_matrix(n, seed, symmetric=symmetric))

    assert seen, "the final polish must reach the canonical 3-opt layer"
    assert sorted(result.tour) == list(range(n))


def test_old_kernel_is_documented_as_non_canonical():
    for name in ("nb_three_opt", "_three_opt_improve_atsp_numba"):
        doc = (getattr(numba_accel, name).__doc__ or "") if name == "nb_three_opt" else (
            getattr(numba_accel, name).py_func.__doc__ or ""
        )
        assert "NON-CANONICAL" in doc, name
