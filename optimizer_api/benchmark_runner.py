"""
Benchmark Runner for Algorithm Comparison

Migrated from: .proposed_changes/10.04.2026/TSP_Benchmark_Studio-main/upload/

This module runs TSP/CVRP benchmarks against multiple algorithms and collects metrics.

D-1 FIX (14.04.2026): TSPLIB-native tour distance calculation.
Instead of relying on strategy's broken total_distance_km=0.0, we compute
euclidean tour distance directly from original TSPLIB coordinates using
the route_details node sequence.
"""

import asyncio
import json
import time
import random
import math
import numpy as np
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


from uniride_core.models import ProblemInstance

from verification.response_certifier import certify_benchmark_response


@dataclass
class AlgorithmConfig:
    """Configuration for an algorithm run"""
    name: str
    algorithm_id: str
    params: Dict = field(default_factory=dict)


@dataclass
class ExperimentResult:
    """Result of running one algorithm on one problem"""
    algorithm: str
    problem: str
    run_number: int
    tour_length: float
    elapsed_ms: float
    gap_percent: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict = field(default_factory=dict)


class BenchmarkRunner:
    """
    Runs benchmark experiments comparing multiple algorithms.
    
    ARCHITECTURE CHANGES (13.04.2026):
    - Added state_manager parameter for progress tracking
    - Added run_id parameter for state identification
    - Updates state_manager.update_progress() during execution
    - Calls state_manager.complete_run()/fail_run() at end
    
    D-1 FIX (14.04.2026):
    - _compute_tsplib_tour_distance(): Computes euclidean distance from route_details
    - _benchmark_problem_to_optimization_request(): For TSP, sets capacity=dimension to force single tour
    - _run_single_experiment(): Uses TSPLIB-native distance instead of broken total_distance_km
    
    This allows non-blocking web integration:
    - Daemon thread in main.py calls runner.run()
    - Runner updates state_manager while executing
    - Frontend polls /api/v1/benchmark/status for progress
    """
    
    def __init__(self, strategies_registry=None, state_manager=None, run_id=None):
        self.strategies_registry = strategies_registry
        self.state_manager = state_manager
        self.run_id = run_id
        self.results: List[ExperimentResult] = []
        self.start_time: Optional[float] = None
        self.running = False
    
    # ============================================================
    # D-1: TSPLIB-native distance calculation
    # ============================================================
    
    def _build_coord_index(self, problem: ProblemInstance) -> Dict[str, Tuple[float, float]]:
        """
        Build mapping from location_id -> (x, y) for distance calculation.
        
        Maps the location codes used by strategies back to original TSPLIB coordinates:
          - "depot" -> coordinates[depot_index]
          - "loc_{i}" -> coordinates[i]
          - "student_{i}" -> coordinates[i]
        """
        coord_index: Dict[str, Tuple[float, float]] = {}
        for i, coord in enumerate(problem.coordinates):
            if i == problem.depot_index:
                coord_index["depot"] = coord
            coord_index[f"loc_{i}"] = coord
            coord_index[f"student_{i}"] = coord
        return coord_index
    
    def _compute_tsplib_tour_distance(self, problem: ProblemInstance, response) -> float:
        """
        Compute actual TSPLIB tour distance from strategy response.

        Uses the correct TSPLIB distance function based on the problem's
        edge_weight_type (EUC_2D, GEO, ATT, CEIL_2D), not just EUC_2D.

        Args:
            problem: Original ProblemInstance with TSPLIB coordinates
            response: OptimizationResponse from strategy.optimize()

        Returns:
            Total tour distance (float, integer-valued for EUC_2D/GEO/ATT). NaN if failed.
        """
        from utils.tsplib_parser import tsplib_distance_by_type

        ewt = getattr(problem, "edge_weight_type", "EUC_2D")
        coord_index = self._build_coord_index(problem)
        total_distance = 0
        steps_found = 0
        steps_missing = 0

        for route in response.routes:
            if not route.route_details:
                continue
            for step in route.route_details:
                c1 = coord_index.get(step.location1)
                c2 = coord_index.get(step.location2)
                if c1 and c2:
                    total_distance += tsplib_distance_by_type(ewt, c1, c2)
                    steps_found += 1
                else:
                    steps_missing += 1

        if steps_missing > 0:
            logger.warning(
                f"[Benchmark] {steps_missing}/{steps_found + steps_missing} steps "
                f"could not be mapped to coordinates for {problem.name}"
            )

        if steps_found == 0:
            return float('nan')

        return float(total_distance)
    
    # ============================================================
    # Problem -> Request conversion
    # ============================================================
    
    def _benchmark_problem_to_optimization_request(self, problem: ProblemInstance, algorithm_id: str):
        """
        Convert ProblemInstance -> OptimizationRequest for real strategy dispatch.
        
        Handles both TSP (single tour) and CVRPTW (multi-vehicle) problem formats.
        
        KEY (D-1): For TSP problems, capacity is set to problem.dimension so ALL nodes
        fit in a single vehicle — producing a single tour comparable to TSPLIB optimal.
        """
        from models.schemas import (
            OptimizationRequest, OptimizationMode, TripDirection,
            LocationNode, StudentNode
        )
        
        # Step 1: Create depot
        depot_coord = problem.coordinates[problem.depot_index]
        depot = LocationNode(
            id="depot",
            lat=depot_coord[0],
            lng=depot_coord[1],
            type="So"
        )
        
        # Step 2: Create students
        students = []
        for i, coord in enumerate(problem.coordinates):
            if i == problem.depot_index:
                continue
            student = StudentNode(
                id=f"student_{i}",
                name=f"Student {i}",
                location_code=f"loc_{i}",
                coordinates={"lat": coord[0], "lng": coord[1]},
                disability_type="So"
            )
            students.append(student)
        
        # Step 3: Detect problem type
        use_time_windows = problem.problem_type == "cvrptw" and problem.time_windows is not None
        is_asymmetric = problem.problem_type == "atsp"
        
        # Step 4: For TSP/ATSP, force single-vehicle tour by setting capacity = dimension
        # This ensures the strategy produces ONE tour visiting ALL nodes,
        # which is directly comparable to the TSPLIB optimal solution.
        is_single_tour = problem.problem_type in ("tsp", "atsp")
        if is_single_tour:
            capacity = problem.dimension  # All nodes in one vehicle
            max_travel = 99999  # No time constraint for pure TSP
        else:
            capacity = problem.capacity or 4
            max_travel = 180
        
        # Step 5: Determine best algorithm (promote to Split for CVRPTW if needed)
        best_algo = algorithm_id
        if problem.problem_type == "cvrptw":
            if algorithm_id in ["ga", "pso", "gwo", "hho"]:
                best_algo = f"{algorithm_id}_split"
        
        # Step 6: Build OptimizationRequest
        request = OptimizationRequest(
            algorithm=best_algo,
            students=students,
            depot=depot,
            max_travel_time=max_travel,
            sw_capacity=capacity,
            so_capacity=capacity,
            direction=TripDirection.PICKUP,
            use_time_windows=use_time_windows,
            mode=OptimizationMode.BENCHMARK,
            is_asymmetric=is_asymmetric
        )
        
        return request
    
    # ============================================================
    # Main benchmark execution
    # ============================================================
    
    def run(
        self,
        problems: List[ProblemInstance],
        algorithms: List[AlgorithmConfig],
        n_runs: int = 3,
        seed: int = 42,
        skip_cached: bool = False
    ) -> Tuple[List[ExperimentResult], Dict]:
        """
        Run benchmark experiments.
        
        Args:
            problems: List of benchmark problems
            algorithms: List of algorithm configurations
            n_runs: Number of runs per problem-algorithm combination
            seed: Random seed for reproducibility
            skip_cached: If True, skip cached results
            
        Returns:
            Tuple of (results, metadata)
        """
        self.results = []
        self.running = True
        self.start_time = time.time()
        
        random.seed(seed)
        np.random.seed(seed)
        
        metadata = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "total_experiments": len(problems) * len(algorithms) * n_runs,
            "problems_count": len(problems),
            "algorithms_count": len(algorithms),
            "n_runs": n_runs,
            "seed": seed
        }
        
        completed = 0
        
        try:
            for problem in problems:
                for algorithm in algorithms:
                    for run_num in range(1, n_runs + 1):
                        if not self.running:
                            break
                        
                        try:
                            result = self._run_single_experiment(
                                problem, algorithm, run_num
                            )
                            self.results.append(result)
                            completed += 1
                            
                            # Update state manager for web progress tracking
                            if self.state_manager and self.run_id:
                                self.state_manager.update_progress(
                                    self.run_id,
                                    completed,
                                    f"Completed: {algorithm.algorithm_id} on {problem.name} "
                                    f"(run {run_num}) - {completed}/{metadata['total_experiments']}"
                                )
                                from dataclasses import asdict
                                self.state_manager.add_result(self.run_id, asdict(result))
                            
                            gap_str = (
                                f"{result.gap_percent:.1f}%"
                                if result.gap_percent is not None and not math.isnan(result.gap_percent)
                                else "n/a"
                            )
                            logger.info(
                                f"[{completed}/{metadata['total_experiments']}] "
                                f"{algorithm.algorithm_id} on {problem.name} "
                                f"(run {run_num}): tour={result.tour_length:.1f} "
                                f"gap={gap_str} "
                                f"({result.elapsed_ms:.1f}ms)"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error running {algorithm.algorithm_id} "
                                f"on {problem.name} (run {run_num}): {e}"
                            )
                    
                    if not self.running:
                        break
        
        finally:
            self.running = False
            elapsed = time.time() - self.start_time
            metadata["end_time"] = datetime.now(timezone.utc).isoformat()
            metadata["elapsed_seconds"] = elapsed
            metadata["completed_experiments"] = completed
            
            if self.state_manager and self.run_id:
                self.state_manager.complete_run(
                    self.run_id,
                    len(self.results),
                    f"Benchmark completed: {len(self.results)} results in {elapsed:.1f}s"
                )
                logger.info(f"[Benchmark Complete] {self.run_id}: marked as complete in state manager")
        
        return self.results, metadata
    
    def _run_single_experiment(
        self,
        problem: ProblemInstance,
        algorithm: AlgorithmConfig,
        run_number: int
    ) -> ExperimentResult:
        """
        Run a single algorithm on a single problem using real strategy dispatch.
        
        D-1 FIX: Computes tour_length using euclidean distance from original
        TSPLIB coordinates, NOT from strategy's broken total_distance_km.
        """
        start_time = time.time()
        execution_failed = False
        response = None
        
        try:
            # Get strategy from registry
            strategy = None
            if self.strategies_registry:
                strategy = self.strategies_registry.get(algorithm.algorithm_id)
            
            if not strategy:
                from strategies import get_strategy
                strategy = get_strategy(algorithm.algorithm_id)
            
            if not strategy:
                raise ValueError(f"Strategy not found: {algorithm.algorithm_id}")
            
            # Convert benchmark problem to optimization request
            request = self._benchmark_problem_to_optimization_request(
                problem,
                algorithm.algorithm_id
            )
            self._apply_algorithm_params(request, algorithm.algorithm_id, algorithm.params)
            
            # Call real strategy
            response = strategy.optimize(request)
            
            if not response.success:
                logger.warning(
                    f"Strategy {algorithm.algorithm_id} failed on {problem.name}: "
                    f"{response.error_message}"
                )
                execution_failed = True
                tour_length = float('nan')
            else:
                # D-1: Compute tour distance DIRECTLY from TSPLIB coordinates
                # This bypasses strategy's broken total_distance_km=0.0 issue
                tour_length = self._compute_tsplib_tour_distance(problem, response)
                
                # Fallback: if TSPLIB computation returns NaN, try response metrics
                if isinstance(tour_length, float) and tour_length != tour_length:
                    total_dist = sum(r.total_distance_km for r in response.routes)
                    tour_length = total_dist if total_dist > 0 else float('nan')
        
        except Exception as e:
            logger.warning(
                f"Strategy execution failed for {algorithm.algorithm_id} on {problem.name}: "
                f"{str(e)}",
                exc_info=True
            )
            execution_failed = True
            tour_length = float('nan')
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        gap_percent = None
        if problem.optimal and not (isinstance(tour_length, float) and tour_length != tour_length):
            gap_percent = ((tour_length - problem.optimal) / problem.optimal) * 100
        
        routes_count = len(response.routes) if response else 0

        metadata = {
            "problem_dimension": problem.dimension,
            "problem_type": problem.problem_type,
            "problem_category": problem.category,
            "algorithm_params": algorithm.params,
            "execution_failed": execution_failed,
            "routes_count": routes_count,
            "vehicles_used": routes_count,
        }

        if response is not None:
            try:
                metadata["feasibility_certificate"] = certify_benchmark_response(
                    problem, response
                )
            except Exception:
                logger.warning(
                    f"Feasibility certification failed for {algorithm.algorithm_id} "
                    f"on {problem.name}",
                    exc_info=True
                )
        
        return ExperimentResult(
            algorithm=algorithm.algorithm_id,
            problem=problem.name,
            run_number=run_number,
            tour_length=tour_length,
            elapsed_ms=elapsed_ms,
            gap_percent=gap_percent,
            metadata=metadata,
        )

    def _apply_algorithm_params(self, request, algorithm_id: str, params: Dict[str, Any]) -> None:
        """Attach benchmark overrides to existing strategy-specific request config fields."""
        if not params:
            return

        clean_params = {key: value for key, value in params.items() if value is not None and value != ""}
        if not clean_params:
            return

        if "local_search_type" in clean_params:
            request.local_search_type = str(clean_params["local_search_type"])

        config_params = {key: value for key, value in clean_params.items() if key != "local_search_type"}
        key = algorithm_id.lower().replace("-", "_")

        if key in {"genetic_algorithm", "ga", "ga_split"}:
            request.ga_config = config_params
        elif key in {"pso", "pso_split"}:
            request.pso_config = config_params
        elif key in {"gwo", "grey_wolf", "gwo_split"}:
            request.gwo_config = config_params
        elif key in {"hho", "harris_hawks", "hho_split"}:
            request.hho_config = config_params
        elif key in {"e2bso", "entropy_bso", "e2b", "r2dma", "rdma", "paoea", "aoea"}:
            request.sota_config = config_params
        elif key in {"two_opt", "2opt"}:
            request.two_opt_config = config_params
    
    def stop(self):
        """Stop benchmark execution."""
        self.running = False
    
    def get_results_summary(self, results: List[ExperimentResult]) -> Dict:
        """
        Get summary statistics for results.
        
        Returns:
            Dict with aggregated metrics by algorithm and problem
        """
        summary = {}
        
        # Group by algorithm
        by_algo: Dict[str, List] = {}
        for result in results:
            if result.algorithm not in by_algo:
                by_algo[result.algorithm] = []
            by_algo[result.algorithm].append(result)
        
        # Compute statistics
        for algo_id, algo_results in by_algo.items():
            # Filter out NaN tour lengths
            valid_results = [r for r in algo_results 
                           if not (isinstance(r.tour_length, float) and r.tour_length != r.tour_length)]
            
            if not valid_results:
                continue
                
            lengths = [r.tour_length for r in valid_results]
            times = [r.elapsed_ms for r in valid_results]
            gaps = [r.gap_percent for r in valid_results if r.gap_percent is not None]
            
            summary[algo_id] = {
                "avg_tour_length": float(np.mean(lengths)),
                "min_tour_length": float(np.min(lengths)),
                "max_tour_length": float(np.max(lengths)),
                "std_tour_length": float(np.std(lengths)),
                "avg_time_ms": float(np.mean(times)),
                "min_time_ms": float(np.min(times)),
                "avg_gap_percent": float(np.mean(gaps)) if gaps else None,
                "min_gap_percent": float(np.min(gaps)) if gaps else None,
                "best_gap_percent": float(np.min(gaps)) if gaps else None,
                "success_rate": len(valid_results) / len(algo_results) if algo_results else 0,
                "n_runs": len(valid_results),
            }
        
        return summary


__all__ = [
    "BenchmarkRunner",
    "ProblemInstance",
    "AlgorithmConfig",
    "ExperimentResult"
]
