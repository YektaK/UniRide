"""Two-stage composition engine: a pure global stage plus ONE polish stage (C-06).

Implements the composition rules of ``ACADEMIC_STUDY_UNIFICATION_DESIGN.md``
(rules 1-9 and the native-termination variant) for ``GWO/HHO + final polish``:

* the global stage is a pure canonical swarm run (no hidden polish);
* the polish stage runs once, on the global stage's best complete validated
  tour, and reuses the cost the global stage already counted (the incoming tour
  is not re-evaluated; the engine's independent recomputation is the check);
* fixed budget ``B``: one shared counter, global ceiling ``floor(B *
  global_fraction)``, polish may spend the rest, the run total is the shared
  counter and nothing else;
* native mode: no budget and no fraction, each stage keeps its own count, the
  counts are summed for description only, and the aggregate termination is
  ``composite_complete`` only when both stages complete;
* a global failure fails the composition, and so do a polish exception or an
  invalid polish tour.

Changing invocation timing, stage algorithm, transfer semantics, seed derivation
or allocation policy is a new variant (design rule 9 footer), not an edit here.

A stage is a :class:`StageSpec` whose ``run`` callable has a fixed shape so that
a later polish adapter (for example ALNS, C-07) plugs in without touching the
engine:

* global ``run(shared, stage_cap) -> GlobalStageResult``; fixed mode passes the
  one shared :class:`ObjectiveEvaluationBudget` and the absolute stage ceiling,
  native mode passes ``(None, None)`` and the stage counts for itself;
* polish ``run(tour, cost, budget) -> PolishStageResult``; ``budget`` is a
  :class:`StageCappedBudget` over the shared counter (fixed) or a fresh
  unlimited counter (native). Tours are 0-based matrix indices.

This module imports nothing from ``academic_benchmark``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from uniride_core.algorithms.objective_budget import (
    ObjectiveEvaluationBudget,
    StageCappedBudget,
    improve_three_opt_budgeted,
)
from uniride_core.algorithms.three_opt import closed_tour_cost

SMOKE_GLOBAL_FRACTION = 0.80

FIXED_MODE = "fixed_budget"
NATIVE_MODE = "native"
COMPOSITE_COMPLETE = "composite_complete"
EVALUATION_BUDGET_EXHAUSTED = "evaluation_budget_exhausted"

# Native stopping conditions that count as "the stage completed". A native stage
# that ended any other way (budget exhaustion cannot happen without a budget)
# did not complete and fails the composite run.
NATIVE_COMPLETE_REASONS = frozenset({
    "max_iterations", "stagnation_limit", "no_improving_move",
    "no_improvement", "time_limit",
})

_COST_TOLERANCE = 1e-9


class CompositionError(RuntimeError):
    """A composition run failed: a failed stage, an invalid tour or bad accounting."""


@dataclass(frozen=True)
class GlobalStageResult:
    tour: Sequence[int]
    cost: float
    iterations: int
    evaluations: int  # the stage's own spend, cross-checked against the shared counter
    termination_reason: str
    stage_ceiling_reached: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolishStageResult:
    tour: Sequence[int]
    cost: float
    iterations: int
    evaluations: int
    termination_reason: str
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StageSpec:
    """A stage identity plus its callable, parameters (own namespace) and seed."""

    stage_id: str
    run: Callable[..., Any]
    params: Mapping[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None  # None: deterministic stage, no secondary seed


@dataclass(frozen=True)
class StageRecord:
    name: str  # "global" | "polish"
    stage_id: str
    parameters: Dict[str, Any]
    seed: Optional[int]
    allocated_evaluations: Optional[int]  # None in native mode
    consumed_evaluations: int
    termination_reason: str
    iterations: int
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "stage_id": self.stage_id,
            "parameters": dict(self.parameters),
            "seed": self.seed,
            "allocated_evaluations": self.allocated_evaluations,
            "consumed_evaluations": self.consumed_evaluations,
            "termination_reason": self.termination_reason,
            "iterations": self.iterations,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class CompositionResult:
    tour: List[int]
    cost: float
    evaluations: int  # run total: the shared counter (fixed) or the stage sum (native)
    mode: str
    evaluation_budget: Optional[int]
    global_fraction: Optional[float]
    termination_reason: str
    global_stage: StageRecord
    polish_stage: StageRecord
    polish_changed_tour: bool

    @property
    def stages(self) -> Tuple[StageRecord, StageRecord]:
        return (self.global_stage, self.polish_stage)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tour": list(self.tour),
            "cost": self.cost,
            "evaluations": self.evaluations,
            "mode": self.mode,
            "evaluation_budget": self.evaluation_budget,
            "global_fraction": self.global_fraction,
            "termination_reason": self.termination_reason,
            "polish_changed_tour": self.polish_changed_tour,
            "stages": [stage.to_dict() for stage in self.stages],
        }


def resolve_global_fraction(
    global_fraction: Optional[float], *, smoke_default: bool
) -> float:
    """Return an explicit fraction in (0, 1); only smoke runs may default to 0.80."""
    if global_fraction is None:
        if smoke_default:
            return SMOKE_GLOBAL_FRACTION
        raise CompositionError(
            "global_fraction must be given explicitly; the 0.80 default is for "
            "smoke runs only"
        )
    if (
        isinstance(global_fraction, bool)
        or not isinstance(global_fraction, (int, float))
        or not math.isfinite(global_fraction)
        or not 0 < global_fraction < 1
    ):
        raise CompositionError(
            f"global_fraction must be a number strictly between 0 and 1, "
            f"got {global_fraction!r}"
        )
    return float(global_fraction)


def _stage_cap(evaluation_budget: int, fraction: float) -> int:
    # Exact decimal arithmetic: 100 * 0.29 is 28.999999999999996 in binary floats.
    cap = math.floor(Fraction(str(fraction)) * evaluation_budget)
    if cap < 1:
        raise CompositionError(
            f"global stage ceiling floor({evaluation_budget} * {fraction}) is below 1"
        )
    return cap


def _validate_tour(
    tour: Sequence[int], matrix: Sequence[Sequence[float]], cost: float, label: str
) -> List[int]:
    n = len(matrix)
    try:
        nodes = [int(node) for node in tour]
    except (TypeError, ValueError) as exc:
        raise CompositionError(f"{label} tour is not a sequence of nodes") from exc
    if any(isinstance(node, bool) for node in tour):
        raise CompositionError(f"{label} tour contains a boolean node")
    if sorted(nodes) != list(range(n)):
        raise CompositionError(
            f"{label} tour is not a complete permutation of the {n} matrix nodes"
        )
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost):
        raise CompositionError(f"{label} cost is not a finite number")
    independent = closed_tour_cost(nodes, matrix)
    if not math.isclose(cost, independent, rel_tol=_COST_TOLERANCE, abs_tol=_COST_TOLERANCE):
        raise CompositionError(
            f"{label} cost {cost!r} disagrees with the independently recomputed "
            f"closed-cycle cost {independent!r}"
        )
    return nodes


def run_composition(
    matrix: Sequence[Sequence[float]],
    *,
    global_stage: StageSpec,
    polish_stage: StageSpec,
    evaluation_budget: Optional[int] = None,
    global_fraction: Optional[float] = None,
    smoke_default_fraction: bool = False,
) -> CompositionResult:
    """Run the global stage, then one polish on its validated best tour.

    ``evaluation_budget=None`` selects native mode (no budget, no fraction).
    """
    native = evaluation_budget is None
    if native:
        if global_fraction is not None:
            raise CompositionError(
                "native mode imposes no global_fraction or shared budget"
            )
        return _run_native(matrix, global_stage, polish_stage)
    if (
        isinstance(evaluation_budget, bool)
        or not isinstance(evaluation_budget, int)
        or evaluation_budget < 2
    ):
        raise CompositionError("evaluation_budget must be an integer of at least 2")
    fraction = resolve_global_fraction(global_fraction, smoke_default=smoke_default_fraction)
    return _run_fixed(
        matrix, global_stage, polish_stage, evaluation_budget, fraction
    )


def _call_global(spec: StageSpec, shared, cap) -> GlobalStageResult:
    try:
        result = spec.run(shared, cap)
    except Exception as exc:  # a failed global stage fails the composition
        raise CompositionError(f"global stage {spec.stage_id} failed: {exc}") from exc
    if not isinstance(result, GlobalStageResult):
        raise CompositionError(
            f"global stage {spec.stage_id} did not return a GlobalStageResult"
        )
    return result


def _call_polish(spec: StageSpec, tour: List[int], cost: float, budget) -> PolishStageResult:
    try:
        result = spec.run(list(tour), cost, budget)
    except Exception as exc:  # never silently return an unpolished result
        raise CompositionError(f"polish stage {spec.stage_id} failed: {exc}") from exc
    if not isinstance(result, PolishStageResult):
        raise CompositionError(
            f"polish stage {spec.stage_id} did not return a PolishStageResult"
        )
    return result


def _global_record(
    spec: StageSpec, result: GlobalStageResult, allocated: Optional[int], cost: float
) -> StageRecord:
    return StageRecord(
        name="global",
        stage_id=spec.stage_id,
        parameters=dict(spec.params),
        seed=spec.seed,
        allocated_evaluations=allocated,
        consumed_evaluations=int(result.evaluations),
        termination_reason=str(result.termination_reason),
        iterations=int(result.iterations),
        details={
            **dict(result.extra),
            "stage_ceiling_reached": bool(result.stage_ceiling_reached),
            "cost": cost,
        },
    )


def _polish_record(
    spec: StageSpec,
    result: PolishStageResult,
    allocated: Optional[int],
    cost: float,
    changed: bool,
) -> StageRecord:
    return StageRecord(
        name="polish",
        stage_id=spec.stage_id,
        parameters=dict(spec.params),
        seed=spec.seed,
        allocated_evaluations=allocated,
        consumed_evaluations=int(result.evaluations),
        termination_reason=str(result.termination_reason),
        iterations=int(result.iterations),
        details={
            **dict(result.extra),
            "incoming_cost_reused": True,
            "polish_changed_tour": changed,
            "cost": cost,
        },
    )


def _run_fixed(matrix, global_spec, polish_spec, budget_total, fraction) -> CompositionResult:
    shared = ObjectiveEvaluationBudget(budget_total)
    cap = _stage_cap(budget_total, fraction)

    # Global stage: pure, capped at floor(B * fraction) on the shared counter.
    global_result = _call_global(global_spec, shared, cap)
    global_tour = _validate_tour(global_result.tour, matrix, global_result.cost, "global")
    global_used = shared.used
    if global_used > cap:
        raise CompositionError(
            f"global stage exceeded its ceiling: used={global_used}, cap={cap}"
        )
    if int(global_result.evaluations) != global_used:
        raise CompositionError(
            "global stage accounting mismatch: the stage reports "
            f"{global_result.evaluations} evaluations but the shared counter holds "
            f"{global_used}"
        )

    # Polish stage: the rest of the budget, a view built now that the stage starts.
    polish_view = StageCappedBudget(shared, None)
    polish_result = _call_polish(
        polish_spec, global_tour, float(global_result.cost), polish_view
    )
    polish_tour = _validate_tour(polish_result.tour, matrix, polish_result.cost, "polish")
    if shared.used > budget_total:  # unreachable through the counter; kept as a guard
        raise CompositionError("evaluation budget exceeded")
    polish_used = shared.used - global_used
    if int(polish_result.evaluations) != polish_used:
        raise CompositionError(
            "polish stage accounting mismatch: the stage reports "
            f"{polish_result.evaluations} evaluations but the shared counter moved "
            f"by {polish_used}"
        )

    changed = polish_tour != global_tour
    termination = (
        EVALUATION_BUDGET_EXHAUSTED
        if polish_result.termination_reason == EVALUATION_BUDGET_EXHAUSTED
        else str(polish_result.termination_reason)
    )
    return CompositionResult(
        tour=polish_tour,
        cost=float(polish_result.cost),
        evaluations=shared.used,  # the run total comes from the shared counter
        mode=FIXED_MODE,
        evaluation_budget=budget_total,
        global_fraction=fraction,
        termination_reason=termination,
        global_stage=_global_record(global_spec, global_result, cap, float(global_result.cost)),
        polish_stage=_polish_record(
            polish_spec, polish_result, budget_total - global_used,
            float(polish_result.cost), changed,
        ),
        polish_changed_tour=changed,
    )


def _run_native(matrix, global_spec, polish_spec) -> CompositionResult:
    global_result = _call_global(global_spec, None, None)
    global_tour = _validate_tour(global_result.tour, matrix, global_result.cost, "global")
    if global_result.termination_reason not in NATIVE_COMPLETE_REASONS:
        raise CompositionError(
            "native composite requires both stages to complete; global stage "
            f"ended with {global_result.termination_reason!r}"
        )
    polish_result = _call_polish(
        polish_spec, global_tour, float(global_result.cost), ObjectiveEvaluationBudget(None)
    )
    polish_tour = _validate_tour(polish_result.tour, matrix, polish_result.cost, "polish")
    if polish_result.termination_reason not in NATIVE_COMPLETE_REASONS:
        raise CompositionError(
            "native composite requires both stages to complete; polish stage "
            f"ended with {polish_result.termination_reason!r}"
        )
    changed = polish_tour != global_tour
    return CompositionResult(
        tour=polish_tour,
        cost=float(polish_result.cost),
        evaluations=int(global_result.evaluations) + int(polish_result.evaluations),
        mode=NATIVE_MODE,
        evaluation_budget=None,
        global_fraction=None,
        termination_reason=COMPOSITE_COMPLETE,
        global_stage=_global_record(global_spec, global_result, None, float(global_result.cost)),
        polish_stage=_polish_record(
            polish_spec, polish_result, None, float(polish_result.cost), changed
        ),
        polish_changed_tour=changed,
    )


# ---- stage adapters ------------------------------------------------------

_HIDDEN_POLISH_KEYS = frozenset({
    "polish_enabled", "polish_iters", "polish_interval", "final_polish_iters",
})

_SWARM_REQUIRED = {
    "GWO": ("pack_size", "max_iterations", "initial_a", "exploration_rate",
            "max_no_improvement"),
    "HHO": ("hawks", "max_iterations", "initial_energy", "jump_probability",
            "max_no_improvement", "dive_count", "levy_scale"),
}
_THREE_OPT_REQUIRED = ("max_iterations", "first_improvement", "window")


def _require_explicit(params: Mapping[str, Any], required: Sequence[str], who: str) -> None:
    missing = [name for name in required if name not in params]
    if missing:
        raise CompositionError(
            f"{who} needs explicit hyperparameters, missing: {', '.join(missing)}"
        )


def swarm_global_stage(
    algorithm: str,
    matrix: Sequence[Sequence[float]],
    params: Mapping[str, Any],
    *,
    seed: int,
    strict: bool = True,
) -> StageSpec:
    """Pure canonical GWO/HHO global stage on the injected shared counter.

    ``params`` is the ``global`` namespace. Polish keys are refused: the global
    stage performs no hidden polish. ``strict`` (the default) requires every
    swarm hyperparameter to be given, as paper-scale manifests do.
    """
    if algorithm not in _SWARM_REQUIRED:
        raise CompositionError(f"unsupported global algorithm {algorithm!r}")
    hidden = sorted(_HIDDEN_POLISH_KEYS.intersection(params))
    if hidden:
        raise CompositionError(
            f"the global stage performs no hidden polish; remove from the global "
            f"namespace: {', '.join(hidden)} (polish belongs to the polish stage)"
        )
    if strict:
        _require_explicit(params, _SWARM_REQUIRED[algorithm], f"{algorithm} global stage")
    kwargs = dict(params)
    stage_id = f"Core-{algorithm}-TSP-Pure"

    def run(shared, cap) -> GlobalStageResult:
        if algorithm == "GWO":
            from uniride_core.algorithms.tsp_matrix_metaheuristics.gwo_solver import (
                GWOOptimizer as Solver,
            )
        else:
            from uniride_core.algorithms.tsp_matrix_metaheuristics.hho_solver import (
                HHOOptimizer as Solver,
            )

        solver = Solver(
            **kwargs,
            random_seed=seed,
            polish_enabled=False,
            shared_budget=shared,
            stage_cap=cap,
        )
        # recalculate=False: the cost is the one the stage counted.
        result = solver.solve_with_matrix(
            [list(row) for row in matrix], recalculate=False, closed_tsp=True
        )
        stats = dict(result.extra_stats or {})
        ceiling = bool(stats.get("budget_terminated", False))
        iterations = int(result.iterations or 0)
        if ceiling:
            # Stage ceiling (or total limit) reached: this is the global stage's
            # own termination reason, not the run's aggregate reason.
            reason = EVALUATION_BUDGET_EXHAUSTED
        elif iterations >= int(kwargs.get("max_iterations", 0) or 0):
            reason = "max_iterations"
        else:
            reason = "stagnation_limit"
        return GlobalStageResult(
            tour=[int(node) for node in result.tour],
            cost=float(result.tour_length),
            iterations=iterations,
            evaluations=int(stats.get("objective_evaluations") or 0),
            termination_reason=reason,
            stage_ceiling_reached=ceiling,
            extra={
                "variant": stats.get("variant"),
                "polish_executed": stats.get("polish_executed"),
                "execution_backend": stats.get("execution_backend"),
            },
        )

    return StageSpec(stage_id, run, dict(params), seed=seed)


def three_opt_polish_stage(
    matrix: Sequence[Sequence[float]],
    params: Mapping[str, Any],
    *,
    strict: bool = True,
) -> StageSpec:
    """Canonical ``Core-ThreeOpt-TSP`` polish on the supplied tour and known cost.

    Deterministic: the spec records no seed. The incoming tour is not
    re-evaluated (``initial_cost``); a directed matrix keeps directed costs.
    """
    if strict:
        _require_explicit(params, _THREE_OPT_REQUIRED, "3-opt polish stage")
    kwargs = dict(params)

    def run(tour, cost, budget) -> PolishStageResult:
        search = improve_three_opt_budgeted(
            tour, matrix, budget, initial_cost=cost, **kwargs
        )
        return PolishStageResult(
            tour=search.route,
            cost=search.cost,
            iterations=search.iterations,
            evaluations=search.evaluations,
            termination_reason=search.termination_reason,
            extra={"mode": search.mode},
        )

    return StageSpec("Core-ThreeOpt-TSP", run, dict(params), seed=None)


__all__ = [
    "COMPOSITE_COMPLETE",
    "CompositionError",
    "CompositionResult",
    "GlobalStageResult",
    "PolishStageResult",
    "SMOKE_GLOBAL_FRACTION",
    "StageRecord",
    "StageSpec",
    "resolve_global_fraction",
    "run_composition",
    "swarm_global_stage",
    "three_opt_polish_stage",
]
