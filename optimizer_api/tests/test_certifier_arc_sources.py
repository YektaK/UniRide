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


class _CountingStrategy(_StubStrategy):
    def __init__(self, response):
        super().__init__(response)
        self.calls = 0

    def optimize(self, request):
        self.calls += 1
        return super().optimize(request)


def _install_counting_stub(monkeypatch):
    strategy = _CountingStrategy(_response(["D", "L1", "L2", "D"], [0.0, 0.0, 0.0]))
    resolution = optimization.ResolvedStrategy(
        "stub", "stub", lambda: strategy, ("stub",)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(
        optimization, "resolve_unique_strategies", lambda keys: [resolution]
    )
    return strategy


def _loader_for(repository):
    class _Loader:
        @classmethod
        def get_instance(cls):
            return cls

        @classmethod
        def refresh(cls, force=False):
            return None

    _Loader.repository = repository
    return _Loader


def _coordinate_only_repository(allow_coordinate_fallback=None):
    repository = TimeMatrixRepository(
        provider=None, allow_coordinate_fallback=allow_coordinate_fallback
    )
    repository.load()
    return repository


@pytest.mark.parametrize("opt_in", [None, True])
def test_unbound_optimize_503_before_solving_without_an_authoritative_matrix(
    monkeypatch, opt_in
):
    """Ordering: the arcs are captured BEFORE the solve, so an unavailable
    matrix is a redacted 503 and the strategy never runs. The coordinate-fallback
    opt-in does not make coordinate values authoritative for the certificate."""
    from fastapi import HTTPException

    monkeypatch.setattr(
        optimization, "DataLoader", _loader_for(_coordinate_only_repository(opt_in))
    )
    strategy = _install_counting_stub(monkeypatch)

    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(_request(2))

    assert caught.value.status_code == 503
    assert caught.value.detail == optimization.MATRIX_UNAVAILABLE_DETAIL
    assert strategy.calls == 0


def test_unbound_optimize_422_before_solving_for_unknown_locations(monkeypatch):
    from fastapi import HTTPException

    repository = _decimal_repository()  # knows D, L1..L5 only
    monkeypatch.setattr(optimization, "DataLoader", _loader_for(repository))
    strategy = _install_counting_stub(monkeypatch)
    request = _request(2)
    request.students[0].location_code = "NOT_IN_MATRIX"

    with pytest.raises(HTTPException) as caught:
        optimization.optimize_route(request)

    assert caught.value.status_code == 422
    assert strategy.calls == 0


def test_bound_optimize_keeps_the_200_binding_failure_when_the_snapshot_is_gone(
    monkeypatch,
):
    from utils.matrix_repository import MatrixSnapshotError

    class _Gone(_SnapshotLoader):
        def matrix_snapshot(self, student_locations, depot_code):
            raise MatrixSnapshotError("gone")

    monkeypatch.setattr(optimization, "DataLoader", _Gone(_arcs()))
    strategy = _install_counting_stub(monkeypatch)

    result = optimization.optimize_route(_request(2, expected_matrix_sha256=DIGEST))

    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._MATRIX_BINDING_ERROR
    assert strategy.calls == 0


def test_compare_503_before_solving_without_an_authoritative_matrix(monkeypatch):
    from fastapi import HTTPException
    from models.schemas import CompareRequest

    monkeypatch.setattr(
        optimization, "DataLoader", _loader_for(_coordinate_only_repository())
    )
    strategy = _install_counting_stub(monkeypatch)
    request = CompareRequest(
        students=_request(2).students,
        depot=_request(2).depot,
        sw_capacity=4,
        so_capacity=5,
        max_travel_time=60,
        algorithms=["stub"],
    )

    with pytest.raises(HTTPException) as caught:
        optimization.compare_algorithms(request)

    assert caught.value.status_code == 503
    assert strategy.calls == 0


# -- public strict repository accessors -----------------------------------------


def test_repository_capture_arcs_is_strict_and_a_copy():
    repository = _decimal_repository()
    arcs = repository.capture_arcs(["D", "L1", "L1", "L2"])

    assert set(arcs) == {
        (a, b) for a in ("D", "L1", "L2") for b in ("D", "L1", "L2") if a != b
    }
    before = arcs[("D", "L1")]
    repository.time_matrix[repository.loc_to_idx["D"]][repository.loc_to_idx["L1"]] = 99.0
    assert arcs[("D", "L1")] == before  # a plain copy
    assert repository.arc("D", "L1") == 99.0
    assert repository.arc("L1", "L1") == 0.0
    with pytest.raises(IncompleteTravelMatrixError) as caught:
        repository.capture_arcs(["D", "NOPE"])
    assert caught.value.unknown_location is True


@pytest.mark.parametrize("opt_in", [None, True])
def test_repository_accessors_never_serve_coordinate_values(opt_in):
    """Not under the dev opt-in and not inside the academic coordinate scope:
    the certificate may only be judged on the stored matrix."""
    from utils.matrix_repository import MatrixUnavailableError, academic_coordinate_scope

    repository = _coordinate_only_repository(opt_in)
    with pytest.raises(MatrixUnavailableError):
        repository.arc("A", "B")
    with pytest.raises(MatrixUnavailableError):
        repository.capture_arcs(["A", "B"])
    with academic_coordinate_scope():
        # the academic metric still works for the TSPLIB runner ...
        coords = {"A": {"lat": 0.0, "lng": 0.0}, "B": {"lat": 3.0, "lng": 4.0}}
        assert repository.get_submatrix(["A", "B"], coords)[0][1] == 5.0
        # ... but never becomes an authoritative arc
        with pytest.raises(MatrixUnavailableError):
            repository.arc("A", "B")
        with pytest.raises(MatrixUnavailableError):
            repository.capture_arcs(["A", "B"])


def test_benchmark_certificate_does_not_use_the_arc_lookup():
    """The academic runner certifies with certify_benchmark_response over the
    problem's own matrix; the lookup (and so the stored matrix) is not involved."""
    import inspect

    from verification import response_certifier

    source = inspect.getsource(response_certifier.certify_benchmark_response)
    assert "arc_lookup" not in source


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


def test_matrix_refresh_during_the_solve_does_not_change_the_certificate_matrix(
    monkeypatch,
):
    """Unbound request: arcs are captured before the solve, not re-read after it."""
    rows = [
        {"origin_code": a, "destination_code": b, "duration_minutes": TRUE_ARC}
        for a in ("D", "L1", "L2")
        for b in ("D", "L1", "L2")
        if a != b
    ]

    class _Provider:
        def fetch_rows(self):
            return [dict(row) for row in rows]

    repository = TimeMatrixRepository(provider=_Provider(), ttl_seconds=600)
    repository.load()
    loader = _RepositoryLoader(repository)
    monkeypatch.setattr(optimization, "DataLoader", loader)

    class _RefreshingStrategy(_StubStrategy):
        def optimize(self, request):
            # the matrix table changes while the solver is running
            for row in rows:
                row["duration_minutes"] = 99.0
            repository.refresh(force=True)
            return super().optimize(request)

    # the response matches the matrix the solve STARTED from
    response = _response(["D", "L1", "L2", "D"], [TRUE_ARC] * 3)
    strategy = _RefreshingStrategy(response)
    resolution = optimization.ResolvedStrategy(
        "stub", "stub", lambda: strategy, ("stub",)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)

    result = optimization.optimize_route(_request(2))

    # the live repository really changed ...
    assert arc_lookup_from_repository(repository)("D", "L1") == 99.0
    # ... but the certificate still judged the captured, pre-solve arcs
    assert result.feasibility_certificate.is_feasible is True, (
        result.feasibility_certificate.violations
    )
    assert result.success is True


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
