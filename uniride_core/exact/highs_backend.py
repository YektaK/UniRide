"""HiGHS backend and lexicographic stage runner for the joint day model (WP-E11 J4, design JOINT_DAY_MODEL_DESIGN.md
2.4, 4.1-4.3; status vocabulary of EXACT_SOLVER_AMPL_DESIGN.md section 4).

* ``highspy`` is an optional extra (``requirements-exact.txt``) and is imported lazily inside ``_import_highspy`` only,
  never at module import time. A missing ``highspy`` gives a result with status ``backend_unavailable``; the public entry
  points do not raise it into callers.
* ``run_day_stages`` solves the J3 stages in order (homogeneous 1-2, typed 1-3), each stage as one solver call with its
  own time limit and the earlier stage values fixed. The fixed and the minimised type are passed to ``build_joint_model``
  explicitly (a typed day refuses an instance whose first type is not the larger one), never through its default.
* Determinism and limits (design 4.2): threads 1, random seed 0, MIP relative gap 0, absolute gap 0.99 (integer
  objectives), time limit per call (default 600 s). HiGHS has no work limit, so a time-limited stage is always
  ``timing_dependent``. The option string that was applied is stored verbatim (it is built from the very list that is
  applied).
* A stage is ``optimal`` only if the runner's own check ``incumbent <= ceil(bound - 1e-6)`` holds. The incumbent is not
  the solver's objective: the solution values are rounded (refused as ``rejected`` when one is fractional beyond the
  integrality tolerance), re-checked against every bound and row of the model in integers, and the objective is
  recomputed from them.
* Stage 1 (or a later stage) with an incumbent but no proof makes every later stage ``non_lexicographic``; with no
  incumbent later stages are skipped (``skipped_no_stage1_incumbent`` / ``skipped_no_stage2_incumbent``).

Offline research tooling: not imported by optimizer_api or src, not in the production registry. Imports nothing from
``academic_benchmark``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Tuple

from .ampl_backend import StageResult, snap_to_integer_data
from .day_instance import READY, DayInstance
from .day_joint import JointModel, build_joint_model, selection_from_values

DEFAULT_TIME_LIMIT_SECONDS = 600.0  # owner decision E14: per solver call
MIP_GAP = 0.0
MIP_GAP_ABS = 0.99  # integer objectives: incumbent - bound < 1 proves optimality
_INT_TOL = 1e-5  # integrality tolerance of the incumbent values (HiGHS default is 1e-6)
_BOUND_TOL = 1e-6
_HUGE = 1e20
_TIMING_REASONS = ("wall_limit", "other_limit")
_BOUND_STATUSES = ("optimal", "feasible_with_gap", "bound_only")
_OTHER_LIMITS = frozenset({"kIterationLimit", "kSolutionLimit", "kInterrupt", "kHighsInterrupt", "kObjectiveBound",
                           "kObjectiveTarget", "kMemoryLimit"})
_FAILURES = frozenset({"kUnbounded", "kUnboundedOrInfeasible", "kLoadError", "kModelError", "kPresolveError",
                       "kSolveError", "kPostsolveError", "kUnknown", "kNotset", "kModelEmpty"})


class HighsBackendUnavailable(RuntimeError):
    """``highspy`` is missing or unusable (status ``backend_unavailable``)."""


def _import_highspy():
    """The only place where ``highspy`` is imported."""
    try:
        import highspy
    except Exception as exc:  # noqa: BLE001 - any import problem means the backend cannot be used
        raise HighsBackendUnavailable(f"highspy unavailable: {type(exc).__name__}") from exc
    return highspy


@dataclass(frozen=True)
class HighsSettings:
    threads: int = 1
    seed: int = 0
    mip_gap: float = MIP_GAP
    mip_gap_abs: float = MIP_GAP_ABS
    time_limit: float = DEFAULT_TIME_LIMIT_SECONDS

    def options(self) -> Tuple[Tuple[str, object], ...]:
        """The options exactly as applied to HiGHS, in order."""
        return (("output_flag", False), ("threads", self.threads), ("random_seed", self.seed),
                ("mip_rel_gap", float(self.mip_gap)), ("mip_abs_gap", float(self.mip_gap_abs)),
                ("time_limit", float(self.time_limit)))

    def option_string(self) -> str:
        return " ".join(f"{k}={str(v).lower() if isinstance(v, bool) else format(v, 'g') if isinstance(v, float) else v}"
                        for k, v in self.options())


def highs_probe() -> Tuple[bool, Optional[str], str]:
    """(available, HiGHS version, reason): imports ``highspy`` and solves nothing."""
    try:
        highspy = _import_highspy()
        return True, str(highspy.Highs().version()), ""
    except HighsBackendUnavailable as exc:
        return False, None, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"highspy unusable: {type(exc).__name__}"


# ---------------------------------------------------------------- outcome classification
def classify_highs_outcome(model_status: str, *, incumbent: Optional[int], bound: Optional[float]) -> StageResult:
    """Map a HiGHS model status name (``kOptimal``, ``kTimeLimit``, ...) to the protocol labels.

    ``incumbent`` is the integer objective of a verified feasible solution (``None`` when there is none); ``bound`` is
    the solver's best dual bound (``None``, infinite or absent means none). Every objective coefficient is >= 0 and
    every variable >= 0, so 0 is always a valid bound.
    """
    name = str(model_status)
    if name == "kInfeasible":
        return StageResult(status="infeasible_proven", stop_reason="infeasible", solve_result=name)
    if name in _FAILURES or not (name == "kOptimal" or name == "kTimeLimit" or name in _OTHER_LIMITS):
        return StageResult(status="rejected", stop_reason="solver_failure", solve_result=name)
    b = None
    if bound is not None and math.isfinite(float(bound)) and abs(float(bound)) < _HUGE:
        b = float(bound)
    b_ceil, source = (max(0, math.ceil(b - _BOUND_TOL)), "solver") if b is not None else (0, "trivial_zero")
    if incumbent is not None:
        b_ceil = min(b_ceil, incumbent)
    if name == "kOptimal":
        if incumbent is None:
            return StageResult(status="rejected", stop_reason="solver_failure", solve_result=name, bound=b)
        if incumbent - b_ceil < 1:
            status, reason = "optimal", "optimal"
        else:  # the solver reported solved, the runner's own check did not confirm it
            status, reason = "feasible_with_gap", "gap_tolerance"
    else:
        reason = "wall_limit" if name == "kTimeLimit" else "other_limit"
        status = "feasible_with_gap" if incumbent is not None else "bound_only"
    return StageResult(status=status, stop_reason=reason, timing_dependent=reason in _TIMING_REASONS,
                       objective=incumbent, bound=b, bound_ceil=b_ceil, bound_source=source, solve_result=name)


def _status_name(status) -> str:
    return getattr(status, "name", None) or str(status).split(".")[-1]


# ---------------------------------------------------------------- one stage on HiGHS
@dataclass(frozen=True)
class StageSolve:
    """What a stage solver returns: the labelled outcome and the integer values of every variable (or ``None``)."""
    result: StageResult
    values: Optional[Mapping[str, int]] = None


def check_integer_solution(model: JointModel, raw: Mapping[str, float]) -> Optional[Tuple[Mapping[str, int], int]]:
    """Round ``raw`` and verify bounds and rows in integers; ``(values, objective)`` or ``None`` when it is not a solution."""
    values = {}
    for v in model.variables:
        x = raw[v.name]
        if not math.isfinite(x) or abs(x - round(x)) > _INT_TOL:
            return None
        values[v.name] = int(round(x))
        if not (v.lower <= values[v.name] <= v.upper):
            return None
    names = [v.name for v in model.variables]
    for r in model.rows:
        act = sum(c * values[names[vi]] for vi, c in r.terms)
        if (r.sense == "E" and act != r.rhs) or (r.sense == "L" and act > r.rhs) or (r.sense == "G" and act < r.rhs):
            return None
    return values, sum(v.objective * values[v.name] for v in model.variables)


def highs_solve_stage(model: JointModel, settings: Optional[HighsSettings] = None) -> StageSolve:
    """One stage as one HiGHS call. Raises ``HighsBackendUnavailable`` when ``highspy`` is missing."""
    settings = settings or HighsSettings()
    highspy = _import_highspy()
    inf = highspy.kHighsInf
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = len(model.variables), len(model.rows)
    lp.col_cost_ = [float(v.objective) for v in model.variables]
    lp.col_lower_ = [float(v.lower) for v in model.variables]
    lp.col_upper_ = [float(v.upper) for v in model.variables]
    lp.integrality_ = [highspy.HighsVarType.kInteger] * len(model.variables)
    lp.row_lower_ = [float(r.rhs) if r.sense in ("E", "G") else -inf for r in model.rows]
    lp.row_upper_ = [float(r.rhs) if r.sense in ("E", "L") else inf for r in model.rows]
    start, index, value = [0], [], []
    for r in model.rows:
        for vi, c in r.terms:
            index.append(vi)
            value.append(float(c))
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = start, index, value
    h = highspy.Highs()
    for key, val in settings.options():
        if h.setOptionValue(key, val) != highspy.HighsStatus.kOk:
            raise RuntimeError(f"HiGHS refused option {key}={val}")
    if h.passModel(lp) == highspy.HighsStatus.kError:
        return StageSolve(StageResult(status="rejected", stop_reason="solver_failure", solve_result="pass_model_error"))
    h.run()
    status = _status_name(h.getModelStatus())
    info = h.getInfo()
    values, incumbent = None, None
    if info.primal_solution_status == 2:  # a feasible primal solution exists
        col_value = list(h.getSolution().col_value)
        checked = check_integer_solution(model, {v.name: col_value[i] for i, v in enumerate(model.variables)})
        if checked is None:  # fractional, out of bounds or violating a row: never an incumbent
            return StageSolve(StageResult(status="rejected", stop_reason="solver_failure", solve_result=status))
        values, incumbent = checked
    _, bound = snap_to_integer_data(None, info.mip_dual_bound)
    return StageSolve(classify_highs_outcome(status, incumbent=incumbent, bound=bound), values)


# ---------------------------------------------------------------- day runner
@dataclass(frozen=True)
class DayStage:
    stage: int
    model_name: str
    objective_name: str
    mps_sha256: str
    result: StageResult
    fixed: Mapping[str, int]
    selection: tuple = ()  # ((wave index, column_index, copies), ...) of the incumbent


@dataclass(frozen=True)
class DaySolveResult:
    status: str  # optimal, feasible_with_gap, bound_only, infeasible_proven, rejected, backend_unavailable, input_rejected
    mode: str = ""
    note: str = ""
    stages: Tuple[DayStage, ...] = ()
    objective: Optional[tuple] = None  # (K, total minutes) or (S, total minutes, car minutes); only with an incumbent at every stage
    non_lexicographic: bool = False
    timing_dependent: bool = False
    solver: str = "highs"
    solver_version: Optional[str] = None
    solver_options: str = ""  # verbatim
    time_limit: Optional[float] = None


def _capacity(t) -> int:
    return t.total_capacity if t.total_capacity is not None else t.sw_capacity + t.so_capacity


def run_day_stages(instance: DayInstance, *, large_limit: Optional[int] = None, aggregate: bool = False,
                   max_cars: Optional[int] = None, fixed_type: Optional[str] = None,
                   minimised_type: Optional[str] = None, settings: Optional[HighsSettings] = None,
                   solve_stage: Optional[Callable[[JointModel, HighsSettings], StageSolve]] = None) -> DaySolveResult:
    """The lexicographic stages of one ready cell (design 1.3). ``solve_stage`` replaces HiGHS (tests, J5)."""
    settings = settings or HighsSettings()
    common = dict(solver="highs", solver_options=settings.option_string(), time_limit=settings.time_limit)
    if instance.status != READY:
        return DaySolveResult(status="input_rejected", note=f"day instance status {instance.status!r}", **common)
    types = instance.types
    typed = len(types) == 2
    fixed_id = minimised_id = None
    if typed:
        fixed_id, minimised_id = fixed_type, minimised_type
        if fixed_id is None and minimised_id is None:
            if _capacity(types[0]) <= _capacity(types[1]):
                raise ValueError("a typed day instance must list the larger (fixed) type first, or name fixed_type and "
                                 "minimised_type explicitly")
            fixed_id, minimised_id = types[0].type_id, types[1].type_id
        elif fixed_id is None or minimised_id is None:
            raise ValueError("name both fixed_type and minimised_type, or neither")
    version = None
    if solve_stage is None:
        available, version, reason = highs_probe()
        if not available:
            return DaySolveResult(status="backend_unavailable", note=reason, mode="typed" if typed else "homogeneous", **common)
        solve_stage = highs_solve_stage
    n_stages = 3 if typed else 2
    kw = dict(large_limit=large_limit, aggregate=aggregate, max_cars=max_cars, fixed_type=fixed_id, minimised_type=minimised_id)
    mode = "typed" if typed else "homogeneous"
    stages: list = []
    fixed: dict = {}
    non_lex = False
    for stage in range(1, n_stages + 1):
        model = build_joint_model(instance, stage=stage, fixed=dict(fixed), **kw)
        try:
            out = solve_stage(model, settings)
        except HighsBackendUnavailable as exc:
            return DaySolveResult(status="backend_unavailable", note=str(exc), mode=mode, stages=tuple(stages), **common)
        res = out.result
        if stage > 1:
            res = _replace(res, non_lexicographic=non_lex, k_fix=fixed["peak"])
        selection = selection_from_values(model, out.values) if out.values is not None and res.objective is not None else ()
        stages.append(DayStage(stage, model.name, model.objective_name, model.mps_sha256, res, dict(fixed), selection))
        if res.status == "infeasible_proven" and stage > 1:
            # an incumbent of the earlier stage is feasible for this one: infeasible here is a defect
            stages[-1] = DayStage(stage, model.name, model.objective_name, model.mps_sha256,
                                  _replace(res, status="rejected", stop_reason="solver_failure"), dict(fixed), selection)
            return _finish(mode, stages, version, common, note=f"stage {stage} infeasible after a stage {stage - 1} incumbent")
        if res.status not in _BOUND_STATUSES or res.objective is None:
            if res.status in _BOUND_STATUSES:  # bound only: later stages cannot be fixed
                for later in range(stage + 1, n_stages + 1):
                    stages.append(_skipped(later, "skipped_no_stage1_incumbent" if stage == 1 else "skipped_no_stage2_incumbent"))
            return _finish(mode, stages, version, common)
        non_lex = non_lex or res.status != "optimal"
        if stage == 1:
            fixed["peak"] = res.objective
        elif stage == 2:
            fixed["total_minutes"] = res.objective
    return _finish(mode, stages, version, common)


def _replace(res: StageResult, **changes) -> StageResult:
    import dataclasses

    return dataclasses.replace(res, **changes)


def _skipped(stage: int, status: str) -> DayStage:
    return DayStage(stage, "", "", "", StageResult(status=status), {})


def _finish(mode: str, stages: list, version: Optional[str], common: dict, note: str = "") -> DaySolveResult:
    results = [s.result for s in stages]
    first = results[0]
    if any(r.status == "rejected" for r in results):
        status = "rejected"
    elif first.status == "infeasible_proven":
        status = "infeasible_proven"
    elif first.status == "bound_only":
        status = "bound_only"
    elif all(r.status == "optimal" for r in results) and len(results) == (3 if mode == "typed" else 2):
        status = "optimal"
    else:
        status = "feasible_with_gap"
    complete = all(r.objective is not None for r in results) and len(results) == (3 if mode == "typed" else 2)
    objective = None
    if complete and status in ("optimal", "feasible_with_gap"):
        objective = tuple(r.objective for r in results)
    return DaySolveResult(status=status, mode=mode, note=note, stages=tuple(stages), objective=objective,
                          non_lexicographic=any(r.non_lexicographic for r in results),
                          timing_dependent=any(r.timing_dependent for r in results), solver_version=version, **common)
