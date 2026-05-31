import pytest

from uniride_core.algorithms.engine_factory import (
    canonical_matrix_engine_name,
    create_matrix_engine,
    list_matrix_engine_names,
)
from uniride_core.algorithms.fcm_split_engine import FCMSplitMatrixEngine
from uniride_core.algorithms.greedy_engine import GreedyMatrixEngine
from uniride_core.algorithms.tsp_meta_matrix_engine import TSPMetaMatrixEngine


def test_matrix_engine_factory_lists_core_engines():
    names = set(list_matrix_engine_names())

    assert {
        "Core-Greedy-Routing",
        "Core-TwoOpt-TSP",
        "Core-GA-TSP",
        "Core-PSO-TSP",
        "Core-GWO-TSP",
        "Core-HHO-TSP",
        "FCM-GA-TSP",
        "FCM-PSO-TSP",
        "FCM-GWO-TSP",
        "FCM-HHO-TSP",
    }.issubset(names)


def test_matrix_engine_factory_creates_greedy_and_tsp_engines():
    assert isinstance(create_matrix_engine("Core-Greedy-Routing"), GreedyMatrixEngine)
    assert isinstance(create_matrix_engine("Core-GA-TSP"), TSPMetaMatrixEngine)
    assert isinstance(create_matrix_engine("FCM-GA-TSP"), FCMSplitMatrixEngine)


def test_matrix_engine_factory_normalizes_aliases():
    assert canonical_matrix_engine_name("Core-2OPT-TSP") == "Core-TwoOpt-TSP"
    assert canonical_matrix_engine_name("Core-Genetic-TSP") == "Core-GA-TSP"
    assert canonical_matrix_engine_name("greedy") == "Core-Greedy-Routing"


def test_matrix_engine_factory_rejects_unknown_engine():
    with pytest.raises(KeyError):
        create_matrix_engine("not-a-core-engine")
