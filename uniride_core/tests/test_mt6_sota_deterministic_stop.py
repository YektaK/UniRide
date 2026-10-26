"""MT6-03 (audit H11): SOTA TSP solvers stop on iteration limits, not on wall clock.

A SOTA result must be a function of its seed and configuration only. The wall
clock is allowed in exactly one place: the optional ``deadline_seconds`` safety
deadline (``uniride_core/algorithms/sota_tsp/deadline.py``). When that deadline
is hit the result says so (``termination_reason == "wall_clock_deadline"``,
``reproducible is False``; both live in ``TSPResult.extra_stats``).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import random
import time
from pathlib import Path

import pytest

from uniride_core.algorithms.sota_tsp import ls_engine
from uniride_core.algorithms.sota_tsp.cgo_tsp import CGO_TSP, CGOConfig
from uniride_core.algorithms.sota_tsp.e2bso_tsp import (
    E2BSO_TSP,
    E2BSO_TSP_CPSO,
    E2BSOCPSPConfig,
    E2BSOTSPConfig,
)
from uniride_core.algorithms.sota_tsp.paoea_tsp import PAOEA_TSP, PAOEAConfig
from uniride_core.algorithms.sota_tsp.r2dma_tsp import R2DMA_TSP, R2DMATSPConfig
from uniride_core.algorithms.sota_tsp.run_tsp import RUN_TSP, RUNConfig

SOTA_DIR = Path(ls_engine.__file__).resolve().parent
SOLVER_FILES = ["e2bso_tsp.py", "r2dma_tsp.py", "paoea_tsp.py", "cgo_tsp.py", "run_tsp.py"]
CLOCK_NAMES = {"monotonic", "perf_counter", "time", "process_time"}

N = 12
MAX_ITER = 4

SOLVERS = [
    ("E2BSO", E2BSO_TSP, E2BSOTSPConfig, {"population_size": 6}),
    ("E2BSO-CPSO", E2BSO_TSP_CPSO, E2BSOCPSPConfig, {"population_size": 6}),
    ("R2DMA", R2DMA_TSP, R2DMATSPConfig, {"population_size": 6, "tournament_k": 2}),
    ("P-AOEA", PAOEA_TSP, PAOEAConfig, {"population_size": 6, "genome_population_size": 2}),
    ("CGO", CGO_TSP, CGOConfig, {"population_size": 6}),
    ("RUN", RUN_TSP, RUNConfig, {"population_size": 6}),
]
IDS = [row[0] for row in SOLVERS]


def _matrix(n: int = N, seed: int = 11) -> list:
    rng = random.Random(seed)
    pts = [(rng.random() * 100, rng.random() * 100) for _ in range(n)]
    return [
        [0 if i == j else round(((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2) ** 0.5)
         for j in range(n)]
        for i in range(n)
    ]


def _config(config_type, extra, **overrides):
    values = {"max_iterations": MAX_ITER, "seed": 7}
    values.update(extra)
    values.update(overrides)
    return config_type(**values)


class _FakeClock:
    """Advances ``step`` seconds on every call, whatever the real time is."""

    def __init__(self, step: float = 10.0):
        self.now = 0.0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


def _install_fake_clock(monkeypatch, step: float = 10.0) -> _FakeClock:
    clock = _FakeClock(step)
    monkeypatch.setattr(time, "monotonic", clock)
    monkeypatch.setattr(time, "perf_counter", clock)
    return clock


def _solve(solver_type, config):
    return solver_type(config).solve_with_matrix(_matrix())


def _signature(result):
    return (list(result.tour), float(result.tour_length), list(result.history or []), result.iterations)


# (1) same seed + config -> same result, whatever the clock does ----------------------------


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), SOLVERS, ids=IDS)
def test_result_does_not_depend_on_the_clock(monkeypatch, name, solver_type, config_type, extra):
    config = _config(config_type, extra)

    real = _signature(_solve(solver_type, config))
    again = _signature(_solve(solver_type, config))
    _install_fake_clock(monkeypatch, step=10.0)
    fake = _signature(_solve(solver_type, config))

    assert real == again
    assert fake == real


def test_multilayer_ls_does_not_depend_on_the_clock(monkeypatch):
    matrix = _matrix()
    tour = list(range(N))
    random.Random(3).shuffle(tour)

    real = ls_engine.MultiLayerLS.improve(tour, matrix, None, "full", 50)
    _install_fake_clock(monkeypatch, step=10.0)
    fake = ls_engine.MultiLayerLS.improve(tour, matrix, None, "full", 50)

    assert fake[0] == real[0]
    assert fake[1] == real[1]
    assert real[1] < ls_engine._tour_cost(tour, matrix)  # it did improve a shuffled tour


def test_multilayer_ls_has_no_time_limit_parameter():
    assert "time_limit" not in inspect.signature(ls_engine.MultiLayerLS.improve).parameters


# (2) the optional deadline ------------------------------------------------------------------


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), SOLVERS, ids=IDS)
def test_configs_have_deadline_and_no_old_clock_fields(name, solver_type, config_type, extra):
    by_name = {f.name: f for f in dataclasses.fields(config_type)}
    assert "deadline_seconds" in by_name
    assert by_name["deadline_seconds"].default is None
    assert "time_limit" not in by_name
    assert "ls_time_limit" not in by_name


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), SOLVERS, ids=IDS)
def test_no_deadline_reports_iteration_limit_and_reproducible(name, solver_type, config_type, extra):
    result = _solve(solver_type, _config(config_type, extra))
    assert result.extra_stats["termination_reason"] == "iteration_limit"
    assert result.extra_stats["reproducible"] is True


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), SOLVERS, ids=IDS)
def test_deadline_that_is_not_reached_changes_nothing(name, solver_type, config_type, extra):
    plain = _solve(solver_type, _config(config_type, extra))
    roomy = _solve(solver_type, _config(config_type, extra, deadline_seconds=1.0e9))

    assert _signature(roomy) == _signature(plain)
    assert roomy.extra_stats["termination_reason"] == "iteration_limit"
    assert roomy.extra_stats["reproducible"] is True


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), SOLVERS, ids=IDS)
def test_deadline_that_is_hit_is_reported_and_marks_result_non_reproducible(
    monkeypatch, name, solver_type, config_type, extra
):
    config = _config(config_type, extra, max_iterations=50, deadline_seconds=5.0)
    _install_fake_clock(monkeypatch, step=10.0)

    result = _solve(solver_type, config)

    assert result.extra_stats["termination_reason"] == "wall_clock_deadline"
    assert result.extra_stats["reproducible"] is False
    assert result.iterations < 50
    assert sorted(result.tour) == list(range(N))


@pytest.mark.parametrize(("name", "solver_type", "config_type", "extra"), [r for r in SOLVERS if r[0] in {"E2BSO", "E2BSO-CPSO", "R2DMA", "P-AOEA"}], ids=lambda v: v if isinstance(v, str) else None)
def test_final_polish_still_runs_after_the_deadline_is_hit(
    monkeypatch, name, solver_type, config_type, extra
):
    """No time-derived final_ls_budget: the polish runs with its iteration limit."""
    calls = []
    real_improve = ls_engine.MultiLayerLS.improve

    def spy(tour, dm, dm_np=None, intensity="full", max_iterations=1000, three_opt_window=12):
        calls.append((intensity, max_iterations))
        return real_improve(tour, dm, dm_np, intensity, max_iterations, three_opt_window)

    monkeypatch.setattr(ls_engine.MultiLayerLS, "improve", staticmethod(spy))
    _install_fake_clock(monkeypatch, step=10.0)

    _solve(solver_type, _config(config_type, extra, max_iterations=50, deadline_seconds=5.0))

    assert ("full", 500) in calls


# (3) no clock comparison outside the deadline helper ---------------------------------------


def _clock_calls_in(node: ast.AST):
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "time"
            and sub.func.attr in CLOCK_NAMES
        ):
            yield sub


@pytest.mark.parametrize("filename", SOLVER_FILES + ["ls_engine.py"])
def test_no_clock_comparison_outside_the_deadline_helper(filename):
    tree = ast.parse((SOTA_DIR / filename).read_text(encoding="utf-8"))
    offenders = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Compare) and list(_clock_calls_in(node))
    ]
    assert offenders == [], f"{filename}: clock compared at lines {offenders}"


@pytest.mark.parametrize("filename", SOLVER_FILES + ["ls_engine.py"])
def test_old_time_limit_names_are_gone(filename):
    tree = ast.parse((SOTA_DIR / filename).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.add(node.arg)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    assert not names & {"time_limit", "ls_time_limit", "final_ls_budget"}


def test_deadline_helper_is_the_only_module_that_compares_the_clock():
    helper = SOTA_DIR / "deadline.py"
    assert helper.exists()
    tree = ast.parse(helper.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Compare) for node in ast.walk(tree))
