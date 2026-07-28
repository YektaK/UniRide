from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from academic_benchmark.core.preflight import RuntimeBackendAvailability

from academic_benchmark.fairness import FairComparisonManifest, FairRunResult
from academic_benchmark.fair_pilot import APPROVED_ALGORITHMS, FairPilotError, run_fair_pilot
from uniride_core.algorithms.capabilities import BackendKind, ExecutionBackendProfile


RUNTIME = RuntimeBackendAvailability(True, True, "deterministic pilot fixture")


@dataclass
class _Problem:
    name: str
    problem_type: str
    dist_matrix: list[list[float]]
    optimal: float
    dimension: int = 4
    edge_weight_type: str = "EXPLICIT"
    is_time_matrix: bool = False


def _config(tmp_path: Path, **overrides: Any) -> Path:
    config: dict[str, Any] = {
        "protocol_version": "uniride-fair-tsp-v1",
        "problems": ["tiny-tsp", "tiny-atsp"],
        "algorithms": {algorithm: {} for algorithm in APPROVED_ALGORITHMS},
        "runs": 2,
        "evaluation_budget": 20,
        "base_seed": 123,
        "budget_policy": "atomic_upper_bound_v1",
        "workers": 1,
        "replay_replicates": [0],
        "allow_repository_output": False,
        "overwrite": False,
    }
    config.update(overrides)
    path = tmp_path / "fair.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _problems() -> list[_Problem]:
    return [
        _Problem("tiny-tsp", "tsp", [[0, 2, 7, 4], [2, 0, 5, 6], [7, 5, 0, 7], [4, 6, 7, 0]], 18),
        _Problem("tiny-atsp", "atsp", [[0, 2, 8, 9], [6, 0, 3, 8], [4, 7, 0, 5], [9, 1, 6, 0]], 19),
    ]


def _registry(algorithm_id: str):
    family = {
        "Core-GWO-TSP-Pure": "GWO", "Core-HHO-TSP-Pure": "HHO",
        "Core-TwoOpt-TSP": "2-opt", "Core-ThreeOpt-TSP": "3-opt",
    }[algorithm_id]

    def execute(problem, params, seed, run_idx):
        manifest = FairComparisonManifest.from_value(params["fair_comparison"])
        assert manifest is not None
        tour = [1, 2, 3, 4]
        cost = float(sum(problem.dist_matrix[i][(i + 1) % 4] for i in range(4)))
        return FairRunResult(
            problem=problem.name, algorithm=algorithm_id, algorithm_id=algorithm_id,
            algorithm_family=family, variant="pure", run=run_idx, seed=seed,
            seed_group=manifest.seed_group(problem.name, run_idx), dimension=4,
            optimal=problem.optimal, tour_cost=cost, objective_cost=cost,
            gap_pct=((cost - problem.optimal) / problem.optimal) * 100,
            elapsed_sec=0.001, iterations=2, evaluations=5, objective_evaluations=5,
            evaluation_budget=manifest.evaluation_budget, budget_terminated=False,
            tour=tour, initialization_policy="paired_seed_random_permutation_all_nodes",
            termination_policy="atomic_upper_bound_v1", execution_backend=(
                "numba-objective" if family in {"GWO", "HHO"} else "python-canonical-matrix"
            ), polish_policy={"enabled": False, "initial": False, "periodic": False,
                            "final": False, "operator": None},
        )

    return execute

def _gateway(**kwargs: Any):
    algorithm_id = kwargs["requested_algorithm_id"]
    executor = kwargs["registry_getter"](algorithm_id)
    result = executor(
        kwargs["problem"], kwargs["params"], kwargs["seed"], kwargs["run_idx"]
    )
    backend = BackendKind.NUMBA_NOPYTHON if algorithm_id in {
        "Core-GWO-TSP-Pure", "Core-HHO-TSP-Pure"
    } else BackendKind.PYTHON
    decision = SimpleNamespace(
        backend_policy=kwargs["backend_policy"],
        selected_backend=ExecutionBackendProfile(backend),
        fallback_reason=None,
        executor_registry_id=algorithm_id,
        evidence_ids=(f"fixture::{algorithm_id}",),
    )
    return result, decision




def test_fair_pilot_writes_only_validated_external_artifacts(tmp_path: Path):
    output = tmp_path / "external-output"
    result = run_fair_pilot(
        _config(tmp_path), output, problem_loader=_problems, registry_getter=_registry,
        repo_root=tmp_path / "repository", runtime_probe=lambda: RUNTIME, registered_algorithms_provider=lambda: APPROVED_ALGORITHMS, gateway_executor=_gateway,
    )
    assert result["records"] == 24  # 2 problems x 4 algorithms x (2 primary + replay run 0)
    assert {path.name for path in output.iterdir()} == {
        "manifest.json", "runs.jsonl", "aggregate.csv", "validation.json",
    }
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 24
    assert all(row["validation_status"] == "passed" for row in rows)
    assert {row["record_kind"] for row in rows} == {"primary", "replay"}
    assert json.loads((output / "validation.json").read_text(encoding="utf-8"))["status"] == "passed"


def test_fair_pilot_rejects_repository_output_without_creating_it(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(FairPilotError, match="repository-contained"):
        run_fair_pilot(_config(tmp_path), repository / "results", problem_loader=_problems,
                       registry_getter=_registry, repo_root=repository, runtime_probe=lambda: RUNTIME, registered_algorithms_provider=lambda: APPROVED_ALGORITHMS, gateway_executor=_gateway)
    assert not (repository / "results").exists()


def test_fair_pilot_fails_cleanly_before_execution_when_atsp_missing(tmp_path: Path):
    output = tmp_path / "external-output"
    with pytest.raises(FairPilotError, match="at least one TSP and one ATSP"):
        run_fair_pilot(_config(tmp_path, problems=["tiny-tsp"]), output, problem_loader=_problems,
                       registry_getter=_registry, repo_root=tmp_path / "repository", runtime_probe=lambda: RUNTIME, registered_algorithms_provider=lambda: APPROVED_ALGORITHMS, gateway_executor=_gateway)
    assert {path.name for path in output.iterdir()} == {"validation.json"}
    assert json.loads((output / "validation.json").read_text(encoding="utf-8"))["status"] == "failed"


def test_cli_fair_argument_pair_is_rejected_before_legacy_initialization(monkeypatch):
    from academic_benchmark import cli_engine
    monkeypatch.setattr(cli_engine, "_ensure_dirs", lambda: pytest.fail("legacy initialization ran"))
    assert cli_engine.main(["--fair-config", "fair.json"]) == 2
