"""Result contract of the ``global_then_final_3opt`` and ``global_then_final_alns``
compositions (Gate C, C-08 and C-09).

``Core-GWO-TSP-Memetic-3opt`` / ``Core-HHO-TSP-Memetic-3opt`` and the ``-Memetic-ALNS`` pair
run a pure GWO/HHO global stage and then one canonical polish (3-opt or ALNS) on the best
validated global tour, on ONE shared objective counter (``uniride_core.algorithms.composition.run_composition``). A composite
result row carries the stage record in ``composition`` and is validated here, once, for the
fixed-budget manifest, the native manifest and the governed gateway.

Accounting rules (``ACADEMIC_STUDY_UNIFICATION_DESIGN.md`` composition rules 1-9):

* fixed budget ``B`` with an explicit ``global_fraction``: the global stage is allocated
  ``global_stage_cap(B, f)`` (the shared engine rule, never local float arithmetic), the
  polish stage the rest, ``B - global consumed``; the run total is the shared counter and
  equals the sum of the stage evaluations;
* the row ``termination_reason`` is the polish stage's reason and
  ``budget_terminated == (termination_reason == "evaluation_budget_exhausted")``; the global
  stage's ceiling stop stays in the global stage record;
* native mode: no budget, no cap, stage counts are summed for description only, and the row
  reason is ``composite_complete`` only when both stages completed. ``composite_complete``
  belongs to composite rows and to no other row;
* the 3-opt polish is deterministic and records no seed; the ALNS polish records the seed
  ``derive_polish_seed(protocol_version, run_seed)`` of the manifest's own protocol version
  and the per-run paired seed (never the base seed), plus both inputs, in its stage;
* every stage record carries its own wall time ``elapsed_sec`` (design native rule 4).

This module imports only ``uniride_core``; ``fairness`` and ``native_protocol`` import it.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional

from uniride_core.algorithms.composition import (
    COMPOSITE_COMPLETE,
    CompositionError,
    CompositionResult,
    derive_polish_seed,
    global_stage_cap,
    validate_alns_polish_params,
)

KIND_3OPT = "global_then_final_3opt"
KIND_ALNS = "global_then_final_alns"
COMPOSITE_VARIANTS = frozenset({KIND_3OPT, KIND_ALNS})
COMPOSITE_COMPLETE_REASON = COMPOSITE_COMPLETE
# composition kind -> polish stage ID / polish_policy operator
POLISH_STAGE_IDS: Dict[str, str] = {KIND_3OPT: "Core-ThreeOpt-TSP", KIND_ALNS: "ALNS-TSP"}
POLISH_OPERATORS: Dict[str, str] = {KIND_3OPT: "3-opt", KIND_ALNS: "ALNS"}
# canonical composite ID -> (family, global stage ID)
COMPOSITE_ALGORITHMS: Dict[str, tuple] = {
    "Core-GWO-TSP-Memetic-3opt": ("GWO", "Core-GWO-TSP-Pure"),
    "Core-HHO-TSP-Memetic-3opt": ("HHO", "Core-HHO-TSP-Pure"),
    "Core-GWO-TSP-Memetic-ALNS": ("GWO", "Core-GWO-TSP-Pure"),
    "Core-HHO-TSP-Memetic-ALNS": ("HHO", "Core-HHO-TSP-Pure"),
}
COMPOSITE_KIND_OF: Dict[str, str] = {
    "Core-GWO-TSP-Memetic-3opt": KIND_3OPT,
    "Core-HHO-TSP-Memetic-3opt": KIND_3OPT,
    "Core-GWO-TSP-Memetic-ALNS": KIND_ALNS,
    "Core-HHO-TSP-Memetic-ALNS": KIND_ALNS,
}
FIXED_GLOBAL_REASONS = frozenset({"evaluation_budget_exhausted", "max_iterations", "stagnation_limit"})
# ALNS never stops for lack of an improving move, so that reason is refused for it
FIXED_POLISH_REASONS = {
    KIND_3OPT: frozenset({"evaluation_budget_exhausted", "max_iterations", "no_improving_move"}),
    KIND_ALNS: frozenset({"evaluation_budget_exhausted", "max_iterations", "stagnation_limit"}),
}
NATIVE_GLOBAL_REASONS = frozenset({"max_iterations", "stagnation_limit"})
NATIVE_POLISH_REASONS = {
    KIND_3OPT: frozenset({"max_iterations", "no_improving_move"}),
    KIND_ALNS: frozenset({"max_iterations", "stagnation_limit"}),
}
HIDDEN_POLISH_KEYS = frozenset({"polish_enabled", "polish_iters", "polish_interval", "final_polish_iters"})
POLISH_REQUIRED_KEYS = frozenset({"max_iterations", "first_improvement", "window"})


def is_composite_algorithm(algorithm_id: Any) -> bool:
    return algorithm_id in COMPOSITE_ALGORITHMS


def is_composite_variant(variant: Any) -> bool:
    return variant in COMPOSITE_VARIANTS


def composite_kind(algorithm_id: str) -> str:
    return COMPOSITE_KIND_OF[algorithm_id]


def composition_record(result: CompositionResult, kind: str) -> Dict[str, Any]:
    """The persisted stage record of one composite run (no tour: the row carries it)."""
    if kind not in COMPOSITE_VARIANTS:
        raise ValueError(f"unknown composition kind {kind!r}")
    return {
        "kind": kind,
        "mode": result.mode,
        "evaluation_budget": result.evaluation_budget,
        "global_fraction": result.global_fraction,
        "polish_changed_tour": result.polish_changed_tour,
        "stages": [stage.to_dict() for stage in result.stages],
    }


def _is_count(value: Any, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _is_wall_time(value: Any) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and value >= 0
    )


def validate_composite_result(
    result: Any, *, fixed_budget: Optional[int], protocol_version: Optional[str] = None
) -> List[str]:
    """Errors of a composite result row; ``fixed_budget`` None selects the native contract.

    ``protocol_version`` is the version of the manifest that validates the row; the ALNS
    polish seed must be derived from it and from the row's own run seed.
    """
    errors: List[str] = []
    native = fixed_budget is None
    algorithm_id = getattr(result, "algorithm_id", None)
    variant = getattr(result, "variant", None)
    reason = getattr(result, "termination_reason", None)
    if not is_composite_algorithm(algorithm_id):
        if is_composite_variant(variant):
            errors.append("composite variants are reserved for the composite algorithm IDs")
        if reason == COMPOSITE_COMPLETE_REASON:
            errors.append("composite_complete is reserved for composite rows")
        return errors
    family, global_id = COMPOSITE_ALGORITHMS[algorithm_id]
    kind = COMPOSITE_KIND_OF[algorithm_id]
    polish_id = POLISH_STAGE_IDS[kind]
    if variant != kind:
        errors.append(f"composite algorithm variant must be {kind}")
        return errors
    if getattr(result, "algorithm_family", None) != family:
        errors.append("composite algorithm_family does not match algorithm_id")

    record = getattr(result, "composition", None)
    if not isinstance(record, Mapping):
        errors.append("composite row must carry its composition stage record")
        return errors
    if record.get("kind") != kind:
        errors.append(f"composition kind must be {kind}")
    expected_mode = "native" if native else "fixed_budget"
    if record.get("mode") != expected_mode:
        errors.append(f"composition mode must be {expected_mode}")
    stages = record.get("stages")
    if (
        not isinstance(stages, list)
        or len(stages) != 2
        or not all(isinstance(stage, Mapping) for stage in stages)
        or [stage.get("name") for stage in stages] != ["global", "polish"]
    ):
        errors.append("composition must record exactly the global and the polish stage")
        return errors
    global_stage, polish_stage = stages
    if global_stage.get("stage_id") != global_id:
        errors.append(f"global stage must be {global_id} (pure, no hidden polish)")
    if polish_stage.get("stage_id") != polish_id:
        errors.append(f"polish stage must be {polish_id}")
    if kind == KIND_3OPT and polish_stage.get("seed") is not None:
        errors.append("the deterministic 3-opt polish stage records no secondary seed")
    if kind == KIND_ALNS:
        errors.extend(_alns_seed_errors(polish_stage, getattr(result, "seed", None), protocol_version))
    if global_stage.get("seed") != getattr(result, "seed", None):
        errors.append("global stage seed must be the paired run seed")
    global_params = global_stage.get("parameters")
    polish_params = polish_stage.get("parameters")
    if not isinstance(global_params, Mapping) or HIDDEN_POLISH_KEYS & set(global_params):
        errors.append("global stage parameters must not carry polish keys (no hidden polish)")
    if kind == KIND_3OPT:
        if not isinstance(polish_params, Mapping) or set(polish_params) != POLISH_REQUIRED_KEYS:
            errors.append("polish stage parameters must be exactly " + ", ".join(sorted(POLISH_REQUIRED_KEYS)))
    elif not isinstance(polish_params, Mapping):
        errors.append("polish stage parameters must be a mapping")
    else:
        try:  # one ALNS rule set, owned by the composition engine
            validate_alns_polish_params(polish_params, strict=True)
        except CompositionError as exc:
            errors.append(f"polish stage ALNS parameters are invalid: {exc}")
    for label, stage in (("global", global_stage), ("polish", polish_stage)):
        if not _is_wall_time(stage.get("elapsed_sec")):
            errors.append(f"{label} stage elapsed_sec must be a finite non-negative number")

    consumed = []
    for label, stage in (("global", global_stage), ("polish", polish_stage)):
        value = stage.get("consumed_evaluations")
        if not _is_count(value):
            errors.append(f"{label} stage consumed_evaluations must be a non-negative integer")
        else:
            consumed.append(value)
    if len(consumed) != 2:
        return errors
    global_used, polish_used = consumed
    if global_used < 1:
        errors.append("global stage must consume at least one evaluation")
    evaluations = getattr(result, "evaluations", None)
    if evaluations != global_used + polish_used:
        errors.append(
            "composite evaluations must equal the sum of the stage evaluations "
            f"({global_used} + {polish_used}), got {evaluations!r}"
        )

    global_reason = global_stage.get("termination_reason")
    polish_reason = polish_stage.get("termination_reason")
    ceiling = (global_stage.get("details") or {}).get("stage_ceiling_reached")
    if not isinstance(ceiling, bool):
        errors.append("global stage must record stage_ceiling_reached")
    elif ceiling is not (global_reason == "evaluation_budget_exhausted"):
        errors.append("global stage_ceiling_reached must match its termination_reason")
    changed = record.get("polish_changed_tour")
    if not isinstance(changed, bool) or changed is not (polish_stage.get("details") or {}).get("polish_changed_tour"):
        errors.append("polish_changed_tour must be a boolean recorded in the record and the polish stage")

    if native:
        if record.get("evaluation_budget") is not None or record.get("global_fraction") is not None:
            errors.append("native composition imposes no budget and no global_fraction")
        for label, stage in (("global", global_stage), ("polish", polish_stage)):
            if stage.get("allocated_evaluations") is not None:
                errors.append(f"native {label} stage has no allocated evaluations")
        if global_reason not in NATIVE_GLOBAL_REASONS or polish_reason not in NATIVE_POLISH_REASONS[kind]:
            errors.append("native composite requires both stages to complete on their own")
        if reason != COMPOSITE_COMPLETE_REASON:
            errors.append("native composite row termination_reason must be composite_complete")
        return errors

    # ---- fixed budget ----
    fraction = record.get("global_fraction")
    if record.get("evaluation_budget") != fixed_budget:
        errors.append("composition evaluation_budget does not match the manifest")
    try:
        if isinstance(fraction, bool) or not isinstance(fraction, (int, float)) or not math.isfinite(fraction) or not 0 < fraction < 1:
            raise CompositionError("global_fraction must be a number strictly between 0 and 1")
        cap = global_stage_cap(fixed_budget, fraction)
    except CompositionError as exc:
        errors.append(f"global_fraction is invalid: {exc}")
        cap = None
    if cap is not None and global_stage.get("allocated_evaluations") != cap:
        errors.append(
            f"global stage allocation must be global_stage_cap({fixed_budget}, {fraction!r}) = {cap}, "
            f"got {global_stage.get('allocated_evaluations')!r}"
        )
    if cap is not None and global_used > cap:
        errors.append(f"global stage exceeds its allocation ({global_used} > {cap})")
    if polish_stage.get("allocated_evaluations") != fixed_budget - global_used:
        errors.append("polish stage allocation must be the budget minus the global evaluations")
    if polish_used > fixed_budget - global_used:
        errors.append("polish stage exceeds its allocation")
    if global_reason not in FIXED_GLOBAL_REASONS or polish_reason not in FIXED_POLISH_REASONS[kind]:
        errors.append("composite stage termination reasons are invalid for the fixed budget")
    if reason != polish_reason:
        errors.append("row termination_reason must be the polish stage's reason, not the global stage's")
    if getattr(result, "budget_terminated", None) is not (reason == "evaluation_budget_exhausted"):
        errors.append("budget_terminated must equal (termination_reason == evaluation_budget_exhausted)")
    return errors


def _alns_seed_errors(
    polish_stage: Mapping[str, Any], run_seed: Any, protocol_version: Optional[str]
) -> List[str]:
    """The ALNS polish seed is derived from the manifest's version and the per-run seed."""
    seed = polish_stage.get("seed")
    details = polish_stage.get("details") or {}
    recorded = details.get("protocol_version")
    if not isinstance(recorded, str) or not recorded:
        return ["ALNS polish seed derivation must record its protocol_version"]
    errors: List[str] = []
    version = recorded if protocol_version is None else protocol_version
    if recorded != version:
        errors.append("ALNS polish seed must be derived from the manifest protocol_version")
    try:
        expected = derive_polish_seed(version, run_seed)
    except (TypeError, ValueError):
        return errors + ["ALNS polish seed cannot be derived from the run seed"]
    if seed != expected or details.get("derived_seed") != expected:
        errors.append(
            "ALNS polish seed must be derive_polish_seed(protocol_version, run_seed) "
            f"= {expected}, got {seed!r}"
        )
    if details.get("run_seed") != run_seed:
        errors.append("ALNS polish stage must record the per-run seed it derived from")
    return errors


def validate_composite_policy(polish_policy: Mapping[str, Any], result: Any) -> List[str]:
    """Polish-policy flags of a composite row follow the executed polish stage."""
    errors: List[str] = []
    stages = (getattr(result, "composition", None) or {}).get("stages") or [{}, {}]
    ran = (stages[1].get("consumed_evaluations") or 0) > 0 if len(stages) == 2 else False
    expected = {"enabled": ran, "initial": False, "periodic": False, "final": ran}
    for name, value in expected.items():
        if polish_policy.get(name) is not value:
            errors.append(f"composite polish_policy {name} must be {value} (executed final polish)")
    kind = COMPOSITE_KIND_OF.get(getattr(result, "algorithm_id", None), KIND_3OPT)
    operator = POLISH_OPERATORS[kind]
    if polish_policy.get("operator") != (operator if ran else None):
        errors.append(f"composite polish_policy operator must be '{operator}' exactly when the polish ran")
    return errors
