# Findings

## Current mismatch areas (`optimizer_api` vs `academic_benchmark/sota_tsp`)

1. `ls_engine.py` lacks `3-opt` layer in full mode. ✅ FIXED (2026-04-30)
2. `repair_ops.py` lacks `Regret3Insertion`. ✅ FIXED (2026-04-30)
3. `r2dma_tsp.py` resonance metric is simplified (edge+position blend), not close to multi-component version in `optimizer_api`. ✅ FIXED (2026-04-30 — 6-dim resonance implemented)
4. `run_smart_benchmark_numba.py` fallback path still imports numba-only module in worker process. ✅ FIXED (2026-04-30)
5. `run_smart_benchmark_sota.py` seeds use Python `hash()`, not deterministic across runs/processes. ✅ FIXED (2026-04-30 — `make_deterministic_seed()` via hashlib)

## Validation baseline

- Syntax check for benchmark entry scripts passed.
- SOTA smoke run on `berlin52` with all three TSP SOTA variants passed.
- 22/22 academic_benchmark tests passing (2026-05-06).
