from optimizer_api.benchmark_runner import BenchmarkRunner


class DummyRequest:
    local_search_type = "two_opt"
    ga_config = None
    pso_config = None
    gwo_config = None
    hho_config = None
    two_opt_config = None
    sota_config = None


def test_benchmark_params_forward_to_ga_split_config():
    request = DummyRequest()

    BenchmarkRunner()._apply_algorithm_params(
        request,
        "ga_split",
        {"population_size": 12, "max_iterations": 20, "local_search_type": "three_opt"},
    )

    assert request.local_search_type == "three_opt"
    assert request.ga_config == {"population_size": 12, "max_iterations": 20}


def test_benchmark_params_forward_to_two_opt_config():
    request = DummyRequest()

    BenchmarkRunner()._apply_algorithm_params(
        request,
        "two_opt",
        {"max_iterations": 150, "first_improvement": True},
    )

    assert request.two_opt_config == {"max_iterations": 150, "first_improvement": True}


def test_benchmark_params_forward_to_sota_config():
    request = DummyRequest()

    BenchmarkRunner()._apply_algorithm_params(
        request,
        "e2bso",
        {"population_size": 12, "max_iterations": 20, "local_search_type": "or_opt"},
    )

    assert request.local_search_type == "or_opt"
    assert request.sota_config == {"population_size": 12, "max_iterations": 20}
