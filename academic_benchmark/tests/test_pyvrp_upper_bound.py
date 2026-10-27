"""Every pyvrp requirement must carry the ``<0.14`` upper bound.

PyVRP 0.14.0 replaced ``Model.add_depot(x=, y=)`` with a ``location`` argument,
so six PyVRP tests fail with 0.14.1 (D-04b2 strong-PC measurement; DECISION_LOG
A18, decision b). Until ``uniride_core/algorithms/pyvrp_cvrp_engine.py`` is
adapted, installs must stay below 0.14.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOUND = "<0.14"


def _is_pyvrp_requirement(line: str) -> bool:
    return re.match(r"\s*pyvrp\b", line, re.IGNORECASE) is not None


def _specifier_has_bound(spec: str) -> bool:
    return BOUND in spec.replace(" ", "")


def test_requirements_benchmark_pins_pyvrp_below_0_14():
    path = PROJECT_ROOT / "optimizer_api" / "requirements-benchmark.txt"
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if _is_pyvrp_requirement(line)
    ]

    assert lines, "requirements-benchmark.txt no longer names pyvrp"
    for line in lines:
        assert _specifier_has_bound(line), line


def test_pyproject_solvers_extra_pins_pyvrp_below_0_14():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = [
        entry
        for entry in data["project"]["optional-dependencies"]["solvers"]
        if _is_pyvrp_requirement(entry)
    ]

    assert entries, "pyproject solvers extra no longer names pyvrp"
    for entry in entries:
        assert _specifier_has_bound(entry), entry


def test_optimizer_requirements_install_hint_pins_pyvrp_below_0_14():
    path = PROJECT_ROOT / "optimizer_api" / "requirements.txt"
    hints = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if re.search(r"pip install\s+[\"']?pyvrp", line, re.IGNORECASE)
    ]

    assert hints, "requirements.txt no longer carries the pyvrp install hint"
    for hint in hints:
        assert _specifier_has_bound(hint), hint


def test_no_other_requirement_or_constraints_file_names_pyvrp_unbounded():
    """Any other requirements/constraints text file that names pyvrp needs the bound."""
    skipped_dirs = {"archive", "uniride.egg-info", "node_modules", ".venv-jit", ".venv", ".git", ".claude", ".next"}
    offenders = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in skipped_dirs]
        for filename in files:
            lowered = filename.lower()
            if not lowered.endswith(".txt") or not ("requirements" in lowered or "constraints" in lowered):
                continue
            path = Path(root) / filename
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if _is_pyvrp_requirement(line) and not _specifier_has_bound(line):
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{number}: {line.strip()}")

    assert offenders == []
