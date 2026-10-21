"""Gurobi cross-check for the joint day model, reached through AMPL (WP-E11 J5, owner decision DECISION_LOG E14;
design JOINT_DAY_MODEL_DESIGN.md 2.4, 4.1-4.3).

* The cross-check solves the SAME ``JointModel`` object the HiGHS backend (J4) solves, stage by stage, through
  ``run_day_stages(..., solve_stage=...)``. AMPL does not read MPS, so one small generic sparse-MIP AMPL model
  (``DAY_MIP_MODEL``: integer variables with bounds, rows with a sense and a right-hand side, sparse integer
  coefficients, a linear objective) is loaded once per stage and fed through the amplpy data API; no model text is built
  per cell. ``readback_model`` reads every bound, cost, row, right-hand side and coefficient back from AMPL so a test can
  prove the AMPL side is the J3 model.
* ``amplpy`` is imported lazily (inside ``ampl_backend``), never at module import time; neither is ``highspy``. AMPL is
  found the way ``ampl_backend`` finds it (``UNIRIDE_AMPL_DIR``, the git-ignored local config, amplpy's default lookup).
  A missing amplpy, AMPL directory, Gurobi or licence gives a result with status ``backend_unavailable``; the public
  entry points do not raise it.
* Limits and determinism (design 4.2): threads 1, seed 0, MIP gap 0, absolute gap 0.99, time limit per call (default
  600 s), and a ``work_limit`` (Gurobi ``lim:work``, ``None`` by default; its value comes from the J10 calibration). The
  option string is built from the very list that is applied and stored verbatim. The Gurobi log is captured in memory
  only to read the work units; it is never stored or printed, and the first line of the solve message is scrubbed.
* Labels follow ``ampl_backend.classify_outcome`` (AMPL ``solve_result_num``: 0-99 solved, 100-199 solved?, 200-299
  infeasible, 300-399 unbounded, 400-449 limit with a solution, 450-499 limit without one, 500+ failure). Infeasible
  (200-299) is a proof because every variable is bounded; "infeasible or unbounded" is never accepted as a proof.
  A stage is ``optimal`` only if the runner's own check ``incumbent <= ceil(bound - 1e-6)`` holds, and the incumbent is
  recomputed in integers from the returned values after the same ``check_integer_solution`` re-check as the HiGHS path.
* ``crosscheck_day_results`` compares a HiGHS and a Gurobi ``DaySolveResult`` stage by stage. A disagreement in a proven
  value is ``blocking`` with both values; unproven, timing-dependent or non-lexicographic stages are ``inconclusive``,
  never agreement.

Offline research tooling: not imported by optimizer_api or src, not in the production registry. Imports nothing from
``academic_benchmark``.
"""
from __future__ import annotations

import dataclasses
import math
import re
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Tuple

from .ampl_backend import (
    _BOUND_SENTINEL,
    _BOUND_TOL,
    AmplSession,
    ExactBackendUnavailable,
    SolverSettings,
    StageResult,
    _scrub,
    backend_absent,
    classify_outcome,
    has_incumbent,
    reconcile_objective,
    snap_to_integer_data,
)
from .day_instance import READY, DayInstance
from .day_joint import JointModel
from .highs_backend import (
    BOUND_ABOVE_INCUMBENT,
    DEFAULT_TIME_LIMIT_SECONDS,
    DaySolveResult,
    DayStage,
    HighsBackendUnavailable,
    HighsSettings,
    StageSolve,
    check_integer_solution,
    run_day_stages,
)

SOLVER = "gurobi"
OBJECTIVE = "Obj"

# One generic sparse MIP, the same text for every cell and stage (no per-cell string building). Variables and rows are
# the zero-based indices of the J3 model; every variable is integer with explicit finite bounds.
DAY_MIP_MODEL = """\
set VARS;
set ROWS_E;
set ROWS_L;
set ROWS_G;
set NZ within {ROWS_E union ROWS_L union ROWS_G, VARS};
suffix bestbound OUT;
param lo {VARS} integer;
param hi {VARS} integer;
param obj {VARS} integer;
param rhs {ROWS_E union ROWS_L union ROWS_G} integer;
param coef {NZ} integer;
var x {v in VARS} integer >= lo[v], <= hi[v];
minimize Obj: sum {v in VARS} obj[v] * x[v];
subject to RowE {r in ROWS_E}: sum {(r, v) in NZ} coef[r, v] * x[v] = rhs[r];
subject to RowL {r in ROWS_L}: sum {(r, v) in NZ} coef[r, v] * x[v] <= rhs[r];
subject to RowG {r in ROWS_G}: sum {(r, v) in NZ} coef[r, v] * x[v] >= rhs[r];
"""


class GurobiBackendUnavailable(HighsBackendUnavailable):
    """amplpy, AMPL, Gurobi or its licence is missing (status ``backend_unavailable``).

    A subclass of the HiGHS runner's exception, so ``run_day_stages`` reports it instead of raising it.
    """


_AMPL_PRESOLVE_INFEASIBLE = "presolve finds no feasible solution"  # AMPL message, lower case
AMPL_PREFIX = "ampl:"  # options with this prefix are AMPL options, the rest are the Gurobi driver's options


@dataclass(frozen=True)
class GurobiSettings(HighsSettings):
    """Same fields as ``HighsSettings`` plus the Gurobi work limit; the option string is Gurobi's (through AMPL).

    ``ampl_presolve`` is the AMPL ``presolve`` option (default 0). With AMPL's own presolve on, AMPL itself settles a
    stage whose bounds and rows are inconsistent (message "presolve finds no feasible solution possible", result 299)
    and Gurobi never runs, so it would not be a second solver's proof. ``None`` makes this adapter set nothing: the
    session keeps whatever value of ``presolve`` was set in it last (AMPL's own default, on, only in a fresh session),
    so results may then depend on earlier calls in a reused session.
    """
    work_limit: Optional[float] = None
    ampl_presolve: Optional[int] = 0

    def options(self) -> Tuple[Tuple[str, object], ...]:
        """The options exactly as applied, in order: AMPL options (``ampl:`` prefix), then the Gurobi driver options
        (the names of ``ampl_backend.solver_option_string``)."""
        opts = []
        if self.ampl_presolve is not None:
            opts.append((AMPL_PREFIX + "presolve", int(self.ampl_presolve)))
        opts += [("mip:bestbound", 1), ("tech:threads", self.threads), ("tech:seed", self.seed),
                ("mip:gap", float(self.mip_gap)), ("mip:gapabs", float(self.mip_gap_abs)),
                ("lim:time", float(self.time_limit))]
        if self.work_limit is not None:
            opts.append(("lim:work", float(self.work_limit)))
        opts.append(("outlev", 1))  # the log is read for work units only, never stored
        return tuple(opts)

    @staticmethod
    def _format(key: str, val: object) -> str:
        return f"{key}={format(val, 'g') if isinstance(val, float) else val}"

    def ampl_options(self) -> Tuple[Tuple[str, object], ...]:
        return tuple((k[len(AMPL_PREFIX):], v) for k, v in self.options() if k.startswith(AMPL_PREFIX))

    def solver_options_string(self) -> str:
        """The ``gurobi_options`` string handed to AMPL (``option_string`` without the AMPL options)."""
        return " ".join(self._format(k, v) for k, v in self.options() if not k.startswith(AMPL_PREFIX))


# ---------------------------------------------------------------- session and probe
def open_session(settings: Optional[GurobiSettings] = None) -> AmplSession:
    """An open AMPL session that has solved a probe model with Gurobi. Raises ``GurobiBackendUnavailable`` only for absence."""
    settings = settings or GurobiSettings()
    session = AmplSession(SolverSettings(solver=SOLVER, threads=settings.threads, seed=settings.seed,
                                         mip_gap=settings.mip_gap, mip_gap_abs=settings.mip_gap_abs))
    try:
        session.open()
    except ExactBackendUnavailable as exc:
        raise GurobiBackendUnavailable(str(exc)) from exc
    return session


def gurobi_probe() -> Tuple[bool, Optional[str], str]:
    """(available, 'Gurobi x.y.z', reason): opens AMPL, solves a two-variable probe, stores no log."""
    try:
        session = open_session()
    except GurobiBackendUnavailable as exc:
        return False, None, str(exc)
    try:
        return True, session.solver_version, ""
    finally:
        session.close()


# ---------------------------------------------------------------- the J3 model in AMPL
def load_day_model(ampl, model: JointModel) -> None:
    """Replace the model of the AMPL session by ``DAY_MIP_MODEL`` filled with the stage's data (amplpy data API)."""
    variables, rows = model.variables, model.rows
    for ri, r in enumerate(rows):  # refuse before AMPL is touched: a dict would collapse a duplicate pair silently
        if r.sense not in ("E", "L", "G"):
            raise ValueError(f"row {r.name!r} has the sense {r.sense!r}, expected E, L or G")
        seen = set()
        for vi, _ in r.terms:
            if vi in seen:
                raise ValueError(f"row {r.name!r} lists variable index {vi} more than once")
            seen.add(vi)
    ampl.reset()
    ampl.eval(DAY_MIP_MODEL)
    ampl.set["VARS"] = list(range(len(variables)))
    for sense in ("E", "L", "G"):
        ampl.set[f"ROWS_{sense}"] = [i for i, r in enumerate(rows) if r.sense == sense]
    nonzeros = {(ri, vi): c for ri, r in enumerate(rows) for vi, c in r.terms}
    ampl.set["NZ"] = list(nonzeros)
    if variables:
        ampl.param["lo"] = {i: v.lower for i, v in enumerate(variables)}
        ampl.param["hi"] = {i: v.upper for i, v in enumerate(variables)}
        ampl.param["obj"] = {i: v.objective for i, v in enumerate(variables)}
    if rows:
        ampl.param["rhs"] = {i: r.rhs for i, r in enumerate(rows)}
    if nonzeros:
        ampl.param["coef"] = nonzeros


def readback_model(ampl) -> dict:
    """Everything the AMPL session holds about the loaded stage, read back from AMPL (not from the Python model)."""
    n_vars = int(round(float(ampl.get_value("card(VARS)"))))
    sizes = {s: int(round(float(ampl.get_value(f"card(ROWS_{s})")))) for s in "ELG"}
    n_nz = int(round(float(ampl.get_value("card(NZ)"))))
    variables = [(0, 0, 0)] * n_vars
    if n_vars:
        for i, lo, hi, obj in ampl.get_data("{v in VARS} (lo[v], hi[v], obj[v])").to_list():
            variables[int(i)] = (int(round(lo)), int(round(hi)), int(round(obj)))
    rows: dict = {}
    for sense in "ELG":
        if sizes[sense]:
            for r, rhs in ampl.get_data(f"{{r in ROWS_{sense}}} rhs[r]").to_list():
                rows[int(r)] = (sense, int(round(rhs)))
    coefficients = {}
    if n_nz:
        for r, v, c in ampl.get_data("{(r, v) in NZ} coef[r, v]").to_list():
            coefficients[(int(r), int(v))] = int(round(c))
    return {"n_variables": n_vars, "n_rows": sum(sizes.values()), "n_nonzeros": n_nz, "variables": variables,
            "rows": [rows[i] for i in sorted(rows)], "coefficients": coefficients}


# ---------------------------------------------------------------- outcome classification
def classify_gurobi_outcome(num: int, message: str, objective: Optional[float], bound: Optional[float]) -> StageResult:
    """Map AMPL ``solve_result_num`` and message of a Gurobi stage to the protocol labels (design 4).

    The bound goes through the same ``snap_to_integer_data`` rule as the HiGHS bound (a solver bound can sit a hair above an
    integer: 540.000003 is the integer 540, not the lower bound 541), and a bound that is still above the incumbent after
    the snap is clipped to it with the HiGHS note ``bound_above_incumbent`` in ``solver_message`` (J9b: the label then
    withholds the proof claim). The wave path (``classify_outcome``) is not snapped: its design rule is ``ceil(b - 1e-6)``.
    """
    msg = str(message).lower()
    if 200 <= num < 300 and "unbounded" not in msg:
        # AMPL's own phrase: AMPL settled it and Gurobi never ran (see GurobiSettings.ampl_presolve)
        return StageResult(status="infeasible_proven", stop_reason="infeasible",
                           bound_source="ampl_presolve" if _AMPL_PRESOLVE_INFEASIBLE in msg else None)
    if 200 <= num < 400:  # unbounded, or "infeasible or unbounded": no proof of anything
        return StageResult(status="rejected", stop_reason="solver_failure")
    _, bound = snap_to_integer_data(None, bound)
    out = classify_outcome(num, message, objective, bound)
    if out.objective is not None and out.bound is not None and out.bound_source == "solver":
        unclipped = max(0, math.ceil(out.bound - _BOUND_TOL))  # the ceiling rule of classify_outcome, before its clip
        if unclipped > out.objective:
            out = dataclasses.replace(out, solver_message=f"{BOUND_ABOVE_INCUMBENT}: ceil(bound - 1e-6)={unclipped} > "
                                                          f"incumbent={out.objective}; bound clipped to the incumbent")
    return out


def stage_solve_from_values(model: JointModel, out: StageResult, raw: Optional[Mapping[str, float]]) -> StageSolve:
    """The runner's own re-check of a classified stage: integer values, bounds, rows and the recomputed objective.

    ``out`` carries the solver's classification and objective; with an incumbent the values must pass
    ``check_integer_solution`` and their recomputed objective must equal the solver's, else the stage is ``rejected``.
    """
    if out.objective is None:
        return StageSolve(out)
    checked = check_integer_solution(model, raw) if raw is not None else None
    if checked is None or checked[1] != out.objective:
        return StageSolve(dataclasses.replace(out, status="rejected", stop_reason="solver_failure"))
    values, objective = checked
    return StageSolve(dataclasses.replace(out, objective=objective), values)


# ---------------------------------------------------------------- one stage on Gurobi
def _is_session_error(exc: BaseException) -> bool:
    """An error of the AMPL process or its connection (amplpy ``AMPLException``, broken pipe), not of our data."""
    return isinstance(exc, (OSError, EOFError)) or any(c.__name__ == "AMPLException" for c in type(exc).__mro__)


def gurobi_solve_stage(session: AmplSession, model: JointModel, settings: Optional[GurobiSettings] = None) -> StageSolve:
    """One stage as one Gurobi call through the open AMPL session.

    Raises ``GurobiBackendUnavailable`` (which ``run_day_stages`` reports as ``backend_unavailable``, never raising it
    to the caller) when the AMPL session fails during the solve (amplpy ``AMPLException``, a broken pipe) or when the
    solver result is a failure (500 or more) whose message or log names a missing solver or licence. Any other failure
    is a defect and propagates; a failure without that evidence is ``rejected``.
    """
    settings = settings or GurobiSettings()
    ampl = session.ampl
    load_day_model(ampl, model)
    ampl.option["solver"] = SOLVER
    for key, val in settings.ampl_options():
        ampl.option[key] = val
    ampl.option[f"{SOLVER}_options"] = settings.solver_options_string()
    ampl.eval(f"let {OBJECTIVE}.bestbound := {_BOUND_SENTINEL:g};")  # no earlier bound can leak into this stage
    session._log.clear()
    t0 = time.perf_counter()
    try:
        ampl.solve()
    except Exception as exc:  # noqa: BLE001 - classified below
        if _is_session_error(exc):
            # the exception type only, as ampl_backend.open does: the text can carry licence or path details
            raise GurobiBackendUnavailable(f"AMPL session failed during a stage: {type(exc).__name__}") from exc
        raise
    seconds = time.perf_counter() - t0
    num = int(ampl.get_value("solve_result_num"))
    message = str(ampl.get_value("solve_message"))
    log = "\n".join(session._log)  # read for work units only, never stored
    session._log.clear()
    if num >= 500 and backend_absent(SOLVER, f"{message}\n{log}"):
        raise GurobiBackendUnavailable(f"{SOLVER}: solver or license missing")
    objective = ampl.get_objective(OBJECTIVE).value()
    bound_value = float(ampl.get_value(f"{OBJECTIVE}.bestbound"))
    bound = None if bound_value <= _BOUND_SENTINEL / 10 else bound_value
    raw = None
    if has_incumbent(num) and objective is not None and math.isfinite(float(objective)):
        values = ampl.var["x"].get_values().to_dict()
        raw = {v.name: float(values[i]) for i, v in enumerate(model.variables)}
        # integrality is a test of the values (J11): the raw objective of near-integral values need not be integral
        objective = reconcile_objective(objective, [v.objective for v in model.variables],
                                        [raw[v.name] for v in model.variables])
    out = classify_gurobi_outcome(num, message, objective, bound)
    if out.objective is None:
        raw = None
    work = None
    found = re.findall(r"\(([\d.]+) work units\)", log)
    if found:
        work = float(found[-1])
    first = _scrub(message.splitlines()[0]) if message else ""
    out = dataclasses.replace(out, solve_result=str(ampl.solve_result), solve_result_num=num, solver_message=f"{out.solver_message}; {first}" if out.solver_message else first,
                              wall_seconds=round(seconds, 4), work_units=work, time_limit=settings.time_limit,
                              work_limit=settings.work_limit)
    return stage_solve_from_values(model, out, raw)


# ---------------------------------------------------------------- day runner
def run_day_stages_gurobi(instance: DayInstance, *, large_limit: Optional[int] = None, aggregate: bool = False,
                          max_cars: Optional[int] = None, fixed_type: Optional[str] = None,
                          minimised_type: Optional[str] = None, settings: Optional[GurobiSettings] = None,
                          session: Optional[AmplSession] = None,
                          stage_solver: Optional[Callable[[JointModel, HighsSettings], StageSolve]] = None) -> DaySolveResult:
    """The lexicographic stages of one ready cell on Gurobi; same runner, same checks and labels as the HiGHS path.

    ``session`` is an open AMPL session to reuse (``open_session``); without it one is opened and closed here. Never
    raises for an absent backend. ``stage_solver`` replaces the stage call (tests).
    """
    settings = settings or GurobiSettings()
    mode = "typed" if len(instance.types) == 2 else "homogeneous"
    kw = dict(large_limit=large_limit, aggregate=aggregate, max_cars=max_cars, fixed_type=fixed_type,
              minimised_type=minimised_type, settings=settings)
    owned = None
    try:
        if instance.status != READY:
            return _as_gurobi(run_day_stages(instance, **kw), None)
        if session is None and stage_solver is None:
            try:
                session = owned = open_session(settings)
            except GurobiBackendUnavailable as exc:
                return DaySolveResult(status="backend_unavailable", note=str(exc), mode=mode, solver=SOLVER,
                                      solver_options=settings.option_string(), time_limit=settings.time_limit)
        solve = stage_solver or (lambda model, s: gurobi_solve_stage(session, model, settings))
        version = getattr(session, "solver_version", None)
        return _as_gurobi(run_day_stages(instance, solve_stage=solve, **kw), version)
    finally:
        if owned is not None:
            owned.close()


def _as_gurobi(result: DaySolveResult, version: Optional[str]) -> DaySolveResult:
    return dataclasses.replace(result, solver=SOLVER, solver_version=version)


# ---------------------------------------------------------------- cross-check of two solvers
AGREE, BLOCKING, INCONCLUSIVE = "agree", "blocking", "inconclusive"
_LABELS = {AGREE: "crosscheck: agree", BLOCKING: "crosscheck: BLOCKING", INCONCLUSIVE: "crosscheck: inconclusive"}
_PROVEN = ("optimal", "infeasible_proven")


@dataclass(frozen=True)
class StageCrossCheck:
    stage: int
    verdict: str  # agree, blocking or inconclusive
    detail: str


@dataclass(frozen=True)
class CrossCheck:
    verdict: str
    stages: Tuple[StageCrossCheck, ...] = ()
    note: str = ""

    @property
    def label(self) -> str:
        return _LABELS[self.verdict]


def _describe(name: str, r: StageResult) -> str:
    return (f"{name}: {r.status}" + (f" objective {r.objective}" if r.objective is not None else "")
            + (f" bound_ceil {r.bound_ceil}" if r.bound_ceil is not None else ""))


def _compare_stage(index: int, a: DayStage, b: DayStage, names: Tuple[str, str]) -> StageCrossCheck:
    ra, rb = a.result, b.result
    na, nb = names
    both = f"{_describe(na, ra)}; {_describe(nb, rb)}"
    # facts that hold whatever the stage inputs were: a verified feasible plan against a proof
    if ra.status == "infeasible_proven" and rb.objective is not None:
        return StageCrossCheck(index, BLOCKING, f"{na} proves infeasible but {nb} has a verified plan; {both}")
    if rb.status == "infeasible_proven" and ra.objective is not None:
        return StageCrossCheck(index, BLOCKING, f"{nb} proves infeasible but {na} has a verified plan; {both}")
    if a.fixed == b.fixed:
        for x, y, nx, ny in ((ra, rb, na, nb), (rb, ra, nb, na)):
            if x.objective is not None and y.bound_ceil is not None and x.objective < y.bound_ceil:
                return StageCrossCheck(index, BLOCKING, f"{nx} has a plan below the lower bound proven by {ny}; {both}")
        if ra.status == "optimal" and rb.status == "optimal" and ra.objective != rb.objective:
            return StageCrossCheck(index, BLOCKING, f"proven optimal values differ; {both}")
        if ra.status in _PROVEN and rb.status in _PROVEN and ra.status != rb.status:
            return StageCrossCheck(index, BLOCKING, f"one solver proves optimal and the other infeasible; {both}")
        if ra.bound_source == "ampl_presolve" or rb.bound_source == "ampl_presolve":
            return StageCrossCheck(index, INCONCLUSIVE, f"settled by AMPL presolve, not proven by the solver; {both}")
        if (ra.status in _PROVEN and rb.status in _PROVEN and not (ra.timing_dependent or rb.timing_dependent
                                                                    or ra.non_lexicographic or rb.non_lexicographic)):
            return StageCrossCheck(index, AGREE, both)
        return StageCrossCheck(index, INCONCLUSIVE, f"not both proven, or timing-dependent or non-lexicographic; {both}")
    return StageCrossCheck(index, INCONCLUSIVE, f"the stage inputs differ ({na} {dict(a.fixed)}, {nb} {dict(b.fixed)}); {both}")


def crosscheck_day_results(highs: DaySolveResult, gurobi: DaySolveResult) -> CrossCheck:
    """Compare two day results stage by stage (see the module docstring). Parameter order only names the sides."""
    names = (highs.solver or "highs", gurobi.solver or "gurobi")
    if names[0] == names[1]:
        names = ("first", "second")
    for res in (highs, gurobi):
        if res.status in ("backend_unavailable", "input_rejected"):
            return CrossCheck(INCONCLUSIVE, note=f"{res.solver}: {res.status}")
    stages = []
    for i in range(max(len(highs.stages), len(gurobi.stages))):
        if i >= len(highs.stages) or i >= len(gurobi.stages):
            stages.append(StageCrossCheck(i + 1, INCONCLUSIVE, "stage missing on one side"))
            continue
        a, b = highs.stages[i], gurobi.stages[i]
        if any(r.status not in _PROVEN + ("feasible_with_gap", "bound_only") for r in (a.result, b.result)):
            # skipped, rejected or not run: a failed stage is neither agreement nor a disagreement of proven values
            verdict = _compare_stage(i + 1, a, b, names)
            if verdict.verdict == BLOCKING:
                stages.append(verdict)
            else:
                stages.append(StageCrossCheck(i + 1, INCONCLUSIVE, f"{_describe(names[0], a.result)}; {_describe(names[1], b.result)}"))
            continue
        stages.append(_compare_stage(i + 1, a, b, names))
    if any(s.verdict == BLOCKING for s in stages):
        verdict = BLOCKING
    elif stages and all(s.verdict == AGREE for s in stages) and len(highs.stages) == len(gurobi.stages):
        verdict = AGREE
    else:
        verdict = INCONCLUSIVE
    return CrossCheck(verdict, tuple(stages))
