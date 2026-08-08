"""
Data Loader Module
Loads time matrix from Supabase and provides efficient access.

Kept as the verified process-level singleton facade (``SingletonMeta``);
the actual cache/lifecycle/health lives in an injectable
``TimeMatrixRepository`` (``utils.matrix_repository``) so tests can control
the provider without touching the singleton.
"""

import os
import logging
from typing import Dict, List, Optional

from uniride_core.algorithms._platform import fix_windows_encoding

fix_windows_encoding()

logger = logging.getLogger(__name__)

from utils.patterns import SingletonMeta
from utils.matrix_repository import (
    IncompleteTravelMatrixError,
    SupabaseTimeMatrixProvider,
    TimeMatrixRepository,
)


class DataLoader(metaclass=SingletonMeta):
    """
    Fetches the full NxN time matrix from the Supabase `time_matrix` table.

    Uses SingletonMeta (thread-safe double-checked locking) so the matrix is
    loaded exactly once per server session. Delegates the actual cache to an
    injectable ``TimeMatrixRepository``; construction accepts an optional
    pre-built repository (honored only before the singleton is created).
    Falls back to coordinate-based distance calculation if a pair is missing.
    """

    def __init__(self, repository: Optional[TimeMatrixRepository] = None):
        self._lock = repository._lock if repository is not None else None

        if repository is None:
            try:
                ttl = int(os.environ.get("TIME_MATRIX_CACHE_TTL_SECONDS", "600"))
            except ValueError:
                ttl = 600
            try:
                timeout = float(
                    os.environ.get("TIME_MATRIX_PROVIDER_TIMEOUT_SECONDS", "10.0")
                )
            except ValueError:
                timeout = 10.0
            supabase_url = os.environ.get("SUPABASE_URL", "")
            supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
            if supabase_url and supabase_key:
                provider = SupabaseTimeMatrixProvider(
                    supabase_url, supabase_key, timeout_seconds=timeout
                )
            else:
                logger.warning(
                    "SUPABASE credentials not found. Using coordinate-based distance calculation."
                )
                provider = None
            repository = TimeMatrixRepository(
                provider=provider,
                ttl_seconds=ttl,
            )
            repository.load()
        self._repository = repository

    # ------------------------------------------------------------ composition

    @property
    def repository(self) -> TimeMatrixRepository:
        """The injectable repository backing this singleton."""
        return self._repository

    @classmethod
    def get_instance(cls) -> "DataLoader":
        """Returns the singleton instance (backward-compatible alias)."""
        return cls()

    # ---------------------------------------------------------- delegation

    def refresh(self, force: bool = False) -> None:
        """Refresh the cached time matrix when stale or forced."""
        self._repository.refresh(force=force)

    def get_submatrix(
        self,
        request_locations: List[str],
        coordinates: Optional[Dict[str, Dict[str, float]]] = None,
        geo_coords: bool = False,
        asymmetric_haversine: bool = False,
    ) -> List[List[float]]:
        """
        Extract an NxN time submatrix for the given subset of location IDs.

        Falls back to coordinate-based distance when the Supabase matrix is
        not loaded. See ``TimeMatrixRepository.get_submatrix``.
        """
        return self._repository.get_submatrix(
            request_locations,
            coordinates=coordinates,
            geo_coords=geo_coords,
            asymmetric_haversine=asymmetric_haversine,
        )

    def get_duration(self, from_loc: str, to_loc: str) -> float:
        """Get duration between two locations (0 if unknown)."""
        return self._repository.get_duration(from_loc, to_loc)

    def has_location(self, loc_id: str) -> bool:
        """Check if location exists in the time matrix."""
        return self._repository.has_location(loc_id)

    def health(self) -> dict:
        """Cache-health metadata for the singleton's repository."""
        return self._repository.health()

    # ------------------------------------------------------ legacy attributes

    @property
    def locations(self) -> List[str]:
        return self._repository.locations

    @property
    def loc_to_idx(self) -> dict:
        return self._repository.loc_to_idx

    @property
    def time_matrix(self):
        return self._repository.time_matrix

    @property
    def _use_coordinates(self) -> bool:
        return self._repository._use_coordinates

    @property
    def _loaded_at(self) -> Optional[float]:
        return self._repository._loaded_at

    @property
    def _cache_ttl_seconds(self) -> int:
        return self._repository._ttl_seconds

    @property
    def _supabase_url(self) -> str:
        return ""

    @property
    def _supabase_key(self) -> str:
        return ""

    # ------------------------------------------------------------ static builders

    @staticmethod
    def build_euclidean_matrix(
        locations: List[str],
        coordinates: Dict[str, Dict[str, float]]
    ) -> List[List[float]]:
        """
        Build NxN euclidean distance matrix from coordinate dict.

        Delegates to ``TimeMatrixRepository.build_euclidean_matrix``.
        """
        return TimeMatrixRepository.build_euclidean_matrix(locations, coordinates)

    @staticmethod
    def build_haversine_matrix(
        locations: List[str],
        coordinates: Dict[str, Dict[str, float]],
        avg_speed_kmh: float = 40.0,
        asymmetric: bool = False,
        asymmetry_range: float = 0.15,
    ) -> List[List[float]]:
        """
        Build NxN travel-time matrix (minutes) from geographic lat/lng.

        Delegates to ``TimeMatrixRepository.build_haversine_matrix``.
        """
        return TimeMatrixRepository.build_haversine_matrix(
            locations,
            coordinates,
            avg_speed_kmh=avg_speed_kmh,
            asymmetric=asymmetric,
            asymmetry_range=asymmetry_range,
        )


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate euclidean (L2) distance between two 2D points. Backward-compatible wrapper."""
    from uniride_core.algorithms.distance import euclidean_distance_2d

    return euclidean_distance_2d((x1, y1), (x2, y2))


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Backward-compatible re-export from uniride_core.algorithms.distance."""
    from uniride_core.algorithms.distance import haversine_distance as _hd

    return _hd(lat1, lng1, lat2, lng2)