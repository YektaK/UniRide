from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict

from pydantic import Field, NonNegativeFloat, NonNegativeInt

from .common import JsonValue, OutputChecksumV1, StrictContract
from .dataset import DatasetManifestV1


class ExecutionBackendProfileV1(TypedDict):
    objective: Literal["python", "numba"]
    polish: Literal["none", "python", "numba"]


class GitStateV1(StrictContract):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dirty: bool


class EnvironmentV1(StrictContract):
    python: str
    operating_system: str
    cpu: str
    numpy: str
    numba: str
    llvmlite: str
    statistics_library: str


class AlgorithmRunV1(StrictContract):
    algorithm_id: str = Field(min_length=1)
    capabilities: dict[str, JsonValue]
    requested_algorithm_id: str | None = Field(default=None, min_length=1)
    backend_policy: Literal["python_only", "prefer_numba", "require_numba"]
    backend_profile: ExecutionBackendProfileV1
    capability_evidence_ids: list[str] = Field(min_length=1, strict=True)
    configuration: dict[str, JsonValue]
    composition_stages: list[dict[str, JsonValue]]


class SeedScheduleV1(StrictContract):
    base_seed: int
    derived: dict[str, int]


class BudgetRecordV1(StrictContract):
    levels: list[int] = Field(min_length=1)
    policy: Literal["atomic_upper_bound_v1", "native_uncapped"]
    objective_evaluations: NonNegativeInt
    stage_allocation: dict[str, NonNegativeInt]


class TerminationRecordV1(StrictContract):
    reason: str = Field(min_length=1)
    runtime_seconds: NonNegativeFloat


class ValidationRecordV1(StrictContract):
    passed: bool
    checks: list[str]


class RunManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-run/v1"}}

    schema_version: Literal["uniride-run/v1"]
    run_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    study_id: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    git: GitStateV1
    environment: EnvironmentV1
    dataset: DatasetManifestV1
    algorithm: AlgorithmRunV1
    seeds: SeedScheduleV1
    budget: BudgetRecordV1
    termination: TerminationRecordV1
    validation: ValidationRecordV1
    outputs: list[OutputChecksumV1]
