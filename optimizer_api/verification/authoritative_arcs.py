"""Authoritative directed arc lookups for the route certificate (audit C2).

The certificate must judge a response against the ``time_matrix`` the solve
used, so it receives a ``Callable[[str, str], float]`` over physical location
codes. Two sources are supported:

* a request-bound snapshot (``expected_matrix_sha256``): the immutable ``arcs``
  captured by ``TimeMatrixRepository.matrix_snapshot``, i.e. exactly the data
  the binding digest vouches for;
* the process DataLoader repository, for unbound requests (copied via the public `capture_arcs` before the solve).

Neither source synthesizes, defaults or guesses an arc: a missing, zero,
negative or non-finite arc, or an unloaded
matrix raises, which the certifier reports as ``missing_arc``.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from utils.matrix_repository import IncompleteTravelMatrixError

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

    _attach_provenance(lookup, snapshot.get("provenance"))
    return lookup


def _attach_provenance(lookup: ArcLookup, provenance: Any) -> None:
    """Record the provenance of the matrix state a lookup was built from."""
    if isinstance(provenance, Mapping):
        lookup.matrix_provenance = dict(provenance)  # type: ignore[attr-defined]


def matrix_provenance_of(lookup: Optional[ArcLookup]) -> Optional[Dict[str, Any]]:
    """Provenance (source/sha256/location_count/loaded_at/age_seconds) of the
    matrix state ``lookup`` was captured from, or ``None`` if unknown."""
    provenance = getattr(lookup, "matrix_provenance", None)
    return dict(provenance) if isinstance(provenance, Mapping) else None


def arc_lookup_from_repository(repository: Any) -> ArcLookup:
    """Live directed lookup over a ``TimeMatrixRepository`` (``repository.arc``).

    Reads the repository at every call; prefer :func:`capture_repository_arcs`
    when a solve happens in between. Strict: never coordinate-derived values.
    """

    def lookup(origin: str, destination: str) -> float:
        return float(repository.arc(origin, destination))

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

    ``repository.capture_arcs`` takes the copy atomically and strictly; the
    returned lookup only reads that copy, so a later cache refresh (or a refresh
    during the solve) cannot change what the certificate re-costs on.
    ``MatrixUnavailableError`` / ``IncompleteTravelMatrixError`` propagate: the
    caller must fail closed before solving.
    """
    codes = [str(request.depot.id)] + [
        str(student.location_code) for student in request.students
    ]
    provenance: Any = None
    if hasattr(repository, "capture_arcs_with_provenance"):
        captured, provenance = repository.capture_arcs_with_provenance(codes)
    else:
        captured = repository.capture_arcs(codes)

    def lookup(origin: str, destination: str) -> float:
        if origin == destination:
            return 0.0
        value = captured.get((origin, destination))
        if value is None:
            raise IncompleteTravelMatrixError(origin, destination)
        return value

    _attach_provenance(lookup, provenance)
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
    reads the live repository.

    A matrix that cannot answer (``MatrixSnapshotError`` including
    ``MatrixUnavailableError``, ``IncompleteTravelMatrixError``) propagates so
    the router can fail closed with its redacted 503/422 BEFORE solving. Any
    other failure to reach a repository yields ``None``, which makes the
    certifier fail closed.
    """
    if isinstance(snapshot, Mapping):
        return arc_lookup_from_snapshot(snapshot)
    try:
        if loader is None:
            from utils.data_loader import DataLoader as loader
        repository = loader.get_instance().repository
    except Exception:  # noqa: BLE001 - no repository => certifier fails closed
        return None
    if request is not None:
        return capture_repository_arcs(repository, request)
    return arc_lookup_from_repository(repository)


__all__ = [
    "ArcLookup",
    "arc_lookup_from_repository",
    "arc_lookup_from_snapshot",
    "capture_repository_arcs",
    "arc_lookup_from_submatrix",
    "authoritative_arc_lookup",
    "matrix_provenance_of",
]
