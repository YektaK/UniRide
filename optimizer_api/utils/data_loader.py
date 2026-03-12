import os
import numpy as np
from typing import List

# Use supabase-py to query the time_matrix table
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

class DataLoader:
    """
    Fetches the full NxN time matrix from the Supabase `time_matrix` table.
    Uses a singleton pattern so the matrix is only loaded once per server session.
    Falls back to zeros if a pair is missing (safe default).
    """
    _instance = None

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as environment variables."
            )

        print("Loading Time Matrix from Supabase `time_matrix` table...")
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Fetch ALL rows from time_matrix (no limit needed for 812 rows)
        response = client.table("time_matrix").select(
            "origin_code, destination_code, duration_minutes"
        ).execute()

        rows = response.data
        if not rows:
            raise RuntimeError("time_matrix table is empty. Run `node import_time_matrix.js` first.")

        # Collect all unique location codes while preserving order
        location_set: dict[str, int] = {}
        for row in rows:
            for col in ("origin_code", "destination_code"):
                if row[col] not in location_set:
                    location_set[row[col]] = len(location_set)

        n = len(location_set)
        self.locations: List[str] = list(location_set.keys())
        self.loc_to_idx: dict[str, int] = location_set

        # Build NxN matrix (default 0)
        matrix = np.zeros((n, n), dtype=float)
        for row in rows:
            i = self.loc_to_idx.get(row["origin_code"])
            j = self.loc_to_idx.get(row["destination_code"])
            if i is not None and j is not None:
                matrix[i][j] = float(row["duration_minutes"])

        # Diagonal must be 0
        np.fill_diagonal(matrix, 0.0)
        self.time_matrix = matrix

        print(f"[✓] Time Matrix loaded: {n} locations, {len(rows)} edges.")

    @classmethod
    def get_instance(cls) -> "DataLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_submatrix(self, request_locations: List[str]) -> List[List[float]]:
        """
        Extracts an NxN time submatrix for the given subset of location IDs.
        Unknown locations default to 0 (safe, handled in ortools as 0-cost arc).
        """
        n = len(request_locations)
        submatrix = [[0.0] * n for _ in range(n)]

        for i, from_loc in enumerate(request_locations):
            for j, to_loc in enumerate(request_locations):
                idx_from = self.loc_to_idx.get(from_loc)
                idx_to = self.loc_to_idx.get(to_loc)
                if idx_from is not None and idx_to is not None:
                    submatrix[i][j] = float(self.time_matrix[idx_from][idx_to])
                # else: leave as 0.0

        return submatrix
