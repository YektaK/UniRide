"""The single definition of the ``exact_reference_v1`` protocol (design
docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 4; WP-E2).

* A separate protocol: neither the fixed-budget primary protocol nor native termination (A04).
  No objective-evaluation budget; a solver time/work limit instead. Exact rows are never ranked,
  averaged or tested statistically together with heuristic rows (``assert_not_pooled``).
* Status labels: the per-stage/per-wave labels of section 4. The set itself lives in
  ``uniride_core.exact.EXACT_STATUSES`` because core must not import academic_benchmark; this
  module gives each label its protocol meaning, and a test keeps the two identical.
* ``exact_manifest.json`` (one per campaign): required fields and ``validate_manifest``. The
  manifest never holds absolute paths, user names, e-mail addresses or license text; the AMPL
  location is recorded only as "local AMPL installation used" (section 7).
"""
from __future__ import annotations

import re
from typing import Iterable, List, Mapping

from uniride_core.exact import EXACT_STATUSES
from uniride_core.exact.route_enumeration import COLUMN_CAP_DEFAULT, LABEL_CAP_DEFAULT, WALL_CLOCK_LIMIT_DEFAULT

PROTOCOL_ID = "exact_reference_v1"
MANIFEST_FILENAME = "exact_manifest.json"
MANIFEST_SCHEMA_VERSION = 1

STATUS_LABELS = {
    "optimal": "Incumbent certified and the solver reports optimal with absgap < 1 (integer data).",
    "feasible_with_gap": "Certified incumbent and a valid bound, not closed within the limit.",
    "bound_only": "Valid bound, no incumbent.",
    "infeasible_proven": "The solver proves that no feasible solution exists.",
    "rejected": "Certificate, objective cross-check or solver run failed (an error to investigate).",
    "backend_unavailable": "AMPL, a solver or its license is missing.",
    "input_rejected": "The archive is inconsistent (sha, class cross-check, arc values).",
    "timing_dependent_abort": "Enumeration hit its wall-clock safety limit before a count cap; no model switch.",
    "skipped_no_stage1_incumbent": "Stage 2 skipped because stage 1 has no incumbent (section 1.1).",
}
if set(STATUS_LABELS) != set(EXACT_STATUSES) - {"not_run"}:  # pragma: no cover - guarded by a test as well
    raise ImportError("exact_reference_v1 status labels differ from uniride_core.exact.EXACT_STATUSES")

# Section 4 names the first four. WP-E2 adds two observed solver outcomes (to be confirmed in review):
# "gap_tolerance" (solver says solved but incumbent - ceil(bound) >= 1) and "solver_failure"
# (AMPL solve_result failure/unbounded, or a fractional incumbent): both never count as optimal.
STOP_REASONS = {
    "optimal": "Proven optimal.",
    "work_limit": "Deterministic work limit (Gurobi lim:work).",
    "wall_limit": "Wall-clock limit (lim:time); always timing_dependent.",
    "infeasible": "Proven infeasible.",
    "gap_tolerance": "Solver reported solved but the integer gap is not closed.",
    "solver_failure": "Solver failure or an invalid (fractional) incumbent.",
    "other_limit": "Another solver limit.",
}
STAGES = ("stage1", "stage2", "free")
MODELS = ("SP", "compact")
AMPL_LOCATION_VALUES = ("local AMPL installation used", "amplpy default lookup")
WALL_LIMIT_SECONDS = 60  # owner decisions EQ1, D-C (per solver call)
PEAK_WALL_LIMIT_SECONDS = 600  # every call on a peak wave (D-B)
THREADS = 1
ENUMERATION_CAPS = {"column_cap": COLUMN_CAP_DEFAULT, "label_cap": LABEL_CAP_DEFAULT,
                    "wall_clock_limit_seconds": int(WALL_CLOCK_LIMIT_DEFAULT)}

MANIFEST_FIELDS = {
    "protocol": str, "schema_version": int, "git_commit": str, "dirty_working_tree": bool,
    "source_campaign": dict, "matrix_sha256": dict, "peak_waves": dict, "ampl": dict, "solver": dict,
    "enumeration": dict, "waves": list, "python_version": str, "host_os": str,
}
SOLVER_FIELDS = ("name", "version", "option_string", "threads", "seed", "time_limit_seconds",
                 "peak_time_limit_seconds", "work_limit", "peak_work_limit", "mip_gap", "mip_gap_abs")
WAVE_FIELDS = ("wave_id", "service_date", "R", "peak", "model", "columns", "labels", "stages")
STAGE_FIELDS = ("stage", "status", "stop_reason", "timing_dependent", "non_lexicographic", "objective", "bound",
                "wall_seconds")
_INCUMBENT_STATUSES = ("optimal", "feasible_with_gap")
_NO_RUN_STATUSES = ("skipped_no_stage1_incumbent", "backend_unavailable", "input_rejected", "timing_dependent_abort")

_ABS_PATH = re.compile(r"(^|[\s\"'=(])([A-Za-z]:[\\/]|\\\\|/(Users|home|root|mnt|tmp|var|opt)/)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LICENSE = re.compile(r"licen[cs]e|licensee|registered to", re.I)
_BARE_BESTBOUND = re.compile(r"(^|\s)bestbound=")


def _strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, Mapping):
        for k, v in obj.items():
            yield from _strings(k, f"{path}.<key>") if isinstance(k, str) else ()
            yield from _strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


def private_data_errors(obj) -> List[str]:
    """Absolute paths, e-mail addresses and license text anywhere in a manifest or row."""
    errors = []
    for where, text in _strings(obj):
        if _ABS_PATH.search(text):
            errors.append(f"{where}: absolute path not allowed")
        if _EMAIL.search(text):
            errors.append(f"{where}: e-mail address not allowed")
        if _LICENSE.search(text):
            errors.append(f"{where}: license text not allowed")
    return errors


def validate_stage_row(row: Mapping) -> List[str]:
    errors = [f"stage row: missing {f}" for f in STAGE_FIELDS if f not in row]
    if errors:
        return errors
    stage, status, reason = row["stage"], row["status"], row["stop_reason"]
    if stage not in STAGES:
        errors.append(f"stage {stage!r} unknown")
    if status not in STATUS_LABELS:
        errors.append(f"status {status!r} unknown")
    if reason is not None and reason not in STOP_REASONS:
        errors.append(f"stop_reason {reason!r} unknown")
    if reason is None and status not in _NO_RUN_STATUSES:
        errors.append(f"stop_reason missing for status {status!r}")
    if status == "skipped_no_stage1_incumbent" and stage != "stage2":
        errors.append("skipped_no_stage1_incumbent is a stage-2 status")
    if reason == "wall_limit" and row["timing_dependent"] is not True:
        errors.append("a wall_limit stop must be timing_dependent: true")
    if row["non_lexicographic"] and stage != "stage2":
        errors.append("non_lexicographic applies to stage 2 only")
    if status in _INCUMBENT_STATUSES and row["objective"] is None:
        errors.append(f"status {status!r} needs an incumbent objective")
    if status == "optimal" and reason != "optimal":
        errors.append("status optimal needs stop_reason optimal")
    return errors


def validate_manifest(doc: Mapping) -> List[str]:
    """Return a list of schema errors (empty when valid); never mutates ``doc``."""
    errors = []
    for name, typ in MANIFEST_FIELDS.items():
        if name not in doc:
            errors.append(f"missing field {name}")
        elif not isinstance(doc[name], typ) or (typ is int and isinstance(doc[name], bool)):
            errors.append(f"field {name} must be {typ.__name__}")
    if errors:
        return errors + private_data_errors(doc)
    if doc["protocol"] != PROTOCOL_ID:
        errors.append(f"protocol must be {PROTOCOL_ID!r}")
    if doc["schema_version"] != MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {MANIFEST_SCHEMA_VERSION}")
    if not re.fullmatch(r"[0-9a-f]{7,40}", doc["git_commit"]):
        errors.append("git_commit must be a hex commit id")
    src = doc["source_campaign"]
    if not isinstance(src.get("path"), str) or not re.fullmatch(r"[0-9a-f]{64}", str(src.get("manifest_sha256"))):
        errors.append("source_campaign needs a relative path and a manifest_sha256")
    for key, sha in doc["matrix_sha256"].items():
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}_R\d+", key) or not re.fullmatch(r"[0-9a-f]{64}", str(sha)):
            errors.append(f"matrix_sha256 entry {key!r} invalid")
    ampl = doc["ampl"]
    for f in ("version", "amplpy_version", "location"):
        if not ampl.get(f):
            errors.append(f"ampl.{f} missing")
    if ampl.get("location") not in AMPL_LOCATION_VALUES:
        errors.append(f"ampl.location must be one of {AMPL_LOCATION_VALUES}")
    solver = doc["solver"]
    for f in SOLVER_FIELDS:
        if f not in solver:
            errors.append(f"solver.{f} missing")
    if solver.get("threads") != THREADS:
        errors.append(f"solver.threads must be {THREADS} (section 4)")
    if (solver.get("time_limit_seconds"), solver.get("peak_time_limit_seconds")) != (WALL_LIMIT_SECONDS, PEAK_WALL_LIMIT_SECONDS):
        errors.append("solver time limits must be 60 s and 600 s on peak waves (EQ1, D-C)")
    if _BARE_BESTBOUND.search(str(solver.get("option_string", ""))):
        errors.append("solver.option_string uses the bare bestbound=1 (use mip:bestbound=1, F17)")
    for f, want in ENUMERATION_CAPS.items():
        if doc["enumeration"].get(f) != want:
            errors.append(f"enumeration.{f} must be {want}")
    for i, wave in enumerate(doc["waves"]):
        missing = [f for f in WAVE_FIELDS if f not in wave]
        if missing:
            errors.append(f"waves[{i}] missing {missing}")
            continue
        if wave["model"] not in MODELS:
            errors.append(f"waves[{i}].model must be one of {MODELS}")
        for row in wave["stages"]:
            errors.extend(f"waves[{i}]: {e}" for e in validate_stage_row(row))
    return errors + private_data_errors(doc)


def assert_not_pooled(rows: Iterable[Mapping]) -> None:
    """Raise ValueError unless every row carries ``protocol = exact_reference_v1``."""
    bad = sorted({str(r.get("protocol")) for r in rows if r.get("protocol") != PROTOCOL_ID})
    if bad:
        raise ValueError(f"exact_reference_v1 rows must not be pooled with other protocols: {bad}")
