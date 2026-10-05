"""C2: where the certificate's authoritative arcs come from, and the endpoint wiring.

Companion to ``test_certifier_authoritative_matrix.py`` (which covers the
re-costing semantics with an injected lookup).
"""

import os

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

import pytest

from routers import optimization
from test_certifier_authoritative_matrix import (
    TRUE_ARC,
    _arcs,
    _request,
    _response,
)
from utils.matrix_repository import (
    IncompleteTravelMatrixError,
    MatrixSnapshotError,
    TimeMatrixRepository,
)
from verification.authoritative_arcs import (
    arc_lookup_from_repository,
    arc_lookup_from_snapshot,
    authoritative_arc_lookup,
)


def test_snapshot_lookup_serves_only_the_bound_arcs():
    snapshot = {
        "arcs": [
            {"origin_code": "D", "destination_code": "L1", "duration_minutes": 7.5},
            {"origin_code": "L1", "destination_code": "D", "duration_minutes": 9.0},
        ]
    }
    lookup = arc_lookup_from_snapshot(snapshot)
    assert lookup("D", "L1") == 7.5
    assert lookup("L1", "D") == 9.0  # directed
    assert lookup("L1", "L1") == 0.0
    with pytest.raises(IncompleteTravelMatrixError):
        lookup("D", "L2")


def test_repository_lookup_wraps_the_directed_arc_accessor():
    class _Provider:
        def fetch_rows(self):
            return [
                {"origin_code": a, "destination_code": b, "duration_minutes": d}
                for a, b, d in [("A", "B", 5), ("B", "A", 6.25)]
            ]

    repository = TimeMatrixRepository(provider=_Provider(), ttl_seconds=600)
    repository.load()
    lookup = arc_lookup_from_repository(repository)
    assert lookup("A", "B") == 5.0
    assert lookup("B", "A") == 6.25
    with pytest.raises(IncompleteTravelMatrixError):
        lookup("A", "Z")


def test_repository_lookup_refuses_coordinate_fallback():
    repository = TimeMatrixRepository(provider=None)
    repository.load()  # no provider: coordinate mode, not authoritative
    with pytest.raises(MatrixSnapshotError):
        arc_lookup_from_repository(repository)("A", "B")


def test_no_authoritative_matrix_means_no_lookup():
    class _BrokenLoader:
        @staticmethod
        def get_instance():
            raise RuntimeError("no loader")

    assert authoritative_arc_lookup(None, _BrokenLoader) is None


DIGEST = "a" * 64


class _StubStrategy:
    name = "stub"
    display_name = "Stub"
    description = "claims a fixed response"

    def __init__(self, response):
        self.response = response

    def optimize(self, request):
        return self.response.model_copy(deep=True)


def _install_stub(monkeypatch, response):
    strategy = _StubStrategy(response)
    resolution = optimization.ResolvedStrategy(
        "stub", "stub", lambda: strategy, ("stub",)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(
        optimization, "resolve_unique_strategies", lambda keys: [resolution]
    )


class _SnapshotLoader:
    """DataLoader stand-in whose repository serves one bound snapshot."""

    def __init__(self, arcs):
        codes = list(arcs)
        self.snapshot = {
            "id": f"time_matrix:sha256:{DIGEST}",
            "version": DIGEST,
            "sha256": DIGEST,
            "source": "supabase",
            "arcs": [
                {"origin_code": a, "destination_code": b, "duration_minutes": arcs[a][b]}
                for a in codes
                for b in codes
                if a != b
            ],
        }
        self.repository = self

    def get_instance(self):
        return self

    def refresh(self, force=False):
        return None

    def matrix_snapshot(self, student_locations, depot_code):
        return self.snapshot


def test_optimize_endpoint_rejects_zero_duration_claim_on_bound_snapshot(monkeypatch):
    """C2(a) end to end: a bound request is certified on the snapshot arcs."""
    monkeypatch.setattr(optimization, "DataLoader", _SnapshotLoader(_arcs()))
    _install_stub(monkeypatch, _response(["D", "L1", "L2", "D"], [0.0, 0.0, 0.0]))

    result = optimization.optimize_route(_request(2, expected_matrix_sha256=DIGEST))

    assert result.success is False
    assert result.feasibility_certificate.is_feasible is False
    types = {v.type for v in result.feasibility_certificate.violations}
    assert "arc_duration_mismatch" in types


def test_optimize_endpoint_accepts_matching_claim_on_bound_snapshot(monkeypatch):
    monkeypatch.setattr(optimization, "DataLoader", _SnapshotLoader(_arcs()))
    _install_stub(monkeypatch, _response(["D", "L1", "L2", "D"], [TRUE_ARC] * 3))

    result = optimization.optimize_route(_request(2, expected_matrix_sha256=DIGEST))

    assert result.feasibility_certificate.is_feasible is True, (
        result.feasibility_certificate.violations
    )
    assert result.success is True


def test_optimize_endpoint_fails_closed_without_an_authoritative_matrix(monkeypatch):
    """Unbound request and a DataLoader with no loaded matrix: never certify."""

    class _CoordinateOnly:
        repository = TimeMatrixRepository(provider=None)

        @classmethod
        def get_instance(cls):
            return cls

        @classmethod
        def refresh(cls, force=False):
            return None

    _CoordinateOnly.repository.load()
    monkeypatch.setattr(optimization, "DataLoader", _CoordinateOnly)
    _install_stub(monkeypatch, _response(["D", "L1", "L2", "D"], [0.0, 0.0, 0.0]))

    result = optimization.optimize_route(_request(2))

    assert result.success is False
    assert result.feasibility_certificate.is_feasible is False


# -- real repository, real strategies, decimal asymmetric arcs ------------------


class _RepositoryLoader:
    """The DataLoader contract over a real ``TimeMatrixRepository``."""

    def __init__(self, repository):
        self.repository = repository

    def get_instance(self):
        return self

    def refresh(self, force=False):
        self.repository.refresh(force)

    def get_submatrix(self, request_locations, coordinates=None, **_kwargs):
        return self.repository.get_submatrix(request_locations, coordinates)


def _decimal_repository():
    codes = ["D", "L1", "L2", "L3", "L4", "L5"]
    rows = []
    for i, a in enumerate(codes):
        for j, b in enumerate(codes):
            if a != b:
                # directed, non-integer, not representable at 1 decimal
                rows.append(
                    {
                        "origin_code": a,
                        "destination_code": b,
                        "duration_minutes": 3.0
                        + 0.137 * i
                        + 0.291 * j
                        + (0.043 if i > j else 0),
                    }
                )

    class _Provider:
        def fetch_rows(self):
            return rows

    repository = TimeMatrixRepository(provider=_Provider(), ttl_seconds=600)
    repository.load()
    return repository


@pytest.mark.parametrize(
    "key",
    [
        "ga",
        "pso",
        "gwo",
        "hho",
        "ga_split",
        "pso_split",
        "gwo_split",
        "hho_split",
        "two_opt",
        "greedy",
        "permutation_tsp",
        "ortools_cvrp",
    ],
)
def test_operational_strategies_certify_on_a_real_decimal_directed_matrix(
    monkeypatch, key
):
    """Every operational strategy reports the matrix arcs the certificate re-costs."""
    pytest.importorskip("ortools")
    loader = _RepositoryLoader(_decimal_repository())
    monkeypatch.setattr(
        "utils.data_loader.DataLoader.get_instance", staticmethod(lambda: loader)
    )
    request = _request(5, algorithm=key, max_travel_time=120)

    result = optimization.optimize_route(request)

    assert result.success is True, (key, result.error_message)
    assert result.feasibility_certificate.is_feasible is True, (
        key,
        result.feasibility_certificate.violations,
    )
    lookup = arc_lookup_from_repository(loader.repository)
    for route in result.routes:
        for step in route.route_details:
            expected = lookup(step.location1, step.location2)
            assert step.duration == pytest.approx(expected, abs=0.005), (key, step)
