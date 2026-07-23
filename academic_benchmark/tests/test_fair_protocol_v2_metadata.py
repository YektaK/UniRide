from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from academic_benchmark.core import registry_setup  # noqa: F401 - register fair executors
from academic_benchmark.engine_core import AlgorithmRegistry
from academic_benchmark.fair_pilot import FairPilotError, _result_record, load_fair_pilot_config
from academic_benchmark.fairness import FairComparisonManifest, FairnessValidationError
from uniride_core.models import ProblemInstance


V2 = "uniride-fair-tsp-v2"
REGIME = "fixed_evaluation_budget"
ALGORITHMS = (
    "Core-GWO-TSP-Pure",
    "Core-HHO-TSP-Pure",
    "Numba-2-opt",
    "Numba-3-opt-bounded",
)


def _matrix(directed: bool = False) -> list[list[float]]:
    return [
        [0.0 if i == j else float((i + 1) * 7 + (j + 1) * 3 + (i * j if directed else abs(i - j)))
         for j in range(6)]
        for i in range(6)
    ]


def _problem(directed: bool = False) -> ProblemInstance:
    return ProblemInstance(
        name="protocol-v2-atsp" if directed else "protocol-v2-tsp",
        dimension=6,
        coordinates=[],
        problem_type="atsp" if directed else "tsp",
        dist_matrix=_matrix(directed),
        optimal=1.0,
    )


def _algorithm_blocks(first_improvement: bool = False) -> dict[str, dict]:
    return {
        "Core-GWO-TSP-Pure": {"pack_size": 4, "max_iterations": 2, "max_no_improvement": 10},
        "Core-HHO-TSP-Pure": {"hawks": 4, "max_iterations": 2, "dive_count": 0, "max_no_improvement": 10},
        "Numba-2-opt": {"max_iterations": 20, "first_improvement": first_improvement},
        "Numba-3-opt-bounded": {"max_iterations": 20, "first_improvement": first_improvement, "window": 4},
    }


def _v2_config(**overrides: object) -> dict:
    value = {
        "protocol_version": V2,
        "comparison_regime": REGIME,
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": _algorithm_blocks(),
        "runs": 1,
        "evaluation_budget": 100,
        "base_seed": 17,
        "budget_policy": "atomic_upper_bound_v1",
        "workers": 1,
        "replay_replicates": [],
        "allow_repository_output": False,
        "overwrite": False,
    }
    value.update(overrides)
    return value


def _write_config(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "fair-v2.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(algorithm: str, *, directed: bool = False, budget: int = 100, max_iterations: int | None = None, first_improvement: bool = False):
    params = _algorithm_blocks(first_improvement)[algorithm]
    if max_iterations is not None:
        params["max_iterations"] = max_iterations
    params["fair_comparison"] = {
        "protocol_version": V2,
        "comparison_regime": REGIME,
        "evaluation_budget": budget,
        "base_seed": 17,
        "budget_policy": "atomic_upper_bound_v1",
    }
    return AlgorithmRegistry.get_executor(algorithm)(_problem(directed), params, seed=999, run_idx=0)


def _closed_cost(tour: list[int], matrix: list[list[float]]) -> float:
    zero_indexed = [node - 1 for node in tour]
    return sum(
        matrix[node][zero_indexed[(index + 1) % len(zero_indexed)]]
        for index, node in enumerate(zero_indexed)
    )


def test_v1_config_remains_loadable(tmp_path: Path):
    config = _v2_config(protocol_version="uniride-fair-tsp-v1")
    config.pop("comparison_regime")
    config["algorithms"] = {name: {} for name in ALGORITHMS}

    loaded = load_fair_pilot_config(_write_config(tmp_path, config))

    assert loaded.protocol_version == "uniride-fair-tsp-v1"
    assert loaded.comparison_regime is None
    assert "comparison_regime" not in loaded.fair_comparison


def test_v2_fixed_evaluation_config_loads_and_propagates_manifest(tmp_path: Path):
    loaded = load_fair_pilot_config(_write_config(tmp_path, _v2_config()))

    assert loaded.comparison_regime == REGIME
    assert loaded.manifest.comparison_regime == REGIME
    assert loaded.fair_comparison["comparison_regime"] == REGIME


@pytest.mark.parametrize(
    ("regime", "match"),
    [
        (None, "missing=.*comparison_regime"),
        ("unknown", "comparison_regime must be"),
        ("algorithm_native_termination", "not implemented"),
    ],
)
def test_v2_rejects_missing_unknown_or_unimplemented_regimes(tmp_path: Path, regime: str | None, match: str):
    config = _v2_config()
    if regime is None:
        config.pop("comparison_regime")
    else:
        config["comparison_regime"] = regime

    with pytest.raises(FairPilotError, match=match):
        load_fair_pilot_config(_write_config(tmp_path, config))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda blocks: blocks["Numba-2-opt"].pop("first_improvement"),
        lambda blocks: blocks["Numba-2-opt"].__setitem__("first_improvement", 1),
        lambda blocks: blocks["Numba-3-opt-bounded"].pop("first_improvement"),
        lambda blocks: blocks["Numba-3-opt-bounded"].__setitem__("window", 1),
        lambda blocks: blocks["Numba-3-opt-bounded"].__setitem__("window", True),
        lambda blocks: blocks["Core-GWO-TSP-Pure"].__setitem__("first_improvement", False),
    ],
)
def test_v2_rejects_ambiguous_or_invalid_local_search_policy(tmp_path: Path, mutate):
    config = _v2_config()
    mutate(config["algorithms"])

    with pytest.raises(FairPilotError):
        load_fair_pilot_config(_write_config(tmp_path, config))


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_v2_results_report_truthful_structured_metadata(algorithm: str):
    result = _run(algorithm)

    assert result.comparison_regime == REGIME
    assert result.termination_reason in FairComparisonManifest.TERMINATION_REASONS
    if algorithm in {"Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"}:
        assert result.acceptance_policy == "population_evolution"
        assert result.neighborhood_window is None
    elif algorithm == "Numba-2-opt":
        assert result.acceptance_policy == "best_improvement"
        assert result.neighborhood_window is None
    else:
        assert result.acceptance_policy == "best_improvement"
        assert result.neighborhood_window == 4


def test_first_improvement_metadata_is_explicit_and_directed_cost_is_preserved():
    problem = _problem(directed=True)
    result = _run("Numba-3-opt-bounded", directed=True, first_improvement=True)

    assert result.acceptance_policy == "first_improvement"
    assert result.neighborhood_window == 4
    assert result.tour_cost == pytest.approx(_closed_cost(result.tour, problem.dist_matrix))


def test_local_search_termination_reasons_distinguish_budget_iteration_and_local_optimum():
    exhausted = _run("Numba-2-opt", budget=1, max_iterations=20)
    capped = _run("Numba-2-opt", budget=100, max_iterations=0)
    local_optimum = _run("Numba-2-opt", budget=100, max_iterations=20)

    assert exhausted.termination_reason == "evaluation_budget_exhausted"
    assert capped.termination_reason == "max_iterations"
    assert local_optimum.termination_reason == "no_improving_move"


def test_v2_metadata_serializes_and_survives_fair_pilot_record(tmp_path: Path):
    config = load_fair_pilot_config(_write_config(tmp_path, _v2_config()))
    problem = _problem(directed=True)
    result = _run("Numba-3-opt-bounded", directed=True)

    serialized = asdict(result)
    assert {"comparison_regime", "acceptance_policy", "neighborhood_window", "termination_reason"} <= set(serialized)
    record = _result_record(
        result,
        problem=problem,
        matrix=problem.dist_matrix,
        matrix_sha256="test-matrix",
        algorithm_id="Numba-3-opt-bounded",
        replicate=0,
        seed=result.seed,
        config=config,
        elapsed_ms=1.0,
        record_kind="primary",
    )
    assert record["comparison_regime"] == REGIME
    assert record["acceptance_policy"] == "best_improvement"
    assert record["neighborhood_window"] == 4


def test_v2_manifest_rejects_incompatible_metadata():
    result = _run("Numba-2-opt")
    manifest = FairComparisonManifest.from_value({
        "protocol_version": V2,
        "comparison_regime": REGIME,
        "evaluation_budget": 100,
        "base_seed": 17,
        "budget_policy": "atomic_upper_bound_v1",
    })
    assert manifest is not None
    result.neighborhood_window = 4

    with pytest.raises(FairnessValidationError, match="2-opt neighborhood_window must be null"):
        manifest.validate_result(result)