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
_TEXT_SUFFIXES = {".py", ".json", ".csv", ".md", ".txt", ".toml", ".yaml", ".yml", ".ini", ".env"}


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


def scan_sensitive_file(path: Path) -> list[SensitiveFinding]:
    if path.suffix.lower() not in _TEXT_SUFFIXES:
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
                    if (
                        match
                        and not re.search(r"(?i)(os\.environ|getenv)", line)
                        and not re.fullmatch(
                            r"(?i)(?:example|placeholder|change[-_ ]?me|your[-_ ]?)", match.group(1)
                        )
                    ):
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
    entries = list(withheld)
    for relative in sorted(original_paths, key=lambda item: item.as_posix()):
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
    for entry in manifest.entries:
        relative = PurePosixPath(entry.original_path).relative_to(source_root)
        if entry.classification is EvidenceClass.WITHHELD_SENSITIVE:
            continue
        path = archived_root / Path(*relative.parts)
        if not path.is_file():
            errors.append(f"missing: {relative.as_posix()}")
        elif sha256_file(path) != entry.sha256:
            errors.append(f"checksum mismatch: {relative.as_posix()}")
        elif path.stat().st_size != entry.byte_size:
            errors.append(f"size mismatch: {relative.as_posix()}")
    return errors
