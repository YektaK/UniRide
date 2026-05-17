"""
SOTA TSP — State-of-the-Art TSP Algorithm Variants

TSP-native implementations of E²BSO, R²DMA, and P-AOEA.
Uses integer-indexed tours, Numba-accelerated distance computation,
and the same interface as bildiri2026/core solvers.

Usage:
    from academic_benchmark.sota_tsp import E2BSO_TSP, R2DMA_TSP, PAOEA_TSP

    solver = E2BSO_TSP()
    result = solver.solve(coordinates)
    print(result.tour_length, result.elapsed_ms)
"""

from .base_solver import BaseTSPSolver, TSPResult
from .base_solver import BaseTSPSolver, TSPResult
from .e2bso_tsp import E2BSO_TSP, E2BSOTSPConfig, E2BSO_TSP_CPSO, E2BSOCPSPConfig
from .r2dma_tsp import R2DMA_TSP, R2DMATSPConfig
from .paoea_tsp import PAOEA_TSP, PAOEAConfig
from .cgo_tsp import CGO_TSP, CGOConfig
from .run_tsp import RUN_TSP, RUNConfig
from .ls_engine import MultiLayerLS

__all__ = [
    "BaseTSPSolver",
    "TSPResult",
    "E2BSO_TSP",
    "E2BSOTSPConfig",
    "E2BSO_TSP_CPSO",
    "E2BSOCPSPConfig",
    "R2DMA_TSP",
    "R2DMATSPConfig",
    "PAOEA_TSP",
    "PAOEAConfig",
    "CGO_TSP",
    "CGOConfig",
    "RUN_TSP",
    "RUNConfig",
    "MultiLayerLS",
]

SOTA_TSP_VERSION = "1.0.0"
