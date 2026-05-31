from optimizer_api.models.schemas import OptimizationRequest
from optimizer_api.strategies.sota_config_utils import merge_sota_config
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
