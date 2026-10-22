from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, PositiveInt, model_validator
from pydantic import field_validator

from academic_benchmark.core.algorithm_errors import (
    CandidateAlgorithmError,
    ForbiddenAliasError,
    PlannedAlgorithmError,
)
from academic_benchmark.core.algorithm_resolution import (
    FORBIDDEN_ALGORITHM_REPLACEMENTS,
    IdentifierSource,
    resolve_algorithm_id,
)
from uniride_core.algorithms.capabilities import LifecycleStatus, get_algorithm_capability

from .common import JsonValue, RepositoryRelativePath, StrictContract

ProblemFamily = Literal["TSP", "ATSP", "CVRP", "CVRPTW", "UniRide"]


def _validate_manifest_algorithm_ids(algorithm_ids: list[str]) -> list[str]:
    for algorithm_id in algorithm_ids:
        resolution = resolve_algorithm_id(algorithm_id, IdentifierSource.MANIFEST)
        capability = get_algorithm_capability(resolution.canonical_id)
        if capability is not None:
            if capability.lifecycle is LifecycleStatus.CANDIDATE:
                raise CandidateAlgorithmError(capability.canonical_id)
            if capability.lifecycle is LifecycleStatus.PLANNED:
                raise PlannedAlgorithmError(capability.canonical_id)
    return algorithm_ids


class FixedBudgetProtocolV1(StrictContract):
    protocol_id: Literal["fixed_evaluation_budget"]
    protocol_version: str = Field(min_length=1)
    budget_policy: Literal["atomic_upper_bound_v1"]


class NativeProtocolV1(StrictContract):
    protocol_id: Literal["algorithm_native_termination"]
    protocol_version: str = Field(min_length=1)
    termination: dict[str, JsonValue]
    algorithm_ids: list[str] | None = None



    @field_validator("algorithm_ids")
    @classmethod
    def validate_canonical_algorithm_ids(cls, value: list[str] | None):
        return None if value is None else _validate_manifest_algorithm_ids(value)
class OutputPolicyV1(StrictContract):
    repository_outputs: Literal["smoke_only", "none"]
    paper_scale_location: Literal["external"]


class PaperMetadataV1(StrictContract):
    paper_id: str = Field(min_length=1)
    year: PositiveInt
    venue: str = Field(min_length=1)


TWO_OPT_SCAN_RULE = "two_opt_scan_multiples_v1"


def two_opt_scan_size(dimension: int) -> int:
    """Candidates in one full 2-opt scan of an ``n``-node tour: ``n(n-1)/2``."""
    return dimension * (dimension - 1) // 2


def _dimension_of_scan_size(scan_size: int) -> int | None:
    """``n >= 2`` with ``n(n-1)/2 == scan_size``, or ``None`` when there is none."""
    n = int(((8 * scan_size + 1) ** 0.5 + 1) / 2)
    for candidate in (n - 1, n, n + 1):
        if candidate >= 2 and two_opt_scan_size(candidate) == scan_size:
            return candidate
    return None


class ScaledFixedBudgetLevelsV1(StrictContract):
    """Per-dataset fixed budget levels from a declared rule (C-19, owner 2026-10-21).

    ``two_opt_scan_multiples_v1``: level ``i`` of a dataset is ``scan_multipliers[i] x n(n-1)/2``
    objective evaluations, ``n`` the dataset dimension (one full 2-opt scan per unit). The table is
    stated in full so that the study says which budgets run; the contract checks that it is
    internally consistent and the study service recomputes every entry from the dataset manifest.
    Keys are dataset ids.
    """

    rule: Literal["two_opt_scan_multiples_v1"]
    scan_multipliers: list[PositiveInt] = Field(min_length=1)
    levels_by_dataset: dict[str, list[PositiveInt]]

    @model_validator(mode="after")
    def validate_table_follows_the_rule(self) -> "ScaledFixedBudgetLevelsV1":
        multipliers = self.scan_multipliers
        if any(b <= a for a, b in zip(multipliers, multipliers[1:])):
            raise ValueError("scan_multipliers must be strictly increasing (and so unique)")
        if not self.levels_by_dataset:
            raise ValueError("levels_by_dataset must name at least one dataset")
        for dataset_id, levels in self.levels_by_dataset.items():
            if len(levels) != len(multipliers):
                raise ValueError(
                    f"levels_by_dataset[{dataset_id!r}] needs one level per multiplier "
                    f"({len(multipliers)}), found {len(levels)}"
                )
            if any(level % multiplier for level, multiplier in zip(levels, multipliers)) or len(
                {level // multiplier for level, multiplier in zip(levels, multipliers)}
            ) != 1:
                raise ValueError(
                    f"levels_by_dataset[{dataset_id!r}] = {levels} is not multiplier x n(n-1)/2 "
                    f"for one n (multipliers {multipliers})"
                )
            scan_size = levels[0] // multipliers[0]
            if _dimension_of_scan_size(scan_size) is None:
                raise ValueError(
                    f"levels_by_dataset[{dataset_id!r}]: {scan_size} evaluations per scan is not "
                    "n(n-1)/2 for any integer n >= 2"
                )
        return self


# Exactly one budget declaration (C-19), stated in the JSON schema too: a present key must hold a
# value and the other key must be absent or null (the model treats null as absent).
_EXACTLY_ONE_BUDGET_DECLARATION = [
    {
        "required": ["fixed_budget_levels"],
        "properties": {
            "fixed_budget_levels": {"type": "array"},
            "scaled_fixed_budget_levels": {"type": "null"},
        },
    },
    {
        "required": ["scaled_fixed_budget_levels"],
        "properties": {
            "scaled_fixed_budget_levels": {"type": "object"},
            "fixed_budget_levels": {"type": "null"},
        },
    },
]


class StudyManifestV1(StrictContract):
    model_config = StrictContract.model_config | {
        "json_schema_extra": {"$id": "uniride-study/v1", "oneOf": _EXACTLY_ONE_BUDGET_DECLARATION}
    }

    schema_version: Literal["uniride-study/v1"]
    study_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1)
    status: Literal["draft", "active", "archived"]
    algorithm_ids: list[str] = Field(min_length=1)
    algorithm_parameters: dict[str, dict[str, JsonValue]]
    dataset_manifest_refs: list[RepositoryRelativePath] = Field(min_length=1)
    primary_protocol: FixedBudgetProtocolV1
    secondary_protocol: NativeProtocolV1 | None = None
    # exactly one of the two budget declarations (C-19): one list for every dataset, or the
    # per-dataset table of a declared scaling rule
    fixed_budget_levels: Annotated[list[PositiveInt], Field(min_length=1)] | None = None
    scaled_fixed_budget_levels: ScaledFixedBudgetLevelsV1 | None = None
    run_count: PositiveInt
    base_seed: int
    seed_protocol_version: str = Field(min_length=1)
    problem_families: list[ProblemFamily] = Field(min_length=1)
    analysis_plan_id: str = Field(min_length=1)
    output_policy: OutputPolicyV1
    paper_metadata: PaperMetadataV1


    @field_validator("algorithm_ids")
    @classmethod
    def validate_canonical_algorithm_ids(cls, value: list[str]) -> list[str]:
        return _validate_manifest_algorithm_ids(value)
    @model_validator(mode="after")
    def validate_algorithm_parameter_keys(self) -> "StudyManifestV1":
        if len(set(self.algorithm_ids)) != len(self.algorithm_ids):
            raise ValueError("algorithm_ids must be unique")
        # a false historical label used only as a parameter key is refused with its replacement named
        # (as in algorithm_ids), not as a mere key mismatch
        for key in self.algorithm_parameters:
            if key in FORBIDDEN_ALGORITHM_REPLACEMENTS:
                raise ForbiddenAliasError(key, FORBIDDEN_ALGORITHM_REPLACEMENTS[key])
        if set(self.algorithm_parameters) != set(self.algorithm_ids):
            raise ValueError("algorithm_parameters keys must exactly match algorithm_ids")
        if (self.fixed_budget_levels is None) == (self.scaled_fixed_budget_levels is None):
            raise ValueError(
                "give exactly one of fixed_budget_levels and scaled_fixed_budget_levels"
            )
        if self.fixed_budget_levels is not None and len(set(self.fixed_budget_levels)) != len(
            self.fixed_budget_levels
        ):
            raise ValueError("fixed_budget_levels must be unique")
        if self.secondary_protocol is not None:
            secondary_ids = self.secondary_protocol.algorithm_ids
            if secondary_ids is not None:
                if not secondary_ids:
                    raise ValueError("secondary_protocol.algorithm_ids must be non-empty")
                if len(set(secondary_ids)) != len(secondary_ids):
                    raise ValueError("secondary_protocol.algorithm_ids must be unique")
                if not set(secondary_ids).issubset(self.algorithm_ids):
                    raise ValueError(
                        "secondary_protocol.algorithm_ids must be a subset of algorithm_ids"
                    )
        return self
