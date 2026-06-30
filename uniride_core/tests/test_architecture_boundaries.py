from __future__ import annotations

import ast
from pathlib import Path


def _read_python_source(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def test_uniride_core_does_not_import_application_layers():
    root = Path(__file__).resolve().parents[1]
    disallowed_roots = ("optimizer_api", "academic_benchmark")
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == root_name or name.startswith(f"{root_name}.") for root_name in disallowed_roots):
                    offenders.append(f"{path.relative_to(root)} imports {name}")

    assert offenders == []


def test_active_benchmark_helpers_do_not_import_optimizer_api_algorithm_shims():
    project_root = Path(__file__).resolve().parents[1].parent
    benchmark_helpers = [
        project_root / ".temp_master_numba.py",
        project_root / "optimizer_api" / "tests" / "run_interactive_benchmark_v2_numba.py",
        project_root / "optimizer_api" / "tests" / "run_smart_benchmark_numba.py",
    ]
    disallowed_modules = {
        "optimizer_api.utils.local_search",
        "optimizer_api.utils.local_search_numba",
        "optimizer_api.utils.split_decoder",
        "optimizer_api.utils.linear_split_decoder",
        "optimizer_api.utils.clustering",
        "optimizer_api.utils.clustering_strategies",
    }
    offenders: list[str] = []

    for path in benchmark_helpers:
        if not path.exists():
            continue
        tree = ast.parse(_read_python_source(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(
                name in disallowed_modules
                or any(name.startswith(f"{module}.") for module in disallowed_modules)
                for name in names
            ):
                offenders.append(str(path.relative_to(project_root)))

    assert offenders == []
