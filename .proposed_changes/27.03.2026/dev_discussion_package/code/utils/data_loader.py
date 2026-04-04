"""
Data Loader Module
Loads time matrix from Supabase and provides efficient access
"""

import os
import sys
import logging
import numpy as np
from typing import List, Optional

# Windows ortaminda Unicode karakterlerin konsola yazilmasinda
# charmap encoding hatasi olusmasini onler
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Fetches the full NxN time matrix from the Supabase `time_matrix` table.
    Uses a singleton pattern so the matrix is only loaded once per server session.
    Falls back to coordinate-based distance calculation if a pair is missing.
    """
    _instance = None

    def __init__(self):
        # Try Supabase first
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

        if supabase_url and supabase_key:
            self._load_from_supabase(supabase_url, supabase_key)
        else:
            # Fallback to local CSV/JSON or generate synthetic matrix
            logger.warning("SUPABASE credentials not found. Using coordinate-based distance calculation.")
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True

    def _load_from_supabase(self, url: str, key: str):
        """Load time matrix from Supabase"""
        try:
            from supabase import create_client, Client

            logger.info("Loading Time Matrix from Supabase time_matrix table...")
            client: Client = create_client(url, key)

            response = client.table("time_matrix").select(
                "origin_code, destination_code, duration_minutes"
            ).execute()

            rows = response.data
            if not rows:
                raise RuntimeError("time_matrix table is empty.")

            # Build location index
            location_set: dict = {}
            for row in rows:
                for col in ("origin_code", "destination_code"):
                    if row[col] not in location_set:
                        location_set[row[col]] = len(location_set)

            n = len(location_set)
            self.locations: List[str] = list(location_set.keys())
            self.loc_to_idx: dict = location_set
            self._use_coordinates = False

            # Build NxN matrix
            matrix = np.zeros((n, n), dtype=float)
            for row in rows:
                i = self.loc_to_idx.get(row["origin_code"])
                j = self.loc_to_idx.get(row["destination_code"])
                if i is not None and j is not None:
                    matrix[i][j] = float(row["duration_minutes"])

            np.fill_diagonal(matrix, 0.0)
            self.time_matrix = matrix

            logger.info("Time Matrix loaded: %d locations, %d edges", n, len(rows))

        except Exception as e:
            logger.error("Failed to load from Supabase: %s", e)
            logger.warning("Falling back to coordinate-based distance calculation.")
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True

    @classmethod
    def get_instance(cls) -> "DataLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_submatrix(self, request_locations: List[str]) -> List[List[float]]:
        """
        Extracts an NxN time submatrix for the given subset of location IDs.
        Falls back to coordinate-based calculation if matrix not loaded.
        """
        n = len(request_locations)

        if self._use_coordinates or self.time_matrix is None:
            # Return zeros - actual distances calculated elsewhere
            return [[0.0] * n for _ in range(n)]

        submatrix = [[0.0] * n for _ in range(n)]

        for i, from_loc in enumerate(request_locations):
            for j, to_loc in enumerate(request_locations):
                idx_from = self.loc_to_idx.get(from_loc)
                idx_to = self.loc_to_idx.get(to_loc)
                if idx_from is not None and idx_to is not None:
                    submatrix[i][j] = float(self.time_matrix[idx_from][idx_to])

        return submatrix

    def get_duration(self, from_loc: str, to_loc: str) -> float:
        """
        Get duration between two locations.
        Returns 0 if not found (same location or unknown).
        """
        if self._use_coordinates or self.time_matrix is None:
            return 0.0

        idx_from = self.loc_to_idx.get(from_loc)
        idx_to = self.loc_to_idx.get(to_loc)

        if idx_from is not None and idx_to is not None:
            return float(self.time_matrix[idx_from][idx_to])

        return 0.0

    def has_location(self, loc_id: str) -> bool:
        """Check if location exists in time matrix"""
        return loc_id in self.loc_to_idx


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points.
    Returns distance in meters.
    """
    import math

    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def estimate_travel_time(distance_meters: float, avg_speed_kmh: float = 40.0) -> float:
    """
    Estimate travel time from distance.
    Returns time in minutes.
    """
    distance_km = distance_meters / 1000
    time_hours = distance_km / avg_speed_kmh
    return time_hours * 60  # Convert to minutes
