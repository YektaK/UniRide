# Requested-Algorithm Policy — Verification

**Verified:** 2026-08-14
**Scope:** The mandatory feasibility certificate contract must apply to every
explicitly-requested algorithm — including non-default requested keys — on every
production surface that invokes a solver.

## Contract scope (in scope)

| Endpoint | Handler | Solver call | Certification | Delegation |
|----------|---------|-------------|---------------|------------|
| `POST /api/v1/optimize` | `optimize_route` (optimization.py:118) | `strategy.optimize(request)` (:145) | `certify_optimization_response(request, result)` (:181), unconditional; `success = original_success and certificate.is_feasible` (:184) | — |
| `POST /api/v1/compare` | `compare_algorithms` (optimization.py:371) | per-algorithm `strategy.optimize(effective_request)` in `_run_single_algorithm` (:315) | `certify_optimization_response(effective_request, response)` (:322), unconditional | — |
| `POST /api/v1/vehicle-calculator` | `calculate_vehicles` (optimization.py:511) | — | — | `return optimize_route(request)` (:512) → certified via `/optimize` |

The certifier (`certify_optimization_response`, response_certifier.py:196) is
solver-independent and fail-closed; it has no algorithm branch, so non-default
requested algorithms pass through the identical gate.

## Deliberately out of scope

- `GET /health`, `GET/POST /strategies`, and the benchmark router
  (`optimizer_api/routers/benchmark.py`) never invoke `strategy.optimize` and do
  not produce optimization-shaped routing payloads; benchmark results are
  governed by the academic execution-gateway `RunResult` contract instead.
- Non-HTTP `strategy.optimize` callers (`benchmark_runner.py`, `run_all_tests.py`,
  `test_*.py`) are development scripts/tests, not production surfaces.

## Escape audit

`rg -l "@router"` over `optimizer_api` yields four router files; `optimization.py`
is the only one that calls `strategy.optimize`. Both such call sites (optimization.py
:145 and :315) are immediately followed by a mandatory `certify_optimization_response`
call. **No code path allows a solver result to reach a caller without the certificate
contract.**

## Proof (confirmation suite)

`optimizer_api/tests/test_requested_algorithm_policy.py` — 22 tests:

- `test_real_non_default_requested_algorithm_certifies` (7 keys): a real solve for
  each always-available non-default requested key (`hho_split`, `gwo_split`,
  `pso_split`, `e2bso`, `rdma`, `paoea`, `permutation_tsp`) is admitted and certified
  feasible at the endpoint.
- `test_non_default_requested_algorithm_infeasible_success_is_demoted` (7): a solver
  claiming `success=True` with an occurrence-incomplete route is demoted to
  `success=False` at `/optimize`.
- `test_non_default_requested_algorithm_demoted_in_compare` (7): the same is demoted
  at `/compare`.
- `test_certification_line_is_load_bearing`: stubbing the certificate always-feasible
  lets a lying non-default algorithm pass — proving the endpoint certification line is
  the enforcement point. This is the mutation-removal property of the suite: remove the
  line and the demotion tests fail.

This is distinct from the roadmap "Mutation proof" item (closed at `d3b19de`), which
proves solver success cannot survive an injected hard violation; this verifies the
non-default *requested* dimension of the same gate.