from __future__ import annotations

from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import JsonValue, RepositoryRelativePath, StrictContract

ProblemFamily = Literal["TSP", "ATSP", "CVRP", "CVRPTW", "UniRide"]


class FixedBudgetProtocolV1(StrictContract):
    protocol_id: Literal["fixed_evaluation_budget"]
    protocol_version: str = Field(min_length=1)
    budget_policy: Literal["atomic_upper_bound_v1"]


class NativeProtocolV1(StrictContract):
    protocol_id: Literal["algorithm_native_termination"]
    protocol_version: str = Field(min_length=1)
    termination: dict[str, JsonValue]


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

    @model_validator(mode="after")
    def validate_algorithm_parameter_keys(self) -> "StudyManifestV1":
        if len(set(self.algorithm_ids)) != len(self.algorithm_ids):
            raise ValueError("algorithm_ids must be unique")
        if set(self.algorithm_parameters) != set(self.algorithm_ids):
            raise ValueError("algorithm_parameters keys must exactly match algorithm_ids")
        if len(set(self.fixed_budget_levels)) != len(self.fixed_budget_levels):
            raise ValueError("fixed_budget_levels must be unique")
        return self
