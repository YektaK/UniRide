from __future__ import annotations

import copy
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_pilot import (
    NativePilotError,
    _native_result_record,
    aggregate_native_records,
    load_native_pilot_config,
    run_native_pilot,
)
from academic_benchmark.native_protocol import (
    APPROVED_NATIVE_ALGORITHMS,
    NATIVE_PROTOCOL,
    NATIVE_TERMINATION_REGIME,
    NativeComparisonManifest,
)


@dataclass
class _Problem:
    name: str
    dist_matrix: list[list[float]]
    problem_type: str
    optimal: float = 1.0
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False

    @property
    def dimension(self) -> int:
        return len(self.dist_matrix)

    def prepare_matrices(self) -> None:
        return None


SYMMETRIC = [
    [0, 3, 8, 7, 6, 4],
    [3, 0, 5, 9, 3, 7],
    [8, 5, 0, 4, 8, 6],
    [7, 9, 4, 0, 2, 5],
    [6, 3, 8, 2, 0, 4],
    [4, 7, 6, 5, 4, 0],
]
DIRECTED = [
    [0, 2, 9, 7, 6, 4],
    [8, 0, 3, 9, 2, 7],
    [5, 6, 0, 2, 8, 3],
    [4, 7, 6, 0, 2, 5],
    [9, 3, 7, 8, 0, 2],
    [3, 8, 4, 6, 9, 0],
]
UNIFORM = [[0 if i == j else 1 for j in range(6)] for i in range(6)]


def _problem(name: str = "tiny-tsp", *, directed: bool = False, uniform: bool = False) -> _Problem:
    matrix = UNIFORM if uniform else DIRECTED if directed else SYMMETRIC
    return _Problem(
        name=name,
        dist_matrix=[list(map(float, row)) for row in matrix],
        problem_type="atsp" if directed else "tsp",
        optimal=6.0 if uniform else 18.0,
    )


def _executor(algorithm_id: str):
    from academic_benchmark.engine_core import AlgorithmRegistry
    import academic_benchmark.core.registry_setup  # noqa: F401

    return AlgorithmRegistry.get_executor(algorithm_id)


def _native_payload(base_seed: int = 71) -> dict[str, Any]:
    return {
        "protocol_version": NATIVE_PROTOCOL,
        "comparison_regime": NATIVE_TERMINATION_REGIME,
        "base_seed": base_seed,
    }


def _algorithm_config() -> dict[str, dict[str, Any]]:
    return {
        "Core-GWO-TSP-Pure": {
            "pack_size": 4,
            "max_iterations": 2,
            "max_no_improvement": 1,
        },
        "Core-HHO-TSP-Pure": {
            "hawks": 4,
            "max_iterations": 2,
            "max_no_improvement": 1,
            "dive_count": 1,
        },
        "Numba-2-opt": {
            "max_iterations": 2,
            "first_improvement": False,
        },
        "Numba-3-opt-bounded": {
            "max_iterations": 2,
            "first_improvement": True,
            "window": 4,
        },
    }


def _config() -> dict[str, Any]:
    return {
        "protocol_version": NATIVE_PROTOCOL,
        "comparison_regime": NATIVE_TERMINATION_REGIME,
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": _algorithm_config(),
        "runs": 1,
        "base_seed": 71,
        "workers": 1,
        "replay_replicates": [0],
        "allow_repository_output": False,
        "overwrite": False,
    }


def _write_config(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "native.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    route = [node - 1 for node in tour]
    return sum(matrix[node][route[(index + 1) % len(route)]] for index, node in enumerate(route))


@pytest.mark.parametrize(
    ("protocol_version", "comparison_regime"),
    [
        ("uniride-fair-tsp-v1", None),
        ("uniride-fair-tsp-v2", "fixed_evaluation_budget"),
    ],
)
def test_fixed_protocol_execution_remains_budgeted(protocol_version, comparison_regime):
    fair = {
        "protocol_version": protocol_version,
        "base_seed": 17,
        "evaluation_budget": 20,
        "budget_policy": "atomic_upper_bound_v1",
    }
    if comparison_regime is not None:
        fair["comparison_regime"] = comparison_regime
    result = _executor("Numba-2-opt")(
        _problem(),
        {
            "max_iterations": 3,
            "first_improvement": False,
            "fair_comparison": fair,
        },
        999,
        0,
    )
    assert result.evaluation_budget == 20
    assert 0 < result.objective_evaluations <= 20
    assert result.comparison_regime == "fixed_evaluation_budget"
    assert result.seed == FairComparisonManifest.from_value(fair).paired_seed("tiny-tsp", 0)


def test_registry_rejects_simultaneous_fixed_and_native_payloads():
    with pytest.raises(ValueError, match="mutually exclusive"):
        _executor("Numba-2-opt")(
            _problem(),
            {
                "max_iterations": 1,
                "first_improvement": False,
                "fair_comparison": {
                    "evaluation_budget": 10,
                    "base_seed": 1,
                },
                "native_comparison": _native_payload(),
            },
            1,
            0,
        )


def test_native_config_rejects_evaluation_budget(tmp_path):
    data = _config()
    data["evaluation_budget"] = 100
    with pytest.raises(NativePilotError, match="must not declare evaluation_budget"):
        load_native_pilot_config(_write_config(tmp_path, data))
    with pytest.raises(ValueError, match="must not declare evaluation_budget"):
        NativeComparisonManifest.from_value({"evaluation_budget": 100})


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda data: data.update(workers=2), "workers must be 1"),
        (
            lambda data: data["algorithms"]["Core-GWO-TSP-Pure"].pop("max_no_improvement"),
            "parameter schema mismatch",
        ),
        (
            lambda data: data["algorithms"]["Numba-3-opt-bounded"].update(window=1),
            "window must be an integer >= 2",
        ),
        (
            lambda data: data["algorithms"]["Core-HHO-TSP-Pure"].update(memetic=True),
            "parameter schema mismatch",
        ),
    ],
)
def test_native_config_is_strict(tmp_path, mutate, message):
    data = _config()
    mutate(data)
    with pytest.raises(NativePilotError, match=message):
        load_native_pilot_config(_write_config(tmp_path, data))


@pytest.mark.parametrize(
    ("algorithm_id", "params", "family", "window"),
    [
        (
            "Numba-2-opt",
            {"max_iterations": 3, "first_improvement": False},
            "2-opt",
            None,
        ),
        (
            "Numba-3-opt-bounded",
            {"max_iterations": 2, "first_improvement": True, "window": 4},
            "3-opt",
            4,
        ),
    ],
)
def test_native_local_search_preserves_directed_cycle_and_metadata(
    algorithm_id, params, family, window
):
    problem = _problem("tiny-atsp", directed=True)
    params = {**params, "native_comparison": _native_payload()}
    result = _executor(algorithm_id)(problem, params, 999, 0)
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    assert result.objective_cost == pytest.approx(_closed_cost(result.tour, problem.dist_matrix))
    assert result.algorithm_family == family
    assert result.execution_backend == "python-canonical-matrix"
    assert result.neighborhood_window == window
    assert result.acceptance_policy == (
        "first_improvement" if params["first_improvement"] else "best_improvement"
    )
    assert result.evaluation_budget is None
    assert result.budget_terminated is False
    assert result.objective_evaluations > 0
    assert result.termination_reason in {"max_iterations", "no_improving_move"}


@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"])
def test_native_metaheuristics_use_numba_and_report_actual_counts(algorithm_id):
    problem = _problem("uniform-tsp", uniform=True)
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params.update(max_iterations=10, max_no_improvement=1)
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(problem, params, 999, 0)
    assert sorted(result.tour) == list(range(1, problem.dimension + 1))
    assert result.objective_cost == pytest.approx(_closed_cost(result.tour, problem.dist_matrix))
    assert result.execution_backend == "objective=numba;polish=none"
    assert result.objective_evaluations > 0
    assert result.evaluation_budget is None
    assert result.budget_terminated is False
    assert result.polish_policy == {
        "enabled": False,
        "initial": False,
        "periodic": False,
        "final": False,
        "operator": None,
    }
    assert result.termination_reason == "stagnation_limit"


@pytest.mark.parametrize(
    "execution_backend",
    [
        "numba-objective",
        "objective=numba;polish=python",
        "objective=python+numba;polish=none",
        "objective=numba;polish=none;fallback=python",
    ],
)
def test_native_pilot_rejects_inexact_pure_metaheuristic_backend(
    tmp_path: Path, execution_backend: str
):
    algorithm_id = "Core-GWO-TSP-Pure"
    problem = _problem("uniform-tsp", uniform=True)
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(problem, params, 999, 0)
    config = load_native_pilot_config(_write_config(tmp_path, _config()))

    with pytest.raises(NativePilotError, match="exact pure Numba backend"):
        _native_result_record(
            result=replace(result, execution_backend=execution_backend),
            problem=problem,
            matrix=problem.dist_matrix,
            matrix_sha256="0" * 64,
            algorithm_id=algorithm_id,
            replicate=0,
            seed=999,
            config=config,
            elapsed_ms=0.0,
            record_kind="primary",
        )


@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"])
def test_native_metaheuristic_max_iteration_reason_is_truthful(algorithm_id):
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params.update(max_iterations=1, max_no_improvement=99)
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(_problem(uniform=True), params, 999, 0)
    assert result.iterations == 1
    assert result.termination_reason == "max_iterations"


@pytest.mark.parametrize("algorithm_id", ["Numba-2-opt", "Numba-3-opt-bounded"])
def test_native_local_no_improvement_reason_is_truthful(algorithm_id):
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params.update(max_iterations=5)
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(_problem(uniform=True), params, 999, 0)
    assert result.iterations == 1
    assert result.termination_reason == "no_improving_move"


def test_native_pilot_pairs_seeds_and_replays_all_metadata(tmp_path):
    config_path = _write_config(tmp_path, _config())
    output = tmp_path / "native-output"
    result = run_native_pilot(
        config_path,
        output,
        problem_loader=lambda: [
            _problem("tiny-tsp"),
            _problem("tiny-atsp", directed=True),
        ],
        repo_root=tmp_path / "separate-repository-root",
    )
    assert result["validation"]["status"] == "passed"
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 16
    assert {row["algorithm_id"] for row in rows} == APPROVED_NATIVE_ALGORITHMS
    assert {row["protocol_version"] for row in rows} == {NATIVE_PROTOCOL}
    assert {row["comparison_regime"] for row in rows} == {NATIVE_TERMINATION_REGIME}
    assert {row["evaluation_budget"] for row in rows} == {None}
    assert not any(row["budget_terminated"] for row in rows)

    for problem_name in {row["problem"] for row in rows}:
        primary = [
            row for row in rows
            if row["problem"] == problem_name and row["record_kind"] == "primary"
        ]
        assert len({row["seed"] for row in primary}) == 1
        assert len({row["seed_group"] for row in primary}) == 1
        for row in primary:
            replay = next(
                item for item in rows
                if item["problem"] == problem_name
                and item["algorithm_id"] == row["algorithm_id"]
                and item["record_kind"] == "replay"
            )
            for field in (
                "tour", "objective_cost", "objective_evaluations",
                "termination_reason", "seed", "seed_group",
                "acceptance_policy", "neighborhood_window",
                "initialization_policy", "execution_backend", "polish_policy",
            ):
                assert replay[field] == row[field]

    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["protocol_version"] == NATIVE_PROTOCOL
    assert manifest["comparison_regime"] == NATIVE_TERMINATION_REGIME
    assert "evaluation_budget" not in manifest["configuration"]


def test_native_aggregate_rejects_fixed_protocol_rows():
    fixed_row = {
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
        "evaluation_budget": 100,
    }
    with pytest.raises(NativePilotError, match="foreign protocol"):
        aggregate_native_records([fixed_row], replay_ok=False)