"""Smoke test: every name in __all__ is importable."""

import importlib
import pytest

MODULES = [
    "uniride_core.algorithms.tsp_meta_engines",
    "uniride_core.algorithms.ga_operators",
    "uniride_core.algorithms.ga_split_engine",
    "uniride_core.algorithms.pso_split_engine",
    "uniride_core.algorithms.gwo_split_engine",
    "uniride_core.algorithms.hho_split_engine",
]


@pytest.mark.parametrize("module_path", MODULES)
def test_all_exports_importable(module_path):
    mod = importlib.import_module(module_path)
    for name in mod.__all__:
        assert hasattr(mod, name), f"{module_path}.__all__ lists '{name}' but it is not defined"
