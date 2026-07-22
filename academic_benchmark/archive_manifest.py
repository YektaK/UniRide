from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Iterable, Literal

from pydantic import Field, model_validator

from academic_benchmark.contracts.common import RepositoryRelativePath, Sha256Digest, StrictContract


class EvidenceClass(StrEnum):
    INVALID = "INVALID"
    HISTORICAL_UNVERIFIED = "HISTORICAL_UNVERIFIED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    WITHHELD_SENSITIVE = "WITHHELD_SENSITIVE"


class ArchiveEntry(StrictContract):
    original_path: RepositoryRelativePath
    archive_path: RepositoryRelativePath | None
    byte_size: int = Field(ge=0)
    sha256: Sha256Digest
    classification: EvidenceClass

    @model_validator(mode="after")
    def validate_withholding(self) -> "ArchiveEntry":
        withheld = self.classification is EvidenceClass.WITHHELD_SENSITIVE
        if withheld != (self.archive_path is None):
            raise ValueError("only WITHHELD_SENSITIVE entries omit archive_path")
        return self


class ArchiveManifest(StrictContract):
    schema_version: Literal["uniride-archive/v1"]
    archive_id: str
    source_root: RepositoryRelativePath
    archive_root: RepositoryRelativePath
    entries: list[ArchiveEntry]


@dataclass(frozen=True)
class SensitiveFinding:
    path: str
    line: int
    rule: str
    severity: Literal["confirmed", "ambiguous"]


_CONFIRMED = (
    ("private_key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,255}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
)
_AMBIGUOUS = (
    (
        "credential_assignment",
        re.compile(
            r"(?i)(?:api[_-]?key|secret|token|password)[\"']?\s*[:=]+\s*[\"']?([^\s\"']{16,})"
        ),
    ),
)
_TEXT_SUFFIXES = {".py", ".js", ".ts", ".json", ".csv", ".md", ".txt", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".sh", ".env"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_yaem_evidence(path: PurePosixPath) -> EvidenceClass:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    in_results = "results" in parts
    in_reports = in_results and "reports" in parts
    if in_reports or (in_results and "student_matrix" in name):
        return EvidenceClass.INVALID
    if in_results:
        return EvidenceClass.HISTORICAL_UNVERIFIED
    return EvidenceClass.REFERENCE_ONLY


def _is_text_file(path: Path) -> bool:
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.") or path.suffix.lower() in _TEXT_SUFFIXES


def _is_placeholder_value(value: str) -> bool:
    return bool(re.fullmatch(
        r"(?i)(?:placeholder|example|change[-_ ]?me|your[-_ ]?(?:api[_-]?key|token|secret)|replace[-_ ]?me)[-_a-z0-9]*",
        value,
    ))


def _is_value_expression(value: str) -> bool:
    return bool(re.fullmatch(r"(?i)(?:os\.environ(?:\[[^\]]+\])?|(?:os\.)?getenv\([^)]*\))", value))


def scan_sensitive_file(path: Path) -> list[SensitiveFinding]:
    if not _is_text_file(path):
        return []
    findings: list[SensitiveFinding] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            confirmed_on_line = False
            for rule, pattern in _CONFIRMED:
                if pattern.search(line):
                    findings.append(SensitiveFinding(path.as_posix(), line_number, rule, "confirmed"))
                    confirmed_on_line = True
            if not confirmed_on_line:
                for rule, pattern in _AMBIGUOUS:
                    match = pattern.search(line)
                    if match:
                        value = match.group(1)
                        if not _is_value_expression(value) and not _is_placeholder_value(value):
                            findings.append(SensitiveFinding(path.as_posix(), line_number, rule, "ambiguous"))
    return findings


def build_manifest(
    *,
    archive_id: str,
    source_root: PurePosixPath,
    archive_root: PurePosixPath,
    archived_root: Path,
    original_paths: Iterable[PurePosixPath],
    withheld: Iterable[ArchiveEntry],
) -> ArchiveManifest:
    paths = sorted(original_paths, key=lambda item: item.as_posix())
    for relative in paths:
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in {"", "."}:
            raise ValueError("original paths must be repository-relative")
    entries = list(withheld)
    for relative in paths:
        archived = archived_root / Path(*relative.parts)
        entries.append(
            ArchiveEntry(
                original_path=(source_root / relative).as_posix(),
                archive_path=(archive_root / relative).as_posix(),
                byte_size=archived.stat().st_size,
                sha256=sha256_file(archived),
                classification=classify_yaem_evidence(relative),
            )
        )
    entries.sort(key=lambda entry: entry.original_path)
    return ArchiveManifest(
        schema_version="uniride-archive/v1",
        archive_id=archive_id,
        source_root=source_root.as_posix(),
        archive_root=archive_root.as_posix(),
        entries=entries,
    )

def verify_manifest(manifest: ArchiveManifest, archived_root: Path) -> list[str]:
    errors: list[str] = []
    source_root = PurePosixPath(manifest.source_root)
    archive_root = PurePosixPath(manifest.archive_root)
    for entry in manifest.entries:
        if entry.classification is EvidenceClass.WITHHELD_SENSITIVE:
            continue
        original = PurePosixPath(entry.original_path)
        archive_path = PurePosixPath(entry.archive_path or "")
        try:
            relative = original.relative_to(source_root)
        except ValueError:
            errors.append(f"original path outside source root: {original.as_posix()}")
            continue
        try:
            archived_relative = archive_path.relative_to(archive_root)
        except ValueError:
            errors.append(f"archive path outside archive root: {archive_path.as_posix()}")
            continue
        path = archived_root / Path(*archived_relative.parts)
        if not path.is_file():
            errors.append(f"missing: {relative.as_posix()}")
        elif path.stat().st_size != entry.byte_size:
            errors.append(f"size mismatch: {relative.as_posix()}")
        elif sha256_file(path) != entry.sha256:
            errors.append(f"checksum mismatch: {relative.as_posix()}")
    return errors
