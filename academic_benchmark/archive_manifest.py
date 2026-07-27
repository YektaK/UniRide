from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import stat
import sys
import tempfile
import warnings
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Literal

from pydantic import Field, ValidationError, model_validator

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


EvidenceClassifier = Callable[[PurePosixPath], EvidenceClass]


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


def classify_bildiri_evidence(path: PurePosixPath) -> EvidenceClass:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    if "results" in parts and "student_matrix" in name:
        return EvidenceClass.INVALID
    if "results" in parts or name == "tuned_parameters_db.json":
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


def _is_repository_relative_path(value: PurePosixPath | str) -> bool:
    raw = str(value)
    path = PurePosixPath(raw)
    return bool(
        raw
        and "\\" not in raw
        and ":" not in raw
        and not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() not in {"", "."}
    )

def build_manifest(
    *,
    archive_id: str,
    source_root: PurePosixPath,
    archive_root: PurePosixPath,
    archived_root: Path,
    original_paths: Iterable[PurePosixPath],
    withheld: Iterable[ArchiveEntry],
    classifier: EvidenceClassifier | None = None,
) -> ArchiveManifest:
    classify = classifier if classifier is not None else classify_yaem_evidence
    paths = sorted(original_paths, key=lambda item: item.as_posix())
    for value in (source_root, archive_root, *paths):
        if not _is_repository_relative_path(value):
            raise ValueError("paths must be repository-relative")
    entries = list(withheld)
    for relative in paths:
        archived = archived_root / Path(*relative.parts)
        entries.append(
            ArchiveEntry(
                original_path=(source_root / relative).as_posix(),
                archive_path=(archive_root / relative).as_posix(),
                byte_size=archived.stat().st_size,
                sha256=sha256_file(archived),
                classification=classify(relative),
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
        if not _is_repository_relative_path(entry.original_path):
            errors.append(f"unsafe original path: {entry.original_path}")
            continue
        if not _is_repository_relative_path(entry.archive_path or ""):
            errors.append(f"unsafe archive path: {entry.archive_path or ''}")
            continue
        original = PurePosixPath(entry.original_path)
        archive_path = PurePosixPath(entry.archive_path)
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

class QuarantineBlocked(RuntimeError):
    """Raised when legacy evidence cannot be quarantined safely."""


def _require_repository_relative(value: PurePosixPath | str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not _is_repository_relative_path(path):
        raise QuarantineBlocked("expected a repository-relative path without traversal")
    if ".git" in {part.lower() for part in path.parts}:
        raise QuarantineBlocked(".git containment is forbidden")
    return path


def _git_paths(repo_root: Path, *arguments: str) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", *arguments], cwd=repo_root, check=True, capture_output=True
    )
    return sorted(
        (PurePosixPath(raw.decode("utf-8")) for raw in completed.stdout.split(b"\0") if raw),
        key=lambda item: item.as_posix(),
    )


def _git_directory(repo_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=repo_root, check=True, capture_output=True, text=True, encoding="utf-8", errors="strict",
    )
    return Path(completed.stdout.strip()).resolve()


def _canonical_repo_root(repo_root: Path) -> Path:
    candidate = repo_root.resolve()
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=candidate,
        check=True, capture_output=True, text=True, encoding="utf-8", errors="strict",
    )
    top_level = Path(completed.stdout.strip()).resolve()
    if candidate != top_level:
        raise QuarantineBlocked("repo_root must resolve exactly to the git toplevel")
    return top_level


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _checked_path(repo_root: Path, intended_root: Path, path: Path) -> Path:
    root = repo_root.resolve()
    if not _is_relative_to(path, root) or not _is_relative_to(path, intended_root):
        raise QuarantineBlocked("path escapes its intended repository root")
    current = root
    for component in path.relative_to(root).parts:
        current = current / component
        if _is_reparse_point(current):
            raise QuarantineBlocked("reparse-point components are forbidden")
    resolved = path.resolve(strict=False)
    intended_resolved = intended_root.resolve(strict=False)
    if not _is_relative_to(resolved, root) or not _is_relative_to(resolved, intended_resolved):
        raise QuarantineBlocked("resolved path escapes its intended repository root")
    return path


def _paths_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _transaction_roots(
    repo_root: Path, source_root: PurePosixPath, archive_root: PurePosixPath
) -> tuple[Path, PurePosixPath, PurePosixPath, Path, Path]:
    canonical = _canonical_repo_root(repo_root)
    source_root = _require_repository_relative(source_root)
    archive_root = _require_repository_relative(archive_root)
    if _paths_overlap(source_root, archive_root):
        raise QuarantineBlocked("source and archive roots overlap")
    source_fs = canonical / Path(*source_root.parts)
    destination_root = canonical / Path(*archive_root.parts)
    _checked_path(canonical, source_fs, source_fs)
    _checked_path(canonical, destination_root, destination_root)
    return canonical, source_root, archive_root, source_fs, destination_root


def _relative_paths(paths: Iterable[PurePosixPath], source_root: PurePosixPath) -> list[PurePosixPath]:
    relative_paths: list[PurePosixPath] = []
    for path in paths:
        try:
            relative = path.relative_to(source_root)
        except ValueError as exc:
            raise QuarantineBlocked(f"Git returned a path outside {source_root}") from exc
        if not _is_repository_relative_path(source_root / relative):
            raise QuarantineBlocked("Git returned an unsafe repository path")
        relative_paths.append(relative)
    return relative_paths


def git_tracked_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    canonical = _canonical_repo_root(repo_root)
    source_root = _require_repository_relative(source_root)
    return _relative_paths(_git_paths(canonical, "ls-files", "-z", "--", source_root.as_posix()), source_root)


def _git_untracked_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    return _relative_paths(_git_paths(repo_root, "ls-files", "-z", "--others", "--exclude-standard", "--", source_root.as_posix()), source_root)


def _git_ignored_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    return _relative_paths(_git_paths(repo_root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", source_root.as_posix()), source_root)


def _is_disposable_cache(path: PurePosixPath) -> bool:
    return path.suffix.lower() in {".pyc", ".pyo", ".nbc", ".nbi", ".db"}


def _source_path(repo_root: Path, source_fs: Path, relative: PurePosixPath) -> Path:
    return _checked_path(repo_root, source_fs, source_fs / Path(*relative.parts))


def _validate_include_paths(
    repo_root: Path, source_fs: Path, include_paths: list[PurePosixPath] | None
) -> list[PurePosixPath] | None:
    if include_paths is None:
        return None
    resolved_includes: list[PurePosixPath] = []
    for raw_include in include_paths:
        include_path = PurePosixPath(raw_include)
        if not _is_repository_relative_path(include_path):
            raise QuarantineBlocked("include path must be repository-relative")
        source = _source_path(repo_root, source_fs, include_path)
        if not (source.is_file() or source.is_dir()):
            raise QuarantineBlocked(f"include path not found: {include_path.as_posix()}")
        resolved_includes.append(
            PurePosixPath(source.resolve(strict=False).relative_to(source_fs.resolve(strict=False)).as_posix())
        )
    return sorted(set(resolved_includes), key=lambda path: path.as_posix())


def _expand_tracked_includes(
    tracked: list[PurePosixPath], include_paths: list[PurePosixPath]
) -> list[PurePosixPath]:
    return sorted(
        {
            tracked_file
            for include_path in include_paths
            for tracked_file in tracked
            if tracked_file.is_relative_to(include_path)
        },
        key=lambda path: path.as_posix(),
    )


def scan_tracked_tree(
    repo_root: Path,
    source_root: PurePosixPath,
    *,
    tracked: list[PurePosixPath] | None = None,
) -> tuple[list[PurePosixPath], list[SensitiveFinding]]:
    canonical = _canonical_repo_root(repo_root)
    source_root = _require_repository_relative(source_root)
    source_fs = canonical / Path(*source_root.parts)
    _checked_path(canonical, source_fs, source_fs)
    tracked_files = git_tracked_files(canonical, source_root) if tracked is None else tracked
    findings: list[SensitiveFinding] = []
    for relative in tracked_files:
        source = _source_path(canonical, source_fs, relative)
        for finding in scan_sensitive_file(source):
            findings.append(SensitiveFinding((source_root / relative).as_posix(), finding.line, finding.rule, finding.severity))
    return tracked_files, findings


def write_manifest(manifest: ArchiveManifest, path: Path) -> None:
    content = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def load_manifest(path: Path) -> ArchiveManifest:
    return ArchiveManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _prune_empty_directories(source_root: Path) -> None:
    if not source_root.exists():
        return
    for directory in sorted(_safe_directories(source_root.parents[2], source_root), key=lambda item: len(item.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if source_root.is_dir() and not any(source_root.iterdir()):
        source_root.rmdir()


def _retention_warning(message: str) -> None:
    try:
        warnings.warn(message, RuntimeWarning)
    except BaseException:
        pass


def _safe_directories(repo_root: Path, source_root: Path) -> list[Path]:
    directories = [source_root]
    pending = [source_root]
    while pending:
        directory = pending.pop()
        _checked_path(repo_root, source_root, directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                child = Path(entry.path)
                _checked_path(repo_root, source_root, child)
                if entry.is_dir(follow_symlinks=False):
                    directories.append(child)
                    pending.append(child)
    return directories

def _cleanup_empty_parents(path: Path, stop_at: Path) -> None:
    current = path.parent
    while current != stop_at and current.exists():
        if any(current.iterdir()):
            return
        current.rmdir()
        current = current.parent


def _rollback(
    *, repo_root: Path, source_fs: Path, destination_root: Path, backup_root: Path,
    moved: list[PurePosixPath], withheld: list[PurePosixPath], staged_caches: list[PurePosixPath],
    expected: dict[PurePosixPath, str], existing_destination_parent: Path, source_directories: list[PurePosixPath],
) -> list[str]:
    errors: list[str] = []

    def attempt(label: str, operation) -> None:
        try:
            operation()
        except BaseException as exc:
            errors.append(f"{label}: {type(exc).__name__}")

    for relative in reversed(moved):
        def restore_moved(relative: PurePosixPath = relative) -> None:
            source = _source_path(repo_root, source_fs, relative)
            destination = _checked_path(repo_root, destination_root, destination_root / Path(*relative.parts))
            if destination.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                destination.replace(source)
        attempt("restore moved", restore_moved)
    for relative in withheld:
        def restore_withheld(relative: PurePosixPath = relative) -> None:
            source = _source_path(repo_root, source_fs, relative)
            backup = backup_root / "sensitive" / Path(*relative.parts)
            if backup.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                backup.replace(source)
        attempt("restore withheld", restore_withheld)
    for relative in staged_caches:
        def restore_cache(relative: PurePosixPath = relative) -> None:
            source = _source_path(repo_root, source_fs, relative)
            backup = backup_root / "cache" / Path(*relative.parts)
            if backup.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                backup.replace(source)
        attempt("restore cache", restore_cache)
    for directory in source_directories:
        attempt("restore directory", lambda directory=directory: (source_fs / Path(*directory.parts)).mkdir(parents=True, exist_ok=True))
    for relative, digest in expected.items():
        def verify_restore(relative: PurePosixPath = relative, digest: str = digest) -> None:
            source = _source_path(repo_root, source_fs, relative)
            if not source.is_file() or sha256_file(source) != digest:
                raise OSError("restoration mismatch")
        attempt("verify restoration", verify_restore)
    if not errors:
        attempt("remove destination", lambda: shutil.rmtree(destination_root) if destination_root.exists() else None)
        attempt("remove empty parents", lambda: _cleanup_empty_parents(destination_root, existing_destination_parent))
    if destination_root.exists() and not errors:
        errors.append("destination cleanup incomplete")
    return errors


def quarantine_tracked_tree(
    *,
    repo_root: Path,
    source_root: PurePosixPath,
    archive_root: PurePosixPath,
    archive_id: str,
    classifier: EvidenceClassifier | None = None,
    include_paths: list[PurePosixPath] | None = None,
) -> ArchiveManifest:
    repo_root, source_root, archive_root, source_fs, destination_root = _transaction_roots(repo_root, source_root, archive_root)
    validated_includes = _validate_include_paths(repo_root, source_fs, include_paths)
    tracked = git_tracked_files(repo_root, source_root)
    if not tracked:
        raise QuarantineBlocked(f"no tracked files under {source_root}")
    if validated_includes is not None:
        tracked = _expand_tracked_includes(tracked, validated_includes)
    tracked, findings = scan_tracked_tree(repo_root, source_root, tracked=tracked)
    if destination_root.exists():
        raise QuarantineBlocked(f"archive destination already exists: {archive_root}")
    untracked = _git_untracked_files(repo_root, source_root)
    ignored = _git_ignored_files(repo_root, source_root)
    for relative in [*tracked, *untracked, *ignored]:
        _source_path(repo_root, source_fs, relative)
    if untracked:
        raise QuarantineBlocked("untracked non-ignored files require review: " + ", ".join(item.as_posix() for item in untracked))
    unsafe_ignored = [item for item in ignored if not _is_disposable_cache(item)]
    if unsafe_ignored:
        raise QuarantineBlocked("ignored non-cache files require review: " + ", ".join(item.as_posix() for item in unsafe_ignored))
    ambiguous = [item for item in findings if item.severity == "ambiguous"]
    if ambiguous:
        raise QuarantineBlocked("ambiguous high-risk match; no files moved: " + ", ".join(f"{item.path}:{item.line}:{item.rule}" for item in ambiguous))
    confirmed_paths = sorted({PurePosixPath(item.path).relative_to(source_root) for item in findings if item.severity == "confirmed"}, key=lambda item: item.as_posix())
    all_mutating = [*tracked, *ignored]
    expected = {relative: sha256_file(_source_path(repo_root, source_fs, relative)) for relative in all_mutating}
    source_directories = sorted((PurePosixPath(path.relative_to(source_fs).as_posix()) for path in _safe_directories(repo_root, source_fs) if path != source_fs), key=lambda item: (len(item.parts), item.as_posix()))
    existing_destination_parent = destination_root.parent
    while not existing_destination_parent.exists():
        existing_destination_parent = existing_destination_parent.parent
    backup_root = Path(tempfile.mkdtemp(prefix="uniride-quarantine-", dir=_git_directory(repo_root)))
    moved: list[PurePosixPath] = []
    withheld: list[PurePosixPath] = []
    staged_caches: list[PurePosixPath] = []
    try:
        for relative in all_mutating:
            _source_path(repo_root, source_fs, relative)
        _checked_path(repo_root, destination_root, destination_root)
        for relative in confirmed_paths:
            source = _source_path(repo_root, source_fs, relative)
            backup = backup_root / "sensitive" / Path(*relative.parts)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
        destination_root.mkdir(parents=True)
        withheld_entries: list[ArchiveEntry] = []
        for relative in tracked:
            source = _source_path(repo_root, source_fs, relative)
            if relative in confirmed_paths:
                withheld_entries.append(ArchiveEntry(original_path=(source_root / relative).as_posix(), archive_path=None, byte_size=source.stat().st_size, sha256=sha256_file(source), classification=EvidenceClass.WITHHELD_SENSITIVE))
                source.unlink()
                withheld.append(relative)
                continue
            destination = _checked_path(repo_root, destination_root, destination_root / Path(*relative.parts))
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
            moved.append(relative)
        for relative in moved:
            _checked_path(repo_root, destination_root, destination_root / Path(*relative.parts))
        manifest = build_manifest(
            archive_id=archive_id,
            source_root=source_root,
            archive_root=archive_root,
            archived_root=destination_root,
            original_paths=moved,
            withheld=withheld_entries,
            classifier=classifier,
        )
        write_manifest(manifest, _checked_path(repo_root, destination_root, destination_root / "manifest.json"))
        errors = verify_manifest(manifest, destination_root)
        if errors:
            raise QuarantineBlocked("; ".join(errors))
        for relative in ignored:
            source = _source_path(repo_root, source_fs, relative)
            backup = backup_root / "cache" / Path(*relative.parts)
            backup.parent.mkdir(parents=True, exist_ok=True)
            source.replace(backup)
            staged_caches.append(relative)
        _prune_empty_directories(source_fs)
    except BaseException as original:
        recovery_errors = _rollback(repo_root=repo_root, source_fs=source_fs, destination_root=destination_root, backup_root=backup_root, moved=moved, withheld=withheld, staged_caches=staged_caches, expected=expected, existing_destination_parent=existing_destination_parent, source_directories=source_directories)
        if recovery_errors:
            raise QuarantineBlocked(f"recovery incomplete; backup retained at {backup_root}: {'; '.join(recovery_errors)}") from original
        try:
            shutil.rmtree(backup_root)
        except OSError:
            _retention_warning("backup retained after rollback cleanup failure")
        raise
    try:
        shutil.rmtree(backup_root)
    except OSError:
        _retention_warning("backup retained after commit cleanup failure")
    return manifest


def _safe_verify_manifest(repo_root: Path, manifest_path: Path) -> tuple[ArchiveManifest, Path, list[str]]:
    canonical = _canonical_repo_root(repo_root)
    _checked_path(canonical, canonical, manifest_path)
    manifest = load_manifest(manifest_path)
    archive_root = _require_repository_relative(PurePosixPath(manifest.archive_root))
    archived_root = canonical / Path(*archive_root.parts)
    _checked_path(canonical, archived_root, archived_root)
    for entry in manifest.entries:
        if entry.archive_path:
            try:
                relative = PurePosixPath(entry.archive_path).relative_to(archive_root)
            except ValueError:
                continue
            _checked_path(canonical, archived_root, archived_root / Path(*relative.parts))
    return manifest, archived_root, verify_manifest(manifest, archived_root)

def _as_repo_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or normalized.startswith("/") or ".." in path.parts:
        raise argparse.ArgumentTypeError("expected a repository-relative path without traversal")
    if ":" in path.parts[0]:
        raise argparse.ArgumentTypeError("absolute Windows paths are forbidden")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan, quarantine, or verify legacy academic evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--repo-root", type=Path, required=True)
    scan_parser.add_argument("--source", type=_as_repo_path, required=True)

    quarantine_parser = subparsers.add_parser("quarantine")
    quarantine_parser.add_argument("--repo-root", type=Path, required=True)
    quarantine_parser.add_argument("--source", type=_as_repo_path, required=True)
    quarantine_parser.add_argument("--archive", type=_as_repo_path, required=True)
    quarantine_parser.add_argument("--archive-id", required=True)
    quarantine_parser.add_argument("--profile", choices=["yaem", "bildiri"], default="yaem")
    quarantine_parser.add_argument("--include", action="append", type=_as_repo_path, dest="include_paths")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=_as_repo_path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            repo_root = args.repo_root.resolve()
            tracked, findings = scan_tracked_tree(repo_root, args.source)
            untracked = _git_untracked_files(repo_root, args.source)
            ignored = _git_ignored_files(repo_root, args.source)
            unsafe_ignored = [path for path in ignored if not _is_disposable_cache(path)]
            for finding in findings:
                print(f"{finding.path}:{finding.line}:{finding.rule}:{finding.severity}")
            print(
                f"tracked={len(tracked)} "
                f"confirmed={sum(item.severity == 'confirmed' for item in findings)} "
                f"ambiguous={sum(item.severity == 'ambiguous' for item in findings)} "
                f"untracked={len(untracked)} unsafe_ignored={len(unsafe_ignored)}"
            )
            return 2 if any(item.severity == "ambiguous" for item in findings) or untracked or unsafe_ignored else 0

        if args.command == "quarantine":
            classifier = classify_bildiri_evidence if args.profile == "bildiri" else classify_yaem_evidence
            manifest = quarantine_tracked_tree(
                repo_root=args.repo_root,
                source_root=args.source,
                archive_root=args.archive,
                archive_id=args.archive_id,
                classifier=classifier,
                include_paths=args.include_paths,
            )
            counts = Counter(entry.classification.value for entry in manifest.entries)
            print(f"archived={len(manifest.entries)} classifications={dict(sorted(counts.items()))}")
            return 0

        manifest_path = args.repo_root.resolve() / Path(*args.manifest.parts)
        manifest, archived_root, errors = _safe_verify_manifest(args.repo_root, manifest_path)
        if errors:
            for error in errors:
                print("manifest mapping error" if "path outside" in error else error, file=sys.stderr)
            return 1
        print(f"verified {len(manifest.entries)} entries")
        return 0
    except ValidationError as exc:
        locations = sorted('.'.join(str(part) for part in item['loc']) for item in exc.errors(include_input=False))
        print('manifest validation failed: ' + (', '.join(locations) or 'invalid manifest'), file=sys.stderr)
        return 2
    except (OSError, subprocess.CalledProcessError, QuarantineBlocked, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
