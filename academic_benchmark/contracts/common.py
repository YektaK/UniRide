from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue, WithJsonSchema


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def validate_repository_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or normalized == ".":
        raise ValueError("path must identify a repository-relative file")
    if path.is_absolute() or (path.parts and ":" in path.parts[0]):
        raise ValueError("absolute paths are forbidden")
    if ".." in path.parts:
        raise ValueError("path traversal is forbidden")
    return path.as_posix()


RepositoryRelativePath = Annotated[
    str,
    AfterValidator(validate_repository_relative_path),
    WithJsonSchema({"type": "string", "format": "uniride-repository-relative-path"}),
]
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ChecksumV1(StrictContract):
    algorithm: Literal["sha256"]
    value: Sha256Digest


class OutputChecksumV1(StrictContract):
    path: RepositoryRelativePath
    checksum: ChecksumV1
