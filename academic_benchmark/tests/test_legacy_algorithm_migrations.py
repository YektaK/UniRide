import builtins
import sys
from types import SimpleNamespace

import pytest

from academic_benchmark import cli_engine
from academic_benchmark import smart_benchmark
from uniride_core.algorithms import numba_accel


LEGACY_ALGORITHM_MIGRATIONS = {
    "B-GA": "Core-GA-TSP",
    "B-PSO": "Core-PSO-TSP",
}


@pytest.mark.parametrize("legacy_id,replacement_id", LEGACY_ALGORITHM_MIGRATIONS.items())
def test_legacy_algorithm_validator_rejects_ids_with_canonical_replacement(
    legacy_id, replacement_id
):
    assert cli_engine.LEGACY_ALGORITHM_MIGRATIONS[legacy_id] == replacement_id

    with pytest.raises(ValueError, match=replacement_id):
        cli_engine._validate_algorithm_migration(legacy_id)


@pytest.mark.parametrize("legacy_id,replacement_id", LEGACY_ALGORITHM_MIGRATIONS.items())
def test_legacy_algorithms_are_rejected_before_any_solver_execution(
    monkeypatch, legacy_id, replacement_id
):
    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            raise AssertionError("retired legacy solver must not enumerate the registry")

        @staticmethod
        def get_executor(_algorithm_id):
            raise AssertionError("retired legacy solver must not request a registry executor")

    monkeypatch.setattr(cli_engine, "_HAS_NUMBA_REGISTRY", True)
    monkeypatch.setattr(cli_engine, "_AlgoReg", ExplodingRegistry)

    task = (
        {
            "name": "legacy-rejection",
            "dimension": 0,
            "coordinates": [],
            "optimal": None,
        },
        legacy_id,
        legacy_id,
        {},
        0,
        1,
    )

    with pytest.raises(ValueError, match=replacement_id):
        cli_engine._evaluate_param_combo(task)


def test_detect_numba_imports_canonical_module_without_mutating_sys_path(monkeypatch):
    original_import = builtins.__import__
    imports = []

    def recording_import(name, *args, **kwargs):
        imports.append(name)
        if name == "numba":
            raise ImportError("force canonical acceleration boundary")
        return original_import(name, *args, **kwargs)

    before = list(sys.path)
    monkeypatch.setattr(builtins, "__import__", recording_import)

    assert cli_engine._detect_numba() is bool(numba_accel.NUMBA_AVAILABLE)
    assert "uniride_core.algorithms" in imports
    assert sys.path == before

@pytest.mark.parametrize("legacy_id,replacement_id", LEGACY_ALGORITHM_MIGRATIONS.items())
def test_cli_main_rejects_retired_ids_before_setup_or_registry_enumeration(
    monkeypatch, legacy_id, replacement_id
):
    def explode(*_args, **_kwargs):
        raise AssertionError("legacy id reached CLI setup or registry enumeration")

    monkeypatch.setattr(cli_engine, "_ensure_dirs", explode)
    monkeypatch.setattr(cli_engine, "_param_db_set", explode)
    monkeypatch.setattr(cli_engine, "_all_strategy_specs", explode)
    monkeypatch.setattr(cli_engine, "load_problems", explode)

    with pytest.raises(ValueError, match=replacement_id):
        cli_engine.main(["--mode", "default", "--algos", legacy_id])


@pytest.mark.parametrize("legacy_id,replacement_id", LEGACY_ALGORITHM_MIGRATIONS.items())
def test_smart_benchmark_rejects_retired_ids_before_db_matrix_registry_or_warmup(
    monkeypatch, legacy_id, replacement_id
):
    def explode(*_args, **_kwargs):
        raise AssertionError("retired id reached smart benchmark setup")

    class ExplodingRegistry:
        @staticmethod
        def list_algorithms():
            explode()

        @staticmethod
        def get_executor(_algorithm_id):
            explode()

    monkeypatch.setattr(smart_benchmark, "_db_get_best", explode)
    monkeypatch.setattr(smart_benchmark, "_dm_from_cache", explode)
    monkeypatch.setattr(smart_benchmark, "run_warmup", explode)
    monkeypatch.setattr(smart_benchmark, "AlgorithmRegistry", ExplodingRegistry)

    problem = SimpleNamespace(name="legacy-boundary", dist_matrix=None, coordinates=[])
    with pytest.raises(ValueError, match=replacement_id):
        smart_benchmark.run_unified_benchmark(
            [problem], [legacy_id], "db", 1, 1, {"results": {}}
        )
