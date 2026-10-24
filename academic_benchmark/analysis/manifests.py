"""Run manifests, campaign index, detached ``.sha256`` files and their verifier (Gate D, D-02).

Design "Reproducibility Manifest" (``ACADEMIC_STUDY_UNIFICATION_DESIGN.md``): every run records its git state, environment,
dataset, algorithm, seeds, budget, termination, validation and output checksums; a detached ``<manifest>.sha256`` holds the
manifest's own checksum, so the manifest never hashes itself; writes are atomic so an interrupted run cannot masquerade as
complete.

Granularity (plan D-02, lead recommendation): one ``RunManifestV1`` per run (algorithm x dataset x budget level x
replicate) plus one campaign index (``uniride-run-index/v1``) that lists every manifest with its checksum and carries what the
whole campaign shares (mode, git, environment, base seed, seed protocol version). Layout under the campaign directory::

    run_index.json, run_index.json.sha256
    manifests/<run_id>.json, manifests/<run_id>.json.sha256
    fixed_runs.jsonl, native_runs.jsonl, failed_runs.jsonl   (the result files; their checksums are in each manifest's
                                                             ``outputs`` and in the index)

Paths in ``outputs`` are relative to the campaign directory. A manifest never lists a manifest, a ``.sha256`` file or the
index among its outputs. The sidecar is a ``sha256sum`` line (``<hex>  <file name>``); write order is the manifest, then its
sidecar, and the index with its sidecar last, so a crash leaves a file without a matching sidecar, which does not verify.

Timing: ``termination.runtime_seconds`` and the stage ``elapsed_sec`` are results of the run and are persisted, but they never
enter an identity: the index's ``comparison_key_digest`` comes from the D-01 key (which reads no timing), and
``comparable_manifest_view`` is the replay-comparison view without timing and without the output checksums (the result files
carry ``elapsed_ms``). The module runs no solver and reads no database.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Optional, Sequence

from pydantic import BaseModel, ValidationError

from academic_benchmark.analysis.identity import SEED_PROTOCOL_VERSION, ComparisonIdentityError, comparison_cell_key
from academic_benchmark.contracts import DatasetManifestV1, OutputChecksumV1, RunManifestV1
from academic_benchmark.contracts.common import ChecksumV1
from academic_benchmark.contracts.run import EnvironmentV1, GitStateV1
from academic_benchmark.contracts.run_index import RunIndexEntryV1, RunIndexV1
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.protocol_registry import classify_row

INDEX_FILE = "run_index.json"
MANIFEST_DIR = "manifests"
SIDECAR_SUFFIX = ".sha256"
# result files whose every row needs a manifest (the failed-run file holds records, not observations)
RESULT_FILES = ("fixed_runs.jsonl", "native_runs.jsonl")
REPORT_FILES = ("smoke_report.txt", "smoke_report.json", "run_report.txt", "run_report.json")
# no statistics library exists before D-04a pins one (EnvironmentV1 requires a string); the literal is recorded as is
STATISTICS_LIBRARY_NONE = "none"
# native_uncapped runs have no budget level, but ``BudgetRecordV1.levels`` needs one entry: 0 is that sentinel
NATIVE_LEVELS = [0]

_BACKEND_POLICY = {
    "python_only": "python_only",
    "prefer_numba_objective": "prefer_numba",
    "require_numba_objective": "require_numba",
    "prefer_numba": "prefer_numba",
    "require_numba": "require_numba",
}
_BACKEND_KIND = {"python": "python", "numba": "numba", "numba_nopython": "numba", "none": "none"}
_SIDECAR_LINE = re.compile(r"^([0-9a-f]{64})  (.+)\n?$")
_ID_UNSAFE = re.compile(r"[^a-z0-9._-]")


class ManifestError(ValueError):
    """A run manifest, campaign index or checksum file cannot be written or does not hold."""


# ---------------------------------------------------------------------------------------------- bytes and checksums
def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: BaseModel | Mapping[str, Any]) -> bytes:
    """Sorted-key, two-space JSON with LF line ends and a final newline; the exact bytes that are checksummed."""
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_json_with_sidecar(path: Path, payload: BaseModel | Mapping[str, Any]) -> ChecksumV1:
    """Write ``payload`` atomically, then its detached ``<path>.sha256``; return the checksum of the written bytes."""
    path = Path(path)
    data = canonical_json_bytes(payload)
    digest = hashlib.sha256(data).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_bytes_atomic(path, data)
    _write_bytes_atomic(Path(str(path) + SIDECAR_SUFFIX), f"{digest}  {path.name}\n".encode("ascii", "replace"))
    return ChecksumV1(algorithm="sha256", value=digest)


# ---------------------------------------------------------------------------------------------------- environment
def _version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


def collect_environment(statistics_library: str = STATISTICS_LIBRARY_NONE) -> EnvironmentV1:
    """Interpreter, system and library versions from package metadata (no heavy import)."""
    return EnvironmentV1(
        python=platform.python_version(), operating_system=platform.platform(),
        cpu=platform.processor() or platform.machine() or "unknown",
        numpy=_version("numpy"), numba=_version("numba"), llvmlite=_version("llvmlite"),
        statistics_library=statistics_library,
    )


# ------------------------------------------------------------------------------------------------- manifest content
def make_run_id(study_id: str, dataset_id: str, algorithm_id: str, level_index: Optional[int], replicate: int) -> str:
    """Deterministic run id: study, dataset, protocol and level index, algorithm, replicate (lower case, ``[a-z0-9._-]``)."""
    protocol = "native" if level_index is None else f"fixed-l{level_index}"
    parts = [study_id, dataset_id, protocol, algorithm_id, f"r{replicate}"]
    return ".".join(_ID_UNSAFE.sub("-", part.lower()) for part in parts)


def _outputs_exclude_manifests(outputs: Iterable[OutputChecksumV1]) -> list[str]:
    bad = []
    for item in outputs:
        path = item.path
        if path.startswith(f"{MANIFEST_DIR}/") or path.endswith(SIDECAR_SUFFIX) or path == INDEX_FILE:
            bad.append(path)
    return bad


def _backend_profile(row: Mapping[str, Any]) -> dict[str, str]:
    text = row.get("execution_backend")
    if isinstance(text, str):
        parts = dict(item.split("=", 1) for item in text.split(";") if "=" in item)
    elif isinstance(row.get("backend_profile"), Mapping):
        parts = dict(row["backend_profile"])
    else:
        raise ManifestError("row has no execution_backend or backend_profile: the backend profile is part of the manifest")
    try:
        profile = {"objective": _BACKEND_KIND[parts["objective"]], "polish": _BACKEND_KIND[parts["polish"]]}
    except KeyError as exc:
        raise ManifestError(f"row backend profile {parts!r} is not understood (missing or unknown {exc})") from exc
    if profile["objective"] == "none":
        raise ManifestError("a run has an objective backend (python or numba)")
    return profile


def _stage_records(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    composition = row.get("composition")
    if not isinstance(composition, Mapping):
        return []
    stages = composition.get("stages")
    return [copy.deepcopy(dict(stage)) for stage in stages] if isinstance(stages, list) else []


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def build_run_manifest(
    row: Mapping[str, Any],
    *,
    study_id: str,
    dataset: DatasetManifestV1,
    base_seed: int,
    levels: Sequence[int],
    configuration: Mapping[str, Any],
    git: GitStateV1 | Mapping[str, Any],
    environment: EnvironmentV1 | Mapping[str, Any],
    outputs: Sequence[OutputChecksumV1],
) -> RunManifestV1:
    """The ``RunManifestV1`` of one successful heuristic row.

    ``levels`` is the dataset's own fixed-budget level list (``studies.service.fixed_budget_levels_for``), recorded whole, not
    the smoke slice; a native row records ``[0]`` (no level). ``configuration`` is the parameter block the run received, without
    the protocol echoes (``fair_comparison``/``native_comparison``). Refuses failed runs, exact/union/joint rows and an output
    list that names a manifest, a checksum file or the index."""
    if row.get("record_kind") == "failed_run" or row.get("validation_status") == "failed":
        raise ManifestError("a failed run has no run manifest: it is recorded in the failed-run file and excluded")
    try:
        kind = classify_row(row)
    except ValueError as exc:
        raise ManifestError(f"row protocol kind cannot be determined: {exc}") from exc
    if not kind.rankable:
        raise ManifestError(f"{kind.kind} rows are not heuristic runs and get no run manifest")
    native = kind.pooling_group == "native"
    algorithm_id, problem = row.get("algorithm_id"), row.get("problem")
    replicate, seed = row.get("replicate"), row.get("seed")
    if not isinstance(algorithm_id, str) or not isinstance(problem, str) or not _is_int(replicate) or not _is_int(seed):
        raise ManifestError("row needs algorithm_id, problem, an integer replicate and an integer seed")
    dataset_id = dataset.dataset_id
    if "dataset_id" in row and row["dataset_id"] != dataset_id:
        raise ManifestError(f"row dataset_id {row['dataset_id']!r} differs from the dataset manifest's {dataset_id!r}")
    expected = f"tsplib-{normalize_problem(problem)}"
    if dataset_id.startswith("tsplib-") and dataset_id != expected:
        raise ManifestError(
            f"a TSPLIB dataset id must be {expected!r} for problem {problem!r} (tsplib-<normalised NAME>), got {dataset_id!r}"
        )
    if native:
        record_levels, level_index = list(NATIVE_LEVELS), None
        policy = "native_uncapped"
    else:
        record_levels = [int(level) for level in levels]
        budget = row.get("evaluation_budget")
        if not _is_int(budget) or budget not in record_levels:
            raise ManifestError(f"evaluation_budget {budget!r} is not one of the dataset's levels {record_levels}")
        level_index, policy = record_levels.index(budget), "atomic_upper_bound_v1"
    stages = _stage_records(row)
    allocation = {
        str(stage["name"]): stage["allocated_evaluations"]
        for stage in stages if _is_int(stage.get("allocated_evaluations"))
    }
    derived = {"run_seed": seed}
    for stage in stages:
        if _is_int(stage.get("seed")):
            derived[f"{stage['name']}_stage_seed"] = stage["seed"]
    policy_value = row.get("backend_policy")
    if policy_value not in _BACKEND_POLICY:
        raise ManifestError(f"row backend_policy {policy_value!r} is not understood: the backend policy is part of the manifest")
    # the checks are those the row's own fields show were run; the manifest asserts nothing the row does not carry
    passed = row.get("validation_status") == "passed" and row.get("hamiltonian_validation") == "passed"
    checks = ["result_record_validation"]
    if row.get("independent_objective_cost") is not None:
        checks.append("independent_cost_recomputation")
    if row.get("hamiltonian_validation") == "passed":
        checks.append("hamiltonian_cycle")
    if stages:
        checks.append("composite_stage_accounting")
    capabilities = {
        key: row[key] for key in ("canonical_algorithm_id", "algorithm_family", "problem_type", "variant")
        if row.get(key) is not None
    }
    capabilities["protocol"] = "native_termination" if native else "fixed_budget"
    manifest = RunManifestV1.model_validate({
        "schema_version": "uniride-run/v1",
        "run_id": make_run_id(study_id, dataset_id, algorithm_id, level_index, replicate),
        "study_id": study_id,
        "protocol_version": row.get("protocol_version"),
        "git": GitStateV1.model_validate(git).model_dump(),
        "environment": EnvironmentV1.model_validate(environment).model_dump(),
        "dataset": dataset.model_dump(mode="json"),
        "algorithm": {
            "algorithm_id": algorithm_id,
            "capabilities": capabilities,
            "requested_algorithm_id": row.get("requested_algorithm_id"),
            "backend_policy": _BACKEND_POLICY[policy_value],
            "backend_profile": _backend_profile(row),
            "capability_evidence_ids": list(row.get("capability_evidence_ids") or []),
            "configuration": copy.deepcopy(dict(configuration)),
            "composition_stages": stages,
        },
        "seeds": {"base_seed": base_seed, "derived": derived},
        "budget": {
            "levels": record_levels, "policy": policy,
            "objective_evaluations": row.get("objective_evaluations"), "stage_allocation": allocation,
        },
        "termination": {"reason": row.get("termination_reason"), "runtime_seconds": float(row.get("elapsed_ms", 0.0)) / 1000.0},
        "validation": {"passed": passed, "checks": checks},
        "outputs": [item.model_dump(mode="json") for item in outputs],
    })
    bad = _outputs_exclude_manifests(manifest.outputs)
    if bad:
        raise ManifestError(f"a run manifest must not list manifest, checksum or index files among its outputs: {bad}")
    return manifest


def comparable_manifest_view(manifest: RunManifestV1) -> dict[str, Any]:
    """The manifest without timing (``runtime_seconds``, stage ``elapsed_sec``) and without ``outputs``.

    ``outputs`` is left out because the result files carry ``elapsed_ms``: their checksums differ between two same-seed runs.
    Two same-seed runs have equal views."""
    view = manifest.model_dump(mode="json")
    view["termination"].pop("runtime_seconds", None)
    for stage in view["algorithm"]["composition_stages"]:
        stage.pop("elapsed_sec", None)
    view.pop("outputs", None)
    return view


# ----------------------------------------------------------------------------------------------- campaign writing
def _check_shared(manifests: Sequence[RunManifestV1], *, study_id: str, base_seed: int, git: GitStateV1, environment: EnvironmentV1) -> list[str]:
    errors = []
    for manifest in manifests:
        for name, got, want in (
            ("study_id", manifest.study_id, study_id), ("base_seed", manifest.seeds.base_seed, base_seed),
            ("git", manifest.git, git), ("environment", manifest.environment, environment),
        ):
            if got != want:
                errors.append(f"{manifest.run_id}: {name} {got!r} differs from the campaign's {want!r}")
    return errors


def write_run_campaign(
    output_dir: Path,
    *,
    mode: str,
    study_id: str,
    seed_protocol_version: str,
    base_seed: int,
    git: GitStateV1 | Mapping[str, Any],
    environment: EnvironmentV1 | Mapping[str, Any],
    status: str,
    runs: Sequence[tuple[Mapping[str, Any], RunManifestV1]],
    output_files: Sequence[str],
) -> RunIndexV1:
    """Write every run manifest, then the campaign index, each with its ``.sha256``; return the index.

    ``runs`` are ``(row, manifest)`` pairs; ``output_files`` are the result files (relative names, already written). Nothing is
    written when the pairs are inconsistent with the campaign values or share a run id."""
    if seed_protocol_version != SEED_PROTOCOL_VERSION:
        raise ManifestError(
            f"seed_protocol_version {seed_protocol_version!r} is not the implemented {SEED_PROTOCOL_VERSION!r}: "
            "the index field and the comparison key digest must not diverge"
        )
    output_dir = Path(output_dir)
    git_state, env = GitStateV1.model_validate(git), EnvironmentV1.model_validate(environment)
    ids = [manifest.run_id for _, manifest in runs]
    duplicates = sorted({run_id for run_id in ids if ids.count(run_id) > 1})
    if duplicates:
        raise ManifestError(f"duplicate run ids in one campaign: {duplicates}")
    errors = _check_shared(
        [manifest for _, manifest in runs], study_id=study_id, base_seed=base_seed, git=git_state, environment=env
    )
    if errors:
        raise ManifestError("; ".join(errors))
    outputs = []
    for name in output_files:
        if not (output_dir / name).is_file():
            raise ManifestError(f"output file {name!r} does not exist in {output_dir}")
        outputs.append(OutputChecksumV1(path=name, checksum=ChecksumV1(algorithm="sha256", value=file_sha256(output_dir / name))))
    bad = _outputs_exclude_manifests(outputs)
    if bad:
        raise ManifestError(f"the campaign outputs must not name manifest, checksum or index files: {bad}")
    entries = []
    for row, manifest in runs:
        try:
            digest = comparison_cell_key(row, manifest, allow_dirty=True).digest()
        except ComparisonIdentityError as exc:
            raise ManifestError(f"{manifest.run_id}: the row has no comparison identity: {exc}") from exc
        relative = f"{MANIFEST_DIR}/{manifest.run_id}.json"
        checksum = write_json_with_sidecar(output_dir / relative, manifest)
        entries.append(RunIndexEntryV1(
            run_id=manifest.run_id, manifest_path=relative, manifest_checksum=checksum, comparison_key_digest=digest,
        ))
    index = RunIndexV1(
        schema_version="uniride-run-index/v1", study_id=study_id, mode=mode, status=status,
        seed_protocol_version=seed_protocol_version, base_seed=base_seed, git=git_state, environment=env,
        runs=entries, outputs=outputs,
    )
    write_json_with_sidecar(output_dir / INDEX_FILE, index)
    return index


# ---------------------------------------------------------------------------------------------------- verification
class VerificationResult:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.errors: list[str] = []
        self.checked = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _verified_bytes(path: Path, root: Path, errors: list[str]) -> Optional[bytes]:
    """The bytes of ``path`` if its detached sidecar exists, names it and matches; else record why not."""
    label = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    sidecar = Path(str(path) + SIDECAR_SUFFIX)
    if not path.is_file():
        errors.append(f"{label}: file is missing")
        return None
    if not sidecar.is_file():
        errors.append(f"{label}: detached {SIDECAR_SUFFIX} file is missing (an incomplete write does not verify)")
        return None
    match = _SIDECAR_LINE.match(sidecar.read_text(encoding="ascii", errors="replace"))
    if match is None:
        errors.append(f"{label}{SIDECAR_SUFFIX}: not a '<sha256>  <file name>' line")
        return None
    if match.group(2) != path.name:
        errors.append(f"{label}{SIDECAR_SUFFIX}: names {match.group(2)!r}, not {path.name!r}")
        return None
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != match.group(1):
        errors.append(f"{label}: checksum mismatch (sidecar {match.group(1)}, file {actual})")
        return None
    return data


def _check_output(root: Path, item: OutputChecksumV1, where: str, errors: list[str]) -> None:
    target = (root / item.path).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        errors.append(f"{where}: output {item.path} is missing")
        return
    actual = file_sha256(target)
    if actual != item.checksum.value:
        errors.append(f"{where}: output {item.path} checksum mismatch (recorded {item.checksum.value}, file {actual})")


def _row_run_id(manifest: RunManifestV1, row: Mapping[str, Any]) -> Optional[str]:
    """The run id this row would have under ``manifest``'s dataset, level list and policy; ``None`` when the row cannot
    belong to it (a fixed row needs a budget that is one of the levels, a native row needs none)."""
    native = manifest.budget.policy == "native_uncapped"
    budget, levels = row.get("evaluation_budget"), list(manifest.budget.levels)
    if native:
        if budget is not None:
            return None
        level_index = None
    else:
        if not _is_int(budget) or budget not in levels:
            return None
        level_index = levels.index(budget)
    if not _is_int(row.get("replicate")):
        return None
    return make_run_id(manifest.study_id, manifest.dataset.dataset_id, manifest.algorithm.algorithm_id, level_index, row["replicate"])


def _bind_row(manifest: RunManifestV1, rows: list[dict[str, Any]], file_name: str, digest: str, errors: list[str]) -> list[int]:
    """Check the manifest against its row in ``rows`` and return the indices of the matching rows.

    A row matches on algorithm, protocol, dataset, run seed *and* run id (replicate and budget level): the seed depends only on
    problem and replicate, so one seed recurs at every budget level of a campaign."""
    seed = manifest.seeds.derived.get("run_seed")
    dataset_id = manifest.dataset.dataset_id
    indices = [
        i for i, row in enumerate(rows)
        if row.get("algorithm_id") == manifest.algorithm.algorithm_id
        and row.get("protocol_version") == manifest.protocol_version
        and row.get("dataset_id", dataset_id) == dataset_id
        and row.get("seed") == seed
        and _row_run_id(manifest, row) == manifest.run_id
    ]
    if len(indices) != 1:
        errors.append(
            f"{manifest.run_id}: {len(indices)} row(s) in {file_name} match the manifest "
            "(algorithm, protocol, dataset, run seed, budget level, replicate); expected exactly 1"
        )
        return indices
    row = rows[indices[0]]
    if row.get("objective_evaluations") != manifest.budget.objective_evaluations:
        errors.append(f"{manifest.run_id}: row objective_evaluations differs from the manifest's")
    try:
        actual = comparison_cell_key(row, manifest, allow_dirty=True).digest()
    except ComparisonIdentityError as exc:
        errors.append(f"{manifest.run_id}: the row does not belong to its manifest: {exc}")
        return indices
    if actual != digest:
        errors.append(f"{manifest.run_id}: comparison key digest differs from the index")
    return indices


def _load_rows(root: Path, path: str, cache: dict[str, list[dict[str, Any]]], errors: list[str]) -> list[dict[str, Any]]:
    if path not in cache:
        target = root / path
        rows: list[dict[str, Any]] = []
        if target.is_file():
            try:
                rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
            except ValueError:
                errors.append(f"{path}: not a JSON-lines file")
        cache[path] = rows
    return cache[path]


def verify_campaign_detailed(directory: Path | str) -> VerificationResult:
    """Recompute every checksum of a campaign directory and cross-check manifests, index and result rows."""
    root = Path(directory)
    result = VerificationResult(root)
    errors = result.errors
    if not root.is_dir():
        errors.append(f"{root}: not a directory")
        return result
    data = _verified_bytes(root / INDEX_FILE, root, errors)
    if data is None:
        return result
    try:
        index = RunIndexV1.model_validate_json(data)
    except ValidationError as exc:
        errors.append(f"{INDEX_FILE}: not a valid {RunIndexV1.__name__}: {exc.error_count()} error(s)")
        return result
    if index.seed_protocol_version != SEED_PROTOCOL_VERSION:
        errors.append(
            f"{INDEX_FILE}: seed_protocol_version {index.seed_protocol_version!r} is not the implemented {SEED_PROTOCOL_VERSION!r}"
        )
    for item in index.outputs:
        _check_output(root, item, INDEX_FILE, errors)
    row_cache: dict[str, list[dict[str, Any]]] = {}
    bound: dict[tuple[str, int], list[str]] = {}
    listed: set[str] = set()
    for entry in index.runs:
        relative = entry.manifest_path
        listed.update({relative, relative + SIDECAR_SUFFIX})
        if relative != f"{MANIFEST_DIR}/{entry.run_id}.json":
            errors.append(f"{entry.run_id}: manifest path {relative} is not {MANIFEST_DIR}/<run_id>.json")
            continue
        raw = _verified_bytes(root / relative, root, errors)
        if raw is None:
            continue
        result.checked += 1
        if hashlib.sha256(raw).hexdigest() != entry.manifest_checksum.value:
            errors.append(f"{relative}: checksum mismatch against the index entry")
        try:
            manifest = RunManifestV1.model_validate_json(raw)
        except ValidationError as exc:
            errors.append(f"{relative}: not a valid RunManifestV1: {exc.error_count()} error(s)")
            continue
        if manifest.run_id != entry.run_id:
            errors.append(f"{relative}: run_id {manifest.run_id!r} differs from the index entry's {entry.run_id!r}")
        errors.extend(_check_shared([manifest], study_id=index.study_id, base_seed=index.base_seed, git=index.git, environment=index.environment))
        bad = _outputs_exclude_manifests(manifest.outputs)
        if bad:
            errors.append(f"{relative}: the manifest lists manifest, checksum or index files among its outputs: {bad}")
        if not manifest.outputs:
            errors.append(f"{relative}: the manifest lists no result file")
        if manifest.budget.policy == "native_uncapped" and list(manifest.budget.levels) != NATIVE_LEVELS:
            errors.append(
                f"{relative}: a native manifest carries the sentinel levels {NATIVE_LEVELS} (no budget level), "
                f"got {list(manifest.budget.levels)}"
            )
        for item in manifest.outputs:
            _check_output(root, item, relative, errors)
        for item in manifest.outputs:
            if not item.path.endswith(".jsonl") or not (root / item.path).is_file():
                continue
            rows = _load_rows(root, item.path, row_cache, errors)
            for i in _bind_row(manifest, rows, item.path, entry.comparison_key_digest, errors):
                bound.setdefault((item.path, i), []).append(manifest.run_id)
    # completeness: every result row is bound by exactly one manifest, and the index lists no other run
    rows_total = 0
    for item in index.outputs:
        if item.path not in RESULT_FILES:
            continue
        rows = _load_rows(root, item.path, row_cache, errors)
        rows_total += len(rows)
        for i in range(len(rows)):
            owners = bound.get((item.path, i), [])
            if not owners:
                errors.append(f"{item.path}: row {i + 1} has no run manifest")
            elif len(owners) > 1:
                errors.append(f"{item.path}: row {i + 1} is bound by {len(owners)} manifests {owners}")
    if len(index.runs) != rows_total:
        errors.append(f"{INDEX_FILE}: lists {len(index.runs)} run(s) but the result files hold {rows_total} row(s)")
    folder = root / MANIFEST_DIR
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            relative = f"{MANIFEST_DIR}/{path.name}"
            if relative not in listed:
                errors.append(f"{relative}: file is not listed in {INDEX_FILE}")
    expected = {INDEX_FILE, INDEX_FILE + SIDECAR_SUFFIX, MANIFEST_DIR, *REPORT_FILES}
    expected.update(PurePosixPath(item.path).parts[0] for item in index.outputs)
    for path in sorted(root.iterdir()):
        if path.name not in expected:
            errors.append(f"{path.name}: unexpected file in the campaign folder (not the index, a listed output, a report or {MANIFEST_DIR}/)")
    return result


def verify_campaign(directory: Path | str) -> list[str]:
    """The verification errors of a campaign directory; an empty list means it verifies."""
    return verify_campaign_detailed(directory).errors


__all__ = [
    "INDEX_FILE", "MANIFEST_DIR", "ManifestError", "NATIVE_LEVELS", "REPORT_FILES", "RESULT_FILES", "SIDECAR_SUFFIX", "STATISTICS_LIBRARY_NONE",
    "VerificationResult", "build_run_manifest", "canonical_json_bytes", "collect_environment", "comparable_manifest_view",
    "file_sha256", "make_run_id", "verify_campaign", "verify_campaign_detailed", "write_json_with_sidecar",
    "write_run_campaign",
]
