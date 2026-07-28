from __future__ import annotations

from dataclasses import dataclass

import pytest

from academic_benchmark.core.problem_validation import validate_problem_for_preflight
from uniride_core.algorithms.capabilities import ProblemContract


@dataclass
class _Problem:
    name: str = "tiny"
    dimension: int = 3
    problem_type: str = "tsp"
    dist_matrix: object | None = None
    time_matrix: object | None = None
    is_time_matrix: bool = False
    matrix_kind: str = "distance"


def _symmetric_matrix() -> list[list[int]]:
    return [[0, 2, 4], [2, 0, 3], [4, 3, 0]]


def test_validation_returns_frozen_tsp_report_with_stable_fingerprint() -> None:
    problem = _Problem(dist_matrix=_symmetric_matrix())

    first = validate_problem_for_preflight(problem)
    second = validate_problem_for_preflight(problem)

    assert first.problem_name == "tiny"
    assert first.contract is ProblemContract.TSP
    assert first.dimension == 3
    assert first.matrix_kind == "distance"
    assert first.matrix == ((0.0, 2.0, 4.0), (2.0, 0.0, 3.0), (4.0, 3.0, 0.0))
    assert first.matrix_sha256 == second.matrix_sha256
    assert first.observed_asymmetric is False
    with pytest.raises(TypeError):
        first.matrix[0][1] = 9  # type: ignore[index]


def test_validation_honors_declared_atsp_when_matrix_is_symmetric() -> None:
    report = validate_problem_for_preflight(
        _Problem(problem_type="ATSP", dist_matrix=_symmetric_matrix())
    )

    assert report.contract is ProblemContract.ATSP
    assert report.observed_asymmetric is False


def test_validation_uses_time_matrix_when_problem_declares_time_costs() -> None:
    report = validate_problem_for_preflight(
        _Problem(
            dist_matrix=_symmetric_matrix(),
            time_matrix=[[0, 7, 8], [7, 0, 9], [8, 9, 0]],
            is_time_matrix=True,
            matrix_kind="travel_time",
        )
    )

    assert report.matrix_kind == "travel_time"
    assert report.matrix[0][1] == 7.0


def test_validation_prepares_missing_matrix_once_before_extracting_it() -> None:
    class _PreparedProblem(_Problem):
        def __init__(self) -> None:
            super().__init__(dist_matrix=None)
            self.preparations = 0

        def prepare_matrices(self) -> None:
            self.preparations += 1
            self.dist_matrix = _symmetric_matrix()

    problem = _PreparedProblem()

    report = validate_problem_for_preflight(problem)

    assert problem.preparations == 1
    assert report.matrix == ((0.0, 2.0, 4.0), (2.0, 0.0, 3.0), (4.0, 3.0, 0.0))


@pytest.mark.parametrize(
    ("matrix", "dimension", "message"),
    [
        ([[0, 1], [1]], 2, "square"),
        (_symmetric_matrix(), 4, "dimension"),
        ([[0, "bad", 4], [2, 0, 3], [4, 3, 0]], 3, "numeric"),
        ([[0, float("nan"), 4], [2, 0, 3], [4, 3, 0]], 3, "finite"),
        ([[0, -1, 4], [2, 0, 3], [4, 3, 0]], 3, "non-negative"),
    ],
)
def test_validation_rejects_invalid_off_diagonal_cost_matrix(
    matrix: object, dimension: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_problem_for_preflight(_Problem(dist_matrix=matrix, dimension=dimension))


def test_validation_preserves_finite_tsplib_diagonal_sentinel() -> None:
    report = validate_problem_for_preflight(
        _Problem(
            problem_type="atsp",
            dist_matrix=[[9999999, 2, 8], [6, 9999999, 3], [4, 7, 9999999]],
        )
    )

    assert report.matrix[0][0] == 9999999.0
    assert report.contract is ProblemContract.ATSP
    assert report.observed_asymmetric is True


def test_validation_rejects_non_tsp_contract() -> None:
    with pytest.raises(ValueError, match="TSP or ATSP"):
        validate_problem_for_preflight(_Problem(problem_type="cvrp", dist_matrix=_symmetric_matrix()))
