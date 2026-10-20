"""Cell labels of the joint day model (WP-E11 J9b; design JOINT_DAY_MODEL_DESIGN.md 4.3, 3, 5.3; DECISION_LOG E13, E14).

A pure function of facts that were computed elsewhere: the primary solver's ``DaySolveResult``, the J2 ``DayBounds`` (bounds
and the infeasibility certificate), the verdict of the independent plan checker (J6) and the verdict of the second solver
(Gurobi cross-check, J5). Nothing is solved here and nothing outside ``uniride_core.exact`` is imported.

Vocabulary: exactly the ``day_status`` labels of design 4.3 (``LABELS``). The cross-check is a separate field of the same
table (``crosscheck_status``, design 6.1), so the label stays the design label and the proof claim is gated next to it:

* ``proof_claim_allowed`` is true only when a paper table may present the cell as proven. ``optimal``,
  ``optimal_stage1_by_bound``, ``infeasible_solver_proven`` and a tier-2 ``infeasible_certified`` need the cross-check
  verdict ``agree`` (E14: every optimal / solver-proven-infeasible paper cell, and tier 2 rests on solver-proven wave
  minima, design 3.2). A tier-1 certificate rests on arithmetic only and needs none. All other labels claim no proof.
* ``proof_claim_reason`` says why (``crosscheck_agree``, ``crosscheck_not_run``, ``crosscheck_inconclusive``,
  ``arithmetic_certificate``, ``not_a_proof_label``, ``rejected``). A cross-check verdict ``blocking`` (the two solvers
  disagree, design 4.1) makes the cell ``rejected`` ("certificate, checker or objective cross-check failed", design 4.3).

Bounds (design 3 and 4.3): the stage-1 value is K (homogeneous: LB0, LB0w) or S (typed: LB_S). ``bound_used`` is the best
bound among the solver's stage-1 bound and those §3 bounds, with its source and proof tag. A bound whose contributing wave
values include ``PROOF_UNVERIFIED`` is listed in ``bounds_considered`` and ``unverified_bounds`` but is never the bound
used and never makes a stage-1 value optimal; a stage-1 value below it is only flagged (``value_below_unverified_bound``).
A stage-1 value below a verified bound makes the cell ``rejected`` (design 5.3: bound consistency).

Flags: ``bound_above_incumbent:stageN`` (the stage's ``solver_message`` starts with the clip note of
``highs_backend``), ``non_lexicographic``, ``timing_dependent``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .day_bounds import PROOF_ARITHMETIC, PROOF_SOLVER, PROOF_UNVERIFIED, BoundResult, DayBounds
from .highs_backend import BOUND_ABOVE_INCUMBENT

LABEL_OPTIMAL = "optimal"
LABEL_OPTIMAL_STAGE1_BY_BOUND = "optimal_stage1_by_bound"
LABEL_FEASIBLE_WITH_GAP = "feasible_with_gap"
LABEL_BOUND_ONLY = "bound_only"
LABEL_INFEASIBLE_CERTIFIED = "infeasible_certified"
LABEL_INFEASIBLE_SOLVER_PROVEN = "infeasible_solver_proven"
LABEL_NOT_RUN_ENUMERATION_CAP = "not_run_enumeration_cap"
LABEL_REJECTED = "rejected"
LABEL_INPUT_REJECTED = "input_rejected"
LABEL_BACKEND_UNAVAILABLE = "backend_unavailable"
LABELS = (LABEL_OPTIMAL, LABEL_OPTIMAL_STAGE1_BY_BOUND, LABEL_FEASIBLE_WITH_GAP, LABEL_BOUND_ONLY,
          LABEL_INFEASIBLE_CERTIFIED, LABEL_INFEASIBLE_SOLVER_PROVEN, LABEL_NOT_RUN_ENUMERATION_CAP, LABEL_REJECTED,
          LABEL_INPUT_REJECTED, LABEL_BACKEND_UNAVAILABLE)

CROSSCHECK_AGREE = "agree"
CROSSCHECK_BLOCKING = "blocking"
CROSSCHECK_INCONCLUSIVE = "inconclusive"
CROSSCHECK_NOT_RUN = "not_run"
CROSSCHECK_VERDICTS = (CROSSCHECK_AGREE, CROSSCHECK_BLOCKING, CROSSCHECK_INCONCLUSIVE, CROSSCHECK_NOT_RUN)

SOURCE_SOLVER = "solver"
SOURCE_CERTIFICATE = "certificate"
_PROOF_RANK = {PROOF_ARITHMETIC: 2, PROOF_SOLVER: 1, PROOF_UNVERIFIED: 0}
_SOURCE_ORDER = ("solver", "trivial_zero", "ampl_presolve", "lb0w", "lb0", "lb_s")  # ties: earlier wins


@dataclass(frozen=True)
class BoundCandidate:
    """One lower bound on the stage-1 value, with where it comes from and how it is known."""

    name: str  # solver, trivial_zero, ampl_presolve, lb0, lb0w, lb_s
    value: int
    proof: str  # PROOF_SOLVER, PROOF_ARITHMETIC or PROOF_UNVERIFIED
    unverified_waves: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CellLabel:
    label: str
    reason: str = ""
    bound_used: Optional[int] = None
    bound_source: Optional[str] = None
    bound_proof: Optional[str] = None
    bounds_considered: Tuple[BoundCandidate, ...] = ()
    unverified_bounds: Tuple[Tuple[str, str], ...] = ()  # (bound name, wave id) with PROOF_UNVERIFIED
    certificate_tier: Optional[int] = None
    stage_statuses: Tuple[str, ...] = ()
    flags: Tuple[str, ...] = ()
    crosscheck_status: str = CROSSCHECK_NOT_RUN
    proof_claim_allowed: bool = False
    proof_claim_reason: str = ""


# ------------------------------------------------------------------ helpers
def _candidate_from_bound(name: str, b: Optional[BoundResult]) -> Optional[BoundCandidate]:
    if b is None:
        return None
    unverified = tuple(c.wave_id for c in b.contributions if c.proof == PROOF_UNVERIFIED)
    if unverified:
        proof = PROOF_UNVERIFIED
    elif any(c.proof == PROOF_SOLVER for c in b.contributions):
        proof = PROOF_SOLVER
    else:  # only arithmetic contributions, or none (value 0)
        proof = PROOF_ARITHMETIC
    return BoundCandidate(name, b.value, proof, unverified)


def _candidates(stage1, bounds: Optional[DayBounds], typed: bool) -> Tuple[BoundCandidate, ...]:
    out = []
    if stage1 is not None and stage1.bound_ceil is not None:
        source = stage1.bound_source or SOURCE_SOLVER
        proof = PROOF_ARITHMETIC if source == "trivial_zero" else PROOF_SOLVER
        out.append(BoundCandidate(source, int(stage1.bound_ceil), proof))
    if bounds is not None:
        wanted = (("lb_s", bounds.lb_s),) if typed else (("lb0", bounds.lb0), ("lb0w", bounds.lb0w))
        out.extend(c for c in (_candidate_from_bound(n, b) for n, b in wanted) if c is not None)
    return tuple(out)


def _best_verified(candidates: Tuple[BoundCandidate, ...]) -> Optional[BoundCandidate]:
    verified = [c for c in candidates if c.proof != PROOF_UNVERIFIED]
    if not verified:
        return None

    def key(c: BoundCandidate):
        order = _SOURCE_ORDER.index(c.name) if c.name in _SOURCE_ORDER else len(_SOURCE_ORDER)
        return (-c.value, -_PROOF_RANK[c.proof], order)

    return min(verified, key=key)


def _flags(result) -> Tuple[str, ...]:
    flags = []
    for stage in getattr(result, "stages", ()) or ():
        message = stage.result.solver_message
        if message and str(message).startswith(BOUND_ABOVE_INCUMBENT):
            flags.append(f"{BOUND_ABOVE_INCUMBENT}:stage{stage.stage}")
    if getattr(result, "non_lexicographic", False):
        flags.append("non_lexicographic")
    if getattr(result, "timing_dependent", False):
        flags.append("timing_dependent")
    return tuple(flags)


def _gate(label: str, crosscheck: str, certificate_tier: Optional[int]) -> Tuple[bool, str]:
    """Whether a paper table may present this cell as proven (E14), and why."""
    if label == LABEL_REJECTED:
        return False, "rejected"
    if label == LABEL_INFEASIBLE_CERTIFIED and certificate_tier == 1:
        return True, "arithmetic_certificate"
    if label in (LABEL_OPTIMAL, LABEL_OPTIMAL_STAGE1_BY_BOUND, LABEL_INFEASIBLE_SOLVER_PROVEN, LABEL_INFEASIBLE_CERTIFIED):
        return crosscheck == CROSSCHECK_AGREE, f"crosscheck_{crosscheck}"
    return False, "not_a_proof_label"


# ------------------------------------------------------------------ the label
def label_cell(*, enumeration_complete: bool, result, bounds: Optional[DayBounds] = None,
               crosscheck: str = CROSSCHECK_NOT_RUN, checker_ok: Optional[bool] = None) -> CellLabel:
    """The design 4.3 label of one cell.

    ``result`` is the primary solver's ``DaySolveResult`` (``None`` when the solver did not run, e.g. a certified or an
    enumeration-capped cell); ``bounds`` the J2 ``DayBounds`` (``None`` when none were computed); ``crosscheck`` one of
    ``CROSSCHECK_VERDICTS`` (an input: this module does not talk to the second solver); ``checker_ok`` the verdict of the
    independent plan checker on the plan of the cell, required (``True``/``False``) whenever the solver found a plan.
    Precedence: enumeration cap, solver rejection / checker failure / solver disagreement, certificate (a certificate with
    a plan is a contradiction), solver status.
    """
    if crosscheck not in CROSSCHECK_VERDICTS:
        raise ValueError(f"cross-check verdict must be one of {CROSSCHECK_VERDICTS}, got {crosscheck!r}")
    stages = tuple(getattr(result, "stages", ()) or ()) if result is not None else ()
    stage1 = stages[0].result if stages else None
    has_plan = stage1 is not None and stage1.objective is not None
    flags = _flags(result) if result is not None else ()
    statuses = tuple(s.result.status for s in stages)
    certificate = bounds.certificate if bounds is not None else None
    typed = bool(result is not None and getattr(result, "mode", "") == "typed")
    candidates = _candidates(stage1, bounds, typed)
    unverified = tuple((c.name, w) for c in candidates for w in c.unverified_waves)
    best = _best_verified(candidates)

    def make(label: str, reason: str = "", *, used: Optional[BoundCandidate] = None, tier: Optional[int] = None,
             extra_flags: Tuple[str, ...] = ()) -> CellLabel:
        allowed, why = _gate(label, crosscheck, tier)
        return CellLabel(label=label, reason=reason, bound_used=None if used is None else used.value,
                         bound_source=None if used is None else used.name,
                         bound_proof=None if used is None else used.proof, bounds_considered=candidates,
                         unverified_bounds=unverified, certificate_tier=tier, stage_statuses=statuses,
                         flags=flags + extra_flags, crosscheck_status=crosscheck, proof_claim_allowed=allowed,
                         proof_claim_reason=why)

    if not enumeration_complete:
        return make(LABEL_NOT_RUN_ENUMERATION_CAP)
    if has_plan and checker_ok is None:
        raise ValueError("a cell with a plan needs the verdict of the independent checker (checker_ok True or False)")
    if result is not None and result.status == "rejected":
        return make(LABEL_REJECTED, "solver_rejected")
    if has_plan and checker_ok is False:
        return make(LABEL_REJECTED, "checker_failed")
    if crosscheck == CROSSCHECK_BLOCKING:
        return make(LABEL_REJECTED, "crosscheck_disagreement")
    if certificate is not None:
        if has_plan:
            return make(LABEL_REJECTED, "certificate_contradicts_plan")
        cert_candidate = BoundCandidate(SOURCE_CERTIFICATE, certificate.lower_bound, PROOF_ARITHMETIC
                                        if certificate.tier == 1 else PROOF_SOLVER)
        return make(LABEL_INFEASIBLE_CERTIFIED, certificate.kind, used=cert_candidate, tier=certificate.tier)
    if result is None:
        raise ValueError("no solver result and no certificate: nothing to label")
    if result.status == "input_rejected":
        return make(LABEL_INPUT_REJECTED, getattr(result, "note", "") or "")
    if result.status == "backend_unavailable":
        return make(LABEL_BACKEND_UNAVAILABLE, getattr(result, "note", "") or "")
    if result.status == "infeasible_proven":
        return make(LABEL_INFEASIBLE_SOLVER_PROVEN)
    if result.status == "bound_only":
        return make(LABEL_BOUND_ONLY, used=best)
    # a plan exists (optimal / feasible_with_gap)
    value = stage1.objective
    if best is not None and value < best.value:
        return make(LABEL_REJECTED, "value_below_bound", used=best)
    extra = ()
    if any(c.proof == PROOF_UNVERIFIED and value < c.value for c in candidates):
        extra = ("value_below_unverified_bound",)
    if result.status == "optimal":
        return make(LABEL_OPTIMAL, used=best, extra_flags=extra)
    if stage1.status != "optimal" and best is not None and value == best.value:
        return make(LABEL_OPTIMAL_STAGE1_BY_BOUND, used=best, extra_flags=extra)
    return make(LABEL_FEASIBLE_WITH_GAP, used=best, extra_flags=extra)
