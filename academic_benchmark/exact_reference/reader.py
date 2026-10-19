"""Reader of the committed ``exact_reference_v1`` results (WP-E8 Task 4/5; DECISION_LOG A04, E09, E12).

``load_exact_reference(results_dir, repo_root=...)`` turns one committed results directory into typed
:class:`~academic_benchmark.exact_reference.rows.ExactReferenceRowV1` rows, or refuses. ``discover_exact_references``
reads exactly the directories listed in ``results_index.json`` (no glob discovery). Dispatch is on the triple
(``protocol``, manifest kind, ``schema_version``); an unknown triple is refused with a message, never guessed.

* ``tsp_reference`` (WP-E7 ``manifest.json``): ``reference.csv`` (31 columns, frozen as ``TSP_REFERENCE_CSV_FIELDS_V1``),
  ``tours.json`` and ``README.md`` are verified against ``outputs`` (sha256 over raw bytes), the CSV is cross-checked against
  the manifest, the tours and itself; per instance one ``primary`` (Gurobi) and one ``verification`` (HiGHS) row.
  ``gap_to_reference``, ``verdict`` and ``reference_in_bracket`` are recomputed and checked, then dropped (owner decision OQ2:
  the row model carries no gap field). MTZ agreement is checked, not emitted.
* ``wave_campaign`` (WP-E3/WP-E4a ``exact_manifest.json``): checked by schema (``protocol.validate_manifest`` and
  ``validate_stage_row`` on every Gurobi and HiGHS stage row) and by fingerprints (``exact_routes`` sha256 and the sha256 of
  each source campaign manifest) only; their rows keep ``ub_validated = false`` with the basis
  ``certified_by_producing_run`` (owner decision OQ3).
* ``union_day_v1`` (WP-E4b) and the gap report (WP-E6) are other protocols and are refused.

Refused paths: absolute, ``..``, anything with a component named ``archive`` (any letter case), anything outside
``repo_root``. Standard library plus pydantic; nothing is written, no database is opened, no ``scripts.*`` module is imported.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path, PurePosixPath
from typing import Optional

from academic_benchmark.contracts.common import JsonValue, RepositoryRelativePath, Sha256Digest, StrictContract
from academic_benchmark.exact_reference import protocol
from academic_benchmark.exact_reference.rows import ExactReferenceRowV1

TSP_REFERENCE_CSV_FIELDS_V1 = (
    "protocol", "instance", "problem_type", "n", "edge_weight_type", "reference_optimum", "reference_source", "exact_status",
    "stop_reason", "ub", "lb", "gap_to_reference", "reference_in_bracket", "verdict", "ub_source", "cut_rounds", "cuts",
    "solver", "solver_version", "wall_seconds", "timing_dependent", "highs_status", "highs_value", "highs_lb",
    "highs_wall_seconds", "highs_timing_dependent", "highs_agreement", "mtz_status", "mtz_value", "mtz_wall_seconds",
    "mtz_agreement")
TSP_OUTPUT_FILES = ("README.md", "reference.csv", "tours.json")
WAVE_MANIFEST_NAME = protocol.MANIFEST_FILENAME  # exact_manifest.json
TSP_MANIFEST_NAME = protocol.TSP_REFERENCE_MANIFEST_FILENAME  # manifest.json
UNION_MANIFEST_NAME = protocol.UNION_DAY_MANIFEST_FILENAME
INDEX_RELATIVE_PATH = "academic_benchmark/exact_reference/results_index.json"
INDEX_SCHEMA = "uniride-exact-results-index/v1"
KIND_TSP, KIND_WAVE = "tsp_reference", "wave_campaign"
_ACCEPTED_AGREEMENT = ("agree", "secondary_time_limited")
_REFUSED_COMPONENT = "arch" + "ive"  # components with this name are never read
_SHA = re.compile(r"[0-9a-f]{64}")


class ExactReferenceRefused(ValueError):
    """A results directory is not a valid, verifiable ``exact_reference_v1`` result (the message says why)."""


class ExactReferenceSet(StrictContract):
    """The rows of one committed results directory with the manifest they came from."""

    results_dir: RepositoryRelativePath
    manifest_kind: str
    manifest_sha256: Sha256Digest
    manifest: dict[str, JsonValue]
    rows: list[ExactReferenceRowV1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _crlf_form(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


# ---------------------------------------------------------------- locating and dispatching
def _refuse_path(results_dir) -> PurePosixPath:
    text = str(results_dir).replace("\\", "/")
    if not text.strip() or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ExactReferenceRefused(f"results_dir {text!r} must be a repository-relative path (absolute paths are refused)")
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise ExactReferenceRefused(f"results_dir {text!r} contains '..' (path escape refused)")
    if any(p.lower() == _REFUSED_COMPONENT for p in parts):
        raise ExactReferenceRefused(f"results_dir {text!r} lies in the {_REFUSED_COMPONENT} directory; archived files are never read")
    if not parts:
        raise ExactReferenceRefused("results_dir is empty")
    return PurePosixPath(*parts)


def _locate(results_dir, repo_root) -> tuple:
    rel = _refuse_path(results_dir)
    root = Path(repo_root).resolve()
    target = (root / Path(*rel.parts)).resolve()
    if target != root and root not in target.parents:
        raise ExactReferenceRefused(f"results_dir {rel} resolves outside the repository")
    inside = target.relative_to(root).parts
    if any(p.lower() == _REFUSED_COMPONENT for p in inside):
        raise ExactReferenceRefused(f"results_dir {rel} resolves into the {_REFUSED_COMPONENT} directory")
    if not target.is_dir():
        raise ExactReferenceRefused(f"results_dir {rel} is not a directory")
    return rel, target


def _read_json(path: Path):
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise ExactReferenceRefused(f"{path.name}: cannot read as JSON ({exc})") from exc


def _find_manifest(directory: Path) -> tuple:
    """(path, doc) of the directory's manifest; refuses a union-day or unknown manifest kind."""
    if (directory / UNION_MANIFEST_NAME).is_file():
        raise ExactReferenceRefused(f"{UNION_MANIFEST_NAME}: union_day_v1 is its own protocol and is not an exact_reference_v1 row source")
    wave, tsp = directory / WAVE_MANIFEST_NAME, directory / TSP_MANIFEST_NAME
    if wave.is_file() and tsp.is_file():
        raise ExactReferenceRefused("the directory holds both exact_manifest.json and manifest.json; refused as ambiguous")
    path = wave if wave.is_file() else tsp
    if not path.is_file():
        raise ExactReferenceRefused(f"no exact_manifest.json or manifest.json in {directory.name}")
    doc = _read_json(path)
    if not isinstance(doc, dict):
        raise ExactReferenceRefused(f"{path.name}: the manifest is not a JSON object")
    return path, doc


def _kind_of(path: Path, doc: dict) -> tuple:
    protocol_id = doc.get("protocol")
    kind = doc.get("manifest_kind") or (KIND_WAVE if path.name == WAVE_MANIFEST_NAME else None)
    triple = (protocol_id, kind, doc.get("schema_version"))
    if protocol_id == protocol.UNION_DAY_PROTOCOL_ID:
        raise ExactReferenceRefused(f"{path.name}: protocol union_day_v1 is not exact_reference_v1")
    known = {(protocol.PROTOCOL_ID, KIND_TSP, protocol.TSP_REFERENCE_SCHEMA_VERSION),
             (protocol.PROTOCOL_ID, KIND_WAVE, protocol.MANIFEST_SCHEMA_VERSION)}
    if triple not in known:
        raise ExactReferenceRefused(f"{path.name}: unknown (protocol, manifest_kind, schema_version) {triple!r}; "
                                    f"known: {sorted(known)}")
    return triple[1]


# ---------------------------------------------------------------- shared checks
def _manifest_checks(doc: dict, errors: list, what: str) -> None:
    if errors:
        raise ExactReferenceRefused(f"{what}: manifest schema errors: {errors[:5]}")
    if doc.get("blocking_errors"):
        raise ExactReferenceRefused(f"{what}: the manifest records blocking errors; it is not a verified reference")
    private = protocol.private_data_errors(doc)
    if private:
        raise ExactReferenceRefused(f"{what}: private data in the manifest: {private[:3]}")


def _int_or_none(text: str, what: str) -> Optional[int]:
    if text == "":
        return None
    try:
        return int(text)
    except ValueError as exc:
        raise ExactReferenceRefused(f"{what}: {text!r} is not an integer") from exc


def _float_or_none(text: str, what: str) -> Optional[float]:
    if text == "":
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ExactReferenceRefused(f"{what}: {text!r} is not a number") from exc


def _bool(text: str, what: str) -> bool:
    if text not in ("true", "false"):
        raise ExactReferenceRefused(f"{what}: {text!r} is not true/false")
    return text == "true"


def _bool_or_none(text: str, what: str) -> Optional[bool]:
    return None if text == "" else _bool(text, what)


# ---------------------------------------------------------------- tsp_reference (WP-E7)
def _verdict(status: str, lb, ub, reference: int) -> str:
    """The WP-E7 verdict rule, recomputed here (not imported from the runner script)."""
    if status == "optimal":
        return "reproduced" if ub == reference else "defect"
    if status == "feasible_with_gap":
        return "bracketed" if lb is not None and ub is not None and lb <= reference <= ub else "defect"
    if status == "bound_only":
        return "not_bracketed"
    return "defect"


def _check_run_history(manifest: dict) -> None:
    history = manifest.get("run_history")
    if not isinstance(history, dict):
        raise ExactReferenceRefused("manifest.run_history missing")
    old = "invocations_at_this_commit" in history
    new = {"invocations_in_this_manifest", "started_utc", "ended_utc"} <= set(history)
    if not (old or new):
        raise ExactReferenceRefused("manifest.run_history has neither the original nor the polished WP-E7 shape")
    for key in ("cache", "retries", "serial"):
        if key not in history:
            raise ExactReferenceRefused(f"manifest.run_history.{key} missing")


def _verify_outputs(directory: Path, manifest: dict) -> dict:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != set(TSP_OUTPUT_FILES):
        raise ExactReferenceRefused(f"manifest.outputs must list exactly {list(TSP_OUTPUT_FILES)}")
    data = {}
    for name in TSP_OUTPUT_FILES:
        path = directory / name
        if not path.is_file():
            raise ExactReferenceRefused(f"{name} is missing")
        raw = path.read_bytes()
        if sha256_bytes(raw) != outputs[name]:
            raise ExactReferenceRefused(f"{name}: sha256 {sha256_bytes(raw)} differs from the manifest outputs entry {outputs[name]}")
        data[name] = raw
    return data


def _csv_records(raw: bytes) -> list:
    text = raw.decode("utf-8")
    table = list(csv.reader(io.StringIO(text, newline="")))
    if not table or tuple(table[0]) != TSP_REFERENCE_CSV_FIELDS_V1:
        raise ExactReferenceRefused("reference.csv: the header differs from TSP_REFERENCE_CSV_FIELDS_V1 (column set or order)")
    records = []
    for number, cells in enumerate(table[1:], start=2):
        if len(cells) != len(TSP_REFERENCE_CSV_FIELDS_V1):
            raise ExactReferenceRefused(f"reference.csv line {number}: {len(cells)} cells, expected {len(TSP_REFERENCE_CSV_FIELDS_V1)}")
        records.append(dict(zip(TSP_REFERENCE_CSV_FIELDS_V1, cells)))
    if not records:
        raise ExactReferenceRefused("reference.csv has no rows")
    return records


def _check_tours(doc, records: list) -> dict:
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 or doc.get("node_base") != 1 \
            or doc.get("solution_kind") != protocol.TSP_REFERENCE_SOLUTION_KIND or not isinstance(doc.get("tours"), dict):
        raise ExactReferenceRefused("tours.json: schema_version 1, node_base 1, solution_kind hamiltonian_cycle and tours are required")
    tours = doc["tours"]
    extra = sorted(set(tours) - {r["instance"] for r in records})
    if extra:
        raise ExactReferenceRefused(f"tours.json lists instances absent from reference.csv: {extra}")
    return tours


def _tsp_rows(directory: Path, rel: PurePosixPath, manifest: dict, manifest_sha: str) -> list:
    _check_run_history(manifest)
    data = _verify_outputs(directory, manifest)
    records = _csv_records(data["reference.csv"])
    tours = _check_tours(json.loads(data["tours.json"].decode("utf-8")), records)
    instances, solvers = manifest["instances"], manifest["solvers"]
    names = [r["instance"] for r in records]
    if len(set(names)) != len(names):
        raise ExactReferenceRefused("reference.csv lists an instance twice")
    if set(names) != set(instances):
        raise ExactReferenceRefused("reference.csv and manifest.instances list different instances")
    source = {"results_dir": str(rel), "manifest_kind": KIND_TSP, "manifest_sha256": manifest_sha,
              "work_package": manifest["work_package"], "git_commit": manifest["git_commit"]}
    rows = []
    for rec in records:
        name = rec["instance"]
        where = f"reference.csv {name}"
        if rec["protocol"] != protocol.PROTOCOL_ID:
            raise ExactReferenceRefused(f"{where}: protocol {rec['protocol']!r} is not {protocol.PROTOCOL_ID!r}")
        inst = instances[name]
        n = _int_or_none(rec["n"], f"{where} n")
        reference = _int_or_none(rec["reference_optimum"], f"{where} reference_optimum")
        for field, want in (("problem_type", inst["problem_type"]), ("edge_weight_type", inst["edge_weight_type"])):
            if rec[field] != want:
                raise ExactReferenceRefused(f"{where}: {field} {rec[field]!r} differs from the manifest {want!r}")
        if n != inst["n"] or reference != inst["published_optimum"] or rec["reference_source"] != inst["published_source"]:
            raise ExactReferenceRefused(f"{where}: n, reference_optimum or reference_source differ from the manifest")
        if reference is None or rec["reference_source"] not in protocol.TSP_REFERENCE_PUBLISHED_SOURCES:
            raise ExactReferenceRefused(f"{where}: the published reference must be an integer with source tsplib")
        status = rec["exact_status"]
        ub, lb = _int_or_none(rec["ub"], f"{where} ub"), _int_or_none(rec["lb"], f"{where} lb")
        # consistency of the derived columns (then dropped: no gap field exists on a row)
        if rec["gap_to_reference"] != ("" if ub is None else str(ub - reference)):
            raise ExactReferenceRefused(f"{where}: gap_to_reference {rec['gap_to_reference']!r} is not ub - reference_optimum")
        in_bracket = lb is not None and ub is not None and lb <= reference <= ub
        if _bool(rec["reference_in_bracket"], f"{where} reference_in_bracket") != in_bracket:
            raise ExactReferenceRefused(f"{where}: reference_in_bracket disagrees with lb <= reference_optimum <= ub")
        if rec["verdict"] != _verdict(status, lb, ub, reference):
            raise ExactReferenceRefused(f"{where}: verdict {rec['verdict']!r} disagrees with status and bounds")
        if rec["solver"] != solvers["gurobi"]["name"] or rec["solver_version"] != solvers["gurobi"]["version"]:
            raise ExactReferenceRefused(f"{where}: solver or solver_version differs from manifest.solvers.gurobi")
        # tours
        if ub is not None:
            tour = tours.get(name)
            if tour is None:
                raise ExactReferenceRefused(f"{where}: no tour in tours.json for an instance with an incumbent")
            if tour.get("length") != ub or tour.get("n") != n or tour.get("status") != status or tour.get("solver") != rec["solver"]:
                raise ExactReferenceRefused(f"{where}: tours.json length/n/status/solver differ from reference.csv (length {tour.get('length')} vs ub {ub})")
        elif name in tours:
            raise ExactReferenceRefused(f"{where}: tours.json holds a tour for an instance without an incumbent")
        # second solvers: contradictions are refused, the result is not emitted (MTZ) or emitted as a verification row (HiGHS)
        if rec["highs_status"] and rec["highs_agreement"] not in _ACCEPTED_AGREEMENT:
            raise ExactReferenceRefused(f"{where}: HiGHS agreement {rec['highs_agreement']!r} is a contradiction")
        if rec["highs_status"] == "optimal" and status == "optimal" and _int_or_none(rec["highs_value"], where) != ub:
            raise ExactReferenceRefused(f"{where}: HiGHS proved {rec['highs_value']} but the primary proved {ub}")
        if rec["mtz_status"] and rec["mtz_agreement"] not in _ACCEPTED_AGREEMENT:
            raise ExactReferenceRefused(f"{where}: MTZ agreement {rec['mtz_agreement']!r} is a contradiction")
        if rec["mtz_status"] == "optimal" and status == "optimal" and _int_or_none(rec["mtz_value"], where) != ub:
            raise ExactReferenceRefused(f"{where}: MTZ proved {rec['mtz_value']} but the primary proved {ub}")
        common = dict(
            row_schema_version="uniride-exact-reference-row/v1", protocol=protocol.PROTOCOL_ID,
            solution_kind="hamiltonian_cycle", problem_contract=rec["problem_type"], instance_id=name, stage=None,
            reference_optimum=reference, reference_optimum_source="tsplib", ub_validated=False,
            ub_validation_basis="not_validated", source=source)
        rows.append(ExactReferenceRowV1(
            **common, solver_role="primary", solver_name=solvers["gurobi"]["name"], solver_version=solvers["gurobi"]["version"],
            option_string=solvers["gurobi"]["option_string"], status=status,
            stop_reason=rec["stop_reason"] or None, lb=lb, ub=ub,
            timing_dependent=_bool(rec["timing_dependent"], f"{where} timing_dependent"),
            wall_seconds=_float_or_none(rec["wall_seconds"], f"{where} wall_seconds")))
        if rec["highs_status"]:
            highs_status = rec["highs_status"]
            rows.append(ExactReferenceRowV1(
                **common, solver_role="verification", solver_name=solvers["highs"]["name"],
                solver_version=solvers["highs"]["version"], option_string=solvers["highs"]["option_string"],
                status=highs_status, stop_reason="optimal" if highs_status == "optimal" else None,  # a proven optimum stops as optimal (protocol rule)
                lb=_int_or_none(rec["highs_lb"], f"{where} highs_lb"), ub=_int_or_none(rec["highs_value"], f"{where} highs_value"),
                timing_dependent=bool(_bool_or_none(rec["highs_timing_dependent"], f"{where} highs_timing_dependent")),
                wall_seconds=_float_or_none(rec["highs_wall_seconds"], f"{where} highs_wall_seconds")))
    return rows


# ---------------------------------------------------------------- wave_campaign (WP-E3, WP-E4a)
def _crlf_tolerant_match(raw: bytes, expected: str) -> bool:
    """A source campaign manifest was hashed where it was written (Windows, CRLF) while git stores LF: accept either form."""
    return sha256_bytes(raw) == expected or sha256_bytes(_crlf_form(raw)) == expected


def _check_wave_fingerprints(directory: Path, manifest: dict, repo_root: Path) -> None:
    routes = manifest.get("exact_routes")
    if not isinstance(routes, dict) or not _SHA.fullmatch(str(routes.get("sha256"))) or not routes.get("file"):
        raise ExactReferenceRefused("manifest.exact_routes needs a file and a sha256")
    path = directory / PurePosixPath(routes["file"]).name
    if not path.is_file() or sha256_bytes(path.read_bytes()) != routes["sha256"]:
        raise ExactReferenceRefused(f"{routes['file']}: missing or its sha256 differs from manifest.exact_routes")
    campaigns = {}
    if isinstance(manifest.get("source_campaign"), dict):
        campaigns["source_campaign"] = manifest["source_campaign"]
    if isinstance(manifest.get("source_campaigns"), dict):
        campaigns.update({f"source_campaigns[{k}]": v for k, v in manifest["source_campaigns"].items()})
    for label, campaign in campaigns.items():
        rel = _refuse_path(campaign["path"])
        source_manifest = repo_root.resolve() / Path(*rel.parts) / "run_manifest.json"
        if not source_manifest.is_file():
            raise ExactReferenceRefused(f"{label}: {rel}/run_manifest.json is missing, its fingerprint cannot be checked")
        if not _crlf_tolerant_match(source_manifest.read_bytes(), campaign["manifest_sha256"]):
            raise ExactReferenceRefused(f"{label}: the sha256 of {rel}/run_manifest.json differs from the recorded fingerprint")


def _instance_id(wave: dict) -> str:
    base = f"{wave['service_date']}_R{wave['R']}/{wave['wave_id']}"
    if "option" in wave:  # WP-E4a: the same wave repeats per fleet and option
        return f"{base}/{wave['fleet']}/{wave['option']}"
    return base


def _stage_row(wave: dict, stage: dict, role: str, solver: dict, source: dict) -> ExactReferenceRowV1:
    objective, bound_ceil = stage["objective"], stage.get("bound_ceil")
    for label, value in (("objective", objective), ("bound_ceil", bound_ceil)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ExactReferenceRefused(f"{_instance_id(wave)} {stage['stage']}: {label} {value!r} is not an integer")
    option_string = solver["peak_option_string"] if wave["peak"] else solver["option_string"]
    return ExactReferenceRowV1(
        row_schema_version="uniride-exact-reference-row/v1", protocol=protocol.PROTOCOL_ID, solution_kind="vehicle_routes",
        problem_contract="uniride_wave", instance_id=_instance_id(wave), stage=stage["stage"], solver_role=role,
        solver_name=solver["name"], solver_version=solver["version"], option_string=option_string, status=stage["status"],
        stop_reason=stage["stop_reason"], lb=bound_ceil, ub=objective, reference_optimum=None, reference_optimum_source=None,
        timing_dependent=stage["timing_dependent"], wall_seconds=stage.get("wall_seconds"), ub_validated=False,
        ub_validation_basis="certified_by_producing_run", source=source)


def _wave_rows(directory: Path, rel: PurePosixPath, manifest: dict, manifest_sha: str, repo_root: Path) -> list:
    _check_wave_fingerprints(directory, manifest, repo_root)
    source = {"results_dir": str(rel), "manifest_kind": KIND_WAVE, "manifest_sha256": manifest_sha,
              "work_package": manifest["work_package"], "git_commit": manifest["git_commit"]}
    verification = manifest.get("verification_solver")
    rows, seen = [], set()
    for wave in manifest["waves"]:
        key = _instance_id(wave)
        if key in seen:
            raise ExactReferenceRefused(f"{key}: the same wave/option appears twice")
        seen.add(key)
        for stage in wave["stages"]:
            rows.append(_stage_row(wave, stage, "primary", manifest["solver"], source))
        highs = wave.get("highs_stages") or []
        if highs and not isinstance(verification, dict):
            raise ExactReferenceRefused("waves carry highs_stages but the manifest has no verification_solver")
        for stage in highs:
            problems = protocol.validate_stage_row(stage)
            if problems:
                raise ExactReferenceRefused(f"{key}: HiGHS stage row invalid: {problems[:3]}")
            rows.append(_stage_row(wave, stage, "verification", verification, source))
    return rows


# ---------------------------------------------------------------- public API
def _sort_key(row: ExactReferenceRowV1) -> tuple:
    return (row.instance_id, row.stage or "", row.solver_role)


def load_exact_reference(results_dir, *, repo_root) -> ExactReferenceSet:
    """Rows of one committed results directory (repository-relative ``results_dir``), sorted by instance, stage and role.
    Raises :class:`ExactReferenceRefused` for anything that does not verify."""
    rel, directory = _locate(results_dir, repo_root)
    path, manifest = _find_manifest(directory)
    kind = _kind_of(path, manifest)
    manifest_sha = sha256_bytes(path.read_bytes())
    if kind == KIND_TSP:
        _manifest_checks(manifest, protocol.validate_tsp_reference_manifest(manifest), str(rel))
        rows = _tsp_rows(directory, rel, manifest, manifest_sha)
    else:
        _manifest_checks(manifest, protocol.validate_manifest(manifest), str(rel))
        rows = _wave_rows(directory, rel, manifest, manifest_sha, Path(repo_root))
    return ExactReferenceSet(results_dir=str(rel), manifest_kind=kind, manifest_sha256=manifest_sha, manifest=manifest,
                             rows=sorted(rows, key=_sort_key))


def read_index(repo_root) -> list:
    """The entries of ``results_index.json`` (``results_dir``, ``manifest_file``, ``manifest_kind``, ``manifest_sha256``,
    ``rows``); an unknown schema is refused."""
    doc = _read_json(Path(repo_root) / INDEX_RELATIVE_PATH)
    if not isinstance(doc, dict) or doc.get("schema_version") != INDEX_SCHEMA or not isinstance(doc.get("entries"), list):
        raise ExactReferenceRefused(f"results_index.json: schema_version {doc.get('schema_version') if isinstance(doc, dict) else None!r}, expected {INDEX_SCHEMA!r}")
    dirs = [e.get("results_dir") for e in doc["entries"]]
    if len(set(dirs)) != len(dirs):
        raise ExactReferenceRefused("results_index.json lists a results directory twice")
    return doc["entries"]


def discover_exact_references(repo_root) -> tuple:
    """Load exactly the directories listed in ``results_index.json``; each manifest sha256 and row count must match the
    index entry (no glob discovery: an unlisted directory is not an exact reference)."""
    sets = []
    for entry in read_index(repo_root):
        loaded = load_exact_reference(entry["results_dir"], repo_root=repo_root)
        if loaded.manifest_sha256 != entry.get("manifest_sha256") or loaded.manifest_kind != entry.get("manifest_kind"):
            raise ExactReferenceRefused(f"{entry['results_dir']}: manifest sha256 or kind differs from results_index.json")
        if len(loaded.rows) != entry.get("rows"):
            raise ExactReferenceRefused(f"{entry['results_dir']}: {len(loaded.rows)} rows, results_index.json says {entry.get('rows')}")
        sets.append(loaded)
    return tuple(sets)
