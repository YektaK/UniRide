"""The single definition of the ``exact_reference_v1`` protocol (design
docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 4; WP-E2).

* A separate protocol: neither the fixed-budget primary protocol nor native termination (A04).
  No objective-evaluation budget; a solver time/work limit instead. Exact rows are never ranked,
  averaged or tested statistically together with heuristic rows (``assert_not_pooled``).
* Status labels: the per-stage/per-wave labels of section 4. The set itself lives in
  ``uniride_core.exact.EXACT_STATUSES`` because core must not import academic_benchmark; this
  module gives each label its protocol meaning, refuses to import if the two differ, and a test
  keeps them identical.
* ``wall_seconds`` in a stage row is the wall time of the AMPL ``solve`` call: it includes AMPL's
  model generation and the solver start, while ``lim:time`` limits only the solver run.
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

# Section 4. gap_tolerance, solver_failure and other_limit were accepted by the owner on 2026-10-16
# (DECISION_LOG E03); other_limit counts as timing_dependent, like wall_limit.
STOP_REASONS = {
    "optimal": "Proven optimal.",
    "work_limit": "Deterministic work limit (Gurobi lim:work).",
    "wall_limit": "Wall-clock limit (lim:time); always timing_dependent.",
    "infeasible": "Proven infeasible.",
    "gap_tolerance": "Solver reported solved but the integer gap is not closed.",
    "solver_failure": "Solver failure or an invalid (fractional) incumbent.",
    "other_limit": "Another solver limit; always timing_dependent.",
}
TIMING_STOP_REASONS = ("wall_limit", "other_limit")
STAGES = ("stage1", "stage2", "free")
MODELS = ("SP", "compact")
AMPL_LOCATION_VALUES = ("local AMPL installation used", "amplpy default lookup")
WALL_LIMIT_SECONDS = 60  # owner decisions EQ1, D-C (per solver call)
PEAK_WALL_LIMIT_SECONDS = 600  # every call on a peak wave (D-B)
THREADS = 1
GUROBI_WORK_LIMIT = 20  # work units per call; owner decision 2026-10-16 (E03)
GUROBI_PEAK_WORK_LIMIT = 200  # every call on a peak wave
ENUMERATION_CAPS = {"column_cap": COLUMN_CAP_DEFAULT, "label_cap": LABEL_CAP_DEFAULT,
                    "wall_clock_limit_seconds": int(WALL_CLOCK_LIMIT_DEFAULT)}

MANIFEST_FIELDS = {
    "protocol": str, "schema_version": int, "git_commit": str, "dirty_working_tree": bool,
    "matrix_sha256": dict, "peak_waves": dict, "ampl": dict, "solver": dict,
    "enumeration": dict, "waves": list, "python_version": str, "host_os": str,
}
SOLVER_FIELDS = ("name", "version", "option_string", "peak_option_string", "threads", "seed", "time_limit_seconds",
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
    if reason in TIMING_STOP_REASONS and row["timing_dependent"] is not True:
        errors.append(f"a {reason} stop must be timing_dependent: true")
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
    # One source campaign (``source_campaign``, WP-E3) or several (``source_campaigns``: name -> campaign, WP-E4a).
    sources = []
    if isinstance(doc.get("source_campaign"), dict):
        sources.append(("source_campaign", doc["source_campaign"]))
    if isinstance(doc.get("source_campaigns"), dict):
        sources.extend((f"source_campaigns[{name}]", src) for name, src in doc["source_campaigns"].items())
    if not sources:
        errors.append("missing field source_campaign (or a non-empty source_campaigns)")
    for label, src in sources:
        if not isinstance(src, dict) or not isinstance(src.get("path"), str) or not re.fullmatch(
                r"[0-9a-f]{64}", str(src.get("manifest_sha256"))):
            errors.append(f"{label} needs a relative path and a manifest_sha256")
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
    errors.extend(_option_string_errors(solver))
    for f, want in ENUMERATION_CAPS.items():
        if doc["enumeration"].get(f) != want:
            errors.append(f"enumeration.{f} must be {want}")
    peak_ids = {w for v in doc["peak_waves"].values() if isinstance(v, Mapping) for w in v.get("wave_ids", ())}
    for i, wave in enumerate(doc["waves"]):
        missing = [f for f in WAVE_FIELDS if f not in wave]
        if missing:
            errors.append(f"waves[{i}] missing {missing}")
            continue
        if wave["peak"] is not (wave["wave_id"] in peak_ids):
            errors.append(f"waves[{i}].peak must be {wave['wave_id'] in peak_ids} (peak_waves list, D-B)")
        if wave["model"] not in MODELS:
            errors.append(f"waves[{i}].model must be one of {MODELS}")
        for row in wave["stages"]:
            errors.extend(f"waves[{i}]: {e}" for e in validate_stage_row(row))
    return errors + private_data_errors(doc)


def _g(value) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)


def _option_string_errors(solver: Mapping) -> List[str]:
    """The verbatim option strings must agree with the declared limits, threads and seed."""
    errors = []
    name = solver.get("name")
    if name == "gurobi" and (solver.get("work_limit"), solver.get("peak_work_limit")) != (GUROBI_WORK_LIMIT, GUROBI_PEAK_WORK_LIMIT):
        errors.append(f"solver.work_limit/peak_work_limit must be {GUROBI_WORK_LIMIT}/{GUROBI_PEAK_WORK_LIMIT} for gurobi (E03)")
    if name != "gurobi" and (solver.get("work_limit"), solver.get("peak_work_limit")) != (None, None):
        errors.append("solver.work_limit applies to gurobi only (null otherwise)")
    for key, time_key, work_key in (("option_string", "time_limit_seconds", "work_limit"),
                                    ("peak_option_string", "peak_time_limit_seconds", "peak_work_limit")):
        text = str(solver.get(key, ""))
        tokens = text.split()
        if _BARE_BESTBOUND.search(text):
            errors.append(f"solver.{key} uses the bare bestbound=1 (use mip:bestbound=1, F17)")
        if "mip:bestbound=1" not in tokens:
            errors.append(f"solver.{key} must request mip:bestbound=1")
        if f"lim:time={_g(solver.get(time_key))}" not in tokens:
            errors.append(f"solver.{key} lim:time disagrees with solver.{time_key}")
        if f"tech:threads={solver.get('threads')}" not in tokens:
            errors.append(f"solver.{key} tech:threads disagrees with solver.threads")
        work = solver.get(work_key)
        works = [t for t in tokens if t.startswith("lim:work=")]
        if (work is None and works) or (work is not None and works != [f"lim:work={_g(work)}"]):
            errors.append(f"solver.{key} lim:work disagrees with solver.{work_key}")
    return errors


def assert_not_pooled(rows: Iterable[Mapping]) -> None:
    """Raise ValueError unless every row carries ``protocol = exact_reference_v1``."""
    bad = sorted({str(r.get("protocol")) for r in rows if r.get("protocol") != PROTOCOL_ID})
    if bad:
        raise ValueError(f"exact_reference_v1 rows must not be pooled with other protocols: {bad}")


# ---------------------------------------------------------------------------------------------------------------
# union_day_v1 (WP-E4b manifest; moved here from scripts/run_exact_union_day.py by WP-E6, design section 1.5
# "Manifest validator"). The union-menu day level is a CP-SAT selection over the GA menus and the per-wave exact menus.
# It is its own protocol id: it is neither exact_reference_v1 nor a heuristic row, and is never pooled with either.
# ---------------------------------------------------------------------------------------------------------------
UNION_DAY_PROTOCOL_ID = "union_day_v1"
UNION_DAY_MANIFEST_FILENAME = "union_day_manifest.json"
UNION_DAY_TIME_SCALE = 100  # centi-minutes, as the producer and the router (F16)
UNION_DAY_REQUIRED_KEYS = (
    "protocol", "work_package", "git_commit", "dirty_working_tree", "source_campaigns", "exact_options_source", "cpsat",
    "time_scale", "router_caps", "tools", "python_provenance", "python_version", "host_os", "run_history", "claim",
    "ga_recompute", "labels", "blocking_errors", "total_wall_seconds")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def validate_union_day_manifest(manifest: Mapping) -> List[str]:
    """Schema errors of a ``union_day_manifest.json`` (empty when valid); never mutates ``manifest``."""
    from uniride_core.planning import union_day_menu as udm  # lazy: keeps the exact_reference_v1 import path light

    problems = [f"missing {k}" for k in UNION_DAY_REQUIRED_KEYS if k not in manifest]
    if manifest.get("protocol", UNION_DAY_PROTOCOL_ID) != UNION_DAY_PROTOCOL_ID:
        problems.append(f"protocol must be {UNION_DAY_PROTOCOL_ID!r}")
    if "time_scale" in manifest and manifest["time_scale"] != UNION_DAY_TIME_SCALE:
        problems.append(f"time_scale must be {UNION_DAY_TIME_SCALE}")
    if "claim" in manifest and manifest["claim"] != udm.CLAIM:
        problems.append("claim text differs from the design wording")
    if "git_commit" in manifest and not re.fullmatch(r"[0-9a-f]{7,40}", str(manifest["git_commit"])):
        problems.append("git_commit must be a hex commit id")
    if "dirty_working_tree" in manifest and not isinstance(manifest["dirty_working_tree"], bool):
        problems.append("dirty_working_tree must be bool")
    if "labels" in manifest and (not isinstance(manifest["labels"], Mapping)
                                 or set(manifest["labels"]) != set(udm.LABELS)):
        problems.append(f"labels must carry exactly the keys {sorted(udm.LABELS)}")
    sources = manifest.get("source_campaigns")
    if "source_campaigns" in manifest:
        if not isinstance(sources, Mapping) or not sources:
            problems.append("source_campaigns must be a non-empty mapping")
        else:
            for name, src in sources.items():
                if not isinstance(src, Mapping) or not isinstance(src.get("path"), str) \
                        or not _SHA256.fullmatch(str(src.get("manifest_sha256"))):
                    problems.append(f"source_campaigns[{name}] needs a relative path and a manifest_sha256")
    exact = manifest.get("exact_options_source")
    if "exact_options_source" in manifest:
        if not isinstance(exact, Mapping):
            problems.append("exact_options_source must be a mapping")
        else:
            for key in ("exact_routes_sha256", "option_gaps_sha256", "manifest_sha256"):
                if not _SHA256.fullmatch(str(exact.get(key))):
                    problems.append(f"exact_options_source.{key} must be a sha256")
    problems.extend(private_data_errors(manifest))
    return problems


# ---------------------------------------------------------------------------------------------------------------
# WP-E7 (GOAL 2 stage 1, DECISION_LOG E09): the TSP/ATSP reference manifest. Rows are Hamiltonian-cycle rows of
# the same protocol id (exact_reference_v1); the manifest is its own kind, so ``validate_manifest`` (wave
# campaigns) and ``validate_union_day_manifest`` are unchanged. The published TSPLIB optimum is a reference
# value (``reference_optimum``, source ``tsplib``), never a computed result and never labelled ``optimal``
# unless a solver proved it (design section 5).
# ---------------------------------------------------------------------------------------------------------------
TSP_REFERENCE_KIND = "tsp_reference"
TSP_REFERENCE_SCHEMA_VERSION = 1
TSP_REFERENCE_MANIFEST_FILENAME = "manifest.json"
TSP_REFERENCE_TOTAL_SECONDS = 600  # wall time in total per instance, all cut-loop re-solves together (EQ6, E09)
TSP_REFERENCE_SOLUTION_KIND = "hamiltonian_cycle"
TSP_REFERENCE_CLAIM = ("Verification subset (a correctness check of the exact TSP/ATSP pipeline and of the TSPLIB distance "
                       "convention), not a paper instance set; published TSPLIB optima are reference values; no superiority "
                       "claim.")
TSP_REFERENCE_DATA_SOURCES = ("tsp_file", "atsp_file", "tsplib_db_coordinates")
TSP_REFERENCE_PUBLISHED_SOURCES = ("tsplib",)
TSP_REFERENCE_REQUIRED_KEYS = (
    "protocol", "manifest_kind", "schema_version", "work_package", "solution_kind", "git_commit", "dirty_working_tree", "ampl",
    "solvers", "limits", "instances", "published_optimum_source", "python_provenance", "python_version", "host_os", "claim",
    "blocking_errors", "total_wall_seconds")
_TSP_INSTANCE_FIELDS = ("problem_type", "n", "edge_weight_type", "data_source", "sha256", "matrix_sha256", "published_optimum",
                        "published_source")


def validate_tsp_reference_manifest(manifest: Mapping) -> List[str]:
    """Schema errors of a TSP reference ``manifest.json`` (empty when valid); never mutates ``manifest``."""
    problems = [f"missing {k}" for k in TSP_REFERENCE_REQUIRED_KEYS if k not in manifest]
    if manifest.get("protocol", PROTOCOL_ID) != PROTOCOL_ID:
        problems.append(f"protocol must be {PROTOCOL_ID!r}")
    if manifest.get("manifest_kind", TSP_REFERENCE_KIND) != TSP_REFERENCE_KIND:
        problems.append(f"manifest_kind must be {TSP_REFERENCE_KIND!r}")
    if manifest.get("schema_version", TSP_REFERENCE_SCHEMA_VERSION) != TSP_REFERENCE_SCHEMA_VERSION:
        problems.append(f"schema_version must be {TSP_REFERENCE_SCHEMA_VERSION}")
    if manifest.get("solution_kind", TSP_REFERENCE_SOLUTION_KIND) != TSP_REFERENCE_SOLUTION_KIND:
        problems.append(f"solution_kind must be {TSP_REFERENCE_SOLUTION_KIND!r}")
    if "claim" in manifest and manifest["claim"] != TSP_REFERENCE_CLAIM:
        problems.append("claim text differs from the protocol wording")
    if "git_commit" in manifest and not re.fullmatch(r"[0-9a-f]{7,40}", str(manifest["git_commit"])):
        problems.append("git_commit must be a hex commit id")
    if "dirty_working_tree" in manifest and not isinstance(manifest["dirty_working_tree"], bool):
        problems.append("dirty_working_tree must be bool")
    if "blocking_errors" in manifest and not isinstance(manifest["blocking_errors"], list):
        problems.append("blocking_errors must be a list")
    ampl = manifest.get("ampl")
    if "ampl" in manifest:
        if not isinstance(ampl, Mapping):
            problems.append("ampl must be a mapping")
        else:
            for f in ("version", "amplpy_version", "location"):
                if not ampl.get(f):
                    problems.append(f"ampl.{f} missing")
            if ampl.get("location") not in AMPL_LOCATION_VALUES:
                problems.append(f"ampl.location must be one of {AMPL_LOCATION_VALUES}")
    limits = manifest.get("limits")
    if "limits" in manifest:
        if not isinstance(limits, Mapping):
            problems.append("limits must be a mapping")
        else:
            if limits.get("threads") != THREADS:
                problems.append(f"limits.threads must be {THREADS} (E09)")
            if limits.get("total_seconds_per_instance") != TSP_REFERENCE_TOTAL_SECONDS:
                problems.append(f"limits.total_seconds_per_instance must be {TSP_REFERENCE_TOTAL_SECONDS} "
                                "(E09: 600 s in total per instance)")
    solvers = manifest.get("solvers")
    if "solvers" in manifest:
        if not isinstance(solvers, Mapping):
            problems.append("solvers must be a mapping")
        else:
            for name in ("gurobi", "highs"):
                if not isinstance(solvers.get(name), Mapping):
                    problems.append(f"solvers.{name} missing")
                    continue
                problems.extend(_tsp_solver_errors(name, solvers[name]))
    instances = manifest.get("instances")
    if "instances" in manifest:
        if not isinstance(instances, Mapping) or not instances:
            problems.append("instances must be a non-empty mapping")
        else:
            for name, inst in instances.items():
                problems.extend(_tsp_instance_errors(name, inst))
    problems.extend(private_data_errors(manifest))
    return problems


def _tsp_solver_errors(name: str, solver: Mapping) -> List[str]:
    errors = []
    for f in ("name", "version", "option_string", "threads", "seed", "time_limit_seconds", "work_limit"):
        if f not in solver:
            errors.append(f"solvers.{name}.{f} missing")
    if errors:
        return errors
    if solver["threads"] != THREADS:
        errors.append(f"solvers.{name}.threads must be {THREADS}")
    if solver["time_limit_seconds"] != TSP_REFERENCE_TOTAL_SECONDS:
        errors.append(f"solvers.{name}.time_limit_seconds must be {TSP_REFERENCE_TOTAL_SECONDS}")
    if solver["work_limit"] is not None:
        errors.append(f"solvers.{name}.work_limit must be null (no work limit in the GOAL 2 verification run)")
    text = str(solver["option_string"])
    tokens = text.split()
    if _BARE_BESTBOUND.search(text):
        errors.append(f"solvers.{name}.option_string uses the bare bestbound=1 (use mip:bestbound=1, F17)")
    if "mip:bestbound=1" not in tokens:
        errors.append(f"solvers.{name}.option_string must request mip:bestbound=1")
    if f"lim:time={_g(solver['time_limit_seconds'])}" not in tokens:
        errors.append(f"solvers.{name}.option_string lim:time disagrees with time_limit_seconds")
    if f"tech:threads={solver['threads']}" not in tokens:
        errors.append(f"solvers.{name}.option_string tech:threads disagrees with threads")
    if any(t.startswith("lim:work=") for t in tokens):
        errors.append(f"solvers.{name}.option_string must not carry a work limit")
    return errors


def _tsp_instance_errors(name: str, inst) -> List[str]:
    if not isinstance(inst, Mapping):
        return [f"instances[{name}] must be a mapping"]
    errors = [f"instances[{name}] missing {f}" for f in _TSP_INSTANCE_FIELDS if f not in inst]
    if errors:
        return errors
    if inst["data_source"] not in TSP_REFERENCE_DATA_SOURCES:
        errors.append(f"instances[{name}].data_source must be one of {TSP_REFERENCE_DATA_SOURCES}")
    for f in ("sha256", "matrix_sha256"):
        if not _SHA256.fullmatch(str(inst[f])):
            errors.append(f"instances[{name}].{f} must be a sha256")
    if inst["published_source"] not in TSP_REFERENCE_PUBLISHED_SOURCES:
        errors.append(f"instances[{name}].published_source must be one of {TSP_REFERENCE_PUBLISHED_SOURCES} "
                      "(best_solutions is our own run history)")
    if not isinstance(inst["published_optimum"], int) or isinstance(inst["published_optimum"], bool):
        errors.append(f"instances[{name}].published_optimum must be an integer")
    return errors


# ---------------------------------------------------------------------------------------------------------------
# WP-E11 J7 (DECISION_LOG E13, E14; docs/designs/JOINT_DAY_MODEL_DESIGN.md sections 4.3 and 6.1): the joint day model.
# One exact day model over all enumerated routes of a service date. It is its own protocol id: it is neither
# exact_reference_v1 wave rows, nor union_day_v1 (menu-conditioned) rows, nor a heuristic row, and is never pooled,
# ranked, averaged or tested with any of them. ``validate_manifest``, ``validate_union_day_manifest`` and
# ``validate_tsp_reference_manifest`` are unchanged.
# ---------------------------------------------------------------------------------------------------------------
DAY_JOINT_PROTOCOL_ID = "exact_day_joint_v1"
DAY_JOINT_MANIFEST_FILENAME = "day_joint_manifest.json"
DAY_JOINT_MANIFEST_SCHEMA_VERSION = 1
DAY_JOINT_TIME_LIMIT_SECONDS = PEAK_WALL_LIMIT_SECONDS  # E14 Q3: 600 s per solver call, threads 1
DAY_JOINT_CLAIM = ("Exact joint day model over all enumerated routes of a service date (solver-proven value or bound); a "
                   "separate protocol, never pooled with exact_reference_v1 wave rows, union_day_v1 menu rows or heuristic "
                   "rows; prototype results are reproduction targets, never tuning targets.")

# Cell labels (``day_status``), design section 4.3. Paper wording (E13): "no day plan exists with at most L large vehicles"
# is allowed for ``infeasible_certified`` only; ``infeasible_solver_proven`` reads "infeasible, solver-proven".
DAY_JOINT_DAY_STATUSES = {
    "optimal": "Every stage optimal on the primary solver; plan certified and checked.",
    "optimal_stage1_by_bound": "Stage-1 incumbent equals LB0, LB0w or LB_S although the solver stopped on a limit.",
    "feasible_with_gap": "Certified incumbent and a bound below it; the bound source is named.",
    "bound_only": "A bound, no incumbent.",
    "infeasible_certified": "A section 3.2 certificate (tier named), independent of the day MIP.",
    "infeasible_solver_proven": "The solver proves infeasibility without a certificate; the cross-check field names agreement.",
    "not_run_enumeration_cap": "Some wave of the date did not enumerate completely.",
    "rejected": "Certificate, checker or objective cross-check failed (an error to investigate).",
    "input_rejected": "The archive is inconsistent (as exact design section 4).",
    "backend_unavailable": "A solver or its license is missing (as exact design section 4).",
}
# Stage rows carry ``status``, ``stop_reason``, ``timing_dependent`` and ``non_lexicographic`` with the meanings of exact
# design section 4: the same vocabulary, not a new one.
DAY_JOINT_STOP_REASONS = dict(STOP_REASONS)
DAY_JOINT_TIMING_STOP_REASONS = TIMING_STOP_REASONS

DAY_JOINT_REQUIRED_KEYS = (
    "protocol", "schema_version", "work_package", "git_commit", "dirty_working_tree", "python_provenance", "python_version",
    "host_os", "source_manifests", "solvers", "enumeration", "mps_sha256", "output_sha256", "run_history", "claim",
    "blocking_errors", "total_wall_seconds")
_DAY_JOINT_SOLVER_FIELDS = ("name", "version", "options", "threads", "seed", "time_limit_seconds", "work_limit")


def validate_day_joint_manifest(manifest: Mapping) -> List[str]:
    """Schema errors of a ``day_joint_manifest.json`` (empty when valid); never mutates ``manifest``.

    Like the other manifests it never holds absolute paths, e-mail addresses or license text, and it must carry the
    ``run_history`` of the run (E06)."""
    problems = [f"missing {k}" for k in DAY_JOINT_REQUIRED_KEYS if k not in manifest]
    if manifest.get("protocol", DAY_JOINT_PROTOCOL_ID) != DAY_JOINT_PROTOCOL_ID:
        problems.append(f"protocol must be {DAY_JOINT_PROTOCOL_ID!r}")
    if manifest.get("schema_version", DAY_JOINT_MANIFEST_SCHEMA_VERSION) != DAY_JOINT_MANIFEST_SCHEMA_VERSION:
        problems.append(f"schema_version must be {DAY_JOINT_MANIFEST_SCHEMA_VERSION}")
    if "claim" in manifest and manifest["claim"] != DAY_JOINT_CLAIM:
        problems.append("claim text differs from the protocol wording")
    if "git_commit" in manifest and not re.fullmatch(r"[0-9a-f]{7,40}", str(manifest["git_commit"])):
        problems.append("git_commit must be a hex commit id")
    if "dirty_working_tree" in manifest and not isinstance(manifest["dirty_working_tree"], bool):
        problems.append("dirty_working_tree must be bool")
    if "blocking_errors" in manifest and not isinstance(manifest["blocking_errors"], list):
        problems.append("blocking_errors must be a list")
    history = manifest.get("run_history")
    if "run_history" in manifest and (not isinstance(history, Mapping) or not history):
        problems.append("run_history must be a non-empty mapping (E06)")
    sources = manifest.get("source_manifests")
    if "source_manifests" in manifest:
        if not isinstance(sources, Mapping) or not sources:
            problems.append("source_manifests must be a non-empty mapping")
        else:
            for name, src in sources.items():
                if not isinstance(src, Mapping) or not isinstance(src.get("path"), str) \
                        or not _SHA256.fullmatch(str(src.get("manifest_sha256"))):
                    problems.append(f"source_manifests[{name}] needs a relative path and a manifest_sha256")
    solvers = manifest.get("solvers")
    if "solvers" in manifest:
        if not isinstance(solvers, Mapping):
            problems.append("solvers must be a mapping")
        else:
            if not isinstance(solvers.get("highs"), Mapping):
                problems.append("solvers.highs missing (primary solver, E14 Q4)")
            for name, solver in solvers.items():
                problems.extend(_day_joint_solver_errors(name, solver, sensitivity=_is_sensitivity_run(manifest)))
    enumeration = manifest.get("enumeration")
    if "enumeration" in manifest:
        if not isinstance(enumeration, Mapping):
            problems.append("enumeration must be a mapping")
        else:
            for f in ("column_cap", "label_cap"):
                if enumeration.get(f) != ENUMERATION_CAPS[f]:
                    problems.append(f"enumeration.{f} must be {ENUMERATION_CAPS[f]}")
            if not isinstance(enumeration.get("columns_per_day"), Mapping):
                problems.append("enumeration.columns_per_day must be a mapping")
    for key in ("mps_sha256", "output_sha256"):
        table = manifest.get(key)
        if key in manifest:
            if not isinstance(table, Mapping):
                problems.append(f"{key} must be a mapping")
            else:
                problems.extend(f"{key}[{k}] must be a sha256" for k, sha in table.items() if not _SHA256.fullmatch(str(sha)))
    problems.extend(private_data_errors(manifest))
    return problems


def _is_sensitivity_run(manifest: Mapping) -> bool:
    """A labelled sensitivity run: ``sensitivity_run`` is exactly ``True`` and ``run_label`` a non-empty string."""
    label = manifest.get("run_label")
    return manifest.get("sensitivity_run") is True and isinstance(label, str) and bool(label.strip())


def _day_joint_solver_errors(name: str, solver, sensitivity: bool = False) -> List[str]:
    if not isinstance(solver, Mapping):
        return [f"solvers.{name} must be a mapping"]
    errors = [f"solvers.{name}.{f} missing" for f in _DAY_JOINT_SOLVER_FIELDS if f not in solver]
    if errors:
        return errors
    if solver["threads"] != THREADS:
        errors.append(f"solvers.{name}.threads must be {THREADS} (E14 Q3)")
    limit = solver["time_limit_seconds"]
    if sensitivity:  # a labelled sensitivity run (never pooled with the 600 s protocol run) may use another positive limit
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not limit > 0:
            errors.append(f"solvers.{name}.time_limit_seconds must be a positive number")
    elif limit != DAY_JOINT_TIME_LIMIT_SECONDS:
        errors.append(f"solvers.{name}.time_limit_seconds must be {DAY_JOINT_TIME_LIMIT_SECONDS} unless sensitivity_run is true "
                      "with a non-empty run_label (E14 Q3)")
    work = solver["work_limit"]
    if work is not None and (not isinstance(work, (int, float)) or isinstance(work, bool) or work <= 0):
        errors.append(f"solvers.{name}.work_limit must be null or a positive number")
    return errors
