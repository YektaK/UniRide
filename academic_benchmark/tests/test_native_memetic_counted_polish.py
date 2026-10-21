"""C-10 step 1: native memetic-2opt runs count their polish as objective evaluations."""

from __future__ import annotations

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401
from academic_benchmark.engine_core import AlgorithmRegistry, ProblemInstance
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms import numba_accel as _nb
from uniride_core.algorithms import objective_budget as _ob
from uniride_core.algorithms.tsp_matrix_metaheuristics.base_solver import BaseTSPSolver

MEMETIC_IDS = ("Core-GWO-TSP-Memetic-2opt", "Core-HHO-TSP-Memetic-2opt")
NATIVE = {
    "base_seed": 239,
    "protocol_version": "uniride-native-tsp-v1",
    "comparison_regime": "algorithm_native_termination",
}


def _problem(kind: str) -> ProblemInstance:
    n = 7
    if kind == "tsp":
        matrix = [
            [0.0 if i == j else float(((i + 1) * (j + 1)) % 11 + abs(i - j) + 1) for j in range(n)]
            for i in range(n)
        ]
    else:
        matrix = [
            [0.0 if i == j else float((i * 5 + j * 3 + (i * j) % 7) % 13 + 1) for j in range(n)]
            for i in range(n)
        ]
    return ProblemInstance(
        name=f"c10-{kind}-{n}", dimension=n, coordinates=[], problem_type=kind,
        dist_matrix=matrix, optimal=1.0,
    )


def _params(algorithm_id: str, **overrides) -> dict:
    params = {
        "max_iterations": 3,
        "max_no_improvement": 99,
        "polish_iters": 2,
        "final_polish_iters": 3,
        "native_comparison": dict(NATIVE),
    }
    if "GWO" in algorithm_id:
        params["pack_size"] = 5
    else:
        params.update(hawks=5, dive_count=0, jump_probability=0.0)
    params.update(overrides)
    return params


@pytest.mark.parametrize("periodic", [False, True])
@pytest.mark.parametrize("kind", ["tsp", "atsp"])
@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_native_memetic_objective_evaluations_equal_independent_count(
    algorithm_id, kind, periodic, monkeypatch
):
    """Independent count: every complete-tour pricing the run performed.

    Search evaluations go through ``_tour_length_fast``; polish pricing (the starting
    tour and every 2-opt candidate) goes through ``closed_tour_cost``. Both are
    spied at their definition, so the count does not come from the solver's counter.
    """
    seen = {"search": 0, "polish": 0}
    original_fast = BaseTSPSolver._tour_length_fast
    original_cost = _ob.closed_tour_cost

    def fast_spy(self, tour):
        seen["search"] += 1
        return original_fast(self, tour)

    def cost_spy(route, matrix):
        seen["polish"] += 1
        return original_cost(route, matrix)

    monkeypatch.setattr(BaseTSPSolver, "_tour_length_fast", fast_spy)
    monkeypatch.setattr(_ob, "closed_tour_cost", cost_spy)

    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem(kind),
        _params(algorithm_id, **({"polish_interval": 1} if periodic else {})),
        seed=1, run_idx=0,
    )
    assert seen["polish"] > 0, "native polish priced no tour through the counted path"
    assert result.objective_evaluations == result.evaluations == seen["search"] + seen["polish"]
    assert result.evaluation_budget is None
    # polish_policy is truthful in native mode too (C-04 contract).
    policy = result.polish_policy
    assert policy["enabled"] is True and policy["operator"] == "2-opt"
    evaluations = policy["evaluations"]
    assert evaluations["initial"] > 0 and evaluations["final"] > 0
    assert policy["initial"] is True and policy["final"] is True
    assert policy["executed"]["initial"] >= 1 and policy["executed"]["final"] == 1
    # The default interval (25) never fires in 3 iterations; interval 1 must.
    assert (evaluations["periodic"] > 0) is periodic
    assert policy["periodic"] is periodic
    # Candidate evaluations only: the starting-tour pricing of each initial polish is
    # counted in objective_evaluations but is not polish work.
    assert sum(evaluations.values()) + policy["executed"]["initial"] == seen["polish"]
    assert result.execution_backend == "objective=numba;polish=python"
    assert result.variant == "memetic_2opt"


@pytest.mark.parametrize("kind", ["tsp", "atsp"])
@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_native_memetic_never_calls_the_numba_two_opt_kernel(algorithm_id, kind, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("native protocol run took the uncounted Numba 2-opt kernel")

    monkeypatch.setattr(_nb, "_two_opt_improve_atsp_numba", forbidden)
    monkeypatch.setattr(_nb, "nb_two_opt", forbidden)
    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem(kind), _params(algorithm_id), seed=1, run_idx=0
    )
    assert result.polish_policy["enabled"] is True


def test_native_manifest_accepts_memetic_only_with_truthful_counts():
    manifest = NativeComparisonManifest.from_value(dict(NATIVE))
    for algorithm_id in MEMETIC_IDS:
        result = AlgorithmRegistry.get_executor(algorithm_id)(
            _problem("tsp"), _params(algorithm_id), seed=1, run_idx=0
        )
        manifest.validate_result(result)  # the executor already validated; must not raise


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_native_manifest_rejects_untruthful_memetic_records(algorithm_id):
    from copy import deepcopy
    from dataclasses import replace

    from academic_benchmark.fairness import FairnessValidationError

    manifest = NativeComparisonManifest.from_value(dict(NATIVE))
    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem("tsp"), _params(algorithm_id), seed=1, run_idx=0
    )
    zero = deepcopy(result.polish_policy)
    zero["evaluations"] = {"initial": 0, "periodic": 0, "final": 0}
    with pytest.raises(FairnessValidationError, match="flag must equal"):
        manifest.validate_result(replace(result, polish_policy=zero))
    flags_off = {"enabled": False, "initial": False, "periodic": False, "final": False,
                 "operator": None}
    with pytest.raises(FairnessValidationError, match="at least one polish phase"):
        manifest.validate_result(replace(result, polish_policy=flags_off))
    with pytest.raises(FairnessValidationError, match="memetic_2opt variant"):
        manifest.validate_result(replace(result, variant="pure"))


def test_ungoverned_memetic_run_keeps_the_numba_polish_kernel(monkeypatch):
    """Only protocol runs are counted; an ungoverned run still takes the fast kernel."""
    calls = []
    original = _nb._two_opt_improve_atsp_numba

    def spy(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(_nb, "_two_opt_improve_atsp_numba", spy)
    params = _params("Core-GWO-TSP-Memetic-2opt")
    params.pop("native_comparison")
    AlgorithmRegistry.get_executor("Core-GWO-TSP-Memetic-2opt")(
        _problem("tsp"), params, seed=1, run_idx=0
    )
    assert calls


def _pilot_config_with(memetic_blocks):
    from academic_benchmark.tests.native_config_helpers import native_pilot_config as _config

    data = _config()
    data["algorithms"].update(memetic_blocks)
    return data


def test_pilot_config_accepts_memetic_members_as_optional_and_rejects_zero_polish(tmp_path):
    import json

    from academic_benchmark.native_pilot import NativePilotError, load_native_pilot_config

    def load(blocks):
        path = tmp_path / "config.json"
        path.write_text(json.dumps(_pilot_config_with(blocks)), encoding="utf-8")
        return load_native_pilot_config(path)

    good = {
        "Core-GWO-TSP-Memetic-2opt": {
            "pack_size": 5, "max_iterations": 3, "max_no_improvement": 9,
            "polish_iters": 2, "final_polish_iters": 3,
        },
        "Core-HHO-TSP-Memetic-2opt": {
            "hawks": 5, "max_iterations": 3, "max_no_improvement": 9,
            "polish_iters": 2, "final_polish_iters": 3,
        },
    }
    config = load(good)
    assert set(MEMETIC_IDS) <= set(config.algorithms)
    zero = {k: {**v, "polish_iters": 0, "final_polish_iters": 0} for k, v in good.items()}
    with pytest.raises(NativePilotError, match="positive polish_iters"):
        load(zero)
    missing = {k: {kk: vv for kk, vv in v.items() if kk != "final_polish_iters"}
               for k, v in good.items()}
    with pytest.raises(NativePilotError, match="schema mismatch"):
        load(missing)


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_native_manifest_rejects_cross_variant_records_in_both_directions(algorithm_id):
    """A memetic-2opt ID never carries the composite variant; a 3-opt hybrid ID never the memetic_2opt one."""
    from dataclasses import replace

    from academic_benchmark.composite_protocol import COMPOSITE_VARIANT
    from academic_benchmark.fairness import FairnessValidationError

    manifest = NativeComparisonManifest.from_value(dict(NATIVE))
    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem("tsp"), _params(algorithm_id), seed=1, run_idx=0
    )
    with pytest.raises(FairnessValidationError, match="only the memetic_2opt variant for memetic IDs"):
        manifest.validate_result(replace(result, variant=COMPOSITE_VARIANT))
    hybrid_id = algorithm_id.replace("Memetic-2opt", "Memetic-3opt")
    with pytest.raises(FairnessValidationError, match="accepts only pure variants"):
        manifest.validate_result(
            replace(result, algorithm=hybrid_id, algorithm_id=hybrid_id, variant="memetic_2opt")
        )


@pytest.mark.parametrize("algorithm_id", MEMETIC_IDS)
def test_native_manifest_checks_initialization_policy_against_initial_polish(algorithm_id):
    from dataclasses import replace

    from academic_benchmark.fairness import FairnessValidationError

    manifest = NativeComparisonManifest.from_value(dict(NATIVE))
    result = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem("tsp"), _params(algorithm_id), seed=1, run_idx=0
    )
    assert result.polish_policy["initial"] is True
    assert result.initialization_policy.endswith("_with_initial_2opt")
    with pytest.raises(FairnessValidationError, match="initialization_policy"):
        manifest.validate_result(
            replace(result, initialization_policy="paired_seed_random_population_all_nodes")
        )
    # No initial polish: the plain initialization label is the only truthful one.
    no_initial = _params(algorithm_id)
    no_initial.update(polish_iters=0, final_polish_iters=3)
    plain = AlgorithmRegistry.get_executor(algorithm_id)(
        _problem("tsp"), no_initial, seed=1, run_idx=0
    )
    assert plain.polish_policy["initial"] is False
    assert plain.initialization_policy == "paired_seed_random_population_all_nodes"
    with pytest.raises(FairnessValidationError, match="initialization_policy"):
        manifest.validate_result(
            replace(plain, initialization_policy="paired_seed_random_population_all_nodes_with_initial_2opt")
        )
