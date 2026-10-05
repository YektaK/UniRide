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

import contextlib
import contextvars
import math
import hashlib
import json
import time
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Sequence


DEFAULT_RETRY_BASE_SECONDS = 30.0
# Backoff cap when the TTL is disabled (ttl <= 0).
MAX_RETRY_BACKOFF_SECONDS = 600.0
# Rows per PostgREST request when loading ``time_matrix``.
TIME_MATRIX_PAGE_SIZE = 1000


class IncompleteTravelMatrixError(LookupError):
    """A requested directed arc is missing, zero, negative, or non-finite.

    Raised by the repository's lookup path when the loaded travel-time matrix
    cannot answer for a given (source, target) pair. Source==target is always
    valid (0.0). Mirrors the audit P0 requirement on arc completeness.
    """

    def __init__(self, source: str, target: str, *, unknown_location: bool = False):
        self.source = source
        self.target = target
        # True when a requested code is absent from the matrix (a caller-input
        # problem); False when the codes exist but the stored arc is invalid
        # (a stored-data problem). Used only to choose a redacted HTTP status.
        self.unknown_location = unknown_location
        super().__init__(
            f"Incomplete travel matrix: no valid arc {source!r} -> {target!r}."
        )


class MatrixSnapshotError(RuntimeError):
    """Raised when a healthy, complete Supabase matrix snapshot is unavailable."""


class MatrixUnavailableError(MatrixSnapshotError):
    """No authoritative travel-time matrix is loaded (fail closed).

    Raised by the repository's lookup path when the Supabase ``time_matrix``
    has not been (successfully) loaded, instead of returning zeros or values
    derived from coordinates. The message is fixed and never carries provider
    errors, URLs, keys or location codes.
    """

    def __init__(self) -> None:
        super().__init__("authoritative travel-time matrix unavailable")


_ACADEMIC_COORDINATE_SCOPE: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "uniride_academic_coordinate_scope", default=False
)


@contextlib.contextmanager
def academic_coordinate_scope() -> Iterator[None]:
    """Mark a block as an academic benchmark run (TSPLIB/CVRPLIB).

    Inside the scope, ``get_submatrix`` builds distances from the problem's
    own coordinates (those define the academic metric); the stored UniRide
    ``time_matrix`` is neither consulted nor required. This is explicit and
    scoped to the current context: operational requests never enter it, so
    coordinate-derived values still cannot stand in for UniRide travel times.
    """
    token = _ACADEMIC_COORDINATE_SCOPE.set(True)
    try:
        yield
    finally:
        _ACADEMIC_COORDINATE_SCOPE.reset(token)


def in_academic_coordinate_scope() -> bool:
    """True while inside :func:`academic_coordinate_scope` (legacy /benchmark runner)."""
    return _ACADEMIC_COORDINATE_SCOPE.get()


def _coordinate_fallback_allowed() -> bool:
    """Read the explicit dev/test opt-in (``UNIRIDE_ALLOW_COORDINATE_FALLBACK``)."""
    try:
        from runtime_config import allow_coordinate_fallback
    except ModuleNotFoundError:  # package-style import path
        from optimizer_api.runtime_config import allow_coordinate_fallback
    return allow_coordinate_fallback()


def matrix_sha256(locations: list[str], matrix: list[list[float]]) -> str:
    """Return a stable digest for every directed off-diagonal matrix entry."""
    if len(locations) != len(matrix) or any(len(row) != len(locations) for row in matrix):
        raise ValueError("matrix must be square and match locations")
    if len(set(locations)) != len(locations):
        raise ValueError("locations must be unique")

    entries = [
        [origin, destination, float(matrix[i][j]).hex()]
        for i, origin in enumerate(locations)
        for j, destination in enumerate(locations)
        if i != j
    ]
    entries.sort(key=lambda row: (row[0], row[1]))
    payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
        rows: List[Dict[str, Any]] = []
        start = 0
        # PostgREST caps a response at its max-rows setting (1000 on hosted
        # projects); page until a short page so larger matrices are not truncated.
        while True:
            response = (
                client.table("time_matrix")
                .select("origin_code, destination_code, duration_minutes")
                .order("origin_code")
                .order("destination_code")
                .range(start, start + TIME_MATRIX_PAGE_SIZE - 1)
                .execute()
            )
            page = response.data or []
            rows.extend(page)
            if len(page) < TIME_MATRIX_PAGE_SIZE:
                break
            start += TIME_MATRIX_PAGE_SIZE
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
            from supabase.client import ClientOptions

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
        allow_coordinate_fallback: Optional[bool] = None,
        retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
    ):
        self._provider = provider
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        # Failed-load backoff: base * 2**(consecutive_failures - 1), capped at
        # the TTL; reset by a successful load.
        self._retry_base_seconds = (
            retry_base_seconds if retry_base_seconds > 0 else DEFAULT_RETRY_BASE_SECONDS
        )
        self._consecutive_failures = 0
        # None -> read UNIRIDE_ALLOW_COORDINATE_FALLBACK at call time.
        self._allow_coordinate_fallback = allow_coordinate_fallback
        self._lock = threading.RLock()

        self.locations: List[str] = []
        self.loc_to_idx: dict = {}
        self.time_matrix = None
        self._use_coordinates = True
        self._loaded_at: Optional[float] = None
        self._last_error: Optional[str] = None
        self._next_retry_at: Optional[float] = None

    # ------------------------------------------------------------------ lifecycle

    def load(self) -> None:
        """Load from the provider; fail closed on first-load failure.

        Last-known-good: if a matrix is already loaded and a *refresh* fetch
        fails, the previous matrix is kept (and reported stale via health)
        instead of clearing to empty. A failed fetch also sets a retry
        backoff (``_next_retry_at``) so automatic refreshes do not hammer a
        down provider on every call. The very first load has no prior matrix,
        so failure leaves the repository empty ("no authoritative matrix");
        lookups then raise ``MatrixUnavailableError`` until a later automatic
        retry (after the backoff) or a forced refresh succeeds.
        """
        if self._provider is None:
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True
            self._loaded_at = None
            self._last_error = None
            self._next_retry_at = None
            self._consecutive_failures = 0
            return
        have_matrix = self.time_matrix is not None and not self._use_coordinates
        try:
            rows = self._provider.fetch_rows()
            self._build_from_rows(rows)
            self._use_coordinates = False
            self._loaded_at = self._clock()
            self._last_error = None
            self._next_retry_at = None
            self._consecutive_failures = 0
        except Exception as exc:  # noqa: BLE001 - fallback, not propagate
            self._last_error = str(exc)
            self._consecutive_failures += 1
            self._next_retry_at = self._clock() + self._retry_backoff_seconds()
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
        """Reload from the provider when stale or forced (double-checked lock).

        Automatic refreshes respect the retry backoff set by a failed load:
        while ``_next_retry_at`` is in the future, no fetch is attempted and
        the last-known-good matrix (or coordinate fallback) keeps serving.
        A forced refresh always bypasses the backoff. A repository that has a
        provider but never loaded successfully counts as stale, so a failed
        first load is retried (after the backoff) without a restart.
        """
        if self._provider is None:
            return
        if not force and self._in_backoff():
            return
        if not force and not self._is_cache_stale():
            return
        with self._lock:
            if not force and self._in_backoff():
                return
            if not force and not self._is_cache_stale():
                return
            self.load()

    def _retry_backoff_seconds(self) -> float:
        """Exponential backoff for the current failure streak, capped at the TTL."""
        cap = self._ttl_seconds if self._ttl_seconds > 0 else MAX_RETRY_BACKOFF_SECONDS
        exponent = min(max(self._consecutive_failures - 1, 0), 32)
        return min(cap, self._retry_base_seconds * (2 ** exponent))

    def _in_backoff(self) -> bool:
        """True while a failed load's retry window is still active."""
        if self._next_retry_at is None:
            return False
        return self._clock() < self._next_retry_at

    def close(self) -> None:
        """Clear cached state — test isolation / lifecycle boundary."""
        with self._lock:
            self.locations = []
            self.loc_to_idx = {}
            self.time_matrix = None
            self._use_coordinates = True
            self._loaded_at = None
            self._last_error = None
            self._next_retry_at = None
            self._consecutive_failures = 0

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
            if self._loaded_at is None:
                # Never loaded: stale whenever a provider could still load it.
                return self._provider is not None
            if self._ttl_seconds <= 0:
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
        """Directed travel-time submatrix (minutes) from the stored matrix.

        Fail-closed contract: refreshes in every mode (so a failed first load
        recovers once the provider is back), and when no authoritative matrix
        is loaded raises ``MatrixUnavailableError`` instead of returning
        zeros or coordinate-derived values. A requested location missing from
        a loaded matrix raises ``IncompleteTravelMatrixError``. Only the
        explicit opt-in ``UNIRIDE_ALLOW_COORDINATE_FALLBACK`` re-enables the
        coordinate (haversine/Euclidean) stand-ins, and only when coordinates
        are supplied.
        """
        n = len(request_locations)

        if coordinates and _ACADEMIC_COORDINATE_SCOPE.get():
            # Academic benchmark problem: its coordinates define the metric.
            if geo_coords:
                return self.build_haversine_matrix(
                    request_locations, coordinates, asymmetric=True
                )
            return self.build_euclidean_matrix(request_locations, coordinates)

        with self._lock:
            self.refresh()

            if self._use_coordinates or self.time_matrix is None:
                if coordinates and self._coordinate_fallback_enabled():
                    if geo_coords:
                        return self.build_haversine_matrix(
                            request_locations, coordinates,
                            asymmetric=asymmetric_haversine if not geo_coords else True,
                        )
                    return self.build_euclidean_matrix(request_locations, coordinates)
                raise MatrixUnavailableError()

            submatrix = [[0.0] * n for _ in range(n)]

            for i, from_loc in enumerate(request_locations):
                for j, to_loc in enumerate(request_locations):
                    submatrix[i][j] = self._arc_value(from_loc, to_loc)
            return submatrix

    def get_duration(self, from_loc: str, to_loc: str) -> float:
        """Directed duration (minutes); never 0.0 for an unknown pair.

        Raises ``MatrixUnavailableError`` when no authoritative matrix is
        loaded and ``IncompleteTravelMatrixError`` for a missing or invalid
        arc. Only ``from_loc == to_loc`` yields 0.0.
        """
        with self._lock:
            self.refresh()
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixUnavailableError()
            return self._arc_value(from_loc, to_loc)

    def arc(self, from_loc: str, to_loc: str) -> float:
        """Strict directed arc (minutes) from the stored matrix only.

        Public accessor for the route certificate. Unlike ``get_submatrix`` it
        never serves coordinate-derived values, neither under the
        ``UNIRIDE_ALLOW_COORDINATE_FALLBACK`` opt-in nor inside
        ``academic_coordinate_scope()``: a certificate may only be judged on
        the authoritative ``time_matrix``. Raises ``MatrixUnavailableError``
        when it is not loaded and ``IncompleteTravelMatrixError`` for a missing
        or invalid arc; ``from_loc == to_loc`` is 0.0.
        """
        with self._lock:
            self.refresh()
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixUnavailableError()
            return self._arc_value(from_loc, to_loc)

    def _provenance_locked(self) -> Dict[str, Any]:
        """Provenance of the loaded matrix; caller holds the lock and has
        verified a matrix is loaded. Never contains keys, URLs or codes."""
        loaded_at = self._loaded_at
        return {
            "source": "supabase",
            "sha256": matrix_sha256(list(self.locations), self.time_matrix),
            "location_count": len(self.locations),
            "loaded_at": (
                datetime.fromtimestamp(loaded_at, tz=timezone.utc).isoformat()
                if loaded_at is not None
                else None
            ),
            "age_seconds": (
                round(max(0.0, self._clock() - loaded_at), 3)
                if loaded_at is not None
                else None
            ),
        }

    def matrix_provenance(self) -> Dict[str, Any]:
        """Public, redaction-safe provenance of the currently loaded matrix.

        Keys: ``source``, ``sha256``, ``location_count``, ``loaded_at`` (ISO
        UTC) and ``age_seconds``. Raises ``MatrixUnavailableError`` when no
        authoritative matrix is loaded.
        """
        with self._lock:
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixUnavailableError()
            return self._provenance_locked()

    def capture_arcs_with_provenance(
        self, codes: Sequence[str]
    ) -> tuple[Dict[tuple, float], Dict[str, Any]]:
        """:meth:`capture_arcs` plus the provenance of that same matrix state,
        taken under one lock so both describe the same snapshot."""
        unique = list(dict.fromkeys(codes))
        with self._lock:
            self.refresh()
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixUnavailableError()
            arcs = {
                (origin, destination): self._arc_value(origin, destination)
                for origin in unique
                for destination in unique
                if origin != destination
            }
            return arcs, self._provenance_locked()

    def capture_arcs(self, codes: Sequence[str]) -> Dict[tuple, float]:
        """Copy every strict directed arc among ``codes`` in one atomic read.

        Same strictness as :meth:`arc`. The result maps ``(origin, destination)``
        (off-diagonal pairs) to minutes and is a plain copy, so a later refresh
        of the repository cannot change it.
        """
        unique = list(dict.fromkeys(codes))
        with self._lock:
            self.refresh()
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixUnavailableError()
            return {
                (origin, destination): self._arc_value(origin, destination)
                for origin in unique
                for destination in unique
                if origin != destination
            }

    def _coordinate_fallback_enabled(self) -> bool:
        if self._allow_coordinate_fallback is not None:
            return bool(self._allow_coordinate_fallback)
        return _coordinate_fallback_allowed()

    def has_location(self, loc_id: str) -> bool:
        with self._lock:
            return loc_id in self.loc_to_idx

    def readiness_summary(
        self,
        student_locations: List[str],
        depot_code: str,
    ) -> Dict[str, Any]:
        """Redacted aggregate matrix-readiness measurement.

        Counts/booleans only: never exposes location codes, missing arc pairs,
        keys, URLs, or the last provider error. The required set is the depot
        code plus the stripped, deduplicated non-depot student home codes.
        Empty or depot-only input is never complete or ready.
        """
        with self._lock:
            seen: Dict[str, None] = {}
            for code in student_locations:
                cleaned = code.strip()
                if not cleaned or cleaned == depot_code:
                    continue
                seen[cleaned] = None
            has_students = bool(seen)
            required = [depot_code] + list(seen)

            if self.time_matrix is not None and not self._use_coordinates:
                source = "supabase"
                loaded = self._loaded_at is not None
                stale = False
                if loaded and self._ttl_seconds > 0:
                    stale = (self._clock() - self._loaded_at) > self._ttl_seconds
            elif self._provider is not None:
                source = "empty"
                loaded = False
                stale = False
            else:
                source = "coordinates"
                loaded = False
                stale = False

            matrix_location_count = len(self.locations)
            n = len(required)
            expected_arcs = n * (n - 1) if has_students else 0
            depot_present = depot_code in self.loc_to_idx

            missing_locations = 0
            valid_arcs = 0
            present = [code for code in required if code in self.loc_to_idx]
            missing_locations = n - len(present)
            if len(present) > 1 and self.time_matrix is not None:
                idx = {code: self.loc_to_idx[code] for code in present}
                for from_code in present:
                    for to_code in present:
                        if from_code == to_code:
                            continue
                        value = self.time_matrix[idx[from_code]][idx[to_code]]
                        if math.isfinite(value) and value > 0.0:
                            valid_arcs += 1

            complete = (
                has_students
                and depot_present
                and missing_locations == 0
                and valid_arcs == expected_arcs
            )
            has_error = self._last_error is not None
            ready = (
                complete
                and source == "supabase"
                and loaded
                and not stale
                and not has_error
            )

            return {
                "source": source,
                "loaded": loaded,
                "stale": stale,
                "hasError": has_error,
                "matrixLocationCount": matrix_location_count,
                "requiredLocationCount": n,
                "missingRequiredLocationCount": missing_locations,
                "expectedRequiredDirectedArcCount": expected_arcs,
                "validRequiredDirectedArcCount": valid_arcs,
                "invalidOrMissingRequiredDirectedArcCount": expected_arcs - valid_arcs,
                "depotPresent": depot_present,
                "complete": complete,
                "ready": ready,
            }

    def matrix_snapshot(
        self,
        student_locations: List[str],
        depot_code: str,
    ) -> Dict[str, Any]:
        """Return an immutable, redaction-safe snapshot for the requested arcs."""
        with self._lock:
            required = [depot_code]
            seen = {depot_code}
            for code in student_locations:
                cleaned = code.strip()
                if cleaned and cleaned not in seen:
                    required.append(cleaned)
                    seen.add(cleaned)

            if len(required) < 2:
                raise MatrixSnapshotError("student locations are required")
            if self._use_coordinates or self.time_matrix is None:
                raise MatrixSnapshotError("coordinate fallback is not authoritative")
            if self._loaded_at is None:
                raise MatrixSnapshotError("matrix is not loaded")
            if self._last_error is not None:
                raise MatrixSnapshotError("matrix provider is unhealthy")
            if self._ttl_seconds > 0 and self._clock() - self._loaded_at > self._ttl_seconds:
                raise MatrixSnapshotError("matrix is stale")

            locations = list(self.locations)
            matrix = [list(row) for row in self.time_matrix]
            loc_to_idx = dict(self.loc_to_idx)
            provenance = self._provenance_locked()

        if len(matrix) != len(locations) or any(
            len(row) != len(locations) for row in matrix
        ):
            raise MatrixSnapshotError("matrix shape is invalid")
        if any(code not in loc_to_idx for code in required):
            raise MatrixSnapshotError("required matrix location is missing")

        arcs = []
        for origin in required:
            for destination in required:
                if origin == destination:
                    continue
                value = float(matrix[loc_to_idx[origin]][loc_to_idx[destination]])
                if not math.isfinite(value) or value <= 0.0:
                    raise MatrixSnapshotError("required matrix arc is incomplete")
                arcs.append({
                    "origin_code": origin,
                    "destination_code": destination,
                    "duration_minutes": value,
                })

        digest = matrix_sha256(locations, matrix)
        return {
            "id": f"time_matrix:sha256:{digest}",
            "version": digest,
            "sha256": digest,
            "source": "supabase",
            "provenance": provenance,
            "arcs": arcs,
        }

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
            raise IncompleteTravelMatrixError(
                from_loc, to_loc, unknown_location=True
            )
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
    "IncompleteTravelMatrixError",
    "academic_coordinate_scope",
    "in_academic_coordinate_scope",
    "MatrixSnapshotError",
    "MatrixUnavailableError",
    "SupabaseTimeMatrixProvider",
    "TimeMatrixRepository",
    "TravelTimeProvider",
    "matrix_sha256",
]
