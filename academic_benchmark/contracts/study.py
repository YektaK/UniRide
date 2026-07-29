from __future__ import annotations

from typing import Literal

from pydantic import Field, PositiveInt, model_validator
from pydantic import field_validator

from academic_benchmark.core.algorithm_errors import CandidateAlgorithmError, PlannedAlgorithmError
from academic_benchmark.core.algorithm_resolution import IdentifierSource, resolve_algorithm_id
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


class StudyManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-study/v1"}}

    schema_version: Literal["uniride-study/v1"]
    study_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1)
    status: Literal["draft", "active", "archived"]
    algorithm_ids: list[str] = Field(min_length=1)
    algorithm_parameters: dict[str, dict[str, JsonValue]]
    dataset_manifest_refs: list[RepositoryRelativePath] = Field(min_length=1)
    primary_protocol: FixedBudgetProtocolV1
    secondary_protocol: NativeProtocolV1 | None = None
    fixed_budget_levels: list[PositiveInt] = Field(min_length=1)
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
        if set(self.algorithm_parameters) != set(self.algorithm_ids):
            raise ValueError("algorithm_parameters keys must exactly match algorithm_ids")
        if len(set(self.fixed_budget_levels)) != len(self.fixed_budget_levels):
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
