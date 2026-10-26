"""DECISION_LOG A20 L2 + L3: production solver provenance after MT6-03.

* L3: the production SOTA strategies (``ebso``/``rdma``/``aoea``, canonical keys
  ``e2bso``/``r2dma``/``paoea``) get a 60 s default ``deadline_seconds``; the
  academic/core defaults stay ``None``. A run that hit the deadline reports
  ``termination_reason: "wall_clock_deadline"`` in the HTTP response; every other
  response omits the field (same pattern as ``fallback_reason``).
* L2: the response carries ``solver_code_version`` taken from the environment
  variable ``UNIRIDE_BUILD_COMMIT`` when it is a short token; otherwise omitted.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from compute_policy import HARD_CEILINGS, apply_compute_policy
from models import schemas
from routers import optimization
from certifier_matrix_support import stub_arc_capture  # noqa: F401 - fixture
from strategies import aoea_strategy, ebso_strategy, rdma_strategy
from strategies.canonical import resolve_strategy
from strategies.sota_config_utils import merge_sota_config
from uniride_core.algorithms.sota_tsp import E2BSOTSPConfig, PAOEAConfig, R2DMATSPConfig

import test_sota_adapter_truth as truth

pytestmark = pytest.mark.usefixtures("stub_arc_capture")

STRATEGIES = [
    (ebso_strategy, ebso_strategy.E2BSoStrategy, "E2BSO_TSP", "e2bso"),
    (rdma_strategy, rdma_strategy.R2DMAStrategy, "R2DMA_TSP", "r2dma"),
    (aoea_strategy, aoea_strategy.PAOEAStrategy, "PAOEA_TSP", "paoea"),
]
CLASSES = [(cls, name) for _module, cls, _attr, name in STRATEGIES]


# ---- L3: default deadline --------------------------------------------------

@pytest.mark.parametrize("cls,name", CLASSES)
def test_production_strategy_defaults_to_a_60_second_deadline(cls, name):
    assert cls()._config.deadline_seconds == 60


@pytest.mark.parametrize("cls,name", CLASSES)
def test_request_deadline_and_legacy_time_limit_still_win(cls, name):
    base = cls()._config
    assert merge_sota_config(base, {"deadline_seconds": 5}).deadline_seconds == 5
    assert merge_sota_config(base, {"time_limit": 9}).deadline_seconds == 9
    assert merge_sota_config(base, {"population_size": 8}).deadline_seconds == 60


@pytest.mark.parametrize("cls,name", CLASSES)
def test_default_deadline_reaches_the_effective_request_config(cls, name):
    request = schemas.OptimizationRequest(
        algorithm=name, students=truth._students(), depot=truth.DEPOT
    )
    resolution = resolve_strategy(name)
    effective, metadata = apply_compute_policy(request, resolution, resolution.create(), HARD_CEILINGS)
    assert effective.sota_config["deadline_seconds"] == 60
    # the policy module may load models.schemas under its package name: compare by value
    assert metadata.limits["deadline_seconds"].source.value == "strategy_default"


@pytest.mark.parametrize("cls,name", CLASSES)
def test_legacy_time_limit_in_the_request_beats_the_injected_default(cls, name):
    # The compute policy writes the registered 60 s default into the effective
    # sota_config as deadline_seconds; that must not outrank a caller time_limit.
    request = schemas.OptimizationRequest(
        algorithm=name, students=truth._students(), depot=truth.DEPOT,
        sota_config={"time_limit": 9},
    )
    resolution = resolve_strategy(name)
    strategy = resolution.create()
    effective, metadata = apply_compute_policy(request, resolution, strategy, HARD_CEILINGS)
    assert merge_sota_config(strategy._config, effective.sota_config).deadline_seconds == 9
    assert "deadline_seconds" not in metadata.limits


def test_core_and_academic_defaults_stay_unbounded():
    for config_cls in (E2BSOTSPConfig, R2DMATSPConfig, PAOEAConfig):
        assert config_cls().deadline_seconds is None


# ---- L3: termination_reason in the response --------------------------------

class _DeadlineSolver:
    def __init__(self, config):
        pass

    def solve_with_matrix(self, matrix):
        n = len(matrix)
        return SimpleNamespace(
            tour=list(range(n)),
            extra_stats={"termination_reason": "wall_clock_deadline", "reproducible": False},
        )


class _IterationLimitSolver(_DeadlineSolver):
    def solve_with_matrix(self, matrix):
        result = super().solve_with_matrix(matrix)
        result.extra_stats = {"termination_reason": "iteration_limit", "reproducible": True}
        return result


@pytest.mark.parametrize("module,cls,solver_attr,name", STRATEGIES)
def test_deadline_hit_is_reported_as_termination_reason(monkeypatch, module, cls, solver_attr, name):
    monkeypatch.setattr(module, "build_sota_request_context", truth._context)
    monkeypatch.setattr(module, solver_attr, _DeadlineSolver)

    response = cls().optimize(truth._request(name))

    assert response.success is True
    assert response.termination_reason == "wall_clock_deadline"
    assert json.loads(response.model_dump_json())["termination_reason"] == "wall_clock_deadline"


@pytest.mark.parametrize("module,cls,solver_attr,name", STRATEGIES)
def test_normal_stop_omits_termination_reason(monkeypatch, module, cls, solver_attr, name):
    monkeypatch.setattr(module, "build_sota_request_context", truth._context)
    monkeypatch.setattr(module, solver_attr, _IterationLimitSolver)

    response = cls().optimize(truth._request(name))

    assert response.termination_reason is None
    assert "termination_reason" not in json.loads(response.model_dump_json())


def test_termination_reason_survives_the_optimize_endpoint(monkeypatch):
    labelled = schemas.OptimizationResponse(
        algorithm_used="e2bso", success=True, routes=[], termination_reason="wall_clock_deadline"
    )
    truth._install_router(monkeypatch, truth._Fixed(labelled), "e2bso", "e2bso")

    result = optimization.optimize_route(
        schemas.OptimizationRequest(algorithm="e2bso", students=[], depot=truth.DEPOT)
    )

    assert result.termination_reason == "wall_clock_deadline"


# ---- L2: solver_code_version ------------------------------------------------

def _optimize(monkeypatch):
    normal = schemas.OptimizationResponse(algorithm_used="e2bso", success=True, routes=[])
    truth._install_router(monkeypatch, truth._Fixed(normal), "e2bso", "e2bso")
    return optimization.optimize_route(
        schemas.OptimizationRequest(algorithm="e2bso", students=[], depot=truth.DEPOT)
    )


@pytest.mark.parametrize("value", ["abc1234", "v1.2.3+build-7", "a" * 64])
def test_build_commit_env_is_reported(monkeypatch, value):
    monkeypatch.setenv("UNIRIDE_BUILD_COMMIT", value)
    result = _optimize(monkeypatch)
    assert result.solver_code_version == value
    assert json.loads(result.model_dump_json())["solver_code_version"] == value


def test_unset_build_commit_omits_the_field(monkeypatch):
    monkeypatch.delenv("UNIRIDE_BUILD_COMMIT", raising=False)
    result = _optimize(monkeypatch)
    assert result.solver_code_version is None
    assert "solver_code_version" not in json.loads(result.model_dump_json())


@pytest.mark.parametrize("value", ["", "   ", "has space", "semi;colon", "a" * 65, "<script>", "line\nbreak"])
def test_invalid_build_commit_is_omitted(monkeypatch, value):
    monkeypatch.setenv("UNIRIDE_BUILD_COMMIT", value)
    result = _optimize(monkeypatch)
    assert result.solver_code_version is None
    assert "solver_code_version" not in json.loads(result.model_dump_json())
