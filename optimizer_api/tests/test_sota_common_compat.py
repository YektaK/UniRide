from optimizer_api.strategies import sota_common as api_sota_common
from uniride_core.algorithms import sota_common as core_sota_common


def test_optimizer_sota_common_reexports_core_objects():
    assert api_sota_common.MultiStartInitializer is core_sota_common.MultiStartInitializer
    assert api_sota_common.MultiLayerLS is core_sota_common.MultiLayerLS
    assert api_sota_common.PenaltyManager is core_sota_common.PenaltyManager
