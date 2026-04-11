"""
Benchmark Runner for Algorithm Comparison

Migrated from: .proposed_changes/10.04.2026/TSP_Benchmark_Studio-main/upload/

This module runs TSP/CVRP benchmarks against multiple algorithms and collects metrics.
"""

import asyncio
import json
import time
import random
import numpy as np
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkProblem:
    """A single benchmark problem instance"""
    name: str
    dimension: int
    coordinates: List[Tuple[float, float]]
    optimal_score: Optional[int] = None
    category: str = "medium"  # small, medium, large


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
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)


class BenchmarkRunner:
    """
    Runs benchmark experiments comparing multiple algorithms.
    
    Usage:
        runner = BenchmarkRunner()
        results = runner.run(problems, algorithms, n_runs=3)
    """
    
    def __init__(self, strategies_registry=None):
        """
        Initialize benchmark runner.
        
        Args:
            strategies_registry: Optional registry of available strategies.
                                If None, will be imported from optimizer_api.strategies
        """
        self.strategies_registry = strategies_registry
        self.results: List[ExperimentResult] = []
        self.start_time: Optional[float] = None
        self.running = False
    
    def run(
        self,
        problems: List[BenchmarkProblem],
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
            "start_time": datetime.utcnow().isoformat(),
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
                            
                            logger.info(
                                f"[{completed}/{metadata['total_experiments']}] "
                                f"{algorithm.algorithm_id} on {problem.name} "
                                f"(run {run_num}): {result.tour_length:.1f} "
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
            metadata["end_time"] = datetime.utcnow().isoformat()
            metadata["elapsed_seconds"] = elapsed
            metadata["completed_experiments"] = completed
        
        return self.results, metadata
    
    def _run_single_experiment(
        self,
        problem: BenchmarkProblem,
        algorithm: AlgorithmConfig,
        run_number: int
    ) -> ExperimentResult:
        """Run a single algorithm on a single problem."""
        
        start_time = time.time()
        
        # TODO: Call actual algorithm via strategies registry
        # For now, simulate with random result
        tour_length = 1000 + random.uniform(-100, 100)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        gap_percent = None
        if problem.optimal_score:
            gap_percent = ((tour_length - problem.optimal_score) / problem.optimal_score) * 100
        
        return ExperimentResult(
            algorithm=algorithm.algorithm_id,
            problem=problem.name,
            run_number=run_number,
            tour_length=tour_length,
            elapsed_ms=elapsed_ms,
            gap_percent=gap_percent,
            metadata={
                "problem_dimension": problem.dimension,
                "problem_category": problem.category,
                "algorithm_params": algorithm.params
            }
        )
    
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
        by_algo = {}
        for result in results:
            if result.algorithm not in by_algo:
                by_algo[result.algorithm] = []
            by_algo[result.algorithm].append(result)
        
        # Compute statistics
        for algo_id, algo_results in by_algo.items():
            lengths = [r.tour_length for r in algo_results]
            times = [r.elapsed_ms for r in algo_results]
            gaps = [r.gap_percent for r in algo_results if r.gap_percent is not None]
            
            summary[algo_id] = {
                "avg_tour_length": np.mean(lengths),
                "min_tour_length": np.min(lengths),
                "max_tour_length": np.max(lengths),
                "std_tour_length": np.std(lengths),
                "avg_time_ms": np.mean(times),
                "avg_gap_percent": np.mean(gaps) if gaps else None,
                "n_runs": len(algo_results)
            }
        
        return summary


__all__ = [
    "BenchmarkRunner",
    "BenchmarkProblem",
    "AlgorithmConfig",
    "ExperimentResult"
]
