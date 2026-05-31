import academic_benchmark.core.registry_setup  # noqa: F401

from academic_benchmark.core.registry_setup import AlgorithmRegistry
from academic_benchmark.param_spaces import NUMBA_PARAM_SPACES, build_doe_space, build_optuna_space


def test_academic_registry_exposes_fcm_srs_tsp_engines():
    names = set(AlgorithmRegistry.list_algorithms())

    assert {"FCM-GA-TSP", "FCM-PSO-TSP", "FCM-GWO-TSP", "FCM-HHO-TSP"}.issubset(names)


def test_fcm_srs_param_spaces_include_fcm_and_base_parameters():
    space = NUMBA_PARAM_SPACES["FCM-GA-TSP"]

    assert "fcm_clusters" in space
    assert "fcm_m" in space
    assert "population_size" in space or "pop_size" in space


def test_fcm_srs_doe_space_can_be_built():
    space = build_doe_space("FCM-PSO-TSP", source="numba")

    assert space
    assert space["fcm_clusters"] == [2, 3, 4]


def test_fcm_srs_optuna_space_can_be_built_from_numba_fallback():
    class Trial:
        def suggest_int(self, name, lo, hi):
            return lo

        def suggest_float(self, name, lo, hi):
            return lo

        def suggest_categorical(self, name, values):
            return values[0]

    params = build_optuna_space("FCM-HHO-TSP", Trial())

    assert params["fcm_clusters"] == 2
    assert params["fcm_m"] == 1.1
