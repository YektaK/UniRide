"""AMPL backend for the set-partitioning wave model (design EXACT_SOLVER_AMPL_DESIGN.md
sections 1.1 Step B, 1.2, 2, 4, 7; WP-E2).

* ``amplpy`` is an optional extra (``requirements-exact.txt``) and is imported lazily, never at
  module import time. AMPL is found through ``UNIRIDE_AMPL_DIR``, else the git-ignored local file
  ``ampl_local.json`` next to this module (``{"ampl_dir": "..."}``), else amplpy's own default
  lookup. No path is hard-coded and none is recorded: results say only
  "local AMPL installation used" (or "amplpy default lookup").
* A missing amplpy, AMPL installation or solver license gives a result with status
  ``backend_unavailable``; public entry points never raise ``ExactBackendUnavailable`` into
  callers.
* Data go through the amplpy API (no temporary ``.dat``). Two lexicographic stages: stage 1
  minimises K (or K_m), stage 2 minimises D with the stage-1 value fixed; an optional third call
  gives ``D_LB_free``. Each call has its own wall limit (60 s, 600 s on a peak wave, D-C) and,
  for Gurobi, a deterministic work limit; threads 1 and a fixed seed (section 4).
* Option names are the fully qualified AMPL MP names confirmed in WP-E2 (F17); the bare
  ``bestbound=1`` is never used. The solver log is parsed for Gurobi work units only and is never
  stored (it can carry license text).

Offline research tooling: not imported by optimizer_api or src, not in the production registry.
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import platform
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Tuple

ENV_VAR = "UNIRIDE_AMPL_DIR"
LOCAL_CONFIG_PATH = Path(__file__).with_name("ampl_local.json")
LOCATION_LABELS = {"env": "local AMPL installation used", "local_config": "local AMPL installation used",
                   "amplpy_default": "amplpy default lookup"}

DEFAULT_WALL_LIMIT_SECONDS = 60  # owner decision EQ1 / D-C: per solver call
PEAK_WALL_LIMIT_SECONDS = 600  # every call on a peak wave (D-B)
# Gurobi deterministic work limit (work units), the primary stop (section 4): owner decision
# 2026-10-16 (DECISION_LOG E03). The WP-E2 calibration (max 1.64 work units on the GOAL 1 grid,
# docs/paper/results/week-2026-10-05-exact/wp-e2-calibration/) is far below either value.
DEFAULT_WORK_LIMIT = 20.0
PEAK_WORK_LIMIT = 200.0
MIP_GAP = 0.0
MIP_GAP_ABS = 0.99  # integer objectives: incumbent - bound < 1 proves optimality
SUPPORTED_SOLVERS = ("gurobi", "highs", "cplex", "copt")
_WORK_LIMIT_SOLVERS = frozenset({"gurobi"})  # confirmed `lim:work` (F17); HiGHS has none
_SEED_OPTION = {"gurobi": "tech:seed", "highs": "tech:seed", "cplex": "tech:seed", "copt": None}  # COPT 8.0.6 refuses tech:seed
_LOG_OPTION = {"gurobi": "outlev=1"}  # log parsed for work units only, never stored
_HUGE = 1e20
# A solver returns an integer variable within its integrality tolerance (Gurobi IntFeasTol default
# 1e-5; HiGHS mip_feasibility_tolerance default 1e-6), so incumbents and lam values are rounded
# with the looser 1e-5. The bound rounding ceil(b - 1e-6) is the design's rule (section 1.2).
_INT_TOL = 1e-5
_BOUND_TOL = 1e-6
# Stops that depend on machine speed (owner decision 2026-10-16, E03: other_limit counts as timing-dependent).
_TIMING_REASONS = ("wall_limit", "other_limit")
_BOUND_SENTINEL = -1e30  # written into .bestbound before every solve; read back as "no bound"
# A missing license (backend_unavailable), as opposed to a backend defect; see backend_absent().
_LICENSE_ABSENT = re.compile(r"licen[cs]e (not found|expired|invalid|error)|\bno\b.*licen[cs]e", re.I)
STAGES = ("stage1", "stage2", "free")


def snap_to_integer_data(objective: Optional[float], bound: Optional[float], rel_tol: float = 1e-6, abs_cap: float = 0.25,
                         bound_rel_tol: float = 1e-8) -> Tuple[Optional[float], Optional[float]]:
    """Remove solver floating-point noise from an objective and a bound of a model with integer data (WP-E7).

    A MIP solver keeps its integer variables within an integrality tolerance, so with large integer costs the reported
    objective can sit a little off an integer (HiGHS 1.15.1 reported 106739.9999 for an objective of 106740 on pr76).
    The objective is snapped to the nearest integer when it is within ``min(rel_tol * |objective|, abs_cap)`` of it; a
    genuinely fractional value is left alone, so ``classify_outcome`` still rejects it. The bound is lowered by the
    relative noise allowance, so a bound just above an integer is not rounded up past the true bound; the lowering is
    far below 1, so a bound that proves optimality (incumbent minus bound below 1) still does.
    """
    obj = objective
    if objective is not None and math.isfinite(float(objective)) and abs(float(objective)) < _HUGE:
        nearest = round(float(objective))
        if abs(float(objective) - nearest) <= min(rel_tol * max(1.0, abs(float(objective))), abs_cap):
            obj = float(nearest)
    b = bound
    if bound is not None and math.isfinite(float(bound)) and abs(float(bound)) < _HUGE:
        b = float(bound) - max(0.0, bound_rel_tol * abs(float(bound)) - _BOUND_TOL)
    return obj, b


_OBJECTIVE_ALLOWANCE_CAP = 0.25  # below one half: an accepted objective is always the integer nearest to the solver's


def reconcile_objective(objective: Optional[float], coefficients: Sequence[float], values: Sequence[float]) -> Optional[float]:
    """Return the integer objective of the ROUNDED variable values when it explains the solver's raw objective, else ``objective``.

    A MIP solver keeps every integer variable within its integrality tolerance, not at an integer, so the objective it
    reports is the objective of slightly off-integer values. Several small deviations add up through large integer
    coefficients: J11 stage 3 (Gurobi) returned 539.9999877 with every value within 1.3e-6 of an integer, which is
    1.2e-5 from 540. Integrality is therefore a test of the VALUES; the raw objective is never required to be integral.

    The values pass when each is finite and within ``_INT_TOL`` of an integer. The objective is then recomputed from the
    rounded values (an integer, with integer coefficients). It replaces the solver's objective only when the two agree
    within the amount the deviations explain: the objective of the raw values and that of the rounded values differ by
    exactly ``sum(c_j * (x_j - round(x_j)))``, so the allowance is ``sum(|c_j| * |x_j - round(x_j)|)`` plus a floating-
    point margin (``_BOUND_TOL`` plus 1e-9 relative), capped at 0.25 so that it can never reach another integer. A real
    mismatch (a deviation beyond the variable tolerance, an objective that the values do not produce, or a coefficient
    that is not an integer) returns the raw
    objective unchanged, so the existing rejection (non-integral objective in ``classify_outcome``, the runner's
    recomputed-objective check) still applies. Whenever the objective is accepted here it equals ``round(objective)``,
    so a result that was accepted before is accepted with the same value.
    """
    if objective is None or not math.isfinite(float(objective)) or abs(float(objective)) >= _HUGE:
        return objective
    if len(coefficients) != len(values):
        raise ValueError("coefficients and values differ in length")
    if any(not float(c).is_integer() for c in coefficients):
        return objective  # the recomputed value is an integer only for integer coefficients (the exact models have them)
    recomputed, explained = 0, 0.0
    for c, x in zip(coefficients, values):
        x = float(x)
        if not math.isfinite(x) or abs(x - round(x)) > _INT_TOL:
            return objective
        recomputed += int(round(c)) * int(round(x))
        explained += abs(float(c)) * abs(x - round(x))
    allowance = min(explained + _BOUND_TOL + 1e-9 * abs(float(objective)), _OBJECTIVE_ALLOWANCE_CAP)
    return float(recomputed) if abs(float(objective) - recomputed) <= allowance else objective


def has_incumbent(num: int) -> bool:
    """True when AMPL ``solve_result_num`` means the solver returned a solution (solved, solved?, or a limit with one)."""
    return num < 200 or 400 <= num < 450


class ExactBackendUnavailable(RuntimeError):
    """amplpy, AMPL or a solver license is missing (status ``backend_unavailable``)."""


def backend_absent(solver: str, text: str) -> bool:
    """True only for a missing solver binary (phrases anchored to ``solver``) or a missing license.

    Used on the open/probe path and on the stage path (the Gurobi day backend, WP-E11 J5), and only on
    an exception text, or on the solve message and the solver output (the solve command's own output
    or the captured log) when ``solve_result_num >= 500``. Anything else that mentions "can't find"
    or "licen" (a normal start-up log names the licence) is a backend defect and must fail, not skip.
    """
    name = re.escape(solver)
    missing = re.compile(rf"can.t find (file )?\W?{name}\b|cannot invoke {name}\b", re.I)
    return bool(missing.search(text) or _LICENSE_ABSENT.search(text))


@dataclass(frozen=True)
class SolverSettings:
    solver: str = "gurobi"
    threads: int = 1
    seed: int = 0
    mip_gap: float = MIP_GAP
    mip_gap_abs: float = MIP_GAP_ABS
    wall_limit: float = DEFAULT_WALL_LIMIT_SECONDS
    peak_wall_limit: float = PEAK_WALL_LIMIT_SECONDS
    work_limit: Optional[float] = DEFAULT_WORK_LIMIT
    peak_work_limit: Optional[float] = PEAK_WORK_LIMIT

    def __post_init__(self) -> None:
        if self.solver not in SUPPORTED_SOLVERS:
            raise ValueError(f"solver must be one of {SUPPORTED_SOLVERS}")

    def wall(self, peak: bool) -> float:
        return self.peak_wall_limit if peak else self.wall_limit

    def work(self, peak: bool) -> Optional[float]:
        if self.solver not in _WORK_LIMIT_SOLVERS:
            return None
        return self.peak_work_limit if peak else self.work_limit


def wall_limit_seconds(peak: bool, settings: Optional[SolverSettings] = None) -> float:
    return (settings or SolverSettings()).wall(peak)


def solver_option_string(settings: SolverSettings, *, peak: bool) -> str:
    """The verbatim ``<solver>_options`` string (recorded in the manifest)."""
    opts = ["mip:bestbound=1", f"tech:threads={settings.threads}"]
    if _SEED_OPTION[settings.solver]:
        opts.append(f"{_SEED_OPTION[settings.solver]}={settings.seed}")
    opts += [f"mip:gap={settings.mip_gap:g}", f"mip:gapabs={settings.mip_gap_abs:g}", f"lim:time={settings.wall(peak):g}"]
    work = settings.work(peak)
    if work is not None:
        opts.append(f"lim:work={work:g}")
    if settings.solver in _LOG_OPTION:
        opts.append(_LOG_OPTION[settings.solver])
    return " ".join(opts)


def locate_ampl(environ: Optional[Mapping[str, str]] = None, config_path: Optional[Path] = None) -> Tuple[Optional[str], str]:
    """(directory or None, source): ``UNIRIDE_AMPL_DIR``, else the local config, else amplpy default."""
    env = os.environ if environ is None else environ
    if env.get(ENV_VAR):
        return env[ENV_VAR], "env"
    cfg = LOCAL_CONFIG_PATH if config_path is None else Path(config_path)
    if cfg.is_file():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8")).get("ampl_dir")
        except (OSError, ValueError, AttributeError):
            value = None
        if value:
            return str(value), "local_config"
    return None, "amplpy_default"


def model_path() -> Path:
    """``wave_sp.mod`` shipped as package data."""
    from importlib import resources

    return Path(str(resources.files("uniride_core.exact").joinpath("models", "wave_sp.mod")))


def _scrub(text: str) -> str:
    return "\n".join("<scrubbed>" if re.search(r"@|licen|registered|expire", ln, re.I) else ln
                     for ln in str(text).splitlines())


# ---------------------------------------------------------------- outcome classification
@dataclass(frozen=True)
class StageResult:
    stage: str = ""
    status: str = "not_run"
    stop_reason: Optional[str] = None  # optimal, work_limit, wall_limit, infeasible, gap_tolerance, solver_failure
    timing_dependent: bool = False
    non_lexicographic: bool = False
    objective: Optional[int] = None  # incumbent value (integer)
    bound: Optional[float] = None  # solver best bound (raw), None if absent/infinite
    bound_ceil: Optional[int] = None  # ceil(bound - 1e-6), or the trivial bound 0
    bound_source: Optional[str] = None  # "solver", "ampl_presolve" (all variables fixed) or "trivial_zero"
    k_fix: Optional[int] = None
    solve_result: Optional[str] = None
    solve_result_num: Optional[int] = None
    solver_message: Optional[str] = None  # first line, scrubbed
    wall_seconds: Optional[float] = None
    work_units: Optional[float] = None  # Gurobi log, else None
    time_limit: Optional[float] = None
    work_limit: Optional[float] = None
    selection: tuple = ()  # ((column index, times), ...) of the incumbent


def classify_outcome(num: int, message: str, objective: Optional[float], bound: Optional[float]) -> StageResult:
    """Map AMPL ``solve_result_num``/``solve_message`` to the protocol labels (section 4).

    AMPL MP codes: 0-99 solved, 100-199 solved?, 200-299 infeasible, 300-399 unbounded,
    400-449 limit with a feasible solution, 450-499 limit without one, 500+ failure.
    """
    msg = str(message).lower()
    limit = "work_limit" if "work limit" in msg else ("wall_limit" if "time limit" in msg else "other_limit")
    if 200 <= num < 300:
        return StageResult(status="infeasible_proven", stop_reason="infeasible")
    if num >= 500 or 300 <= num < 400:
        return StageResult(status="rejected", stop_reason="solver_failure")
    b = None
    if bound is not None and math.isfinite(float(bound)) and abs(float(bound)) < _HUGE:
        b = float(bound)
    # every objective coefficient is >= 0 and lam >= 0, so 0 is always a valid bound
    b_ceil, source = (max(0, math.ceil(b - _BOUND_TOL)), "solver") if b is not None else (0, "trivial_zero")
    if num < 100 and "determined by presolve" in msg and objective is not None:
        # AMPL presolve fixed every variable (the solver did not run, so any .bestbound suffix is stale):
        # the feasible set is that single point and its value is exact
        b = float(objective)
        b_ceil, source = math.ceil(b - _BOUND_TOL), "ampl_presolve"
    inc = None
    if has_incumbent(num):
        if objective is None or not math.isfinite(float(objective)) or abs(objective - round(objective)) > _INT_TOL:
            return StageResult(status="rejected", stop_reason="solver_failure", bound=b)
        inc = int(round(objective))
        b_ceil = min(b_ceil, inc)
    if num < 100 and inc - b_ceil < 1:
        status, reason = "optimal", "optimal"
    elif num < 200:
        status, reason = "feasible_with_gap", "gap_tolerance"
    elif num < 450:
        status, reason = "feasible_with_gap", limit
    else:
        status, reason = "bound_only", limit
    return StageResult(status=status, stop_reason=reason, timing_dependent=reason in _TIMING_REASONS,
                       objective=inc, bound=b, bound_ceil=b_ceil, bound_source=source)


_BOUND_STATUSES = ("optimal", "feasible_with_gap", "bound_only")


def run_stages(call: Callable[[str, Optional[int]], StageResult], *, d_lb_free: bool = True) -> dict:
    """Lexicographic two-stage driver (section 1.1). ``call(stage, k_fix)`` performs one solver call."""
    s1 = dataclasses.replace(call("stage1", None), stage="stage1")
    out = dict(stage1=s1, stage2=None, free=None, k_lb_solver=None, k_lb_solver_source=None, d_lb=None,
               d_lb_free=None, non_lexicographic=False)
    if s1.status not in _BOUND_STATUSES:
        return out
    out["k_lb_solver"] = s1.bound_ceil
    out["k_lb_solver_source"] = s1.bound_source
    if s1.objective is None:
        out["stage2"] = StageResult(stage="stage2", status="skipped_no_stage1_incumbent")
    else:
        nonlex = s1.status != "optimal"
        s2 = dataclasses.replace(call("stage2", s1.objective), stage="stage2", non_lexicographic=nonlex, k_fix=s1.objective)
        out["stage2"] = s2
        out["non_lexicographic"] = nonlex
        if not nonlex and s2.status in _BOUND_STATUSES:
            out["d_lb"] = s2.bound_ceil  # conditional on K = K* (section 1.2)
    if d_lb_free:
        f = dataclasses.replace(call("free", None), stage="free")
        out["free"] = f
        if f.status in _BOUND_STATUSES:
            out["d_lb_free"] = f.bound_ceil
    return out


# ---------------------------------------------------------------- column expansion (E02)
@dataclass(frozen=True)
class ExpandedRoute:
    type_id: str
    column_index: int
    copy: int  # 0..k-1 for a column selected k times
    occurrence_ids: tuple  # visiting order
    cost: int
    ride: int
    tour: int


def expand_selection(enumeration, selection: Sequence[Tuple[int, int]], occurrence_ids: Optional[Sequence] = None) -> tuple:
    """Selected columns -> routes with occurrence ids (section 1.1, DECISION_LOG E02).

    Occurrences of each (location, class) item are taken in sorted id order and handed to the
    selected columns in column order; a column selected ``k`` times becomes ``k`` routes with the
    same stop order, each copy taking its own next ``a_{r,item}`` occurrences.
    """
    items = enumeration.items
    n = sum(it.multiplicity for it in items)
    ids = tuple(range(1, n + 1)) if occurrence_ids is None else tuple(occurrence_ids)
    pools = [deque(sorted(ids[nd - 1] for nd in it.nodes)) for it in items]
    use = [0] * len(items)
    for r, times in selection:
        if not (0 <= r < len(enumeration.columns)) or times <= 0:
            raise ValueError(f"invalid selection entry ({r}, {times})")
        for i, a in enumerate(enumeration.columns[r].multiplicity):
            use[i] += a * times
    if use != [it.multiplicity for it in items]:
        raise ValueError(f"selection does not cover every occurrence exactly once: {use}")
    routes = []
    for r, times in sorted(selection):
        col = enumeration.columns[r]
        for copy in range(times):
            take = {i: [pools[i].popleft() for _ in range(a)] for i, a in enumerate(col.multiplicity) if a}
            seen = [0] * len(items)
            seq = []
            for it in col.stop_order:
                seq.append(take[it][seen[it]])
                seen[it] += 1
            routes.append(ExpandedRoute(col.type_id, r, copy, tuple(seq), col.cost, col.ride, col.tour))
    return tuple(routes)


# ---------------------------------------------------------------- result
@dataclass(frozen=True)
class SPSolveResult:
    wave_id: str
    status: str
    note: str = ""
    stage1: Optional[StageResult] = None
    stage2: Optional[StageResult] = None
    free: Optional[StageResult] = None
    k: Optional[int] = None  # K (single type) or K_m (typed: routes of the minimised type only) of the reported routes
    d: Optional[int] = None
    k_lb: Optional[int] = None
    k_lb_source: Optional[str] = None
    d_lb: Optional[int] = None
    d_lb_free: Optional[int] = None
    non_lexicographic: bool = False
    selection: tuple = ()
    routes: tuple = ()
    peak: bool = False
    column_count: Optional[int] = None
    solver: Optional[str] = None
    solver_version: Optional[str] = None
    ampl_version: Optional[str] = None
    amplpy_version: Optional[str] = None
    ampl_location: Optional[str] = None
    option_string: Optional[str] = None
    threads: Optional[int] = None
    seed: Optional[int] = None
    wall_limit_seconds: Optional[float] = None
    work_limit: Optional[float] = None

    def to_exact_result(self):
        from .wave_instance import ExactResult

        last = self.stage2 if self.stage2 is not None and self.stage2.objective is not None else self.stage1
        return ExactResult(self.wave_id, self.status, tuple(r.occurrence_ids for r in self.routes),
                           None if self.k is None else len(self.routes), self.d,
                           stop_reason=None if last is None else last.stop_reason,
                           timing_dependent=any(s is not None and s.timing_dependent for s in (self.stage1, self.stage2, self.free)),
                           non_lexicographic=self.non_lexicographic, k_lb=self.k_lb, d_lb=self.d_lb, d_lb_free=self.d_lb_free)


def _unavailable(wave_id: str, note: str, peak: bool = False) -> SPSolveResult:
    return SPSolveResult(wave_id, "backend_unavailable", note=note, peak=peak)


_K_LB_SOURCES = {"solver": "solver_bound", "ampl_presolve": "ampl_presolve", "trivial_zero": "trivial_zero"}


def _k_lower_bound(enumeration, k_lb_solver: Optional[int], single_type: bool,
                   bound_source: Optional[str] = "solver") -> Tuple[Optional[int], Optional[str]]:
    """Section 1.2: single type max(solver bound, capacity floors, clique floor); typed: solver bound.

    The source names where the maximum comes from: ``solver_bound``, ``ampl_presolve`` (AMPL settled
    the model), ``trivial_zero`` (no solver bound; 0 is valid because lam >= 0), ``capacity_floor``
    or ``clique_floor``.
    """
    if k_lb_solver is None:
        return None, None
    best, source = k_lb_solver, _K_LB_SOURCES.get(bound_source or "solver", "solver_bound")
    if single_type:
        from .route_enumeration import clique_floor

        t = enumeration.types[0]
        sw = sum(it.multiplicity for it in enumeration.items if it.cls == "Sw")
        so = sum(it.multiplicity for it in enumeration.items if it.cls == "So")
        floors = []
        if sw and t.sw_capacity:
            floors.append(math.ceil(sw / t.sw_capacity))
        if so and t.so_capacity:
            floors.append(math.ceil(so / t.so_capacity))
        if t.total_capacity:
            floors.append(math.ceil((sw + so) / t.total_capacity))
        cap = max(floors, default=0)
        if cap > best:
            best, source = cap, "capacity_floor"
        clique = clique_floor(enumeration)[0]
        if clique > best:
            best, source = clique, "clique_floor"
    return best, source


class AmplSession:
    """One AMPL process reused across solves (tests and calibration). Raises
    ``ExactBackendUnavailable`` from ``open``; use ``solve_columns`` for the non-raising API."""

    def __init__(self, settings: Optional[SolverSettings] = None, environ: Optional[Mapping[str, str]] = None):
        self.settings = settings or SolverSettings()
        self._environ = environ
        self._ampl = None
        self._objective_coefficients: dict = {}  # set by _load
        self._log: list = []
        self.ampl_version = self.amplpy_version = self.location = self.solver_version = None

    def __enter__(self) -> "AmplSession":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self) -> None:
        try:
            import amplpy
        except ImportError as exc:
            raise ExactBackendUnavailable("amplpy is not installed (optional extra requirements-exact.txt)") from exc
        directory, source = locate_ampl(self._environ)
        where = {"env": ENV_VAR, "local_config": "the local AMPL config file", "amplpy_default": "amplpy default lookup"}[source]
        if directory is not None:
            d = Path(directory)
            if not ((d / "ampl.exe").is_file() or (d / "ampl").is_file()):
                raise ExactBackendUnavailable(f"no AMPL executable in the directory named by {where}")
        session = self

        class _Out:
            def output(self, kind, msg):
                session._log.append(msg)

        class _Err:
            def error(self, exc):
                raise exc

            def warning(self, exc):
                session._log.append(str(exc))

        try:
            ampl = amplpy.AMPL(amplpy.Environment(directory)) if directory is not None else amplpy.AMPL()
            ampl.set_output_handler(_Out())
            ampl.set_error_handler(_Err())
            version = str(ampl.get_option("version") or "").splitlines()
        except Exception as exc:  # noqa: BLE001 - any start-up failure means the backend is unavailable
            raise ExactBackendUnavailable(f"AMPL could not start via {where}: {type(exc).__name__}") from exc
        self._ampl = ampl
        self.ampl_version = version[0].strip() if version else None
        self.amplpy_version = getattr(amplpy, "__version__", None)
        self.location = LOCATION_LABELS[source]
        self.solver_version = self._solver_version()

    def _solver_version(self) -> Optional[str]:
        """'<Solver> x.y.z' from a two-variable solve the AMPL presolve cannot settle (license check too)."""
        a = self._ampl
        a.reset()
        a.eval("var x {1..2} binary; minimize o: x[1] + 2 * x[2]; subject to c: x[1] + x[2] >= 1;")
        a.option["solver"] = self.settings.solver
        a.option[f"{self.settings.solver}_options"] = solver_option_string(self.settings, peak=False)
        solver = self.settings.solver
        try:
            # the solve command's own output: AMPL reports a missing solver only there
            # ("Cannot invoke <solver>: no such program.", solve_result_num 999, solve_message "?")
            output = a.solve(return_output=True) or ""
        except Exception as exc:  # noqa: BLE001 - classified below
            if backend_absent(solver, str(exc)):
                raise ExactBackendUnavailable(f"{solver} could not run (solver or license missing)") from exc
            raise
        msg = str(a.get_value("solve_message"))
        num = int(a.get_value("solve_result_num"))
        if num >= 500 and backend_absent(solver, f"{msg}\n{output}"):
            raise ExactBackendUnavailable(f"{solver}: solver or license missing")
        if num >= 500:
            # an AMPL/solver that starts but fails on a trivial model is a backend defect, not absence
            raise RuntimeError(f"{self.settings.solver} failed on the probe model: {_scrub(msg.splitlines()[0] if msg else '')}")
        m = re.match(r"^(\w+) (\d+\.\d+\.\d+):", msg)
        a.reset()
        return f"{m.group(1)} {m.group(2)}" if m else None

    @property
    def ampl(self):
        """The open ``amplpy.AMPL`` object (for models other than the set-partitioning one, WP-E7)."""
        if self._ampl is None:
            raise ExactBackendUnavailable("the AMPL session is not open")
        return self._ampl

    def solve_objective(self, objective: str, *, wall_limit: float, snap_integer: bool = False) -> StageResult:
        """Solve the model currently loaded in the session for one objective and classify the outcome.

        Used by the TSP/ATSP models (WP-E7): the caller loads model and data through ``ampl`` and the
        model declares ``suffix bestbound OUT``. ``wall_limit`` replaces the settings' wall limit for
        this call (the cut loop passes the remaining share of its total budget); there is no work limit
        unless the settings carry one. ``snap_integer`` removes solver noise from the objective and the bound
        (``snap_to_integer_data``) for models whose objective is integer by construction. The suffix is reset first, so a solve that returns no bound can
        never expose an earlier solve's bound. The log is not stored.
        """
        a = self.ampl
        settings = dataclasses.replace(self.settings, wall_limit=wall_limit)
        a.eval(f"objective {objective};")
        a.option["solver"] = settings.solver
        a.option[f"{settings.solver}_options"] = solver_option_string(settings, peak=False)
        a.eval(f"let {objective}.bestbound := {_BOUND_SENTINEL:g};")
        self._log.clear()
        t0 = time.perf_counter()
        a.solve()
        secs = time.perf_counter() - t0
        num = int(a.get_value("solve_result_num"))
        msg = str(a.get_value("solve_message"))
        log = "\n".join(self._log)
        self._log.clear()
        obj_value, bound_value = a.get_objective(objective).value(), self._read_bound(objective)
        if snap_integer:
            obj_value, bound_value = snap_to_integer_data(obj_value, bound_value)
        out = classify_outcome(num, msg, obj_value, bound_value)
        work = None
        m = re.findall(r"\(([\d.]+) work units\)", log)
        if m:
            work = float(m[-1])
        first = _scrub(msg.splitlines()[0]) if msg else ""
        return dataclasses.replace(out, solve_result=str(a.solve_result), solve_result_num=num, solver_message=first,
                                   wall_seconds=round(secs, 4), work_units=work, time_limit=wall_limit,
                                   work_limit=settings.work(False))

    def close(self) -> None:
        if self._ampl is not None:
            try:
                self._ampl.close()
            finally:
                self._ampl = None

    # -- model data
    def _load(self, enumeration, minimize_type, quota, v_max) -> None:
        a = self._ampl
        a.reset()
        a.read(str(model_path()))
        cols = enumeration.columns
        nz = {(r, i): k for r, c in enumerate(cols) for i, k in enumerate(c.multiplicity) if k}
        a.set["COLS"] = list(range(len(cols)))
        a.set["ITEMS"] = list(range(len(enumeration.items)))
        a.set["NZ"] = list(nz)
        if nz:
            a.param["a"] = nz
        a.param["demand"] = {i: it.multiplicity for i, it in enumerate(enumeration.items)}
        counted = [int(minimize_type is None or c.type_id == minimize_type) for c in cols]
        # objective coefficient of every column, per objective: kept for the integrality check of the values (_call)
        self._objective_coefficients = {"RouteCount": counted, "Duration": [c.cost for c in cols]}
        if cols:
            a.param["cost"] = {r: c.cost for r, c in enumerate(cols)}
            a.param["counted"] = {r: counted[r] for r in range(len(cols))}
        if quota is not None:
            qtype, q = quota
            a.param["quota_on"] = 1
            a.param["quota"] = int(q)
            if cols:
                a.param["in_quota"] = {r: int(c.type_id == qtype) for r, c in enumerate(cols)}
        a.param["v_max"] = int(v_max)

    def declared_lambda_bounds(self, enumeration) -> list:
        """Declared upper bounds of ``lam`` (the cover floor of E02), read back from AMPL."""
        self._load(enumeration, None, None, sum(it.multiplicity for it in enumeration.items))
        self._ampl.eval("drop FixCount;")
        values = self._ampl.get_data("{r in COLS} lam[r].ub0").to_dict()  # declared variable bound (not the param)
        return [int(round(v)) if math.isfinite(v) else v for v in (values[r] for r in range(len(enumeration.columns)))]

    def _read_bound(self, name: str) -> Optional[float]:
        """``<objective>.bestbound``, or None when it still holds the pre-solve sentinel (no bound returned)."""
        value = float(self._ampl.get_value(f"{name}.bestbound"))
        return None if value <= _BOUND_SENTINEL / 10 else value

    def _call(self, stage: str, k_fix: Optional[int], peak: bool, ncols: int) -> StageResult:
        a = self._ampl
        if k_fix is None:
            a.eval("drop FixCount;")
        else:
            a.param["k_fix"] = int(k_fix)
            a.eval("restore FixCount;")
        name = "RouteCount" if stage == "stage1" else "Duration"
        a.eval(f"objective {name};")
        a.option["solver"] = self.settings.solver
        a.option[f"{self.settings.solver}_options"] = solver_option_string(self.settings, peak=peak)
        # reset the suffix so a solve that returns no bound can never expose an earlier solve's bound
        a.eval(f"let {name}.bestbound := {_BOUND_SENTINEL:g};")
        self._log.clear()
        t0 = time.perf_counter()
        a.solve()
        secs = time.perf_counter() - t0
        num = int(a.get_value("solve_result_num"))
        msg = str(a.get_value("solve_message"))
        log = "\n".join(self._log)  # parsed for Gurobi work units only, never stored
        self._log.clear()
        objective = a.get_objective(name).value()
        bound = self._read_bound(name)
        values = None
        if (has_incumbent(num) and ncols and objective is not None and math.isfinite(float(objective))
                and name in self._objective_coefficients):
            values = a.var["lam"].get_values().to_dict()
            # integrality is a test of the values: the objective of near-integral values is not itself integral
            objective = reconcile_objective(objective, self._objective_coefficients[name],
                                            [values[r] for r in range(ncols)])
        out = classify_outcome(num, msg, objective, bound)
        selection = ()
        if out.objective is not None and ncols:
            if values is None:
                values = a.var["lam"].get_values().to_dict()
            sel = []
            for r in range(ncols):
                v = values[r]
                if abs(v - round(v)) > _INT_TOL:
                    return dataclasses.replace(out, status="rejected", stop_reason="solver_failure", stage=stage)
                if round(v) > 0:
                    sel.append((r, int(round(v))))
            selection = tuple(sel)
        work = None
        m = re.findall(r"\(([\d.]+) work units\)", log)
        if m:
            work = float(m[-1])
        first = _scrub(msg.splitlines()[0]) if msg else ""
        return dataclasses.replace(out, stage=stage, k_fix=k_fix, solve_result=str(a.solve_result), solve_result_num=num,
                                   solver_message=first, wall_seconds=round(secs, 4), work_units=work,
                                   time_limit=self.settings.wall(peak), work_limit=self.settings.work(peak),
                                   selection=selection)

    def solve_columns(self, enumeration, *, occurrence_ids: Optional[Sequence] = None, wave_id: str = "",
                      minimize_type: Optional[str] = None, quota=None, v_max: Optional[int] = None, peak: bool = False,
                      d_lb_free: bool = True) -> SPSolveResult:
        legs = sum(it.multiplicity for it in enumeration.items)
        settings = self.settings
        common = dict(peak=peak, column_count=len(enumeration.columns), solver=settings.solver,
                      ampl_version=self.ampl_version, amplpy_version=self.amplpy_version, ampl_location=self.location,
                      option_string=solver_option_string(settings, peak=peak), threads=settings.threads,
                      seed=settings.seed, wall_limit_seconds=settings.wall(peak), work_limit=settings.work(peak))
        if enumeration.status != "complete":
            status = "timing_dependent_abort" if enumeration.status == "timing_dependent_abort" else "not_run"
            return SPSolveResult(wave_id, status, note=f"enumeration {enumeration.status}: compact model (WP-E5) required"
                                 if status == "not_run" else "enumeration hit its wall-clock safety limit", **common)
        if quota is not None and minimize_type is None:
            raise ValueError("a quota needs a minimised type (typed case)")
        v_max = min(legs, 50) if v_max is None else v_max
        self._load(enumeration, minimize_type, quota, v_max)
        ncols = len(enumeration.columns)
        stages = run_stages(lambda st, k: self._call(st, k, peak, ncols), d_lb_free=d_lb_free)
        s1, s2 = stages["stage1"], stages["stage2"]
        solver_version = self.solver_version
        single = minimize_type is None and len(enumeration.types) == 1
        k_lb, k_src = _k_lower_bound(enumeration, stages["k_lb_solver"], single, stages["k_lb_solver_source"])
        base = dict(stage1=s1, stage2=s2, free=stages["free"], d_lb=stages["d_lb"], d_lb_free=stages["d_lb_free"],
                    non_lexicographic=stages["non_lexicographic"], solver_version=solver_version, k_lb=k_lb,
                    k_lb_source=k_src, **common)
        if s1.status in ("infeasible_proven", "rejected"):
            return SPSolveResult(wave_id, s1.status, **base)
        if s2 is not None and s2.status in ("infeasible_proven", "rejected"):
            # stage 2 fixes K to the value of an existing stage-1 incumbent, so it cannot be infeasible:
            # a proven-infeasible (or failed) stage 2 is a solver contradiction, never a result
            return SPSolveResult(wave_id, "rejected", note=f"stage 2 {s2.status} after a stage-1 incumbent", **base)
        src = s2 if s2 is not None and s2.objective is not None else s1
        if src.objective is None:
            return SPSolveResult(wave_id, "bound_only", **base)
        routes = expand_selection(enumeration, src.selection, occurrence_ids)
        counted = [r for r in routes if minimize_type is None or r.type_id == minimize_type]
        k, d = len(counted), sum(r.cost for r in routes)
        expected_k = s1.objective if src is s1 else src.k_fix
        mismatch = k != expected_k or (src is s2 and d != s2.objective)
        if quota is not None and sum(1 for r in routes if r.type_id == quota[0]) > quota[1]:
            mismatch = True
        if mismatch:
            return SPSolveResult(wave_id, "rejected", note="objective cross-check failed", **base)
        status = "optimal" if s1.status == "optimal" and s2 is not None and s2.status == "optimal" else "feasible_with_gap"
        return SPSolveResult(wave_id, status, k=k, d=d, selection=src.selection, routes=routes, **base)


def solve_columns(enumeration, *, occurrence_ids: Optional[Sequence] = None, wave_id: str = "",
                  minimize_type: Optional[str] = None, quota=None, v_max: Optional[int] = None, peak: bool = False,
                  settings: Optional[SolverSettings] = None, d_lb_free: bool = True,
                  session: Optional[AmplSession] = None) -> SPSolveResult:
    """Solve the SP over enumerated columns; never raises ``ExactBackendUnavailable``."""
    kw = dict(occurrence_ids=occurrence_ids, wave_id=wave_id, minimize_type=minimize_type, quota=quota,
              v_max=v_max, peak=peak, d_lb_free=d_lb_free)
    try:
        if session is not None:
            return session.solve_columns(enumeration, **kw)
        with AmplSession(settings) as s:
            return s.solve_columns(enumeration, **kw)
    except ExactBackendUnavailable as exc:
        return _unavailable(wave_id, str(exc), peak)


def solve_wave(wave, enumeration, *, minimize_type: Optional[str] = None, quota=None, peak: bool = False,
               settings: Optional[SolverSettings] = None, d_lb_free: bool = True,
               session: Optional[AmplSession] = None) -> SPSolveResult:
    """``solve_columns`` for a ``WaveInstance`` (occurrence ids, V_max = min(legs, 50))."""
    return solve_columns(enumeration, occurrence_ids=wave.occurrence_ids, wave_id=wave.wave_id,
                         minimize_type=minimize_type, quota=quota, v_max=min(wave.legs, 50), peak=peak,
                         settings=settings, d_lb_free=d_lb_free, session=session)


@dataclass(frozen=True)
class ProbeResult:
    available: bool
    reason: Optional[str] = None  # set only when the backend is unavailable
    status: Optional[str] = None  # status of the one-student probe solve (expected: optimal, K = 1, D = 10)
    k: Optional[int] = None
    d: Optional[int] = None
    routes: int = 0


def probe_backend(solver: str = "gurobi") -> ProbeResult:
    """Solve a one-student wave through the full backend path.

    ``available`` is False ONLY when the result is ``backend_unavailable`` (amplpy, AMPL, the solver
    or its license is absent). Every other failure is a backend defect: exceptions propagate and a
    wrong probe solve is returned as it is, so callers (tests) fail instead of skipping.
    """
    from .route_enumeration import enumerate_routes
    from .wave_instance import VehicleTypeSpec

    enum = enumerate_routes("pickup", ((0, 5), (5, 0)), ("A",), ("So",), (VehicleTypeSpec("t", 0, 1, 10),),
                            max_ride=60, max_tour=150)
    res = solve_columns(enum, settings=SolverSettings(solver=solver), d_lb_free=False)
    if res.status == "backend_unavailable":
        return ProbeResult(False, reason=res.note)
    return ProbeResult(True, status=res.status, k=res.k, d=res.d, routes=len(res.routes))


def host_description() -> str:
    """OS name and release only (no host name or user)."""
    return f"{platform.system()}-{platform.release()}"
