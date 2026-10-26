"""Run manifests, campaign index, detached ``.sha256`` files and their verifier (Gate D, D-02).

Design "Reproducibility Manifest" (``ACADEMIC_STUDY_UNIFICATION_DESIGN.md``): every run records its git state, environment,
dataset, algorithm, seeds, budget, termination, validation and output checksums; a detached ``<manifest>.sha256`` holds the
manifest's own checksum, so the manifest never hashes itself; writes are atomic so an interrupted run cannot masquerade as
complete.

Granularity (plan D-02, lead recommendation): one ``RunManifestV1`` per run (algorithm x dataset x budget level x
replicate) plus one campaign index (``uniride-run-index/v2``) that lists every manifest with its checksum and carries what the
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
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Optional, Sequence

from pydantic import BaseModel, ValidationError

from academic_benchmark.analysis.identity import SEED_PROTOCOL_VERSION, ComparisonIdentityError, comparison_cell_key
from academic_benchmark.contracts import DatasetManifestV1, OutputChecksumV1, RunManifestV1
from academic_benchmark.contracts.common import ChecksumV1
from academic_benchmark.contracts.run import EnvironmentV1, GitStateV1
from academic_benchmark.committed_bytes import GitQueryFailed, run_git
from academic_benchmark.contracts.run_index import (
    AnalysisPlanRefV1,
    FailedRunV1,
    OutputLocationV1,
    PlannedRunsV1,
    ProfileRefV1,
    RunIndexEntryV1,
    RunIndexV2,
)
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.protocol_registry import classify_row

INDEX_FILE = "run_index.json"
MANIFEST_DIR = "manifests"
SIDECAR_SUFFIX = ".sha256"
# result files whose every row needs a manifest (the failed-run file holds records, not observations)
RESULT_FILES = ("fixed_runs.jsonl", "native_runs.jsonl")
# The reports quote the index checksum, so the index cannot list them (D-02 contract): none of these files is covered by a checksum,
# and nothing reads them back as input. D-07 adds the descriptive report, which is no different from run_report in this respect.
DESCRIPTIVE_REPORT_FILES = ("descriptive_report.txt", "descriptive_report.json")
REPORT_FILES = ("smoke_report.txt", "smoke_report.json", "run_report.txt", "run_report.json", *DESCRIPTIVE_REPORT_FILES)
FAILED_FILE = "failed_runs.jsonl"
# the schema version the verifier refuses with a message of its own (v1 holds no profile/plan hash, planned counts, output location or failed list)
REFUSED_INDEX_SCHEMA = "uniride-run-index/v1"
INDEX_SCHEMA = "uniride-run-index/v2"
# the committed analysis plan sits next to its study profile (``studies.service.ANALYSIS_PLAN_FILENAME``; a test pins the equality)
ANALYSIS_PLAN_FILE_NAME = "analysis_plan.json"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
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


def failed_run_entries(records: Iterable[Mapping[str, Any]]) -> list[FailedRunV1]:
    """The index records of ``failed_runs.jsonl`` rows (the fields ``FailedRunV1`` names, as the file has them)."""
    entries = []
    for number, record in enumerate(records, start=1):
        try:
            entries.append(FailedRunV1.model_validate({name: record.get(name) for name in FailedRunV1.model_fields}))
        except ValidationError as exc:
            raise ManifestError(f"{FAILED_FILE}: record {number} has no valid failed-run fields ({exc.error_count()} error(s))") from exc
    return entries


def outside_location(output: Path, checked_against: Sequence[Path]) -> dict[str, Any]:
    """The ``output_location`` record of a campaign that passed the outside-the-repository check against ``checked_against``
    (G6): the output folder as an absolute path and the trees it was checked against."""
    return {
        "path": str(Path(output).resolve()),
        "outside_repository_check": {"result": "outside_repository", "checked_against": [str(Path(p)) for p in checked_against]},
    }


def _failed_file_entries(path: Path) -> list[FailedRunV1]:
    if not path.is_file():
        return []
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except ValueError as exc:
        raise ManifestError(f"{FAILED_FILE}: not a JSON-lines file") from exc
    if any(not isinstance(record, dict) for record in records):
        raise ManifestError(f"{FAILED_FILE}: every line must be a JSON object")
    return failed_run_entries(records)


def _campaign_field_errors(
    *, mode: str, status: str, completed: int, planned: PlannedRunsV1, failed: Sequence[FailedRunV1], output_names: Sequence[str]
) -> list[str]:
    """Rules between the v2 campaign fields that the writer enforces and the verifier re-checks."""
    errors = []
    done = completed + len(failed)
    if done > planned.runs:
        errors.append(f"the campaign lists {completed} run(s) and {len(failed)} failed run(s) but planned {planned.runs}")
    elif mode == "paper" and done != planned.runs:
        errors.append(
            f"a paper campaign plans the whole profile: it planned {planned.runs} run(s) but lists {completed} run(s) "
            f"and {len(failed)} failed run(s)"
        )
    if (status == "failed") != bool(failed):
        errors.append(f"status {status!r} disagrees with the failed-run list ({len(failed)} failed run(s))")
    if bool(failed) != (FAILED_FILE in output_names):
        errors.append(f"{FAILED_FILE} must be an output exactly when the index lists failed runs")
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
    profile: ProfileRefV1 | Mapping[str, Any],
    analysis_plan: AnalysisPlanRefV1 | Mapping[str, Any],
    planned: PlannedRunsV1 | Mapping[str, Any],
    output_location: OutputLocationV1 | Mapping[str, Any],
    failed_runs: Sequence[FailedRunV1 | Mapping[str, Any]],
) -> RunIndexV2:
    """Write every run manifest, then the campaign index, each with its ``.sha256``; return the index.

    ``runs`` are ``(row, manifest)`` pairs; ``output_files`` are the result files (relative names, already written).
    ``profile``, ``analysis_plan``, ``planned``, ``output_location`` and ``failed_runs`` are the campaign fields of
    ``uniride-run-index/v2`` (D-10 gaps G1, G2, G3, G6, G7). Nothing is written when the pairs are inconsistent with the
    campaign values or share a run id, when a paper campaign did not plan exactly the runs it lists (completed plus failed), when
    a campaign lists more runs than it planned, when ``status`` disagrees with the failed list or when the failed list differs
    from ``failed_runs.jsonl``."""
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
    try:
        campaign = {
            "profile": ProfileRefV1.model_validate(profile), "analysis_plan": AnalysisPlanRefV1.model_validate(analysis_plan),
            "planned": PlannedRunsV1.model_validate(planned), "output_location": OutputLocationV1.model_validate(output_location),
            "failed_runs": [FailedRunV1.model_validate(item) for item in failed_runs],
        }
    except ValidationError as exc:
        raise ManifestError(f"the campaign fields of the run index are not valid: {exc.error_count()} error(s): {exc}") from exc
    errors = _campaign_field_errors(
        mode=mode, status=status, completed=len(runs), planned=campaign["planned"], failed=campaign["failed_runs"],
        output_names=list(output_files),
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
    if (output_dir / FAILED_FILE).is_file() or campaign["failed_runs"]:
        written = _failed_file_entries(output_dir / FAILED_FILE)
        if written != campaign["failed_runs"]:
            raise ManifestError(f"the failed runs of the index differ from {FAILED_FILE}")
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
    index = RunIndexV2(
        schema_version=INDEX_SCHEMA, study_id=study_id, mode=mode, status=status,
        seed_protocol_version=seed_protocol_version, base_seed=base_seed, git=git_state, environment=env,
        runs=entries, outputs=outputs, **campaign,
    )
    write_json_with_sidecar(output_dir / INDEX_FILE, index)
    return index


# ---------------------------------------------------------------------------------------------------- verification
class VerificationResult:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.errors: list[str] = []
        # facts that are not failures but that a reader must see, e.g. a check that could not be made (never silent)
        self.notes: list[str] = []
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


def _check_recorded_hashes(index: RunIndexV2, repository_root: Path, errors: list[str], notes: list[str]) -> None:
    """Compare the profile and analysis-plan sha256 of the index with the files it names (working-tree bytes, as the run service
    hashed them), when the repository at ``repository_root`` is at the commit the campaign ran at; otherwise say it was not checked."""
    skipped = "profile and analysis plan hashes not checked"
    try:
        head = run_git(["rev-parse", "HEAD"], repository_root).decode("utf-8", "replace").strip()
    except GitQueryFailed as exc:
        notes.append(f"{skipped}: git cannot answer in {repository_root} ({exc.kind})")
        return
    commit = index.git.commit
    if head != commit:
        notes.append(
            f"{skipped}: the repository at {repository_root} is at commit {head[:12]}, the campaign ran at commit "
            f"{commit[:12]}; check out the campaign commit (or pass --repository-root) to compare them"
        )
        return
    matched, before = [], len(errors)
    for label, ref in (("profile", index.profile), ("analysis plan", index.analysis_plan)):
        if ref.path is None or ref.sha256 is None:
            notes.append(f"{label}: no file recorded, so no hash to compare")
            continue
        target = repository_root / ref.path
        if not target.is_file():
            errors.append(f"{INDEX_FILE}: the {label} file {ref.path} does not exist at commit {commit[:12]}")
            continue
        actual = file_sha256(target)
        if actual != ref.sha256:
            errors.append(
                f"{INDEX_FILE}: the {label} sha256 differs from the file {ref.path} at commit {commit[:12]} "
                f"(recorded {ref.sha256}, file {actual}; a changed file, or another core.autocrlf than the run's)"
            )
        else:
            matched.append(label)
    if len(errors) == before and matched:
        notes.append(f"{' and '.join(matched)} sha256 match the file(s) at commit {commit[:12]}")


def verify_campaign_detailed(directory: Path | str, *, repository_root: Path | str | None = None) -> VerificationResult:
    """Recompute every checksum of a campaign directory and cross-check manifests, index and result rows.

    ``repository_root`` (default: the repository this code lives in) is where the profile and analysis plan the index names are
    compared with the recorded hashes; the comparison needs the repository to be at the campaign's commit, and a check that
    cannot be made is reported in ``notes``, never skipped silently."""
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
        declared = json.loads(data).get("schema_version")
    except (ValueError, AttributeError):
        declared = None
    if declared == REFUSED_INDEX_SCHEMA:
        errors.append(
            f"{INDEX_FILE}: schema {REFUSED_INDEX_SCHEMA} is refused: it records no profile or analysis-plan hash, planned run "
            f"count, output location or failed-run list. Only {INDEX_SCHEMA} is verified; re-run the campaign "
            "(no paper evidence exists under v1)"
        )
        return result
    try:
        index = RunIndexV2.model_validate_json(data)
    except ValidationError as exc:
        errors.append(f"{INDEX_FILE}: not a valid {RunIndexV2.__name__}: {exc.error_count()} error(s)")
        return result
    if index.seed_protocol_version != SEED_PROTOCOL_VERSION:
        errors.append(
            f"{INDEX_FILE}: seed_protocol_version {index.seed_protocol_version!r} is not the implemented {SEED_PROTOCOL_VERSION!r}"
        )
    for item in index.outputs:
        _check_output(root, item, INDEX_FILE, errors)
    row_cache: dict[str, list[dict[str, Any]]] = {}
    _check_campaign_fields(index, root, result, row_cache, Path(repository_root) if repository_root is not None else _REPOSITORY_ROOT)
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


def _check_campaign_fields(
    index: RunIndexV2, root: Path, result: VerificationResult, row_cache: dict[str, list[dict[str, Any]]], repository_root: Path
) -> None:
    """The v2 campaign fields: planned counts, failed list against ``failed_runs.jsonl``, plan path, output location, hashes."""
    errors = result.errors
    errors.extend(
        f"{INDEX_FILE}: {message}" for message in _campaign_field_errors(
            mode=index.mode, status=index.status, completed=len(index.runs), planned=index.planned, failed=index.failed_runs,
            output_names=[item.path for item in index.outputs],
        )
    )
    failed_path = root / FAILED_FILE
    if failed_path.is_file():
        rows = _load_rows(root, FAILED_FILE, row_cache, errors)
        try:
            written = failed_run_entries(rows)
        except ManifestError as exc:
            errors.append(str(exc))
        else:
            if written != index.failed_runs:
                errors.append(
                    f"{INDEX_FILE}: the failed runs of the index ({len(index.failed_runs)}) differ from {FAILED_FILE} "
                    f"({len(written)} record(s)): the failures must be listed in the index exactly as the file has them"
                )
    elif index.failed_runs:
        errors.append(f"{INDEX_FILE}: lists {len(index.failed_runs)} failed run(s) but {FAILED_FILE} is missing")
    if index.analysis_plan.path is not None:
        expected = (PurePosixPath(index.profile.path).parent / ANALYSIS_PLAN_FILE_NAME).as_posix()
        if index.analysis_plan.path != expected:
            errors.append(f"{INDEX_FILE}: the analysis plan path {index.analysis_plan.path} is not {expected} (next to the profile)")
    if Path(index.output_location.path).resolve() != root.resolve():
        result.notes.append(
            f"the campaign folder {root} is not the recorded output location {index.output_location.path} (moved or copied)"
        )
    _check_recorded_hashes(index, repository_root, errors, result.notes)


@dataclass(frozen=True)
class VerifiedCampaign:
    """A campaign directory that verified: its index, the sha256 of ``run_index.json``, every completed row paired with its
    run manifest (``items``, in result-file order), the failed-run records (``failed``) and the verifier's ``notes`` (checks it
    could not make or facts a reader must see; a note is not a pass, and a report must show them)."""

    index: RunIndexV2
    index_sha256: str
    items: list
    failed: list
    notes: tuple[str, ...] = ()


def load_verified_campaign(directory: Path | str, *, repository_root: Path | str | None = None) -> VerifiedCampaign:
    """Verify ``directory`` (``verify_campaign_detailed``) and return its rows bound to their manifests.

    ``repository_root`` is the repository the caller loads the study from (default: the repository this code lives in); the
    recorded profile and analysis-plan hashes are checked against that tree. Raises ``ManifestError`` listing the verification
    errors when the campaign does not verify, so that a report or an analysis never reads rows whose checksums, manifests or index
    do not hold. The verifier's notes are returned in ``notes``. Rows are returned as read (no gap columns)."""
    root = Path(directory)
    result = verify_campaign_detailed(root, repository_root=repository_root)
    if not result.ok:
        raise ManifestError(f"{root}: the campaign does not verify ({len(result.errors)} problem(s)): " + "; ".join(result.errors[:5]))
    index_bytes = (root / INDEX_FILE).read_bytes()
    index = RunIndexV2.model_validate_json(index_bytes)
    row_cache: dict[str, list[dict[str, Any]]] = {}
    items: list = []
    errors: list[str] = []
    for entry in index.runs:
        manifest = RunManifestV1.model_validate_json((root / entry.manifest_path).read_bytes())
        for output in manifest.outputs:
            if output.path not in RESULT_FILES:
                continue
            rows = _load_rows(root, output.path, row_cache, errors)
            for i in _bind_row(manifest, rows, output.path, entry.comparison_key_digest, errors):
                items.append((output.path, i, rows[i], manifest))
    if errors:
        raise ManifestError(f"{root}: rows could not be bound to their manifests: " + "; ".join(errors[:5]))
    order = {name: position for position, name in enumerate(RESULT_FILES)}
    items.sort(key=lambda item: (order[item[0]], item[1]))
    failed_path = root / FAILED_FILE
    failed = [json.loads(line) for line in failed_path.read_text(encoding="utf-8").splitlines() if line.strip()] if failed_path.is_file() else []
    return VerifiedCampaign(
        index=index, index_sha256=hashlib.sha256(index_bytes).hexdigest(),
        items=[(row, manifest) for _, _, row, manifest in items], failed=failed, notes=tuple(result.notes),
    )


def verify_campaign(directory: Path | str) -> list[str]:
    """The verification errors of a campaign directory; an empty list means it verifies."""
    return verify_campaign_detailed(directory).errors


__all__ = [
    "DESCRIPTIVE_REPORT_FILES", "FAILED_FILE", "VerifiedCampaign", "load_verified_campaign", "INDEX_FILE", "MANIFEST_DIR", "ManifestError", "NATIVE_LEVELS", "REPORT_FILES", "RESULT_FILES", "SIDECAR_SUFFIX", "STATISTICS_LIBRARY_NONE",
    "ANALYSIS_PLAN_FILE_NAME", "INDEX_SCHEMA", "REFUSED_INDEX_SCHEMA", "VerificationResult", "build_run_manifest", "failed_run_entries", "canonical_json_bytes", "collect_environment", "comparable_manifest_view",
    "file_sha256", "make_run_id", "outside_location", "verify_campaign", "verify_campaign_detailed", "write_json_with_sidecar",
    "write_run_campaign",
]
