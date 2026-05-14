# GWO & HHO Improvement Status

## GWO (`_run_gwo`)

| Improvement | Status | Detail |
|---|---|---|
| Memetic 2-opt initialization | ✅ DONE | `_apply_2opt_to_route(route, duration_func, max_iter=10)` on every wolf |
| Periodic 2-opt refinement | ✅ DONE | Every 10 iterations: α, β, δ are improved with 2-opt (iter=20) |
| Swap-sequence position update | ✅ DONE | Uses `_diff_swaps_str` + `_apply_swaps_str` (bildiri2026 PSO pattern) |
| Exploration/Exploitation via A | ✅ DONE | `|A|>1` → random pack target, `|A|<1` → leader target |
| Final 300-iter 2-opt polishing | ✅ DONE | `_apply_2opt_to_route(best_route, duration_func, max_iter=300)` |

## HHO (`_run_hho`)

| Improvement | Status | Detail |
|---|---|---|
| Memetic 2-opt initialization | ✅ DONE | `_apply_2opt_to_route(route, duration_func, max_iter=10)` on every hawk |
| Lévy flight mutation | ✅ DONE | Mantegna β=1.5, scale-proportional swap count |
| 4-phase besiege strategies | ✅ DONE | Soft/Hard besiege with/without rapid dives |
| Periodic 2-opt refinement | ✅ DONE | Every 10 iterations: best hawk improved with 2-opt (iter=20) |
| Final 300-iter 2-opt polishing | ✅ DONE | `_apply_2opt_to_route(best, duration_func, max_iter=300)` |

## Validation

- All 45 tests pass
- Gate validation passes
- 300-iter final 2-opt matches bildiri2026's `_two_opt_improve_atsp_numba(..., 300, False)`
- Swap-sequence position update matches bildiri2026's `_diff_swaps` + `_combine_velocities` pattern

## Files Modified

- `optimizer_api/tests/run_interactive_benchmark_v2_numba.py` — GWO/HHO functions
