"""GWO/HHO explore-to-exploit schedule follows the budget in fixed-budget runs.

Owner decision 2026-10-22 (DECISION_LOG A17). In FIXED-BUDGET mode (a finite
objective-evaluation limit) GWO's ``a`` and HHO's escape-energy factor decay
with the share of the budget spent, ``decay = 1 - (used - start) / (limit - start)``
(``start`` is 0 for a solver that owns its counter), so every instance and
budget gets the full arc from the start value to 0. NATIVE runs (no limit) keep
the iteration schedule ``1 - it / max_iterations``; ``max_iterations`` only stops
a fixed-mode run.

Observation point: the solvers' ``_schedule_decay(iteration, start_used)`` hook,
called once per iteration before the iteration spends anything; the tests wrap it
to record the shared counter at that moment. GWO's ``a`` and HHO's escape
energy ``E`` are then checked against the hook value they were built from.

Native behaviour is pinned by ``golden/gwo_hho_native_pre_schedule.json``,
captured from the code BEFORE this change (WIP c49b4bbf).
"""

import json
from pathlib import Path

import pytest

from gwo_hho_schedule_cases import (
    GWO_FIXED_ACCOUNTING_CASES,
    NATIVE_CASES,
    SOLVERS,
    asym_matrix,
    run_case,
    swarm_params,
    sym_matrix,
)
from uniride_core.algorithms.composition import run_composition, swarm_global_stage, three_opt_polish_stage
from uniride_core.algorithms.objective_budget import ObjectiveEvaluationBudget

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "gwo_hho_native_pre_schedule.json").read_text(
        encoding="utf-8"
    )
)
N = 8
# 2-opt candidate tours per scan on 8 nodes: 8 * 7 / 2
PAIRS = N * (N - 1) // 2


class _Spy:
    """Wrap ``_schedule_decay`` on a solver class; record (it, used, start, value)."""

    def __init__(self, monkeypatch, cls):
        self.records = []
        original = cls._schedule_decay
        spy = self

        def wrapped(solver, iteration, start_used):
            value = original(solver, iteration, start_used)
            spy.records.append(
                {
                    "it": iteration,
                    "used": solver._objective_budget.used,
                    "start": start_used,
                    "limit": solver._objective_budget.limit,
                    "value": value,
                }
            )
            return value

        monkeypatch.setattr(cls, "_schedule_decay", wrapped)


def _phase_ub(algorithm, params):
    if algorithm == "GWO":
        return params["pack_size"] - 3
    return params["hawks"] * (params["dive_count"] + 2)


def _fixed(algorithm, kind, budget, max_iterations, **extra):
    params = swarm_params(
        algorithm, evaluation_budget=budget, max_iterations=max_iterations, **extra
    )
    return params


FIXED_CASES = [
    # (algorithm, matrix kind, memetic?, budget)
    ("GWO", "sym", False, 100),
    ("GWO", "asym", False, 157),
    ("GWO", "sym", True, 900),
    ("GWO", "asym", True, 1100),
    ("HHO", "sym", False, 600),
    ("HHO", "asym", False, 777),
    ("HHO", "sym", True, 1500),
    ("HHO", "asym", True, 1900),
]


def _case_id(case):
    algorithm, kind, memetic, budget = case
    return f"{algorithm}-{kind}-{'memetic' if memetic else 'pure'}-B{budget}"


# ---- fixed mode: the schedule is the budget share -------------------------

@pytest.mark.parametrize("case", FIXED_CASES, ids=_case_id)
def test_fixed_schedule_equals_one_minus_budget_share(monkeypatch, case):
    algorithm, kind, memetic, budget = case
    spy = _Spy(monkeypatch, SOLVERS[algorithm])
    params = _fixed(algorithm, kind, budget, 5000, polish_enabled=memetic)
    result = run_case(algorithm, kind, **params)

    assert spy.records, "the hook must be called once per iteration"
    assert len(spy.records) >= result["iterations"]
    for rec in spy.records:
        assert rec["limit"] == budget
        assert rec["start"] == 0
        assert rec["value"] == pytest.approx(1.0 - rec["used"] / budget, abs=1e-12)
    values = [rec["value"] for rec in spy.records]
    assert all(0.0 <= v <= 1.0 for v in values)
    assert values == sorted(values, reverse=True), "the arc only decays"
    assert result["budget_terminated"] is True, "max_iterations must not be what stopped the run"


@pytest.mark.parametrize("case", FIXED_CASES, ids=_case_id)
def test_fixed_arc_reaches_zero_within_one_atomic_phase_of_the_budget_end(monkeypatch, case):
    algorithm, kind, memetic, budget = case
    spy = _Spy(monkeypatch, SOLVERS[algorithm])
    params = _fixed(algorithm, kind, budget, 5000, polish_enabled=memetic)
    run_case(algorithm, kind, **params)

    # The last iteration started with room for one atomic phase, and the next one
    # did not fit: the arc is within (two phases + one periodic polish) of zero.
    polish_ub = params["polish_iters"] * PAIRS if memetic else 0
    slack = (2 * _phase_ub(algorithm, params) + polish_ub) / budget
    assert spy.records[-1]["value"] <= slack
    # The arc starts at the share left after initialization (memetic: the counted
    # initial polish is a large part of a small budget), never at 0.
    first = spy.records[0]["value"]
    assert 0.3 < first < 1.0 if memetic else first > 0.9


@pytest.mark.parametrize("algorithm", ["GWO", "HHO"])
@pytest.mark.parametrize("budget", [150, 480])
def test_fixed_arc_does_not_depend_on_max_iterations(monkeypatch, algorithm, budget):
    arcs = []
    for max_iterations in (2_000, 9_000):
        spy = _Spy(monkeypatch, SOLVERS[algorithm])
        params = _fixed(algorithm, "sym", budget, max_iterations, polish_enabled=False)
        result = run_case(algorithm, "sym", **params)
        assert result["budget_terminated"] is True
        arcs.append([(r["it"], r["used"], r["value"]) for r in spy.records])
        monkeypatch.undo()
    assert arcs[0] == arcs[1]
    assert arcs[0][-1][2] <= (2 * _phase_ub(algorithm, swarm_params(algorithm))) / budget


def test_two_budgets_give_the_same_arc_over_the_share(monkeypatch):
    shares = []
    for budget in (150, 480):
        spy = _Spy(monkeypatch, SOLVERS["GWO"])
        run_case("GWO", "asym", **_fixed("GWO", "asym", budget, 5000, polish_enabled=False))
        shares.append([round(1.0 - r["value"], 9) for r in spy.records])
        monkeypatch.undo()
    # Both runs span (almost) the whole 0..1 share, the longer one in finer steps.
    for series, budget in zip(shares, (150, 480)):
        assert series[0] == pytest.approx(6 / budget, abs=1e-9)  # after pack_size init evaluations
        assert series[-1] >= 1.0 - 2 * 3 / budget - 1e-9


# ---- GWO a / HHO E are built from the hook value --------------------------

def test_gwo_a_is_initial_a_times_the_budget_decay(monkeypatch):
    spy = _Spy(monkeypatch, SOLVERS["GWO"])
    seen = []
    original = SOLVERS["GWO"]._move_toward_leader

    def record(solver, wolf, leader, a):
        seen.append((a, spy.records[-1]["value"]))
        return original(solver, wolf, leader, a)

    monkeypatch.setattr(SOLVERS["GWO"], "_move_toward_leader", record)
    run_case(
        "GWO", "sym",
        **_fixed("GWO", "sym", 200, 5000, polish_enabled=False, initial_a=2.5),
    )
    assert seen
    for a, decay in seen:
        assert a == pytest.approx(2.5 * decay, abs=1e-12)
    # The late iterations exploit at small |a|, not at the iteration-schedule value.
    assert min(a for a, _ in seen) < 0.3


def test_hho_escape_energy_is_scaled_by_the_budget_decay(monkeypatch):
    spy = _Spy(monkeypatch, SOLVERS["HHO"])
    energies = []
    for name in ("_soft_besiege", "_hard_besiege", "_soft_besiege_with_dives",
                 "_hard_besiege_with_dives"):
        original = getattr(SOLVERS["HHO"], name)

        def record(solver, hawk, prey, energy, _original=original):
            energies.append((abs(energy), spy.records[-1]["value"]))
            return _original(solver, hawk, prey, energy)

        monkeypatch.setattr(SOLVERS["HHO"], name, record)
    run_case(
        "HHO", "sym",
        **_fixed("HHO", "sym", 700, 5000, polish_enabled=False, initial_energy=1.3),
    )
    assert energies
    for magnitude, decay in energies:
        # E = 2 * e0 * decay * initial_energy with |e0| <= 1
        assert magnitude <= 2 * 1.3 * decay + 1e-12
    late = [m for m, d in energies if d < 0.1]
    assert late and max(late) < 0.26 + 1e-12


# ---- memetic: the shared counter including polish ------------------------

@pytest.mark.parametrize("algorithm", ["GWO", "HHO"])
def test_memetic_schedule_counts_polish_evaluations_in_the_arc(monkeypatch, algorithm):
    budget = 1400
    spy = _Spy(monkeypatch, SOLVERS[algorithm])
    params = _fixed(algorithm, "sym", budget, 5000, polish_enabled=True)
    result = run_case(algorithm, "sym", **params)
    pop = params["pack_size"] if algorithm == "GWO" else params["hawks"]
    initial_polish = result["polish_evaluations"]["initial"]
    assert initial_polish > 0
    # First iteration starts after the initial polish: pricing one start tour per
    # individual plus the polish candidates, all on the one counter.
    first = spy.records[0]
    assert first["used"] == pop + initial_polish
    assert first["value"] == pytest.approx(1.0 - (pop + initial_polish) / budget, abs=1e-12)
    # A periodic polish phase moves the arc by exactly what it spent.
    assert result["polish_executed"]["periodic"] >= 1
    jumps = [
        (b["used"] - a["used"], a["value"] - b["value"]) for a, b in zip(spy.records, spy.records[1:])
    ]
    for spent, moved in jumps:
        assert moved == pytest.approx(spent / budget, abs=1e-12)
    assert max(spent for spent, _ in jumps) > _phase_ub(algorithm, params), (
        "a polish phase is inside the arc"
    )


# ---- composite hybrids: the global stage's own cap -----------------------

def _run_composite(algorithm, kind, budget, fraction, max_iterations):
    matrix = sym_matrix() if kind == "sym" else asym_matrix()
    if algorithm == "GWO":
        params = {"pack_size": 6, "max_iterations": max_iterations, "initial_a": 2.0,
                  "exploration_rate": 0.4, "max_no_improvement": 10_000}
    else:
        params = {"hawks": 6, "max_iterations": max_iterations, "initial_energy": 1.0,
                  "jump_probability": 0.5, "max_no_improvement": 10_000,
                  "dive_count": 2, "levy_scale": 0.3}
    return run_composition(
        matrix,
        global_stage=swarm_global_stage(algorithm, matrix, params, seed=7),
        polish_stage=three_opt_polish_stage(
            matrix, {"max_iterations": 3, "first_improvement": False, "window": 6}
        ),
        evaluation_budget=budget,
        global_fraction=fraction,
    ), params


@pytest.mark.parametrize("algorithm", ["GWO", "HHO"])
@pytest.mark.parametrize("kind", ["sym", "asym"])
def test_composite_arc_spans_the_global_stage_cap_not_the_total_budget(
    monkeypatch, algorithm, kind
):
    budget, fraction = 2000, 0.5
    cap = 1000
    spy = _Spy(monkeypatch, SOLVERS[algorithm])
    result, params = _run_composite(algorithm, kind, budget, fraction, 50_000)

    assert result.global_stage.allocated_evaluations == cap
    assert spy.records
    for rec in spy.records:
        assert rec["limit"] == cap
        assert rec["value"] == pytest.approx(1.0 - rec["used"] / cap, abs=1e-12)
    # The arc ends when the global stage ends: near 0 at the stage cap. With the
    # total budget as denominator it would stop at about 1 - cap/budget = 0.5.
    assert spy.records[-1]["value"] <= 2 * _phase_ub(algorithm, params) / cap


def test_composite_arc_does_not_depend_on_max_iterations(monkeypatch):
    arcs = []
    for max_iterations in (30_000, 90_000):
        spy = _Spy(monkeypatch, SOLVERS["GWO"])
        _run_composite("GWO", "sym", 900, 0.4, max_iterations)
        arcs.append([(r["it"], r["used"], r["value"]) for r in spy.records])
        monkeypatch.undo()
    assert arcs[0] == arcs[1]


def test_injected_counter_with_prior_spend_spans_the_remaining_stage_allowance(monkeypatch):
    spy = _Spy(monkeypatch, SOLVERS["GWO"])
    shared = ObjectiveEvaluationBudget(1000, used=50)
    solver = SOLVERS["GWO"](
        **swarm_params("GWO", max_iterations=5000, polish_enabled=False),
        shared_budget=shared, stage_cap=250,
    )
    solver.solve_with_matrix(sym_matrix(), recalculate=False, closed_tsp=True)
    assert spy.records[0]["start"] == 50
    for rec in spy.records:
        assert rec["value"] == pytest.approx(1.0 - (rec["used"] - 50) / (250 - 50), abs=1e-12)
    assert spy.records[-1]["value"] <= 2 * 3 / 200


# ---- native: iteration schedule, bit-for-bit unchanged -------------------

@pytest.mark.parametrize("name", sorted(NATIVE_CASES))
def test_native_runs_match_the_pre_change_golden(name):
    algorithm, kind, overrides = NATIVE_CASES[name]
    assert run_case(algorithm, kind, **swarm_params(algorithm, **overrides)) == GOLDEN["native"][name]


@pytest.mark.parametrize("algorithm", ["GWO", "HHO"])
@pytest.mark.parametrize("overrides", [{}, {"count_polish": True}, {"polish_enabled": False}])
def test_native_schedule_is_the_iteration_schedule(monkeypatch, algorithm, overrides):
    spy = _Spy(monkeypatch, SOLVERS[algorithm])
    params = swarm_params(algorithm, max_iterations=23, **overrides)
    run_case(algorithm, "sym", **params)
    assert spy.records
    for rec in spy.records:
        assert rec["limit"] is None
        assert rec["value"] == 1.0 - rec["it"] / 23


# ---- accounting is unchanged ---------------------------------------------

@pytest.mark.parametrize("name", sorted(GWO_FIXED_ACCOUNTING_CASES))
def test_pure_gwo_fixed_accounting_matches_the_pre_change_golden(name):
    kind, overrides = GWO_FIXED_ACCOUNTING_CASES[name]
    got = run_case("GWO", kind, **swarm_params("GWO", **overrides))
    expected = GOLDEN["gwo_fixed_accounting"][name]
    for key in ("objective_evaluations", "evaluation_budget", "iterations", "budget_terminated"):
        assert got[key] == expected[key], key


@pytest.mark.parametrize("case", FIXED_CASES, ids=_case_id)
def test_fixed_accounting_invariants(case):
    algorithm, kind, memetic, budget = case
    params = _fixed(algorithm, kind, budget, 5000, polish_enabled=memetic)
    result = run_case(algorithm, kind, **params)
    assert result["evaluation_budget"] == budget
    assert 0 < result["objective_evaluations"] <= budget
    assert result["budget_terminated"] is True
    if memetic:
        assert result["polish_evaluations"] is not None
        assert sum(result["polish_evaluations"].values()) <= result["objective_evaluations"]
        assert result["polish_executed"]["initial"] == (
            params["pack_size"] if algorithm == "GWO" else params["hawks"]
        )
    else:
        assert result["polish_executed"] == {"initial": 0, "periodic": 0, "final": 0}


def test_pure_gwo_fixed_evaluations_are_pack_plus_phases():
    got = run_case("GWO", "sym", **swarm_params(
        "GWO", polish_enabled=False, evaluation_budget=100, max_iterations=500))
    assert got["objective_evaluations"] == 6 + got["iterations"] * 3
