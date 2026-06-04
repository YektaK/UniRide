from __future__ import annotations

import ast
from pathlib import Path


def test_uniride_core_does_not_import_optimizer_api():
    root = Path(__file__).resolve().parents[1]
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
            if any(name == "optimizer_api" or name.startswith("optimizer_api.") for name in names):
                offenders.append(str(path.relative_to(root)))

    assert offenders == []
