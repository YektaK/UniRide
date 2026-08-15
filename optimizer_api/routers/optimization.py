import time
import json
import logging
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException

try:
    from optimizer_api.auth import require_tenant_authorization
    from optimizer_api.rate_limit import require_rate_limit
except ModuleNotFoundError:  # direct-module compatibility
    from auth import require_tenant_authorization
    from rate_limit import require_rate_limit

try:
    from optimizer_api.compute_policy import (
        DEFAULT_COMPARE_ALGORITHMS,
        PolicyValidationError,
        apply_compute_policy,
        load_compute_policy,
    )
    from optimizer_api.strategies.canonical import (
        ResolvedStrategy,
        StrategyRegistryContractError,
        StrategyUnavailableError,
        UnknownStrategyError,
        resolve_strategy,
        resolve_unique_strategies,
    )
except ModuleNotFoundError:  # direct-module compatibility
    from compute_policy import (
        DEFAULT_COMPARE_ALGORITHMS,
        PolicyValidationError,
        apply_compute_policy,
        load_compute_policy,
    )
    from strategies.canonical import (
        ResolvedStrategy,
        StrategyRegistryContractError,
        StrategyUnavailableError,
        UnknownStrategyError,
        resolve_strategy,
        resolve_unique_strategies,
    )

from models.schemas import (
    OptimizationRequest, OptimizationResponse,
    CompareRequest, CompareResponse, AlgorithmResult,
    IEResponseData, BottleneckInfo,
    TimeShiftSuggestion, FeasibilityCertificateInfo,
    AppliedComputePolicyInfo,
)
from utils.resource_profiler import ResourceProfiler
from utils.scheduling import calculate_scheduled_times
from verification.response_certifier import certify_optimization_response

router = APIRouter(
    prefix="/api/v1",
    tags=["Optimization"],
    dependencies=[Depends(require_tenant_authorization), Depends(require_rate_limit)],
)
logger = logging.getLogger(__name__)
_INVALID_CERTIFICATE_ERROR = "certification aborted: invalid certificate payload"
_UNAVAILABLE_CERTIFICATE_ERROR = "certification unavailable: algorithm produced no result"
_EXACT_OPTIMAL_LIMIT = 10


def _is_oversize_exact_request(resolution: ResolvedStrategy, request) -> bool:
    """True when an exact/permutation request exceeds the safe search limit.

    Exact search is factorial; the production cutoff is ``_EXACT_OPTIMAL_LIMIT``
    waypoints. Oversized requests must fail before the solver method is invoked.
    """
    return (
        resolution.canonical == "permutation_tsp"
        and len(request.students) > _EXACT_OPTIMAL_LIMIT
    )


def _typed_certificate(payload: dict | None) -> FeasibilityCertificateInfo:
    if payload is not None:
        try:
            return FeasibilityCertificateInfo.model_validate(payload)
        except Exception:
            logger.exception("Invalid feasibility certificate payload")
    return FeasibilityCertificateInfo(
        is_feasible=False,
        violation_count=0,
        violations=[],
        certify_error=(
            _INVALID_CERTIFICATE_ERROR
            if payload is not None
            else _UNAVAILABLE_CERTIFICATE_ERROR
        ),
    )

def _failure_json(certificate: FeasibilityCertificateInfo) -> str:
    return json.dumps(certificate.model_dump(exclude_none=True))


def _optimization_failure(
    resolution: ResolvedStrategy,
    applied_policy: AppliedComputePolicyInfo,
    execution_time: float,
) -> OptimizationResponse:
    typed_certificate = _typed_certificate(None)
    return OptimizationResponse(
        algorithm_used=resolution.canonical,
        algorithm_requested=resolution.requested,
        applied_policy=applied_policy.model_dump(),
        success=False,
        routes=[],
        execution_time_seconds=round(execution_time, 4),
        error_message=_failure_json(typed_certificate),
        feasibility_certificate=typed_certificate,
    )

@router.post("/optimize", response_model=OptimizationResponse)
def optimize_route(request: OptimizationRequest) -> OptimizationResponse:
    try:
        resolution = resolve_strategy(request.algorithm)
        strategy = resolution.create()
    except (
        UnknownStrategyError,
        StrategyUnavailableError,
        StrategyRegistryContractError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        request, applied_policy = apply_compute_policy(
            request, resolution, strategy, load_compute_policy()
        )
    except PolicyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    if _is_oversize_exact_request(resolution, request):
        return _optimization_failure(resolution, applied_policy, 0.0)

    start_time = time.time()
    try:
        time_windows = {}
        if request.use_time_windows:
            time_windows = request.get_time_windows()
        
        result = strategy.optimize(request)
        execution_time = time.time() - start_time
        if result is None:
            typed_certificate = _typed_certificate(None)
            return OptimizationResponse(
                algorithm_used=resolution.canonical,
                algorithm_requested=resolution.requested,
                applied_policy=applied_policy.model_dump(),
                success=False,
                routes=[],
                execution_time_seconds=round(execution_time, 4),
                error_message=json.dumps(typed_certificate.model_dump(exclude_none=True)),
                feasibility_certificate=typed_certificate,
            )
        result = OptimizationResponse.model_validate(result.model_dump())
        result.algorithm_used = resolution.canonical
        result.algorithm_requested = resolution.requested
        result.applied_policy = AppliedComputePolicyInfo.model_validate(
            applied_policy.model_dump()
        )
        original_result_success = result.success
        result.execution_time_seconds = round(execution_time, 4)
        
        result.direction = request.direction
        result.time_windows_used = request.use_time_windows and len(time_windows) > 0
        
        if request.use_time_windows and result.success:
            distance_matrix = {}
            for route in result.routes:
                for step in route.route_details:
                    if step.location1 not in distance_matrix:
                        distance_matrix[step.location1] = {}
                    distance_matrix[step.location1][step.location2] = step.duration
            result.routes = calculate_scheduled_times(result.routes, request, distance_matrix)

        typed_certificate = _typed_certificate(
            certify_optimization_response(request, result)
        )
        result.feasibility_certificate = typed_certificate
        result.success = bool(original_result_success and typed_certificate.is_feasible)
        if not result.success:
            result.error_message = json.dumps(
                typed_certificate.model_dump(exclude_none=True)
            )

        if result.success:
            profiler = ResourceProfiler(
                standard_sw_capacity=request.sw_capacity,
                standard_so_capacity=request.so_capacity,
                max_tour_duration=request.max_travel_time
            )

            students = request.students
            sw_count = sum(1 for s in students if s.disability_type == 'Sw')
            so_count = len(students) - sw_count

            standard_needs = profiler.calculate_standard_vehicle_needs(students, mode=request.direction.value)
            hourly_demand_raw = profiler.generate_hourly_demand(students)

            hourly_demand = {
                hour: {
                    'pickup': { 'Sw': d.pickup_sw, 'So': d.pickup_so },
                    'dropoff': { 'Sw': d.dropoff_sw, 'So': d.dropoff_so }
                }
                for hour, d in hourly_demand_raw.items()
            }

            available_vehicles = request.vehicles if request.vehicles else []
            bottlenecks_raw = profiler.identify_bottlenecks(
                hourly_demand_raw, available_vehicles, mode=request.direction.value
            )

            bottlenecks = [
                BottleneckInfo(
                    time=b.hour, type=b.type, reason=b.description, affected_students=None
                ) for b in bottlenecks_raw
            ]

            bottleneck_hours = [b.hour for b in bottlenecks_raw if b.severity in ['high', 'medium']]
            shift_suggestions_raw = profiler.suggest_time_shifts(
                hourly_demand_raw, bottleneck_hours, slack_window_minutes=request.slack_window_minutes
            )

            time_shift_suggestions = [
                TimeShiftSuggestion(
                    student_id=s.student_id, current_time=s.current_time,
                    suggested_time=s.suggested_time, savings_vehicles=float(s.savings_vehicles)
                ) for s in shift_suggestions_raw
            ]

            result.ie_data = IEResponseData(
                standard_vehicles_needed=standard_needs.get('standard_vehicles_needed', 0),
                hourly_demand=hourly_demand, bottlenecks=bottlenecks,
                time_shift_suggestions=time_shift_suggestions
            )

        return result

    except Exception:
        logger.exception("Optimization endpoint failed")
        return _optimization_failure(
            resolution, applied_policy, time.time() - start_time
        )

def _algorithm_failure(
    resolution: ResolvedStrategy,
    applied_policy: AppliedComputePolicyInfo,
    execution_time: float = 0.0,
    *,
    soft_deadline: bool = False,
) -> AlgorithmResult:
    typed_certificate = _typed_certificate(None)
    if soft_deadline:
        applied_policy = applied_policy.model_copy(
            update={"cancellation_mode": "soft_response_deadline"}
        )
    return AlgorithmResult(
        algorithm=resolution.canonical,
        algorithm_requested=resolution.requested,
        applied_policy=applied_policy.model_dump(),
        success=False,
        total_vehicles=0,
        total_duration_minutes=0,
        execution_time_seconds=round(execution_time, 4),
        routes=[],
        error_message=_failure_json(typed_certificate),
        feasibility_certificate=typed_certificate,
    )


@dataclass(frozen=True)
class PreparedComparisonRun:
    resolution: ResolvedStrategy
    strategy: object
    request: OptimizationRequest
    applied_policy: AppliedComputePolicyInfo


def _prepare_comparison_run(
    resolution: ResolvedStrategy,
    request: OptimizationRequest,
    policy,
) -> PreparedComparisonRun:
    strategy = resolution.create()
    effective_request, applied_policy = apply_compute_policy(
        request, resolution, strategy, policy
    )
    return PreparedComparisonRun(
        resolution=resolution,
        strategy=strategy,
        request=effective_request,
        applied_policy=AppliedComputePolicyInfo.model_validate(
            applied_policy.model_dump()
        ),
    )


def _run_single_algorithm(
    prepared: PreparedComparisonRun,
) -> AlgorithmResult:
    resolution = prepared.resolution
    strategy = prepared.strategy
    effective_request = prepared.request
    applied_policy = prepared.applied_policy

    start_time = time.time()
    try:
        if _is_oversize_exact_request(resolution, effective_request):
            return _algorithm_failure(resolution, applied_policy, 0.0)

        response = strategy.optimize(effective_request)
        execution_time = time.time() - start_time
        if response is None:
            return _algorithm_failure(resolution, applied_policy, execution_time)
        response = OptimizationResponse.model_validate(response.model_dump())
        original_success = response.success
        typed_certificate = _typed_certificate(
            certify_optimization_response(effective_request, response)
        )
        success = bool(original_success and typed_certificate.is_feasible)
        return AlgorithmResult(
            algorithm=resolution.canonical,
            algorithm_requested=resolution.requested,
            applied_policy=applied_policy.model_dump(),
            success=success,
            total_vehicles=response.total_vehicles,
            total_duration_minutes=response.total_duration_minutes,
            execution_time_seconds=round(execution_time, 4),
            routes=response.routes,
            error_message=(
                response.error_message
                if success
                else _failure_json(typed_certificate)
            ),
            feasibility_certificate=typed_certificate,
        )
    except Exception:
        logger.exception("Algorithm %s failed during compare", resolution.canonical)
        return _algorithm_failure(
            resolution, applied_policy, time.time() - start_time
        )


def _compare_optimization_request(
    request: CompareRequest,
    algorithm: str,
) -> OptimizationRequest:
    payload = request.model_dump()
    payload["algorithm"] = algorithm
    return OptimizationRequest.model_validate(payload)


def _comparison_metadata(
    policy,
    request: CompareRequest,
) -> AppliedComputePolicyInfo:
    return AppliedComputePolicyInfo(
        profile_id=policy.profile_id,
        student_count=len(request.students),
        vehicle_count=0,
        cancellation_mode="soft_response_deadline",
        limits={},
    )


@router.post("/compare", response_model=CompareResponse)
def compare_algorithms(request: CompareRequest) -> CompareResponse:
    explicit = request.algorithms is not None
    if explicit and not request.algorithms:
        raise HTTPException(status_code=400, detail="No algorithms specified")

    keys = tuple(request.algorithms) if explicit else DEFAULT_COMPARE_ALGORITHMS
    try:
        resolutions = resolve_unique_strategies(keys)
    except (
        UnknownStrategyError,
        StrategyUnavailableError,
        StrategyRegistryContractError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    policy = load_compute_policy()
    if len(resolutions) > policy.max_algorithms:
        raise HTTPException(
            status_code=422,
            detail=f"canonical algorithms cannot exceed {policy.max_algorithms}",
        )
    if not resolutions:
        raise HTTPException(status_code=400, detail="No valid algorithms specified")

    opt_request = _compare_optimization_request(request, resolutions[0].requested)
    prepared_runs = []
    try:
        for resolution in resolutions:
            prepared_runs.append(
                _prepare_comparison_run(resolution, opt_request, policy)
            )
    except (
        StrategyUnavailableError,
        StrategyRegistryContractError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except PolicyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    results_by_canonical = {}
    runnable_runs = []
    for prepared in prepared_runs:
        resolution = prepared.resolution
        if _is_oversize_exact_request(resolution, prepared.request):
            results_by_canonical[resolution.canonical] = _algorithm_failure(
                resolution, prepared.applied_policy
            )
        else:
            runnable_runs.append(prepared)

    executor = None
    future_by_canonical = {}
    pending = set()
    try:
        if runnable_runs:
            executor = ThreadPoolExecutor(
                max_workers=min(policy.max_workers, len(runnable_runs))
            )
        for prepared in runnable_runs:
            future = executor.submit(
                _run_single_algorithm,
                prepared,
            )
            future_by_canonical[prepared.resolution.canonical] = future
            pending.add(future)
        done = set()
        if pending:
            done, pending = wait(
                pending,
                timeout=policy.deadline_seconds,
                return_when=ALL_COMPLETED,
            )
        for prepared in runnable_runs:
            resolution = prepared.resolution
            future = future_by_canonical[resolution.canonical]
            if future in done:
                try:
                    result = future.result()
                except Exception:
                    logger.exception(
                        "Algorithm %s future failed", resolution.canonical
                    )
                    result = _algorithm_failure(
                        resolution, prepared.applied_policy
                    )
            else:
                result = _algorithm_failure(
                    resolution,
                    prepared.applied_policy,
                    soft_deadline=True,
                )
            results_by_canonical[resolution.canonical] = result
        results = [results_by_canonical[item.canonical] for item in resolutions]
    finally:
        for future in pending:
            future.cancel()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    eligible = [
        result
        for result in results
        if result.success
        and result.feasibility_certificate is not None
        and result.feasibility_certificate.is_feasible
    ]
    best = min(
        eligible,
        key=lambda result: (
            result.total_duration_minutes,
            result.total_vehicles,
            result.algorithm,
        ),
        default=None,
    )
    fastest = min(
        eligible,
        key=lambda result: (result.execution_time_seconds, result.algorithm),
        default=None,
    )
    summary = {
        result.algorithm: {
            "total_vehicles": result.total_vehicles,
            "total_duration_minutes": round(result.total_duration_minutes, 2),
            "execution_time_seconds": round(result.execution_time_seconds, 4),
            "success": result.success,
        }
        for result in results
    }
    return CompareResponse(
        success=bool(eligible),
        results=results,
        best_algorithm=best.algorithm if best else "",
        fastest_algorithm=fastest.algorithm if fastest else "",
        summary=summary,
        applied_policy=_comparison_metadata(policy, request),
    )


@router.post("/vehicle-calculator", response_model=OptimizationResponse)
def calculate_vehicles(request: OptimizationRequest) -> OptimizationResponse:
    return optimize_route(request)
