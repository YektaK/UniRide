# Findings

## Current mismatch areas (`optimizer_api` vs `academic_benchmark/sota_tsp`)

1. `ls_engine.py` lacks `3-opt` layer in full mode.
2. `repair_ops.py` lacks `Regret3Insertion`.
3. `r2dma_tsp.py` resonance metric is simplified (edge+position blend), not close to multi-component version in `optimizer_api`.
4. `run_smart_benchmark_numba.py` fallback path still imports numba-only module in worker process.
5. `run_smart_benchmark_sota.py` seeds use Python `hash()`, not deterministic across runs/processes.

## Validation baseline

- Syntax check for benchmark entry scripts passed.
- SOTA smoke run on `berlin52` with all three TSP SOTA variants passed.
