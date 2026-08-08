"""
Injectable time-matrix repository.

Owns the travel-time matrix cache, its lifecycle (load/refresh/close),
cache-health metadata, and the provider seam so callers and tests can inject
a controlled source (Supabase or a fake) instead of depending on the
process-level DataLoader singleton.

The DataLoader (utils/data_loader.py) keeps its singleton facade and
delegates here.
"""

from __future__ import annotations

import math
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Protocol


class IncompleteTravelMatrixError(LookupError):
    """A requested directed arc is missing, zero, negative, or non-finite.

    Raised by the repository's lookup path when the loaded travel-time matrix
    cannot answer for a given (source, target) pair. Source==target is always
    valid (0.0). Mirrors the audit P0 requirement on arc completeness.
    """

    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        super().__init__(
            f"Incomplete travel matrix: no valid arc {source!r} -> {target!r}."
        )


class TravelTimeProvider(Protocol):
    """Source of raw travel rows: origin code, destination code, minutes."""

    def fetch_rows(self) -> List[Dict[str, Any]]:
        """Return rows with ``origin_code``, ``destination_code``, ``duration_minutes``."""
        ...


class SupabaseTimeMatrixProvider:
    """Loads `time_matrix` rows from a Supabase table through ``create_client``."""

    def __init__(self, url: str, key: str, timeout_seconds: Optional[float] = None):
        self.url = url
        self.key = key
        self.timeout_seconds = timeout_seconds

    def fetch_rows(self) -> List[Dict[str, Any]]:
        from supabase import create_client, Client  # local import (lazy)

        client = self._build_client(create_client)
        response = client.table("time_matrix").select(
            "origin_code, destination_code, duration_minutes"
        ).execute()
        rows = response.data
        if not rows:
            raise RuntimeError("time_matrix table is empty.")
        return rows

    def _build_client(self, create_client: Callable) -> Any:
        """Create the supabase client, applying the request timeout when the
        installed SDK supports it (``postgrest_client_timeout`` via
        ``ClientOptions``). Version-guarded: if the option is unavailable,
        fall back to the SDK default rather than failing startup.
        """
        if self.timeout_seconds is None:
            return create_client(self.url, self.key)
        try:
            from supabase.lib.client_options import ClientOptions

            return create_client(
                self.url,
                self.key,
                options=ClientOptions(postgrest_client_timeout=self.timeout_seconds),
            )
        except (ImportError, TypeError):
            return create_client(self.url, self.key)


class TimeMatrixRepository:
    """Owns the cached NxN travel-time matrix and its lifecycle/health.

    Attributes mirror the legacy DataLoader shape so delegation is trivial:
    ``locations``, ``loc_to_idx``, ``time_matrix``, ``_use_coordinates``,
    ``_loaded_at``.
    """

    def __init__(
        self,
        provider: Optional[TravelTimeProvider] = None,
        ttl_seconds: int = 600,
        clock: Callable[[], float] = time.time,
    ):
        self._provider = provider
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.RLock()

        self.locations: List[str] = []
        self.loc_to_idx: dict = {}
        self.time_matrix = None
        self._use_coordinates = True
        self._loaded_at: Optional[float] = None
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------ lifecycle

    def load(self) -> None:
        """Load from the provider; coordinate fallback on first-load failure.

        Last-known-good: if a matrix is already loaded and a *refresh* fetch
        fails, the previous matrix is kept (and reported stale via health)
        instead of clearing to empty. The very first load has no prior matrix,
        so failure still falls back to coordinates.
        """
        if self._provider is None:
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True
            self._loaded_at = None
            self._last_error = None
            return
        have_matrix = self.time_matrix is not None and not self._use_coordinates
        try:
            rows = self._provider.fetch_rows()
            self._build_from_rows(rows)
            self._use_coordinates = False
            self._loaded_at = self._clock()
            self._last_error = None
        except Exception as exc:  # noqa: BLE001 - fallback, not propagate
            self._last_error = str(exc)
            if have_matrix:
                # Keep the last-known-good matrix; it is now stale (age grows
                # beyond TTL) rather than an empty coordinate fallback.
                return
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True
            self._loaded_at = None

    def refresh(self, force: bool = False) -> None:
        """Reload from the provider when stale or forced (double-checked lock)."""
        if self._provider is None:
            return
        if not force and not self._is_cache_stale():
            return
        with self._lock:
            if not force and not self._is_cache_stale():
                return
            self.load()

    def close(self) -> None:
        """Clear cached state — test isolation / lifecycle boundary."""
        with self._lock:
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True
            self._loaded_at = None
            self._last_error = None

    # ------------------------------------------------------------------- helpers

    def _build_from_rows(self, rows: List[Dict[str, Any]]) -> None:
        location_set: dict = {}
        for row in rows:
            for col in ("origin_code", "destination_code"):
                if row[col] not in location_set:
                    location_set[row[col]] = len(location_set)

        n = len(location_set)
        self.locations = list(location_set.keys())
        self.loc_to_idx = location_set

        matrix = [[0.0] * n for _ in range(n)]
        for row in rows:
            i = self.loc_to_idx.get(row["origin_code"])
            j = self.loc_to_idx.get(row["destination_code"])
            if i is not None and j is not None:
                matrix[i][j] = float(row["duration_minutes"])
        for i in range(n):
            matrix[i][i] = 0.0
        self.time_matrix = matrix

    def _is_cache_stale(self) -> bool:
        with self._lock:
            if self._loaded_at is None or self._ttl_seconds <= 0:
                return False
            return (self._clock() - self._loaded_at) > self._ttl_seconds

    # -------------------------------------------------------------------- health

    def health(self) -> dict:
        """Cache-health metadata for observability boundaries."""
        with self._lock:
            loaded_at = self._loaded_at
            if self.time_matrix is not None:
                edges = sum(
                    1
                    for routes in self.time_matrix
                    for value in routes
                    if value != 0.0
                )
            else:
                edges = 0
            stale = False
            age_seconds = None
            if loaded_at is not None:
                age_seconds = max(0.0, self._clock() - loaded_at)
                stale = (age_seconds > self._ttl_seconds) if self._ttl_seconds > 0 else False
            if self.time_matrix is not None:
                source = "supabase"
            elif self._provider is not None:
                source = "empty"
            else:
                source = "coordinates"
            return {
                "source": source,
                "loaded": loaded_at is not None,
                "stale": stale,
                "age_seconds": age_seconds,
                "ttl_seconds": self._ttl_seconds,
                "locations": len(self.locations),
                "edges": edges,
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------ queries

    def get_submatrix(
        self,
        request_locations: List[str],
        coordinates: Optional[Dict[str, Dict[str, float]]] = None,
        geo_coords: bool = False,
        asymmetric_haversine: bool = False,
    ) -> List[List[float]]:
        n = len(request_locations)

        with self._lock:
            if not self._use_coordinates and self.time_matrix is not None:
                self.refresh()

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
                    submatrix[i][j] = self._arc_value(from_loc, to_loc)
            return submatrix

    def get_duration(self, from_loc: str, to_loc: str) -> float:
        with self._lock:
            if self._use_coordinates or self.time_matrix is None:
                return 0.0
            return self._arc_value(from_loc, to_loc)

    def has_location(self, loc_id: str) -> bool:
        with self._lock:
            return loc_id in self.loc_to_idx

    def _arc_value(self, from_loc: str, to_loc: str) -> float:
        """Return the directed arc value, rejecting invalid arcs.

        source == target is always 0.0. A missing location or a missing,
        zero, negative, or non-finite off-diagonal value raises
        ``IncompleteTravelMatrixError``.
        """
        if from_loc == to_loc:
            return 0.0
        idx_from = self.loc_to_idx.get(from_loc)
        idx_to = self.loc_to_idx.get(to_loc)
        if idx_from is None or idx_to is None or self.time_matrix is None:
            raise IncompleteTravelMatrixError(from_loc, to_loc)
        value = float(self.time_matrix[idx_from][idx_to])
        if not math.isfinite(value) or value <= 0.0:
            raise IncompleteTravelMatrixError(from_loc, to_loc)
        return value

    # ------------------------------------------------------------ static builders

    @staticmethod
    def build_euclidean_matrix(
        locations: List[str],
        coordinates: Dict[str, Dict[str, float]],
    ) -> List[List[float]]:
        from uniride_core.algorithms.distance import euclidean_distance_2d

        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = coordinates.get(locations[i], {})
            x1, y1 = c1.get("lat", 0.0), c1.get("lng", 0.0)
            for j in range(i + 1, n):
                c2 = coordinates.get(locations[j], {})
                x2, y2 = c2.get("lat", 0.0), c2.get("lng", 0.0)
                dist = euclidean_distance_2d((x1, y1), (x2, y2))
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
        from uniride_core.algorithms.distance import (
            estimate_travel_time,
            haversine_distance,
        )

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


__all__ = [
    "SupabaseTimeMatrixProvider",
    "TimeMatrixRepository",
    "TravelTimeProvider",
]