# Progress Log

## 2026-04-30

- Initialized plan files for Option B implementation.
- Completed comparative review between `optimizer_api/strategies/sota_common` and `academic_benchmark/sota_tsp`.
- Confirmed user-approved scope:
  - Add `3-opt` to TSP LS full chain.
  - Add `Regret3Insertion`.
  - Improve `R2DMA-TSP` resonance parity.
  - Fix Numba fallback worker import path.
  - Make seed generation deterministic via `hashlib`.
- Implemented `3-opt` layer in `academic_benchmark/sota_tsp/ls_engine.py` and wired into full intensity chain.
- Implemented `Regret3Insertion` in `academic_benchmark/sota_tsp/repair_ops.py` and integrated into E2BSO/R2DMA/P-AOEA repair pools.
- Improved `R2DMA-TSP` resonance with optional distance-profile signal and updated internal call sites.
- Added robust worker backend resolver `get_worker_backend_module()` in `academic_benchmark/run_smart_benchmark_numba.py` and switched worker import to dynamic backend.
- Added deterministic seed function `make_deterministic_seed()` in `academic_benchmark/run_smart_benchmark_sota.py` and replaced Python `hash()` usage.
- Added validation-oriented tests under `academic_benchmark/tests/`.
- Validation passed:
  - `py_compile` on updated files.
  - Deterministic seed stability check.
  - Worker backend fallback selection check.
  - SOTA smoke benchmark run (`berlin52`, 3 algorithms, `--re-run`) successful.
