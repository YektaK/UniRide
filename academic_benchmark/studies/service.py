"""Study service: load, resolve, preflight and expand an academic study profile (Gate C, C-11).

A study JSON (``uniride-study/v1``) is turned into an immutable plan of rows:

1. ``load_study``        parse and validate the study with ``StudyManifestV1``;
2. ``resolve_datasets``  load every dataset manifest (repository-relative path) and verify the
                         sha256 of the artifact it references;
3. ``preflight_study``   require one VERIFIED capability claim per (algorithm, problem family,
                         protocol, backend policy) the study needs, using ``find_capability_claim``;
4. ``expand_plan``       one row per (dataset, protocol, algorithm, budget level, replicate) with
                         the paired seed and seed group.

Budget levels are never merged: every fixed-budget row carries its own level and native rows carry
none, so the fixed and native protocols stay separate by construction (AGENTS.md).

Seeds: fixed-budget rows use ``FairComparisonManifest`` (protocol version and budget policy of the
primary protocol, the study's ``base_seed``), native rows use ``NativeComparisonManifest`` with the
secondary protocol version, because that is the manifest the native pilot validates results with.
The problem identity in the seed payload is the dataset manifest's ``dataset_id``. Replicates are
numbered from 0, like the pilots. Neither seed depends on the algorithm or the budget level, so
rows of one dataset and replicate are paired across algorithms and levels.

The service never runs a solver, never reads ``tsplib.db`` and never writes files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

from pydantic import ValidationError

from academic_benchmark.contracts import DatasetManifestV1, StudyManifestV1
from academic_benchmark.contracts.common import validate_repository_relative_path
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.fairness import FairComparisonManifest
from academic_benchmark.native_protocol import NativeComparisonManifest
from uniride_core.algorithms.capabilities import (
    BackendKind,
    BackendPolicy,
    CapabilityClaim,
    ExecutionBackendProfile,
    ExecutionProtocol,
    ProblemContract,
    find_capability_claim,
    get_algorithm_capability,
)

SUPPORTED_SEED_PROTOCOL = "sha256-seed-v1"
DEFAULT_BACKEND_POLICY = BackendPolicy.PREFER_NUMBA_OBJECTIVE

_PROBLEM_CONTRACTS = {"TSP": ProblemContract.TSP, "ATSP": ProblemContract.ATSP}


class StudyServiceError(ValueError):
    """A study profile, dataset manifest or capability preflight was refused."""


@dataclass(frozen=True)
class ResolvedDataset:
    manifest_path: str
    manifest: DatasetManifestV1
    artifact_sha256: str

    @property
    def dataset_id(self) -> str:
        return self.manifest.dataset_id


@dataclass(frozen=True)
class ClaimCheck:
    algorithm_id: str
    problem: ProblemContract
    protocol: ExecutionProtocol
    backend_profile: ExecutionBackendProfile
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlanRow:
    dataset_id: str
    algorithm_id: str
    protocol: ExecutionProtocol
    budget_level: int | None
    replicate: int
    seed: int
    seed_group: str


@dataclass(frozen=True)
class StudyPlan:
    study: StudyManifestV1
    backend_policy: BackendPolicy
    datasets: tuple[ResolvedDataset, ...]
    claims: tuple[ClaimCheck, ...]
    rows: tuple[PlanRow, ...]


def _resolve_inside(repository_root: Path, relative: str, what: str) -> Path:
    try:
        normalized = validate_repository_relative_path(relative)
    except ValueError as exc:
        raise StudyServiceError(f"{what} must be repository-relative: {relative!r} ({exc})") from exc
    root = repository_root.resolve()
    target = (root / normalized).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise StudyServiceError(f"{what} escapes the repository: {relative!r}") from exc
    return target


def _read_json(path: Path, what: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StudyServiceError(f"{what} not found: {path.name}") from exc
    except (OSError, ValueError) as exc:
        raise StudyServiceError(f"{what} is not readable JSON: {path.name} ({exc})") from exc


def load_study(study_path: str, *, repository_root: Path) -> StudyManifestV1:
    """Load and validate one study JSON given by a repository-relative path."""
    path = _resolve_inside(Path(repository_root), study_path, "study path")
    payload = _read_json(path, "study manifest")
    try:
        study = StudyManifestV1.model_validate(payload)
    except ValidationError as exc:
        raise StudyServiceError(f"study manifest {study_path!r} is invalid: {exc}") from exc
    if study.seed_protocol_version != SUPPORTED_SEED_PROTOCOL:
        raise StudyServiceError(
            f"unsupported seed_protocol_version {study.seed_protocol_version!r}; "
            f"only {SUPPORTED_SEED_PROTOCOL!r} is implemented"
        )
    # defence in depth: the contract already refuses aliases, the plan must hold canonical IDs only
    listed = list(study.algorithm_ids)
    if study.secondary_protocol is not None and study.secondary_protocol.algorithm_ids:
        listed.extend(study.secondary_protocol.algorithm_ids)
    for algorithm_id in listed:
        try:
            resolution = resolve_algorithm_id(algorithm_id, IdentifierSource.MANIFEST)
        except Exception as exc:
            raise StudyServiceError(f"algorithm id {algorithm_id!r} is not canonical: {exc}") from exc
        if resolution.canonical_id != algorithm_id or resolution.alias_used:
            raise StudyServiceError(f"algorithm id {algorithm_id!r} is an alias")
    return study


def resolve_datasets(
    study: StudyManifestV1, *, repository_root: Path
) -> tuple[ResolvedDataset, ...]:
    """Load each dataset manifest and verify the checksum of its artifact."""
    resolved: list[ResolvedDataset] = []
    seen_refs: set[str] = set()
    seen_ids: set[str] = set()
    families = set(study.problem_families)
    for ref in study.dataset_manifest_refs:
        if ref in seen_refs:
            raise StudyServiceError(f"dataset manifest ref listed twice: {ref!r}")
        seen_refs.add(ref)
        manifest_path = _resolve_inside(Path(repository_root), ref, "dataset manifest ref")
        payload = _read_json(manifest_path, f"dataset manifest {ref!r}")
        try:
            manifest = DatasetManifestV1.model_validate(payload)
        except ValidationError as exc:
            raise StudyServiceError(f"dataset manifest {ref!r} is invalid: {exc}") from exc
        if manifest.dataset_id in seen_ids:
            raise StudyServiceError(f"dataset_id used twice in one study: {manifest.dataset_id!r}")
        seen_ids.add(manifest.dataset_id)
        if PurePosixPath(manifest.artifact_path).parts[:1] == ("archive",):
            raise StudyServiceError(
                f"dataset {manifest.dataset_id!r} references an archive path: {manifest.artifact_path!r}"
            )
        if manifest.problem_type not in families:
            raise StudyServiceError(
                f"dataset {manifest.dataset_id!r} has problem type {manifest.problem_type!r}, "
                f"which the study does not declare in problem_families {sorted(families)}"
            )
        artifact = _resolve_inside(
            Path(repository_root), manifest.artifact_path, f"artifact of dataset {manifest.dataset_id!r}"
        )
        try:
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        except OSError as exc:
            raise StudyServiceError(
                f"artifact of dataset {manifest.dataset_id!r} is not readable: {manifest.artifact_path!r}"
            ) from exc
        if digest != manifest.checksum.value:
            raise StudyServiceError(
                f"checksum mismatch for dataset {manifest.dataset_id!r}: manifest "
                f"{manifest.checksum.value}, artifact {digest}"
            )
        resolved.append(ResolvedDataset(ref, manifest, digest))
    return tuple(resolved)


def _backend_policy_accepts(policy: BackendPolicy, profile: ExecutionBackendProfile) -> bool:
    python_ok = profile.objective is BackendKind.PYTHON and profile.polish in (
        BackendKind.NONE,
        BackendKind.PYTHON,
    )
    numba_ok = profile.objective is BackendKind.NUMBA_NOPYTHON
    if policy is BackendPolicy.PYTHON_ONLY:
        return python_ok
    if policy is BackendPolicy.REQUIRE_NUMBA_OBJECTIVE:
        return numba_ok
    if policy is BackendPolicy.PREFER_NUMBA_OBJECTIVE:
        return python_ok or numba_ok
    return False


def _claim_is_complete(claim: CapabilityClaim, protocol: ExecutionProtocol) -> bool:
    return (
        claim.fixed_seed_deterministic
        and claim.truthful_result_reporting
        and (claim.problem is not ProblemContract.ATSP or claim.directed_cost_preserved)
        and (protocol is not ExecutionProtocol.FIXED_BUDGET or claim.exact_objective_accounting)
    )


def _verified_claim(
    algorithm_id: str,
    contract: ProblemContract,
    protocol: ExecutionProtocol,
    policy: BackendPolicy,
) -> CapabilityClaim:
    capability = get_algorithm_capability(algorithm_id)
    if capability is not None:
        # Numba claims come first under "prefer": same order as the gateway's selection
        ordered = sorted(
            capability.claims,
            key=lambda c: c.backend_profile.objective is not BackendKind.NUMBA_NOPYTHON,
        )
        for candidate in ordered:
            if candidate.problem is not contract or candidate.protocol is not protocol:
                continue
            if not _backend_policy_accepts(policy, candidate.backend_profile):
                continue
            claim = find_capability_claim(
                algorithm_id,
                problem=contract,
                protocol=protocol,
                backend_profile=candidate.backend_profile,
                composition=candidate.composition,
            )
            if claim is not None and _claim_is_complete(claim, protocol):
                return claim
    raise StudyServiceError(
        f"no verified {protocol.value} claim for {algorithm_id} on {contract.value} "
        f"under backend policy {policy.value}"
    )


def preflight_study(
    study: StudyManifestV1,
    datasets: Sequence[ResolvedDataset],
    *,
    backend_policy: BackendPolicy = DEFAULT_BACKEND_POLICY,
) -> tuple[ClaimCheck, ...]:
    """Require a verified claim for everything the study will run; refuse the study otherwise."""
    contracts: list[ProblemContract] = []
    for family in study.problem_families:
        if family not in _PROBLEM_CONTRACTS:
            raise StudyServiceError(
                f"problem family {family!r} has no verified capability contract "
                "(only TSP and ATSP are supported)"
            )
        contracts.append(_PROBLEM_CONTRACTS[family])
    needed: list[tuple[str, ExecutionProtocol]] = [
        (algorithm_id, ExecutionProtocol.FIXED_BUDGET) for algorithm_id in study.algorithm_ids
    ]
    if study.secondary_protocol is not None:
        native_ids = study.secondary_protocol.algorithm_ids
        for algorithm_id in native_ids if native_ids is not None else study.algorithm_ids:
            needed.append((algorithm_id, ExecutionProtocol.NATIVE_TERMINATION))
    checks: list[ClaimCheck] = []
    for algorithm_id, protocol in needed:
        for contract in contracts:
            claim = _verified_claim(algorithm_id, contract, protocol, backend_policy)
            checks.append(
                ClaimCheck(algorithm_id, contract, protocol, claim.backend_profile, claim.evidence_ids)
            )
    return tuple(checks)


def expand_plan(
    study: StudyManifestV1,
    datasets: Sequence[ResolvedDataset],
) -> tuple[PlanRow, ...]:
    """Expand the study into rows; fixed rows carry their budget level, native rows carry none."""
    rows: list[PlanRow] = []
    try:
        fixed_manifests = {
            level: FairComparisonManifest(
                evaluation_budget=level,
                base_seed=study.base_seed,
                protocol_version=study.primary_protocol.protocol_version,
                budget_policy=study.primary_protocol.budget_policy,
                comparison_regime=(
                    FairComparisonManifest.FIXED_EVALUATION_REGIME
                    if study.primary_protocol.protocol_version == FairComparisonManifest.V2_PROTOCOL
                    else None
                ),
            )
            for level in study.fixed_budget_levels
        }
        native_manifest = (
            NativeComparisonManifest(
                base_seed=study.base_seed,
                protocol_version=study.secondary_protocol.protocol_version,
            )
            if study.secondary_protocol is not None
            else None
        )
    except ValueError as exc:
        raise StudyServiceError(f"study seed manifest is invalid: {exc}") from exc
    native_ids: Sequence[str] = ()
    if study.secondary_protocol is not None:
        native_ids = study.secondary_protocol.algorithm_ids or study.algorithm_ids
    for dataset in datasets:
        problem = dataset.dataset_id
        for algorithm_id in study.algorithm_ids:
            for level in study.fixed_budget_levels:
                manifest = fixed_manifests[level]
                for replicate in range(study.run_count):
                    rows.append(
                        PlanRow(
                            problem,
                            algorithm_id,
                            ExecutionProtocol.FIXED_BUDGET,
                            level,
                            replicate,
                            manifest.paired_seed(problem, replicate),
                            manifest.seed_group(problem, replicate),
                        )
                    )
        if native_manifest is not None:
            for algorithm_id in native_ids:
                for replicate in range(study.run_count):
                    rows.append(
                        PlanRow(
                            problem,
                            algorithm_id,
                            ExecutionProtocol.NATIVE_TERMINATION,
                            None,
                            replicate,
                            native_manifest.paired_seed(problem, replicate),
                            native_manifest.seed_group(problem, replicate),
                        )
                    )
    return tuple(rows)


def build_study_plan(
    study_path: str,
    *,
    repository_root: Path,
    backend_policy: BackendPolicy = DEFAULT_BACKEND_POLICY,
) -> StudyPlan:
    """Load, resolve, preflight and expand a study in one call."""
    study = load_study(study_path, repository_root=repository_root)
    datasets = resolve_datasets(study, repository_root=repository_root)
    claims = preflight_study(study, datasets, backend_policy=backend_policy)
    rows = expand_plan(study, datasets)
    return StudyPlan(study, backend_policy, datasets, claims, rows)
