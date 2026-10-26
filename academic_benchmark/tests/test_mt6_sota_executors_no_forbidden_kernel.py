"""MT6-02 (audit H10): the ``SOTA-*`` registry executors never reach the old Numba 3-opt kernel.

Companion of ``uniride_core/tests/test_mt6_no_forbidden_three_opt.py`` (which covers the core
solvers and the production adapter). Lives here because ``uniride_core`` tests must not import
``academic_benchmark``.
"""
from __future__ import annotations

import random

import pytest

import academic_benchmark.core.registry_setup  # noqa: F401 - registers the executors
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from uniride_core.algorithms import numba_accel

FORBIDDEN = ("_three_opt_improve_atsp_numba", "nb_three_opt", "_build_3opt_candidate")
THREE_OPT_SOTA_IDS = ["SOTA-E2BSO-TSP", "SOTA-R2DMA-TSP", "SOTA-P-AOEA-TSP"]


def _atsp(n: int = 10) -> ProblemInstance:
    rng = random.Random(21)
    matrix = [[0 if i == j else rng.randint(1, 60) for j in range(n)] for i in range(n)]
    return ProblemInstance(
        name="mt6-atsp", dimension=n, coordinates=[], problem_type="atsp", dist_matrix=matrix
    )


@pytest.mark.parametrize("algorithm_id", THREE_OPT_SOTA_IDS)
def test_sota_executor_never_reaches_the_forbidden_kernel(algorithm_id, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def spy(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"forbidden non-canonical 3-opt kernel reached: {name}")

        monkeypatch.setattr(numba_accel, name, spy)

    for name in FORBIDDEN:
        stub(name)

    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _atsp(), {"max_iterations": 3, "population_size": 6}, 42, 1
    )

    assert result.tour is not None and len(result.tour) == 10
    assert calls == []
