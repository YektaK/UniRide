"""H17 + M22: production ignores academic promoted configs unless explicitly enabled.

Owner decision 2026-10-13: UNIRIDE_PROMOTED_CONFIG_PATH alone must not change plans.
Only UNIRIDE_USE_PROMOTED_CONFIG=1 enables the lookup. The /optimize response
reports where the effective config came from and which seed was used.
"""

import json

import pytest

from models.schemas import LocationNode, OptimizationRequest, StudentNode
from strategies.ga_split_strategy import GAEnhancedSplitStrategy, GASplitStrategy
from strategies.promoted_config_loader import (
    PROMOTED_CONFIG_PATH_ENV,
    clear_promoted_config_cache,
    get_promoted_params,
)

USE_PROMOTED_ENV = "UNIRIDE_USE_PROMOTED_CONFIG"
PROMOTED = {"population_size": 7, "max_iterations": 3, "seed": 99}


@pytest.fixture
def promoted_file(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "test",
                "configs": [
                    {
                        "algorithm": "ga_split",
                        "problem_type": "cvrptw",
                        "matrix_kind": "travel_time",
                        "params": {"pop_size": 7, "generations": 3, "seed": 99},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    monkeypatch.delenv(USE_PROMOTED_ENV, raising=False)
    clear_promoted_config_cache()
    yield path
    clear_promoted_config_cache()


class _FakeLoader:
    def get_submatrix(self, locations, coordinates=None, **_kwargs):
        n = len(locations)
        return [[0.0 if i == j else 1.0 for j in range(n)] for i in range(n)]


def _request(**extra):
    students = [
        StudentNode(
            id=f"S{i}", name=f"S{i}", location_code=f"L{i}",
            coordinates={"lat": 0.0, "lng": float(i)}, disability_type="So",
        )
        for i in (1, 2)
    ]
    return OptimizationRequest(
        algorithm="ga_split",
        students=students,
        depot=LocationNode(id="D", lat=0.0, lng=0.0, type="Depot"),
        max_travel_time=240,
        sw_capacity=10,
        so_capacity=10,
        **extra,
    )


@pytest.fixture
def fake_loader(monkeypatch):
    from strategies import ga_split_strategy

    fake = _FakeLoader()
    monkeypatch.setattr(
        ga_split_strategy.DataLoader, "get_instance", staticmethod(lambda: fake)
    )


def test_flag_unset_loader_returns_no_params(promoted_file):
    assert get_promoted_params("ga_split", problem_type="cvrptw", matrix_kind="travel_time") == {}


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1", "1 "])
def test_only_exact_one_enables(promoted_file, monkeypatch, value):
    monkeypatch.setenv(USE_PROMOTED_ENV, value)
    assert GASplitStrategy().config == GASplitStrategy.DEFAULT_CONFIG


@pytest.mark.parametrize("cls", [GASplitStrategy, GAEnhancedSplitStrategy])
def test_flag_unset_uses_default_config(promoted_file, cls):
    assert cls().config == GASplitStrategy.DEFAULT_CONFIG


def test_flag_one_uses_promoted_values(promoted_file, monkeypatch):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    config = GASplitStrategy().config
    assert config["population_size"] == 7
    assert config["max_iterations"] == 3
    assert config["seed"] == 99


def test_response_reports_default_source_and_seed(promoted_file, fake_loader):
    response = GASplitStrategy().optimize(_request())
    assert response.effective_config_source == "default"
    assert response.effective_seed == 42


def test_response_reports_promoted_source_and_seed(promoted_file, fake_loader, monkeypatch):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    response = GASplitStrategy().optimize(_request())
    assert response.effective_config_source == "promoted"
    assert response.effective_seed == 99


def test_response_reports_request_source_and_seed(promoted_file, fake_loader):
    response = GASplitStrategy().optimize(
        _request(ga_config={"population_size": 6, "max_iterations": 2, "seed": 7})
    )
    assert response.effective_config_source == "request"
    assert response.effective_seed == 7


def test_request_config_without_seed_reports_resolved_seed(promoted_file, fake_loader):
    response = GASplitStrategy().optimize(_request(ga_config={"max_iterations": 2}))
    assert response.effective_config_source == "request"
    assert response.effective_seed == 42


def test_fields_serialized_in_json(promoted_file, fake_loader):
    dumped = GASplitStrategy().optimize(_request()).model_dump()
    assert dumped["effective_config_source"] == "default"
    assert dumped["effective_seed"] == 42
