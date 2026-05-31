from strategies.hho_strategy import HarrisHawksOptimizerStrategy
from strategies.pso_strategy import PSOStrategy


def test_pso_strategy_does_not_keep_instance_rng():
    strategy = PSOStrategy({"seed": 123})

    assert not hasattr(strategy, "rng")


def test_hho_strategy_does_not_keep_instance_rng():
    strategy = HarrisHawksOptimizerStrategy({"seed": 123})

    assert not hasattr(strategy, "rng")
