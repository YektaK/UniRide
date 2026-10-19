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

