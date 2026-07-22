from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
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
) -> ArchiveManifest:
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
    return path


def _git_paths(repo_root: Path, *arguments: str) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return sorted(
        (PurePosixPath(raw.decode("utf-8")) for raw in completed.stdout.split(b"\0") if raw),
        key=lambda item: item.as_posix(),
    )


def _git_directory(repo_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


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
    source_root = _require_repository_relative(source_root)
    return _relative_paths(
        _git_paths(repo_root, "ls-files", "-z", "--", source_root.as_posix()),
        source_root,
    )


def _git_untracked_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    source_root = _require_repository_relative(source_root)
    return _relative_paths(
        _git_paths(
            repo_root,
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            "--",
            source_root.as_posix(),
        ),
        source_root,
    )


def _git_ignored_files(repo_root: Path, source_root: PurePosixPath) -> list[PurePosixPath]:
    source_root = _require_repository_relative(source_root)
    return _relative_paths(
        _git_paths(
            repo_root,
            "ls-files",
            "-z",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            source_root.as_posix(),
        ),
        source_root,
    )


def _is_disposable_cache(path: PurePosixPath) -> bool:
    return (
        "__pycache__" in path.parts
        or ".numba_cache" in path.parts
        or path.suffix.lower() in {".pyc", ".pyo", ".nbc", ".nbi"}
    )


def scan_tracked_tree(
    repo_root: Path,
    source_root: PurePosixPath,
) -> tuple[list[PurePosixPath], list[SensitiveFinding]]:
    source_root = _require_repository_relative(source_root)
    tracked = git_tracked_files(repo_root, source_root)
    source_fs = repo_root / Path(*source_root.parts)
    findings: list[SensitiveFinding] = []
    for relative in tracked:
        for finding in scan_sensitive_file(source_fs / Path(*relative.parts)):
            findings.append(
                SensitiveFinding(
                    path=(source_root / relative).as_posix(),
                    line=finding.line,
                    rule=finding.rule,
                    severity=finding.severity,
                )
            )
    return tracked, findings


def write_manifest(manifest: ArchiveManifest, path: Path) -> None:
    content = json.dumps(
        manifest.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def load_manifest(path: Path) -> ArchiveManifest:
    return ArchiveManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _prune_empty_directories(source_root: Path) -> None:
    if not source_root.exists():
        return
    directories = sorted(
        (path for path in source_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        if not any(directory.iterdir()):
            directory.rmdir()
    if source_root.is_dir() and not any(source_root.iterdir()):
        source_root.rmdir()


def quarantine_tracked_tree(
    *,
    repo_root: Path,
    source_root: PurePosixPath,
    archive_root: PurePosixPath,
    archive_id: str,
) -> ArchiveManifest:
    repo_root = repo_root.resolve()
    source_root = _require_repository_relative(source_root)
    archive_root = _require_repository_relative(archive_root)
    source_fs = repo_root / Path(*source_root.parts)
    destination_root = repo_root / Path(*archive_root.parts)
    tracked, findings = scan_tracked_tree(repo_root, source_root)
    if not tracked:
        raise QuarantineBlocked(f"no tracked files under {source_root}")
    if destination_root.exists():
        raise QuarantineBlocked(f"archive destination already exists: {archive_root}")

    untracked = _git_untracked_files(repo_root, source_root)
    if untracked:
        names = ", ".join(path.as_posix() for path in untracked)
        raise QuarantineBlocked("untracked non-ignored files require review: " + names)
    ignored = _git_ignored_files(repo_root, source_root)
    unsafe_ignored = [path for path in ignored if not _is_disposable_cache(path)]
    if unsafe_ignored:
        names = ", ".join(path.as_posix() for path in unsafe_ignored)
        raise QuarantineBlocked("ignored non-cache files require review: " + names)

    ambiguous = [finding for finding in findings if finding.severity == "ambiguous"]
    if ambiguous:
        summary = ", ".join(
            f"{finding.path}:{finding.line}:{finding.rule}" for finding in ambiguous
        )
        raise QuarantineBlocked("ambiguous high-risk match; no files moved: " + summary)

    confirmed_paths = {
        PurePosixPath(finding.path).relative_to(source_root)
        for finding in findings
        if finding.severity == "confirmed"
    }
    moved: list[PurePosixPath] = []
    withheld: list[ArchiveEntry] = []
    existing_destination_parent = destination_root.parent
    while not existing_destination_parent.exists():
        existing_destination_parent = existing_destination_parent.parent

    with tempfile.TemporaryDirectory(
        prefix="uniride-quarantine-", dir=_git_directory(repo_root)
    ) as backup_name:
        backup_root = Path(backup_name)
        try:
            for relative in confirmed_paths:
                source = source_fs / Path(*relative.parts)
                backup = backup_root / Path(*relative.parts)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)

            destination_root.mkdir(parents=True)
            for relative in tracked:
                source = source_fs / Path(*relative.parts)
                if relative in confirmed_paths:
                    withheld.append(
                        ArchiveEntry(
                            original_path=(source_root / relative).as_posix(),
                            archive_path=None,
                            byte_size=source.stat().st_size,
                            sha256=sha256_file(source),
                            classification=EvidenceClass.WITHHELD_SENSITIVE,
                        )
                    )
                    source.unlink()
                    continue
                destination = destination_root / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
                moved.append(relative)

            manifest = build_manifest(
                archive_id=archive_id,
                source_root=source_root,
                archive_root=archive_root,
                archived_root=destination_root,
                original_paths=moved,
                withheld=withheld,
            )
            write_manifest(manifest, destination_root / "manifest.json")
            integrity_errors = verify_manifest(manifest, destination_root)
            if integrity_errors:
                raise QuarantineBlocked("; ".join(integrity_errors))

            for relative in ignored:
                (source_fs / Path(*relative.parts)).unlink(missing_ok=True)
            _prune_empty_directories(source_fs)
            return manifest
        except Exception:
            for relative in reversed(moved):
                destination = destination_root / Path(*relative.parts)
                source = source_fs / Path(*relative.parts)
                if destination.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    destination.replace(source)
            for relative in confirmed_paths:
                backup = backup_root / Path(*relative.parts)
                source = source_fs / Path(*relative.parts)
                if backup.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, source)
            shutil.rmtree(destination_root, ignore_errors=True)
            cleanup_parent = destination_root.parent
            while cleanup_parent != existing_destination_parent and cleanup_parent.exists():
                if any(cleanup_parent.iterdir()):
                    break
                cleanup_parent.rmdir()
                cleanup_parent = cleanup_parent.parent
            raise


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
            manifest = quarantine_tracked_tree(
                repo_root=args.repo_root,
                source_root=args.source,
                archive_root=args.archive,
                archive_id=args.archive_id,
            )
            counts = Counter(entry.classification.value for entry in manifest.entries)
            print(f"archived={len(manifest.entries)} classifications={dict(sorted(counts.items()))}")
            return 0

        manifest_path = args.repo_root.resolve() / Path(*args.manifest.parts)
        manifest = load_manifest(manifest_path)
        archived_root = args.repo_root.resolve() / Path(*PurePosixPath(manifest.archive_root).parts)
        errors = verify_manifest(manifest, archived_root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"verified {len(manifest.entries)} entries")
        return 0
    except (OSError, subprocess.CalledProcessError, QuarantineBlocked, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
