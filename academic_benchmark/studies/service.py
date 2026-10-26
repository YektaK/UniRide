"""Study service: load, resolve, preflight and expand an academic study profile (Gate C, C-11).

A study JSON (``uniride-study/v1``) is turned into an immutable plan of rows:

1. ``load_study``        parse and validate the study with ``StudyManifestV1``;
2. ``resolve_datasets``  load every dataset manifest (repository-relative path) and verify the
                         sha256 of the artifact it references;
3. ``preflight_study``   require one VERIFIED capability claim per (algorithm, problem family,
                         protocol, backend policy) the study needs, using ``find_capability_claim``;
4. ``expand_plan``       one row per (dataset, protocol, algorithm, budget level, replicate) with
                         the paired seed and seed group.

Budget levels (C-19): a study gives either one ``fixed_budget_levels`` list for every dataset or a
``scaled_fixed_budget_levels`` table (rule ``two_opt_scan_multiples_v1``: ``multiplier x n(n-1)/2``
per dataset). ``fixed_budget_levels_for`` recomputes every table entry from the dataset manifest's
``dimension`` (which must equal the artifact's ``DIMENSION:`` header) and refuses a mismatch, a
missing or an extra dataset key; ``expand_plan`` uses it, so a plan is never built from an
unchecked table. All algorithms of a study get the same levels on a given dataset.

Budget levels are never merged: every fixed-budget row carries its own level and native rows carry
none, so the fixed and native protocols stay separate by construction (AGENTS.md).

Seeds: the plan builds its manifests with the governed gateway's own factory
(``governed_comparison_manifest``): a ``FairComparisonManifest`` (fair v2) for fixed-budget rows and
a ``NativeComparisonManifest`` for native rows, both with the study's ``base_seed``. A study whose
primary or secondary ``protocol_version`` differs from the gateway constants is refused (fail
closed). The problem identity in the seed payload is the TSPLIB problem name, read from the
``NAME:`` header of the artifact (``problem_name``; ``normalize_problem`` is applied by the
manifest), because that is what executors, pilots and validators pass as ``problem.name``. The
manifest's ``dataset_id`` is only the row's dataset key and never enters a seed. Replicates are
numbered from 0, like the pilots. Neither seed depends on the algorithm or the budget level, so
rows of one problem and replicate are paired across algorithms and levels. A native algorithm list
of ``None`` means all study algorithms.

Analysis plan (Gate D, D-09): ``analysis_plan_id`` of a study resolves to ``analysis_plan.json`` in
the folder of the study file (schema ``uniride-analysis-plan/v1``). ``load_study(mode=...)`` and
``load_study_with_plan`` resolve it: paper mode refuses an unknown, invalid, mismatching or
non-``active`` plan; smoke mode keeps going and returns a label that says why the plan is not
usable for inference. Without a mode ``load_study`` behaves as before.

The service never runs a solver, never reads ``tsplib.db`` and never writes files.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Sequence

from pydantic import ValidationError

from academic_benchmark.contracts import AnalysisPlanV1, DatasetManifestV1, StudyManifestV1
from academic_benchmark.contracts.study import TWO_OPT_SCAN_RULE, two_opt_scan_size
from academic_benchmark.contracts.common import validate_repository_relative_path
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
from academic_benchmark.core.execution_gateway import (
    GOVERNED_FAIR_PROTOCOL_VERSION,
    governed_comparison_manifest,
)
from academic_benchmark.native_protocol import NATIVE_PROTOCOL
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
    problem_name: str
    artifact_dimension: int | None = None  # the artifact's DIMENSION: header, if it has one

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
    problem_name: str
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
    # the files the plan was read from, as the run index records them (G1): sha256 of the working-tree bytes (``read_bytes()``);
    # the analysis plan fields are ``None`` when the plan did not resolve (missing, invalid, or not this study's plan)
    study_path: str
    study_sha256: str
    analysis_plan_path: str | None
    analysis_plan_sha256: str | None


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


def load_study(
    study_path: str, *, repository_root: Path, mode: AnalysisPlanMode | None = None
) -> StudyManifestV1:
    """Load and validate one study JSON given by a repository-relative path.

    With ``mode`` the study's analysis plan must also resolve (see ``resolve_analysis_plan``):
    ``"paper"`` raises ``StudyServiceError`` when it does not; ``"smoke"`` never raises for the
    plan (use ``load_study_with_plan`` to read the label). ``mode=None`` does not look at the plan.
    """
    if mode is not None:
        _check_mode(mode)
    path = _resolve_inside(Path(repository_root), study_path, "study path")
    payload = _read_json(path, "study manifest")
    try:
        study = StudyManifestV1.model_validate(payload)
    except ValidationError as exc:
        raise StudyServiceError(f"study manifest {study_path!r} is invalid: {exc}") from exc
    if study.primary_protocol.protocol_version != GOVERNED_FAIR_PROTOCOL_VERSION:
        raise StudyServiceError(
            f"primary protocol_version {study.primary_protocol.protocol_version!r} differs from the "
            f"governed gateway version {GOVERNED_FAIR_PROTOCOL_VERSION!r}"
        )
    if (
        study.secondary_protocol is not None
        and study.secondary_protocol.protocol_version != NATIVE_PROTOCOL
    ):
        raise StudyServiceError(
            f"secondary protocol_version {study.secondary_protocol.protocol_version!r} differs "
            f"from the governed gateway version {NATIVE_PROTOCOL!r}"
        )
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
    if mode is not None:
        resolve_analysis_plan(study, study_path, repository_root=repository_root, mode=mode)
    return study


AnalysisPlanMode = Literal["smoke", "paper"]
ANALYSIS_PLAN_FILENAME = "analysis_plan.json"


@dataclass(frozen=True)
class AnalysisPlanResolution:
    """Outcome of resolving a study's ``analysis_plan_id``.

    ``plan`` is the validated plan, or ``None`` when it does not resolve (``problem`` says why).
    ``label`` is the sentence a smoke report prints about the plan.
    """

    analysis_plan_id: str
    plan: AnalysisPlanV1 | None
    problem: str | None
    label: str


@dataclass(frozen=True)
class LoadedStudy:
    study: StudyManifestV1
    analysis_plan: AnalysisPlanResolution


def _check_mode(mode: object) -> None:
    if mode not in ("smoke", "paper"):
        raise StudyServiceError(f"unknown mode {mode!r}; use 'smoke' or 'paper'")


def _plan_problem(
    study: StudyManifestV1, plan_path: Path, plan_name: str, repository_root: Path
) -> tuple[AnalysisPlanV1 | None, str | None]:
    """The validated plan, or ``None`` and the reason the plan id does not resolve."""
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"analysis plan file not found: {plan_name}"
    except (OSError, ValueError) as exc:
        return None, f"analysis plan file is not readable JSON: {plan_name} ({exc})"
    try:
        plan = AnalysisPlanV1.model_validate(payload)
    except ValidationError as exc:
        return None, f"analysis plan file {plan_name} is invalid: {exc}"
    if plan.analysis_plan_id != study.analysis_plan_id:
        return None, (
            f"{plan_name} declares analysis_plan_id {plan.analysis_plan_id!r}, "
            f"the study asks for {study.analysis_plan_id!r}"
        )
    if plan.study_id != study.study_id:
        return None, (
            f"{plan_name} belongs to study_id {plan.study_id!r}, the study is {study.study_id!r}"
        )
    problem_types: dict[str, str] = {}
    for ref in study.dataset_manifest_refs:
        manifest_path = _resolve_inside(Path(repository_root), ref, "dataset manifest ref")
        try:
            manifest = DatasetManifestV1.model_validate(
                _read_json(manifest_path, f"dataset manifest {ref!r}")
            )
        except (ValidationError, StudyServiceError) as exc:
            return None, f"dataset manifest {ref!r} cannot be read for the plan check: {exc}"
        problem_types[manifest.dataset_id] = manifest.problem_type
    for family in plan.families:
        for dataset_id in family.dataset_ids:
            if dataset_id not in problem_types:
                return None, (
                    f"family {family.family_id!r} names dataset {dataset_id!r}, "
                    "which is not a dataset of the study"
                )
            if problem_types[dataset_id] not in family.problem_types:
                return None, (
                    f"family {family.family_id!r} ({family.scope}) takes problem types "
                    f"{family.problem_types} but dataset {dataset_id!r} is "
                    f"{problem_types[dataset_id]}"
                )
    return plan, None


def resolve_analysis_plan(
    study: StudyManifestV1,
    study_path: str,
    *,
    repository_root: Path,
    mode: AnalysisPlanMode,
) -> AnalysisPlanResolution:
    """Resolve ``study.analysis_plan_id`` to the committed plan next to the study file.

    The plan must be a valid ``uniride-analysis-plan/v1`` document with the study's plan id and
    study id, and its families may only name datasets of the study with matching problem types.
    Paper mode raises ``StudyServiceError`` unless the plan resolves and is ``active``; smoke mode
    returns the reason in the label (descriptive output only, no inference).

    D-03 note: the paper-mode preflight of the study run service must go through
    ``load_study(mode="paper")`` or this function; a paper run that skips it would run without a
    resolved, active analysis plan.
    """
    _check_mode(mode)
    study_file = _resolve_inside(Path(repository_root), study_path, "study path")
    plan_path = study_file.parent / ANALYSIS_PLAN_FILENAME
    plan_name = (
        PurePosixPath(validate_repository_relative_path(study_path)).parent / ANALYSIS_PLAN_FILENAME
    ).as_posix()
    plan_id = study.analysis_plan_id
    plan, problem = _plan_problem(study, plan_path, plan_name, Path(repository_root))
    if plan is None:
        if mode == "paper":
            raise StudyServiceError(f"analysis plan {plan_id!r} does not resolve: {problem}")
        return AnalysisPlanResolution(
            plan_id,
            None,
            problem,
            f"analysis plan {plan_id} unresolved ({problem}): descriptive output only, no inference",
        )
    if plan.status != "active":
        names = ", ".join(item.field for item in plan.unresolved) or "none listed"
        if mode == "paper":
            raise StudyServiceError(
                f"analysis plan {plan_id!r} is {plan.status}, paper mode needs an active plan "
                f"(unresolved: {names})"
            )
        return AnalysisPlanResolution(
            plan_id,
            plan,
            None,
            f"analysis plan {plan_id} ({plan.status}; unresolved: {names}): "
            "descriptive output only, no inference",
        )
    return AnalysisPlanResolution(plan_id, plan, None, f"analysis plan {plan_id} (active)")


def load_study_with_plan(
    study_path: str, *, repository_root: Path, mode: AnalysisPlanMode
) -> LoadedStudy:
    """``load_study`` plus the analysis-plan resolution (and its label) for ``mode``."""
    _check_mode(mode)
    study = load_study(study_path, repository_root=repository_root)
    plan = resolve_analysis_plan(study, study_path, repository_root=repository_root, mode=mode)
    return LoadedStudy(study, plan)


_NAME_HEADER = re.compile(r"^NAME[ \t]*[: \t][ \t]*(\S+)", re.IGNORECASE | re.MULTILINE)
_SECTION = re.compile(r"^\s*[A-Z_]+_SECTION\b|^\s*EOF\b", re.MULTILINE)


def _problem_name_from_artifact(data: bytes, dataset_id: str) -> str:
    """TSPLIB problem name from the ``NAME:`` header (pattern of
    ``uniride_core/algorithms/tsplib_parser.py``, tightened so that a NAME line without a value
    is refused)."""
    text = data.decode("utf-8", errors="replace")
    section = _SECTION.search(text)
    header = text[: section.start()] if section else text
    names = {match.group(1) for match in _NAME_HEADER.finditer(header)}
    if len(names) != 1:
        raise StudyServiceError(
            f"artifact of dataset {dataset_id!r} needs exactly one NAME: header "
            f"(the seed identity), found {len(names)}"
        )
    return next(iter(names))


_DIMENSION_HEADER = re.compile(r"^DIMENSION[ \t]*[: \t][ \t]*(\d+)\s*$", re.IGNORECASE | re.MULTILINE)


def _dimension_from_artifact(data: bytes) -> int | None:
    text = data.decode("utf-8", errors="replace")
    section = _SECTION.search(text)
    header = text[: section.start()] if section else text
    values = {int(match.group(1)) for match in _DIMENSION_HEADER.finditer(header)}
    return next(iter(values)) if len(values) == 1 else None


def _native_algorithm_ids(study: StudyManifestV1) -> tuple[str, ...]:
    """Algorithms run under the native protocol; ``None`` means all study algorithms."""
    if study.secondary_protocol is None:
        return ()
    listed = study.secondary_protocol.algorithm_ids
    return tuple(study.algorithm_ids if listed is None else listed)


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
            artifact_bytes = artifact.read_bytes()
            digest = hashlib.sha256(artifact_bytes).hexdigest()
        except OSError as exc:
            raise StudyServiceError(
                f"artifact of dataset {manifest.dataset_id!r} is not readable: {manifest.artifact_path!r}"
            ) from exc
        if digest != manifest.checksum.value:
            raise StudyServiceError(
                f"checksum mismatch for dataset {manifest.dataset_id!r}: manifest "
                f"{manifest.checksum.value}, artifact {digest}"
            )
        problem_name = _problem_name_from_artifact(artifact_bytes, manifest.dataset_id)
        resolved.append(
            ResolvedDataset(
                ref, manifest, digest, problem_name, _dimension_from_artifact(artifact_bytes)
            )
        )
    return tuple(resolved)


def fixed_budget_levels_for(study: StudyManifestV1, dataset: ResolvedDataset) -> tuple[int, ...]:
    """The fixed budget levels of ``dataset`` in ``study``, recomputed and checked (C-19)."""
    if study.fixed_budget_levels is not None:
        return tuple(study.fixed_budget_levels)
    scaled = study.scaled_fixed_budget_levels
    if scaled is None or scaled.rule != TWO_OPT_SCAN_RULE:
        raise StudyServiceError("study has no fixed budget levels this service can compute")
    dataset_id = dataset.dataset_id
    if dataset_id not in scaled.levels_by_dataset:
        raise StudyServiceError(
            f"scaled_fixed_budget_levels has no entry for dataset {dataset_id!r}; its keys must be "
            "the study's dataset ids"
        )
    n = dataset.manifest.dimension
    if dataset.artifact_dimension != n:
        raise StudyServiceError(
            f"dataset {dataset_id!r}: manifest dimension {n} differs from the artifact DIMENSION "
            f"header {dataset.artifact_dimension}; scaled budgets need both to agree"
        )
    scan = two_opt_scan_size(n)
    expected = tuple(multiplier * scan for multiplier in scaled.scan_multipliers)
    stated = tuple(scaled.levels_by_dataset[dataset_id])
    if stated != expected:
        raise StudyServiceError(
            f"scaled budget levels of dataset {dataset_id!r} are {list(stated)}; rule "
            f"{scaled.rule} with multipliers {scaled.scan_multipliers} and n(n-1)/2 = {scan} "
            f"(n = {n}) gives {list(expected)}"
        )
    return expected


def check_budget_levels(
    study: StudyManifestV1, datasets: Sequence[ResolvedDataset]
) -> dict[str, tuple[int, ...]]:
    """Levels per dataset id; a scaled table must name exactly the study's datasets."""
    scaled = study.scaled_fixed_budget_levels
    if scaled is not None:
        ids = {dataset.dataset_id for dataset in datasets}
        if set(scaled.levels_by_dataset) != ids:
            raise StudyServiceError(
                f"scaled_fixed_budget_levels keys {sorted(scaled.levels_by_dataset)} must equal "
                f"the study's dataset ids {sorted(ids)}"
            )
    return {dataset.dataset_id: fixed_budget_levels_for(study, dataset) for dataset in datasets}


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
    for algorithm_id in _native_algorithm_ids(study):
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
    """Expand the study into rows; fixed rows carry their budget level, native rows carry none.

    The seed manifests come from the governed gateway's factory, so a plan seed is by construction
    the seed the gateway accepts for ``problem.name == problem_name`` and the same replicate.
    """
    rows: list[PlanRow] = []
    levels_by_dataset = check_budget_levels(study, datasets)
    try:
        fixed_manifests = {
            level: governed_comparison_manifest(
                ExecutionProtocol.FIXED_BUDGET, level, study.base_seed
            )
            for levels in levels_by_dataset.values()
            for level in levels
        }
        native_manifest = (
            governed_comparison_manifest(
                ExecutionProtocol.NATIVE_TERMINATION, None, study.base_seed
            )
            if study.secondary_protocol is not None
            else None
        )
    except ValueError as exc:
        raise StudyServiceError(f"study seed manifest is invalid: {exc}") from exc
    native_ids = _native_algorithm_ids(study)
    for dataset in datasets:
        name = dataset.problem_name
        for algorithm_id in study.algorithm_ids:
            for level in levels_by_dataset[dataset.dataset_id]:
                manifest = fixed_manifests[level]
                for replicate in range(study.run_count):
                    rows.append(
                        PlanRow(
                            dataset_id=dataset.dataset_id,
                            problem_name=name,
                            algorithm_id=algorithm_id,
                            protocol=ExecutionProtocol.FIXED_BUDGET,
                            budget_level=level,
                            replicate=replicate,
                            seed=manifest.paired_seed(name, replicate),
                            seed_group=manifest.seed_group(name, replicate),
                        )
                    )
        if native_manifest is not None:
            for algorithm_id in native_ids:
                for replicate in range(study.run_count):
                    rows.append(
                        PlanRow(
                            dataset_id=dataset.dataset_id,
                            problem_name=name,
                            algorithm_id=algorithm_id,
                            protocol=ExecutionProtocol.NATIVE_TERMINATION,
                            budget_level=None,
                            replicate=replicate,
                            seed=native_manifest.paired_seed(name, replicate),
                            seed_group=native_manifest.seed_group(name, replicate),
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
    check_budget_levels(study, datasets)
    claims = preflight_study(study, datasets, backend_policy=backend_policy)
    rows = expand_plan(study, datasets)
    study_file = _resolve_inside(Path(repository_root), study_path, "study path")
    plan_relative = (PurePosixPath(validate_repository_relative_path(study_path)).parent / ANALYSIS_PLAN_FILENAME).as_posix()
    plan_file = study_file.parent / ANALYSIS_PLAN_FILENAME
    # the plan is recorded only when it resolved (valid, this study's plan id and study id, datasets match): the hash of a
    # file that did not resolve describes nothing the analysis used; the reason stays in the run report's plan label
    plan_resolved = resolve_analysis_plan(
        study, study_path, repository_root=repository_root, mode="smoke"
    ).plan is not None
    return StudyPlan(
        study, backend_policy, datasets, claims, rows,
        study_path=validate_repository_relative_path(study_path),
        study_sha256=hashlib.sha256(study_file.read_bytes()).hexdigest(),
        analysis_plan_path=plan_relative if plan_resolved else None,
        analysis_plan_sha256=hashlib.sha256(plan_file.read_bytes()).hexdigest() if plan_resolved else None,
    )
