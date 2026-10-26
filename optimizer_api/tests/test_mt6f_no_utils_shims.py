"""MT6F-02 (audit L3-d): the 20 ``optimizer_api/utils`` re-export shims are gone.

Two guards:

1. No Python file in ``optimizer_api`` (tests included), ``academic_benchmark``,
   ``uniride_core`` or the repository root imports a shim, neither statically nor
   by an ``importlib``/``patch``/``setattr`` string target.  Callers use
   ``uniride_core.algorithms.<module>`` directly.
2. None of the 20 modules can be found by ``importlib.util.find_spec`` under
   either import spelling (``utils.<m>`` as run from ``optimizer_api``, or
   ``optimizer_api.utils.<m>``).

The real modules that stay in ``optimizer_api/utils`` (``data_loader``,
``matrix_repository``, ``patterns``, ``resource_profiler_demo``) are not shims
and are not covered here.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
THIS_FILE = Path(__file__).resolve()

SHIM_MODULES = (
    "clustering",
    "haversine",
    "linear_split_decoder",
    "local_search",
    "local_search_numba",
    "resource_profiler",
    "scheduling",
    "split_decoder",
    "time_window_extractor",
    "time_window_violation_tracker",
    "tsplib_parser",
)
STRATEGY_PACKAGE = "clustering_strategies"
STRATEGY_MODULES = (
    "base",
    "clarke_wright",
    "fuzzy_cmeans",
    "fuzzy_cmeans_enhanced",
    "hierarchical_fcm",
    "k_medoids",
    "kmeans",
    "sweep",
)
# 11 top-level shims + the clustering_strategies package __init__ + 8 modules.
ALL_SHIM_NAMES = (
    *SHIM_MODULES,
    STRATEGY_PACKAGE,
    *(f"{STRATEGY_PACKAGE}.{name}" for name in STRATEGY_MODULES),
)
PREFIXES = ("utils", "optimizer_api.utils")

SCAN_DIRS = ("optimizer_api", "academic_benchmark", "uniride_core")
SKIP_PARTS = {".venv", ".venv-jit", "node_modules", "__pycache__", ".git", ".claude"}
STRING_TARGET_CALLS = {"import_module", "__import__", "patch", "setattr", "find_spec"}


def _shim_hit(dotted: str) -> str | None:
    """Return the shim name when ``dotted`` is a (sub)module of a shim."""
    for prefix in PREFIXES:
        head = prefix + "."
        if not dotted.startswith(head):
            continue
        rest = dotted[len(head):]
        for name in ALL_SHIM_NAMES:
            if rest == name or rest.startswith(name + "."):
                return name
    return None


def _python_files():
    files = sorted(REPO_ROOT.glob("*.py"))
    for directory in SCAN_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            if SKIP_PARTS.intersection(path.parts):
                continue
            files.append(path)
    return [path for path in files if path.resolve() != THIS_FILE]


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _violations_in(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    inside_utils = "utils" in path.parts and "optimizer_api" in path.parts
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _shim_hit(alias.name):
                    found.append(f"{path}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _shim_hit(module):
                found.append(f"{path}:{node.lineno}: from {'.' * node.level}{module} import ...")
            elif module in PREFIXES:
                for alias in node.names:
                    if _shim_hit(f"{module}.{alias.name}"):
                        found.append(f"{path}:{node.lineno}: from {module} import {alias.name}")
            elif inside_utils and node.level:
                # relative import inside optimizer_api/utils: ``from .x import`` / ``from . import x``
                for alias in node.names:
                    target = module or alias.name
                    if any(target == n or target.startswith(n + ".") for n in ALL_SHIM_NAMES):
                        found.append(f"{path}:{node.lineno}: relative import of {target}")
        elif isinstance(node, ast.Call) and _call_name(node) in STRING_TARGET_CALLS:
            for arg in node.args[:2]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if _shim_hit(arg.value):
                        found.append(f"{path}:{node.lineno}: string target {arg.value!r}")
    return found


def test_no_python_file_imports_a_utils_shim():
    violations: list[str] = []
    for path in _python_files():
        violations.extend(_violations_in(path))
    assert not violations, "utils shim imports remain:\n" + "\n".join(violations)


def test_scanner_detects_each_import_spelling(tmp_path):
    """The scan must not be vacuous: every spelling it claims to catch is caught."""
    samples = {
        "static_from.py": "from utils.scheduling import minutes_to_time\n",
        "static_pkg_from.py": "from optimizer_api.utils.split_decoder import SplitDecoder\n",
        "static_import.py": "import optimizer_api.utils.clustering_strategies.kmeans\n",
        "from_package.py": "from utils import resource_profiler\n",
        "from_strategies.py": "from utils.clustering_strategies import get_clustering_strategy\n",
        "string_target.py": "import importlib\nimportlib.import_module('utils.tsplib_parser')\n",
        "patch_target.py": "monkeypatch.setattr('optimizer_api.utils.scheduling.minutes_to_time', None)\n",
    }
    for name, source in samples.items():
        sample = tmp_path / name
        sample.write_text(source, encoding="utf-8")
        assert _violations_in(sample), f"scanner missed {name}"
    clean = tmp_path / "clean.py"
    clean.write_text(
        "from utils import matrix_repository\n"
        "from utils.data_loader import x\n"
        "from uniride_core.algorithms.scheduling import minutes_to_time\n",
        encoding="utf-8",
    )
    assert not _violations_in(clean)


def _spec_or_none(name: str):
    try:
        return importlib.util.find_spec(name)
    except (ImportError, ValueError, AttributeError):
        return None


def _is_real_module(spec) -> bool:
    """A leftover ``__pycache__``-only directory is a namespace package, not a shim."""
    if spec is None:
        return False
    if spec.origin not in (None, "namespace"):
        return True
    locations = list(spec.submodule_search_locations or [])
    return any(list(Path(location).glob("*.py")) for location in locations)


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("name", ALL_SHIM_NAMES)
def test_shim_module_is_not_importable(prefix, name):
    assert not _is_real_module(_spec_or_none(f"{prefix}.{name}")), (
        f"{prefix}.{name} is still importable; it should have been deleted (MT6F-02)"
    )


def test_core_modules_the_shims_pointed_at_still_import():
    """Callers moved to the core path; make sure those targets are real."""
    # scheduling -> route_scheduling, split_decoder -> string_split_decoder,
    # haversine -> distance; the clustering shim also re-exported
    # vehicle_assignment.VehicleCalculator.
    renamed = {
        "scheduling": "route_scheduling",
        "split_decoder": "string_split_decoder",
        "haversine": "distance",
    }
    for name in (*(renamed.get(n, n) for n in SHIM_MODULES), "vehicle_assignment"):
        assert importlib.util.find_spec(f"uniride_core.algorithms.{name}") is not None, name
    assert importlib.util.find_spec("uniride_core.algorithms.clustering_strategies") is not None
