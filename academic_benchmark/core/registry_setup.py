import logging
from academic_benchmark.engine_core import AlgorithmRegistry

logger = logging.getLogger(__name__)
from uniride_core.algorithms.numba_strategies import STRATEGIES
from uniride_core.algorithms.local_search_numba import LocalSearchType
from uniride_core.algorithms.registry import list_algorithm_names
from uniride_core.adapters.matrix_builder import MatrixBuilder
from uniride_core.algorithms.sota_tsp.base_solver import BaseTSPSolver
from uniride_core.algorithms.engine_factory import CORE_TSP_SOLVERS, create_matrix_engine
import importlib


def _is_routing_problem(problem) -> bool:
    return str(getattr(problem, "problem_type", "tsp") or "tsp").lower() in {
        "cvrp", "cvrptw", "uniride", "uniride_cvrp", "uniride_cvrptw"
    }


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
            tour_cost=round(float(cost), 2),
            gap_pct=round(gap, 4) if gap is not None else None,
            elapsed_sec=round(elapsed, 4),
            iterations=int(params.get("max_iterations", 0) or 0),
            tour=tour_indices,
            objective_cost=round(float(cost), 2),
            problem_type=str(getattr(problem, "problem_type", "tsp") or "tsp").lower(),
            matrix_kind=matrix_kind,
        )

    return executor

# 1. Register Numba (Legacy) Algorithms
def _make_legacy_executor(strategy_payload: any, algorithm_type: str):
    def executor(problem, params, seed, run_idx):
        import time
        from academic_benchmark.engine_core import RunResult
        import math
        if _is_routing_problem(problem):
            return _run_core_routing_executor(problem, params, seed, run_idx, "core-greedy-routing")
        
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
            # Fallback for standard TSPLIB
            try:
                from academic_benchmark.tsplib_manager import get_distance_matrix
                import os
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tsplib_data", "tsplib.db")
                dist_matrix_np = get_distance_matrix(problem.name, db_path)
            except Exception:
                dist_matrix_np = None
                
            unique_locs = [f"L{i+1}" for i in range(dimension)]
            if dist_matrix_np is None:
                # Use coordinates fallback
                from uniride_core.algorithms.numba_utils import create_np_distance_matrix
                dist_matrix_np = create_np_distance_matrix(problem.coordinates)
            duration_func = create_np_duration_func(dist_matrix_np, unique_locs)
            dist_matrix = dist_matrix_np.tolist()
            
        import random
        indices = list(range(1, dimension + 1))
        random.seed(seed)
        random.shuffle(indices)
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
            
        tour_length = int(tour_length) if not is_tm else round(tour_length, 2)
        
        optimal = getattr(problem, "optimal", None)
        gap = None
        if optimal and optimal > 0:
            gap = ((tour_length - optimal) / optimal) * 100
            
        return RunResult(
            problem=problem.name, algorithm="legacy",
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=optimal, tour_cost=tour_length,
            gap_pct=gap, elapsed_sec=elapsed,
            iterations=0, tour=tour_indices
        )
    return executor

for name, payload, default_params in STRATEGIES:
    algo_type = default_params.get("algorithm_type", "local_search")
    AlgorithmRegistry.register(f"Numba-{name}")(_make_legacy_executor(payload, algo_type))
    # We could register param spaces here too, but for simplicity we rely on the old _build_doe_space inside cli_engine

# 2. Register SOTA Algorithms
_SUPPORTED_SOTA_ALGOS = {"E2BSO-TSP", "R2DMA-TSP", "P-AOEA-TSP", "CGO-TSP", "RUN-TSP", "ALNS-TSP"}
SOTA_ALGOS = [name for name in list_algorithm_names("sota_tsp") if name in _SUPPORTED_SOTA_ALGOS]
def _make_sota_executor(algo: str):
    def executor(problem, params, seed, run_idx):
        import time
        import math
        from academic_benchmark.engine_core import RunResult
        from academic_benchmark.benchmark_utils import compute_gap
        if _is_routing_problem(problem):
            return _run_core_routing_executor(problem, params, seed, run_idx, f"SOTA-{algo}:core-greedy-routing")
        
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
                result = solver.solve(problem.coordinates)
            
        elapsed = time.perf_counter() - start_time
        gap_pct, _ = compute_gap(problem.name, result.tour_length, problem.optimal)
        
        # SOTA solvers return 0-indexed tours (0..N-1). Convert to 1-indexed to align with legacy executor.
        tour_1indexed = [idx + 1 for idx in result.tour] if result.tour else None
        
        return RunResult(
            problem=problem.name, algorithm=f"SOTA-{algo}",
            run=run_idx, seed=seed, dimension=problem.dimension,
            optimal=problem.optimal, tour_cost=int(result.tour_length),
            gap_pct=round(gap_pct, 4) if not math.isnan(gap_pct) else None,
            elapsed_sec=round(elapsed, 3),
            iterations=result.iterations,
            tour=tour_1indexed
        )
    return executor

for algo in SOTA_ALGOS:
    AlgorithmRegistry.register(f"SOTA-{algo}")(_make_sota_executor(algo))


def _core_greedy_executor(problem, params, seed, run_idx):
    return _run_core_routing_executor(problem, params, seed, run_idx, "Core-Greedy-Routing")


AlgorithmRegistry.register("Core-Greedy-Routing")(_core_greedy_executor)


for algo_name, solver in CORE_TSP_SOLVERS.items():
    AlgorithmRegistry.register(algo_name)(_make_core_tsp_executor(algo_name, solver))


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
    "Core-TwoOpt-TSP": "Core-TwoOpt-TSP",
    "Core-GA-TSP": "Core-GA-TSP",
    "Core-PSO-TSP": "Core-PSO-TSP",
    "Core-GWO-TSP": "Core-GWO-TSP",
    "Core-HHO-TSP": "Core-HHO-TSP",
    "Numba-2-opt": "Core-TwoOpt-TSP",
    "Numba-3-opt-bounded": "Core-TwoOpt-TSP",
    "Numba-Or-opt": "Core-TwoOpt-TSP",
    "Numba-Swap": "Core-TwoOpt-TSP",
    "Numba-Hybrid": "Core-TwoOpt-TSP",
    "Numba-GA": "Core-GA-TSP",
    "Numba-PSO": "Core-PSO-TSP",
    "Numba-GWO": "Core-GWO-TSP",
    "Numba-HHO": "Core-HHO-TSP",
    "GA-Split": "Core-GA-TSP",
    "PSO-Split": "Core-PSO-TSP",
    "GWO-Split": "Core-GWO-TSP",
    "HHO-Split": "Core-HHO-TSP",
}

for problem_prefix in ("CVRP", "CVRPTW"):
    for base_name, engine_name in _ROUTING_ALIAS_ENGINES.items():
        alias = f"{problem_prefix}-{base_name}"
        AlgorithmRegistry.register(alias)(_make_routing_alias_executor(alias, engine_name))
    for solver_name in ("OR-Tools", "PyVRP", "VROOM"):
        alias = f"{problem_prefix}-{solver_name}"
        AlgorithmRegistry.register(alias)(_make_holistic_routing_executor(alias, solver_name))

logger.info("Loaded %d algorithms.", len(AlgorithmRegistry.list_algorithms()))
