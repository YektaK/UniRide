"""
UniRide Core

A framework-agnostic Python package for CVRPTW and TSP Optimization.
"""

from .models import (
    CVRPResult,
    ConstraintProfile,
    CostMatrix,
    PermutationResult,
    ProblemInstance,
    RoutingProblem,
    RoutingResult,
    TSPResult,
)
from .benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkResult, MatrixBenchmarkRunner

__all__ = [
    "ProblemInstance",
    "TSPResult",
    "CostMatrix",
    "ConstraintProfile",
    "RoutingProblem",
    "PermutationResult",
    "RoutingResult",
    "CVRPResult",
    "MatrixAlgorithmConfig",
    "MatrixBenchmarkResult",
    "MatrixBenchmarkRunner",
]
