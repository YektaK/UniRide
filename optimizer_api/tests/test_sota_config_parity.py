from models.schemas import OptimizationRequest
from strategies.ebso_strategy import E2BSoStrategy
from strategies.ga_strategy import GeneticAlgorithmStrategy
from strategies.hho_split_strategy import HHOSplitStrategy
from strategies.promoted_config_loader import (
    PROMOTED_CONFIG_PATH_ENV,
    clear_promoted_config_cache,
    get_promoted_params,
    get_promoted_strategy_params,
)
from strategies.sota_config_utils import merge_sota_config
from uniride_core.algorithms.sota_tsp import E2BSOTSPConfig, PAOEAConfig


def test_merge_sota_config_applies_valid_request_overrides():
    base = E2BSOTSPConfig(population_size=24, max_iterations=200, seed=42)

    merged = merge_sota_config(base, {
        "population_size": 8,
        "max_iterations": 10,
        "seed": 7,
        "unknown": "ignored",
    })

    assert merged.population_size == 8
    assert merged.max_iterations == 10
    assert merged.seed == 7
    assert not hasattr(merged, "unknown")
    assert base.population_size == 24


def test_merge_sota_config_converts_list_to_tuple_for_tuple_fields():
    base = PAOEAConfig()

    merged = merge_sota_config(base, {"destroy_ops_pool": ["random", "worst"]})

    assert merged.destroy_ops_pool == ("random", "worst")


def test_optimization_request_accepts_sota_config():
    request = OptimizationRequest(
        depot={"id": "A", "lat": 0.0, "lng": 0.0},
        students=[
            {
                "id": "S1",
                "location_code": "B",
                "coordinates": {"lat": 1.0, "lng": 1.0},
                "disability_type": "Sw",
            }
        ],
        algorithm="e2bso",
        sota_config={"population_size": 8, "max_iterations": 10},
    )

    assert request.sota_config == {"population_size": 8, "max_iterations": 10}


def test_promoted_params_load_from_runtime_config_path(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source": "test",
  "configs": [
    {
      "algorithm": "e2bso",
      "problem_type": "tsp",
      "matrix_kind": "distance",
      "params": {"population_size": 12, "max_iterations": 14}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    clear_promoted_config_cache()

    assert get_promoted_params("e2bso") == {"population_size": 12, "max_iterations": 14}


def test_sota_strategy_constructor_uses_promoted_params(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source": "test",
  "configs": [
    {
      "algorithm": "e2bso",
      "problem_type": "tsp",
      "matrix_kind": "distance",
      "params": {"population_size": 12, "max_iterations": 14}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    clear_promoted_config_cache()

    strategy = E2BSoStrategy()

    assert strategy._config.population_size == 12
    assert strategy._config.max_iterations == 14


def test_promoted_strategy_params_normalize_academic_numba_keys(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source": "test",
  "configs": [
    {
      "algorithm": "Numba-GA",
      "problem_type": "tsp",
      "matrix_kind": "distance",
      "params": {"pop_size": 44, "generations": 55, "elite_size": 6}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    clear_promoted_config_cache()

    assert get_promoted_strategy_params(("genetic_algorithm", "ga", "Numba-GA")) == {
        "population_size": 44,
        "max_iterations": 55,
        "elite_count": 6,
    }


def test_ga_strategy_constructor_uses_promoted_defaults_but_explicit_config_wins(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source": "test",
  "configs": [
    {
      "algorithm": "Numba-GA",
      "problem_type": "tsp",
      "matrix_kind": "distance",
      "params": {"pop_size": 44, "generations": 55}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    clear_promoted_config_cache()

    promoted_strategy = GeneticAlgorithmStrategy()
    explicit_strategy = GeneticAlgorithmStrategy({"population_size": 12})

    assert promoted_strategy.config["population_size"] == 44
    assert promoted_strategy.config["max_iterations"] == 55
    assert explicit_strategy.config["population_size"] == 12


def test_split_strategy_constructor_uses_promoted_routing_defaults(tmp_path, monkeypatch):
    path = tmp_path / "promoted_configs.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source": "test",
  "configs": [
    {
      "algorithm": "CVRPTW-HHO-Split",
      "problem_type": "cvrptw",
      "matrix_kind": "travel_time",
      "params": {"hawks": 33, "iterations": 44}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(PROMOTED_CONFIG_PATH_ENV, str(path))
    clear_promoted_config_cache()

    strategy = HHOSplitStrategy()

    assert strategy.config["population_size"] == 33
    assert strategy.config["max_iterations"] == 44
