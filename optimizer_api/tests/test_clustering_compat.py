from optimizer_api.utils.clustering import VehicleCalculator as ApiVehicleCalculator
from optimizer_api.utils.clustering_strategies import get_clustering_strategy as api_get_strategy
from uniride_core.algorithms.clustering_strategies import get_clustering_strategy as core_get_strategy
from uniride_core.algorithms.vehicle_assignment import VehicleCalculator as CoreVehicleCalculator


def test_optimizer_clustering_reexports_core_vehicle_calculator():
    assert ApiVehicleCalculator is CoreVehicleCalculator


def test_optimizer_clustering_strategy_factory_reexports_core():
    assert api_get_strategy("sweep").__class__ is core_get_strategy("sweep").__class__
