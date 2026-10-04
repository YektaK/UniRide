"""Matrix snapshot binding tests for the preview-only optimize contract."""

from dataclasses import dataclass

from compute_policy import ComputePolicy
from models import schemas
from routers import optimization
from strategies.canonical import ResolvedStrategy
from utils.matrix_repository import MatrixSnapshotError


DEPOT = schemas.LocationNode(id="D.Kampus", lat=0.0, lng=0.0)
FEASIBLE = {"is_feasible": True, "violation_count": 0, "violations": []}


@dataclass
class _Strategy:
    name: str = "genetic_algorithm"
    optimize_calls: int = 0

    def optimize(self, request):
        self.optimize_calls += 1
        return schemas.OptimizationResponse(
            algorithm_used="genetic_algorithm",
            success=False,
            routes=[],
        )


class _Repository:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.calls = 0

    def matrix_snapshot(self, student_locations, depot_code):
        self.calls += 1
        snapshot = self.snapshots[min(self.calls - 1, len(self.snapshots) - 1)]
        if isinstance(snapshot, Exception):
            raise snapshot
        return snapshot


class _DataLoader:
    repository = None
    refresh_calls = 0

    @classmethod
    def get_instance(cls):
        return cls

    @classmethod
    def refresh(cls, force=False):
        cls.refresh_calls += 1


def _snapshot(digest):
    return {
        "id": f"time_matrix:sha256:{digest}",
        "version": digest,
        "sha256": digest,
        "source": "supabase",
        "arcs": [],
    }


def _request(digest):
    return schemas.OptimizationRequest(
        algorithm="ga",
        students=[
            schemas.StudentNode(
                id="S1",
                name="S1",
                location_code="H1",
                coordinates={"lat": 1.0, "lng": 1.0},
                disability_type="So",
            )
        ],
        depot=DEPOT,
        expected_matrix_sha256=digest,
    )


def _install(monkeypatch, strategy, repository):
    resolution = ResolvedStrategy(
        "ga", "genetic_algorithm", lambda: strategy, ("ga",)
    )
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())
    monkeypatch.setattr(
        optimization,
        "apply_compute_policy",
        lambda request, actual_resolution, actual_strategy, policy: (
            request.model_copy(deep=True),
            schemas.AppliedComputePolicyInfo(
                profile_id="production-conservative-v1",
                algorithm_requested="ga",
                algorithm_canonical="genetic_algorithm",
                student_count=len(request.students),
                vehicle_count=0,
                cancellation_mode="none",
                limits={},
            ),
        ),
    )
    monkeypatch.setattr(
        optimization, "certify_optimization_response", lambda request, result: FEASIBLE
    )
    _DataLoader.repository = repository
    monkeypatch.setattr(optimization, "DataLoader", _DataLoader)


def test_expected_matrix_hash_mismatch_skips_solver(monkeypatch):
    expected = "a" * 64
    strategy = _Strategy()
    _install(monkeypatch, strategy, _Repository([_snapshot("b" * 64)]))

    result = optimization.optimize_route(_request(expected))

    assert strategy.optimize_calls == 0
    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._MATRIX_BINDING_ERROR


def test_matrix_change_after_solver_invalidates_result(monkeypatch):
    expected = "a" * 64
    strategy = _Strategy()
    repository = _Repository([_snapshot(expected), _snapshot("b" * 64)])
    _install(monkeypatch, strategy, repository)

    result = optimization.optimize_route(_request(expected))

    assert strategy.optimize_calls == 1
    assert repository.calls == 2
    assert result.success is False
    assert result.feasibility_certificate.certify_error == optimization._MATRIX_BINDING_ERROR


def test_healthy_unchanged_matrix_preserves_existing_call_behavior(monkeypatch):
    expected = "a" * 64
    strategy = _Strategy()
    repository = _Repository([_snapshot(expected), _snapshot(expected)])
    _install(monkeypatch, strategy, repository)

    result = optimization.optimize_route(_request(expected))

    assert strategy.optimize_calls == 1
    assert result.feasibility_certificate.certify_error is None


def test_unhealthy_matrix_fails_closed_before_solver(monkeypatch):
    expected = "a" * 64
    strategy = _Strategy()
    _install(
        monkeypatch,
        strategy,
        _Repository([MatrixSnapshotError("provider secret")]),
    )

    result = optimization.optimize_route(_request(expected))

    assert strategy.optimize_calls == 0
    assert result.feasibility_certificate.certify_error == optimization._MATRIX_BINDING_ERROR
    assert "provider secret" not in (result.error_message or "")
