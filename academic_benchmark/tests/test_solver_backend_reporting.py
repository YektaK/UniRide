"""Runtime-truthful backend reporting for canonical GWO and HHO."""
from __future__ import annotations

from typing import Callable, Type

import numpy as np
import pytest

from uniride_core.algorithms import numba_accel as _nb
from uniride_core.algorithms.tsp_matrix_metaheuristics.base_solver import BaseTSPSolver
from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import GWOOptimizer
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import HHOOptimizer


SolverType = Type[GWOOptimizer] | Type[HHOOptimizer]


def _symmetric_matrix() -> list[list[float]]:
    return [
        [0, 7, 9, 11, 8, 10],
        [7, 0, 6, 5, 12, 9],
        [9, 6, 0, 4, 7, 13],
        [11, 5, 4, 0, 6, 8],
        [8, 12, 7, 6, 0, 5],
        [10, 9, 13, 8, 5, 0],
    ]


def _directed_matrix() -> list[list[float]]:
    return [
        [0, 9, 4, 12, 7, 15],
        [3, 0, 11, 5, 14, 6],
        [13, 8, 0, 10, 2, 9],
        [6, 16, 3, 0, 8, 4],
        [11, 5, 17, 1, 0, 12],
        [7, 14, 6, 13, 3, 0],
    ]


def _require_working_jit() -> None:
    if not _nb.NUMBA_AVAILABLE:
        pytest.skip("Numba JIT unavailable: backend reporting is not JIT-validated")

    matrix = np.ascontiguousarray(
        np.array([[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]),
        dtype=np.float64,
    )
    route = np.ascontiguousarray(np.array([0, 1, 2], dtype=np.int64))
    assert _nb._calculate_tour_length_atsp_numba(route, matrix) == pytest.approx(9.0)
    assert _nb._calculate_tour_length_atsp_numba.nopython_signatures


def _solver(
    solver_type: SolverType,
    *,
    polish_enabled: bool,
    fair: bool,
    max_iterations: int = 1,
) -> BaseTSPSolver:
    common = {
        "max_iterations": max_iterations,
        "random_seed": 1729,
        "polish_enabled": polish_enabled,
        "polish_interval": 1,
        "polish_iters": 1,
        "final_polish_iters": 1,
        "evaluation_budget": 100 if fair else None,
    }
    if solver_type is GWOOptimizer:
        return solver_type(pack_size=4, **common)
    return solver_type(hawks=4, dive_count=0, **common)


def _solve(solver: BaseTSPSolver, matrix: list[list[float]]):
    return solver.solve_with_matrix(matrix, closed_tsp=True, recalculate=False)


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
@pytest.mark.parametrize(
    ("matrix_factory", "matrix_kind"),
    [(_symmetric_matrix, "symmetric-tsp"), (_directed_matrix, "directed-atsp")],
)
@pytest.mark.parametrize("polish_enabled", [False, True], ids=["pure", "memetic"])
def test_reports_compiled_objective_and_fair_python_polish(
    solver_type: SolverType,
    matrix_factory: Callable[[], list[list[float]]],
    matrix_kind: str,
    polish_enabled: bool,
) -> None:
    del matrix_kind
    _require_working_jit()

    result = _solve(
        _solver(solver_type, polish_enabled=polish_enabled, fair=True),
        matrix_factory(),
    )

    expected_polish = "python" if polish_enabled else "none"
    assert result.extra_stats["execution_backend"] == (
        f"objective=numba;polish={expected_polish}"
    )
    if polish_enabled:
        assert result.extra_stats["variant"] == "memetic_2opt"
    else:
        assert result.extra_stats["variant"] == "pure"


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
@pytest.mark.parametrize(
    ("matrix_factory", "matrix_kind"),
    [(_symmetric_matrix, "symmetric-tsp"), (_directed_matrix, "directed-atsp")],
)
def test_forced_objective_failure_reports_successful_python_fallback(
    monkeypatch: pytest.MonkeyPatch,
    solver_type: SolverType,
    matrix_factory: Callable[[], list[list[float]]],
    matrix_kind: str,
) -> None:
    del matrix_kind
    _require_working_jit()

    def _force_python_fallback(*_args: object, **_kwargs: object) -> float:
        raise RuntimeError("test-local forced Python objective fallback")

    monkeypatch.setattr(_nb, "_calculate_tour_length_atsp_numba", _force_python_fallback)
    result = _solve(
        _solver(solver_type, polish_enabled=False, fair=True), matrix_factory()
    )

    assert result.extra_stats["execution_backend"] == "objective=python;polish=none"


def test_missing_cached_objective_kernel_reports_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(_nb, "_calculate_tour_length_atsp_numba")
    solver = _solver(GWOOptimizer, polish_enabled=False, fair=True)

    result = _solve(solver, _symmetric_matrix())

    assert solver._dist_matrix_np is not None
    assert result.extra_stats["execution_backend"] == "objective=python;polish=none"


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
def test_cached_objective_plain_python_shim_reports_python(
    monkeypatch: pytest.MonkeyPatch, solver_type: SolverType
) -> None:
    monkeypatch.setattr(_nb, "NUMBA_AVAILABLE", False)

    def _python_objective(route: np.ndarray, matrix: np.ndarray) -> float:
        return sum(
            float(matrix[node, route[(index + 1) % len(route)]])
            for index, node in enumerate(route)
        )

    monkeypatch.setattr(_nb, "_calculate_tour_length_atsp_numba", _python_objective)
    solver = _solver(solver_type, polish_enabled=False, fair=True)
    result = _solve(solver, _symmetric_matrix())

    assert solver._dist_matrix_np is not None
    assert result.extra_stats["execution_backend"] == "objective=python;polish=none"


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
def test_pure_python_objective_path_reports_python(
    monkeypatch: pytest.MonkeyPatch, solver_type: SolverType
) -> None:
    monkeypatch.setattr(
        BaseTSPSolver,
        "_build_np_cache",
        lambda solver: setattr(solver, "_dist_matrix_np", None),
    )

    result = _solve(
        _solver(solver_type, polish_enabled=False, fair=True), _symmetric_matrix()
    )

    assert result.extra_stats["execution_backend"] == "objective=python;polish=none"


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
@pytest.mark.parametrize(
    ("matrix_factory", "matrix_kind"),
    [(_symmetric_matrix, "symmetric-tsp"), (_directed_matrix, "directed-atsp")],
)
def test_direct_compiled_polish_reports_numba(
    solver_type: SolverType,
    matrix_factory: Callable[[], list[list[float]]],
    matrix_kind: str,
) -> None:
    del matrix_kind
    _require_working_jit()

    result = _solve(
        _solver(
            solver_type,
            polish_enabled=True,
            fair=False,
            max_iterations=0,
        ),
        matrix_factory(),
    )

    assert result.extra_stats["execution_backend"] == "objective=unused;polish=numba"
    assert _nb._two_opt_improve_atsp_numba.nopython_signatures


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
def test_cached_polish_plain_python_shim_reports_python(
    monkeypatch: pytest.MonkeyPatch, solver_type: SolverType
) -> None:
    monkeypatch.setattr(_nb, "NUMBA_AVAILABLE", False)

    def _python_two_opt(
        route: np.ndarray,
        matrix: np.ndarray,
        _max_iterations: int,
        _first_improvement: bool,
    ) -> tuple[np.ndarray, float]:
        cost = sum(
            float(matrix[node, route[(index + 1) % len(route)]])
            for index, node in enumerate(route)
        )
        return route.copy(), cost

    monkeypatch.setattr(_nb, "_two_opt_improve_atsp_numba", _python_two_opt)
    solver = _solver(
        solver_type,
        polish_enabled=True,
        fair=False,
        max_iterations=0,
    )
    result = _solve(solver, _symmetric_matrix())

    assert solver._dist_matrix_np is not None
    assert result.extra_stats["execution_backend"] == (
        "objective=unused;polish=python"
    )


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
def test_uncached_polish_wrapper_reports_executed_python_kernel(
    monkeypatch: pytest.MonkeyPatch, solver_type: SolverType
) -> None:
    monkeypatch.setattr(
        BaseTSPSolver,
        "_build_np_cache",
        lambda solver: setattr(solver, "_dist_matrix_np", None),
    )

    def _python_two_opt(
        route: np.ndarray,
        matrix: np.ndarray,
        _max_iterations: int,
        _first_improvement: bool,
    ) -> tuple[np.ndarray, float]:
        cost = sum(
            float(matrix[node, route[(index + 1) % len(route)]])
            for index, node in enumerate(route)
        )
        return route.copy(), cost

    monkeypatch.setattr(_nb, "_two_opt_improve_atsp_numba", _python_two_opt)
    result = _solve(
        _solver(
            solver_type,
            polish_enabled=True,
            fair=False,
            max_iterations=0,
        ),
        _symmetric_matrix(),
    )

    assert result.extra_stats["execution_backend"] == (
        "objective=unused;polish=python"
    )


@pytest.mark.parametrize("solver_type", [GWOOptimizer, HHOOptimizer], ids=["gwo", "hho"])
def test_mixed_objective_execution_is_preserved_and_reset_per_solve(
    monkeypatch: pytest.MonkeyPatch, solver_type: SolverType
) -> None:
    _require_working_jit()
    compiled_objective = _nb._calculate_tour_length_atsp_numba
    call_count = 0

    def _fail_once(*_args: object, **_kwargs: object) -> float:
        nonlocal call_count
        call_count += 1
        monkeypatch.setattr(
            _nb, "_calculate_tour_length_atsp_numba", compiled_objective
        )
        raise RuntimeError("test-local first objective call failure")

    monkeypatch.setattr(_nb, "_calculate_tour_length_atsp_numba", _fail_once)
    solver = _solver(solver_type, polish_enabled=False, fair=True)
    mixed_result = _solve(solver, _symmetric_matrix())

    assert call_count == 1
    assert mixed_result.extra_stats["execution_backend"] == (
        "objective=numba+python;polish=none"
    )

    monkeypatch.setattr(_nb, "_calculate_tour_length_atsp_numba", compiled_objective)
    compiled_result = _solve(solver, _symmetric_matrix())

    assert compiled_result.extra_stats["execution_backend"] == (
        "objective=numba;polish=none"
    )
