import ast
from pathlib import Path


def test_data_loader_keeps_app_glue_boundary_without_solver_imports():
    path = Path(__file__).resolve().parents[1] / "utils" / "data_loader.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module or "")

    assert "uniride_core.algorithms.distance" in imported_modules
    assert not any(module.startswith("uniride_core.engines") for module in imported_modules)
    assert not any(module.startswith("uniride_core.algorithms.ga_") for module in imported_modules)
    assert not any(module.startswith("uniride_core.algorithms.pso_") for module in imported_modules)
    assert not any(module.startswith("uniride_core.algorithms.gwo_") for module in imported_modules)
    assert not any(module.startswith("uniride_core.algorithms.hho_") for module in imported_modules)
    assert not any("optimizer_api.strategies" in module for module in imported_modules)
