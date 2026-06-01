"""CVRPLIB/Solomon facade over the unified academic SQLite store.

This module intentionally does not own a separate schema.  It provides
CVRP/CVRPTW-friendly names while delegating storage and loading to
``academic_benchmark.tsplib_manager``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from academic_benchmark.tsplib_manager import (
    DB_PATH,
    get_all_problems,
    load_routing_problem,
    problem_row_to_instance,
    store_academic_text,
)

CVRPLIB_EXTENSIONS = {".vrp"}
SOLOMON_EXTENSIONS = {".solomon", ".txt", ".vrptw"}


def import_cvrplib_text(
    text: str,
    *,
    name: str = "cvrplib",
    db_path: str = DB_PATH,
    source_file: Optional[str] = None,
):
    """Parse and store CVRPLIB text as a core ``RoutingProblem``."""
    return store_academic_text(text, "cvrplib", name=name, db_path=db_path, source_file=source_file)


def import_solomon_text(
    text: str,
    *,
    name: str = "solomon",
    db_path: str = DB_PATH,
    source_file: Optional[str] = None,
):
    """Parse and store Solomon CVRPTW text as a core ``RoutingProblem``."""
    return store_academic_text(text, "solomon", name=name, db_path=db_path, source_file=source_file)


def import_cvrplib_file(path: str | Path, *, db_path: str = DB_PATH):
    """Read and store a CVRPLIB file using the unified academic DB."""
    file_path = Path(path)
    return import_cvrplib_text(
        file_path.read_text(encoding="utf-8"),
        name=file_path.stem,
        db_path=db_path,
        source_file=str(file_path),
    )


def import_solomon_file(path: str | Path, *, db_path: str = DB_PATH):
    """Read and store a Solomon CVRPTW file using the unified academic DB."""
    file_path = Path(path)
    return import_solomon_text(
        file_path.read_text(encoding="utf-8"),
        name=file_path.stem,
        db_path=db_path,
        source_file=str(file_path),
    )


def import_cvrp_paths(paths: Iterable[str | Path], *, db_path: str = DB_PATH) -> Dict[str, List[str]]:
    """Import supported CVRPLIB/Solomon files from files or directories."""
    imported: List[str] = []
    skipped: List[str] = []
    for file_path in _iter_candidate_files(paths):
        kind = _candidate_kind(file_path)
        try:
            if kind == "cvrplib":
                imported.append(import_cvrplib_file(file_path, db_path=db_path).name)
            elif kind == "solomon":
                imported.append(import_solomon_file(file_path, db_path=db_path).name)
            else:
                skipped.append(file_path.name)
        except Exception:
            skipped.append(file_path.name)
    return {"imported": sorted(imported), "skipped": sorted(skipped)}


def scan_cvrp_paths(paths: Iterable[str | Path]) -> Dict[str, List[object]]:
    """Return a non-mutating import-readiness report for files/directories."""
    supported: List[Dict[str, str]] = []
    skipped: List[str] = []
    missing: List[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            missing.append(str(path))
            continue
        for file_path in _iter_candidate_files([path]):
            kind = _candidate_kind(file_path)
            if kind:
                supported.append({"path": str(file_path), "kind": kind})
            else:
                skipped.append(str(file_path))
    return {
        "supported": sorted(supported, key=lambda item: item["path"]),
        "skipped": sorted(skipped),
        "missing": sorted(missing),
    }


def load_cvrp_problem(name: str, *, db_path: str = DB_PATH):
    """Load a CVRP/CVRPTW academic problem as a core ``RoutingProblem``."""
    problem = load_routing_problem(name, db_path=db_path)
    if problem is None:
        return None
    if problem.problem_type not in {"cvrp", "cvrptw"}:
        raise ValueError(f"Problem {name!r} is {problem.problem_type!r}, not CVRP/CVRPTW")
    return problem


def get_cvrp_problems(*, db_path: str = DB_PATH, max_dim: int = 10_000, as_legacy: bool = False):
    """List stored CVRP/CVRPTW problems from the unified academic DB."""
    rows = [
        row
        for row in get_all_problems(db_path=db_path, max_dim=max_dim, exclude_explicit=False)
        if str(row.get("problem_type", "")).upper() in {"CVRP", "CVRPTW"}
    ]
    if as_legacy:
        return [problem_row_to_instance(row) for row in rows]
    return rows


def get_cvrp_problem_as_instance(name: str, *, db_path: str = DB_PATH):
    """Load a CVRP/CVRPTW problem through the legacy benchmark instance shape."""
    rows = [row for row in get_cvrp_problems(db_path=db_path, as_legacy=False) if row["name"] == name]
    if not rows:
        return None
    return problem_row_to_instance(rows[0])


def summarize_cvrp_store(*, db_path: str = DB_PATH) -> Dict[str, object]:
    """Return simple CVRP/CVRPTW counts from the unified academic DB."""
    rows = get_cvrp_problems(db_path=db_path)
    by_type: Dict[str, int] = {}
    for row in rows:
        problem_type = str(row.get("problem_type", "")).upper()
        by_type[problem_type] = by_type.get(problem_type, 0) + 1
    return {"total": len(rows), "by_type": dict(sorted(by_type.items()))}


def _iter_candidate_files(paths: Iterable[str | Path]) -> List[Path]:
    files: List[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        elif path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: str(item))


def _candidate_kind(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    if suffix in CVRPLIB_EXTENSIONS:
        return "cvrplib"
    if suffix in SOLOMON_EXTENSIONS:
        return "solomon"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """CLI facade for importing/listing CVRP and CVRPTW academic problems."""
    parser = argparse.ArgumentParser(description="CVRPLIB/Solomon facade over unified academic SQLite storage")
    parser.add_argument("--db-path", default=DB_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import .vrp/.txt/.vrptw/.solomon files from files or directories")
    import_parser.add_argument("paths", nargs="+")

    scan_parser = subparsers.add_parser("scan", help="Scan paths and report importable CVRPLIB/Solomon files without writing DB")
    scan_parser.add_argument("paths", nargs="+")

    subparsers.add_parser("list", help="List stored CVRP/CVRPTW problem names")
    subparsers.add_parser("status", help="Print CVRP/CVRPTW store counts")

    args = parser.parse_args(argv)
    if args.command == "import":
        result = import_cvrp_paths(args.paths, db_path=args.db_path)
        print(f"imported={result['imported']}")
        print(f"skipped={result['skipped']}")
        return 0
    if args.command == "scan":
        result = scan_cvrp_paths(args.paths)
        print(f"supported={result['supported']}")
        print(f"skipped={result['skipped']}")
        print(f"missing={result['missing']}")
        return 0
    if args.command == "list":
        for row in get_cvrp_problems(db_path=args.db_path):
            print(f"{row['name']}\t{row['problem_type']}\t{row['dimension']}")
        return 0

    summary = summarize_cvrp_store(db_path=args.db_path)
    print(f"total={summary['total']}")
    print(f"by_type={summary['by_type']}")
    return 0


__all__ = [
    "import_cvrplib_file",
    "import_cvrplib_text",
    "import_cvrp_paths",
    "import_solomon_file",
    "import_solomon_text",
    "load_cvrp_problem",
    "get_cvrp_problem_as_instance",
    "get_cvrp_problems",
    "scan_cvrp_paths",
    "summarize_cvrp_store",
]


if __name__ == "__main__":
    raise SystemExit(main())
