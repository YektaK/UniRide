import logging
from academic_benchmark.engine_core import AlgorithmRegistry

logger = logging.getLogger(__name__)
from uniride_core.algorithms.numba_strategies import STRATEGIES
from uniride_core.algorithms.local_search_numba import LocalSearchType
from uniride_core.algorithms.registry import list_algorithm_names
from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.sota_tsp.base_solver import BaseTSPSolver
from uniride_core.algorithms.engine_factory import FCM_TSP_SOLVERS, MATRIX_LEGACY_TSP_SOLVERS, create_matrix_engine
from academic_benchmark.core.reported_cost import report_cycle_cost
import importlib


def _is_routing_problem(problem) -> bool:
    return str(getattr(problem, "problem_type", "tsp") or "tsp").lower() in {
        "cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"
    }


class CoreRoutingRefusedError(ValueError):
    """A capability-catalog ID (TSP/ATSP claim) was handed a CVRP/CVRPTW problem."""


# Catalog ID -> the CVRP-*/CVRPTW-* alias base that keeps the legacy matrix engine this ID
# used to delegate to on routing problems. IDs without an entry have no routing alternative
# (their old routing branch ran the greedy router under a Core-* label, or never existed).
# The table is checked against the registered aliases at the end of this module.
_ROUTING_ALTERNATIVE_BASES = {
    "Core-TwoOpt-TSP": "Core-TwoOpt-TSP",
    "Core-GA-TSP": "Core-GA-TSP",
    "Core-GA-TSP-Memetic-2opt": "Core-GA-TSP",
    "Core-PSO-TSP": "Core-PSO-TSP",
    "Core-GWO-TSP-Pure": "Core-GWO-TSP",
    "Core-GWO-TSP-Memetic-2opt": "Core-GWO-TSP",
    "Core-HHO-TSP-Pure": "Core-HHO-TSP",
    "Core-HHO-TSP-Memetic-2opt": "Core-HHO-TSP",
}


def _refuse_routing(canonical_id, problem):
    problem_type = str(getattr(problem, "problem_type", "tsp") or "tsp").lower()
    base = _ROUTING_ALTERNATIVE_BASES.get(canonical_id)
    if base is None:
        advice = "no CVRP-/CVRPTW- alternative exists for this ID."
    else:
        advice = (
            f"use the legacy routing names CVRP-{base} (CVRP) or CVRPTW-{base} (CVRPTW) instead."
        )
    raise CoreRoutingRefusedError(
        f"{canonical_id} is a TSP/ATSP algorithm and refuses {problem_type.upper()} routing "
        f"problems before any evaluation; {advice}"
    )


def _register_catalog_executor(canonical_id, executor):
    """Register a capability-catalog executor behind the routing refusal (all paths)."""
    import functools

    @functools.wraps(executor)
    def guarded(problem, params, seed, run_idx):
        if _is_routing_problem(problem):
            _refuse_routing(canonical_id, problem)
        return executor(problem, params, seed, run_idx)

    guarded.refuses_routing = True
    AlgorithmRegistry.register(canonical_id)(guarded)
    return guarded


def _run_core_routing_executor(problem, params, seed, run_idx, algorithm_name, engine_name="Core-Greedy-Routing"):
    import time
    from academic_benchmark.engine_core import RunResult

    routing_problem = MatrixBuilder.to_routing_problem(problem)
    engine = create_matrix_engine(engine_name)
    start_time = time.perf_counter()
    result = engine.solve_problem(routing_problem, config=params, seed=seed)
    elapsed = time.perf_counter() - start_time
    gap = None
    optimal = getattr(problem, "optimal", None)
    if optimal and optimal > 0:
        gap = ((result.objective_cost - optimal) / optimal) * 100
    return RunResult(
        problem=problem.name,
        algorithm=algorithm_name,
        run=run_idx,
        seed=seed,
        dimension=problem.dimension,
        optimal=optimal,
        tour_cost=float(result.objective_cost),
        gap_pct=gap,
        elapsed_sec=elapsed,
        iterations=getattr(result, "iterations", 0),
        tour=result.tour,
        objective_cost=float(result.objective_cost),
        routes=result.routes,
        num_vehicles=result.num_vehicles,
        route_loads=result.route_loads,
        route_costs=result.route_costs,
        capacity_violations=result.capacity_violations,
        tw_violations=result.tw_violations,
        problem_type=routing_problem.problem_type,
        matrix_kind=routing_problem.matrix.kind,
        constraint_profile={
            "capacities": routing_problem.constraints.capacities,
            "depot_index": routing_problem.constraints.depot_index,
        },
    )


def _problem_matrix(problem):
    """Return the explicit matrix backing a TSP/ATSP academic problem."""
    if getattr(problem, "is_time_matrix", False) and getattr(problem, "time_matrix", None) is not None:
        return problem.time_matrix, "travel_time"
    if getattr(problem, "dist_matrix", None) is not None:
        matrix = problem.dist_matrix
        return matrix.tolist() if hasattr(matrix, "tolist") else matrix, "distance"

    problem.prepare_matrices()
    matrix = problem.dist_matrix
    if matrix is None:
        raise ValueError(f"Problem {problem.name} has no matrix or coordinates")
    return matrix.tolist() if hasattr(matrix, "tolist") else matrix, "distance"


def _route_cost(route, matrix):
    if not route:
        return 0.0
    indices = [int(location[1:]) - 1 if isinstance(location, str) and location.startswith("L") else int(location) for location in route]
    total = 0.0
    for idx, current in enumerate(indices):
        nxt = indices[(idx + 1) % len(indices)]
        total += float(matrix[current][nxt])
    return total


def _make_core_tsp_executor(algorithm_name, solver):
    def executor(problem, params, seed, run_idx):
        import random
        import time
        from academic_benchmark.engine_core import RunResult

        if _is_routing_problem(problem):
            return _run_core_routing_executor(
                problem,
                params,
                seed,
                run_idx,
                algorithm_name,
                engine_name=algorithm_name,
            )

        matrix, matrix_kind = _problem_matrix(problem)
        waypoints = [f"L{i + 1}" for i in range(problem.dimension)]

        def duration_func(route):
            return _route_cost(route, matrix)

        start_time = time.perf_counter()
        route, cost = solver(waypoints, duration_func, random.Random(seed), params)
        elapsed = time.perf_counter() - start_time

        tour_indices = [
            int(location[1:]) if isinstance(location, str) and location.startswith("L") else int(location) + 1
            for location in route
        ]
        optimal = getattr(problem, "optimal", None)
        gap = None
        if optimal and optimal > 0:
            gap = ((cost - optimal) / optimal) * 100

        return RunResult(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=float(cost),
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(params.get("max_iterations", 0) or 0),
            tour=tour_indices,
            objective_cost=float(cost),
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
        )

    return executor


def _make_matrix_tsp_executor(algorithm_name: str):
    def executor(problem, params, seed, run_idx):
        import time
        from academic_benchmark.engine_core import RunResult

        routing_problem = MatrixBuilder.to_routing_problem(problem)
        engine = create_matrix_engine(algorithm_name)
        start_time = time.perf_counter()
        result = engine.solve_problem(routing_problem, config=params, seed=seed)
        elapsed = time.perf_counter() - start_time

        cost = float(getattr(result, "tour_length", getattr(result, "objective_cost", 0.0)))
        optimal = getattr(problem, "optimal", None)
        gap = None
        if optimal and optimal > 0:
            gap = ((cost - optimal) / optimal) * 100

        return RunResult(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=cost,
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(params.get("max_iterations", params.get("iterations", 0)) or 0),
            tour=[int(node) + 1 for node in getattr(result, "tour", [])] if getattr(result, "tour", None) else None,
            objective_cost=cost,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=getattr(routing_problem.matrix, "kind", "distance"),
        )

    return executor


def _run_fair_local_search(problem, params, run_idx, algorithm_name, strategy_payload, manifest):
    """Execute exactly-accounted 2-opt/3-opt under a shared fair budget."""
    import random
    import time
    from academic_benchmark.fairness import (
        FairRunResult,
        ObjectiveEvaluationBudget,
        improve_three_opt_budgeted,
        improve_two_opt_budgeted,
    )

    if strategy_payload not in {LocalSearchType.TWO_OPT, LocalSearchType.THREE_OPT}:
        raise ValueError(
            f"{algorithm_name} does not expose exact objective accounting in fair mode"
        )

    matrix, matrix_kind = _problem_matrix(problem)
    seed = manifest.paired_seed(problem.name, run_idx)
    route = list(range(problem.dimension))
    random.Random(seed).shuffle(route)
    budget = ObjectiveEvaluationBudget(manifest.evaluation_budget)
    max_iterations = int(params.get("max_iterations", 1000))
    first_improvement = bool(params.get("first_improvement", False))
    acceptance_policy = "first_improvement" if first_improvement else "best_improvement"
    neighborhood_window = None

    started = time.perf_counter()
    if strategy_payload == LocalSearchType.TWO_OPT:
        search = improve_two_opt_budgeted(
            route, matrix, budget, max_iterations=max_iterations,
            first_improvement=first_improvement,
        )
        family = "2-opt"
    else:
        neighborhood_window = params.get("window", params.get("max_segment_length", 12))
        search = improve_three_opt_budgeted(
            route, matrix, budget, max_iterations=max_iterations,
            first_improvement=first_improvement,
            window=neighborhood_window,
        )
        family = "3-opt"
    elapsed = time.perf_counter() - started
    # L8: report the solver's own reason; re-deriving it from the iteration counter mislabels a search
    # that converged on its last permitted iteration.
    termination_reason = search.termination_reason

    optimal = getattr(problem, "optimal", None)
    gap = ((search.cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
    result = FairRunResult(
        problem=problem.name, algorithm=algorithm_name, algorithm_id=algorithm_name,
        algorithm_family=family, variant="pure", run=run_idx, seed=seed,
        seed_group=manifest.seed_group(problem.name, run_idx),
        dimension=problem.dimension, optimal=optimal, tour_cost=float(search.cost),
        objective_cost=float(search.cost), gap_pct=gap, elapsed_sec=elapsed,
        iterations=search.iterations, evaluations=budget.used,
        objective_evaluations=budget.used, evaluation_budget=manifest.evaluation_budget,
        budget_terminated=search.budget_exhausted,
        tour=[node + 1 for node in search.route],
        problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
        matrix_kind=matrix_kind,
        initialization_policy="paired_seed_random_permutation_all_nodes",
        termination_policy=(
            f"{manifest.budget_policy};max_iterations={max_iterations};"
            f"budget_exhausted={search.budget_exhausted}"
        ),
        execution_backend="objective=python;polish=none",
        polish_policy={
            "enabled": False, "initial": False, "periodic": False,
            "final": False, "operator": None,
        },
        comparison_regime=(
            manifest.comparison_regime or "fixed_evaluation_budget"
        ),
        acceptance_policy=acceptance_policy,
        neighborhood_window=neighborhood_window,
        termination_reason=termination_reason,
    )
    manifest.validate_result(result)
    return result


def _run_native_local_search(problem, params, run_idx, algorithm_name, strategy_payload, manifest):
    """Execute canonical local search to its configured native stopping rule."""
    import random
    import time
    from academic_benchmark.fairness import (
        ObjectiveEvaluationBudget,
        improve_three_opt_budgeted,
        improve_two_opt_budgeted,
    )
    from academic_benchmark.native_protocol import NativeRunResult

    if strategy_payload not in {LocalSearchType.TWO_OPT, LocalSearchType.THREE_OPT}:
        raise ValueError(
            f"{algorithm_name} does not expose exact objective accounting in native mode"
        )
    if "max_iterations" not in params or "first_improvement" not in params:
        raise ValueError("native local search requires max_iterations and first_improvement")
    if strategy_payload == LocalSearchType.THREE_OPT and "window" not in params:
        raise ValueError("native 3-opt requires window")

    matrix, matrix_kind = _problem_matrix(problem)
    seed = manifest.paired_seed(problem.name, run_idx)
    route = list(range(problem.dimension))
    random.Random(seed).shuffle(route)
    accounting = ObjectiveEvaluationBudget(None)
    max_iterations = int(params["max_iterations"])
    first_improvement = params["first_improvement"]
    acceptance_policy = "first_improvement" if first_improvement else "best_improvement"
    neighborhood_window = None

    started = time.perf_counter()
    if strategy_payload == LocalSearchType.TWO_OPT:
        search = improve_two_opt_budgeted(
            route, matrix, accounting, max_iterations=max_iterations,
            first_improvement=first_improvement,
        )
        family = "2-opt"
    else:
        neighborhood_window = int(params["window"])
        search = improve_three_opt_budgeted(
            route, matrix, accounting, max_iterations=max_iterations,
            first_improvement=first_improvement, window=neighborhood_window,
        )
        family = "3-opt"
    elapsed = time.perf_counter() - started
    if search.budget_exhausted or search.termination_reason == "evaluation_budget_exhausted":
        raise ValueError("native local search unexpectedly exhausted a measurement counter")

    optimal = getattr(problem, "optimal", None)
    gap = ((search.cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
    result = NativeRunResult(
        problem=problem.name, algorithm=algorithm_name, algorithm_id=algorithm_name,
        algorithm_family=family, variant="pure", run=run_idx, seed=seed,
        seed_group=manifest.seed_group(problem.name, run_idx),
        dimension=problem.dimension, optimal=optimal, tour_cost=float(search.cost),
        objective_cost=float(search.cost), gap_pct=gap, elapsed_sec=elapsed,
        iterations=search.iterations, evaluations=accounting.used,
        objective_evaluations=accounting.used, evaluation_budget=None,
        budget_terminated=False, tour=[node + 1 for node in search.route],
        problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
        matrix_kind=matrix_kind,
        initialization_policy="paired_seed_random_permutation_all_nodes",
        termination_policy=f"algorithm_native_termination;max_iterations={max_iterations}",
        execution_backend="objective=python;polish=none",
        polish_policy={
            "enabled": False, "initial": False, "periodic": False,
            "final": False, "operator": None,
        },
        comparison_regime=manifest.comparison_regime,
        acceptance_policy=acceptance_policy,
        neighborhood_window=neighborhood_window,
        termination_reason=search.termination_reason,
    )
    manifest.validate_result(result)
    return result


# 1. Register Numba (Legacy) Algorithms
def _make_legacy_executor(strategy_payload: any, algorithm_type: str, algorithm_name: str):
    def executor(problem, params, seed, run_idx):
        import time
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.fairness import fair_manifest_from_params
        from academic_benchmark.native_protocol import native_manifest_from_params
        import math
        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        if manifest is not None:
            if _is_routing_problem(problem):
                raise ValueError("fair TSP comparison mode does not accept routing problems")
            return _run_fair_local_search(
                problem, params, run_idx, algorithm_name, strategy_payload, manifest
            )
        if native_manifest is not None:
            if _is_routing_problem(problem):
                raise ValueError("native TSP comparison mode does not accept routing problems")
            return _run_native_local_search(
                problem, params, run_idx, algorithm_name, strategy_payload,
                native_manifest,
            )
        if _is_routing_problem(problem):
            return _run_core_routing_executor(problem, params, seed, run_idx, algorithm_name)
        
        # Build duration func
        from uniride_core.algorithms.numba_utils import create_np_duration_func, convert_route_to_indices
        from uniride_core.algorithms.local_search_numba import apply_local_search
        import numpy as np
        
        is_tm = getattr(problem, 'is_time_matrix', False)
        dimension = problem.dimension
        
        if is_tm and hasattr(problem, 'time_matrix'):
            time_matrix = problem.time_matrix
            unique_locs = [f"L{i+1}" for i in range(dimension)]
            np_matrix = np.array(time_matrix, dtype=np.float64)
            duration_func = create_np_duration_func(np_matrix, unique_locs)
            dist_matrix = time_matrix
        else:
            unique_locs = [f"L{i+1}" for i in range(dimension)]

            dist_matrix_np = None
            problem_dm = getattr(problem, 'dist_matrix', None)
            if problem_dm is not None:
                dist_matrix_np = np.array(problem_dm, dtype=np.float64)
            else:
                # Fallback for standard TSPLIB
                try:
                    from academic_benchmark.tsplib_manager import get_distance_matrix
                    import os
                    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tsplib_data", "tsplib.db")
                    dist_matrix_np = get_distance_matrix(problem.name, db_path)
                except Exception:
                    dist_matrix_np = None
                if dist_matrix_np is None:
                    from uniride_core.algorithms.numba_utils import create_np_distance_matrix
                    dist_matrix_np = create_np_distance_matrix(problem.coordinates)

            duration_func = create_np_duration_func(dist_matrix_np, unique_locs)
            dist_matrix = dist_matrix_np.tolist()
            
        import random
        indices = list(range(1, dimension + 1))
        # Local generator (same permutation as random.seed(seed) + random.shuffle): the
        # process-global ``random`` state is never reseeded (audit H12).
        random.Random(seed).shuffle(indices)
        initial_route = [f"L{i}" for i in indices]

        start_time = time.time()
        if algorithm_type == "local_search":
            improved_route, _ = apply_local_search(
                initial_route, duration_func, strategy_payload,
                max_iterations=int(params.get("max_iterations", 1000)),
            )
        else:
            from uniride_core.algorithms.numba_metaheuristics import run_meta_heuristic
            improved_route = run_meta_heuristic(
                str(strategy_payload), initial_route, duration_func, params, seed,
            )
        elapsed = time.time() - start_time
        
        tour_indices = convert_route_to_indices(improved_route)
        tour_length = 0
        for k in range(len(tour_indices)):
            a = tour_indices[k] - 1
            b = tour_indices[(k + 1) % len(tour_indices)] - 1
            tour_length += dist_matrix[a][b]
            
        tour_length = tour_length if is_tm else report_cycle_cost(tour_length, dist_matrix)
        
        optimal = getattr(problem, "optimal", None)
        gap = None
        if optimal and optimal > 0:
            gap = ((tour_length - optimal) / optimal) * 100
            
        return RunResult(
            problem=problem.name, algorithm=algorithm_name,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=optimal, tour_cost=tour_length,
            gap_pct=gap, elapsed_sec=elapsed,
            iterations=0, tour=tour_indices,
            objective_cost=tour_length,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind="travel_time" if is_tm else "distance",
        )
    return executor

_ALIAS_NAMES_WITHOUT_OWN_ENTRY = frozenset({"Numba-2-opt", "Numba-3-opt-bounded", "Numba-Or-opt"})

for name, payload, default_params in STRATEGIES:
    algo_type = default_params.get("algorithm_type", "local_search")
    if algo_type == "meta_heuristic":
        # C-14: no raw executor over numba_metaheuristics.py is registered. Numba-GA and
        # Numba-PSO are deprecated aliases of the canonical Core-GA-TSP / Core-PSO-TSP,
        # and Numba-GWO / Numba-HHO are registered once by the canonical GWO/HHO block.
        continue
    public_name = f"Numba-{name}"
    if public_name in _ALIAS_NAMES_WITHOUT_OWN_ENTRY:
        # Gate C follow-up: deprecated aliases of Core-TwoOpt/ThreeOpt/OrOpt reach only the
        # canonical executor through the resolver; they have no executor of their own.
        continue
    AlgorithmRegistry.register(public_name)(_make_legacy_executor(payload, algo_type, public_name))
    # We could register param spaces here too, but for simplicity we rely on the old _build_doe_space inside cli_engine

# 2. Register SOTA Algorithms
_SUPPORTED_SOTA_ALGOS = {"E2BSO-TSP", "R2DMA-TSP", "P-AOEA-TSP", "CGO-TSP", "RUN-TSP", "ALNS-TSP"}
SOTA_ALGOS = [name for name in list_algorithm_names("sota_tsp") if name in _SUPPORTED_SOTA_ALGOS]
def _make_sota_executor(algo: str, reported_algorithm_id: str | None = None):
    public_id = reported_algorithm_id or f"SOTA-{algo}"
    def executor(problem, params, seed, run_idx):
        import time
        import math
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.benchmark_utils import compute_gap
        from academic_benchmark.fairness import fair_manifest_from_params
        from academic_benchmark.native_protocol import native_manifest_from_params

        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        if manifest is not None or native_manifest is not None:
            if algo != "ALNS-TSP":
                raise ValueError(
                    f"{algo} does not expose exact objective accounting in scientific protocol mode"
                )
            if _is_routing_problem(problem):
                regime = "fair" if manifest is not None else "native"
                raise ValueError(f"{regime} TSP comparison mode does not accept routing problems")
            return _run_canonical_alns(
                problem,
                params,
                run_idx,
                manifest or native_manifest,
                native=native_manifest is not None,
            )

        if _is_routing_problem(problem):
            return _run_core_routing_executor(problem, params, seed, run_idx, f"{public_id}:core-greedy-routing")
        
        # Map SOTA algorithm names to their actual module, class, and config names
        mod_map = {
            "E2BSO-TSP": ("e2bso_tsp", "E2BSO_TSP", "E2BSOTSPConfig"),
            "R2DMA-TSP": ("r2dma_tsp", "R2DMA_TSP", "R2DMATSPConfig"),
            "P-AOEA-TSP": ("paoea_tsp", "PAOEA_TSP", "PAOEAConfig"),
            "CGO-TSP": ("cgo_tsp", "CGO_TSP", "CGOConfig"),
            "RUN-TSP": ("run_tsp", "RUN_TSP", "RUNConfig"),
            "ALNS-TSP": ("alns_tsp", "ALNS_TSP", "ALNSConfig"),
        }
        mod_name, cls_name, cfg_name = mod_map[algo]
        mod = importlib.import_module(f"uniride_core.algorithms.sota_tsp.{mod_name}")
        cls = getattr(mod, cls_name)
        cfg_cls = getattr(mod, cfg_name)
        
        # Build config object
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cfg_cls)}
        cfg_kwargs = {k: v for k, v in params.items() if k in valid_fields}
        cfg_kwargs["seed"] = seed
        config = cfg_cls(**cfg_kwargs)
        
        solver = cls(config=config)
        
        start_time = time.perf_counter()
        is_tm = getattr(problem, 'is_time_matrix', False)
        
        if is_tm and hasattr(problem, 'time_matrix'):
            tm = problem.time_matrix
            # Keep original depot-prepending layout for real-world UniRide compatibility
            n = len(tm)
            full_tm = [[0.0] * (n + 1) for _ in range(n + 1)]
            for i in range(n):
                for j in range(n):
                    full_tm[i + 1][j + 1] = float(tm[i][j])
            result = solver.solve_with_matrix(full_tm)
        elif getattr(problem, "dist_matrix", None) is not None:
            matrix = problem.dist_matrix
            result = solver.solve_with_matrix(
                matrix.tolist() if hasattr(matrix, "tolist") else matrix
            )
        else:
            # Load correct distance matrix from TSPLIB DB cache
            dist_matrix_np = None
            try:
                from academic_benchmark.tsplib_manager import get_distance_matrix
                import os
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tsplib_data", "tsplib.db")
                dist_matrix_np = get_distance_matrix(problem.name, db_path)
            except Exception:
                dist_matrix_np = None
                
            if dist_matrix_np is not None:
                result = solver.solve_with_matrix(dist_matrix_np)
            else:
                # Build correct distance matrix using edge_weight_type dispatch.
                # Using solver.solve(coordinates) would default to EUC_2D NINT,
                # producing wrong distances for GEO/ATT/CEIL_2D problems.
                ewt = getattr(problem, "edge_weight_type", "EUC_2D")
                if ewt == "EUC_2D":
                    result = solver.solve(problem.coordinates)
                else:
                    from uniride_core.algorithms.distance import tsplib_distance_by_type
                    coords = problem.coordinates
                    n = len(coords)
                    dm = [[0.0] * n for _ in range(n)]
                    for i in range(n):
                        for j in range(n):
                            if i != j:
                                dm[i][j] = float(tsplib_distance_by_type(ewt, coords[i], coords[j]))
                    result = solver.solve_with_matrix(dm)
            
        elapsed = time.perf_counter() - start_time
        objective_cost = float(result.tour_length)
        gap_pct, _ = compute_gap(problem.name, objective_cost, problem.optimal)
        
        # SOTA solvers return 0-indexed tours (0..N-1). Convert to 1-indexed to align with legacy executor.
        tour_1indexed = [idx + 1 for idx in result.tour] if result.tour else None
        
        return RunResult(
            problem=problem.name, algorithm=public_id,
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=objective_cost,
            objective_cost=objective_cost,
            gap_pct=round(gap_pct, 4) if not math.isnan(gap_pct) else None,
            elapsed_sec=round(elapsed, 3),
            iterations=result.iterations,
            tour=tour_1indexed
        )
    return executor

for algo in SOTA_ALGOS:
    if algo == "ALNS-TSP":
        # SOTA-ALNS-TSP is a deprecated alias of the catalog ID ALNS-TSP: no entry of its own.
        continue
    AlgorithmRegistry.register(f"SOTA-{algo}")(_make_sota_executor(algo))
_register_catalog_executor("ALNS-TSP", _make_sota_executor("ALNS-TSP", "ALNS-TSP"))


def _core_greedy_executor(problem, params, seed, run_idx):
    return _run_core_routing_executor(problem, params, seed, run_idx, "Core-Greedy-Routing")


AlgorithmRegistry.register("Core-Greedy-Routing")(_core_greedy_executor)


# C-14: the string-waypoint matrix engines are registered under their truthful
# Matrix-*-legacy names only; every Core-* catalog ID is owned by exactly one canonical
# executor registered further below.
for algo_name, solver in MATRIX_LEGACY_TSP_SOLVERS.items():
    AlgorithmRegistry.register(algo_name)(_make_core_tsp_executor(algo_name, solver))

_CANONICAL_LOCAL_SEARCH_REGISTRATIONS = {
    "Core-TwoOpt-TSP": LocalSearchType.TWO_OPT,
    "Core-ThreeOpt-TSP": LocalSearchType.THREE_OPT,
    "Core-OrOpt-TSP": LocalSearchType.OR_OPT,
}

for canonical_id, payload in _CANONICAL_LOCAL_SEARCH_REGISTRATIONS.items():
    _register_catalog_executor(
        canonical_id, _make_legacy_executor(payload, "local_search", canonical_id)
    )


def _executed_polish_policy(extra_stats, polish_enabled=False):
    """Build ``polish_policy`` from the polish work the solver actually did.

    A phase flag is never taken from the ``polish_enabled`` boolean. In fixed-budget
    mode the solver reports the candidate evaluations each polish phase spent
    (``polish_evaluations``); a phase is reported only when it spent at least one
    (audit M19: a polish call that finds the budget already exhausted did nothing).
    ``executed`` keeps the per-phase call counts as information. Where no counter
    exists (an ungoverned run) the flags fall back to the call counts and
    ``evaluations`` is omitted. Governed native memetic runs count their polish too
    (C-10), so they report ``evaluations`` like the fixed-budget path.
    """
    phases = ("initial", "periodic", "final")
    calls = {
        phase: int((extra_stats.get("polish_executed") or {}).get(phase, 0) or 0)
        for phase in phases
    }
    counted = extra_stats.get("polish_evaluations")
    if counted is not None:
        evaluations = {phase: int(counted.get(phase, 0) or 0) for phase in phases}
        ran = {phase: evaluations[phase] > 0 for phase in phases}
    else:
        evaluations = None
        ran = {phase: calls[phase] > 0 for phase in phases}
    any_ran = any(ran.values())
    policy = {
        "enabled": any_ran,
        "initial": ran["initial"],
        "periodic": ran["periodic"],
        "final": ran["final"],
        "operator": "2-opt" if any_ran else None,
    }
    if any_ran or polish_enabled:
        # Pure results keep the historical five-key shape (pinned by the fixed-budget
        # golden); memetic results always carry the counts, even when they are all
        # zero, so the validator can reject them.
        policy["executed"] = calls
        if evaluations is not None:
            policy["evaluations"] = evaluations
    return policy


def _make_numba_metah_executor(
    algorithm_name, solver_cls, default_params, routing_engine_name=None,
    variant="memetic_2opt", polish_enabled=True,
):
    """Executor for Numba-accelerated Bildiri2026 metaheuristics (GWO/HHO).

    Uses the cached-numpy + JIT-kernel path from BaseTSPSolver
    (solve_with_matrix) rather than the slow string-route duration_func
    path used by _make_core_tsp_executor. This routes Core-GWO-TSP and
    Core-HHO-TSP to the fast numba_accel pipeline.

    ``routing_engine_name`` is kept for signature compatibility and is unused: the executors are
    registered behind the catalog routing refusal and never see CVRP/CVRPTW problems.
    """
    # Legacy param aliases used by the old tsp_meta_engines executors → new
    # GWOOptimizer / HHOOptimizer constructor names.
    _ALIASES = {
        "num_wolves": "pack_size",
        "num_hawks": "hawks",
        "a_initial": "initial_a",
        "escape_energy_factor": "initial_energy",
        "iterations": "max_iterations",
        "levy_beta": "levy_beta",  # accepted via _levy_flight scale, not a kwarg
        "local_search_rate": "local_search_rate",  # ignored by new solvers
    }
    import inspect as _inspect
    _valid_kwargs = set(_inspect.signature(solver_cls).parameters)

    def executor(problem, params, seed, run_idx):
        import time as _time
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.fairness import FairRunResult, fair_manifest_from_params
        from academic_benchmark.native_protocol import native_manifest_from_params

        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        protocol_manifest = manifest or native_manifest
        if protocol_manifest is not None:
            if _is_routing_problem(problem):
                raise ValueError("academic TSP comparison mode does not accept routing problems")
            seed = protocol_manifest.paired_seed(problem.name, run_idx)

        # Routing problems never get here: every catalog executor is registered behind
        # _register_catalog_executor, which refuses them (the CVRP-*/CVRPTW-* aliases keep
        # the legacy matrix engines).
        matrix, matrix_kind = _problem_matrix(problem)

        cfg = dict(default_params)
        for k, v in params.items():
            new_k = _ALIASES.get(k, k)
            if new_k in _valid_kwargs:
                cfg[new_k] = v
        # Always honor explicit max_iterations overrides.
        if "max_iterations" in params:
            cfg["max_iterations"] = int(params["max_iterations"])
        cfg["random_seed"] = seed
        cfg["polish_enabled"] = polish_enabled
        if manifest is not None:
            cfg["evaluation_budget"] = manifest.evaluation_budget
        if native_manifest is not None and polish_enabled:
            # C-10: native memetic polish is counted (budgeted Python 2-opt, no cap).
            cfg["count_polish"] = True

        solver = solver_cls(**cfg)
        if polish_enabled and (
            int(solver.polish_iters) <= 0 and int(solver.final_polish_iters) <= 0
        ):
            raise ValueError(
                f"{algorithm_name} is a memetic 2-opt configuration but polish_iters="
                f"{solver.polish_iters} and final_polish_iters={solver.final_polish_iters} "
                "execute no polish; give at least one phase a positive polish budget "
                "or use the Pure variant"
            )
        start_time = _time.perf_counter()
        result = solver.solve_with_matrix(
            matrix, recalculate=protocol_manifest is None, closed_tsp=True
        )
        elapsed = _time.perf_counter() - start_time

        cost = float(getattr(result, "tour_length", 0.0))
        optimal = getattr(problem, "optimal", None)
        gap = None
        if optimal and optimal > 0:
            gap = ((cost - optimal) / optimal) * 100

        tour = getattr(result, "tour", None)
        if tour is not None:
            tour = [int(node) + 1 for node in tour]

        extra_stats = dict(getattr(result, "extra_stats", {}) or {})
        evaluations = int(extra_stats.get("objective_evaluations") or 0)
        polish_policy = _executed_polish_policy(extra_stats, polish_enabled)
        budget_terminated = bool(extra_stats.get("budget_terminated", False))
        if budget_terminated:
            termination_reason = "evaluation_budget_exhausted"
        elif int(getattr(result, "iterations", 0) or 0) >= int(cfg.get("max_iterations", 0) or 0):
            termination_reason = "max_iterations"
        else:
            termination_reason = "stagnation_limit"
        common_kwargs = dict(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=cost,
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(getattr(result, "iterations", 0) or 0),
            tour=tour,
            objective_cost=cost,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
            evaluations=evaluations,
        )
        if protocol_manifest is None:
            return RunResult(**common_kwargs)

        if native_manifest is not None:
            native_result = FairRunResult(
                **common_kwargs,
                algorithm_id=algorithm_name,
                algorithm_family="GWO" if "GWO" in algorithm_name else "HHO",
                variant=variant,
                seed_group=native_manifest.seed_group(problem.name, run_idx),
                objective_evaluations=evaluations,
                evaluation_budget=None,
                budget_terminated=False,
                comparison_regime=native_manifest.comparison_regime,
                acceptance_policy="population_evolution",
                neighborhood_window=None,
                termination_reason=termination_reason,
                initialization_policy=(
                    "paired_seed_random_population_all_nodes_with_initial_2opt"
                    if polish_policy["initial"] else "paired_seed_random_population_all_nodes"
                ),
                termination_policy=(
                    f"algorithm_native_termination;max_iterations={cfg.get('max_iterations')};"
                    f"max_no_improvement={cfg.get('max_no_improvement')}"
                ),
                execution_backend=str(extra_stats.get("execution_backend", "unknown")),
                polish_policy=polish_policy,
            )
            native_manifest.validate_result(native_result)
            return native_result

        fair_result = FairRunResult(
            **common_kwargs,
            algorithm_id=algorithm_name,
            algorithm_family="GWO" if "GWO" in algorithm_name else "HHO",
            variant=variant,
            seed_group=manifest.seed_group(problem.name, run_idx),
            objective_evaluations=evaluations,
            evaluation_budget=manifest.evaluation_budget,
            budget_terminated=budget_terminated,
            comparison_regime=(
                manifest.comparison_regime or "fixed_evaluation_budget"
            ),
            acceptance_policy="population_evolution",
            neighborhood_window=None,
            termination_reason=termination_reason,
            initialization_policy=(
                "paired_seed_random_population_all_nodes_with_initial_2opt"
                if polish_policy["initial"] else "paired_seed_random_population_all_nodes"
            ),
            termination_policy=(
                f"{manifest.budget_policy};max_iterations={cfg.get('max_iterations')};"
                f"max_no_improvement={cfg.get('max_no_improvement')}"
            ),
            execution_backend=str(extra_stats.get("execution_backend", "unknown")),
            polish_policy=polish_policy,
        )
        manifest.validate_result(fair_result)
        return fair_result
    return executor


def _make_canonical_ga_executor(algorithm_name="Core-GA-TSP", memetic=False):
    """Manifest-aware executor for the canonical GA (C-16a pure, C-16c memetic).

    Fixed-budget and native runs take the strict scientific parameter schema (all keys
    required, unknown keys rejected) and the paired seed from the manifest. The pure GA
    has no polish stage, so ``polish_policy`` is always the no-polish shape. With
    ``memetic=True`` (``Core-GA-TSP-Memetic-2opt``) the polish iteration counts are
    required keys with no default and no zero, the polish is counted (budgeted Python
    2-opt, also in native mode) and ``polish_policy`` is derived from the executed counts;
    the GA has no periodic polish, so ``periodic`` is never reported true.
    """
    defaults = {
        "population_size": 100, "max_iterations": 500, "crossover_rate": 0.85,
        "mutation_rate": 0.15, "elite_count": 2, "tournament_size": 3,
        "max_no_improvement": 100,
    }
    # Non-protocol callers only: the DOE/Optuna GA space (NUMBA_PARAM_SPACES["GA"],
    # shared with Numba-GA) names the population and elite keys pop_size/elite_size.
    # Protocol runs stay on the strict schema and take no aliases.
    aliases = {
        "generations": "max_iterations", "iterations": "max_iterations",
        "pop_size": "population_size", "elite_size": "elite_count",
    }

    def executor(problem, params, seed, run_idx):
        import time as _time
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.fairness import (
            FairRunResult,
            fair_manifest_from_params,
            validate_scientific_ga_memetic_params,
            validate_scientific_ga_params,
        )
        from academic_benchmark.native_protocol import native_manifest_from_params
        from uniride_core.algorithms.tsp_matrix_metaheuristics import GAOptimizer

        validate_params = (
            validate_scientific_ga_memetic_params if memetic else validate_scientific_ga_params
        )

        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        protocol_manifest = manifest or native_manifest
        if protocol_manifest is not None:
            if _is_routing_problem(problem):
                raise ValueError("academic TSP comparison mode does not accept routing problems")
            seed = protocol_manifest.paired_seed(problem.name, run_idx)
            cfg = validate_params({
                key: value for key, value in params.items()
                if key not in {"fair_comparison", "native_comparison"}
            })
        else:
            for alias in ("pop_size", "elite_size"):
                if alias in params and aliases[alias] in params:
                    raise ValueError(
                        f"GA parameters {alias!r} and {aliases[alias]!r} are aliases of "
                        "the same setting; give only one"
                    )
            cfg = dict(defaults)
            for key, value in params.items():
                key = aliases.get(key, key)
                if key in defaults:
                    cfg[key] = value
            if memetic:
                # No defaults for the polish: a memetic run states its polish budget.
                polish_cfg = {
                    key: params.get(key) for key in ("initial_polish_iters", "final_polish_iters")
                    if key in params
                }
                validate_scientific_ga_memetic_params({**cfg, **polish_cfg})
                cfg.update(polish_cfg)

        matrix, matrix_kind = _problem_matrix(problem)
        solver = GAOptimizer(
            **cfg,
            polish_enabled=memetic,
            random_seed=seed,
            evaluation_budget=manifest.evaluation_budget if manifest is not None else None,
        )
        start_time = _time.perf_counter()
        result = solver.solve_with_matrix(
            matrix, recalculate=protocol_manifest is None, closed_tsp=True
        )
        elapsed = _time.perf_counter() - start_time

        cost = float(result.tour_length)
        optimal = getattr(problem, "optimal", None)
        gap = ((cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
        tour = [int(node) + 1 for node in result.tour] if result.tour is not None else None

        extra_stats = dict(result.extra_stats or {})
        evaluations = int(extra_stats.get("objective_evaluations") or 0)
        budget_terminated = bool(extra_stats.get("budget_terminated", False))
        # The solver reports max_no_improvement; result rows use the vocabulary shared
        # with GWO/HHO/ALNS (stagnation_limit).
        termination_reason = {"max_no_improvement": "stagnation_limit"}.get(
            extra_stats["termination_reason"], extra_stats["termination_reason"]
        )
        common_kwargs = dict(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=cost,
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(result.iterations or 0),
            tour=tour,
            objective_cost=cost,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
            evaluations=evaluations,
        )
        if protocol_manifest is None:
            return RunResult(**common_kwargs)

        polish_policy = _executed_polish_policy(extra_stats, memetic)
        termination_detail = (
            f"max_iterations={cfg['max_iterations']};"
            f"max_no_improvement={cfg['max_no_improvement']}"
        )
        if memetic:
            termination_detail += (
                f";initial_polish_iters={cfg['initial_polish_iters']};"
                f"final_polish_iters={cfg['final_polish_iters']}"
            )
        protocol_kwargs = dict(
            algorithm_id=algorithm_name,
            algorithm_family="GA",
            variant="memetic_2opt" if memetic else "pure",
            objective_evaluations=evaluations,
            acceptance_policy="population_evolution",
            neighborhood_window=None,
            termination_reason=termination_reason,
            initialization_policy=(
                "paired_seed_random_population_all_nodes_with_initial_2opt"
                if polish_policy["initial"] else "paired_seed_random_population_all_nodes"
            ),
            execution_backend=str(extra_stats.get("execution_backend", "unknown")),
            polish_policy=polish_policy,
        )
        if native_manifest is not None:
            native_result = FairRunResult(
                **common_kwargs,
                **protocol_kwargs,
                seed_group=native_manifest.seed_group(problem.name, run_idx),
                evaluation_budget=None,
                budget_terminated=False,
                comparison_regime=native_manifest.comparison_regime,
                termination_policy=f"algorithm_native_termination;{termination_detail}",
            )
            native_manifest.validate_result(native_result)
            return native_result

        fair_result = FairRunResult(
            **common_kwargs,
            **protocol_kwargs,
            seed_group=manifest.seed_group(problem.name, run_idx),
            evaluation_budget=manifest.evaluation_budget,
            budget_terminated=budget_terminated,
            comparison_regime=manifest.comparison_regime or "fixed_evaluation_budget",
            termination_policy=f"{manifest.budget_policy};{termination_detail}",
        )
        manifest.validate_result(fair_result)
        return fair_result

    return executor


_register_catalog_executor("Core-GA-TSP", _make_canonical_ga_executor("Core-GA-TSP"))
# C-16c: promotion commit only (a registry ID needs its catalog entry).
_register_catalog_executor(
    "Core-GA-TSP-Memetic-2opt",
    _make_canonical_ga_executor("Core-GA-TSP-Memetic-2opt", memetic=True),
)


def _make_canonical_pso_executor(algorithm_name="Core-PSO-TSP"):
    """Manifest-aware executor for the canonical pure PSO (C-16b).

    Fixed-budget and native runs take the strict scientific parameter schema (all keys
    required, unknown keys rejected) and the paired seed from the manifest; the PSO has
    no polish stage, so ``polish_policy`` is always the no-polish shape. The counted
    diversity re-initialization is a solver parameter (``reinit_interval``), not polish.

    Outside the two protocols (no ``fair_comparison`` / ``native_comparison`` key) the
    executor is the legacy path: unknown keys are silently ignored, missing keys take the
    defaults below and no parameter validation runs (same as the GA executor). Only the
    protocol path validates strictly. The fixed parts of the diversity step
    (``REINIT_RANDOM_FRACTION``, ``REINIT_MAX_SWAPS``) are not parameters; they are
    written into every protocol row's ``termination_policy`` so that changing them makes
    a different pooling identity.
    """
    # Defaults of the archived Bildiri PSO (reference only), used outside the protocols.
    defaults = {
        "swarm_size": 50, "max_iterations": 500, "inertia_weight": 0.729,
        "cognitive_coeff": 1.49445, "social_coeff": 1.49445, "max_velocity_size": 5,
        "max_no_improvement": 100, "reinit_interval": 50,
    }
    aliases = {"iterations": "max_iterations", "generations": "max_iterations"}

    def executor(problem, params, seed, run_idx):
        import time as _time
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.fairness import (
            FairRunResult,
            fair_manifest_from_params,
            validate_scientific_pso_params,
        )
        from academic_benchmark.native_protocol import native_manifest_from_params
        from uniride_core.algorithms.tsp_matrix_metaheuristics import PSOOptimizer

        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        protocol_manifest = manifest or native_manifest
        if protocol_manifest is not None:
            if _is_routing_problem(problem):
                raise ValueError("academic TSP comparison mode does not accept routing problems")
            seed = protocol_manifest.paired_seed(problem.name, run_idx)
            cfg = validate_scientific_pso_params({
                key: value for key, value in params.items()
                if key not in {"fair_comparison", "native_comparison"}
            })
        else:
            cfg = dict(defaults)
            for key, value in params.items():
                key = aliases.get(key, key)
                if key in defaults:
                    cfg[key] = value

        matrix, matrix_kind = _problem_matrix(problem)
        solver = PSOOptimizer(
            **cfg,
            random_seed=seed,
            evaluation_budget=manifest.evaluation_budget if manifest is not None else None,
        )
        start_time = _time.perf_counter()
        result = solver.solve_with_matrix(
            matrix, recalculate=protocol_manifest is None, closed_tsp=True
        )
        elapsed = _time.perf_counter() - start_time

        cost = float(result.tour_length)
        optimal = getattr(problem, "optimal", None)
        gap = ((cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
        tour = [int(node) + 1 for node in result.tour] if result.tour is not None else None

        extra_stats = dict(result.extra_stats or {})
        evaluations = int(extra_stats.get("objective_evaluations") or 0)
        budget_terminated = bool(extra_stats.get("budget_terminated", False))
        # The solver reports max_no_improvement; result rows use the vocabulary shared
        # with GWO/HHO/ALNS/GA (stagnation_limit).
        termination_reason = {"max_no_improvement": "stagnation_limit"}.get(
            extra_stats["termination_reason"], extra_stats["termination_reason"]
        )
        common_kwargs = dict(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=cost,
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(result.iterations or 0),
            tour=tour,
            objective_cost=cost,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
            evaluations=evaluations,
        )
        if protocol_manifest is None:
            return RunResult(**common_kwargs)

        polish_policy = _executed_polish_policy(extra_stats, False)
        termination_detail = (
            f"max_iterations={cfg['max_iterations']};"
            f"max_no_improvement={cfg['max_no_improvement']};"
            f"reinit_interval={cfg['reinit_interval']};"
            f"reinit_random_fraction={PSOOptimizer.REINIT_RANDOM_FRACTION};"
            f"reinit_max_swaps={PSOOptimizer.REINIT_MAX_SWAPS}"
        )
        protocol_kwargs = dict(
            algorithm_id=algorithm_name,
            algorithm_family="PSO",
            variant="pure",
            objective_evaluations=evaluations,
            acceptance_policy="population_evolution",
            neighborhood_window=None,
            termination_reason=termination_reason,
            initialization_policy="paired_seed_random_swarm_all_nodes",
            execution_backend=str(extra_stats.get("execution_backend", "unknown")),
            polish_policy=polish_policy,
        )
        if native_manifest is not None:
            native_result = FairRunResult(
                **common_kwargs,
                **protocol_kwargs,
                seed_group=native_manifest.seed_group(problem.name, run_idx),
                evaluation_budget=None,
                budget_terminated=False,
                comparison_regime=native_manifest.comparison_regime,
                termination_policy=f"algorithm_native_termination;{termination_detail}",
            )
            native_manifest.validate_result(native_result)
            return native_result

        fair_result = FairRunResult(
            **common_kwargs,
            **protocol_kwargs,
            seed_group=manifest.seed_group(problem.name, run_idx),
            evaluation_budget=manifest.evaluation_budget,
            budget_terminated=budget_terminated,
            comparison_regime=manifest.comparison_regime or "fixed_evaluation_budget",
            termination_policy=f"{manifest.budget_policy};{termination_detail}",
        )
        manifest.validate_result(fair_result)
        return fair_result

    return executor


_register_catalog_executor("Core-PSO-TSP", _make_canonical_pso_executor("Core-PSO-TSP"))


def _make_hybrid_executor(algorithm_name):
    """Manifest-aware executor of ``Core-GWO/HHO-TSP-Memetic-3opt`` (C-08) and ``-ALNS`` (C-09).

    A pure GWO/HHO global stage and ONE canonical polish (3-opt, or ALNS with the derived
    polish seed) on the best validated global tour, run by ``run_composition`` on one
    shared objective counter. Fixed-budget runs cap
    the global stage at ``global_stage_cap(B, global_fraction)`` and give the polish the
    rest; native runs have no budget and count each stage separately. The result row is the
    polish stage's tour and cost and carries the stage record in ``composition``. The two
    protocols are the only way to run it: there is no unaccounted legacy path.
    """
    from academic_benchmark.composite_protocol import (
        COMPOSITE_ALGORITHMS,
        COMPOSITE_KIND_OF,
        KIND_ALNS,
        POLISH_OPERATORS,
    )

    family, _global_stage_id = COMPOSITE_ALGORITHMS[algorithm_name]
    kind = COMPOSITE_KIND_OF[algorithm_name]
    is_alns = kind == KIND_ALNS

    def executor(problem, params, seed, run_idx):
        import time as _time
        from academic_benchmark.composite_protocol import (
            COMPOSITE_COMPLETE_REASON,
            composition_record,
        )
        from academic_benchmark.fairness import (
            FairRunResult,
            fair_manifest_from_params,
            validate_scientific_hybrid_3opt_params,
            validate_scientific_hybrid_alns_params,
        )
        from academic_benchmark.native_protocol import native_manifest_from_params
        from uniride_core.algorithms.composition import (
            alns_polish_stage,
            global_stage_cap,
            run_composition,
            swarm_global_stage,
            three_opt_polish_stage,
        )

        manifest = fair_manifest_from_params(params)
        native_manifest = native_manifest_from_params(params)
        if manifest is not None and native_manifest is not None:
            raise ValueError("fair_comparison and native_comparison are mutually exclusive")
        protocol_manifest = manifest or native_manifest
        if protocol_manifest is None:
            raise ValueError(
                f"{algorithm_name} runs only under fair_comparison or native_comparison; "
                "it has no unaccounted execution path"
            )
        if _is_routing_problem(problem):
            raise ValueError("academic TSP comparison mode does not accept routing problems")
        seed = protocol_manifest.paired_seed(problem.name, run_idx)
        validate_params = (
            validate_scientific_hybrid_alns_params if is_alns
            else validate_scientific_hybrid_3opt_params
        )
        cfg = validate_params(
            family,
            {k: v for k, v in params.items() if k not in {"fair_comparison", "native_comparison"}},
            fixed_budget=manifest is not None,
        )

        matrix, matrix_kind = _problem_matrix(problem)
        if is_alns:
            # the polish seed comes from the manifest's OWN protocol version and the
            # per-run paired seed (never the base seed)
            polish_stage = alns_polish_stage(
                matrix, cfg["polish"],
                protocol_version=protocol_manifest.protocol_version, run_seed=seed,
            )
        else:
            polish_stage = three_opt_polish_stage(matrix, cfg["polish"])
        start_time = _time.perf_counter()
        composed = run_composition(
            matrix,
            global_stage=swarm_global_stage(family, matrix, cfg["global"], seed=seed),
            polish_stage=polish_stage,
            evaluation_budget=manifest.evaluation_budget if manifest is not None else None,
            global_fraction=cfg.get("global_fraction"),
        )
        elapsed = _time.perf_counter() - start_time

        cost = float(composed.cost)
        optimal = getattr(problem, "optimal", None)
        gap = ((cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
        record = composition_record(composed, kind)
        global_record, polish_record = record["stages"]
        polish_ran = polish_record["consumed_evaluations"] > 0
        # Stage-aware backend label: the objective backend the global stage really used
        # (it reports ``objective=<x>;polish=none``) plus the Python 3-opt polish.
        reported_backend = str(global_record["details"].get("execution_backend") or "unknown")
        objective_part = next(
            (part for part in reported_backend.split(";") if part.startswith("objective=")), None
        )
        execution_backend = (
            f"{objective_part};polish=python" if objective_part else "unknown"
        )
        global_cfg, polish_cfg = cfg["global"], cfg["polish"]
        if is_alns:
            polish_detail = (
                "polish_alns_params="
                + ",".join(f"{key}={polish_cfg[key]}" for key in sorted(polish_cfg))
                + f";polish_derived_seed={polish_record['seed']};polish_incoming_cost_reused=True"
            )
        else:
            polish_detail = (
                f"polish_max_iterations={polish_cfg['max_iterations']};"
                f"polish_first_improvement={polish_cfg['first_improvement']};"
                f"polish_window={polish_cfg['window']};polish_incoming_cost_reused=True"
            )
        detail = (
            f"composition={kind};"
            + (
                f"global_fraction={cfg['global_fraction']};"
                f"global_cap={global_stage_cap(manifest.evaluation_budget, cfg['global_fraction'])};"
                if manifest is not None else ""
            )
            + f"global_max_iterations={global_cfg['max_iterations']};"
            f"global_max_no_improvement={global_cfg['max_no_improvement']};"
            + polish_detail
        )
        common_kwargs = dict(
            problem=problem.name,
            algorithm=algorithm_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=cost,
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(global_record["iterations"]) + int(polish_record["iterations"]),
            tour=[int(node) + 1 for node in composed.tour],
            objective_cost=cost,
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
            evaluations=int(composed.evaluations),
        )
        protocol_kwargs = dict(
            algorithm_id=algorithm_name,
            algorithm_family=family,
            variant=kind,
            objective_evaluations=int(composed.evaluations),
            acceptance_policy="population_evolution",
            neighborhood_window=None,
            initialization_policy="paired_seed_random_population_all_nodes",
            execution_backend=execution_backend,
            polish_policy={
                "enabled": polish_ran, "initial": False, "periodic": False,
                "final": polish_ran,
                "operator": POLISH_OPERATORS[kind] if polish_ran else None,
            },
            composition=record,
        )
        if native_manifest is not None:
            native_result = FairRunResult(
                **common_kwargs,
                **protocol_kwargs,
                seed_group=native_manifest.seed_group(problem.name, run_idx),
                evaluation_budget=None,
                budget_terminated=False,
                comparison_regime=native_manifest.comparison_regime,
                termination_reason=COMPOSITE_COMPLETE_REASON,
                termination_policy=f"algorithm_native_termination;{detail}",
            )
            native_manifest.validate_result(native_result)
            return native_result

        # The row reason is the polish stage's (it ran last); the global stage's own
        # ceiling stop stays in its stage record.
        reason = composed.termination_reason
        fair_result = FairRunResult(
            **common_kwargs,
            **protocol_kwargs,
            seed_group=manifest.seed_group(problem.name, run_idx),
            evaluation_budget=manifest.evaluation_budget,
            budget_terminated=reason == "evaluation_budget_exhausted",
            comparison_regime=manifest.comparison_regime or "fixed_evaluation_budget",
            termination_reason=reason,
            termination_policy=f"{manifest.budget_policy};{detail}",
        )
        manifest.validate_result(fair_result)
        return fair_result

    return executor


_make_hybrid_3opt_executor = _make_hybrid_executor  # the C-08 name, kept as an alias

for _hybrid_id in (
    "Core-GWO-TSP-Memetic-3opt", "Core-HHO-TSP-Memetic-3opt",
    "Core-GWO-TSP-Memetic-ALNS", "Core-HHO-TSP-Memetic-ALNS",
):
    _register_catalog_executor(_hybrid_id, _make_hybrid_executor(_hybrid_id))


# Canonical GWO/HHO executors over the Numba-accelerated Bildiri2026 solvers (GWOOptimizer /
# HHOOptimizer: cached numpy matrix + numba JIT kernel path via BaseTSPSolver.solve_with_matrix).
# Core-GWO-TSP, Core-HHO-TSP, Numba-GWO and Numba-HHO are deprecated resolver aliases of the
# memetic-2opt entries and have no executor of their own (Gate C follow-up after C-14).
# C-14: a failed import must fail closed. There is no fallback engine under these names, so
# the ImportError propagates and the academic registry does not load.
from uniride_core.algorithms.tsp_matrix_metaheuristics import GWOOptimizer, HHOOptimizer

_NUMBA_METAH_OVERRIDES = {
    "Core-GWO-TSP-Pure": (GWOOptimizer, {
        "pack_size": 50, "max_iterations": 250, "initial_a": 2.0,
        "exploration_rate": 0.4, "max_no_improvement": 75,
    }, "Matrix-GWO-TSP-legacy", "pure", False),
    "Core-GWO-TSP-Memetic-2opt": (GWOOptimizer, {
        "pack_size": 50, "max_iterations": 250, "initial_a": 2.0,
        "exploration_rate": 0.4, "max_no_improvement": 75,
    }, "Matrix-GWO-TSP-legacy", "memetic_2opt", True),
    "Core-HHO-TSP-Pure": (HHOOptimizer, {
        "hawks": 50, "max_iterations": 250, "initial_energy": 1.0,
        "jump_probability": 0.5, "max_no_improvement": 75,
    }, "Matrix-HHO-TSP-legacy", "pure", False),
    "Core-HHO-TSP-Memetic-2opt": (HHOOptimizer, {
        "hawks": 50, "max_iterations": 250, "initial_energy": 1.0,
        "jump_probability": 0.5, "max_no_improvement": 75,
    }, "Matrix-HHO-TSP-legacy", "memetic_2opt", True),
}

for _algo_name, (_cls, _defaults, _routing_eng, _variant, _polish_enabled) in _NUMBA_METAH_OVERRIDES.items():
    _register_catalog_executor(
        _algo_name,
        _make_numba_metah_executor(
            _algo_name, _cls, _defaults, _routing_eng, _variant, _polish_enabled
        ),
    )

for algo_name in FCM_TSP_SOLVERS:
    AlgorithmRegistry.register(algo_name)(_make_matrix_tsp_executor(algo_name))


def _make_routing_alias_executor(alias_name: str, engine_name: str):
    def executor(problem, params, seed, run_idx):
        return _run_core_routing_executor(
            problem,
            params,
            seed,
            run_idx,
            alias_name,
            engine_name=engine_name,
        )
    return executor


def _make_holistic_routing_executor(alias_name: str, solver_name: str):
    def executor(problem, params, seed, run_idx):
        import time
        import numpy as np
        from academic_benchmark.engine_core import RunResult

        routing_problem = MatrixBuilder.to_routing_problem(problem)
        matrix = np.asarray(routing_problem.matrix.values, dtype=float).tolist()
        constraints = routing_problem.constraints
        demands = list(constraints.demands or [])
        disability_types = _disability_types_from_demands(demands[1:])
        sw_capacity, so_capacity = _sw_so_capacities(constraints.capacities)
        max_route_duration = float(
            constraints.max_route_duration
            or params.get("max_route_duration")
            or max(1.0, sum(max(row) for row in matrix))
        )
        num_vehicles = routing_problem.metadata.get("vehicles") or getattr(problem, "num_vehicles", None)
        time_limit_seconds = int(params.get("time_limit_seconds", params.get("time_limit", 30)))

        start = time.perf_counter()
        if solver_name == "OR-Tools":
            from uniride_core.algorithms.ortools_cvrp_engine import solve_ortools_cvrp
            solution = solve_ortools_cvrp(
                time_matrix=matrix,
                disability_types=disability_types,
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_route_duration=max_route_duration,
                num_vehicles=num_vehicles,
                time_limit_seconds=time_limit_seconds,
            )
        elif solver_name == "PyVRP":
            from uniride_core.algorithms.pyvrp_cvrp_engine import solve_pyvrp_cvrp
            solution = solve_pyvrp_cvrp(
                duration_matrix=matrix,
                coordinates=_coordinates_for_holistic(routing_problem),
                disability_types=disability_types,
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                num_vehicles=num_vehicles,
                time_limit_seconds=time_limit_seconds,
            )
        elif solver_name == "VROOM":
            from uniride_core.algorithms.vroom_cvrp_engine import solve_vroom_cvrp
            solution = solve_vroom_cvrp(
                duration_matrix=matrix,
                disability_types=disability_types,
                sw_capacity=sw_capacity,
                so_capacity=so_capacity,
                max_route_duration=max_route_duration,
                num_vehicles=num_vehicles,
            )
        else:
            raise ValueError(f"Unsupported holistic solver: {solver_name}")

        elapsed = time.perf_counter() - start
        if not solution.success:
            return RunResult(
                problem=problem.name,
                algorithm=alias_name,
                run=run_idx,
                seed=seed,
                dimension=problem.dimension,
                optimal=getattr(problem, "optimal", None),
                tour_cost=float("inf"),
                gap_pct=None,
                elapsed_sec=elapsed,
                error=solution.error_message,
                objective_cost=float("inf"),
                routes=[],
                num_vehicles=0,
                problem_type=routing_problem.problem_type,
                matrix_kind=routing_problem.matrix.kind,
            )

        routes = [[idx + 1 for idx in route.customer_indices] for route in solution.routes]
        route_loads = [[route.sw_count, route.so_count] for route in solution.routes]
        route_costs = _route_costs(routes, matrix, constraints.depot_index)
        objective_cost = float(sum(route_costs))
        optimal = getattr(problem, "optimal", None)
        gap = ((objective_cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
        return RunResult(
            problem=problem.name,
            algorithm=alias_name,
            run=run_idx,
            seed=seed,
            dimension=problem.dimension,
            optimal=optimal,
            tour_cost=objective_cost,
            gap_pct=gap,
            elapsed_sec=elapsed,
            routes=routes,
            route_loads=route_loads,
            route_costs=route_costs,
            num_vehicles=len(routes),
            objective_cost=objective_cost,
            problem_type=routing_problem.problem_type,
            matrix_kind=routing_problem.matrix.kind,
        )
    return executor


def _disability_types_from_demands(demands):
    out = []
    for demand in demands:
        vector = list(demand) if isinstance(demand, (list, tuple)) else [0, int(demand)]
        out.append("Sw" if len(vector) > 1 and int(vector[0]) > 0 else "So")
    return out


def _sw_so_capacities(capacities):
    caps = list(capacities or [4, 5])
    if len(caps) == 1:
        return 0, int(caps[0])
    return int(caps[0]), int(caps[1])


def _coordinates_for_holistic(routing_problem):
    coords = list(routing_problem.coordinates or [])
    if not coords:
        coords = [(float(idx), 0.0) for idx in range(routing_problem.dimension)]
    return [{"lat": float(y), "lng": float(x)} for x, y in coords]


def _route_costs(routes, matrix, depot_index):
    costs = []
    for route in routes:
        current = int(depot_index)
        total = 0.0
        for node in route:
            total += float(matrix[current][node])
            current = node
        total += float(matrix[current][depot_index])
        costs.append(total)
    return costs


_ROUTING_ALIAS_ENGINES = {
    "Core-Greedy-Routing": "Core-Greedy-Routing",
    "Core-TwoOpt-TSP": "Matrix-TwoOpt-TSP-legacy",
    "Core-GA-TSP": "Matrix-GA-TSP-legacy",
    "Core-PSO-TSP": "Matrix-PSO-TSP-legacy",
    "Core-GWO-TSP": "Matrix-GWO-TSP-legacy",
    "Core-HHO-TSP": "Matrix-HHO-TSP-legacy",
    "Numba-2-opt": "Matrix-TwoOpt-TSP-legacy",
    "Numba-3-opt-bounded": "Matrix-TwoOpt-TSP-legacy",
    "Numba-Or-opt": "Matrix-TwoOpt-TSP-legacy",
    "Numba-Swap": "Matrix-TwoOpt-TSP-legacy",
    "Numba-Hybrid": "Matrix-TwoOpt-TSP-legacy",
    "Numba-GA": "Matrix-GA-TSP-legacy",
    "Numba-PSO": "Matrix-PSO-TSP-legacy",
    "Numba-GWO": "Matrix-GWO-TSP-legacy",
    "Numba-HHO": "Matrix-HHO-TSP-legacy",
    "GA-Split": "Matrix-GA-TSP-legacy",
    "PSO-Split": "Matrix-PSO-TSP-legacy",
    "GWO-Split": "Matrix-GWO-TSP-legacy",
    "HHO-Split": "Matrix-HHO-TSP-legacy",
}

for problem_prefix in ("CVRP", "CVRPTW"):
    for base_name, engine_name in _ROUTING_ALIAS_ENGINES.items():
        alias = f"{problem_prefix}-{base_name}"
        AlgorithmRegistry.register(alias)(_make_routing_alias_executor(alias, engine_name))
    for solver_name in ("OR-Tools", "PyVRP", "VROOM"):
        alias = f"{problem_prefix}-{solver_name}"
        AlgorithmRegistry.register(alias)(_make_holistic_routing_executor(alias, solver_name))

def _verify_catalog_routing_refusal() -> None:
    """Fail closed at import: every catalog ID refuses routing and names real alternatives."""
    from uniride_core.algorithms.capabilities import list_algorithm_capabilities

    registered = set(AlgorithmRegistry.list_algorithms())
    for capability in list_algorithm_capabilities():
        canonical_id = capability.canonical_id
        if canonical_id not in registered:
            raise RuntimeError(f"catalog ID '{canonical_id}' has no registered executor")
        if not getattr(AlgorithmRegistry.get_executor(canonical_id), "refuses_routing", False):
            raise RuntimeError(
                f"catalog ID '{canonical_id}' was registered without the routing refusal"
            )
    for canonical_id, base in _ROUTING_ALTERNATIVE_BASES.items():
        for prefix in ("CVRP", "CVRPTW"):
            if f"{prefix}-{base}" not in registered:
                raise RuntimeError(
                    f"routing alternative '{prefix}-{base}' named for '{canonical_id}' is not registered"
                )


_verify_catalog_routing_refusal()

logger.info("Loaded %d algorithms.", len(AlgorithmRegistry.list_algorithms()))

def _run_canonical_or_opt(
    problem, params, run_idx, algorithm_name, manifest, *, native: bool
):
    import random
    import time

    from academic_benchmark.fairness import (
        FairRunResult,
        ObjectiveEvaluationBudget,
        improve_or_opt_budgeted,
    )

    matrix, matrix_kind = _problem_matrix(problem)
    seed = manifest.paired_seed(problem.name, run_idx)
    route = list(range(problem.dimension))
    random.Random(seed).shuffle(route)
    accounting = ObjectiveEvaluationBudget(
        None if native else manifest.evaluation_budget
    )
    max_iterations = int(params.get("max_iterations", 1000))
    first_improvement = bool(params.get("first_improvement", False))
    neighborhood_window = int(
        params.get("window", params.get("max_segment_length", 3))
    )
    started = time.perf_counter()
    search = improve_or_opt_budgeted(
        route,
        matrix,
        accounting,
        max_iterations=max_iterations,
        first_improvement=first_improvement,
        max_segment_length=neighborhood_window,
    )
    elapsed = time.perf_counter() - started
    if native and (
        search.budget_exhausted
        or search.termination_reason == "evaluation_budget_exhausted"
    ):
        raise ValueError("native local search unexpectedly exhausted a measurement counter")

    optimal = getattr(problem, "optimal", None)
    gap = ((search.cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
    result = FairRunResult(
        problem=problem.name,
        algorithm=algorithm_name,
        algorithm_id=algorithm_name,
        algorithm_family="Or-opt",
        variant="pure",
        run=run_idx,
        seed=seed,
        seed_group=manifest.seed_group(problem.name, run_idx),
        dimension=problem.dimension,
        optimal=optimal,
        tour_cost=float(search.cost),
        objective_cost=float(search.cost),
        gap_pct=gap,
        elapsed_sec=elapsed,
        iterations=search.iterations,
        evaluations=accounting.used,
        objective_evaluations=accounting.used,
        evaluation_budget=None if native else manifest.evaluation_budget,
        budget_terminated=False if native else search.budget_exhausted,
        tour=[node + 1 for node in search.route],
        problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
        matrix_kind=matrix_kind,
        initialization_policy="paired_seed_random_permutation_all_nodes",
        termination_policy=(
            f"algorithm_native_termination;max_iterations={max_iterations}"
            if native
            else (
                f"{manifest.budget_policy};max_iterations={max_iterations};"
                f"budget_exhausted={search.budget_exhausted}"
            )
        ),
        execution_backend="objective=python;polish=none",
        polish_policy={
            "enabled": False,
            "initial": False,
            "periodic": False,
            "final": False,
            "operator": None,
        },
        comparison_regime=manifest.comparison_regime,
        acceptance_policy=(
            "first_improvement" if first_improvement else "best_improvement"
        ),
        neighborhood_window=neighborhood_window,
        termination_reason=search.termination_reason,
    )
    manifest.validate_result(result)
    return result


def _run_canonical_alns(problem, params, run_idx, manifest, *, native: bool):
    """Run the canonical ALNS implementation under a scientific manifest."""
    import time

    from academic_benchmark.fairness import (
        FairRunResult,
        ObjectiveEvaluationBudget,
        validate_scientific_alns_params,
    )
    from uniride_core.algorithms.sota_tsp.alns_tsp import ALNSConfig, ALNS_TSP

    if _is_routing_problem(problem):
        regime = "native" if native else "fair"
        raise ValueError(f"{regime} TSP comparison mode does not accept routing problems")
    scientific = validate_scientific_alns_params({
        key: value for key, value in params.items()
        if key not in {"fair_comparison", "native_comparison"}
    })
    matrix, matrix_kind = _problem_matrix(problem)
    seed = manifest.paired_seed(problem.name, run_idx)
    config = ALNSConfig(
        iterations=scientific["max_iterations"],
        max_no_improve=scientific["max_no_improvement"],
        remove_ratio=scientific["remove_ratio"],
        min_remove=scientific["min_remove"],
        segment_length=scientific["segment_length"],
        weight_update_factor=scientific["weight_update_factor"],
        use_sa=scientific["use_sa"],
        sa_start_temp=scientific.get("sa_start_temp", ALNSConfig.sa_start_temp),
        sa_cooling_rate=scientific.get("sa_cooling_rate", ALNSConfig.sa_cooling_rate),
        seed=seed,
    )
    accounting = ObjectiveEvaluationBudget(None if native else manifest.evaluation_budget)
    started = time.perf_counter()
    search = ALNS_TSP(config).solve_accounted_with_matrix(matrix, accounting)
    elapsed = time.perf_counter() - started
    if native and (
        search.budget_exhausted
        or search.termination_reason == "evaluation_budget_exhausted"
    ):
        raise ValueError("native ALNS unexpectedly exhausted a measurement counter")

    optimal = getattr(problem, "optimal", None)
    cost = float(search.cost)
    gap = ((cost - optimal) / optimal) * 100 if optimal and optimal > 0 else None
    result = FairRunResult(
        problem=problem.name,
        algorithm="ALNS-TSP",
        algorithm_id="ALNS-TSP",
        algorithm_family="ALNS",
        variant="pure",
        run=run_idx,
        seed=seed,
        seed_group=manifest.seed_group(problem.name, run_idx),
        dimension=problem.dimension,
        optimal=optimal,
        tour_cost=cost,
        objective_cost=cost,
        gap_pct=gap,
        elapsed_sec=elapsed,
        iterations=search.iterations,
        evaluations=accounting.used,
        objective_evaluations=accounting.used,
        evaluation_budget=None if native else manifest.evaluation_budget,
        budget_terminated=(
            False if native else search.termination_reason == "evaluation_budget_exhausted"
        ),
        tour=[node + 1 for node in search.route],
        problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
        matrix_kind=matrix_kind,
        initialization_policy="nearest_neighbor_from_node_zero_all_nodes",
        termination_policy=(
            f"algorithm_native_termination;max_iterations={scientific['max_iterations']}"
            if native
            else (
                f"{manifest.budget_policy};max_iterations={scientific['max_iterations']};"
                f"budget_exhausted={search.budget_exhausted}"
            )
        ),
        execution_backend="objective=python;polish=none",
        polish_policy={
            "enabled": False,
            "initial": False,
            "periodic": False,
            "final": False,
            "operator": None,
        },
        comparison_regime=manifest.comparison_regime,
        acceptance_policy=(
            "simulated_annealing" if scientific["use_sa"] else "improving_only"
        ),
        neighborhood_window=None,
        termination_reason=search.termination_reason,
    )
    manifest.validate_result(result)
    return result

_existing_fair_local_search = _run_fair_local_search
_existing_native_local_search = _run_native_local_search


def _run_fair_local_search(
    problem, params, run_idx, algorithm_name, strategy_payload, manifest
):
    if strategy_payload == LocalSearchType.OR_OPT:
        return _run_canonical_or_opt(
            problem, params, run_idx, algorithm_name, manifest, native=False
        )
    return _existing_fair_local_search(
        problem, params, run_idx, algorithm_name, strategy_payload, manifest
    )


def _run_native_local_search(
    problem, params, run_idx, algorithm_name, strategy_payload, manifest
):
    if strategy_payload == LocalSearchType.OR_OPT:
        return _run_canonical_or_opt(
            problem, params, run_idx, algorithm_name, manifest, native=True
        )
    return _existing_native_local_search(
        problem, params, run_idx, algorithm_name, strategy_payload, manifest
    )
