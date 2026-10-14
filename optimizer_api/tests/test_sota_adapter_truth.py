"""M26 / QW11: SOTA strategies must report which algorithm actually ran.

* A SOTA solver failure keeps serving the greedy order but the response is
  explicitly labelled ``greedy_fallback`` (requested algorithm and a short
  reason code are carried; the exception text never reaches the client).
* The matrix the solver optimises is the depot-anchored directed duration the
  response reports, so the reported cost is the optimised objective.
"""

from __future__ import annotations

import itertools
import json
from types import SimpleNamespace

import pytest

from compute_policy import ComputePolicy
from models import schemas
from routers import optimization
from certifier_matrix_support import stub_arc_capture  # noqa: F401 - fixture
from strategies import aoea_strategy, ebso_strategy, rdma_strategy
from strategies.canonical import ResolvedStrategy

pytestmark = pytest.mark.usefixtures("stub_arc_capture")

SECRET = "secret-internal-detail-7731"
DEPOT = schemas.LocationNode(id="depot", lat=0.0, lng=0.0)
FEASIBLE = {"is_feasible": True, "violation_count": 0, "violations": []}

# Directed, asymmetric durations; the fake "distance" below deliberately
# disagrees with them so a distance-based objective picks a different order.
_DUR = {
    ("depot", "A"): 3.0, ("depot", "B"): 1.0, ("depot", "C"): 4.0,
    ("A", "depot"): 2.0, ("B", "depot"): 9.0, ("C", "depot"): 1.0,
    ("A", "B"): 5.0, ("B", "A"): 1.0,
    ("A", "C"): 1.0, ("C", "A"): 6.0,
    ("B", "C"): 2.0, ("C", "B"): 7.0,
}
_NODES = ("depot", "A", "B", "C")

STRATEGIES = [
    (ebso_strategy, ebso_strategy.E2BSoStrategy, "E2BSO_TSP", "e2bso"),
    (rdma_strategy, rdma_strategy.R2DMAStrategy, "R2DMA_TSP", "r2dma"),
    (aoea_strategy, aoea_strategy.PAOEAStrategy, "PAOEA_TSP", "paoea"),
]


def _students():
    return [
        schemas.StudentNode(
            id=f"s{code}", name=code, location_code=code,
            coordinates={"lat": 0.0, "lng": float(i)}, disability_type="So",
        )
        for i, code in enumerate("ABC", start=1)
    ]


def _request(algorithm):
    return schemas.OptimizationRequest(algorithm=algorithm, students=_students(), depot=DEPOT)


def _context(*_args, **_kwargs):
    return {
        "coordinates": {n: {"lat": 0.0, "lng": 0.0} for n in _NODES},
        "time_matrix": {a: {b: _DUR.get((a, b), 0.0) for b in _NODES} for a in _NODES},
        "student_ids": ["A", "B", "C"],
        "distance_lookup": lambda a, b: 0.0 if a == b else float(abs(ord(a[0]) - ord(b[0]))) + 1.0,
    }


class _FailingSolver:
    def __init__(self, config):
        pass

    def solve_with_matrix(self, matrix):
        raise RuntimeError(SECRET)


class _BruteForceSolver:
    def __init__(self, config):
        pass

    def solve_with_matrix(self, matrix):
        n = len(matrix)

        def cost(tour):
            return sum(matrix[tour[i]][tour[(i + 1) % n]] for i in range(n))

        best = min(([0, *p] for p in itertools.permutations(range(1, n))), key=cost)
        return SimpleNamespace(tour=best)


def _cycle_cost(order):
    path = ["depot", *order, "depot"]
    return sum(_DUR[(a, b)] for a, b in zip(path, path[1:]))


@pytest.mark.parametrize("module,cls,solver_attr,name", STRATEGIES)
def test_solver_failure_is_labelled_greedy_fallback_without_leaking(
    monkeypatch, module, cls, solver_attr, name
):
    monkeypatch.setattr(module, "build_sota_request_context", _context)
    monkeypatch.setattr(module, solver_attr, _FailingSolver)

    response = cls().optimize(_request(name))

    assert response.success is True
    assert response.algorithm_used == "greedy_fallback"
    assert response.fallback_reason == "solver_error"
    assert response.routes and response.routes[0].student_ids
    assert SECRET not in response.model_dump_json()


@pytest.mark.parametrize("module,cls,solver_attr,name", STRATEGIES)
def test_successful_run_keeps_algorithm_name_and_omits_fallback_field(
    monkeypatch, module, cls, solver_attr, name
):
    monkeypatch.setattr(module, "build_sota_request_context", _context)
    monkeypatch.setattr(module, solver_attr, _BruteForceSolver)

    response = cls().optimize(_request(name))

    assert response.algorithm_used == name
    assert response.fallback_reason is None
    assert "fallback_reason" not in json.loads(response.model_dump_json())


@pytest.mark.parametrize("module,cls,solver_attr,name", STRATEGIES)
def test_optimised_objective_equals_reported_duration(
    monkeypatch, module, cls, solver_attr, name
):
    monkeypatch.setattr(module, "build_sota_request_context", _context)
    monkeypatch.setattr(module, solver_attr, _BruteForceSolver)

    response = cls().optimize(_request(name))

    best = min(itertools.permutations("ABC"), key=lambda o: _cycle_cost(list(o)))
    assert response.total_duration_minutes == pytest.approx(_cycle_cost(list(best)))
    assert response.routes[0].student_ids == list(best)


def _metadata(requested, canonical):
    return schemas.AppliedComputePolicyInfo(
        profile_id="production-conservative-v1", algorithm_requested=requested,
        algorithm_canonical=canonical, student_count=0, vehicle_count=0,
        cancellation_mode="none", limits={},
    )


def _install_router(monkeypatch, strategy, requested, canonical):
    resolution = ResolvedStrategy(requested, canonical, lambda: strategy, (requested,))
    monkeypatch.setattr(optimization, "resolve_strategy", lambda key: resolution)
    monkeypatch.setattr(optimization, "load_compute_policy", lambda: ComputePolicy())
    monkeypatch.setattr(
        optimization, "apply_compute_policy",
        lambda request, res, strat, policy: (
            request.model_copy(deep=True), _metadata(requested, canonical)
        ),
    )
    monkeypatch.setattr(
        optimization, "certify_optimization_response",
        lambda request, result, arc_lookup=None: FEASIBLE,
    )
    return resolution


class _Fixed:
    def __init__(self, response):
        self.response = response
        self.name = "e2bso"

    def optimize(self, request):
        return self.response


def _fallback_response():
    return schemas.OptimizationResponse(
        algorithm_used="greedy_fallback", fallback_reason="solver_error",
        success=True, routes=[],
    )


def test_optimize_endpoint_does_not_relabel_a_fallback_as_the_requested_algorithm(monkeypatch):
    _install_router(monkeypatch, _Fixed(_fallback_response()), "e2bso", "e2bso")

    result = optimization.optimize_route(
        schemas.OptimizationRequest(algorithm="e2bso", students=[], depot=DEPOT)
    )

    assert result.algorithm_used == "greedy_fallback"
    assert result.algorithm_requested == "e2bso"
    assert result.fallback_reason == "solver_error"


def test_optimize_endpoint_still_relabels_normal_responses_to_canonical(monkeypatch):
    normal = schemas.OptimizationResponse(algorithm_used="whatever", success=True, routes=[])
    _install_router(monkeypatch, _Fixed(normal), "e2bso", "e2bso")

    result = optimization.optimize_route(
        schemas.OptimizationRequest(algorithm="e2bso", students=[], depot=DEPOT)
    )

    assert result.algorithm_used == "e2bso"
    assert result.fallback_reason is None


def test_compare_marks_fallback_result_and_excludes_it_from_best(monkeypatch):
    resolution = _install_router(monkeypatch, _Fixed(_fallback_response()), "e2bso", "e2bso")
    monkeypatch.setattr(optimization, "authoritative_arc_lookup", lambda *a, **k: None)
    prepared = optimization.PreparedComparisonRun(
        resolution=resolution,
        strategy=_Fixed(_fallback_response()),
        request=schemas.OptimizationRequest(algorithm="e2bso", students=[], depot=DEPOT),
        applied_policy=_metadata("e2bso", "e2bso"),
    )

    result = optimization._run_single_algorithm(prepared)

    assert result.algorithm == "e2bso"
    assert result.algorithm_executed == "greedy_fallback"
    assert result.fallback_reason == "solver_error"


def test_compare_best_and_fastest_ignore_a_fallback_result(monkeypatch):
    from compute_policy import DEFAULT_COMPARE_ALGORITHMS  # noqa: F401
    import test_package_b_compare_orchestration as compare_support

    resolutions = [compare_support._resolution("e2bso"), compare_support._resolution("ga")]
    compare_support._install_resolutions(monkeypatch, resolutions)
    compare_support._install_policy(monkeypatch)

    def run(prepared):
        name = prepared.resolution.canonical
        if name == "e2bso":
            return schemas.AlgorithmResult(
                algorithm="e2bso", algorithm_requested="e2bso", success=True,
                total_vehicles=1, total_duration_minutes=1.0,
                execution_time_seconds=0.1, routes=[],
                feasibility_certificate=compare_support.CERTIFIED,
                applied_policy=_metadata("e2bso", "e2bso"),
                algorithm_executed="greedy_fallback", fallback_reason="solver_error",
            )
        return compare_support._result("ga", duration=50.0, seconds=9.0)

    monkeypatch.setattr(optimization, "_run_single_algorithm", run)

    response = optimization.compare_algorithms(compare_support._request(["e2bso", "ga"]))

    assert response.best_algorithm == "ga"
    assert response.fastest_algorithm == "ga"
