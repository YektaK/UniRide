"""Gate C item C-03 (audit H13, L9 seed helper): governed CLI and Smart runs.

Governed entry points must hand the executor a comparison manifest built from the
preflight decision and use the contract seed (SHA-256 over protocol version, base
seed, normalized problem and replicate; never algorithm, combination index or run
order).  All problems here are in-memory; nothing touches a benchmark database.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field

import numpy as np
import pytest

from academic_benchmark import benchmark_utils, cli_engine, smart_benchmark
from academic_benchmark.core.algorithm_errors import AlgorithmSelectionError
from academic_benchmark.core.algorithm_resolution import IdentifierSource
from academic_benchmark.core.execution_gateway import execute_preflighted
from academic_benchmark.core.preflight import RuntimeBackendAvailability
from academic_benchmark.engine_core import (
    GovernedExecutionRequest,
    ProblemInstance,
)
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.capabilities import BackendPolicy, ExecutionProtocol

ALGORITHMS = ("Core-TwoOpt-TSP", "ALNS-TSP", "Core-GWO-TSP-Pure")
BUDGET = 1000
SMART_BASE_SEED = getattr(smart_benchmark, "SMART_GOVERNED_BASE_SEED", 42)
CLI_BASE_SEED = getattr(cli_engine, "CLI_GOVERNED_BASE_SEED", 1000)


def _matrix7() -> list[list[float]]:
    rng = np.random.default_rng(7)
    points = rng.uniform(0.0, 100.0, size=(7, 2))
    matrix = np.rint(np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2) * 10.0) / 10.0
    return matrix.tolist()


@dataclass
class _Problem7:
    name: str = "c03-tsp7"
    problem_type: str = "tsp"
    dimension: int = 7
    optimal: float | None = None
    dist_matrix: list[list[float]] = field(default_factory=_matrix7)
    coordinates: list[tuple[float, float]] = field(
        default_factory=lambda: [(float(i), float(i * i % 5)) for i in range(7)]
    )
    category: str = "test"
    source: str = "c03-fixture"
    is_time_matrix: bool = False


# Fair ALNS runs require the exact scientific parameter set (no hidden defaults,
# fairness.py ALNS_REQUIRED_PARAMS); GWO/HHO write max_no_improvement and max_iterations explicitly on
# fixed-budget paths (A17 2026-10-23; 75 and 250 are the values the registry defaults supplied before);
# 2-opt writes max_iterations (1000 was its registry default).
ALNS_PARAMS = {
    "max_iterations": 8,
    "max_no_improvement": 3,
    "remove_ratio": 0.34,
    "min_remove": 1,
    "segment_length": 2,
    "weight_update_factor": 0.2,
    "use_sa": True,
}


def _params_for(algorithm_id: str) -> dict:
    if algorithm_id == "ALNS-TSP":
        return dict(ALNS_PARAMS)
    if "GWO" in algorithm_id or "HHO" in algorithm_id:
        return {"max_no_improvement": 75, "max_iterations": 250}
    return {"max_iterations": 1000}


def _manifest(base_seed: int) -> FairComparisonManifest:
    return FairComparisonManifest(
        evaluation_budget=BUDGET,
        base_seed=base_seed,
        protocol_version="uniride-fair-tsp-v2",
        comparison_regime="fixed_evaluation_budget",
    )


def _request(algorithm_id: str) -> GovernedExecutionRequest:
    return GovernedExecutionRequest(
        algorithm_id, algorithm_id, ExecutionProtocol.FIXED_BUDGET, BUDGET,
        BackendPolicy.PREFER_NUMBA_OBJECTIVE,
    )


# ---------------------------------------------------------------- Smart ----

def _run_smart(monkeypatch, problem, algorithms, n_runs, param_source="db", log=None, params_for=None):
    import academic_benchmark.tsplib_manager as tsplib_manager

    saved: list[dict] = []
    log = {} if log is None else log
    log.update(run_statuses=[], metadata_saves=[], saved=saved)
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_a: None)
    monkeypatch.setattr(
        smart_benchmark, "ProcessPoolExecutor", concurrent.futures.ThreadPoolExecutor
    )
    monkeypatch.setattr(smart_benchmark, "_check_interrupt_key", lambda: False)
    monkeypatch.setattr(smart_benchmark, "_save_best_solution", lambda **_k: None)
    monkeypatch.setattr(
        smart_benchmark, "save_metadata", lambda *a, **_k: log["metadata_saves"].append(a)
    )
    monkeypatch.setattr(smart_benchmark, "_current_results", [])
    monkeypatch.setattr(smart_benchmark, "_current_metadata", {})
    monkeypatch.setattr(smart_benchmark, "_shutdown_requested", False)
    monkeypatch.setattr(
        smart_benchmark, "_db_get_best",
        lambda _problem, algorithm_id, _db: {"params": (params_for or _params_for)(algorithm_id)},
    )
    monkeypatch.setattr(
        tsplib_manager, "save_benchmark_run",
        lambda _run_id, **kwargs: log["run_statuses"].append(kwargs.get("status")),
    )
    monkeypatch.setattr(
        tsplib_manager, "save_benchmark_result",
        lambda _run_id, payload, **_k: saved.append(payload),
    )
    smart_benchmark.run_unified_benchmark(
        [problem], list(algorithms), param_source, n_runs, 2, {"results": {}}
    )
    return smart_benchmark._current_results, saved


def test_governed_smart_run_produces_validated_results_with_contract_seeds(monkeypatch) -> None:
    results, saved = _run_smart(monkeypatch, _Problem7(), ALGORITHMS, n_runs=2)

    assert len(results) == len(ALGORITHMS) * 2
    manifest = _manifest(SMART_BASE_SEED)
    by_run: dict[int, set[tuple[int, str]]] = {}
    for row in results:
        assert row["algorithm_id"] == row["algorithm"]
        assert row["seed"] == manifest.paired_seed("c03-tsp7", row["run"])
        assert row["seed_group"] == manifest.seed_group("c03-tsp7", row["run"])
        assert 0 < row["objective_evaluations"] <= BUDGET
        by_run.setdefault(row["run"], set()).add((row["seed"], row["seed_group"]))
    assert sorted(by_run) == [1, 2]
    assert all(len(pairs) == 1 for pairs in by_run.values())
    assert by_run[1] != by_run[2]
    # The seed group and base seed are persisted next to the decision metadata
    # (the DB write itself is stubbed out here).
    assert len(saved) == len(ALGORITHMS) * 2
    for payload in saved:
        run_number = payload["run_number"]
        assert payload["metadata"]["seed_group"] == manifest.seed_group("c03-tsp7", run_number)
        assert payload["metadata"]["comparison_base_seed"] == SMART_BASE_SEED


# ------------------------------------------------------------------ CLI ----

def test_governed_cli_run_produces_validated_results_with_contract_seeds() -> None:
    manifest = _manifest(CLI_BASE_SEED)
    problem = cli_engine._make_problem_dict(_Problem7())
    expected = [
        (manifest.paired_seed("c03-tsp7", r), manifest.seed_group("c03-tsp7", r))
        for r in range(2)
    ]
    assert len({seed for seed, _ in expected}) == 2
    for combo_idx in (0, 3):
        for algorithm_id in ALGORITHMS:
            aggregate = cli_engine._evaluate_param_combo(
                (problem, algorithm_id, algorithm_id, _params_for(algorithm_id), combo_idx, 2,
                 _request(algorithm_id))
            )
            rows = aggregate["per_run_fairness"]
            assert [row["algorithm_id"] for row in rows] == [algorithm_id] * 2
            # Same seed and group across algorithms AND across parameter combinations.
            assert [(row["seed"], row["seed_group"]) for row in rows] == expected


# -------------------------------------------------------------- gateway ----

_RUNTIME = RuntimeBackendAvailability(True, True, "test runtime")


class _Stop(Exception):
    pass


def _gateway_call(protocol, budget, base_seed, *, params=None, seed=None, run_idx=2):
    captured: dict = {}
    problem = _Problem7()

    def getter(_algorithm_id):
        def executor(_problem, params_, seed_, run_idx_):
            captured.update(params=dict(params_), seed=seed_, run_idx=run_idx_)
            raise _Stop

        return executor

    if protocol is ExecutionProtocol.FIXED_BUDGET:
        contract = _manifest(base_seed or 0)
    else:
        contract = NativeComparisonManifest(base_seed=base_seed or 0)
    kwargs = dict(
        requested_algorithm_id="Core-TwoOpt-TSP",
        identifier_source=IdentifierSource.INTERNAL,
        problem=problem,
        params=params or {},
        seed=contract.paired_seed(problem.name, run_idx) if seed is None else seed,
        run_idx=run_idx,
        protocol=protocol,
        backend_policy=BackendPolicy.PYTHON_ONLY,
        evaluation_budget=budget,
        registered_algorithm_ids=frozenset({"Core-TwoOpt-TSP"}),
        runtime_backends=_RUNTIME,
        registry_getter=getter,
    )
    if base_seed is not None:
        kwargs["comparison_base_seed"] = base_seed
    try:
        execute_preflighted(**kwargs)
    except _Stop:
        pass
    return captured


def test_gateway_injects_fair_manifest_built_from_the_decision() -> None:
    captured = _gateway_call(ExecutionProtocol.FIXED_BUDGET, BUDGET, 77)
    manifest = captured["params"]["fair_comparison"]
    assert manifest.evaluation_budget == BUDGET
    assert manifest.base_seed == 77
    assert manifest.protocol_version == "uniride-fair-tsp-v2"
    assert manifest.comparison_regime == "fixed_evaluation_budget"
    assert "native_comparison" not in captured["params"]
    assert captured["seed"] == manifest.paired_seed("c03-tsp7", 2)


def test_gateway_injects_native_manifest_for_native_protocol() -> None:
    captured = _gateway_call(ExecutionProtocol.NATIVE_TERMINATION, None, 77)
    manifest = captured["params"]["native_comparison"]
    assert manifest.base_seed == 77
    assert "fair_comparison" not in captured["params"]
    assert captured["seed"] == manifest.paired_seed("c03-tsp7", 2)


def test_gateway_rejects_a_seed_that_is_not_the_contract_seed() -> None:
    with pytest.raises(AlgorithmSelectionError, match="contract seed"):
        _gateway_call(ExecutionProtocol.FIXED_BUDGET, BUDGET, 77, seed=42 + 2)


def test_gateway_rejects_a_preexisting_manifest_when_it_injects_one() -> None:
    with pytest.raises(ValueError, match="already"):
        _gateway_call(
            ExecutionProtocol.FIXED_BUDGET, BUDGET, 77,
            params={"fair_comparison": {"evaluation_budget": BUDGET}},
        )


def test_gateway_without_base_seed_leaves_params_and_seed_untouched() -> None:
    captured = _gateway_call(ExecutionProtocol.FIXED_BUDGET, BUDGET, None, params={"x": 1}, seed=41)
    assert captured["params"] == {"x": 1}
    assert captured["seed"] == 41


# ------------------------------------------------ non-governed unchanged ----

def _cvrp() -> ProblemInstance:
    return ProblemInstance(
        name="c03-cvrp",
        dimension=4,
        coordinates=[],
        problem_type="cvrp",
        dist_matrix=[[0, 10, 10, 10], [10, 0, 1, 1], [10, 1, 0, 1], [10, 1, 1, 0]],
        demands=[0, 1, 1, 1],
        capacities=[2],
        capacity=2,
    )


def test_non_governed_smart_seeds_are_unchanged(monkeypatch) -> None:
    """NON_C1_ROUTING keeps the legacy Smart schedule: seed = 42 + run_idx."""
    results, saved = _run_smart(monkeypatch, _cvrp(), ["Core-Greedy-Routing"], n_runs=3)
    assert sorted(row["seed"] for row in results) == [43, 44, 45]
    assert all("seed_group" not in p["metadata"] for p in saved)


def test_non_governed_cli_seeds_and_tuple_shape_are_unchanged(monkeypatch) -> None:
    """NON_C1_ROUTING keeps six-field tuples and seed = 1000 + combo_idx*100 + run_idx."""
    problem = _cvrp()
    problem_dict = cli_engine._make_problem_dict(problem)
    real_get_executor = cli_engine._AlgoReg.get_executor
    seeds: list[int] = []

    def recording_get_executor(name):
        executor = real_get_executor(name)

        def run(problem_, params, seed, run_idx):
            seeds.append(seed)
            return executor(problem_, params, seed, run_idx)

        return run

    monkeypatch.setattr(cli_engine._AlgoReg, "get_executor", recording_get_executor)
    task = (problem_dict, "Core-Greedy-Routing", "Core-Greedy-Routing", {}, 2, 3)
    assert len(task) == 6
    cli_engine._evaluate_param_combo(task)
    assert seeds == [1200, 1201, 1202]


def test_make_deterministic_seed_is_removed() -> None:
    """L9 seed-helper bullet: the algorithm-name-hashing helper must not exist."""
    assert not hasattr(benchmark_utils, "make_deterministic_seed")


# ----------------------------------------- B1: no silent partial batches ----

def test_governed_smart_batch_aborts_on_any_task_failure_and_saves_nothing(monkeypatch) -> None:
    """ALNS without scientific params raises a plain ValueError.  A governed batch must not
    drop that task, save the other rows and mark the run completed (unification design:
    failures are never dropped silently).  2-opt carries its explicit max_iterations (A17
    2026-10-23), so ALNS is the one failing task; Smart's empty-parameter ``default`` mode
    refuses 2-opt as well (see the test below)."""
    log: dict = {}
    with pytest.raises(ValueError, match="ALNS parameter schema mismatch"):
        _run_smart(
            monkeypatch, _Problem7(), ["Core-TwoOpt-TSP", "ALNS-TSP"], 2,
            param_source="db", log=log,
            params_for=lambda algorithm_id: {} if algorithm_id == "ALNS-TSP" else _params_for(algorithm_id),
        )
    assert log["run_statuses"] == []
    assert log["metadata_saves"] == []
    assert smart_benchmark._current_results == []
    assert log["saved"] == []


@pytest.mark.parametrize("algorithm_id,key", [
    ("Core-TwoOpt-TSP", "max_iterations"),
    ("Core-GWO-TSP-Pure", "max_no_improvement"),
])
def test_governed_smart_default_mode_refuses_algorithms_that_need_explicit_stopping_keys(
    monkeypatch, algorithm_id, key
) -> None:
    """Owner decision 4 (2026-10-23): Smart's ``default`` mode sends empty parameters and is
    given no implicit stopping values; a fixed-budget run that needs one is refused."""
    with pytest.raises(ValueError, match=rf"{algorithm_id}.*{key}"):
        _run_smart(monkeypatch, _Problem7(), [algorithm_id], 1, param_source="default")


def test_non_governed_smart_batch_still_skips_a_failed_task(monkeypatch) -> None:
    """Non-governed batches keep their behaviour: a failed task is reported and skipped."""
    real = smart_benchmark._run_single_task

    def flaky(args):
        task, _problem = args
        if task.run_idx == 2:
            raise RuntimeError("boom")
        return real(args)

    monkeypatch.setattr(smart_benchmark, "_run_single_task", flaky)
    log: dict = {}
    results, saved = _run_smart(
        monkeypatch, _cvrp(), ["Core-Greedy-Routing"], 3, log=log
    )
    assert sorted(row["run"] for row in results) == [1, 3]
    assert len(saved) == 2
    assert "completed" in log["run_statuses"]


def test_governed_legacy_config_batch_aborts_on_any_task_failure_and_saves_nothing(monkeypatch) -> None:
    """Same abort rule in the legacy ``run_benchmark`` loop (config-driven batches)."""
    from academic_benchmark.engine_core import BenchmarkConfig, BenchmarkTask

    saves: list[dict] = []
    metadata_saves: list[tuple] = []
    monkeypatch.setattr(smart_benchmark, "run_warmup", lambda *_a: None)
    monkeypatch.setattr(
        smart_benchmark, "ProcessPoolExecutor", concurrent.futures.ThreadPoolExecutor
    )
    monkeypatch.setattr(smart_benchmark, "_check_interrupt_key", lambda: False)
    monkeypatch.setattr(smart_benchmark, "_save_best_solution", lambda **k: saves.append(k))
    monkeypatch.setattr(
        smart_benchmark, "save_metadata", lambda *a, **_k: metadata_saves.append(a)
    )
    monkeypatch.setattr(smart_benchmark, "_current_results", [])
    monkeypatch.setattr(smart_benchmark, "_current_metadata", {})
    monkeypatch.setattr(smart_benchmark, "_shutdown_requested", False)
    problem = _Problem7()
    tasks = []
    for algorithm_id in ("Core-TwoOpt-TSP", "ALNS-TSP"):
        request = _request(algorithm_id)
        # ALNS-TSP gets no scientific params, so its executor raises a plain ValueError;
        # 2-opt writes its max_iterations explicitly (A17 2026-10-23) and succeeds.
        tasks.append(
            BenchmarkTask(
                problem.name, algorithm_id, 1,
                smart_benchmark._smart_task_seed(request, problem.name, 1),
                {"max_iterations": 1000} if algorithm_id == "Core-TwoOpt-TSP" else {}, request,
            )
        )
    config = BenchmarkConfig("c03-legacy", "now", tasks)
    saved_results: dict = {}

    with pytest.raises(ValueError, match="ALNS parameter schema mismatch"):
        smart_benchmark.run_benchmark(config, [problem], saved_results, 2)

    assert saves == []
    assert metadata_saves == []
    assert smart_benchmark._current_results == []
    assert saved_results == {}


# ------------------------------------------- P2: CLI row provenance --------

def _cli_persisted_rows(monkeypatch, tmp_path, task):
    import academic_benchmark.tsplib_manager as tsplib_manager

    saved: list[dict] = []
    monkeypatch.setattr(cli_engine, "RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(cli_engine, "save_metadata", lambda *_a, **_k: None)
    monkeypatch.setattr(tsplib_manager, "save_benchmark_run", lambda *_a, **_k: None)
    monkeypatch.setattr(
        tsplib_manager, "save_benchmark_result",
        lambda _run_id, payload, **_k: saved.append(payload),
    )
    cli_engine._execute_benchmark_tasks([task], 1, {}, "BENCH")
    return saved


def test_governed_cli_rows_persist_seed_provenance(monkeypatch, tmp_path) -> None:
    problem = cli_engine._make_problem_dict(_Problem7())
    task = (
        problem, "Core-TwoOpt-TSP", "Core-TwoOpt-TSP", {"max_iterations": 1000}, 4, 2,
        _request("Core-TwoOpt-TSP"),
    )
    (payload,) = _cli_persisted_rows(monkeypatch, tmp_path, task)
    manifest = _manifest(CLI_BASE_SEED)
    metadata = payload["metadata"]
    assert metadata["comparison_base_seed"] == CLI_BASE_SEED
    assert metadata["protocol_version"] == "uniride-fair-tsp-v2"
    assert metadata["seed_groups"] == [manifest.seed_group("c03-tsp7", r) for r in range(2)]
    assert metadata["seed_group"] in metadata["seed_groups"]
    assert metadata["canonical_algorithm_id"] == "Core-TwoOpt-TSP"  # decision metadata kept


def test_non_governed_cli_rows_carry_no_seed_provenance(monkeypatch, tmp_path) -> None:
    task = (
        cli_engine._make_problem_dict(_cvrp()), "Core-Greedy-Routing", "Core-Greedy-Routing", {}, 0, 1,
    )
    (payload,) = _cli_persisted_rows(monkeypatch, tmp_path, task)
    for key in ("comparison_base_seed", "protocol_version", "seed_group", "seed_groups"):
        assert key not in payload["metadata"]


def test_gateway_rejects_an_empty_problem_name() -> None:
    problem = _Problem7(name="  ")
    with pytest.raises(AlgorithmSelectionError, match="problem name"):
        execute_preflighted(
            requested_algorithm_id="Core-TwoOpt-TSP",
            identifier_source=IdentifierSource.INTERNAL,
            problem=problem,
            params={},
            seed=1,
            run_idx=0,
            protocol=ExecutionProtocol.FIXED_BUDGET,
            backend_policy=BackendPolicy.PYTHON_ONLY,
            evaluation_budget=BUDGET,
            registered_algorithm_ids=frozenset({"Core-TwoOpt-TSP"}),
            runtime_backends=_RUNTIME,
            registry_getter=lambda _id: (lambda *_a: None),
            comparison_base_seed=7,
        )
