"""C-05: a stage-capped view over one shared objective counter.

Pure GWO/HHO accept an injected ``ObjectiveEvaluationBudget`` plus a stage cap
and must neither reset the shared counter nor spend above the cap. The default
(own counter) behaviour is pinned by the existing evidence tests; the identity
test here guards it as well.
"""

import random

import pytest

from uniride_core.algorithms.objective_budget import (
    EvaluationBudgetExhausted,
    ObjectiveEvaluationBudget,
)
from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import GWOOptimizer
from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import HHOOptimizer


def _coordinates(n: int = 12, seed: int = 7):
    rng = random.Random(seed)
    return [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]


def _stage_view(shared, cap):
    from uniride_core.algorithms.objective_budget import StageCappedBudget

    return StageCappedBudget(shared, cap)


# ---- the view's own semantics -------------------------------------------

def test_view_shares_the_counter_and_respects_cap_and_total():
    shared = ObjectiveEvaluationBudget(100, used=10)
    view = _stage_view(shared, 60)
    assert view.used == 10
    assert view.limit == 60
    assert view.remaining == 50
    assert view.can_spend(50)
    assert not view.can_spend(51)
    view.consume(5)
    assert shared.used == 15  # one shared counter, not a copy
    assert view.used == 15


def test_total_limit_binds_when_below_the_cap():
    shared = ObjectiveEvaluationBudget(30, used=10)
    view = _stage_view(shared, 60)
    assert view.limit == 30
    assert view.can_spend(20)
    assert not view.can_spend(21)


def test_cap_binds_when_below_the_total_limit():
    shared = ObjectiveEvaluationBudget(100, used=10)
    view = _stage_view(shared, 60)
    with pytest.raises(EvaluationBudgetExhausted):
        view.consume(51)
    assert shared.used == 10  # refused before any spend


def test_uncapped_view_over_unlimited_counter_is_unbounded():
    view = _stage_view(ObjectiveEvaluationBudget(None), None)
    assert view.limit is None and view.remaining is None
    assert view.can_spend(10**9)


def test_view_rejects_cap_below_used_and_non_positive_cap():
    with pytest.raises(ValueError):
        _stage_view(ObjectiveEvaluationBudget(100, used=10), 9)
    with pytest.raises(ValueError):
        _stage_view(ObjectiveEvaluationBudget(100), 0)


def test_view_has_no_used_setter():
    view = _stage_view(ObjectiveEvaluationBudget(100, used=10), 60)
    with pytest.raises(AttributeError):
        view.used = 0


# ---- injected counter in pure GWO / HHO ----------------------------------

def _gwo(shared, cap, **overrides):
    params = dict(
        pack_size=10, max_iterations=1000, max_no_improvement=10**6,
        polish_enabled=False, random_seed=5,
        shared_budget=shared, stage_cap=cap,
    )
    params.update(overrides)
    return GWOOptimizer(**params)


def _hho(shared, cap, **overrides):
    params = dict(
        hawks=8, max_iterations=1000, max_no_improvement=10**6,
        polish_enabled=False, random_seed=5,
        shared_budget=shared, stage_cap=cap,
    )
    params.update(overrides)
    return HHOOptimizer(**params)


@pytest.mark.parametrize("factory", [_gwo, _hho])
def test_injected_counter_is_not_reset_and_stage_cap_holds(factory):
    shared = ObjectiveEvaluationBudget(100, used=10)
    result = factory(shared, 60).solve(_coordinates())
    assert 10 < shared.used <= 60
    stats = result.extra_stats
    assert stats["budget_terminated"] is True
    # The stage reports only what it spent; the shared counter keeps the rest.
    assert stats["objective_evaluations"] == shared.used - 10
    assert stats["shared_counter_used"] == shared.used
    assert stats["stage_cap"] == 60
    assert stats["evaluation_budget"] == 60 - 10  # the stage allowance


@pytest.mark.parametrize("factory", [_gwo, _hho])
def test_total_limit_stops_a_stage_whose_cap_is_higher(factory):
    shared = ObjectiveEvaluationBudget(40, used=10)
    factory(shared, 90).solve(_coordinates())
    assert 10 < shared.used <= 40


@pytest.mark.parametrize("factory", [_gwo, _hho])
def test_atomic_initialization_refused_when_cap_is_too_small(factory):
    shared = ObjectiveEvaluationBudget(100, used=10)
    with pytest.raises(ValueError, match="atomic population initialization"):
        factory(shared, 12).solve(_coordinates())
    assert shared.used == 10  # refusal spends nothing


@pytest.mark.parametrize("factory", [_gwo, _hho])
def test_boundary_one_unit_below_the_phase_needs_runs_no_phase(factory):
    # Initialization (pack/hawks units) fits exactly; no iteration phase fits.
    coords = _coordinates()
    shared = ObjectiveEvaluationBudget(100, used=10)
    units = 10 if factory is _gwo else 8
    result = factory(shared, 10 + units).solve(coords)
    assert shared.used == 10 + units
    assert result.iterations == 0
    assert result.extra_stats["budget_terminated"] is True


def test_injection_rejects_a_second_budget_source_and_unbounded_stage():
    shared = ObjectiveEvaluationBudget(100)
    with pytest.raises(ValueError):
        GWOOptimizer(evaluation_budget=50, shared_budget=shared, stage_cap=60)
    with pytest.raises(ValueError):
        HHOOptimizer(evaluation_budget=50, shared_budget=shared, stage_cap=60)
    with pytest.raises(ValueError):
        GWOOptimizer(shared_budget=ObjectiveEvaluationBudget(None), stage_cap=None)
    with pytest.raises(ValueError):
        GWOOptimizer(stage_cap=60)  # a cap without a counter


_PURE = {"polish_enabled": False}
_MEMETIC = {"polish_enabled": True, "polish_iters": 1, "final_polish_iters": 1,
            "polish_interval": 5}


@pytest.mark.parametrize("variant", [_PURE, _MEMETIC], ids=["pure", "memetic"])
@pytest.mark.parametrize(
    "make, size_key",
    [(GWOOptimizer, "pack_size"), (HHOOptimizer, "hawks")],
)
def test_injected_zero_start_counter_matches_the_own_counter(make, size_key, variant):
    coords = _coordinates()
    common = {size_key: 8, "max_iterations": 40, "random_seed": 11, **variant}
    a = make(evaluation_budget=3000, **common).solve(coords)
    shared = ObjectiveEvaluationBudget(3000)
    b = make(shared_budget=shared, stage_cap=3000, **common).solve(coords)
    assert (a.tour, a.tour_length, a.iterations) == (b.tour, b.tour_length, b.iterations)
    assert a.extra_stats["objective_evaluations"] == b.extra_stats["objective_evaluations"]
    assert a.extra_stats["objective_evaluations"] == shared.used
    assert a.extra_stats["polish_evaluations"] == b.extra_stats["polish_evaluations"]
    assert a.extra_stats["execution_backend"] == b.extra_stats["execution_backend"]
    assert a.history == b.history


@pytest.mark.parametrize("factory", [GWOOptimizer, HHOOptimizer])
def test_default_result_has_no_injection_keys(factory):
    result = factory(
        random_seed=3, max_iterations=3, evaluation_budget=5000, polish_enabled=False
    ).solve(_coordinates())
    assert "shared_counter_used" not in result.extra_stats
    assert "stage_cap" not in result.extra_stats


@pytest.mark.parametrize(
    "make, size_key",
    [(GWOOptimizer, "pack_size"), (HHOOptimizer, "hawks")],
)
def test_memetic_polish_is_held_to_the_stage_cap(make, size_key):
    """Polish must spend through the capped view, not the raw shared counter.

    Initialization polish fits the cap (polish_iters=1) but the final polish
    (final_polish_iters=200) would run far past it if it bypassed the view.
    """
    shared = ObjectiveEvaluationBudget(5000, used=10)
    cap = 600
    result = make(
        **{size_key: 6},
        max_iterations=5, max_no_improvement=10**6, random_seed=5,
        polish_enabled=True, polish_iters=1, final_polish_iters=200,
        polish_interval=2, shared_budget=shared, stage_cap=cap,
    ).solve(_coordinates())
    stats = result.extra_stats
    assert 10 < shared.used <= cap  # not reset, held to the cap
    assert stats["objective_evaluations"] == shared.used - 10
    assert sum(stats["polish_evaluations"].values()) <= stats["objective_evaluations"]
    assert stats["polish_evaluations"]["final"] > 0
    assert stats["budget_terminated"] is True  # the final polish hit the cap
