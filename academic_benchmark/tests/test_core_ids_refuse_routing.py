"""Gate C follow-up after C-14: Core-* IDs refuse routing problems (owner 2026-10-21).

Every capability-catalog ID names a TSP/ATSP claim. Handing it a CVRP/CVRPTW problem used to
run a legacy matrix routing engine (or the greedy router) while the row kept the Core-*
label. Now every catalog executor refuses routing problems on every path, before any
evaluation, and the legacy engines stay reachable only under the CVRP-* / CVRPTW-* names.
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import math
import random
import re
import sys
import types
from pathlib import Path

import pytest

import academic_benchmark.core.registry_setup as rs
from academic_benchmark import cli_engine, smart_benchmark
from academic_benchmark.core.algorithm_resolution import (
    CLI_ALIAS_TARGETS,
    IdentifierSource,
    resolve_algorithm_id,
)
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from uniride_core.algorithms.capabilities import (
    BackendPolicy,
    ExecutionProtocol,
    list_algorithm_capabilities,
)

CATALOG_IDS = [capability.canonical_id for capability in list_algorithm_capabilities()]
ROUTING_TYPES = ("cvrp", "cvrptw")

# Routing variants offered by the refusal message. They are NOT claimed to run the same
# engine the Core-* ID ran before (Core-TwoOpt-TSP used the greedy router there).
EXPECTED_ALTERNATIVES = {
    "Core-TwoOpt-TSP": "Core-TwoOpt-TSP",
    "Core-GA-TSP": "Core-GA-TSP",
    "Core-GA-TSP-Memetic-2opt": "Core-GA-TSP",
    "Core-PSO-TSP": "Core-PSO-TSP",
    "Core-GWO-TSP-Pure": "Core-GWO-TSP",
    "Core-GWO-TSP-Memetic-2opt": "Core-GWO-TSP",
    "Core-HHO-TSP-Pure": "Core-HHO-TSP",
    "Core-HHO-TSP-Memetic-2opt": "Core-HHO-TSP",
}

# Eight names that, before this item, had their own registry entry next to the canonical one.
REMOVED_ALIAS_ENTRIES = (
    "Core-GWO-TSP",
    "Core-HHO-TSP",
    "Numba-2-opt",
    "Numba-3-opt-bounded",
    "Numba-Or-opt",
    "Numba-GWO",
    "Numba-HHO",
    "SOTA-ALNS-TSP",
)

FIXTURE = Path(__file__).parent / "fixtures" / "cvrp_alias_golden_pre_core_refusal.json"
FIXTURE25 = Path(__file__).parent / "fixtures" / "cvrp_alias_golden25_pre_core_refusal.json"


def _spy_problem(problem_type: str):
    """No matrix, no coordinates: any evaluation attempt fails with AttributeError."""
    return types.SimpleNamespace(name="spy-" + problem_type, dimension=4, problem_type=problem_type)


def _cvrp() -> ProblemInstance:
    return ProblemInstance(
        name="tiny-cvrp", dimension=5, coordinates=[], problem_type="cvrp",
        dist_matrix=[[0, 10, 10, 10, 12], [10, 0, 1, 1, 5], [10, 1, 0, 1, 5],
                     [10, 1, 1, 0, 5], [12, 5, 5, 5, 0]],
        demands=[0, 1, 1, 1, 1], capacities=[2], capacity=2,
    )


def _cvrptw() -> ProblemInstance:
    return ProblemInstance(
        name="tiny-cvrptw", dimension=4, coordinates=[], problem_type="cvrptw",
        dist_matrix=[[0, 10, 10, 10], [10, 0, 3, 3], [10, 3, 0, 3], [10, 3, 3, 0]],
        demands=[0, 1, 1, 1], capacities=[2], capacity=2,
        time_windows=[(0, 999), (0, 50), (0, 50), (0, 50)], service_times=[0, 0, 0, 0],
        direction="dropoff",
    )


@pytest.fixture
def evaluation_spies(monkeypatch):
    """Fail loudly if any routing engine, matrix builder or routing helper is reached."""
    calls: list[str] = []

    def tripwire(label):
        def _raise(*_a, **_k):
            calls.append(label)
            raise AssertionError(f"evaluation reached: {label}")
        return _raise

    monkeypatch.setattr(rs, "_run_core_routing_executor", tripwire("_run_core_routing_executor"))
    monkeypatch.setattr(rs, "create_matrix_engine", tripwire("create_matrix_engine"))
    monkeypatch.setattr(rs.MatrixBuilder, "to_routing_problem", tripwire("to_routing_problem"))
    return calls


def test_catalog_has_the_expected_shape() -> None:
    assert len(CATALOG_IDS) == 15 and "ALNS-TSP" in CATALOG_IDS


@pytest.mark.parametrize("problem_type", ROUTING_TYPES)
@pytest.mark.parametrize("canonical_id", CATALOG_IDS)
def test_every_catalog_executor_refuses_routing_before_any_evaluation(
    canonical_id, problem_type, evaluation_spies
) -> None:
    executor = AlgorithmRegistry.get_executor(canonical_id)
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        executor(_spy_problem(problem_type), {"max_iterations": 5}, 42, 1)
    message = str(excinfo.value)
    assert canonical_id in message
    assert problem_type.upper() in message.upper()
    assert evaluation_spies == []


@pytest.mark.parametrize("canonical_id", CATALOG_IDS)
def test_refusal_names_a_registered_alternative_or_says_none_exists(canonical_id) -> None:
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        AlgorithmRegistry.get_executor(canonical_id)(_spy_problem("cvrp"), {}, 42, 1)
    message = str(excinfo.value)
    named = set(re.findall(r"\bCVRP(?:TW)?-[A-Za-z0-9-]+[A-Za-z0-9]", message))
    registered = set(AlgorithmRegistry.list_algorithms())
    assert named <= registered, f"message names unregistered alternatives: {named - registered}"
    base = EXPECTED_ALTERNATIVES.get(canonical_id)
    if base is None:
        assert not named
        assert "no CVRP" in message
    else:
        assert named == {f"CVRP-{base}", f"CVRPTW-{base}"}


@pytest.mark.parametrize("canonical_id", ["Core-GA-TSP", "Core-GWO-TSP-Memetic-3opt", "ALNS-TSP"])
def test_refusal_also_beats_scientific_protocol_params(canonical_id, evaluation_spies) -> None:
    executor = AlgorithmRegistry.get_executor(canonical_id)
    for params in ({"fair_comparison": {"x": 1}}, {"native_comparison": {"x": 1}}):
        with pytest.raises(rs.CoreRoutingRefusedError):
            executor(_spy_problem("cvrp"), params, 42, 1)
    assert evaluation_spies == []


def test_every_catalog_executor_is_marked_as_refusing_routing() -> None:
    for canonical_id in CATALOG_IDS:
        assert getattr(AlgorithmRegistry.get_executor(canonical_id), "refuses_routing", False), canonical_id


@pytest.mark.parametrize("problem_type", ROUTING_TYPES)
@pytest.mark.parametrize("canonical_id", CATALOG_IDS)
def test_raw_factory_executor_behind_the_wrapper_also_refuses_routing(
    canonical_id, problem_type, evaluation_spies
) -> None:
    """The refusal must not live only in the registry wrapper: unwrap to the factory executor."""
    wrapped = AlgorithmRegistry.get_executor(canonical_id)
    raw = inspect.unwrap(wrapped)
    assert raw is not wrapped
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        raw(_spy_problem(problem_type), {"max_iterations": 5}, 42, 1)
    assert canonical_id in str(excinfo.value)
    assert evaluation_spies == []


def test_core_greedy_routing_is_a_routing_id_and_still_runs_routing() -> None:
    result = AlgorithmRegistry.get_executor("Core-Greedy-Routing")(_cvrp(), {}, 42, 1)
    assert result.routes and result.problem_type == "cvrp"


@pytest.mark.parametrize("canonical_id", ["Core-TwoOpt-TSP", "Core-GA-TSP"])
def test_tsp_problems_still_run_under_core_ids(canonical_id) -> None:
    problem = ProblemInstance(
        name="tiny-tsp", dimension=4, coordinates=[], problem_type="tsp",
        dist_matrix=[[0, 1, 5, 1], [1, 0, 1, 5], [5, 1, 0, 1], [1, 5, 1, 0]],
    )
    result = AlgorithmRegistry.get_executor(canonical_id)(problem, {"max_iterations": 5}, 42, 1)
    assert result.problem_type == "tsp" and result.tour


# --- CVRP-* / CVRPTW-* names are unchanged -------------------------------------------------

_GOLDEN = json.loads(FIXTURE.read_text(encoding="utf-8"))["results"]


@pytest.mark.parametrize("alias", sorted(_GOLDEN))
def test_routing_aliases_reproduce_the_pre_refusal_results(alias) -> None:
    problem = _cvrp() if alias.startswith("CVRP-") else _cvrptw()
    result = AlgorithmRegistry.get_executor(alias)(problem, {"max_iterations": 5}, 42, 1)
    expected = _GOLDEN[alias]
    assert result.algorithm == expected["algorithm"] == alias
    assert round(float(result.objective_cost), 9) == expected["cost"]
    assert [list(r) for r in result.routes] == expected["routes"]
    assert result.num_vehicles == expected["veh"]


# 25-node seeded instances (the tiny 4-5 node golden above gives every engine the same cost, so
# an engine swap such as GWO -> HHO would survive). Captured on 276f234f, before the refusal.
_GOLDEN25 = json.loads(FIXTURE25.read_text(encoding="utf-8"))


def _matrix25():
    rng = random.Random(14)
    pts = [(rng.randint(0, 100), rng.randint(0, 100)) for _ in range(25)]
    matrix = [[math.hypot(a[0] - b[0], a[1] - b[1]) for b in pts] for a in pts]
    demands = [0] + [rng.randint(1, 4) for _ in range(24)]
    return matrix, demands


def _cvrp25() -> ProblemInstance:
    matrix, demands = _matrix25()
    return ProblemInstance(
        name="golden-cvrp25", dimension=25, coordinates=[], problem_type="cvrp",
        dist_matrix=matrix, demands=demands, capacities=[12], capacity=12,
    )


def _cvrptw25() -> ProblemInstance:
    matrix, demands = _matrix25()
    return ProblemInstance(
        name="golden-cvrptw25", dimension=25, coordinates=[], problem_type="cvrptw",
        dist_matrix=matrix, demands=demands, capacities=[12], capacity=12,
        time_windows=[(0, 100000)] + [(0, 2000)] * 24, service_times=[0] + [5] * 24,
        direction="dropoff",
    )


def test_golden25_instance_is_the_one_that_was_captured() -> None:
    digest = hashlib.sha256(json.dumps(list(_matrix25())).encode()).hexdigest()
    assert digest == _GOLDEN25["matrix_sha256"]
    results = _GOLDEN25["results"]
    assert len(results) == 38
    # the instance separates the engines: GA, PSO, TwoOpt, GWO, HHO and greedy all differ
    costs = {results[f"CVRP-{base}"]["cost"] for base in (
        "Core-GA-TSP", "Core-PSO-TSP", "Core-TwoOpt-TSP", "Core-GWO-TSP", "Core-HHO-TSP",
        "Core-Greedy-Routing")}
    assert len(costs) == 6


@pytest.mark.parametrize("alias", sorted(_GOLDEN25["results"]))
def test_routing_aliases_reproduce_the_25_node_pre_refusal_results(alias) -> None:
    problem = _cvrp25() if alias.startswith("CVRP-") else _cvrptw25()
    result = AlgorithmRegistry.get_executor(alias)(problem, {"max_iterations": 3}, 42, 1)
    expected = _GOLDEN25["results"][alias]
    assert result.algorithm == expected["algorithm"] == alias
    assert round(float(result.objective_cost), 9) == expected["cost"]
    assert [list(r) for r in result.routes] == expected["routes"]
    assert result.num_vehicles == expected["veh"]


def test_routing_alias_table_is_not_renamed() -> None:
    names = set(AlgorithmRegistry.list_algorithms())
    for prefix in ("CVRP", "CVRPTW"):
        for base in rs._ROUTING_ALIAS_ENGINES:
            assert f"{prefix}-{base}" in names


# --- the eight alias names no longer have their own executor --------------------------------


@pytest.mark.parametrize("alias", REMOVED_ALIAS_ENTRIES)
def test_alias_names_have_no_registry_entry_of_their_own(alias) -> None:
    assert alias not in AlgorithmRegistry.list_algorithms()
    with pytest.raises(ValueError, match="not found"):
        AlgorithmRegistry.get_executor(alias)


@pytest.mark.parametrize("alias", REMOVED_ALIAS_ENTRIES)
def test_alias_names_reach_only_the_canonical_executor_through_the_resolver(alias) -> None:
    assert alias in CLI_ALIAS_TARGETS
    resolution = resolve_algorithm_id(alias, IdentifierSource.CLI)
    assert resolution.canonical_id in CATALOG_IDS
    assert resolution.canonical_id in AlgorithmRegistry.list_algorithms()


# --- CLI and Smart ------------------------------------------------------------------------


@pytest.mark.parametrize("canonical_id", ["Core-GA-TSP", "Core-TwoOpt-TSP", "Core-GWO-TSP-Pure"])
def test_cli_never_evaluates_a_core_id_on_a_routing_problem(canonical_id, evaluation_spies) -> None:
    request = cli_engine.GovernedExecutionRequest(
        canonical_id, canonical_id, ExecutionProtocol.FIXED_BUDGET, 100, BackendPolicy.PYTHON_ONLY
    )
    problem_dict = cli_engine._make_problem_dict(_cvrp())
    with pytest.raises(Exception) as excinfo:
        cli_engine._evaluate_param_combo(
            (problem_dict, canonical_id, canonical_id, {}, 0, 1, request)
        )
    assert not isinstance(excinfo.value, AssertionError)
    assert evaluation_spies == []


@pytest.mark.parametrize("canonical_id", ["Core-GA-TSP", "Core-TwoOpt-TSP", "Core-GWO-TSP-Pure"])
def test_smart_never_evaluates_a_core_id_on_a_routing_problem(canonical_id, evaluation_spies) -> None:
    request = smart_benchmark.GovernedExecutionRequest(
        canonical_id, canonical_id, ExecutionProtocol.FIXED_BUDGET, 100, BackendPolicy.PYTHON_ONLY
    )
    task = smart_benchmark.BenchmarkTask("tiny-cvrp", canonical_id, 1, 42, {}, governed_request=request)
    try:
        result = smart_benchmark._run_single_task((task, _cvrp()))
    except Exception as exc:  # governed refusal may raise instead of returning an error row
        assert not isinstance(exc, AssertionError)
    else:
        assert getattr(result, "error", None)
    assert evaluation_spies == []


def test_smart_registry_path_returns_an_error_row_for_core_id_on_routing(evaluation_spies) -> None:
    """The ungoverned branch of _run_single_task hands the task to the registry executor."""
    task = smart_benchmark.BenchmarkTask("tiny-cvrp", "Core-GA-TSP", 1, 42, {})
    try:
        result = smart_benchmark._run_single_task((task, _cvrp()))
    except Exception as exc:
        assert not isinstance(exc, AssertionError)
    else:
        assert result.error
    assert evaluation_spies == []


# --- cli_engine fails closed ---------------------------------------------------------------


def test_cli_engine_reraises_a_failed_registry_import_with_a_clear_message(monkeypatch) -> None:
    path = Path(cli_engine.__file__)
    spec = importlib.util.spec_from_file_location("cli_engine_import_failure_probe", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "academic_benchmark.core.registry_setup", None)
    with pytest.raises(ImportError, match="registry") as excinfo:
        spec.loader.exec_module(module)
    assert "partial" in str(excinfo.value).lower() or "fail" in str(excinfo.value).lower()
    assert "already registered" not in str(excinfo.value)
