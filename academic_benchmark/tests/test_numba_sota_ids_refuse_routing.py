"""Owner decision 4 (2026-10-23): Numba-Swap, Numba-Hybrid and the SOTA-*-TSP IDs refuse routing.

These seven IDs are not capability-catalog IDs, but they name TSP/ATSP algorithms. Before this
item they ran the greedy router on CVRP/CVRPTW problems under their own labels (Numba-Swap,
Numba-Hybrid) or under ``SOTA-*:core-greedy-routing``. Now they refuse routing problems on
every path, before any evaluation. TSP/ATSP behaviour is pinned by a golden captured before the
change; the CVRP-*/CVRPTW-* names are pinned by the goldens in test_core_ids_refuse_routing.py.
"""
from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest

import academic_benchmark.core.registry_setup as rs
from academic_benchmark import cli_engine, smart_benchmark
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance

REFUSING_IDS = [
    "Numba-Swap",
    "Numba-Hybrid",
    "SOTA-E2BSO-TSP",
    "SOTA-R2DMA-TSP",
    "SOTA-P-AOEA-TSP",
    "SOTA-CGO-TSP",
    "SOTA-RUN-TSP",
]
ROUTING_TYPES = ("cvrp", "cvrptw")
FIXTURE = Path(__file__).parent / "fixtures" / "numba_sota_tsp_golden_pre_refusal.json"


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


@pytest.mark.parametrize("problem_type", ROUTING_TYPES)
@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_registered_executor_refuses_routing_before_any_evaluation(
    algorithm_id, problem_type, evaluation_spies
) -> None:
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        AlgorithmRegistry.get_executor(algorithm_id)(
            _spy_problem(problem_type), {"max_iterations": 5}, 42, 1
        )
    message = str(excinfo.value)
    assert algorithm_id in message
    assert problem_type.upper() in message.upper()
    assert evaluation_spies == []


@pytest.mark.parametrize("problem_type", ROUTING_TYPES)
@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_refusal_works_on_real_routing_instances(algorithm_id, problem_type, evaluation_spies) -> None:
    problem = _cvrp() if problem_type == "cvrp" else _cvrptw()
    with pytest.raises(rs.CoreRoutingRefusedError):
        AlgorithmRegistry.get_executor(algorithm_id)(problem, {"max_iterations": 5}, 42, 1)
    assert evaluation_spies == []


@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_refusal_says_that_no_truthful_alternative_exists(algorithm_id) -> None:
    """No CVRP-*/CVRPTW-* name is truthful for these IDs: none exists for SOTA-*, and the
    CVRP-Numba-Swap/-Hybrid aliases run the legacy 2-opt matrix engine under another label."""
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        AlgorithmRegistry.get_executor(algorithm_id)(_spy_problem("cvrp"), {}, 42, 1)
    message = str(excinfo.value)
    assert "no truthful CVRP-/CVRPTW- alternative exists" in message
    assert "a routing variant is available" not in message


@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_executor_is_marked_as_refusing_routing(algorithm_id) -> None:
    assert getattr(AlgorithmRegistry.get_executor(algorithm_id), "refuses_routing", False)


@pytest.mark.parametrize("problem_type", ROUTING_TYPES)
@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_raw_executor_behind_the_wrapper_also_refuses_routing(
    algorithm_id, problem_type, evaluation_spies
) -> None:
    wrapped = AlgorithmRegistry.get_executor(algorithm_id)
    raw = inspect.unwrap(wrapped)
    assert raw is not wrapped
    with pytest.raises(rs.CoreRoutingRefusedError) as excinfo:
        raw(_spy_problem(problem_type), {"max_iterations": 5}, 42, 1)
    assert algorithm_id in str(excinfo.value)
    assert evaluation_spies == []


@pytest.mark.parametrize("algorithm_id", REFUSING_IDS)
def test_refusal_also_beats_scientific_protocol_params(algorithm_id, evaluation_spies) -> None:
    for params in ({"fair_comparison": {"x": 1}}, {"native_comparison": {"x": 1}}):
        with pytest.raises(rs.CoreRoutingRefusedError):
            AlgorithmRegistry.get_executor(algorithm_id)(_spy_problem("cvrp"), params, 42, 1)
    assert evaluation_spies == []


def test_unmarked_executors_that_run_routing_are_exactly_the_known_ones() -> None:
    """Pins the inventory: a non-CVRP-* ID that runs routing problems must be listed here."""
    runs_routing = {
        name for name in AlgorithmRegistry.list_algorithms()
        if not name.startswith(("CVRP-", "CVRPTW-"))
        and not getattr(AlgorithmRegistry.get_executor(name), "refuses_routing", False)
    }
    assert runs_routing == {
        "Core-Greedy-Routing",  # the routing ID
        # FCM-*-TSP now refuse routing too (test_fcm_ids_refuse_routing.py).
        "Matrix-TwoOpt-TSP-legacy", "Matrix-GA-TSP-legacy", "Matrix-PSO-TSP-legacy",
        "Matrix-GWO-TSP-legacy", "Matrix-HHO-TSP-legacy",  # truthful legacy engine names
    }


# --- TSP/ATSP behaviour is unchanged ---------------------------------------------------------

_GOLDEN = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _golden_problems():
    import hashlib
    import math
    import random

    rng = random.Random(7)
    pts = [(rng.randint(0, 100), rng.randint(0, 100)) for _ in range(9)]
    sym = [[int(round(math.hypot(a[0] - b[0], a[1] - b[1]))) for b in pts] for a in pts]
    asym = [[0 if i == j else sym[i][j] + rng.randint(0, 9) for j in range(9)] for i in range(9)]
    assert hashlib.sha256(json.dumps([sym, asym]).encode()).hexdigest() == _GOLDEN["matrix_sha256"]
    return {
        "tsp": ProblemInstance(name="golden-tsp9", dimension=9, coordinates=[], problem_type="tsp", dist_matrix=sym),
        "atsp": ProblemInstance(name="golden-atsp9", dimension=9, coordinates=[], problem_type="atsp", dist_matrix=asym),
    }


def test_golden_covers_all_ids_on_tsp_and_atsp() -> None:
    assert sorted(_GOLDEN["results"]) == sorted(
        f"{ptype}:{algo}" for ptype in ("tsp", "atsp") for algo in REFUSING_IDS
    )


@pytest.mark.parametrize("key", sorted(_GOLDEN["results"]))
def test_tsp_and_atsp_results_reproduce_the_pre_refusal_golden(key) -> None:
    ptype, algorithm_id = key.split(":", 1)
    problem = _golden_problems()[ptype]
    params = (
        dict(_GOLDEN["params"]["Numba-Swap/Hybrid"])
        if algorithm_id.startswith("Numba-")
        else dict(_GOLDEN["params"]["SOTA-*"])
    )
    result = AlgorithmRegistry.get_executor(algorithm_id)(problem, params, _GOLDEN["seed"], 1)
    expected = _GOLDEN["results"][key]
    assert result.algorithm == expected["algorithm"] == algorithm_id
    assert round(float(result.objective_cost), 9) == expected["cost"]
    assert [int(x) for x in result.tour] == expected["tour"]


# --- CLI and Smart -----------------------------------------------------------------------------


@pytest.mark.parametrize("algorithm_id", ["Numba-Swap", "SOTA-RUN-TSP"])
def test_cli_never_evaluates_these_ids_on_a_routing_problem(algorithm_id, evaluation_spies) -> None:
    problem_dict = cli_engine._make_problem_dict(_cvrp())
    with pytest.raises(Exception) as excinfo:
        cli_engine._evaluate_param_combo((problem_dict, algorithm_id, algorithm_id, {}, 0, 1, None))
    assert not isinstance(excinfo.value, AssertionError)
    assert "refuses CVRP routing" in str(excinfo.value)
    assert evaluation_spies == []


@pytest.mark.parametrize("algorithm_id", ["Numba-Hybrid", "SOTA-E2BSO-TSP"])
def test_smart_never_evaluates_these_ids_on_a_routing_problem(algorithm_id, evaluation_spies) -> None:
    """Smart already stops these uncataloged IDs at the worker boundary (any problem type);
    the registry executor behind it refuses routing as well (tests above)."""
    from academic_benchmark.core.algorithm_errors import ExecutorUnavailableError

    task = smart_benchmark.BenchmarkTask("tiny-cvrp", algorithm_id, 1, 42, {})
    with pytest.raises(ExecutorUnavailableError):
        smart_benchmark._run_single_task((task, _cvrp()))
    assert evaluation_spies == []
