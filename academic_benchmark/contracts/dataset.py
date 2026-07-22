from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import ChecksumV1, RepositoryRelativePath, StrictContract


class DatasetSourceV1(StrictContract):
    authority_url: str = Field(min_length=1)
    retrieved_on: date


class MatrixSemanticsV1(StrictContract):
    directed: bool
    edge_weight_type: str = Field(min_length=1)
    edge_weight_format: str | None = None
    diagonal_semantics: Literal["zero", "sentinel", "problem_defined"]


class BestKnownV1(StrictContract):
    status: Literal["optimal", "best_known", "unknown"]
    value: float | None
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_value_for_known_status(self) -> "BestKnownV1":
        if self.status != "unknown" and self.value is None:
            raise ValueError("optimal and best_known records require value")
        return self


class DatasetManifestV1(StrictContract):
    model_config = StrictContract.model_config | {"json_schema_extra": {"$id": "uniride-dataset/v1"}}

    schema_version: Literal["uniride-dataset/v1"]
    dataset_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    artifact_path: RepositoryRelativePath
    source: DatasetSourceV1
    checksum: ChecksumV1
    problem_type: Literal["TSP", "ATSP", "CVRP", "CVRPTW", "UniRide"]
    dimension: PositiveInt
    matrix_semantics: MatrixSemanticsV1
    best_known: BestKnownV1
