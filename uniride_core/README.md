# uniride\_core

Framework-agnostic shared kernel for UniRide's dual-engine TSP/CVRPTW optimization system. Used by the production FastAPI compatibility layer and `academic_benchmark` research harness.

## Structure

```
uniride_core/
├── __init__.py           # Exports ProblemInstance, TSPResult
├── models.py             # Domain dataclasses
├── algorithms/
│   ├── base_solver.py    # BaseTSPSolver abstract class
│   ├── config.py         # MetaHeuristicConfig + per-solver configs
│   ├── utils.py          # Population diversity computation
│   ├── numba_accel.py    # JIT-accelerated local search kernels
│   └── sota_tsp/         # 5 SOTA metaheuristic solvers
│       ├── e2bso_tsp.py  # E²BSO-TSP + CPSO variant
│       ├── r2dma_tsp.py  # R²DMA-TSP
│       ├── paoea_tsp.py  # P-AOEA-TSP
│       ├── cgo_tsp.py    # Chaos Game Optimizer
│       ├── run_tsp.py    # Runge-Kutta Optimizer
│       ├── ls_engine.py  # MultiLayerLS local search
│       ├── repair_ops.py # Greedy/Regret-k insertion
│       └── destroy_ops.py# ALNS destroy operators
└── tests/
    └── sota_tsp/
        └── test_sota_algorithms.py
```

## Usage

```python
from uniride_core import ProblemInstance, TSPResult
from uniride_core.algorithms.sota_tsp import E2BSO_TSP, E2BSOTSPConfig

coords = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]
solver = E2BSO_TSP(E2BSOTSPConfig(seed=42))
result = solver.solve(coords)
# → TSPResult(tour=[...], tour_length=40.0, ...)

# With precomputed distance matrix:
result = solver.solve_with_matrix(matrix)
```

## Solvers

| Algorithm | Config | File |
|---|---|---|
| E²BSO-TSP (+ CPSO) | `E2BSOTSPConfig` / `E2BSOCPSPConfig` | `e2bso_tsp.py` |
| R²DMA-TSP | `R2DMATSPConfig` | `r2dma_tsp.py` |
| P-AOEA-TSP | `PAOEAConfig` | `paoea_tsp.py` |
| CGO-TSP | `CGOConfig` | `cgo_tsp.py` |
| RUN-TSP | `RUNConfig` | `run_tsp.py` |

All solvers inherit from `BaseTSPSolver` and support `solve(coordinates)` and `solve_with_matrix(matrix)`.

## Tests

```bash
cd <repo-root>
python -m pytest uniride_core/tests/sota_tsp/ -v
```
