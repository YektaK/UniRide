#!/usr/bin/env python3
"""WP-E11 J9a: runner of the joint day model (design docs/designs/JOINT_DAY_MODEL_DESIGN.md sections 4-6; DECISION_LOG E13, E14).

OFFLINE: reads the committed archives through ``scripts/exact_archive_loader.py`` (never the DB or HTTP). Per cell
(fleet, date, R[, L]) it runs, in this order:

    J1 day instance -> J2 wave values and bounds (LB0/LB0w or LB_L/LB_S, certificate) -> J3 model + J4 HiGHS (primary)
    -> J5 Gurobi cross-check (``--crosscheck``, default on; required for paper cells, E14 Q5) -> certification of every
    wave's routes (``certification.py`` + ``certify_optimization_response``) -> J6 independent checker -> typed cells
    through ``scripts/verify-typed-selection.ts`` -> label hook -> files.

* Typed fleet: the fixed (large) type and the minimised type come from the source manifest (``fixed_type``,
  ``minimize_type``) and are passed explicitly to the stage runner (J4); capacity order is never relied on. The Doblo
  type id of the archive is ``minivan``.
* Homogeneous cells (``single_4sw5so``): the TypeScript CLI needs BOTH ``fixedType`` and ``minimiseType`` (zod schema
  ``verifyCaseSchema``, ``src/services/typed-selection-verify.ts``), so it does not accept a single type; the
  homogeneous cell is confirmed by the J6 checker alone (``ts_confirmation = not_applicable_single_type``).
* A failing certificate, checker, objective cross-check or TS CLI gives ``day_status = rejected``. A solver
  disagreement (cross-check ``blocking``) is rejected too. A missing TS CLI (node absent) is a blocking error but not
  a rejection (the check is missing, not failed, as in ``run_exact_union_day.py``).
* ``backend_unavailable`` (HiGHS, Gurobi or the AMPL wave solver) STOPS the run (E06): exit 3, nothing is written, the
  cell is never skipped.
* Limits: ``--time-limit`` (default 600 s per solver call, E14 Q3) and ``--run-label``. The protocol validator accepts
  only 600 s; another limit needs a non-empty ``--run-label``, is recorded as ``sensitivity_run`` and the manifest
  is validated with the limit normalised (never pooled with the 600 s run). ``--jobs`` accepts only 1 (E06: serial).
* Dirty tree (E06): a dirty working tree (the output directory excluded) is refused with exit 2 unless
  ``--allow-dirty``; then the manifest says ``dirty_working_tree: true`` and ``development_run: true``.
* Output rule (E04): ``--out`` must lie below ``docs/paper/results`` when inside the repository, must not overlap a
  source campaign or an existing results folder, and must not exist non-empty; otherwise exit 2 before any work.
* Label hook: ``label_day_cell(facts)`` below is the ONLY place that decides ``day_status``, ``bound_used`` and
  ``bound_source`` for a solved cell: an adapter on J9b's ``uniride_core.exact.day_labels.label_cell`` (day verdict
  ``crosscheck_status`` -> ``crosscheck``, wave-value verdict ``wave_values_status`` -> ``wave_values_crosscheck``, the
  independent checker -> ``checker_ok``, the primary ``DaySolveResult`` and the J2 ``DayBounds``). Statuses the runner set
  itself are final: ``input_rejected`` and a rejection by the certificate, the checker or the TypeScript CLI are never
  replaced by a label (``settle_label``). ``day_joint.csv`` carries the label fields ``bound_proof``, ``flags``,
  ``unverified_bounds``, ``proof_claim_allowed``, ``proof_claim_reason`` and ``reason``; a paper table presents a cell as
  proven only when ``proof_claim_allowed`` is ``True``.

Files (design 6.1): ``day_joint_manifest.json``, ``day_joint.csv``, ``day_joint_stages.csv``, ``day_joint_plans.json``,
``day_joint_week.csv``, ``lb0.csv``. Not written here: ``README.md`` (lead, J11), ``comparison.csv`` and
``reproduction_check.csv`` (they need WP-E4b and prototype inputs: J9b/J11).

Exit codes: 0 ok; 1 blocking error (results are still written); 2 refused (arguments, unsafe --out, dirty tree, archive);
3 backend unavailable (nothing written).

Run: PYTHONPATH=<repo root> python scripts/run_exact_day_joint.py --out <dir> [--fleets ...] [--rides ...] [--dates ...]
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import platform
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO / "optimizer_api"), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import importlib.util  # noqa: E402

from academic_benchmark.exact_reference import protocol  # noqa: E402
from academic_benchmark.validation import day_plan as checker  # noqa: E402
from uniride_core.exact import ampl_backend as ab  # noqa: E402
from uniride_core.exact import certification as cert  # noqa: E402
from uniride_core.exact import day_bounds as bounds_mod  # noqa: E402
from uniride_core.exact import day_labels  # noqa: E402
from uniride_core.exact import gurobi_day_backend as gdb  # noqa: E402
from uniride_core.exact import highs_backend as hb  # noqa: E402
from uniride_core.exact.day_instance import READY, build_day_instance  # noqa: E402
from uniride_core.planning import fleet_selection_request as fsr  # noqa: E402
from uniride_core.planning import union_day_menu as udm  # noqa: E402


def _load_module(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ud = _load_module("run_exact_union_day")  # TS CLI helpers (run_cli, cli_case, exact_menu_option, tool_versions)
tm = ud.tm
wg = tm.wg
loader = tm.loader
replay = tm.replay

RESULTS = REPO / "docs" / "paper" / "results"
SOURCE_4SW5SO = RESULTS / "week-2026-10-05-4sw5so"
DEFAULT_OUT = RESULTS / "week-2026-10-05-exact" / "wp-e11-joint-day"
MANIFEST_FILENAME = protocol.DAY_JOINT_MANIFEST_FILENAME
WORK_PACKAGE = "WP-E11"
HOMOGENEOUS = "single_4sw5so"
FLEET_NAMES = (HOMOGENEOUS, *tm.SOURCES)
SOURCE_PATHS = {HOMOGENEOUS: SOURCE_4SW5SO, **tm.SOURCES}
DEFAULT_TIME_LIMIT = hb.DEFAULT_TIME_LIMIT_SECONDS  # 600 s per solver call (E14 Q3)
OUT_FILES = ("day_joint.csv", "day_joint_stages.csv", "day_joint_plans.json", "day_joint_week.csv", "lb0.csv")

CSV_FIELDS = (
    "fleet", "date", "R", "L", "waves", "legs", "columns", "columns_outside_day", "day_status", "K_or_S", "large_peak",
    "total_minutes", "car_minutes", "routes", "lb0", "lb0w", "lb_L", "lb_S", "bound_used", "bound_source",
    "bound_proof", "proof_claim_allowed", "proof_claim_reason", "reason", "flags", "unverified_bounds", "certificate_tier", "timing_dependent", "non_lexicographic", "crosscheck_solver", "crosscheck_status", "wave_values_status", "checker_ok",
    "ts_confirmation", "wall_seconds", "note",
)
STAGE_FIELDS = ("fleet", "date", "R", "L", "solver", "stage", "status", "stop_reason", "objective", "bound", "bound_ceil",
                "bound_source", "timing_dependent", "non_lexicographic", "wall_seconds", "work_units", "solve_result", "mps_sha256")
WEEK_FIELDS = ("fleet", "R", "L", "dates", "weekly_fleet_max", "vehicle_days_sum", "cells_not_proven", "cells_without_value")
LB_FIELDS = ("fleet", "date", "R", "L", "bound", "value", "point", "contributions", "wave_value_source", "used_value",
             "used_proof")  # wave_* rows: used_value/used_proof = what the bounds really received (a blocked l_w becomes 0)


class BackendUnavailable(RuntimeError):
    """A solver or its licence is missing during the run: the run stops (E06), the cell is never skipped."""


class CellRefused(Exception):
    """The archive of a cell is inconsistent (input_rejected)."""


# ---------------------------------------------------------------- strict values
def strict_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    return value


def int_list(text: str, name: str) -> list:
    out = []
    for part in [p.strip() for p in str(text).split(",") if p.strip()]:
        try:
            out.append(strict_int(int(part), name))
        except ValueError as exc:
            raise ValueError(f"{name}: {part!r} is not an integer") from exc
    return out


def positive_float(text) -> float:
    if isinstance(text, bool):
        raise argparse.ArgumentTypeError("a number is expected, not a bool")
    try:
        value = float(text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive finite number, got {text!r}")
    return value


def serial_jobs(text) -> int:
    try:
        value = strict_int(int(text), "--jobs")
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("--jobs must be the integer 1") from exc
    if value != 1:
        raise argparse.ArgumentTypeError("--jobs must be 1: the joint day runs are serial (E06)")
    return value


def run_label_text(text: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]{0,64}", text):
        raise argparse.ArgumentTypeError("--run-label may hold letters, digits, '.', '_' and '-' (max 64)")
    return text


def strict_manifest_problems(manifest: dict) -> list:
    """The protocol validator compares ints with ``==``, so ``True`` passes where ``1`` is expected; refuse every bool."""
    problems = []
    for name, solver in (manifest.get("solvers") or {}).items():
        for key in ("threads", "seed"):
            if isinstance(solver.get(key), bool) or not isinstance(solver.get(key), int):
                problems.append(f"solvers.{name}.{key} must be an integer, not a bool")
        tl = solver.get("time_limit_seconds")
        if isinstance(tl, bool) or not isinstance(tl, (int, float)):
            problems.append(f"solvers.{name}.time_limit_seconds must be a number, not a bool")
        wl = solver.get("work_limit")
        if isinstance(wl, bool):
            problems.append(f"solvers.{name}.work_limit must not be a bool")
    for key, value in ((manifest.get("enumeration") or {}).get("columns_per_day") or {}).items():
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"enumeration.columns_per_day[{key}] must be an integer")
    history = manifest.get("run_history") or {}
    for key in ("cells_planned", "cells_solved", "jobs"):
        if key in history and (isinstance(history[key], bool) or not isinstance(history[key], int)):
            problems.append(f"run_history.{key} must be an integer")
    return problems


# ---------------------------------------------------------------- configuration and dependencies
@dataclasses.dataclass(frozen=True)
class Config:
    time_limit: float = DEFAULT_TIME_LIMIT
    work_limit: Optional[float] = None
    crosscheck: bool = True
    aggregate: bool = True
    wave_values: str = "sp"  # "sp" (wave SP through AMPL) or "trivial" (arithmetic floors only, development)
    run_label: str = ""


@dataclasses.dataclass
class Deps:
    """Everything that touches a solver or node. Tests replace these with fakes; the real ones are never called there."""

    highs_run: Callable
    gurobi_run: Optional[Callable]
    wave_solver: Optional[Callable]  # (wave, enumeration, minimize_type, solver, peak) -> SPSolveResult
    cli: Callable
    close: Callable = lambda: None


class _RealWaveSolver:
    """The wave SP through lazily opened AMPL sessions (one per solver name)."""

    def __init__(self):
        self._sessions: dict = {}

    def __call__(self, wave, enumeration, minimize_type, solver, peak):
        if solver not in self._sessions:
            session = ab.AmplSession(ab.SolverSettings(solver=solver))
            try:
                session.open()
            except ab.ExactBackendUnavailable as exc:
                raise BackendUnavailable(f"wave solver {solver}: {exc}") from exc
            self._sessions[solver] = session
        return ab.solve_wave(wave, enumeration, minimize_type=minimize_type, peak=peak, d_lb_free=False,
                             session=self._sessions[solver])

    def close(self):
        for s in self._sessions.values():
            s.close()


def real_deps(cfg: Config) -> Deps:
    waves = _RealWaveSolver() if cfg.wave_values == "sp" else None
    holder: dict = {}

    def gurobi_run(instance, **kw):
        settings = kw["settings"]
        if "session" not in holder:
            try:
                holder["session"] = gdb.open_session(settings)
            except gdb.GurobiBackendUnavailable as exc:
                return hb.DaySolveResult(status="backend_unavailable", note=str(exc), solver=gdb.SOLVER,
                                         solver_options=settings.option_string(), time_limit=settings.time_limit)
        return gdb.run_day_stages_gurobi(instance, session=holder["session"], **kw)

    def close():
        if "session" in holder:
            holder["session"].close()
        if waves is not None:
            waves.close()

    return Deps(hb.run_day_stages, gurobi_run if cfg.crosscheck else None, waves, ud.run_cli, close)


# ---------------------------------------------------------------- the label hook (J9b's label_cell)
def label_day_cell(facts: dict) -> dict:
    """THE label hook: an adapter on ``day_labels.label_cell`` (J9b); no label logic lives here.

    ``facts``: the plain values fleet, date, ride, large_limit, solve_status, objective, stage_statuses, timing_dependent,
    non_lexicographic, bound_above_incumbent, crosscheck_status, wave_values_status, stage1_bound_ceil, bounds,
    certificate and certificate_tier (for logs and spies), plus the objects ``label_cell`` takes: ``enumeration_complete``,
    ``result`` (the primary ``DaySolveResult`` or ``None``), ``day_bounds`` (the J2 ``DayBounds``) and ``checker_ok``
    (``None`` when there is no plan). Returns ``day_status``, ``reason``, ``bound_used``, ``bound_source``,
    ``bound_proof``, ``flags``, ``unverified_bounds``, ``certificate_tier``, ``proof_claim_allowed``, ``proof_claim_reason``.
    Raises ``ValueError`` (from ``label_cell``) on inconsistent facts; the caller turns that into a rejected cell.
    """
    cell = day_labels.label_cell(
        enumeration_complete=facts["enumeration_complete"], result=facts.get("result"), bounds=facts.get("day_bounds"),
        crosscheck=facts["crosscheck_status"], checker_ok=facts.get("checker_ok"),
        wave_values_crosscheck=facts["wave_values_status"])
    return {"day_status": cell.label, "reason": cell.reason, "bound_used": cell.bound_used, "bound_source": cell.bound_source or "",
            "bound_proof": cell.bound_proof or "", "flags": ";".join(cell.flags),
            "unverified_bounds": ";".join(f"{name}:{wave}" for name, wave in cell.unverified_bounds),
            "certificate_tier": cell.certificate_tier, "proof_claim_allowed": cell.proof_claim_allowed,
            "proof_claim_reason": cell.proof_claim_reason}


def settle_label(label: dict, forced: Optional[str] = None, reason: str = "") -> dict:
    """The label of a cell after the runner's own verdicts: a status the runner set (``forced``: rejected by the certificate,
    the checker or the TypeScript CLI) is final, whatever the label says, and a forced status never claims a proof."""
    if forced is None:
        return label
    return dict(label, day_status=forced, proof_claim_allowed=False, proof_claim_reason=forced,
                reason=reason or label.get("reason", ""))


# ---------------------------------------------------------------- inputs
@dataclasses.dataclass(frozen=True)
class FleetInput:
    name: str
    path: Path
    campaign: object
    manifest: dict
    types: tuple  # (fixed, minimised) for a typed fleet, the single type otherwise
    fixed_id: Optional[str]
    minimised_id: Optional[str]
    ctx: object = None  # typed: the FleetContext of run_exact_typed_menus
    l_values: tuple = ()

    @property
    def typed(self) -> bool:
        return self.ctx is not None

    def matrix_path(self, date: str, ride: int) -> Path:
        stem = f"{date}_R{ride}" + ("" if self.typed else "_repeat1")
        return self.path / f"{stem}.matrix.json"


def load_fleet(name: str) -> FleetInput:
    path = SOURCE_PATHS[name]
    if name == HOMOGENEOUS:
        camp = loader.load_campaign(path)
        manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
        return FleetInput(name, path, camp, manifest, tuple(camp.fleet_types), None, None)
    ctx = tm.load_fleet_context(path)
    return FleetInput(name, path, ctx.campaign, ctx.manifest, (ctx.fixed, ctx.minimise), ctx.fixed.type_id,
                      ctx.minimise.type_id, ctx, tuple(ctx.replay_fleet.l_values))


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise CellRefused(f"cannot read {Path(path).name}: {type(exc).__name__}") from exc


def checker_waves(fleet: FleetInput, waves: tuple, date: str, ride: int) -> list:
    """The checker's wave definitions (occurrence id -> location code).

    Typed archives: the demand list comes from the MENU of the archive itself (``<date>_R<R>.menu_options.json``: the
    occurrences of every wave's routes with the archive's own ``occurrenceLabels``), then it is compared with the loader's
    wave instances (occurrence ids, direction, anchor); any difference refuses the cell. Homogeneous archive: the loader's
    wave instances (built from the reference response) are the only source.
    """
    if not fleet.typed:
        return [checker.Wave(w.wave_id, w.direction, w.anchor_minutes, dict(zip(w.occurrence_ids, w.location_codes))) for w in waves]
    menu = read_json(fleet.path / f"{date}_R{ride}.menu_options.json")
    labels = menu["occurrenceLabels"]
    by_id = {w.wave_id: w for w in waves}
    out = []
    if {m["waveId"] for m in menu["waves"]} != set(by_id):
        raise CellRefused(f"{date} R{ride}: menu waves differ from the loaded waves")
    for m in menu["waves"]:
        w = by_id[m["waveId"]]
        included = [o for o in m["options"] if o["status"] == "included"]
        if not included or included[0]["optionId"] != "base":
            raise CellRefused(f"{m['waveId']}: no included baseline option in the menu")
        occ = {oid for o in included for r in o["routes"] for oid in r["studentIds"]}
        for o in included:
            if {oid for r in o["routes"] for oid in r["studentIds"]} != occ:
                raise CellRefused(f"{m['waveId']}: menu option {o['optionId']} covers other occurrences than the baseline")
        if occ != set(w.occurrence_ids) or m["direction"] != w.direction or m["anchorMinutes"] != w.anchor_minutes:
            raise CellRefused(f"{m['waveId']}: menu demand differs from the loaded wave")
        out.append(checker.Wave(m["waveId"], m["direction"], m["anchorMinutes"], {oid: labels[oid] for oid in sorted(occ)}))
    return out


def type_specs(types) -> dict:
    return {t.type_id: checker.TypeSpec(t.type_id, t.sw_capacity, t.so_capacity, t.cooldown_minutes, t.total_capacity,
                                        t.ride_limit_minutes, t.tour_limit_minutes) for t in types}


# ---------------------------------------------------------------- bounds
AGREE, BLOCKING, INCONCLUSIVE, NOT_RUN = "agree", "blocking", "inconclusive", "not_run"


@dataclasses.dataclass(frozen=True)
class WaveRecord:
    """One wave quantity as the bounds use it, with what each solver said and the two-solver verdict (owner decision E14, 2026-10-21)."""

    kind: str  # "k_any" or "l"
    wave_id: str
    used: object  # WaveValue passed to the bounds
    verdict: str  # agree / blocking / inconclusive / not_run
    detail: str  # both solvers' values, e.g. "gurobi=3[optimal];highs=3[optimal]"
    in_bounds: object = None  # the WaveValue the bounds received when it differs from ``used`` (a blocked l_w: floor 0)


def _solver_value(deps, wave, day_wave, minimize_type, large_id, solver, peak):
    """``(WaveValue or None, stage-1 optimal, text)`` of one solver. A refused or unproven value is ``None`` (never an error)."""
    sp = deps.wave_solver(wave, day_wave.enumeration, minimize_type, solver, peak)
    if sp.status == "backend_unavailable":
        raise BackendUnavailable(f"wave solver {solver}: {sp.note}")
    try:
        wv = bounds_mod.wave_value_from_sp(sp, legs=wave.legs, minimize_type=minimize_type, large_type_id=large_id)
    except ValueError as exc:
        return None, False, f"{solver}=refused({str(exc)[:60]})"
    optimal = sp.stage1 is not None and sp.stage1.status == "optimal" and sp.stage1.objective is not None
    return wv, optimal, f"{solver}={wv.value}[{'optimal' if optimal else 'bound'}]"


def _wave_record(deps: Deps, cfg: Config, wave, day_wave, *, minimize_type, large_id, peak, errors, tag) -> WaveRecord:
    """The wave value used and its verdict.

    * ``agree``: both solvers solved the wave, both stage 1 optimal, equal values.
    * ``blocking``: both proven and different, or one solver's proven bound exceeds the other's proven optimum; the value
      used is the smaller one and is tagged ``PROOF_UNVERIFIED`` (tier 2 refuses it).
    * ``inconclusive``: a value comes from a bound, a time limit, a refusal or the trivial floor.
    * ``not_run``: ``--no-crosscheck`` or ``--wave-values trivial`` (no two-solver check was attempted).
    """
    kind, objective = ("l", bounds_mod.OBJ_L) if minimize_type is not None else ("k_any", bounds_mod.OBJ_K_ANY)
    trivial = bounds_mod.WaveValue(0 if kind == "l" else 1, bounds_mod.PROOF_ARITHMETIC, objective)
    if cfg.wave_values != "sp" or deps.wave_solver is None:
        return WaveRecord(kind, wave.wave_id, trivial, NOT_RUN, "trivial_floor")
    solvers = ("gurobi", "highs") if cfg.crosscheck else ("highs",)
    got = [_solver_value(deps, wave, day_wave, minimize_type, large_id, sv, peak) for sv in solvers]
    detail = ";".join(g[2] for g in got)
    proven = [g for g in got if g[0] is not None]
    if not proven:
        return WaveRecord(kind, wave.wave_id, trivial, NOT_RUN if len(solvers) == 1 else INCONCLUSIVE, detail + ";trivial_floor")
    low = min(proven, key=lambda g: g[0].value)[0]
    if len(solvers) == 1:
        return WaveRecord(kind, wave.wave_id, low, NOT_RUN, detail)
    if len(proven) < 2:
        return WaveRecord(kind, wave.wave_id, low, INCONCLUSIVE, detail)
    (va, oa, _), (vb, ob, _) = got
    conflict = (oa and ob and va.value != vb.value) or (oa and not ob and vb.value > va.value) or (ob and not oa and va.value > vb.value)
    if conflict:
        errors.append(f"{tag} {wave.wave_id}: the two solvers contradict each other on the {kind} wave value ({detail})")
        return WaveRecord(kind, wave.wave_id, dataclasses.replace(low, proof=bounds_mod.PROOF_UNVERIFIED), BLOCKING, detail)
    if oa and ob:
        return WaveRecord(kind, wave.wave_id, low, AGREE, detail)
    return WaveRecord(kind, wave.wave_id, low, INCONCLUSIVE, detail)


def wave_values_status(records) -> str:
    verdicts = {r.verdict for r in records}
    for v in (BLOCKING, INCONCLUSIVE, NOT_RUN):
        if v in verdicts:
            return v
    return AGREE if verdicts else NOT_RUN


def day_bounds(instance, fleet: FleetInput, limit, deps, cfg, errors, tag) -> tuple:
    """``(DayBounds, [WaveRecord])``. Unverified (blocking) ``l_w`` values are replaced by the arithmetic floor 0: tier 2 refuses them."""
    typed = fleet.typed
    peak_legs = max(w.wave.legs for w in instance.waves)
    k_any, l, records = {}, {}, []
    for dw in instance.waves:
        peak = dw.wave.legs == peak_legs
        rec = _wave_record(deps, cfg, dw.wave, dw, minimize_type=None, large_id=fleet.fixed_id, peak=peak, errors=errors, tag=tag)
        records.append(rec)
        k_any[dw.wave_id] = rec.used
        if typed and cfg.wave_values == "sp":
            lrec = _wave_record(deps, cfg, dw.wave, dw, minimize_type=fleet.fixed_id, large_id=fleet.fixed_id, peak=peak,
                                errors=errors, tag=tag)
            records.append(lrec)
            if lrec.used.proof == bounds_mod.PROOF_UNVERIFIED:
                floor0 = bounds_mod.WaveValue(0, bounds_mod.PROOF_ARITHMETIC, bounds_mod.OBJ_L)
                records[-1] = dataclasses.replace(lrec, in_bounds=floor0)
                l[dw.wave_id] = floor0
            else:
                l[dw.wave_id] = lrec.used
    if typed:
        return bounds_mod.compute_day_bounds(instance, l=l or None, k_any=k_any, large_limit=limit, large_type_index=0), records
    return bounds_mod.compute_day_bounds(instance, k=k_any), records


# ---------------------------------------------------------------- plan, certification, checker, TS
def plan_from_result(instance, result):
    """``{wave index: [ExpandedRoute]}`` of the last stage with an incumbent, or ``None``."""
    chosen = [s for s in result.stages if s.selection]
    if not chosen:
        return None
    selection = chosen[-1].selection
    plan = {}
    for wi, dw in enumerate(instance.waves):
        pairs = tuple((ci, copies) for w, ci, copies in selection if w == wi)
        plan[wi] = ab.expand_selection(dw.enumeration, pairs, dw.wave.occurrence_ids) if pairs else ()
    return plan


def certify_plan(fleet: FleetInput, instance, plan, arcs_doc) -> list:
    """Problems (empty when every wave's routes pass ``certify_optimization_response``) and the integer minutes."""
    problems = []
    for wi, dw in enumerate(instance.waves):
        routes = plan[wi]
        pairs = [(r.type_id, r.occurrence_ids) for r in routes]
        if fleet.typed:
            request = cert.typed_request_payload(dw.wave, list(instance.types), minimize_type=fleet.minimised_id, quota=None)
            response = cert.typed_response_payload(dw.wave, pairs, type_ids=[t.type_id for t in instance.types])
        else:
            t = instance.types[0]
            request = cert.request_payload(dw.wave, sw_capacity=t.sw_capacity, so_capacity=t.so_capacity, cooldown_minutes=t.cooldown_minutes)
            response = cert.response_payload(dw.wave, [r.occurrence_ids for r in routes])
        c = wg.certificate(request, response, arcs_doc)
        if not c.get("is_feasible"):
            problems.append(f"{dw.wave_id}: certificate failed ({wg._violation_types(c)})")
        if sum(r.cost for r in routes) != cert.recompute_objective(dw.wave, [r.occurrence_ids for r in routes])[1]:
            problems.append(f"{dw.wave_id}: column cost differs from the recomputed tour minutes")
    return problems


def check_plan(fleet: FleetInput, instance, plan, arcs_doc, waves_checker, limit, objective):
    routes = []
    for wi, dw in enumerate(instance.waves):
        routes.extend(checker.Route(dw.wave_id, r.type_id, tuple(r.occurrence_ids)) for r in plan[wi])
    peak_type = fleet.minimised_id if fleet.typed else instance.types[0].type_id
    claims = checker.DayClaims(route_count=len(routes), total_minutes=objective[1],
                               minutes_by_type={fleet.minimised_id: objective[2]} if fleet.typed else {},
                               peaks={peak_type: objective[0]})
    arcs = {(r["origin_code"], r["destination_code"]): r["duration_minutes"] for r in arcs_doc["arcs"]}
    w0 = instance.waves[0].wave
    return checker.check_day_plan(
        waves=waves_checker, routes=routes, types=type_specs(instance.types), arcs=arcs, depot=w0.depot_code,
        tour_limit=instance.tour, ride_limit=instance.ride,
        peak_caps={fleet.fixed_id: limit} if fleet.typed else None, claims=claims)


def ts_confirm(fleet: FleetInput, instance, plan, limit, objective, deps, tag) -> tuple:
    """``(status, detail)`` of the TypeScript confirmation; statuses: confirmed, failed, missing, not_applicable_single_type."""
    if not fleet.typed:
        return "not_applicable_single_type", "the TS CLI needs a fixed and a minimised type"
    ctx = fleet.ctx
    menus, selection = [], {}
    for wi, dw in enumerate(instance.waves):
        doc = {"kind": "q", "quota": 0, "routes": [{"type_id": r.type_id, "occurrence_ids": list(r.occurrence_ids)} for r in plan[wi]]}
        option, reason = ud.exact_menu_option(dw.wave, doc, ctx.type_ids)
        if option is None:
            return "failed", f"{dw.wave_id}: {reason}"
        menus.append(udm.WaveMenu(dw.wave_id, dw.wave.direction, dw.wave.anchor_minutes, (option,)))
        selection[dw.wave_id] = {"option_id": option.option_id,
                                 "labels": ["large" if r.type_id == fleet.fixed_id else "car" for r in plan[wi]]}
    rf = ctx.replay_fleet
    request = fsr.build_selection_request(
        udm.request_waves(menus), fixed_type=rf.fixed, minimise_type=rf.minimise, max_large=limit, ride_default=instance.ride,
        tour_default=instance.tour, cooldown_large_minutes=replay._cooldown(rf, rf.fixed),
        cooldown_car_minutes=replay._cooldown(rf, rf.minimise), max_cars=rf.max_cars, time_limit_seconds=30.0)
    case = ud.cli_case(tag, ctx, {"maxRideTimeMinutes": instance.ride, "maxTourMinutes": instance.tour}, limit, request, menus,
                       SimpleNamespace(selection=selection))
    results, error = deps.cli([case])
    if results is None:
        return "missing", error
    r = results[tag]
    if not r["ok"]:
        return "failed", f"problems {r['problems'][:2]} recheck {r['recheck']['failures'][:2]} differences {len(r['intervalDifferences'])}"
    if r["assignment"]["cars"] != objective[0]:
        return "failed", f"TS minimum cars {r['assignment']['cars']} differs from S {objective[0]}"
    return "confirmed", f"assignment {r['assignment']['status']}, cars {r['assignment']['cars']}"


# ---------------------------------------------------------------- one cell
def _facts_base(fleet, date, ride, limit) -> dict:
    return {"fleet": fleet.name, "date": date, "ride": ride, "large_limit": limit}


def _bound_dict(b):
    return None if b is None else {"value": b.value, "point": b.point,
                                   "contributions": [(c.wave_id, c.value, c.proof) for c in b.contributions]}


def _stage_rows(base: dict, solver: str, result) -> list:
    rows = []
    for s in result.stages:
        r = s.result
        rows.append(dict(base, solver=solver, stage=s.stage, status=r.status, stop_reason=r.stop_reason, objective=r.objective,
                         bound=r.bound, bound_ceil=r.bound_ceil, bound_source=r.bound_source, timing_dependent=r.timing_dependent,
                         non_lexicographic=r.non_lexicographic, wall_seconds=r.wall_seconds, work_units=r.work_units,
                         solve_result=r.solve_result, mps_sha256=s.mps_sha256))
    return rows


def solve_cell(fleet: FleetInput, date: str, ride: int, limit, cfg: Config, deps: Deps) -> dict:
    """One cell: ``{"row", "stages", "plan", "lb_rows", "mps", "errors", "columns"}``. Raises ``BackendUnavailable`` (run stops)."""
    t0 = time.perf_counter()
    tag = f"{fleet.name}|{date}|R{ride}|L{limit if limit is not None else '-'}"
    errors: list = []
    base = {"fleet": fleet.name, "date": date, "R": ride, "L": limit}
    row = dict(base, waves="", legs="", columns="", columns_outside_day="", day_status="", K_or_S="", large_peak="", total_minutes="",
               car_minutes="", routes="", lb0="", lb0w="", lb_L="", lb_S="", bound_used="", bound_source="", bound_proof="",
               proof_claim_allowed=False, proof_claim_reason="", reason="", flags="", unverified_bounds="", certificate_tier="",
               timing_dependent="", non_lexicographic="", crosscheck_solver="", crosscheck_status="not_run", wave_values_status="", checker_ok="",
               ts_confirmation="", wall_seconds="", note="")
    out = {"row": row, "stages": [], "plan": None, "lb_rows": [], "mps": {}, "errors": errors, "columns": None, "versions": {}}

    def finish(status, note=""):
        row.update(day_status=status, note=note, wall_seconds=round(time.perf_counter() - t0, 2))
        if status in ("input_rejected", "rejected") and not row["reason"]:
            row["reason"] = note  # a runner status without a label: its text is the reason, never a claim
        return out

    def labelled(facts):
        """``label_day_cell`` with inconsistent facts (``ValueError``) failing closed as a rejected cell."""
        try:
            return label_day_cell(facts)
        except ValueError as exc:
            errors.append(f"{tag}: label_cell refused the facts: {exc}")
            return {"day_status": "rejected", "reason": f"label_cell refused: {exc}", "proof_claim_allowed": False,
                    "proof_claim_reason": "rejected"}

    def apply_label(label):
        row.update(bound_used="" if label.get("bound_used") is None else label["bound_used"], bound_source=label.get("bound_source") or "",
                   bound_proof=label.get("bound_proof") or "", flags=label.get("flags") or "",
                   unverified_bounds=label.get("unverified_bounds") or "", reason=label.get("reason") or "",
                   proof_claim_allowed=bool(label.get("proof_claim_allowed", False)),
                   proof_claim_reason=label.get("proof_claim_reason") or "")

    try:
        waves = tuple(w for w in fleet.campaign.waves_for(ride) if w.service_date == date)
        if not waves:
            raise CellRefused(f"no waves of {date} at R{ride}")
        arcs_doc = read_json(fleet.matrix_path(date, ride))
        waves_checker = checker_waves(fleet, waves, date, ride)
    except (CellRefused, loader.InputRejected, KeyError) as exc:
        errors.append(f"{tag}: input_rejected: {exc}")
        return finish("input_rejected", str(exc))
    instance = build_day_instance(waves, fleet.types, service_date=date, column_cap=protocol.ENUMERATION_CAPS["column_cap"],
                                  label_cap=protocol.ENUMERATION_CAPS["label_cap"])
    row.update(waves=len(waves), legs=sum(w.legs for w in waves), columns=instance.columns_total,
               columns_outside_day=instance.filtered_total)
    out["columns"] = instance.enumerated_columns
    if instance.status != READY:
        note = "waves not complete: " + ",".join(b.wave_id for b in instance.blocking)
        label = labelled(dict(_facts_base(fleet, date, ride, limit), enumeration_complete=False, result=None, day_bounds=None,
                              checker_ok=None, crosscheck_status="not_run", wave_values_status="not_run"))
        label = settle_label(label, forced=None if label["day_status"] == "not_run_enumeration_cap" else "rejected")
        apply_label(label)
        return finish(label["day_status"], note)

    # J2 bounds and certificate
    try:
        bnds, records = day_bounds(instance, fleet, limit, deps, cfg, errors, tag)
    except bounds_mod.WaveInfeasible as exc:
        errors.append(f"{tag}: {exc}")
        return finish("rejected", f"wave infeasible: {exc}")
    wstatus = wave_values_status(records)
    row["wave_values_status"] = wstatus
    by_key = {(r.kind, r.wave_id): r for r in records}
    for r in records:  # both solvers' values of every wave, whether or not a bound contributes
        out["lb_rows"].append(dict(base, bound=f"wave_{r.kind}", value=r.used.value, point="",
                                   contributions=f"{r.wave_id}:{r.used.value}:{r.used.proof}",
                                   wave_value_source=f"{r.detail};verdict={r.verdict}",
                                   used_value=(r.in_bounds or r.used).value, used_proof=(r.in_bounds or r.used).proof))
    for name in ("lb0", "lb0w", "lb_l", "lb_s"):
        b = getattr(bnds, name)
        if b is not None:
            row[{"lb_l": "lb_L", "lb_s": "lb_S"}.get(name, name)] = b.value
            kind = "l" if name == "lb_l" else "k_any"
            src = ";".join(f"{c.wave_id}={by_key[(kind, c.wave_id)].verdict}" for c in b.contributions if (kind, c.wave_id) in by_key)
            out["lb_rows"].append(dict(base, bound=name, value=b.value, point=b.point,
                                       contributions=";".join(f"{c.wave_id}:{c.value}:{c.proof}" for c in b.contributions),
                                       wave_value_source=src))
    certificate = None
    if bnds.certificate is not None:
        c = bnds.certificate
        row["certificate_tier"] = c.tier
        out["lb_rows"].append(dict(base, bound="certificate", value=c.lower_bound, point=c.point,
                                   contributions=";".join(f"{x.wave_id}:{x.value}:{x.proof}" for x in c.contributions),
                                   wave_value_source=f"{c.kind};wave_values={wstatus}"))
        certificate = {"tier": c.tier, "kind": c.kind, "lower_bound": c.lower_bound, "point": c.point, "large_limit": c.large_limit,
                       "contributions": [(x.wave_id, x.value, x.proof) for x in c.contributions]}
        label = labelled(dict(_facts_base(fleet, date, ride, limit), solve_status="certificate", objective=None,
                              stage_statuses=[], timing_dependent=False, non_lexicographic=False, bound_above_incumbent=False,
                              crosscheck_status="not_run", wave_values_status=wstatus, stage1_bound_ceil=None,
                              bounds={n: _bound_dict(getattr(bnds, n)) for n in ("lb0", "lb0w", "lb_l", "lb_s")},
                              certificate=certificate, certificate_tier=c.tier, enumeration_complete=True, result=None,
                              day_bounds=bnds, checker_ok=None))
        if label["day_status"] == "rejected":  # a blocking wave verdict or an inconsistent certificate: nothing more to solve
            apply_label(label)
            return finish("rejected", label.get("reason", ""))
        if label["day_status"] == "infeasible_certified" and label["proof_claim_allowed"]:
            apply_label(label)
            return finish("infeasible_certified", f"{c.kind}: LB_L {c.lower_bound} > L {c.large_limit}")
        # an unclaimed (tier-2 without two-solver wave agreement) certificate: the day MIP is still solved below
        out["note_prefix"] = f"tier-{c.tier} certificate withheld ({label.get('proof_claim_reason', '')})"

    # J3/J4 primary solver, J5 cross-check
    kw = dict(aggregate=cfg.aggregate)
    if fleet.typed:
        kw.update(large_limit=limit, fixed_type=fleet.fixed_id, minimised_type=fleet.minimised_id)
    highs = deps.highs_run(instance, settings=hb.HighsSettings(time_limit=cfg.time_limit), **kw)
    if highs.status == "backend_unavailable":
        raise BackendUnavailable(f"{tag}: highs: {highs.note}")
    out["stages"] += _stage_rows(base, "highs", highs)
    out["versions"]["highs"] = highs.solver_version
    out["mps"] = {f"{tag}|stage{s.stage}": s.mps_sha256 for s in highs.stages if s.mps_sha256}
    cc_status = "not_run"
    guro = None
    if deps.gurobi_run is not None:
        guro = deps.gurobi_run(instance, settings=gdb.GurobiSettings(time_limit=cfg.time_limit, work_limit=cfg.work_limit), **kw)
        if guro.status == "backend_unavailable":
            raise BackendUnavailable(f"{tag}: gurobi: {guro.note}")
        out["stages"] += _stage_rows(base, "gurobi", guro)
        out["versions"]["gurobi"] = guro.solver_version
        cc = gdb.crosscheck_day_results(highs, guro)
        cc_status = cc.verdict
        row["crosscheck_solver"] = "gurobi"
        if cc.verdict == gdb.BLOCKING:
            errors.append(f"{tag}: solver disagreement: " + "; ".join(s.detail for s in cc.stages if s.verdict == gdb.BLOCKING))
    row.update(crosscheck_status=cc_status, timing_dependent=highs.timing_dependent, non_lexicographic=highs.non_lexicographic)

    # certification, checker, TS confirmation of the incumbent
    status_override = "rejected" if cc_status == gdb.BLOCKING or highs.status == "rejected" else None
    notes = []
    plan = plan_from_result(instance, highs) if highs.objective is not None else None
    plan_ok = None  # the independent checker's verdict on the plan (None: no plan)
    if plan is not None:
        try:
            problems = certify_plan(fleet, instance, plan, arcs_doc)
            report = check_plan(fleet, instance, plan, arcs_doc, waves_checker, limit, highs.objective)
        except Exception as exc:  # noqa: BLE001 - a defect in a plan is a rejected cell, never a crash of the campaign
            problems, report = [f"plan check raised {type(exc).__name__}: {exc}"], None
        if report is not None and not report.ok:
            problems += [f"checker {v.code}: {v.where}" for v in report.violations[:5]]
        row["checker_ok"] = plan_ok = report is not None and report.ok and not problems
        if problems:
            status_override = "rejected"
            errors.extend(f"{tag}: {p}" for p in problems)
            notes.append("; ".join(problems[:3]))
        if report is not None:
            peak_type = fleet.minimised_id if fleet.typed else instance.types[0].type_id
            row.update(K_or_S=report.peaks_centi.get(peak_type, 0), total_minutes=report.total_minutes, routes=report.route_count,
                       large_peak=report.peaks_centi.get(fleet.fixed_id, 0) if fleet.typed else "",
                       car_minutes=report.minutes_by_type.get(fleet.minimised_id, 0) if fleet.typed else "")
        ts, detail = ts_confirm(fleet, instance, plan, limit, highs.objective, deps, tag)
        row["ts_confirmation"] = ts
        if ts == "failed":
            status_override = "rejected"
            errors.append(f"{tag}: TypeScript confirmation failed: {detail}")
            notes.append(f"ts: {detail}")
        elif ts == "missing":
            errors.append(f"{tag}: TypeScript confirmation missing: {detail}")
        out["plan"] = {"routes": [
            {"wave_id": dw.wave_id, "type_id": r.type_id, "occurrence_ids": list(r.occurrence_ids), "tour": r.tour,
             "start": dw.wave.anchor_minutes - r.tour if dw.wave.direction == "pickup" else dw.wave.anchor_minutes,
             "end": dw.wave.anchor_minutes if dw.wave.direction == "pickup" else dw.wave.anchor_minutes + r.tour}
            for wi, dw in enumerate(instance.waves) for r in plan[wi]]}

    stage1 = highs.stages[0].result if highs.stages else None
    stage_results = [s.result for s in highs.stages] + [st.result for st in (guro.stages if guro is not None else ())]
    facts = dict(_facts_base(fleet, date, ride, limit), solve_status=highs.status, objective=highs.objective,
                 stage_statuses=[s.result.status for s in highs.stages], timing_dependent=highs.timing_dependent,
                 non_lexicographic=highs.non_lexicographic,
                 bound_above_incumbent=any(str(r.solver_message or "").startswith(hb.BOUND_ABOVE_INCUMBENT) for r in stage_results),
                 crosscheck_status=cc_status, wave_values_status=wstatus,
                 stage1_bound_ceil=None if stage1 is None else stage1.bound_ceil,
                 bounds={n: _bound_dict(getattr(bnds, n)) for n in ("lb0", "lb0w", "lb_l", "lb_s")}, certificate=None,
                 certificate_tier=None if certificate is None else certificate["tier"],
                 enumeration_complete=True, result=highs, day_bounds=bnds, checker_ok=plan_ok)
    label = settle_label(labelled(facts), forced=status_override)  # the runner's own rejection is final
    apply_label(label)
    note = " | ".join(x for x in (out.get("note_prefix"), " | ".join(notes), label.get("reason"), highs.note) if x)
    if status_override is not None:
        note = " | ".join(notes) or "solver disagreement or rejected stage"
    return finish(label["day_status"], note)


# ---------------------------------------------------------------- output
def write_csv(path: Path, fields, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(fields), lineterminator="\n", extrasaction="raise")
        wr.writeheader()
        wr.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)


def week_rows(rows: list) -> list:
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["fleet"], r["R"], r["L"]), []).append(r)
    out = []
    for (fleet, ride, limit), items in groups.items():
        values = [r["K_or_S"] for r in items if r["K_or_S"] != ""]
        out.append({"fleet": fleet, "R": ride, "L": limit, "dates": len(items), "weekly_fleet_max": max(values) if values else "",
                    "vehicle_days_sum": sum(values) if values else "",
                    "cells_not_proven": sum(1 for r in items if r["proof_claim_allowed"] is not True),
                    "cells_without_value": len(items) - len(values)})
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_state(out: Path) -> tuple:
    return wg._git_state(out)


def check_out(out: Path, sources: list) -> str:
    """Refusal text for an unsafe ``--out`` (E04 plus: not an existing non-empty folder, not inside a results folder)."""
    for source in sources:
        refusal = wg.check_out_dir(out, source)
        if refusal:
            return refusal
    out_r = Path(out).resolve()
    if out_r.exists() and (not out_r.is_dir() or any(out_r.iterdir())):
        return "--out exists and is not an empty directory; results are never overwritten"
    results = (REPO / wg.RESULTS_REL).resolve()
    for parent in out_r.parents:
        if parent == results or results not in parent.parents:
            break
        if parent.is_dir() and any(parent.glob("*manifest*.json")):
            return f"--out lies inside an existing results folder ({parent.name})"
    return ""


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fleets", default=",".join(FLEET_NAMES))
    ap.add_argument("--rides", default="", help="comma list of R values (default: all)")
    ap.add_argument("--dates", default="", help="comma list of service dates (default: all)")
    ap.add_argument("--limits", default="", help="comma list of L values of the typed fleets (default: the campaign's)")
    ap.add_argument("--time-limit", type=positive_float, default=DEFAULT_TIME_LIMIT, help="seconds per solver call (default 600)")
    ap.add_argument("--run-label", type=run_label_text, default="", help="required when --time-limit is not 600")
    ap.add_argument("--jobs", type=serial_jobs, default=1)
    ap.add_argument("--crosscheck", action=argparse.BooleanOptionalAction, default=True,
                    help="Gurobi cross-check (E14 Q5; required for paper cells; default on)")
    ap.add_argument("--aggregate", action=argparse.BooleanOptionalAction, default=True, help="duration aggregation (J3)")
    ap.add_argument("--work-limit", type=positive_float, default=None, help="Gurobi work limit (from the J10 calibration)")
    ap.add_argument("--wave-values", choices=("sp", "trivial"), default="sp")
    ap.add_argument("--allow-dirty", action="store_true", help="development run on a dirty tree (flagged in the manifest)")
    return ap.parse_args(argv)


def main(argv=None, deps: Optional[Deps] = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    out = Path(args.out)
    names = [n for n in args.fleets.split(",") if n]
    try:
        rides_f, limits_f = int_list(args.rides, "--rides"), int_list(args.limits, "--limits")
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    dates_f = [d for d in args.dates.split(",") if d]
    unknown = [n for n in names if n not in SOURCE_PATHS]
    if unknown or not names:
        print(f"refused: unknown fleet(s) {unknown}; valid: {list(FLEET_NAMES)}", file=sys.stderr)
        return 2
    cfg = Config(args.time_limit, args.work_limit, args.crosscheck, args.aggregate, args.wave_values, args.run_label)
    sensitivity = cfg.time_limit != DEFAULT_TIME_LIMIT
    if sensitivity and not cfg.run_label:
        print("refused: a --time-limit other than 600 needs a --run-label (sensitivity run, never pooled)", file=sys.stderr)
        return 2
    refusal = check_out(out, [SOURCE_PATHS[n] for n in names])
    if refusal:  # before any work
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    commit, dirty = git_state(out)
    if dirty and not args.allow_dirty:
        print("refused: the working tree is dirty (E06: clean serial runs); commit first or pass --allow-dirty for a development run",
              file=sys.stderr)
        return 2
    t_start = time.perf_counter()
    try:
        provenance = tm._provenance()
        fleets = [load_fleet(n) for n in names]
    except (loader.CampaignRefused, loader.InputRejected, KeyError, OSError, ValueError, RuntimeError) as exc:
        print(f"input_rejected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    deps = deps or real_deps(cfg)
    rows, stage_rows, lb_rows, plans, mps, errors, cell_log, columns_per_day = [], [], [], {}, {}, [], [], {}
    versions: dict = {}
    try:
        for fleet in fleets:
            dates = sorted({w.service_date for w in fleet.campaign.waves_for(fleet.campaign.rides[0])})
            for ride in rides_f or list(fleet.campaign.rides):
                for date in dates_f or dates:
                    for limit in (limits_f or list(fleet.l_values)) if fleet.typed else [None]:
                        try:
                            res = solve_cell(fleet, date, ride, limit, cfg, deps)
                        except BackendUnavailable as exc:
                            print(f"backend unavailable: {exc}; the run stops (E06), nothing is written", file=sys.stderr)
                            return 3
                        rows.append(res["row"])
                        stage_rows += res["stages"]
                        lb_rows += res["lb_rows"]
                        mps.update(res["mps"])
                        versions.update({k: v for k, v in res["versions"].items() if v})
                        errors += res["errors"]
                        if res["plan"] is not None:
                            plans[f"{fleet.name}|{date}|R{ride}|L{'-' if limit is None else limit}"] = res["plan"]
                        if res["columns"] is not None:
                            columns_per_day[f"{fleet.name}|{date}|R{ride}"] = res["columns"]
                        cell_log.append({"cell": f"{fleet.name}|{date}|R{ride}|L{'-' if limit is None else limit}",
                                         "wall_seconds": res["row"]["wall_seconds"], "day_status": res["row"]["day_status"]})
                        print(f"{cell_log[-1]['cell']}: {res['row']['day_status']} K_or_S={res['row']['K_or_S']} "
                              f"({res['row']['wall_seconds']} s)", flush=True)
    finally:
        deps.close()

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "day_joint.csv", CSV_FIELDS, rows)
    write_csv(out / "day_joint_stages.csv", STAGE_FIELDS, stage_rows)
    write_csv(out / "day_joint_week.csv", WEEK_FIELDS, week_rows(rows))
    write_csv(out / "lb0.csv", LB_FIELDS, lb_rows)
    (out / "day_joint_plans.json").write_text(json.dumps(plans, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    wall = round(time.perf_counter() - t_start, 1)
    hs, gs = hb.HighsSettings(time_limit=cfg.time_limit), gdb.GurobiSettings(time_limit=cfg.time_limit, work_limit=cfg.work_limit)
    solvers = {"highs": {"name": "highs", "version": versions.get("highs") or "not_run",
                         "options": hs.option_string(), "threads": hs.threads, "seed": hs.seed, "time_limit_seconds": cfg.time_limit,
                         "work_limit": None}}
    if cfg.crosscheck:
        solvers["gurobi"] = {"name": "gurobi", "version": versions.get("gurobi") or "not_run", "options": gs.solver_options_string(), "threads": gs.threads,
                             "seed": gs.seed, "time_limit_seconds": cfg.time_limit, "work_limit": cfg.work_limit}
    manifest = {
        "protocol": protocol.DAY_JOINT_PROTOCOL_ID, "schema_version": protocol.DAY_JOINT_MANIFEST_SCHEMA_VERSION,
        "work_package": WORK_PACKAGE, "git_commit": commit, "dirty_working_tree": bool(dirty), "development_run": bool(dirty) or not cfg.crosscheck or cfg.wave_values != "sp",
        "python_provenance": provenance, "python_version": platform.python_version(), "host_os": ab.host_description(),
        "run_label": cfg.run_label, "sensitivity_run": sensitivity,
        "source_manifests": {f.name: {"path": wg._rel(f.path), "manifest_sha256": sha256_file(f.path / "run_manifest.json"),
                                      "git_commit": str(f.manifest.get("git_commit")),
                                      "fixed_type": f.fixed_id, "minimised_type": f.minimised_id} for f in fleets},
        "solvers": solvers, "crosscheck_enabled": cfg.crosscheck, "aggregate": cfg.aggregate, "wave_values": cfg.wave_values,
        "enumeration": dict(protocol.ENUMERATION_CAPS, columns_per_day=columns_per_day),
        "mps_sha256": mps, "output_sha256": {n: sha256_file(out / n) for n in OUT_FILES},
        "tools": dict(ud.tool_versions(), cli_command=" ".join(ud.CLI_COMMAND)),
        "options": {"fleets": names, "rides": rides_f, "dates": dates_f, "limits": limits_f},
        "run_history": {"invocations": [{"serial": True, "jobs": args.jobs, "wall_seconds": wall}], "jobs": args.jobs, "cache": "none",
                        "cells_planned": len(rows), "cells_solved": sum(1 for r in rows if r["day_status"] not in ("input_rejected",)),
                        "cells": cell_log},
        "claim": protocol.DAY_JOINT_CLAIM, "blocking_errors": errors, "total_wall_seconds": wall,
    }
    problems = protocol.validate_day_joint_manifest(manifest) + strict_manifest_problems(manifest)
    if problems:
        errors.extend(f"manifest: {p}" for p in problems)
        manifest["blocking_errors"] = errors
    (out / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    summary = {}
    for r in rows:
        summary[r["day_status"]] = summary.get(r["day_status"], 0) + 1
    print(json.dumps(summary, sort_keys=True))
    if errors:
        print(f"{len(errors)} blocking error(s):", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
