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


# ---------------------------------------------------------------------------
# DUZELT round 1: promoted+request, empty-student returns, ga_split_hf, other
# strategies, benchmark-runner provenance
# ---------------------------------------------------------------------------

import hashlib
from types import SimpleNamespace

from benchmark_runner import AlgorithmConfig, BenchmarkRunner
from models.schemas import OptimizationResponse
from strategies.ga_split_hf_strategy import GASplitHFStrategy
from uniride_core.models import ProblemInstance

HF_TYPES = [
    {"type_id": "large", "sw_capacity": 4, "so_capacity": 5},
    {"type_id": "car", "sw_capacity": 0, "so_capacity": 4},
]


def _hf_request(students=None, **extra):
    payload = _request(**extra).model_dump()
    payload["algorithm"] = "ga_split_hf"
    payload["vehicle_types"] = HF_TYPES
    payload["minimize_type"] = "car"
    payload.pop("sw_capacity", None)
    payload.pop("so_capacity", None)
    if students is not None:
        payload["students"] = students
    return OptimizationRequest.model_validate(payload)


def _empty_request(**extra):
    payload = {**_request().model_dump(), "students": [], **extra}
    return OptimizationRequest.model_validate(payload)


def test_flag_on_partial_request_config_reports_promoted_plus_request(
    promoted_file, fake_loader, monkeypatch
):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    response = GASplitStrategy().optimize(_request(ga_config={"max_iterations": 2}))
    assert response.effective_config_source == "promoted+request"
    assert response.effective_seed == 99


def test_flag_off_partial_request_config_stays_request(promoted_file, fake_loader):
    response = GASplitStrategy().optimize(_request(ga_config={"max_iterations": 2}))
    assert response.effective_config_source == "request"


@pytest.mark.parametrize("cls", [GASplitStrategy, GAEnhancedSplitStrategy])
def test_empty_students_response_reports_source_and_seed(promoted_file, cls):
    response = cls().optimize(_empty_request())
    assert response.effective_config_source == "default"
    assert response.effective_seed == 42


def test_empty_students_reports_request_config_seed(promoted_file):
    response = GASplitStrategy().optimize(_empty_request(ga_config={"seed": 5}))
    assert response.effective_config_source == "request"
    assert response.effective_seed == 5


# --- ga_split_hf -----------------------------------------------------------


def test_hf_response_reports_default_source_and_seed(fake_loader):
    response = GASplitHFStrategy().optimize(_hf_request())
    assert response.success
    assert response.effective_config_source == "default"
    assert response.effective_seed == 42


def test_hf_response_reports_request_source_and_seed(fake_loader):
    response = GASplitHFStrategy().optimize(
        _hf_request(ga_config={"population_size": 6, "max_iterations": 2, "seed": 7})
    )
    assert response.effective_config_source == "request"
    assert response.effective_seed == 7


def test_hf_ignores_promoted_file_even_with_flag_on(promoted_file, fake_loader, monkeypatch):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    response = GASplitHFStrategy().optimize(_hf_request())
    assert response.effective_config_source == "default"
    assert response.effective_seed == 42


def test_hf_infeasible_path_reports_source_and_seed(fake_loader, monkeypatch):
    from strategies import ga_split_hf_strategy

    monkeypatch.setattr(
        ga_split_hf_strategy,
        "solve_ga_split_typed",
        lambda **_kwargs: SimpleNamespace(final_result=SimpleNamespace(feasible=False)),
    )
    response = GASplitHFStrategy().optimize(
        _hf_request(ga_config={"seed": 7, "max_iterations": 2})
    )
    assert response.success is False
    assert response.effective_config_source == "request"
    assert response.effective_seed == 7


def test_hf_empty_students_reports_source_and_seed():
    response = GASplitHFStrategy().optimize(_hf_request(students=[]))
    assert response.effective_config_source == "default"
    assert response.effective_seed == 42


# --- strategies that were not covered above -------------------------------


def _strategy_values(name):
    from strategies.pso_strategy import PSOStrategy
    from strategies.rdma_strategy import R2DMAStrategy
    from strategies.two_opt_strategy import TwoOptStrategy

    if name == "pso":
        s = PSOStrategy()
        return s.config.get("population_size"), s.config["max_iterations"]
    if name == "two_opt":
        s = TwoOptStrategy()
        return (s.config["max_iterations"],)
    s = R2DMAStrategy()
    return s._config.population_size, s._config.max_iterations


@pytest.fixture
def other_promoted_file(tmp_path, monkeypatch):
    entries = [
        ("pso", {"pop_size": 7, "iterations": 3}),
        ("two_opt", {"max_iterations": 3}),
        ("r2dma", {"population_size": 7, "max_iterations": 3}),
    ]
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "test",
                "configs": [
                    {"algorithm": a, "problem_type": "tsp", "matrix_kind": "distance", "params": p}
                    for a, p in entries
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


@pytest.mark.parametrize("name", ["pso", "two_opt", "r2dma"])
def test_other_strategies_ignore_promoted_file_when_flag_off(other_promoted_file, name):
    values = _strategy_values(name)
    assert 7 not in values and 3 not in values


@pytest.mark.parametrize("name", ["pso", "two_opt", "r2dma"])
def test_other_strategies_use_promoted_file_when_flag_on(other_promoted_file, monkeypatch, name):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    assert 3 in _strategy_values(name)


# --- benchmark-runner provenance (owner decision 2026-10-14) --------------


class _FailingStub:
    def optimize(self, request):
        return OptimizationResponse(algorithm_used="stub", success=False, routes=[])


def _runner_metadata(monkeypatch=None, *, registry=True):
    """Run one experiment. registry=True: stub comes from the runner's registry
    (like the web runner's STRATEGY_REGISTRY singletons); registry=False: the
    runner falls back to a fresh strategies.get_strategy() call."""
    problem = ProblemInstance(
        name="tiny4", dimension=4, problem_type="tsp", edge_weight_type="EUC_2D",
        category="small",
        coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        depot_index=0,
    )
    if registry:
        runner = BenchmarkRunner(strategies_registry={"stub": _FailingStub()})
    else:
        import strategies

        monkeypatch.setattr(strategies, "get_strategy", lambda name: _FailingStub())
        runner = BenchmarkRunner()
    result = runner._run_single_experiment(
        problem, AlgorithmConfig(name="Stub", algorithm_id="stub", params={}), 1
    )
    return result.metadata


def test_runner_metadata_records_flag_off_and_file_sha(promoted_file, monkeypatch):
    digest = hashlib.sha256(promoted_file.read_bytes()).hexdigest()
    metadata = _runner_metadata(monkeypatch, registry=False)
    assert metadata["promoted_config_flag"] is False
    assert metadata["promoted_config_sha256"] == digest


def test_runner_metadata_records_flag_on_for_fresh_strategy(promoted_file, monkeypatch):
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    metadata = _runner_metadata(monkeypatch, registry=False)
    assert metadata["promoted_config_flag"] is True
    assert metadata["promoted_config_snapshot"] == "call"


def test_registry_singletons_report_import_time_snapshot_not_current_flag(
    promoted_file, monkeypatch
):
    """The flag is set AFTER the registry singletons were built: they were built
    with defaults, so the record must say flag False (snapshot), not True."""
    import strategies

    assert strategies.REGISTRY_PROMOTED_PROVENANCE["promoted_config_flag"] is False
    monkeypatch.setenv(USE_PROMOTED_ENV, "1")
    metadata = _runner_metadata()
    assert metadata["promoted_config_flag"] is False
    assert metadata["promoted_config_sha256"] == (
        strategies.REGISTRY_PROMOTED_PROVENANCE["promoted_config_sha256"]
    )
    assert metadata["promoted_config_snapshot"] == "registry_import"


def test_provenance_sha_is_the_hash_of_what_was_loaded(promoted_file):
    from strategies.promoted_config_loader import promoted_config_provenance

    loaded_digest = hashlib.sha256(promoted_file.read_bytes()).hexdigest()
    assert promoted_config_provenance()["promoted_config_sha256"] == loaded_digest
    promoted_file.write_text('{"schema_version": 1, "source": "edited", "configs": []}')
    # the cached document is still the old one, so the reported hash must be too
    assert promoted_config_provenance()["promoted_config_sha256"] == loaded_digest
    clear_promoted_config_cache()
    assert promoted_config_provenance()["promoted_config_sha256"] != loaded_digest


def test_runner_metadata_sha_is_null_without_file(tmp_path, monkeypatch):
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(tmp_path / "missing.json"))
    monkeypatch.delenv(USE_PROMOTED_ENV, raising=False)
    clear_promoted_config_cache()
    metadata = _runner_metadata(monkeypatch, registry=False)
    assert metadata["promoted_config_flag"] is False
    assert metadata["promoted_config_sha256"] is None


def test_provenance_helper_shape(promoted_file):
    from strategies.promoted_config_loader import promoted_config_provenance

    assert set(promoted_config_provenance()) == {
        "promoted_config_flag",
        "promoted_config_sha256",
    }
