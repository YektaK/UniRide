from optimizer_api.strategies.cvrptw_wrapper import CVRPTWDecoder as ApiDecoder
from uniride_core.algorithms.cvrptw_decoder import CVRPTWDecoder as CoreDecoder


def test_cvrptw_wrapper_reexports_core_decoder():
    assert ApiDecoder is CoreDecoder
