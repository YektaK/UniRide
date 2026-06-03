import importlib

from optimizer_api.strategies import sota_common as api_sota_common
from uniride_core.algorithms import sota_common as core_sota_common


def test_optimizer_sota_common_reexports_core_objects():
    assert api_sota_common.MultiStartInitializer is core_sota_common.MultiStartInitializer
    assert api_sota_common.MultiLayerLS is core_sota_common.MultiLayerLS
    assert api_sota_common.PenaltyManager is core_sota_common.PenaltyManager


def test_optimizer_sota_common_submodules_reexport_core_objects():
    module_names = (
        "acceptance_criteria",
        "destroy_operators",
        "diversity_controller",
        "multi_layer_ls",
        "multi_start_initializer",
        "penalty_manager",
        "repair_operators",
    )

    for module_name in module_names:
        api_module = importlib.import_module(f"optimizer_api.strategies.sota_common.{module_name}")
        core_module = importlib.import_module(f"uniride_core.algorithms.sota_common.{module_name}")

        public_names = [
            name
            for name, value in vars(core_module).items()
            if not name.startswith("_") and getattr(value, "__module__", None) == core_module.__name__
        ]
        assert public_names, f"{core_module.__name__} should expose public core-owned objects"
        for public_name in public_names:
            assert getattr(api_module, public_name) is getattr(core_module, public_name)
