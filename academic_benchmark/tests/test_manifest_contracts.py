from __future__ import annotations

import pytest
from pydantic import ValidationError

from academic_benchmark.contracts.common import (
    ChecksumV1,
    RepositoryRelativePath,
    StrictContract,
)


class _PathProbe(StrictContract):
    path: RepositoryRelativePath


@pytest.mark.parametrize(
    "value",
    ["academic_benchmark/datasets/ft53.json", "studies/yaem2026/study.json"],
)
def test_repository_relative_path_accepts_normalized_paths(value: str):
    assert _PathProbe(path=value).path == value


@pytest.mark.parametrize(
    "value",
    ["/absolute/file.json", r"C:\\secret\\file.json", "../escape.json", "a/../../escape.json", "", "."],
)
def test_repository_relative_path_rejects_absolute_or_traversal(value: str):
    with pytest.raises(ValidationError):
        _PathProbe(path=value)


def test_strict_contract_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ChecksumV1(algorithm="sha256", value="a" * 64, unexpected=True)


def test_sha256_contract_rejects_non_hex_or_wrong_length():
    with pytest.raises(ValidationError):
        ChecksumV1(algorithm="sha256", value="not-a-digest")
