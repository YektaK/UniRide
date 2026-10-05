"""Authoritative directed arc lookups for the route certificate (audit C2).

The certificate must judge a response against the ``time_matrix`` the solve
used, so it receives a ``Callable[[str, str], float]`` over physical location
codes. Two sources are supported:

* a request-bound snapshot (``expected_matrix_sha256``): the immutable ``arcs``
  captured by ``TimeMatrixRepository.matrix_snapshot``, i.e. exactly the data
  the binding digest vouches for;
* the process DataLoader repository, for unbound requests.

Neither source synthesizes, defaults or guesses an arc: a missing, zero,
negative or non-finite arc, a coordinate-fallback repository, or an unloaded
matrix raises, which the certifier reports as ``missing_arc``.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from utils.matrix_repository import IncompleteTravelMatrixError, MatrixSnapshotError

ArcLookup = Callable[[str, str], float]


def arc_lookup_from_snapshot(snapshot: Mapping[str, Any]) -> ArcLookup:
    """Directed lookup over the ``arcs`` of a ``matrix_snapshot`` result."""
    arcs: Dict[Tuple[str, str], float] = {}
    for arc in snapshot.get("arcs") or []:
        origin = str(arc["origin_code"]).strip()
        destination = str(arc["destination_code"]).strip()
        arcs[(origin, destination)] = float(arc["duration_minutes"])

    def lookup(origin: str, destination: str) -> float:
        origin, destination = str(origin).strip(), str(destination).strip()
        if origin == destination:
            return 0.0
        value = arcs.get((origin, destination))
        if value is None or not math.isfinite(value) or value <= 0.0:
            raise IncompleteTravelMatrixError(origin, destination)
        return value

    return lookup


def arc_lookup_from_repository(repository: Any) -> ArcLookup:
    """Directed lookup over a ``TimeMatrixRepository`` (wraps ``_arc_value``).

    Wrapped here because the repository exposes no public single-arc accessor
    that rejects invalid arcs (``get_duration`` returns 0.0 in coordinate mode).
    """

    def lookup(origin: str, destination: str) -> float:
        with repository._lock:
            if getattr(repository, "_use_coordinates", False) or repository.time_matrix is None:
                raise MatrixSnapshotError("authoritative travel-time matrix unavailable")
            return float(repository._arc_value(origin, destination))

    return lookup


def arc_lookup_from_submatrix(loader: Any, request: Any) -> ArcLookup:
    """Directed lookup over any object with the DataLoader ``get_submatrix`` contract.

    Adapter for the loader the solve itself used (live-strategy tests inject
    such fakes). Each arc is read as ``get_submatrix([a, b], coordinates)[0][1]``
    with the request's own physical coordinates, so it is exactly the arc the
    strategies obtained; it is not derived from any response.
    """
    coordinates: Dict[str, Dict[str, float]] = {
        request.depot.id: {"lat": request.depot.lat, "lng": request.depot.lng}
    }
    for student in request.students:
        coordinates[student.location_code] = student.coordinates or {"lat": 0, "lng": 0}

    def lookup(origin: str, destination: str) -> float:
        if origin == destination:
            return 0.0
        return float(loader.get_submatrix([origin, destination], coordinates=coordinates)[0][1])

    return lookup


def capture_repository_arcs(repository: Any, request: Any) -> ArcLookup:
    """Copy every arc among the request's physical codes out of ``repository``.

    The copy is taken under one repository lock acquisition and the returned
    lookup only reads that copy, so a later cache refresh (or a refresh during
    the solve) cannot change what the certificate re-costs on. An arc the
    repository cannot answer is remembered as missing and raises on lookup.
    """
    codes = [str(request.depot.id)]
    for student in request.students:
        code = str(student.location_code)
        if code not in codes:
            codes.append(code)
    captured: Dict[Tuple[str, str], float] = {}
    with repository._lock:
        if getattr(repository, "_use_coordinates", False) or repository.time_matrix is None:
            raise MatrixSnapshotError("authoritative travel-time matrix unavailable")
        for origin in codes:
            for destination in codes:
                if origin == destination:
                    continue
                try:
                    captured[(origin, destination)] = float(
                        repository._arc_value(origin, destination)
                    )
                except IncompleteTravelMatrixError:
                    continue

    def lookup(origin: str, destination: str) -> float:
        if origin == destination:
            return 0.0
        value = captured.get((origin, destination))
        if value is None:
            raise IncompleteTravelMatrixError(origin, destination)
        return value

    return lookup


def authoritative_arc_lookup(
    snapshot: Optional[Mapping[str, Any]] = None,
    loader: Any = None,
    request: Any = None,
) -> Optional[ArcLookup]:
    """Return the arc lookup the certificate must use, or ``None`` if unavailable.

    ``snapshot`` is the request's bound matrix snapshot (when the request is
    snapshot-bound); otherwise the repository of ``loader`` (a DataLoader class
    or instance exposing ``get_instance()``; the process DataLoader by default)
    is used. With ``request`` the repository arcs are copied immediately
    (``capture_repository_arcs``); call this BEFORE the solve so the certificate
    judges the matrix the solve started from. Without ``request`` the lookup
    reads the live repository. ``None`` makes the certifier fail closed.
    """
    try:
        if isinstance(snapshot, Mapping):
            return arc_lookup_from_snapshot(snapshot)
        if loader is None:
            from utils.data_loader import DataLoader as loader
        repository = loader.get_instance().repository
        if request is not None:
            return capture_repository_arcs(repository, request)
        return arc_lookup_from_repository(repository)
    except Exception:  # noqa: BLE001 - no authoritative matrix => fail closed
        return None


__all__ = [
    "ArcLookup",
    "arc_lookup_from_repository",
    "arc_lookup_from_snapshot",
    "capture_repository_arcs",
    "arc_lookup_from_submatrix",
    "authoritative_arc_lookup",
]
