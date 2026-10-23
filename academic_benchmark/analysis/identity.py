"""Comparison identity for analysis: the pooling key below the protocol group (Gate D, D-01).

``protocol_registry.assert_single_pooling_group`` keeps fixed-budget, native and exact rows apart, and nothing more:
it maps fair protocol v1 and v2 rows to one group (``protocol_registry.py`` ``classify_row``) and ignores study,
dataset, budget level, algorithm configuration and code commit. This module adds the finer key that every analysis,
summary and report must use after that guard (plan 2026-10-23, section 3, D-01; DECISION_LOG A17 and A18).

``comparison_cell_key(row, manifest)`` returns a ``ComparisonCellKey``. Rows may be aggregated or tested together only
when their keys are equal, except for the dimension being compared (``assert_single_comparison_family``). Key fields:

=====================  ===============================================================================================
pooling_group          from ``protocol_registry`` (``fixed_budget`` or ``native``); exact/union/joint rows get no key
protocol_version       the exact label (``uniride-fair-tsp-v1`` and ``-v2`` are separate cells)
study_id               of the run manifest
dataset_identity       ``normalize_problem`` of the row's TSPLIB problem name (A17 C-11), never a file or dataset id
budget_level_index     position of the row's budget in the manifest's level list, never the raw budget (A17 C-19);
                       ``None`` for native rows
algorithm_id           canonical ID
configuration_hash     sha256 of the sorted JSON of the configured parameters, the normalised ``termination_policy``
                       (A17 C-16b) and the row's ``variant``; see ``configuration_hash`` for what is excluded
backend_policy,        the manifest's backend policy and execution profile (``objective=...;polish=...``); python
backend_profile        and numba rows are separate cells until the owner decides otherwise (Gate D DUZELT r1)
seed_protocol_version  the one implemented seed protocol
base_seed              of the run manifest (pairing basis)
evidence_class         ``current`` or ``historical_unverified`` (A13); anything else is refused
code_commit            git commit of the run manifest; one campaign is one clean commit (A18 OQ-10 a)
tree_dirty             the manifest's dirty flag; a dirty run has no code identity and is refused unless allowed
=====================  ===============================================================================================

Timing (``elapsed_ms``, the composite stages' ``elapsed_sec``) is never read, so it cannot enter an identity or a hash
(A17 C-09). Outcome fields of a row (``polish_policy`` flags and counts, ``termination_reason``, evaluations) are not
configuration and are not read either. The module reads nothing from disk and runs no solver.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Any, Iterable, Mapping, Optional

from academic_benchmark.contracts import RunManifestV1
from academic_benchmark.fairness import normalize_problem
from academic_benchmark.obsolete_results import EVIDENCE_CURRENT, EVIDENCE_HISTORICAL
from academic_benchmark.protocol_registry import assert_single_pooling_group, classify_row

# One seed protocol is implemented (``studies.service.SUPPORTED_SEED_PROTOCOL``, checked by a test). ``RunManifestV1``
# has no field for it, so the key states the implemented value.
SEED_PROTOCOL_VERSION = "sha256-seed-v1"

# ``termination_policy`` segments (``key=value`` separated by ``;``) that describe the run or the level, not the
# configuration: ``budget_exhausted`` is a result of local-search runs, ``polish_derived_seed`` derives from the run seed,
# ``global_cap`` derives from the budget level. Left in, they would split one configuration per replicate or instance.
# Everything else in the policy (iteration limits, ``reinit_*`` constants, ``global_fraction``, polish parameters) stays.
POLICY_NON_CONFIGURATION_KEYS = frozenset({"budget_exhausted", "polish_derived_seed", "global_cap"})
# the protocol manifest echoed into the parameters carries the level and base seed, which have their own key fields
CONFIGURATION_PROTOCOL_BLOCKS = ("fair_comparison", "native_comparison")

_EVIDENCE_LABELS = {
    EVIDENCE_CURRENT: EVIDENCE_CURRENT,
    "current": EVIDENCE_CURRENT,
    EVIDENCE_HISTORICAL: EVIDENCE_HISTORICAL,
    "HISTORICAL_UNVERIFIED": EVIDENCE_HISTORICAL,
}
# the backend profile belongs to the algorithm (local search: python/none, GA and PSO: numba/none, memetic IDs: numba/python)
VARY_DIMENSIONS = {
    "algorithm": ("algorithm_id", "configuration_hash", "backend_profile"),
    "dataset": ("dataset_identity",),
}


class ComparisonIdentityError(ValueError):
    """Rows cannot be given a comparison identity, or they belong to different comparison cells."""


@dataclass(frozen=True)
class ComparisonCellKey:
    pooling_group: str
    protocol_version: str
    study_id: str
    dataset_identity: str
    budget_level_index: Optional[int]
    algorithm_id: str
    configuration_hash: str
    backend_policy: str
    backend_profile: str
    seed_protocol_version: str
    base_seed: int
    evidence_class: str
    code_commit: str
    tree_dirty: bool

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def digest(self) -> str:
        """sha256 of the canonical JSON of every key field (stable across runs and platforms)."""
        return hashlib.sha256(_canonical_json(self.as_dict()).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComparisonFamily:
    """The shared identity of a set of rows that may be compared: ``shared`` holds the fields all rows agree on,
    ``varied`` the distinct values of the dimension(s) being compared."""
    pooling_group: str
    size: int
    shared: Mapping[str, Any]
    varied: Mapping[str, tuple]
    contains_dirty: bool = False  # True only when built with ``allow_dirty``: D-05 must refuse such a family


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def normalise_termination_policy(text: str) -> str:
    """``text`` without the segments of ``POLICY_NON_CONFIGURATION_KEYS`` (order of the others kept)."""
    kept = [segment for segment in text.split(";") if segment.split("=", 1)[0] not in POLICY_NON_CONFIGURATION_KEYS]
    return ";".join(kept)


def _require_manifest(manifest: Any) -> RunManifestV1:
    if manifest is None:
        raise ComparisonIdentityError(
            "no run manifest: a row without a RunManifestV1 (code commit, seeds, level list) has no comparison identity"
        )
    if not isinstance(manifest, RunManifestV1):
        raise ComparisonIdentityError(f"manifest must be a RunManifestV1, not {type(manifest).__name__}")
    return manifest


def _require_row(row: Any) -> Mapping[str, Any]:
    if not isinstance(row, Mapping):
        raise ComparisonIdentityError(f"a comparison identity needs a mapping row, not {type(row).__name__}")
    return row


def _termination_policy(row: Mapping[str, Any]) -> str:
    policy = row.get("termination_policy")
    if not isinstance(policy, str) or not policy:
        raise ComparisonIdentityError("row has no termination_policy string (part of the identity, A17 C-16b)")
    return normalise_termination_policy(policy)


def configuration_hash(row: Mapping[str, Any], manifest: RunManifestV1) -> str:
    """sha256 of the sorted JSON of the configured parameters (the manifest's ``algorithm.configuration`` without the
    protocol blocks), the normalised ``termination_policy`` and the row's ``variant``.

    Not read: timing, ``polish_policy`` (its flags and counts are results of the run; ``final`` varies by replicate,
    A17 C-04), ``initialization_policy`` (derived from the polish result), evaluations, costs, tours and seeds."""
    row, manifest = _require_row(row), _require_manifest(manifest)
    parameters = {
        key: value for key, value in manifest.algorithm.configuration.items() if key not in CONFIGURATION_PROTOCOL_BLOCKS
    }
    payload = {"parameters": parameters, "termination_policy": _termination_policy(row), "variant": row.get("variant")}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _evidence_class(row: Mapping[str, Any]) -> str:
    label = row.get("evidence_class", EVIDENCE_CURRENT)
    if label is None:
        label = EVIDENCE_CURRENT
    try:
        return _EVIDENCE_LABELS[label]
    except (KeyError, TypeError):
        raise ComparisonIdentityError(
            f"evidence_class {label!r} cannot be compared; only 'current' and 'historical_unverified' rows carry a key"
        ) from None


def _level_index(row: Mapping[str, Any], manifest: RunManifestV1, native: bool) -> Optional[int]:
    budget = row.get("evaluation_budget")
    if native:
        if budget is not None:
            raise ComparisonIdentityError("a native row carries no evaluation_budget")
        return None
    levels = list(manifest.budget.levels)
    if len(set(levels)) != len(levels):
        raise ComparisonIdentityError(f"the manifest's budget levels must be unique, got {levels}")
    if isinstance(budget, bool) or not isinstance(budget, int):
        raise ComparisonIdentityError(f"a fixed-budget row needs an integer evaluation_budget, got {budget!r}")
    if budget not in levels:
        raise ComparisonIdentityError(f"evaluation_budget {budget} is not one of the manifest levels {levels}")
    return levels.index(budget)


def _backend_profile(manifest: RunManifestV1) -> str:
    profile = manifest.algorithm.backend_profile
    return f"objective={profile['objective']};polish={profile['polish']}"


def _check_dataset(row: Mapping[str, Any], manifest: RunManifestV1, problem: str) -> None:
    """The row must belong to the manifest's dataset. Study smoke rows carry ``dataset_id``; pilot, CLI and
    ``FairRunResult`` rows do not, so their TSPLIB problem name must equal ``tsplib-<normalised name>`` (A17 C-11)."""
    manifest_id = manifest.dataset.dataset_id
    if "dataset_id" in row:
        if row["dataset_id"] != manifest_id:
            raise ComparisonIdentityError(f"row dataset_id {row['dataset_id']!r} differs from the manifest's {manifest_id!r}")
        if not manifest_id.startswith("tsplib-"):
            return  # a dataset that is not named after a TSPLIB instance cannot be checked against the problem name
    expected = f"tsplib-{normalize_problem(problem)}"
    if manifest_id != expected:
        raise ComparisonIdentityError(
            f"row problem {problem!r} (dataset {expected!r}) does not match the manifest dataset {manifest_id!r}; "
            "a row without dataset_id is matched to its manifest by the normalised TSPLIB name"
        )


def comparison_cell_key(row: Mapping[str, Any], manifest: Optional[RunManifestV1], *, allow_dirty: bool = False) -> ComparisonCellKey:
    """The comparison identity of one heuristic row. Call after ``assert_single_pooling_group``.

    Refuses (``ComparisonIdentityError``): no manifest; exact, union-day and joint-day rows; a row that disagrees with its
    manifest in algorithm, protocol version, study, dataset id or budget level; a native row with a budget; an unknown
    evidence class; a manifest of a dirty tree unless ``allow_dirty`` (a dirty run has no code identity; the flag is
    for descriptive smoke views, never for statistics)."""
    manifest = _require_manifest(manifest)
    row = _require_row(row)
    if row.get("record_kind") == "failed_run" or row.get("validation_status") == "failed":
        raise ComparisonIdentityError("a failed run is not an observation: it gets no comparison key (record it, exclude it from inference)")
    try:
        kind = classify_row(row)
    except ValueError as exc:
        raise ComparisonIdentityError(f"row protocol kind cannot be determined: {exc}") from exc
    if not kind.rankable:
        raise ComparisonIdentityError(f"{kind.kind} rows are references or selections and are never ranked, averaged or tested; they get no comparison key")
    version = row.get("protocol_version")
    if version != manifest.protocol_version:
        raise ComparisonIdentityError(f"row protocol_version {version!r} differs from the manifest's {manifest.protocol_version!r}")
    if row.get("algorithm_id") != manifest.algorithm.algorithm_id:
        raise ComparisonIdentityError(f"row algorithm_id {row.get('algorithm_id')!r} differs from the manifest's {manifest.algorithm.algorithm_id!r}")
    if "study_id" in row and row["study_id"] != manifest.study_id:
        raise ComparisonIdentityError(f"row study_id {row['study_id']!r} differs from the manifest's {manifest.study_id!r}")
    problem = row.get("problem")
    if not isinstance(problem, str) or not problem.strip():
        raise ComparisonIdentityError("row has no problem name (the TSPLIB identity of the dataset)")
    _check_dataset(row, manifest, problem)
    native = kind.pooling_group == "native"
    expected_policy = "native_uncapped" if native else "atomic_upper_bound_v1"
    if manifest.budget.policy != expected_policy:
        raise ComparisonIdentityError(
            f"manifest budget.policy {manifest.budget.policy!r} does not fit a {kind.pooling_group} row (expected {expected_policy!r})"
        )
    if manifest.git.dirty and not allow_dirty:
        raise ComparisonIdentityError("the run manifest records a dirty working tree: no code identity (one campaign = one clean commit)")
    return ComparisonCellKey(
        pooling_group=kind.pooling_group,
        protocol_version=version,
        study_id=manifest.study_id,
        dataset_identity=normalize_problem(problem),
        budget_level_index=_level_index(row, manifest, native=native),
        algorithm_id=manifest.algorithm.algorithm_id,
        configuration_hash=configuration_hash(row, manifest),
        backend_policy=manifest.algorithm.backend_policy,
        backend_profile=_backend_profile(manifest),
        seed_protocol_version=SEED_PROTOCOL_VERSION,
        base_seed=manifest.seeds.base_seed,
        evidence_class=_evidence_class(row),
        code_commit=manifest.git.commit,
        tree_dirty=manifest.git.dirty,
    )


def assert_single_comparison_family(
    items: Iterable[tuple], *, vary: Iterable[str] = (), allow_dirty: bool = False
) -> Optional[ComparisonFamily]:
    """Raise unless every ``(row, manifest)`` pair belongs to one comparison family; ``None`` for no pairs.

    The pooling-group guard runs first. ``vary`` names the dimension(s) being compared: ``"algorithm"`` (algorithm ID, backend profile and
    its configuration; each algorithm must still have exactly one configuration and backend profile) and ``"dataset"`` (instance). With no
    ``vary`` the pairs must form one cell, with every key field equal. A cross-instance design (Friedman) varies both."""
    vary = tuple(vary)
    unknown = [name for name in vary if name not in VARY_DIMENSIONS]
    if unknown:
        raise ValueError(f"unknown vary dimension(s) {unknown}; known: {sorted(VARY_DIMENSIONS)}")
    pairs = list(items)
    group = assert_single_pooling_group([row for row, _ in pairs])  # fixed/native/exact mixing is refused first
    if not pairs:
        return None
    keys = [comparison_cell_key(row, manifest, allow_dirty=allow_dirty) for row, manifest in pairs]
    masked = {field for name in vary for field in VARY_DIMENSIONS[name]}
    values = {f.name: {getattr(key, f.name) for key in keys} for f in fields(ComparisonCellKey)}
    differing = sorted(name for name, seen in values.items() if name not in masked and len(seen) > 1)
    if differing:
        raise ComparisonIdentityError(
            f"rows are not one comparison family (vary={list(vary)}): these key fields differ: {differing}"
        )
    if "algorithm" in vary:
        per_algorithm: dict = {}
        for key in keys:
            per_algorithm.setdefault(key.algorithm_id, set()).add((key.configuration_hash, key.backend_profile))
        split = sorted(name for name, variants in per_algorithm.items() if len(variants) > 1)
        if split:
            raise ComparisonIdentityError(
                f"algorithm(s) {split} appear with more than one configuration hash or backend profile"
            )
    return ComparisonFamily(
        pooling_group=group,
        size=len(keys),
        shared={name: next(iter(seen)) for name, seen in values.items() if name not in masked},
        varied={name: tuple(sorted(values[name], key=repr)) for name in sorted(masked)},
        contains_dirty=any(key.tree_dirty for key in keys),
    )
