from academic_benchmark.param_spaces import (
    CVRP_PARAM_SPACES,
    CVRPTW_PARAM_SPACES,
    NUMBA_PARAM_SPACES,
    SOTA_PARAM_SPACES,
    build_doe_space,
    build_optuna_space,
)


class _Trial:
    def suggest_int(self, name, low, high):
        return low

    def suggest_float(self, name, low, high):
        return low

    def suggest_categorical(self, name, choices):
        return choices[0]


def test_cvrp_param_spaces_cover_core_sota_and_numba_aliases():
    expected = {
        "CVRP-Core-Greedy-Routing",
        "CVRP-Core-GA-TSP",
        "CVRP-SOTA-E2BSO-TSP",
        "CVRP-Numba-GA",
        "CVRP-Numba-HHO",
    }

    assert expected.issubset(CVRP_PARAM_SPACES)
    for name in expected:
        assert "split_method" in CVRP_PARAM_SPACES[name]
        assert "capacity_penalty" in CVRP_PARAM_SPACES[name]


def test_cvrptw_param_spaces_add_time_window_penalties():
    space = CVRPTW_PARAM_SPACES["CVRPTW-Core-HHO-TSP"]

    assert space["split_method"]["doe"] == ["optimal_split"]
    assert "tw_penalty_rate" in space
    assert "max_route_duration_penalty" in space


def test_routing_spaces_are_visible_to_existing_builders():
    doe = build_doe_space("CVRP-SOTA-E2BSO-TSP", source="sota")
    optuna = build_optuna_space("CVRP-SOTA-E2BSO-TSP", _Trial())
    numba = build_doe_space("CVRPTW-Numba-GA", source="numba")

    assert doe["split_method"] == ["optimal_split"]
    assert optuna["split_method"] == "optimal_split"
    assert "capacity_penalty" in numba
    assert "CVRPTW-Numba-GA" in NUMBA_PARAM_SPACES
    assert "CVRP-SOTA-E2BSO-TSP" in SOTA_PARAM_SPACES


def test_plain_tsp_spaces_do_not_include_routing_only_knobs():
    assert "split_method" not in build_doe_space("E2BSO-TSP", source="sota")
    assert "capacity_penalty" not in build_doe_space("GA", source="numba")
