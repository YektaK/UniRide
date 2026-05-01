import academic_benchmark.run_smart_benchmark_numba as numba_bench
import academic_benchmark.run_smart_benchmark_sota as sota_bench


def test_worker_backend_selection_supports_fallback():
    backend = numba_bench.get_worker_backend_module(prefer_numba=False)
    assert backend in {
        "optimizer_api.tests.run_interactive_benchmark_v2",
        "optimizer_api.tests.run_interactive_benchmark_v2_numba",
    }


def test_deterministic_seed_is_stable():
    s1 = sota_bench.make_deterministic_seed("berlin52", "E2BSO-TSP", 0, 0, 1000)
    s2 = sota_bench.make_deterministic_seed("berlin52", "E2BSO-TSP", 0, 0, 1000)
    s3 = sota_bench.make_deterministic_seed("berlin52", "E2BSO-TSP", 1, 0, 1000)

    assert s1 == s2
    assert s1 != s3
