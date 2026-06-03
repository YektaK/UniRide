"""Apply CVRPLIB/Solomon best-known solution values to the academic DB."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from academic_benchmark.tsplib_manager import DB_PATH, get_db, init_db, load_routing_problem


ROUTE_RE = re.compile(r"^\s*Route\s*#?\s*\d+\s*:\s*(.*)$", re.IGNORECASE)
COST_RE = re.compile(r"^\s*Cost\s+([0-9]+(?:\.[0-9]+)?)\s*$", re.IGNORECASE)


@dataclass
class BKSRecord:
    problem_name: str
    cost: float
    vehicles: int
    source_file: Optional[str] = None
    routes: List[List[int]] = field(default_factory=list)


def parse_routes(text: str) -> List[List[int]]:
    routes: List[List[int]] = []
    for line in text.splitlines():
        match = ROUTE_RE.match(line)
        if not match:
            continue
        route = [int(value) for value in re.findall(r"-?\d+", match.group(1))]
        if route:
            routes.append(route)
    return routes


def parse_cvrplib_solution_text(text: str, *, problem_name: str, source_file: Optional[str] = None) -> BKSRecord:
    routes = parse_routes(text)
    cost = None
    for line in text.splitlines():
        match = COST_RE.match(line)
        if match:
            cost = float(match.group(1))
            break
    if cost is None:
        raise ValueError(f"CVRPLIB solution for {problem_name} does not contain a Cost line")
    return BKSRecord(problem_name=problem_name, cost=cost, vehicles=len(routes), source_file=source_file, routes=routes)


def parse_solomon_solution_text(
    text: str,
    *,
    problem_name: str,
    db_path: str = DB_PATH,
    source_file: Optional[str] = None,
) -> BKSRecord:
    routes = parse_routes(text)
    if not routes:
        raise ValueError(f"Solomon solution for {problem_name} does not contain route rows")
    problem = load_routing_problem(problem_name, db_path=db_path)
    if problem is None:
        raise ValueError(f"Stored RoutingProblem not found for Solomon solution: {problem_name}")
    cost = route_set_cost(routes, problem)
    return BKSRecord(problem_name=problem_name, cost=cost, vehicles=len(routes), source_file=source_file, routes=routes)


def route_set_cost(routes: Sequence[Sequence[int]], problem) -> float:
    matrix = np.asarray(problem.matrix.values, dtype=float)
    depot = int(problem.constraints.depot_index)
    labels = list(problem.matrix.labels or [])
    label_to_index = {str(label): idx for idx, label in enumerate(labels)}

    total = 0.0
    for route in routes:
        current = depot
        for node in route:
            node_index = label_to_index.get(str(int(node)), int(node))
            total += float(matrix[current, node_index])
            current = node_index
        total += float(matrix[current, depot])
    return float(total)


def update_problem_bks(record: BKSRecord, *, db_path: str = DB_PATH) -> None:
    conn = get_db(db_path)
    init_db(conn)
    try:
        conn.execute(
            "UPDATE problems SET optimal=? WHERE name=?",
            (float(record.cost), record.problem_name),
        )
        row = conn.execute(
            "SELECT metadata_json FROM routing_constraints WHERE problem_name=?",
            (record.problem_name,),
        ).fetchone()
        if row is not None:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            metadata.update(
                {
                    "bks_cost": float(record.cost),
                    "bks_vehicles": int(record.vehicles),
                    "bks_source": record.source_file,
                }
            )
            conn.execute(
                "UPDATE routing_constraints SET metadata_json=? WHERE problem_name=?",
                (json.dumps(metadata, sort_keys=True), record.problem_name),
            )
        conn.commit()
    finally:
        conn.close()


def apply_bks_from_solution_dirs(
    *,
    cvrplib_solution_dir: Optional[str] = None,
    solomon_solution_dir: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Dict[str, object]:
    updated: List[str] = []
    skipped: List[Dict[str, str]] = []

    if cvrplib_solution_dir:
        for path in sorted(Path(cvrplib_solution_dir).glob("*.sol")):
            problem_name = path.stem
            try:
                record = parse_cvrplib_solution_text(
                    path.read_text(encoding="utf-8"),
                    problem_name=problem_name,
                    source_file=str(path),
                )
                update_problem_bks(record, db_path=db_path)
                updated.append(problem_name)
            except Exception as exc:  # pragma: no cover - reported by CLI summary
                skipped.append({"file": str(path), "reason": str(exc)})

    if solomon_solution_dir:
        for path in sorted(Path(solomon_solution_dir).glob("*.txt")):
            problem_name = _solomon_problem_name_from_path(path, db_path=db_path)
            try:
                record = parse_solomon_solution_text(
                    path.read_text(encoding="utf-8"),
                    problem_name=problem_name,
                    db_path=db_path,
                    source_file=str(path),
                )
                update_problem_bks(record, db_path=db_path)
                updated.append(problem_name)
            except Exception as exc:  # pragma: no cover - reported by CLI summary
                skipped.append({"file": str(path), "reason": str(exc)})

    return {"updated": updated, "skipped": skipped, "updated_count": len(updated), "skipped_count": len(skipped)}


def _solomon_problem_name_from_path(path: Path, *, db_path: str = DB_PATH) -> str:
    candidate = path.stem.upper()
    if load_routing_problem(candidate, db_path=db_path) is not None:
        return candidate
    if candidate.endswith("B") and load_routing_problem(candidate[:-1], db_path=db_path) is not None:
        return candidate[:-1]
    return candidate


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Apply CVRPLIB/Solomon BKS solution values to academic SQLite DB.")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--cvrplib-solutions")
    parser.add_argument("--solomon-solutions")
    args = parser.parse_args(argv)

    result = apply_bks_from_solution_dirs(
        cvrplib_solution_dir=args.cvrplib_solutions,
        solomon_solution_dir=args.solomon_solutions,
        db_path=args.db_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BKSRecord",
    "apply_bks_from_solution_dirs",
    "parse_cvrplib_solution_text",
    "parse_routes",
    "parse_solomon_solution_text",
    "route_set_cost",
    "update_problem_bks",
]
