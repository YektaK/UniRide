from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.preflight import RuntimeBackendAvailability

from academic_benchmark.fairness import (
    FairComparisonManifest,
    validate_scientific_alns_params,
)
from academic_benchmark.native_pilot import (
    NativePilotError,
    _native_result_record,
    _execute_preflighted_run,
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
from uniride_core.algorithms.capabilities import BackendKind, BackendPolicy, ExecutionBackendProfile, ExecutionProtocol


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


ALNS_PARAMS = {
    "max_iterations": 8,
    "max_no_improvement": 3,
    "remove_ratio": 0.34,
    "min_remove": 1,
    "segment_length": 2,
    "weight_update_factor": 0.2,
    "use_sa": True,
    "sa_start_temp": 4.0,
    "sa_cooling_rate": 0.9,
}

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
        "Core-TwoOpt-TSP": {
            "max_iterations": 2,
            "first_improvement": False,
        },
        "Core-ThreeOpt-TSP": {
            "max_iterations": 2,
            "first_improvement": True,
            "window": 4,
        },
        "Core-OrOpt-TSP": {
            "max_iterations": 3,
            "first_improvement": False,
            "window": 3,
        },
        "ALNS-TSP": dict(ALNS_PARAMS),
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
    result = _executor("Core-TwoOpt-TSP")(
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
        _executor("Core-TwoOpt-TSP")(
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
            lambda data: data["algorithms"]["Core-ThreeOpt-TSP"].update(window=1),
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
            "Core-TwoOpt-TSP",
            {"max_iterations": 3, "first_improvement": False},
            "2-opt",
            None,
        ),
        (
            "Core-ThreeOpt-TSP",
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
    assert result.execution_backend == "objective=python;polish=none"
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



@pytest.mark.parametrize("algorithm_id", ["Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"])
def test_native_metaheuristic_max_iteration_reason_is_truthful(algorithm_id):
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params.update(max_iterations=1, max_no_improvement=99)
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(_problem(uniform=True), params, 999, 0)
    assert result.iterations == 1
    assert result.termination_reason == "max_iterations"


@pytest.mark.parametrize("algorithm_id", ["Core-TwoOpt-TSP", "Core-ThreeOpt-TSP"])
def test_native_local_no_improvement_reason_is_truthful(algorithm_id):
    params = copy.deepcopy(_algorithm_config()[algorithm_id])
    params.update(max_iterations=5)
    params["native_comparison"] = _native_payload()
    result = _executor(algorithm_id)(_problem(uniform=True), params, 999, 0)
    assert result.iterations == 1
    assert result.termination_reason == "no_improving_move"


def test_native_pilot_rejects_unavailable_numba_before_registry_getter(tmp_path):
    config_path = _write_config(tmp_path, _config())
    output = tmp_path / "native-output"
    lookups: list[str] = []

    def getter(algorithm_id: str):
        lookups.append(algorithm_id)
        raise AssertionError("unavailable runtime reached registry getter")

    runtime = RuntimeBackendAvailability(
        python=True,
        numba_nopython=False,
        detail="deterministic Phase B candidate boundary",
    )
    with pytest.raises(NativePilotError, match="candidate and cannot be selected") as exc_info:
        run_native_pilot(
            config_path,
            output,
            problem_loader=lambda: [
                _problem("tiny-tsp"),
                _problem("tiny-atsp", directed=True),
            ],
            repo_root=tmp_path / "separate-repository-root",
            registry_getter=getter,
            runtime_probe=lambda: runtime,
            registered_algorithms_provider=lambda: APPROVED_NATIVE_ALGORITHMS,
        )

    assert lookups == []
    assert "candidate and cannot be selected" in str(exc_info.value)
    validation = json.loads((output / "validation.json").read_text())
    assert validation["status"] == "failed"
    assert "candidate and cannot be selected" in validation["error"]


def test_native_aggregate_rejects_fixed_protocol_rows():
    fixed_row = {
        "protocol_version": "uniride-fair-tsp-v2",
        "comparison_regime": "fixed_evaluation_budget",
        "evaluation_budget": 100,
    }
    with pytest.raises(NativePilotError, match="foreign protocol"):
        aggregate_native_records([fixed_row], replay_ok=False)


def _assert_direct_canonical_native_evidence(
    algorithm_id: str,
    params: dict[str, Any],
) -> None:
    for directed in (False, True):
        problem = _problem(
            f"evidence-{'atsp' if directed else 'tsp'}",
            directed=directed,
        )
        run_params = {**params, "native_comparison": _native_payload(base_seed=313)}
        first = _executor(algorithm_id)(problem, run_params, 999, 0)
        replay = _executor(algorithm_id)(problem, run_params, 999, 0)

        assert first.algorithm == first.algorithm_id == algorithm_id
        assert sorted(first.tour) == list(range(1, problem.dimension + 1))
        independent = _closed_cost(first.tour, problem.dist_matrix)
        assert first.tour_cost == pytest.approx(independent)
        assert first.objective_cost == pytest.approx(independent)
        assert first.evaluations == first.objective_evaluations > 0
        assert first.evaluation_budget is None
        assert first.budget_terminated is False
        assert first.termination_reason in {"max_iterations", "no_improving_move"}
        assert first.execution_backend == "objective=python;polish=none"
        assert first.polish_policy == {
            "enabled": False,
            "initial": False,
            "periodic": False,
            "final": False,
            "operator": None,
        }
        assert replay.tour == first.tour
        assert replay.objective_cost == first.objective_cost
        assert replay.objective_evaluations == first.objective_evaluations
        assert replay.termination_reason == first.termination_reason


def test_core_two_opt_direct_native_tsp_and_atsp_evidence() -> None:
    _assert_direct_canonical_native_evidence(
        "Core-TwoOpt-TSP",
        {"max_iterations": 3, "first_improvement": False},
    )


def test_core_three_opt_direct_native_tsp_and_atsp_evidence() -> None:
    _assert_direct_canonical_native_evidence(
        "Core-ThreeOpt-TSP",
        {"max_iterations": 2, "first_improvement": True, "window": 4},
    )


@pytest.mark.parametrize(
    ("algorithm_id", "params", "evidence_function"),
    [
        (
            "Core-TwoOpt-TSP",
            {"max_iterations": 3, "first_improvement": False},
            "test_core_two_opt_direct_native_tsp_and_atsp_evidence",
        ),
        (
            "Core-ThreeOpt-TSP",
            {"max_iterations": 2, "first_improvement": True, "window": 4},
            "test_core_three_opt_direct_native_tsp_and_atsp_evidence",
        ),
    ],
)
def test_canonical_local_search_native_primary_and_replay_use_real_gateway(
    tmp_path: Path,
    algorithm_id: str,
    params: dict[str, Any],
    evidence_function: str,
) -> None:
    config = load_native_pilot_config(_write_config(tmp_path, _config()))
    expected_evidence = (
        "academic_benchmark/tests/test_native_termination_protocol.py::"
        + evidence_function
    )

    for directed in (False, True):
        problem = _problem(
            f"gateway-{'atsp' if directed else 'tsp'}",
            directed=directed,
        )
        seed = config.manifest.paired_seed(problem.name, 0)
        run_params = {**params, "native_comparison": config.native_comparison}
        lookups: list[str] = []

        def getter(requested_id: str):
            lookups.append(requested_id)
            return _executor(requested_id)

        primary, decision, elapsed_ms = _execute_preflighted_run(
            requested_algorithm_id=algorithm_id,
            identifier_source=IdentifierSource.MANIFEST,
            problem=problem,
            params=run_params,
            seed=seed,
            run_idx=0,
            protocol=ExecutionProtocol.NATIVE_TERMINATION,
            backend_policy=BackendPolicy.PYTHON_ONLY,
            evaluation_budget=None,
            registered_algorithm_ids=frozenset({algorithm_id}),
            runtime_backends=RuntimeBackendAvailability(True, False, "Python fixture"),
            registry_getter=getter,
        )
        replay, replay_decision, replay_elapsed_ms = _execute_preflighted_run(
            requested_algorithm_id=algorithm_id,
            identifier_source=IdentifierSource.MANIFEST,
            problem=problem,
            params=run_params,
            seed=seed,
            run_idx=0,
            protocol=ExecutionProtocol.NATIVE_TERMINATION,
            backend_policy=BackendPolicy.PYTHON_ONLY,
            evaluation_budget=None,
            registered_algorithm_ids=frozenset({algorithm_id}),
            runtime_backends=RuntimeBackendAvailability(True, False, "Python fixture"),
            registry_getter=getter,
        )
        row = _native_result_record(
            primary,
            problem=problem,
            matrix=problem.dist_matrix,
            matrix_sha256="0" * 64,
            algorithm_id=algorithm_id,
            replicate=0,
            seed=seed,
            config=config,
            decision=decision,
            elapsed_ms=elapsed_ms,
            record_kind="primary",
        )
        replay_row = _native_result_record(
            replay,
            problem=problem,
            matrix=problem.dist_matrix,
            matrix_sha256="0" * 64,
            algorithm_id=algorithm_id,
            replicate=0,
            seed=seed,
            config=config,
            decision=replay_decision,
            elapsed_ms=replay_elapsed_ms,
            record_kind="replay",
        )


        assert lookups == [algorithm_id, algorithm_id]
        independent = _closed_cost(primary.tour, problem.dist_matrix)
        assert primary.tour_cost == pytest.approx(independent)
        assert primary.objective_cost == pytest.approx(independent)
        assert replay_decision == decision
        assert replay.tour == primary.tour
        assert replay.objective_cost == primary.objective_cost
        assert replay.objective_evaluations == primary.objective_evaluations
        assert replay.termination_reason == primary.termination_reason
        assert primary.execution_backend == "objective=python;polish=none"
        assert primary.evaluations == primary.objective_evaluations > 0
        assert primary.evaluation_budget is None
        assert primary.budget_terminated is False
        assert primary.termination_reason in {"max_iterations", "no_improving_move"}
        assert row["backend_policy"] == "python_only"
        assert row["backend_profile"] == {"objective": "python", "polish": "none"}
        assert row["backend_fallback_used"] is False
        assert row["backend_fallback_reason"] is None
        assert row["executor_registry_id"] == algorithm_id
        assert row["capability_evidence_ids"] == [expected_evidence]
        assert replay_row["record_kind"] == "replay"
        assert replay_row["algorithm_id"] == algorithm_id
        assert replay_row["backend_policy"] == "python_only"
        assert replay_row["backend_profile"] == {
            "objective": "python", "polish": "none"
        }
        assert replay_row["executor_registry_id"] == algorithm_id
        assert replay_row["capability_evidence_ids"] == [expected_evidence]


def test_core_or_opt_direct_native_tsp_and_atsp_evidence() -> None:
    _assert_direct_canonical_native_evidence(
        "Core-OrOpt-TSP",
        {"max_iterations": 3, "first_improvement": False, "window": 3},
    )

def test_native_config_admits_canonical_alns_exact_set(tmp_path: Path) -> None:
    config = load_native_pilot_config(_write_config(tmp_path, _config()))
    assert set(config.algorithms) == APPROVED_NATIVE_ALGORITHMS
    assert config.algorithms["ALNS-TSP"] == ALNS_PARAMS


def test_native_alns_invalid_parameters_delegate_to_shared_validator(
    tmp_path: Path,
) -> None:
    invalid = {**ALNS_PARAMS, "max_iterations": True}
    with pytest.raises(ValueError) as shared_error:
        validate_scientific_alns_params(invalid)
    data = _config()
    data["algorithms"]["ALNS-TSP"] = invalid
    with pytest.raises(ValueError) as loader_error:
        load_native_pilot_config(_write_config(tmp_path, data))
    assert str(loader_error.value) == str(shared_error.value)


def test_native_alns_key_admission_precedes_shared_validation(tmp_path: Path) -> None:
    data = _config()
    data["algorithms"]["ALNS-TSP"].pop("min_remove")
    with pytest.raises(NativePilotError, match="ALNS-TSP parameter schema mismatch"):
        load_native_pilot_config(_write_config(tmp_path, data))

def test_native_alns_record_replay_provenance(tmp_path: Path) -> None:
    config = load_native_pilot_config(_write_config(tmp_path, _config()))
    problem = _problem("alns-record")
    params = {**ALNS_PARAMS, "native_comparison": config.native_comparison}
    seed = config.manifest.paired_seed(problem.name, 0)
    decision = SimpleNamespace(resolution=SimpleNamespace(requested_id="ALNS-TSP", canonical_id="ALNS-TSP"), backend_policy=BackendPolicy.PYTHON_ONLY, selected_backend=ExecutionBackendProfile(BackendKind.PYTHON), fallback_reason=None, executor_registry_id="ALNS-TSP", evidence_ids=("fixture::ALNS-TSP",))
    rows = [_native_result_record(_executor("ALNS-TSP")(problem, params, seed, 0), problem=problem, matrix=problem.dist_matrix, matrix_sha256="0" * 64, algorithm_id="ALNS-TSP", replicate=0, seed=seed, config=config, decision=decision, elapsed_ms=0.0, record_kind=kind) for kind in ("primary", "replay")]
    primary, replay = rows
    assert primary["algorithm_id"] == "ALNS-TSP" and primary["backend_profile"] == {"objective": "python", "polish": "none"}
    assert primary["capability_evidence_ids"] == ["fixture::ALNS-TSP"]
    assert sorted(primary["tour"]) == list(range(1, problem.dimension + 1))
    assert primary["objective_cost"] == pytest.approx(primary["independent_objective_cost"])
    for field in ("tour", "objective_cost", "objective_evaluations", "iterations", "termination_reason", "execution_backend"):
        assert replay[field] == primary[field]
