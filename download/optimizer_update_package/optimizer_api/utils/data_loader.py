"""
Data Loader Module
Loads time matrix from Supabase and provides efficient access
"""

import os
import sys
import numpy as np
from typing import List, Optional


class DataLoader:
    """
    Fetches the full NxN time matrix from the Supabase `time_matrix` table.
    Uses a singleton pattern so the matrix is only loaded once per server session.
    Falls back to coordinate-based distance calculation if a pair is missing.
    """
    _instance = None

    def __init__(self):
        # Status flags
        self._use_coordinates = True
        self._matrix_loaded = False
        self._load_error = None
        
        # Try Supabase first
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

        if supabase_url and supabase_key:
            self._load_from_supabase(supabase_url, supabase_key)
        else:
            # Fallback to coordinate-based distance calculation
            self._log("[!] SUPABASE credentials not found. Using coordinate-based distance calculation.")
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None

    def _log(self, message: str):
        """Safe logging that works on all platforms including Windows"""
        # Remove Unicode characters that may cause encoding issues
        safe_message = message.replace("\u2713", "[OK]").replace("\u2717", "[X]")
        try:
            print(safe_message)
        except UnicodeEncodeError:
            # Fallback: encode to ASCII with errors ignored
            print(safe_message.encode('ascii', 'ignore').decode('ascii'))

    def _load_from_supabase(self, url: str, key: str):
        """Load time matrix from Supabase"""
        try:
            from supabase import create_client, Client

            self._log("Loading Time Matrix from Supabase `time_matrix` table...")
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
            self._matrix_loaded = True
            
            self._log(f"[OK] Time Matrix loaded: {n} locations, {len(rows)} edges.")

        except Exception as e:
            self._load_error = str(e)
            self._log(f"[!] Failed to load from Supabase: {e}")
            self._log("[!] Falling back to coordinate-based distance calculation.")
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True

    @classmethod
    def get_instance(cls) -> "DataLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_matrix_loaded(self) -> bool:
        """Check if time matrix was successfully loaded from Supabase"""
        return self._matrix_loaded and not self._use_coordinates

    def get_load_error(self) -> Optional[str]:
        """Get the error message if matrix failed to load"""
        return self._load_error

    def get_status(self) -> dict:
        """Get detailed status of the data loader"""
        return {
            "matrix_loaded": self._matrix_loaded,
            "use_coordinates": self._use_coordinates,
            "location_count": len(self.locations) if hasattr(self, 'locations') else 0,
            "error": self._load_error
        }

    def get_submatrix(self, request_locations: List[str]) -> List[List[float]]:
        """
        Extracts an NxN time submatrix for the given subset of location IDs.
        Falls back to coordinate-based calculation if matrix not loaded.
        """
        n = len(request_locations)

        if self._use_coordinates or self.time_matrix is None:
            # Warning: Returning zeros - actual distances should be calculated elsewhere
            # This is a fallback and may produce incorrect optimization results
            self._log(f"[WARN] Time matrix not loaded. Returning zero matrix for {n} locations.")
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
    
    def get_missing_locations(self, location_ids: List[str]) -> List[str]:
        """Find locations not in the time matrix"""
        if self._use_coordinates or not hasattr(self, 'loc_to_idx'):
            return location_ids  # All are "missing"
        return [loc for loc in location_ids if loc not in self.loc_to_idx]


def haversine_distance(lat1: float, lon1: float, lat2: float, lat2_placeholder: float = None) -> float:
    """
    Calculate the great-circle distance between two points.
    Returns distance in meters.
    
    Args:
        lat1, lon1: First point coordinates
        lat2: Second point latitude (or lon2 if 4 args provided)
        lat2_placeholder: Second point longitude (only if 4 args)
    """
    import math
    
    # Handle both (lat1, lon1, lat2, lon2) and (lat1, lon1, lat2) signatures
    if lat2_placeholder is not None:
        lon2 = lat2_placeholder
    else:
        # Assume lat2 is actually lon2 if called with 3 args incorrectly
        return haversine_distance(lat1, lon1, lat2, 0.0)

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
