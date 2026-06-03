from __future__ import annotations

from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_pins_compatible_pydantic_pair():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(data["project"]["dependencies"])

    assert "pydantic==2.13.4" in dependencies
    assert "pydantic-core==2.46.4" in dependencies


def test_pyproject_declares_optional_solver_dependencies():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    solvers = set(data["project"]["optional-dependencies"]["solvers"])

    assert {"ortools", "pyvrp", "pyvroom", "vrplib"}.issubset(solvers)
