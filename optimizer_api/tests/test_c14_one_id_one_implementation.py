"""Gate C item C-14 (audit H9, owner Q10 option a): one ID, one implementation.

Every ID must name exactly one callable in every entry point (CLI resolver plus
registry, ``AlgorithmRegistry``, ``engine_factory`` and the web matrix mode).
The matrix-native engines carry truthful ``Matrix-*-legacy`` names; ``Core-*``
catalog IDs resolve only through the catalog and the gateway.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException

from academic_benchmark.core import registry_setup
from academic_benchmark.core.algorithm_resolution import (
    CLI_ALIAS_TARGETS,
    IdentifierSource,
    resolve_algorithm_id,
)
from academic_benchmark.engine_core import AlgorithmRegistry
from optimizer_api.routers import benchmark
from uniride_core.algorithms import engine_factory, tsp_meta_engines
from uniride_core.algorithms.capabilities import CAPABILITY_CATALOG

REPO = Path(__file__).resolve().parents[2]

MATRIX_LEGACY_SOLVERS = {
    "Matrix-TwoOpt-TSP-legacy": "solve_two_opt_tsp",
    "Matrix-GA-TSP-legacy": "solve_ga_tsp",
    "Matrix-PSO-TSP-legacy": "solve_pso_tsp",
    "Matrix-GWO-TSP-legacy": "solve_gwo_tsp",
    "Matrix-HHO-TSP-legacy": "solve_hho_tsp",
}
OLD_MATRIX_NAMES = (
    "Core-TwoOpt-TSP", "Core-GA-TSP", "Core-PSO-TSP", "Core-GWO-TSP", "Core-HHO-TSP",
    "Core-2OPT-TSP", "Core-2-opt-TSP", "Core-Genetic-TSP",
)
CORE_IDS = sorted(set(CAPABILITY_CATALOG) | set(OLD_MATRIX_NAMES))


def _factory_solver(name: str):
    """What ``engine_factory`` builds for ``name`` (None when it refuses)."""
    try:
        engine = engine_factory.create_matrix_engine(name)
        engine_factory.canonical_matrix_engine_name(name)
    except KeyError:
        return None
    return engine._solver


_RUN_COUNTER = iter(range(10_000))


def _web_matrix_mode(monkeypatch, name: str):
    """What the web matrix mode builds for ``name`` ((config name, solver) or None)."""
    tm = importlib.import_module("academic_benchmark.tsplib_manager")
    monkeypatch.setattr(tm, "load_routing_problem", lambda n: types.SimpleNamespace(name=n))
    monkeypatch.setattr(tm, "save_benchmark_run", lambda *a, **k: None)
    monkeypatch.setattr(tm, "save_benchmark_result", lambda *a, **k: None)
    br = importlib.import_module("uniride_core.benchmark_runner")
    seen: list = []

    class RecordingRunner:
        def __init__(self, algorithms):
            seen.extend(algorithms)

        def run_one(self, *args, **kwargs):
            raise RuntimeError("c14 recording runner stops here")

    monkeypatch.setattr(br, "MatrixBenchmarkRunner", RecordingRunner)
    run_id = f"c14-web-{next(_RUN_COUNTER)}"
    try:
        benchmark._start_matrix_native_benchmark_impl(run_id, [{"id": name}], ["p"], {"n_runs": 1})
    except HTTPException as exc:
        assert exc.status_code == 400
        return None
    benchmark.benchmark_state_manager.get_run(run_id).thread.join(timeout=30)
    assert len(seen) == 1
    return seen[0].name, seen[0].engine._solver


@pytest.mark.parametrize("name", CORE_IDS)
@pytest.mark.parametrize("entry", ["engine_factory", "web_matrix_mode"])
def test_core_ids_never_reach_a_matrix_engine(monkeypatch, entry: str, name: str) -> None:
    resolved = _factory_solver(name) if entry == "engine_factory" else _web_matrix_mode(monkeypatch, name)
    assert resolved is None, f"{name} reaches a matrix engine through {entry}"


@pytest.mark.parametrize("name,solver_name", sorted(MATRIX_LEGACY_SOLVERS.items()))
def test_matrix_legacy_names_resolve_to_one_solver_in_every_entry_point(
    monkeypatch, name: str, solver_name: str
) -> None:
    solver = getattr(tsp_meta_engines, solver_name)
    assert _factory_solver(name) is solver
    assert engine_factory.canonical_matrix_engine_name(name) == name
    assert _web_matrix_mode(monkeypatch, name) == (name, solver)
    assert name in engine_factory.list_matrix_engine_names()
    # registry: the name is registered and is not a catalog ID's executor
    executor = AlgorithmRegistry.get_executor(name)
    for catalog_id in CAPABILITY_CATALOG:
        assert AlgorithmRegistry.get_executor(catalog_id) is not executor
    # the CLI gateway never turns a legacy matrix name into a canonical ID
    with pytest.raises(Exception):
        resolve_algorithm_id(name, IdentifierSource.CLI)


def test_factory_exposes_no_core_name_except_the_greedy_routing_engine() -> None:
    core = [n for n in engine_factory.list_matrix_engine_names() if n.startswith("Core-")]
    assert core == ["Core-Greedy-Routing"]


def test_registry_name_and_factory_name_never_diverge_for_core_ids() -> None:
    """A name shared by the registry and the factory must not be a Core-* name."""
    shared = set(AlgorithmRegistry.list_algorithms()) & set(engine_factory.list_matrix_engine_names())
    core_shared = {n for n in shared if n.startswith("Core-") and n != "Core-Greedy-Routing"}
    assert core_shared == set()


def test_duplicate_registration_raises() -> None:
    name = "C14-Duplicate-Fixture"
    try:
        AlgorithmRegistry.register(name)(lambda *a, **k: None)
        with pytest.raises(ValueError, match=name):
            AlgorithmRegistry.register(name)(lambda *a, **k: None)
    finally:
        AlgorithmRegistry._registry.pop(name, None)


def test_registry_setup_import_registers_no_name_twice(tmp_path) -> None:
    """A fresh import of registry_setup must not trip the duplicate guard."""
    script = tmp_path / "import_registry_setup.py"
    script.write_text("import academic_benchmark.core.registry_setup" + chr(10), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO)},
        text=True, capture_output=True, timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-1500:]


def test_raw_numba_ga_and_pso_are_not_registered_so_the_alias_reaches_only_the_canonical_ga() -> None:
    registered = set(AlgorithmRegistry.list_algorithms())
    for raw, canonical in (("Numba-GA", "Core-GA-TSP"), ("Numba-PSO", "Core-PSO-TSP")):
        assert CLI_ALIAS_TARGETS[raw] == canonical
        assert raw not in registered
        assert canonical in registered


def test_routing_alias_engines_use_factory_legacy_names_only() -> None:
    for alias, engine_name in registry_setup._ROUTING_ALIAS_ENGINES.items():
        assert engine_name not in CAPABILITY_CATALOG, alias
        assert not engine_name.startswith("Core-") or engine_name == "Core-Greedy-Routing", alias
        engine_factory.create_matrix_engine(engine_name)


FAIL_CLOSED_SCRIPT = """
import sys
sys.modules['uniride_core.algorithms.tsp_matrix_metaheuristics'] = None
try:
    import academic_benchmark.core.registry_setup
except ImportError:
    sys.exit(0)
from academic_benchmark.engine_core import AlgorithmRegistry
print('REGISTERED', 'Core-GWO-TSP-Pure' in AlgorithmRegistry.list_algorithms())
sys.exit(3)
"""


def test_failed_numba_metaheuristic_import_fails_closed(tmp_path) -> None:
    script = tmp_path / "fail_closed.py"
    script.write_text(FAIL_CLOSED_SCRIPT, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO)},
        text=True, capture_output=True, timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr[-1500:]
