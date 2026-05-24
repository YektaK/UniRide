"""
Data Loader Module
Loads time matrix from Supabase and provides efficient access
"""

import os
import sys
import logging
import numpy as np
from typing import Dict, List, Optional

# Windows ortaminda Unicode karakterlerin konsola yazilmasinda
# charmap encoding hatasi olusmasini onler
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger(__name__)

from utils.patterns import SingletonMeta


class DataLoader(metaclass=SingletonMeta):
    """
    Fetches the full NxN time matrix from the Supabase `time_matrix` table.
    Uses SingletonMeta (thread-safe double-checked locking) so the matrix is
    loaded exactly once per server session.
    Falls back to coordinate-based distance calculation if a pair is missing.
    """

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
        """Returns the singleton instance (backward-compatible alias)."""
        return cls()

    def get_submatrix(
        self,
        request_locations: List[str],
        coordinates: Optional[Dict[str, Dict[str, float]]] = None,
        geo_coords: bool = False,
        asymmetric_haversine: bool = False,
    ) -> List[List[float]]:
        """
        Extracts an NxN time submatrix for the given subset of location IDs.
        Falls back to coordinate-based distance if the Supabase matrix is not loaded.

        Args:
            request_locations: List of location IDs (same order as matrix indices)
            coordinates: Optional dict mapping location_id -> {"lat": float, "lng": float}.
            geo_coords: When True and Supabase is unavailable, uses haversine distance
                        converted to estimated travel minutes (for real geographic lat/lng).
                        When False (default), uses L2 euclidean distance, which is correct
                        for TSPLIB EUC_2D abstract X-Y coordinates.
            asymmetric_haversine: When True, applies deterministic per-edge perturbation
                        to the haversine matrix to model real-world asymmetric travel times.
                        Enabled by default when geo_coords=True.
        """
        n = len(request_locations)

        if self._use_coordinates or self.time_matrix is None:
            if coordinates:
                if geo_coords:
                    return self.build_haversine_matrix(
                        request_locations, coordinates,
                        asymmetric=asymmetric_haversine if not geo_coords else True,
                    )
                return self.build_euclidean_matrix(request_locations, coordinates)
            return [[0.0] * n for _ in range(n)]

        submatrix = [[0.0] * n for _ in range(n)]

        for i, from_loc in enumerate(request_locations):
            for j, to_loc in enumerate(request_locations):
                idx_from = self.loc_to_idx.get(from_loc)
                idx_to = self.loc_to_idx.get(to_loc)
                if idx_from is not None and idx_to is not None:
                    submatrix[i][j] = float(self.time_matrix[idx_from][idx_to])

        return submatrix

    @staticmethod
    def build_euclidean_matrix(
        locations: List[str],
        coordinates: Dict[str, Dict[str, float]]
    ) -> List[List[float]]:
        """
        Build NxN euclidean distance matrix from coordinate dict.

        Uses L2 (euclidean) distance between coordinate pairs.
        This is the correct distance metric for TSPLIB EUC_2D problems
        where coordinates are abstract X-Y plane positions, NOT geographic.

        Args:
            locations: Ordered list of location IDs (index = matrix row/col)
            coordinates: Dict mapping location_id -> {"lat": float, "lng": float}
                          Note: "lat"/"lng" keys are reused but values are X/Y for TSPLIB.

        Returns:
            NxN symmetric matrix where matrix[i][j] = euclidean distance
        """
        import math

        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = coordinates.get(locations[i], {})
            x1, y1 = c1.get("lat", 0.0), c1.get("lng", 0.0)
            for j in range(i + 1, n):
                c2 = coordinates.get(locations[j], {})
                x2, y2 = c2.get("lat", 0.0), c2.get("lng", 0.0)
                dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                matrix[i][j] = dist
                matrix[j][i] = dist
        return matrix

    @staticmethod
    def build_haversine_matrix(
        locations: List[str],
        coordinates: Dict[str, Dict[str, float]],
        avg_speed_kmh: float = 40.0,
        asymmetric: bool = False,
        asymmetry_range: float = 0.15,
    ) -> List[List[float]]:
        """
        Build NxN travel-time matrix (minutes) from real geographic lat/lng coordinates
        using the haversine formula.

        Args:
            locations: Ordered list of location IDs
            coordinates: Dict mapping location_id -> {"lat": float, "lng": float}
            avg_speed_kmh: Average vehicle speed used to convert distance to time
            asymmetric: When True, applies deterministic per-edge perturbation to model
                        real-world asymmetric travel times (one-way streets, turns, etc.).
            asymmetry_range: Max fractional asymmetry (±15% by default).

        Returns:
            NxN matrix where matrix[i][j] = estimated travel time in minutes
        """
        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = coordinates.get(locations[i], {})
            lat1, lng1 = c1.get("lat", 0.0), c1.get("lng", 0.0)
            for j in range(i + 1, n):
                c2 = coordinates.get(locations[j], {})
                lat2, lng2 = c2.get("lat", 0.0), c2.get("lng", 0.0)
                dist_m = haversine_distance(lat1, lng1, lat2, lng2)
                travel_min = estimate_travel_time(dist_m, avg_speed_kmh)
                if asymmetric:
                    h_ij = hash((locations[i], locations[j])) & 0xFFFFFFFF
                    f_ij = 1.0 + asymmetry_range * (2.0 * (h_ij % 1000) / 1000.0 - 1.0)
                    h_ji = hash((locations[j], locations[i])) & 0xFFFFFFFF
                    f_ji = 1.0 + asymmetry_range * (2.0 * (h_ji % 1000) / 1000.0 - 1.0)
                    matrix[i][j] = travel_min * f_ij
                    matrix[j][i] = travel_min * f_ji
                else:
                    matrix[i][j] = travel_min
                    matrix[j][i] = travel_min
        return matrix

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


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate euclidean (L2) distance between two 2D points.
    This is the standard distance metric for TSPLIB EUC_2D problems.
    """
    import math
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


from utils.haversine import haversine_distance, estimate_travel_time
