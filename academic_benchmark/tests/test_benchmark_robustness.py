from academic_benchmark.benchmark_utils import make_deterministic_seed


def test_worker_backend_selection_supports_fallback():
    """Verify that academic-owned worker backends are importable."""
    candidates = [
        "academic_benchmark.cli_engine",
        "academic_benchmark.smart_benchmark",
    ]
    importable = []
    for mod in candidates:
        try:
            __import__(mod)
            importable.append(mod)
        except Exception:
            pass
    assert importable, "No benchmark worker backend is importable"


def test_deterministic_seed_is_stable():
    s1 = make_deterministic_seed("berlin52", "E2BSO-TSP", 0, 0, 1000)
    s2 = make_deterministic_seed("berlin52", "E2BSO-TSP", 0, 0, 1000)
    s3 = make_deterministic_seed("berlin52", "E2BSO-TSP", 1, 0, 1000)

    assert s1 == s2
    assert s1 != s3
