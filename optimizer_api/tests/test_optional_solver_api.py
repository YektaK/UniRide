"""Regression tests for API behavior when optional solver imports are absent."""

import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("UNIRIDE_DISABLE_AUTH", "1")

import main
import strategies
from models.schemas import (
    AlgorithmResult,
    CompareRequest,
    LocationNode,
    OptimizationRequest,
)
from routers import optimization, strategies as strategies_router


class _Strategy:
    def __init__(self, name: str):
        self.name = name


def _optimization_request(algorithm: str = "unknown") -> OptimizationRequest:
    return OptimizationRequest(
        algorithm=algorithm,
        students=[],
        depot=LocationNode(id="depot", lat=0.0, lng=0.0),
    )


def test_available_strategy_names_excludes_none_deduplicates_aliases_and_sorts(monkeypatch):
    monkeypatch.setattr(
        strategies,
        "STRATEGY_REGISTRY",
        {
            "zeta_alias": _Strategy("zeta"),
            "alpha_alias": _Strategy("alpha"),
            "pyvrp": None,
            "alpha": _Strategy("alpha"),
            "zeta": _Strategy("zeta"),
        },
    )

    assert strategies.get_available_strategy_names() == ["alpha", "zeta"]


def test_health_reports_only_sorted_available_strategy_names(monkeypatch):
    monkeypatch.setattr(main, "get_available_strategy_names", lambda: ["alpha", "zeta"], raising=False)

    assert main.health_check()["algorithms"] == ["alpha", "zeta"]


def test_unknown_algorithm_reports_only_sorted_available_names(monkeypatch):
    monkeypatch.setattr(optimization, "get_available_strategy_names", lambda: ["alpha", "zeta"], raising=False)
    monkeypatch.setitem(optimization.STRATEGY_REGISTRY, "pyvrp", None)

    with pytest.raises(HTTPException) as exc_info:
        optimization.optimize_route(_optimization_request())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unknown algorithm 'unknown'. Available: ['alpha', 'zeta']"


def test_compare_defaults_to_available_canonical_names(monkeypatch):
    monkeypatch.setattr(optimization, "get_available_strategy_names", lambda: ["alpha", "zeta"], raising=False)
    calls = []

    def fake_run(algorithm_name, request):
        calls.append(algorithm_name)
        return AlgorithmResult(
            algorithm=algorithm_name,
            success=True,
            total_vehicles=1,
            total_duration_minutes=1.0 if algorithm_name == "alpha" else 2.0,
            execution_time_seconds=0.1 if algorithm_name == "alpha" else 0.2,
            routes=[],
        )

    monkeypatch.setattr(optimization, "_run_single_algorithm", fake_run)

    response = optimization.compare_algorithms(
        CompareRequest(
            students=[],
            depot=LocationNode(id="depot", lat=0.0, lng=0.0),
        )
    )

    assert calls == ["alpha", "zeta"]
    assert [result.algorithm for result in response.results] == ["alpha", "zeta"]
    assert list(response.summary) == ["alpha", "zeta"]


def test_strategies_endpoint_keeps_unavailable_entries_in_declared_order(monkeypatch):
    monkeypatch.setattr(
        strategies_router,
        "get_strategy_info",
        lambda: [
            {"name": "alpha", "display_name": "Alpha", "description": "available", "available": True},
            {"name": "pyvrp", "display_name": "PyVRP", "description": "unavailable", "available": False},
        ],
    )

    response = strategies_router.list_strategies()

    assert [strategy.available for strategy in response] == [True, False]
