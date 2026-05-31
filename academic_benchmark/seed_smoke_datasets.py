"""Seed small academic benchmark problems into the unified SQLite DB."""

from __future__ import annotations

import argparse
from typing import Dict, List

import numpy as np

from academic_benchmark.cvrplib_manager import import_cvrplib_text, import_solomon_text
from academic_benchmark.tsplib_manager import DB_PATH, load_routing_problem, store_academic_text, store_routing_problem
from uniride_core.models import ConstraintProfile, CostMatrix, RoutingProblem


SMOKE_TSP = """
NAME : smoke-tsp
TYPE : TSP
DIMENSION : 4
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 1 0
3 1 1
4 0 1
EOF
"""


SMOKE_ATSP = """
NAME: smoke-atsp
TYPE: ATSP
DIMENSION: 4
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 3 1 5
2 0 4 2
5 1 0 3
2 6 4 0
EOF
"""


SMOKE_CVRP = """
NAME : smoke-cvrp
TYPE : CVRP
DIMENSION : 4
EDGE_WEIGHT_TYPE : EUC_2D
CAPACITY : 2
NODE_COORD_SECTION
1 0 0
2 3 4
3 6 8
4 7 8
DEMAND_SECTION
1 0
2 1
3 1
4 1
DEPOT_SECTION
1
-1
EOF
"""


SMOKE_SOLOMON = """
smoke-solomon
VEHICLE
NUMBER     CAPACITY
2          2
CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0         0        0        0       0           1000      0
1         3        4        1       0           50        2
2         6        8        1       0           70        2
3         7        8        1       0           90        2
"""


def _smoke_uniride_problem() -> RoutingProblem:
    matrix = np.array(
        [
            [0, 5, 6, 7],
            [5, 0, 2, 4],
            [6, 3, 0, 2],
            [7, 4, 1, 0],
        ],
        dtype=float,
    )
    return RoutingProblem(
        "smoke-uniride",
        "uniride",
        CostMatrix(
            matrix,
            kind="travel_time",
            is_asymmetric=True,
            labels=["campus", "student_001", "student_002", "student_003"],
        ),
        constraints=ConstraintProfile(
            demands=[[0, 0], [1, 0], [0, 1], [0, 1]],
            capacities=[1, 2],
            time_windows=[(0, 100), (10, 50), (20, 70), (30, 90)],
            service_times=[0, 2, 2, 2],
            depot_index=0,
            max_route_duration=30,
            direction="pickup",
        ),
        coordinates=[(0, 0), (3, 4), (6, 8), (7, 8)],
        category="small",
        source="uniride_smoke",
        metadata={
            "matrix_kind": "travel_time",
            "vehicles": 2,
            "anonymized": True,
            "student_count": 3,
            "sw_count": 1,
            "so_count": 2,
        },
    )


def _should_store(name: str, db_path: str, force: bool) -> bool:
    return force or load_routing_problem(name, db_path=db_path) is None


def seed_smoke_datasets(*, db_path: str = DB_PATH, force: bool = False) -> Dict[str, List[str]]:
    """Seed one small TSP, ATSP, CVRP, CVRPTW, and UniRide matrix problem."""
    stored: List[str] = []
    skipped: List[str] = []

    def mark(name: str, did_store: bool) -> None:
        (stored if did_store else skipped).append(name)

    if _should_store("smoke-tsp", db_path, force):
        store_academic_text(SMOKE_TSP, "tsplib", name="smoke-tsp", db_path=db_path, source_file="seed_smoke_datasets")
        mark("smoke-tsp", True)
    else:
        mark("smoke-tsp", False)

    if _should_store("smoke-atsp", db_path, force):
        store_academic_text(SMOKE_ATSP, "atsp", name="smoke-atsp", db_path=db_path, source_file="seed_smoke_datasets")
        mark("smoke-atsp", True)
    else:
        mark("smoke-atsp", False)

    if _should_store("smoke-cvrp", db_path, force):
        import_cvrplib_text(SMOKE_CVRP, name="smoke-cvrp", db_path=db_path, source_file="seed_smoke_datasets")
        mark("smoke-cvrp", True)
    else:
        mark("smoke-cvrp", False)

    if _should_store("smoke-solomon", db_path, force):
        import_solomon_text(SMOKE_SOLOMON, name="smoke-solomon", db_path=db_path, source_file="seed_smoke_datasets")
        mark("smoke-solomon", True)
    else:
        mark("smoke-solomon", False)

    if _should_store("smoke-uniride", db_path, force):
        store_routing_problem(_smoke_uniride_problem(), db_path=db_path, source_file="seed_smoke_datasets")
        mark("smoke-uniride", True)
    else:
        mark("smoke-uniride", False)

    return {"stored": stored, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed small academic benchmark smoke datasets")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--force", action="store_true", help="Replace existing smoke problems")
    args = parser.parse_args()
    result = seed_smoke_datasets(db_path=args.db_path, force=args.force)
    print(f"stored={result['stored']}")
    print(f"skipped={result['skipped']}")


if __name__ == "__main__":
    main()

