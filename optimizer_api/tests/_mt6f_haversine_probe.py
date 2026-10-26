"""Subprocess probe for test_mt6f_haversine_deterministic.py (not a test).

Usage: python _mt6f_haversine_probe.py <academic|fallback>
Prints the ``get_submatrix(..., geo_coords=True)`` result as JSON. Offline:
no provider, no database, no network.
"""

import json
import sys

from utils.matrix_repository import TimeMatrixRepository, academic_coordinate_scope

LOCATIONS = ["D.Kampus", "L1", "L2", "L3", "L4"]
COORDS = {
    "D.Kampus": {"lat": 41.00, "lng": 29.17},
    "L1": {"lat": 41.01, "lng": 29.18},
    "L2": {"lat": 41.02, "lng": 29.19},
    "L3": {"lat": 41.03, "lng": 29.20},
    "L4": {"lat": 40.99, "lng": 29.25},
}


def main(mode: str) -> None:
    repo = TimeMatrixRepository(provider=None)
    repo.load()
    if mode == "academic":
        with academic_coordinate_scope():
            matrix = repo.get_submatrix(LOCATIONS, COORDS, geo_coords=True)
    elif mode == "fallback":
        matrix = repo.get_submatrix(LOCATIONS, COORDS, geo_coords=True)
    else:
        raise SystemExit(f"unknown mode: {mode}")
    print(json.dumps(matrix))


if __name__ == "__main__":
    main(sys.argv[1])
