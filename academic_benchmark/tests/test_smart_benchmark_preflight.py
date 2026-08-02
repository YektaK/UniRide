"""Task C1.9: Smart Benchmark and CLI governed entrypoint preflight."""

from __future__ import annotations

import concurrent.futures
import csv
import json
import pickle
import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from academic_benchmark import cli_engine, smart_benchmark
from academic_benchmark.core.algorithm_errors import (BackendUnavailableError, CandidateAlgorithmError, ExecutorUnavailableError, PlannedAlgorithmError, ResultContractViolation, UnsupportedProtocolError)
from academic_benchmark.engine_core import BenchmarkConfig, BenchmarkTask, GovernedExecutionRequest, RunResult
from academic_benchmark.core.preflight import RuntimeBackendAvailability
from uniride_core.algorithms.capabilities import (
    BackendPolicy,
    CAPABILITY_CATALOG,
    ExecutionProtocol,
    LifecycleStatus,
)


@dataclass
class _Problem:
    name: str = "entrypoint-atsp"
    problem_type: str = "atsp"
    dimension: int = 3
    optimal: float | None = None
    dist_matrix: list[list[float]] | None = None
    coordinates: list[tuple[float, float]] | None = None
    category: str = "test"
    source: str = "task9-fixture"
    is_time_matrix: bool = False

    def __post_init__(self) -> None:
        if self.dist_matrix is None:
            self.dist_matrix = [[0.0, 2.0, 7.0], [5.0, 0.0, 3.0], [4.0, 9.0, 0.0]]
        if self.coordinates is None:
            self.coordinates = [(0.0, 0.0), (2.0, 0.0), (0.0, 3.0)]


def _request(**changes: object) -> GovernedExecutionRequest:
    values = {
        "requested_algorithm_id": "Core-TwoOpt-TSP",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "protocol": ExecutionProtocol.FIXED_BUDGET,
        "evaluation_budget": 10,
        "backend_policy": BackendPolicy.PYTHON_ONLY,
    }
    values.update(changes)
    return GovernedExecutionRequest(**values)


def _valid_result() -> RunResult:
    result = RunResult(
        problem="entrypoint-atsp", algorithm="Core-TwoOpt-TSP", run=0, seed=1000,
        dimension=3, optimal=None, tour_cost=9.0, objective_cost=9.0,
        gap_pct=None, elapsed_sec=0.01, evaluations=7, tour=[1, 2, 3],
    )
    result.algorithm_id = "Core-TwoOpt-TSP"
    result.objective_evaluations = 7
    result.evaluation_budget = 10
    result.budget_terminated = False
    result.termination_reason = "no_improving_move"
    result.execution_backend = "objective=python;polish=none"
    return result


def _decision(
    *,
    requested_id: str = "Core-TwoOpt-TSP",
    backend_policy: BackendPolicy = BackendPolicy.PYTHON_ONLY,
    fallback_reason: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        resolution=SimpleNamespace(
            requested_id=requested_id,
            canonical_id="Core-TwoOpt-TSP",
        ),
        backend_policy=backend_policy,
        selected_backend=SimpleNamespace(
            objective=SimpleNamespace(value="python"),
            polish=SimpleNamespace(value="none"),
        ),
        fallback_reason=fallback_reason,
        executor_registry_id="Core-TwoOpt-TSP",
        evidence_ids=("test-evidence-node",),
    )

def test_governed_request_and_task_are_picklable() -> None:
    request = _request()
    task = BenchmarkTask("p", "Core-TwoOpt-TSP", 1, 42, {}, request)

    restored = pickle.loads(pickle.dumps(task))

    assert restored.governed_request == request
    assert restored.governed_request.canonical_algorithm_id == "Core-TwoOpt-TSP"


def test_cli_governed_task_uses_gateway_without_legacy_direct_fallback(monkeypatch) -> None:
    def direct_fallback(*_args, **_kwargs):
        raise AssertionError("governed TSP reached direct run_single_test fallback")

    from uniride_core.algorithms import numba_metaheuristics

    monkeypatch.setattr(numba_metaheuristics, "run_single_test", direct_fallback)
    observed = {}

    def gateway(**kwargs):
        observed.update(kwargs)
        return _valid_result(), _decision(requested_id="Numba-2-opt")

    monkeypatch.setattr(cli_engine, "execute_preflighted", gateway)
    task = (
        cli_engine._make_problem_dict(_Problem()), "Core-TwoOpt-TSP", "Core-TwoOpt-TSP",
        {}, 0, 1, _request(requested_algorithm_id="Numba-2-opt"),
    )

    with pytest.warns(DeprecationWarning, match="Numba-2-opt"):
        result = cli_engine._evaluate_param_combo(task)

    assert result["algorithm_id"] == "Core-TwoOpt-TSP"
    assert observed["requested_algorithm_id"] == "Numba-2-opt"
    assert observed["evaluation_budget"] == 10
    assert result["preflight_decision_metadata"] == {
        "requested_algorithm_id": "Numba-2-opt",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "backend_policy": "python_only",
        "backend_profile": {"objective": "python", "polish": "none"},
        "backend_fallback_used": False,
        "backend_fallback_reason": None,
        "executor_registry_id": "Core-TwoOpt-TSP",
        "capability_evidence_ids": ["test-evidence-node"],
    }


def test_cli_worker_rejects_ungoverned_catalog_task_before_registry_access(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("registry enumeration occurred")

        @staticmethod
        def get_executor(_algorithm_id):
            raise AssertionError("registry lookup occurred")

    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)
    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    task = (
        cli_engine._make_problem_dict(_Problem()),
        "Core-TwoOpt-TSP",
        "Core-TwoOpt-TSP",
        {},
        0,
        1,
    )

    with pytest.raises(ExecutorUnavailableError, match="GovernedExecutionRequest"):
        cli_engine._evaluate_param_combo(task)


def test_smart_worker_rejects_ungoverned_catalog_task_before_registry_access(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("registry enumeration occurred")

        @staticmethod
        def get_executor(_algorithm_id):
            raise AssertionError("registry lookup occurred")

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", ExplodingRegistry)
    task = BenchmarkTask("entrypoint-atsp", "Core-TwoOpt-TSP", 0, 42, {})

    with pytest.raises(ExecutorUnavailableError, match="GovernedExecutionRequest"):
        smart_benchmark._run_single_task((task, _Problem()))

def test_smart_governed_task_carries_prefer_numba_fallback_provenance(monkeypatch) -> None:
    fallback_reason = "Preferred Numba objective unavailable; selected evidenced Python objective."
    decision = _decision(
        backend_policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE,
        fallback_reason=fallback_reason,
    )
    monkeypatch.setattr(
        smart_benchmark,
        "_preflight_smart_selections",
        lambda *_args: (
            frozenset({"Core-TwoOpt-TSP"}),
            RuntimeBackendAvailability(True, True, "test runtime"),
        ),
    )
    monkeypatch.setattr(
        smart_benchmark,
        "execute_preflighted",
        lambda **_kwargs: (_valid_result(), decision),
    )
    task = BenchmarkTask(
        "entrypoint-atsp",
        "Core-TwoOpt-TSP",
        0,
        42,
        {},
        _request(backend_policy=BackendPolicy.PREFER_NUMBA_OBJECTIVE),
    )

    result = smart_benchmark._run_governed_task(task, _Problem())

    assert result.preflight_decision_metadata == {
        "requested_algorithm_id": "Core-TwoOpt-TSP",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "backend_policy": "prefer_numba_objective",
        "backend_profile": {"objective": "python", "polish": "none"},
        "backend_fallback_used": True,
        "backend_fallback_reason": fallback_reason,
        "executor_registry_id": "Core-TwoOpt-TSP",
        "capability_evidence_ids": ["test-evidence-node"],
    }


def test_smart_persistence_includes_preflight_decision_metadata(monkeypatch) -> None:
    result = _valid_result()
    result.preflight_decision_metadata = {
        "requested_algorithm_id": "Core-TwoOpt-TSP",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "backend_policy": "prefer_numba_objective",
        "backend_profile": {"objective": "python", "polish": "none"},
        "backend_fallback_used": True,
        "backend_fallback_reason": "Preferred Numba objective unavailable.",
        "executor_registry_id": "Core-TwoOpt-TSP",
        "capability_evidence_ids": ["test-evidence-node"],
    }

    class Future:
        def result(self):
            return result

        def cancel(self):
            return True

    future = Future()

    class Executor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, *_args):
            return future

        def shutdown(self, **_kwargs):
            return None

    saved_results = []
    import academic_benchmark.tsplib_manager as tsplib_manager

    monkeypatch.setattr(
        smart_benchmark,
        "_preflight_smart_selections",
        lambda *_args: (
            frozenset({"Core-TwoOpt-TSP"}),
            RuntimeBackendAvailability(True, True, "test runtime"),
        ),
    )
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_args: None)
    monkeypatch.setattr(smart_benchmark, "ProcessPoolExecutor", Executor)
    monkeypatch.setattr(
        smart_benchmark.concurrent.futures,
        "as_completed",
        lambda futures: list(futures),
    )
    monkeypatch.setattr(smart_benchmark, "_check_interrupt_key", lambda: False)
    monkeypatch.setattr(smart_benchmark, "_save_best_solution", lambda **_kwargs: None)
    monkeypatch.setattr(smart_benchmark, "save_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(smart_benchmark, "_current_results", [])
    monkeypatch.setattr(smart_benchmark, "_current_metadata", {})
    monkeypatch.setattr(smart_benchmark, "_shutdown_requested", False)
    monkeypatch.setattr(tsplib_manager, "save_benchmark_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        tsplib_manager,
        "save_benchmark_result",
        lambda _run_id, payload, **_kwargs: saved_results.append(payload),
    )

    smart_benchmark.run_unified_benchmark(
        [_Problem()],
        ["Core-TwoOpt-TSP"],
        "default",
        1,
        1,
        {"results": {}},
    )

    assert len(saved_results) == 1
    assert saved_results[0]["metadata"] == {
        "param_source": "default",
        **result.preflight_decision_metadata,
    }

def test_cli_governed_candidate_rejects_before_registry_or_direct_fallback(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("candidate reached registry enumeration")

    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)
    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    task = (
        cli_engine._make_problem_dict(_Problem()), "Core-GA-TSP", "Core-GA-TSP",
        {}, 0, 1, _request(
            requested_algorithm_id="Core-GA-TSP",
            canonical_algorithm_id="Core-GA-TSP",
        ),
    )

    with pytest.raises(CandidateAlgorithmError):
        cli_engine._evaluate_param_combo(task)


@pytest.mark.parametrize(
    "argv",
    [
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP"],
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP", "--execution-protocol", "fixed_evaluation_budget", "--backend-policy", "python_only"],
        ["--mode", "default", "--algos", "Core-TwoOpt-TSP", "--execution-protocol", "algorithm_native_termination", "--evaluation-budget", "10", "--backend-policy", "python_only"],
    ],
)
def test_cli_governed_configuration_fails_exit_2_before_setup(monkeypatch, argv) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("governed CLI validation reached setup")

    monkeypatch.setattr(cli_engine, "_ensure_dirs", explode)
    monkeypatch.setattr(cli_engine, "_all_strategy_specs", explode)

    assert cli_engine.main(argv) == 2


def test_cli_governed_configuration_resolves_before_registry_enumeration(monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("forbidden identifier reached setup")

    monkeypatch.setattr(cli_engine, "_ensure_dirs", explode)
    monkeypatch.setattr(cli_engine, "_all_strategy_specs", explode)

    assert cli_engine.main([
        "--mode", "default", "--algos", "GWO-LKH",
        "--execution-protocol", "fixed_evaluation_budget", "--evaluation-budget", "10",
        "--backend-policy", "python_only",
    ]) == 2


def test_smart_worker_postflight_violation_raises_and_is_not_converted_to_error(monkeypatch) -> None:
    class Registry:
        @staticmethod
        def list_algorithms():
            return ["Core-TwoOpt-TSP"]

        @staticmethod
        def get_executor(_algorithm_id):
            return lambda *_args: RunResult(
                problem="entrypoint-atsp", algorithm="Core-TwoOpt-TSP", run=0, seed=42,
                dimension=3, optimal=None, tour_cost=999.0, objective_cost=999.0,
                gap_pct=None, elapsed_sec=0.0, evaluations=1, tour=[1, 2, 3],
            )

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)
    task = BenchmarkTask("entrypoint-atsp", "Core-TwoOpt-TSP", 0, 42, {}, _request())

    with pytest.raises(ResultContractViolation):
        smart_benchmark._run_single_task((task, _Problem()))


def test_smart_selection_excludes_candidate_catalog_ids(monkeypatch) -> None:
    class Registry:
        @staticmethod
        def list_algorithms():
            return ["Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-GWO-TSP-Pure", "Core-Greedy-Routing"]

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)

    assert smart_benchmark._selectable_algorithm_ids() == [
        "Core-TwoOpt-TSP", "Core-ThreeOpt-TSP", "Core-GWO-TSP-Pure",
        "Core-Greedy-Routing",
    ]


def test_cli_task_builder_preserves_legacy_tuple_and_adds_governed_request() -> None:
    legacy = cli_engine.StrategySpec("Core-Greedy-Routing", "Core-Greedy-Routing", {}, "routing")
    governed = cli_engine.StrategySpec("Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, "local_search", _request())

    assert len(cli_engine._make_param_combo_task(_Problem(), legacy, {}, 1, 1)) == 6
    task = cli_engine._make_param_combo_task(_Problem(), governed, {}, 1, 1)
    assert task[6] == governed.governed_request

def test_smart_selection_excludes_every_raw_governed_alias_and_preserves_non_c1(monkeypatch) -> None:
    verified_ids = [
        algorithm_id
        for algorithm_id, capability in CAPABILITY_CATALOG.items()
        if capability.lifecycle is LifecycleStatus.VERIFIED
    ]

    class Registry:
        @staticmethod
        def list_algorithms():
            return [
                *CAPABILITY_CATALOG,
                "Numba-2-opt", "Numba-3-opt-bounded", "Numba-Or-opt",
                "Numba-GA", "Numba-PSO", "GWO", "HHO", "Numba-GWO",
                "Core-GWO-TSP", "Numba-HHO", "Core-HHO-TSP",
                "SOTA-ALNS-TSP",
                "Core-Greedy-Routing",
            ]

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)

    assert smart_benchmark._selectable_algorithm_ids() == [
        *verified_ids,
        "Core-Greedy-Routing",
    ]


@pytest.mark.parametrize("algorithm_id", ["Core-GA-TSP", "Numba-GA"])
def test_smart_public_runner_rejects_governed_candidate_before_setup(monkeypatch, algorithm_id) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("governed candidate reached Smart setup")

    monkeypatch.setattr(smart_benchmark, "_db_get_best", explode)
    monkeypatch.setattr(smart_benchmark, "_dm_from_cache", explode)
    monkeypatch.setattr(smart_benchmark, "run_warmup", explode)
    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", type("Registry", (), {"list_algorithms": staticmethod(explode)}))

    with pytest.raises(CandidateAlgorithmError):
        smart_benchmark.run_unified_benchmark([_Problem()], [algorithm_id], "db", 1, 1, {"results": {}})


def test_optuna_governed_contract_failure_is_not_converted_to_infinite_trial(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise ResultContractViolation("postflight mismatch")

    monkeypatch.setattr(cli_engine, "_evaluate_param_combo", fail)
    with pytest.raises(ResultContractViolation):
        cli_engine._run_numba_trial_task({
            "problem_dict": {}, "spec_name": "Core-TwoOpt-TSP", "spec_payload": "Core-TwoOpt-TSP",
            "spec_defaults": {}, "algorithm_type": "local_search", "params": {}, "n_runs": 1,
            "trial_number": 1, "study_name": "governed", "governed_request": _request(),
        })

def test_cli_pool_reraises_governed_selection_failure(monkeypatch) -> None:
    class Future:
        def result(self):
            raise ResultContractViolation("contract failure")

    class Executor:
        def __init__(self, **_kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def submit(self, *_args):
            return Future()

    monkeypatch.setattr(cli_engine.concurrent.futures, "ProcessPoolExecutor", Executor)
    monkeypatch.setattr(cli_engine.concurrent.futures, "as_completed", lambda futures: list(futures))
    task = (cli_engine._make_problem_dict(_Problem()), "Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, 0, 1, _request())

    with pytest.raises(ResultContractViolation):
        cli_engine._run_pool([task], 2)


def test_cli_batch_aborts_before_metadata_persistence_on_governed_failure(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise ResultContractViolation("contract failure")

    monkeypatch.setattr(cli_engine, "_run_pool", fail)
    monkeypatch.setattr(cli_engine, "save_metadata", lambda *_args, **_kwargs: pytest.fail("governed failure persisted metadata"))
    task = (cli_engine._make_problem_dict(_Problem()), "Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, 0, 1, _request())

    with pytest.raises(ResultContractViolation):
        cli_engine._execute_benchmark_tasks([task], 1, {}, "TEST")

def test_cli_alias_selection_uses_canonical_spec_and_governed_request() -> None:
    spec = cli_engine.StrategySpec("Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, "local_search")

    selected = cli_engine._select_cli_specs(
        [spec], ["Numba-2-opt"], "fixed_evaluation_budget", 10, "python_only"
    )

    assert selected[0].name == "Core-TwoOpt-TSP"
    assert selected[0].governed_request is not None
    assert selected[0].governed_request.requested_algorithm_id == "Numba-2-opt"


def test_cli_candidate_alias_fails_instead_of_becoming_zero_tasks() -> None:
    with pytest.raises(CandidateAlgorithmError):
        cli_engine._select_cli_specs(
            [], ["Numba-GA"], "fixed_evaluation_budget", 10, "python_only"
        )


def test_cli_config_governed_spec_requires_explicit_execution_request() -> None:
    spec = cli_engine.StrategySpec("Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, "local_search")

    with pytest.raises(ValueError, match="execution-protocol"):
        cli_engine._govern_selected_specs([spec], None, None, None)

@pytest.mark.parametrize(
    ("algorithm_id", "error_type"),
    [
        ("Numba-GA", CandidateAlgorithmError),
        ("Core-GWO-TSP-Memetic-3opt", PlannedAlgorithmError),
    ],
)
def test_smart_selection_rejects_lifecycle_before_runtime_or_registry(monkeypatch, algorithm_id, error_type) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("selection reached runtime or registry setup")

    monkeypatch.setattr(smart_benchmark, "probe_runtime_backends", explode)
    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", type("Registry", (), {"list_algorithms": staticmethod(explode)}))

    with pytest.raises(error_type):
        smart_benchmark.run_unified_benchmark([_Problem()], [algorithm_id], "default", 1, 1, {"results": {}})


def test_smart_governed_request_uses_caller_declared_backend_policy() -> None:
    request = smart_benchmark._governed_request_for_smart(
        "GWO", BackendPolicy.REQUIRE_NUMBA_OBJECTIVE
    )

    assert request is not None
    assert request.requested_algorithm_id == "GWO"
    assert request.canonical_algorithm_id == "Core-GWO-TSP-Pure"
    assert request.backend_policy is BackendPolicy.REQUIRE_NUMBA_OBJECTIVE


def test_smart_protocol_preflight_rejects_before_runtime_or_registry(monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("protocol failure reached runtime or registry setup")

    monkeypatch.setattr(smart_benchmark, "probe_runtime_backends", explode)
    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", type("Registry", (), {"list_algorithms": staticmethod(explode)}))

    with pytest.raises(UnsupportedProtocolError):
        smart_benchmark._preflight_smart_selections(
            [_Problem()],
            [_request(evaluation_budget=None)],
        )


def test_smart_preflight_uses_registry_snapshot_for_executor_and_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        smart_benchmark,
        "probe_runtime_backends",
        lambda: RuntimeBackendAvailability(True, False, "test runtime"),
    )
    monkeypatch.setattr(
        smart_benchmark,
        "AlgorithmRegistry",
        type("Registry", (), {"list_algorithms": staticmethod(lambda: [])}),
    )

    with pytest.raises(ExecutorUnavailableError):
        smart_benchmark._preflight_smart_selections([_Problem()], [_request()])

    monkeypatch.setattr(
        smart_benchmark,
        "AlgorithmRegistry",
        type("Registry", (), {"list_algorithms": staticmethod(lambda: ["Core-TwoOpt-TSP"])}),
    )
    monkeypatch.setattr(
        smart_benchmark,
        "probe_runtime_backends",
        lambda: RuntimeBackendAvailability(False, False, "test runtime"),
    )
    with pytest.raises(BackendUnavailableError):
        smart_benchmark._preflight_smart_selections([_Problem()], [_request()])

def test_smart_public_runner_reraises_governed_postflight_without_persistence(monkeypatch) -> None:
    class Future:
        def cancel(self):
            self.cancelled = True
        def result(self):
            raise ResultContractViolation("postflight mismatch")

    future = Future()

    class Executor:
        def __init__(self, **_kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def submit(self, *_args):
            return future
        def shutdown(self, **_kwargs):
            return None

    def explode(*_args, **_kwargs):
        raise AssertionError("governed failure reached persistence")

    monkeypatch.setattr(smart_benchmark, "_preflight_smart_selections", lambda *_args: (frozenset(), RuntimeBackendAvailability(True, True, "test")))
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_args: None)
    monkeypatch.setattr(smart_benchmark, "ProcessPoolExecutor", Executor)
    monkeypatch.setattr(smart_benchmark.concurrent.futures, "as_completed", lambda futures: list(futures))
    monkeypatch.setattr(smart_benchmark, "save_metadata", explode)
    monkeypatch.setattr(smart_benchmark, "_save_best_solution", explode)

    with pytest.raises(ResultContractViolation):
        smart_benchmark.run_unified_benchmark([_Problem()], ["Core-TwoOpt-TSP"], "default", 1, 1, {"results": {}})

    assert future.cancelled


def test_cli_and_smart_reject_unapproved_numba_tsp_ids(monkeypatch) -> None:
    class Registry:
        @staticmethod
        def list_algorithms():
            return ["Core-TwoOpt-TSP", "Numba-Swap", "Numba-Hybrid", "Core-Greedy-Routing"]

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", Registry)
    assert smart_benchmark._selectable_algorithm_ids() == ["Core-TwoOpt-TSP", "Core-Greedy-Routing"]

    with pytest.raises(ExecutorUnavailableError):
        cli_engine._select_cli_specs([], ["Numba-Swap"], "fixed_evaluation_budget", 10, "python_only")
    with pytest.raises(ExecutorUnavailableError):
        smart_benchmark.run_unified_benchmark(
            [_Problem()], ["Numba-Hybrid"], "default", 1, 1, {"results": {}}
        )


def test_optuna_coordinator_reraises_governed_failure_without_tell_or_save(monkeypatch) -> None:
    class Study:
        trials = []
        def ask(self):
            return SimpleNamespace(number=1, params={})
        def tell(self, *_args):
            pytest.fail("governed failure was told as an infinite trial")

    study = Study()
    fake_optuna = SimpleNamespace(
        create_study=lambda **_kwargs: study,
        samplers=SimpleNamespace(TPESampler=lambda **_kwargs: object()),
    )

    class Future:
        cancelled = False
        def cancel(self):
            self.cancelled = True
        def result(self):
            raise ResultContractViolation("postflight mismatch")

    future = Future()

    class Executor:
        def __init__(self, **_kwargs):
            self.shutdown_called = False
        def submit(self, *_args):
            return future
        def shutdown(self, **_kwargs):
            self.shutdown_called = True

    executor = Executor()
    monkeypatch.setitem(sys.modules, "optuna", fake_optuna)
    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", lambda **_kwargs: executor)
    monkeypatch.setattr(concurrent.futures, "wait", lambda futures, **_kwargs: (set(futures), set()))
    monkeypatch.setattr(cli_engine, "save_metadata", lambda *_args, **_kwargs: pytest.fail("governed failure saved progress"))
    spec = cli_engine.StrategySpec("Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {}, "local_search", _request())

    with pytest.raises(ResultContractViolation):
        cli_engine._run_optuna_tuning_flow([_Problem()], [spec], 1, 1, {})

    assert future.cancelled
    assert executor.shutdown_called

def test_smart_governed_batch_is_atomic_after_success_then_failure(monkeypatch) -> None:
    success = _valid_result()

    class Future:
        def __init__(self, result=None, error=None):
            self._result = result
            self._error = error
        def cancel(self):
            return True
        def result(self):
            if self._error:
                raise self._error
            return self._result

    futures = [Future(success), Future(error=ResultContractViolation("postflight mismatch"))]

    class Executor:
        def __init__(self, **_kwargs):
            self.index = 0
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def submit(self, *_args):
            future = futures[self.index]
            self.index += 1
            return future
        def shutdown(self, **_kwargs):
            return None

    writes = []
    import academic_benchmark.tsplib_manager as tsplib_manager
    monkeypatch.setattr(smart_benchmark, "_preflight_smart_selections", lambda *_args: (frozenset(), RuntimeBackendAvailability(True, True, "test")))
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_args: None)
    monkeypatch.setattr(smart_benchmark, "ProcessPoolExecutor", Executor)
    monkeypatch.setattr(smart_benchmark.concurrent.futures, "as_completed", lambda submitted: list(submitted))
    monkeypatch.setattr(smart_benchmark, "save_metadata", lambda *_args, **_kwargs: writes.append("metadata"))
    monkeypatch.setattr(smart_benchmark, "_save_best_solution", lambda *_args, **_kwargs: writes.append("best"))
    monkeypatch.setattr(tsplib_manager, "save_benchmark_run", lambda *_args, **_kwargs: writes.append("run"))
    monkeypatch.setattr(tsplib_manager, "save_benchmark_result", lambda *_args, **_kwargs: writes.append("result"))

    with pytest.raises(ResultContractViolation):
        smart_benchmark.run_unified_benchmark([_Problem()], ["Core-TwoOpt-TSP"], "default", 2, 1, {"results": {}})

    assert writes == []


def test_shared_algorithm_domain_contract_classifies_live_registry_and_routing_aliases() -> None:
    from academic_benchmark.core import registry_setup
    from academic_benchmark.engine_core import (
        AcademicAlgorithmDomain,
        AlgorithmRegistry,
        classify_academic_algorithm_id,
    )
    from academic_benchmark.core.algorithm_resolution import RESOLVER_GOVERNED_IDENTIFIERS

    assert registry_setup is not None
    for algorithm_id in AlgorithmRegistry.list_algorithms():
        assert classify_academic_algorithm_id(algorithm_id, RESOLVER_GOVERNED_IDENTIFIERS) is not AcademicAlgorithmDomain.UNKNOWN
    assert classify_academic_algorithm_id("CVRP-Core-TwoOpt-TSP", RESOLVER_GOVERNED_IDENTIFIERS) is AcademicAlgorithmDomain.NON_C1_ROUTING
    assert classify_academic_algorithm_id("CVRPTW-Core-GA-TSP", RESOLVER_GOVERNED_IDENTIFIERS) is AcademicAlgorithmDomain.NON_C1_ROUTING
    assert classify_academic_algorithm_id("Numba-Swap", RESOLVER_GOVERNED_IDENTIFIERS) is AcademicAlgorithmDomain.UNCATALOGED_TSP_ATSP
    assert classify_academic_algorithm_id("Numba-Hybrid", RESOLVER_GOVERNED_IDENTIFIERS) is AcademicAlgorithmDomain.UNCATALOGED_TSP_ATSP
    assert classify_academic_algorithm_id("Future-TSP", RESOLVER_GOVERNED_IDENTIFIERS) is AcademicAlgorithmDomain.UNKNOWN
    routing_spec = cli_engine.StrategySpec("CVRP-Core-TwoOpt-TSP", "CVRP-Core-TwoOpt-TSP", {}, "routing")
    assert cli_engine._select_cli_specs(
        [routing_spec], [routing_spec.name], None, None, None
    )[0].governed_request is None

def test_benchmark_config_json_roundtrips_governed_and_legacy_tasks() -> None:
    governed = BenchmarkTask("p", "Core-TwoOpt-TSP", 1, 42, {}, _request())
    legacy = BenchmarkTask("routing", "CVRP-Core-TwoOpt-TSP", 1, 43, {})

    restored = BenchmarkConfig.from_json(BenchmarkConfig("cfg", "now", [governed, legacy]).to_json())

    assert restored.tasks == [governed, legacy]
    assert pickle.loads(pickle.dumps(restored.tasks[0].governed_request)) == _request()


@pytest.mark.parametrize(
    "request_payload",
    [
        {"requested_algorithm_id": "Core-TwoOpt-TSP"},
        {"requested_algorithm_id": "Core-TwoOpt-TSP", "canonical_algorithm_id": "Core-TwoOpt-TSP", "protocol": "bad", "evaluation_budget": 1, "backend_policy": "python_only"},
    ],
)
def test_benchmark_config_rejects_malformed_governed_request(request_payload) -> None:
    import json
    payload = {"name": "bad", "created_at": "now", "tasks": [{"problem_name": "p", "algorithm": "Core-TwoOpt-TSP", "run_idx": 1, "seed": 1, "params": {}, "governed_request": request_payload}]}

    with pytest.raises(ValueError, match="governed_request"):
        BenchmarkConfig.from_json(json.dumps(payload))


@pytest.mark.parametrize("algorithm", ["Numba-Swap", "Numba-Hybrid"])
def test_legacy_smart_config_rejects_uncataloged_tsp_before_setup(monkeypatch, algorithm) -> None:
    def explode(*_args, **_kwargs):
        raise AssertionError("legacy config reached setup")

    monkeypatch.setattr(smart_benchmark, "_dm_from_cache", explode)
    monkeypatch.setattr(smart_benchmark, "run_warmup", explode)
    config = BenchmarkConfig("bad", "now", [BenchmarkTask("entrypoint-atsp", algorithm, 1, 1, {})])

    with pytest.raises(ExecutorUnavailableError):
        smart_benchmark.run_benchmark(config, [_Problem()], {}, 1)


def test_legacy_smart_config_requires_request_for_catalog_task_before_setup(monkeypatch) -> None:
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_args: pytest.fail("ungoverned catalog config reached warmup"))
    config = BenchmarkConfig("bad", "now", [BenchmarkTask("entrypoint-atsp", "Core-TwoOpt-TSP", 1, 1, {})])

    with pytest.raises(ValueError, match="GovernedExecutionRequest"):
        smart_benchmark.run_benchmark(config, [_Problem()], {}, 1)

def test_cli_persistence_includes_preflight_decision_metadata(monkeypatch) -> None:
    decision_metadata = {
        "requested_algorithm_id": "Numba-2-opt",
        "canonical_algorithm_id": "Core-TwoOpt-TSP",
        "backend_policy": "prefer_numba_objective",
        "backend_profile": {"objective": "python", "polish": "none"},
        "backend_fallback_used": True,
        "backend_fallback_reason": "Preferred Numba objective unavailable.",
        "executor_registry_id": "Core-TwoOpt-TSP",
        "capability_evidence_ids": ["test-evidence-node"],
    }
    aggregate = {
        "problem": "entrypoint-atsp",
        "strategy": "Core-TwoOpt-TSP",
        "avg_length": 9.0,
        "avg_gap": float("nan"),
        "avg_time_ms": 1.0,
        "n_runs": 1,
        "params": {},
        "problem_type": "atsp",
        "matrix_kind": "distance",
        "objective_cost": 9.0,
        "routes": [[1, 2, 3]],
        "route_loads": None,
        "route_costs": [9.0],
        "num_vehicles": 1,
        "capacity_violations": 0,
        "tw_violations": 0,
        "preflight_decision_metadata": decision_metadata,
    }
    task = (
        cli_engine._make_problem_dict(_Problem()),
        "Core-TwoOpt-TSP",
        "Core-TwoOpt-TSP",
        {},
        0,
        1,
        _request(requested_algorithm_id="Numba-2-opt"),
    )
    saved_results = []
    import academic_benchmark.tsplib_manager as tsplib_manager

    monkeypatch.setattr(cli_engine, "_run_pool", lambda *_args, **_kwargs: [aggregate])
    monkeypatch.setattr(cli_engine, "append_csv_row", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_engine, "save_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_engine, "_active_results", [])
    monkeypatch.setattr(tsplib_manager, "save_benchmark_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        tsplib_manager,
        "save_benchmark_result",
        lambda _run_id, payload, **_kwargs: saved_results.append(payload),
    )

    rows = cli_engine._execute_benchmark_tasks([task], 1, {}, "C1")

    assert len(saved_results) == 1
    assert saved_results[0]["metadata"] == {
        "n_runs": 1,
        "stage": "C1",
        **decision_metadata,
    }
    assert json.loads(rows[0]["preflight_decision_metadata_json"]) == decision_metadata

def test_cli_worker_rejects_mismatched_governed_request_before_registry(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("mismatched request reached registry enumeration")

    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)
    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    task = (
        cli_engine._make_problem_dict(_Problem()),
        "Core-TwoOpt-TSP",
        "Core-TwoOpt-TSP",
        {},
        0,
        1,
        _request(
            requested_algorithm_id="Core-ThreeOpt-TSP",
            canonical_algorithm_id="Core-ThreeOpt-TSP",
        ),
    )

    with pytest.raises(ExecutorUnavailableError, match="does not match task"):
        cli_engine._evaluate_param_combo(task)


def test_cli_worker_rejects_governed_request_on_non_c1_task(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("non-C1 request reached registry enumeration")

    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)
    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    task = (
        cli_engine._make_problem_dict(_Problem()),
        "Core-Greedy-Routing",
        "Core-Greedy-Routing",
        {},
        0,
        1,
        _request(),
    )

    with pytest.raises(ExecutorUnavailableError, match="non-C1"):
        cli_engine._evaluate_param_combo(task)


def test_smart_worker_rejects_mismatched_governed_request_before_registry(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("mismatched request reached registry enumeration")

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", ExplodingRegistry)
    task = BenchmarkTask(
        "entrypoint-atsp",
        "Core-TwoOpt-TSP",
        0,
        42,
        {},
        _request(
            requested_algorithm_id="Core-ThreeOpt-TSP",
            canonical_algorithm_id="Core-ThreeOpt-TSP",
        ),
    )

    with pytest.raises(ExecutorUnavailableError, match="does not match task"):
        smart_benchmark._run_single_task((task, _Problem()))


def test_smart_worker_rejects_governed_request_on_non_c1_task(monkeypatch) -> None:
    class ExplodingRegistry:
        @staticmethod
        def get_executor(_algorithm_id):
            raise AssertionError("non-C1 request reached registry lookup")

    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", ExplodingRegistry)
    task = BenchmarkTask(
        "entrypoint-atsp",
        "Core-Greedy-Routing",
        0,
        42,
        {},
        _request(),
    )

    with pytest.raises(ExecutorUnavailableError, match="non-C1"):
        smart_benchmark._run_single_task((task, _Problem()))


def test_smart_worker_preserves_forbidden_migration_error_ordering() -> None:
    replacement_id = "Core-GA-TSP"
    legacy_id = next(
        algorithm_id
        for algorithm_id, replacement in cli_engine.LEGACY_ALGORITHM_MIGRATIONS.items()
        if replacement == replacement_id
    )
    task = BenchmarkTask("entrypoint-atsp", legacy_id, 0, 42, {})

    with pytest.raises(ValueError, match=replacement_id):
        smart_benchmark._run_single_task((task, _Problem()))


def test_append_csv_row_migrates_existing_header_for_preflight_provenance(
    tmp_path,
) -> None:
    from academic_benchmark.benchmark_utils import append_csv_row

    path = tmp_path / "benchmark_progress.csv"
    old_fields = ["problem", "strategy"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=old_fields)
        writer.writeheader()
        writer.writerow({"problem": "old", "strategy": "Core-TwoOpt-TSP"})

    new_fields = [*old_fields, "preflight_decision_metadata_json"]
    append_csv_row(
        str(path),
        new_fields,
        {
            "problem": "new",
            "strategy": "Core-ThreeOpt-TSP",
            "preflight_decision_metadata_json": '{"canonical_algorithm_id":"Core-ThreeOpt-TSP"}',
        },
    )

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == new_fields
    assert rows == [
        {
            "problem": "old",
            "strategy": "Core-TwoOpt-TSP",
            "preflight_decision_metadata_json": "",
        },
        {
            "problem": "new",
            "strategy": "Core-ThreeOpt-TSP",
            "preflight_decision_metadata_json": '{"canonical_algorithm_id":"Core-ThreeOpt-TSP"}',
        },
    ]
