"""C-06: two-stage composition engine (pure global stage + one polish stage).

Design rules under test: ACADEMIC_STUDY_UNIFICATION_DESIGN.md composition rules
1-9 and the native-termination variant. Accounting identity: one shared counter,
global stage capped at ``floor(B * global_fraction)``, polish gets the rest, the
polish stage reuses the cost the global stage already counted.
"""

from __future__ import annotations

import random

import pytest

from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    StageCappedBudget,
    improve_three_opt_budgeted,
)
from uniride_core.algorithms.three_opt import closed_tour_cost
from uniride_core.algorithms.composition import (
    SMOKE_GLOBAL_FRACTION,
    CompositionError,
    GlobalStageResult,
    PolishStageResult,
    StageSpec,
    resolve_global_fraction,
    run_composition,
    swarm_global_stage,
    three_opt_polish_stage,
)


def _sym(n: int, seed: int):
    rng = random.Random(seed)
    pts = [(rng.uniform(0, 50), rng.uniform(0, 50)) for _ in range(n)]
    return [
        [((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in pts] for a in pts
    ]


def _asym(n: int, seed: int):
    rng = random.Random(seed)
    return [[0 if i == j else rng.randint(1, 40) for j in range(n)] for i in range(n)]


SYM9 = _sym(9, 3)
ASYM7 = _asym(7, 11)
THREE_OPT_PARAMS = {"max_iterations": 5, "first_improvement": False, "window": 12}


# ---- stubs ---------------------------------------------------------------

def _view(shared, cap):
    if shared is None:
        return ObjectiveEvaluationBudget(None)
    return StageCappedBudget(shared, cap)


def stub_global(matrix, k, tour=None, *, reason_when_done="max_iterations",
                report_evaluations=None):
    """Global stage: one counted initial tour, then ONE atomic phase of ``k`` units."""
    tour = list(range(len(matrix))) if tour is None else list(tour)

    def run(shared, cap):
        view = _view(shared, cap)
        start = view.used
        cost = view.evaluate(tour, matrix)
        reason, ceiling = reason_when_done, False
        if view.can_spend(k):
            view.consume(k)
        else:
            reason, ceiling = "evaluation_budget_exhausted", True
        spent = view.used - start
        return GlobalStageResult(
            tour=tour,
            cost=cost,
            iterations=1,
            evaluations=spent if report_evaluations is None else report_evaluations,
            termination_reason=reason,
            stage_ceiling_reached=ceiling,
        )

    return StageSpec("Stub-Global", run, {"k": k}, seed=42)


def stub_polish(tour_fn=None, cost_fn=None, *, drain=False, raises=None,
                reason="no_improving_move", matrix=None):
    def run(tour, cost, budget):
        if raises is not None:
            raise raises
        start = budget.used
        if drain and budget.remaining:
            budget.consume(budget.remaining)
        out_tour = list(tour) if tour_fn is None else tour_fn(list(tour))
        out_cost = cost if cost_fn is None else cost_fn(cost)
        return PolishStageResult(
            tour=out_tour,
            cost=out_cost,
            iterations=0,
            evaluations=budget.used - start,
            termination_reason=reason,
        )

    return StageSpec("Stub-Polish", run, {}, seed=None)


# ---- moved 3-opt ---------------------------------------------------------

@pytest.mark.parametrize(
    "matrix,kwargs,expected",
    [
        # Golden values recorded from the pre-move academic_benchmark.fairness
        # implementation (WIP d1c610ee): the move without initial_cost is
        # behaviour-identical.
        (SYM9, dict(max_iterations=5, first_improvement=False, window=12),
         ([0, 4, 2, 7, 6, 5, 8, 1, 3], 152.36761615956553, 4, 841,
          "no_improving_move", "symmetric_tsp")),
        (SYM9, dict(max_iterations=5, first_improvement=True, window=4),
         ([0, 3, 4, 1, 8, 2, 7, 6, 5], 198.54796719210134, 5, 15,
          "max_iterations", "symmetric_tsp")),
        (ASYM7, dict(max_iterations=5, first_improvement=False, window=12),
         ([0, 1, 2, 4, 5, 3, 6], 97.0, 3, 22,
          "no_improving_move", "directed_atsp")),
    ],
)
def test_moved_three_opt_without_initial_cost_is_behaviour_identical(
    matrix, kwargs, expected
):
    budget = ObjectiveEvaluationBudget(2000)
    res = improve_three_opt_budgeted(list(range(len(matrix))), matrix, budget, **kwargs)
    route, cost, iterations, evaluations, reason, mode = expected
    assert res.route == route
    assert res.cost == cost
    assert res.iterations == iterations
    assert res.evaluations == evaluations == budget.used
    assert res.termination_reason == reason
    assert res.mode == mode


def test_moved_three_opt_budget_cut_is_identical():
    res = improve_three_opt_budgeted(
        list(range(9)), SYM9, ObjectiveEvaluationBudget(40), max_iterations=5
    )
    assert res.route == [0, 8, 1, 2, 7, 6, 5, 4, 3]
    assert res.cost == 195.13907259592978
    assert (res.iterations, res.evaluations) == (1, 40)
    assert res.termination_reason == "evaluation_budget_exhausted"


@pytest.mark.parametrize("matrix", [SYM9, ASYM7])
def test_initial_cost_skips_the_incoming_tour_evaluation(matrix):
    n = len(matrix)
    start = list(range(n))
    known = closed_tour_cost(start, matrix)
    counted = ObjectiveEvaluationBudget(5000)
    plain = improve_three_opt_budgeted(start, matrix, counted, max_iterations=5)
    reused_budget = ObjectiveEvaluationBudget(5000)
    reused = improve_three_opt_budgeted(
        start, matrix, reused_budget, max_iterations=5, initial_cost=known
    )
    assert (reused.route, reused.cost, reused.iterations) == (
        plain.route, plain.cost, plain.iterations
    )
    assert reused.evaluations == plain.evaluations - 1
    assert reused_budget.used == counted.used - 1


# ---- global fraction -----------------------------------------------------

def test_smoke_default_is_explicit_and_paper_scale_has_no_default():
    assert SMOKE_GLOBAL_FRACTION == 0.80
    assert resolve_global_fraction(None, smoke_default=True) == 0.80
    with pytest.raises(CompositionError, match="global_fraction"):
        resolve_global_fraction(None, smoke_default=False)
    assert resolve_global_fraction(0.6, smoke_default=True) == 0.6


@pytest.mark.parametrize("bad", [0, 0.0, 1, 1.0, -0.1, 1.5, True, "0.8", float("nan")])
def test_global_fraction_must_be_strictly_between_zero_and_one(bad):
    with pytest.raises(CompositionError, match="global_fraction"):
        resolve_global_fraction(bad, smoke_default=False)


def test_global_cap_is_an_exact_floor_without_float_noise():
    # 100 * 0.29 == 28.999999999999996 in binary floating point: the cap is 29.
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 1),
        polish_stage=stub_polish(),
        evaluation_budget=100,
        global_fraction=0.29,
    )
    assert result.global_stage.allocated_evaluations == 29
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 1),
        polish_stage=stub_polish(),
        evaluation_budget=35,
        global_fraction=0.8,
        smoke_default_fraction=False,
    )
    assert result.global_stage.allocated_evaluations == 28


def test_missing_global_fraction_is_refused_unless_smoke_default_requested():
    with pytest.raises(CompositionError, match="global_fraction"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 1), polish_stage=stub_polish(),
            evaluation_budget=100,
        )
    result = run_composition(
        SYM9, global_stage=stub_global(SYM9, 1), polish_stage=stub_polish(),
        evaluation_budget=100, smoke_default_fraction=True,
    )
    assert result.global_fraction == 0.80
    assert result.global_stage.allocated_evaluations == 80


# ---- boundary triplet ----------------------------------------------------

B, FRACTION = 100, 0.5  # global cap 50; the initial tour uses 1, so 49 remain


@pytest.mark.parametrize(
    "k,refused",
    [(50, True), (49, False), (48, False)],  # remaining is k-1, k, k+1
)
def test_atomic_phase_boundary_triplet(k, refused):
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, k),
        polish_stage=stub_polish(drain=True),
        evaluation_budget=B,
        global_fraction=FRACTION,
    )
    g = result.global_stage
    assert g.allocated_evaluations == 50
    if refused:
        # remaining k-1: the phase is refused whole, only the initial tour counted
        assert g.consumed_evaluations == 1
        assert g.termination_reason == "evaluation_budget_exhausted"
        assert g.details["stage_ceiling_reached"] is True
    else:
        assert g.consumed_evaluations == 1 + k
        assert g.termination_reason == "max_iterations"
        assert g.details["stage_ceiling_reached"] is False
    # the stage ceiling is never exceeded, and polish drains exactly the rest,
    # so the run total lands on B (the total from the shared counter)
    assert g.consumed_evaluations <= 50
    assert result.polish_stage.allocated_evaluations == B - g.consumed_evaluations
    assert result.polish_stage.consumed_evaluations == B - g.consumed_evaluations
    assert result.evaluations == B


# ---- polish stage --------------------------------------------------------

def test_polish_with_zero_remaining_returns_global_tour_and_spends_nothing():
    # floor(B * fraction) < B, so the engine always leaves the polish stage at
    # least one unit; a polish stage handed an exhausted view is exercised directly.
    tour = list(range(9))
    cost = closed_tour_cost(tour, SYM9)
    exhausted = StageCappedBudget(ObjectiveEvaluationBudget(10, used=10), None)
    out = three_opt_polish_stage(SYM9, THREE_OPT_PARAMS).run(tour, cost, exhausted)
    assert out.tour == tour
    assert out.cost == cost
    assert out.evaluations == 0
    assert out.termination_reason == "evaluation_budget_exhausted"
    assert exhausted.used == 10


def test_polish_with_the_minimum_allocation_is_cut_by_the_total_budget():
    # B=2, cap=1: the initial tour uses the one global unit, polish gets 1.
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 0),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
        evaluation_budget=2,
        global_fraction=0.5,
    )
    assert result.global_stage.consumed_evaluations == 1
    assert result.polish_stage.allocated_evaluations == 1
    assert result.polish_stage.consumed_evaluations == 1
    assert result.termination_reason == "evaluation_budget_exhausted"
    assert result.evaluations == 2


def test_unchanged_polish_is_reported_as_unchanged():
    result = run_composition(
        SYM9, global_stage=stub_global(SYM9, 1),
        polish_stage=stub_polish(), evaluation_budget=100, global_fraction=0.5,
    )
    assert result.polish_changed_tour is False
    assert result.tour == list(range(9))


def test_polish_does_not_recount_the_incoming_tour():
    tour = list(range(9))
    expected = improve_three_opt_budgeted(
        tour, SYM9, ObjectiveEvaluationBudget(100000), max_iterations=5,
        initial_cost=closed_tour_cost(tour, SYM9),
    )
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 0 + 1, tour),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
        evaluation_budget=100000,
        global_fraction=0.5,
    )
    assert result.polish_stage.consumed_evaluations == expected.evaluations
    assert result.evaluations == (
        result.global_stage.consumed_evaluations + expected.evaluations
    )
    assert result.tour == expected.route
    assert result.polish_changed_tour is True


def test_polish_exception_fails_the_run_instead_of_returning_unpolished():
    with pytest.raises(CompositionError, match="polish"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 1),
            polish_stage=stub_polish(raises=RuntimeError("boom")),
            evaluation_budget=100, global_fraction=0.5,
        )


@pytest.mark.parametrize(
    "tour_fn",
    [
        lambda t: t[:-1],                 # a node missing
        lambda t: t + [t[0]],             # duplicated closing node
        lambda t: [t[0]] * len(t),        # not a permutation
        lambda t: t[:-1] + [len(t)],      # foreign node
    ],
)
def test_invalid_polish_tour_fails_the_run(tour_fn):
    with pytest.raises(CompositionError, match="polish"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 1),
            polish_stage=stub_polish(tour_fn=tour_fn),
            evaluation_budget=100, global_fraction=0.5,
        )


def test_polish_cost_that_disagrees_with_its_tour_fails_the_run():
    with pytest.raises(CompositionError, match="polish"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 1),
            polish_stage=stub_polish(cost_fn=lambda c: c - 5.0),
            evaluation_budget=100, global_fraction=0.5,
        )


def test_directed_atsp_costs_survive_the_polish_stage():
    start = [0, 6, 5, 4, 3, 2, 1]
    result = run_composition(
        ASYM7,
        global_stage=stub_global(ASYM7, 1, start),
        polish_stage=three_opt_polish_stage(ASYM7, THREE_OPT_PARAMS),
        evaluation_budget=5000,
        global_fraction=0.5,
    )
    assert result.polish_changed_tour is True
    # independent directed closed-cycle cost (arc i -> i+1, last -> first)
    independent = sum(
        ASYM7[result.tour[i]][result.tour[(i + 1) % 7]] for i in range(7)
    )
    assert result.cost == independent
    assert sorted(result.tour) == list(range(7))
    assert result.cost < closed_tour_cost(start, ASYM7)
    assert result.polish_stage.details["mode"] == "directed_atsp"


# ---- global stage --------------------------------------------------------

def test_global_exception_fails_the_composition():
    def boom(shared, cap):
        raise ValueError("fair GWO budget cannot complete atomic population initialization")

    with pytest.raises(CompositionError, match="global"):
        run_composition(
            SYM9, global_stage=StageSpec("Boom", boom, {}, seed=1),
            polish_stage=stub_polish(), evaluation_budget=100, global_fraction=0.5,
        )


def test_invalid_global_tour_fails_the_composition():
    bad = stub_global(SYM9, 1, tour=[0, 1, 2, 3, 4, 5, 6, 7, 7])
    with pytest.raises(CompositionError, match="global"):
        run_composition(
            SYM9, global_stage=bad, polish_stage=stub_polish(),
            evaluation_budget=100, global_fraction=0.5,
        )


def test_global_stage_that_underreports_its_spend_is_refused():
    # the total comes from the shared counter; a stage report that disagrees with
    # it is an accounting error, not something to sum
    under = stub_global(SYM9, 5, report_evaluations=2)
    with pytest.raises(CompositionError, match="account"):
        run_composition(
            SYM9, global_stage=under, polish_stage=stub_polish(),
            evaluation_budget=100, global_fraction=0.5,
        )


def test_run_total_is_the_shared_counter_not_stage_reports():
    result = run_composition(
        SYM9, global_stage=stub_global(SYM9, 7),
        polish_stage=stub_polish(drain=True),
        evaluation_budget=64, global_fraction=0.5,
    )
    assert result.evaluations == 64
    assert (
        result.global_stage.consumed_evaluations
        + result.polish_stage.consumed_evaluations
        == result.evaluations
    )


def test_global_stage_cannot_hide_a_polish_namespace():
    with pytest.raises(CompositionError, match="polish"):
        swarm_global_stage(
            "GWO", SYM9,
            {"pack_size": 6, "max_iterations": 3, "initial_a": 2.0,
             "exploration_rate": 0.4, "max_no_improvement": 5, "polish_iters": 10},
            seed=7,
        )


def test_strict_manifests_refuse_implicit_hyperparameters():
    with pytest.raises(CompositionError, match="explicit"):
        swarm_global_stage("GWO", SYM9, {"pack_size": 6}, seed=7)
    with pytest.raises(CompositionError, match="explicit"):
        three_opt_polish_stage(SYM9, {"max_iterations": 5})


# ---- recorded identity ---------------------------------------------------

def test_result_records_stage_identity_parameters_seeds_and_budgets():
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 20),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
        evaluation_budget=1000,
        global_fraction=0.5,
    )
    g, p = result.global_stage, result.polish_stage
    assert (g.name, g.stage_id) == ("global", "Stub-Global")
    assert g.parameters == {"k": 20}
    assert g.seed == 42
    assert g.allocated_evaluations == 500
    assert g.consumed_evaluations == 21
    assert (p.name, p.stage_id) == ("polish", "Core-ThreeOpt-TSP")
    assert p.parameters == THREE_OPT_PARAMS
    assert p.seed is None  # deterministic 3-opt records no secondary seed
    assert p.allocated_evaluations == 1000 - 21
    assert p.termination_reason in {"no_improving_move", "max_iterations"}
    assert result.mode == "fixed_budget"
    assert result.evaluation_budget == 1000
    assert result.global_fraction == 0.5
    assert result.evaluations == g.consumed_evaluations + p.consumed_evaluations
    as_dict = result.to_dict()
    assert as_dict["polish_changed_tour"] is result.polish_changed_tour
    assert [s["name"] for s in as_dict["stages"]] == ["global", "polish"]


# ---- native mode ---------------------------------------------------------

def test_native_mode_has_no_cap_and_sums_stage_counts():
    result = run_composition(
        SYM9,
        global_stage=stub_global(SYM9, 200),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
    )
    assert result.mode == "native"
    assert result.evaluation_budget is None
    assert result.global_fraction is None
    assert result.global_stage.allocated_evaluations is None
    assert result.polish_stage.allocated_evaluations is None
    assert result.global_stage.consumed_evaluations == 201
    assert result.polish_stage.consumed_evaluations > 0
    assert result.evaluations == (
        result.global_stage.consumed_evaluations
        + result.polish_stage.consumed_evaluations
    )


def test_native_composite_complete_only_when_both_stages_complete():
    both = run_composition(
        SYM9, global_stage=stub_global(SYM9, 3),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
    )
    assert both.termination_reason == "composite_complete"
    assert both.global_stage.termination_reason == "max_iterations"
    assert both.polish_stage.termination_reason in {"no_improving_move", "max_iterations"}
    # a global stage that did not complete natively fails the composite
    with pytest.raises(CompositionError, match="complete"):
        run_composition(
            SYM9,
            global_stage=stub_global(SYM9, 3, reason_when_done="evaluation_budget_exhausted"),
            polish_stage=stub_polish(),
        )
    with pytest.raises(CompositionError, match="complete"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 3),
            polish_stage=stub_polish(reason="evaluation_budget_exhausted"),
        )


def test_native_mode_rejects_a_global_fraction():
    with pytest.raises(CompositionError, match="global_fraction"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 3), polish_stage=stub_polish(),
            global_fraction=0.5,
        )


# ---- real swarm stage ----------------------------------------------------

GWO_PARAMS = {"pack_size": 6, "max_iterations": 4, "initial_a": 2.0,
              "exploration_rate": 0.4, "max_no_improvement": 10}
HHO_PARAMS = {"hawks": 6, "max_iterations": 4, "initial_energy": 1.0,
              "jump_probability": 0.5, "max_no_improvement": 10, "dive_count": 3,
              "levy_scale": 0.3}


@pytest.mark.parametrize(
    "algorithm,params", [("GWO", GWO_PARAMS), ("HHO", HHO_PARAMS)]
)
def test_pure_swarm_then_three_opt_fixed_budget(algorithm, params):
    def go():
        return run_composition(
            SYM9,
            global_stage=swarm_global_stage(algorithm, SYM9, params, seed=11),
            polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
            evaluation_budget=600,
            global_fraction=0.5,
        )

    first, second = go(), go()
    g, p = first.global_stage, first.polish_stage
    assert g.consumed_evaluations <= 300
    assert first.evaluations <= 600
    assert first.evaluations == g.consumed_evaluations + p.consumed_evaluations
    assert sorted(first.tour) == list(range(9))
    assert first.cost == pytest.approx(closed_tour_cost(first.tour, SYM9))
    assert first.cost <= g.details["cost"] + 1e-9
    # no hidden polish inside the global stage
    assert g.details["polish_executed"] == {"initial": 0, "periodic": 0, "final": 0}
    assert g.seed == 11 and p.seed is None
    # deterministic replay
    assert (first.tour, first.cost, first.evaluations) == (
        second.tour, second.cost, second.evaluations
    )


def test_pure_swarm_native_run_sums_separate_stage_counts():
    result = run_composition(
        SYM9,
        global_stage=swarm_global_stage("GWO", SYM9, GWO_PARAMS, seed=5),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
    )
    assert result.termination_reason == "composite_complete"
    assert result.global_stage.termination_reason in {"max_iterations", "stagnation_limit"}
    assert result.evaluations == (
        result.global_stage.consumed_evaluations
        + result.polish_stage.consumed_evaluations
    )


# ---- review round 1 -------------------------------------------------------

from uniride_core.algorithms.composition import global_stage_cap  # noqa: E402


@pytest.mark.parametrize(
    "budget,fraction,expected",
    [
        (10, 0.75, 7),      # 7.5: round() would give 8
        (7, 0.5, 3),        # 3.5: round() would give 4
        (3, 0.99, 2),       # 2.97: round() would give 3
        (100, 0.29, 29),    # binary float product is 28.999999999999996
        (35, 0.8, 28),
        # A repeating fraction is read by its written decimal: 1/3 is
        # 0.3333333333333333, so the product is 9999.99... and the cap 9999,
        # where float arithmetic (30000 * (1/3) == 10000.0) would say 10000.
        (30000, 1 / 3, 9999),
    ],
)
def test_global_stage_cap_is_a_floor_of_the_written_decimal(budget, fraction, expected):
    assert global_stage_cap(budget, fraction) == expected


@pytest.mark.parametrize("budget,fraction,cap", [(10, 0.75, 7), (7, 0.5, 3)])
def test_engine_allocates_the_floored_cap(budget, fraction, cap):
    result = run_composition(
        SYM9, global_stage=stub_global(SYM9, 0), polish_stage=stub_polish(),
        evaluation_budget=budget, global_fraction=fraction,
    )
    assert result.global_stage.allocated_evaluations == cap
    assert result.global_stage.consumed_evaluations <= cap


@pytest.mark.parametrize("reason", ["time_limit", "no_improvement", "evaluation_budget_exhausted"])
def test_native_reasons_outside_the_validator_vocabulary_are_rejected(reason):
    with pytest.raises(CompositionError, match="complete"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 3, reason_when_done=reason),
            polish_stage=stub_polish(),
        )
    with pytest.raises(CompositionError, match="complete"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 3), polish_stage=stub_polish(reason=reason),
        )


def test_native_polish_that_underreports_its_counter_is_refused():
    def run(tour, cost, budget):
        budget.consume(5)
        return PolishStageResult(
            tour=list(tour), cost=cost, iterations=0, evaluations=2,
            termination_reason="no_improving_move",
        )

    with pytest.raises(CompositionError, match="account"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 3),
            polish_stage=StageSpec("Under", run, {}, seed=None),
        )


def test_aggregate_reason_is_the_polish_reason_and_global_ceiling_stays_in_its_record():
    # global stage refused its atomic phase (ceiling reached); polish ends naturally
    natural = run_composition(
        SYM9, global_stage=stub_global(SYM9, 50),
        polish_stage=stub_polish(reason="max_iterations"),
        evaluation_budget=B, global_fraction=FRACTION,
    )
    assert natural.global_stage.termination_reason == "evaluation_budget_exhausted"
    assert natural.termination_reason == "max_iterations"
    # polish cut by the total budget
    cut = run_composition(
        SYM9, global_stage=stub_global(SYM9, 0),
        polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
        evaluation_budget=2, global_fraction=0.5,
    )
    assert cut.termination_reason == "evaluation_budget_exhausted"
    assert cut.polish_stage.consumed_evaluations == cut.polish_stage.allocated_evaluations


def test_both_stages_must_share_the_composition_matrix():
    other = _sym(9, 4)
    assert other != SYM9 and len(other) == len(SYM9)
    with pytest.raises(CompositionError, match="matrix"):
        run_composition(
            SYM9, global_stage=stub_global(SYM9, 1),
            polish_stage=three_opt_polish_stage(other, THREE_OPT_PARAMS),
            evaluation_budget=100, global_fraction=0.5,
        )
    with pytest.raises(CompositionError, match="matrix"):
        run_composition(
            SYM9, global_stage=swarm_global_stage("GWO", other, GWO_PARAMS, seed=1),
            polish_stage=three_opt_polish_stage(SYM9, THREE_OPT_PARAMS),
            evaluation_budget=100, global_fraction=0.5,
        )
    # an equal copy is the same matrix
    copy = [list(row) for row in SYM9]
    result = run_composition(
        SYM9, global_stage=stub_global(SYM9, 1),
        polish_stage=three_opt_polish_stage(copy, THREE_OPT_PARAMS),
        evaluation_budget=100, global_fraction=0.5,
    )
    assert result.evaluations <= 100


# ---- per-stage wall time (design native rule 4, C-09) --------------------------

def _sleeping(stage: StageSpec, seconds: float) -> StageSpec:
    """The same stage with a known wall-clock cost, so a measured time must be visible."""
    import time as _time

    inner = stage.run

    def run(*args):
        _time.sleep(seconds)
        return inner(*args)

    return StageSpec(stage.stage_id, run, stage.params, seed=stage.seed, matrix=stage.matrix)


@pytest.mark.parametrize("budget,fraction", [(1000, 0.5), (None, None)])
def test_each_stage_record_carries_its_own_non_negative_wall_time(budget, fraction):
    result = run_composition(
        SYM9,
        global_stage=_sleeping(stub_global(SYM9, 20), 0.05),
        polish_stage=_sleeping(three_opt_polish_stage(SYM9, THREE_OPT_PARAMS), 0.12),
        evaluation_budget=budget,
        global_fraction=fraction,
    )
    g, p = result.global_stage, result.polish_stage
    for stage in (g, p):
        assert isinstance(stage.elapsed_sec, float) and stage.elapsed_sec >= 0
    # measured separately: each stage owns the time of its own run and nothing else
    assert 0.045 <= g.elapsed_sec < 0.12
    assert 0.115 <= p.elapsed_sec
    assert [s["elapsed_sec"] for s in result.to_dict()["stages"]] == [g.elapsed_sec, p.elapsed_sec]
