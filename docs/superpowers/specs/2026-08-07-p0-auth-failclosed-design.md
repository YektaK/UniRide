# P0-AUTH — Close the Benchmark/CLI Authentication Gap (design)

Status: PROPOSED
Date: 2026-08-07
Package: phase0 hardening follow-up (serial workstream after 1D-objective)
Branch: `codex/phase1-p0-auth-failclosed-20260807` (from origin/WIP @ f07a80c)
Docs: `docs/superpowers/plans/2026-08-07-p0-auth-failclosed.md`

## Why (evidence against WIP @ f07a80c)

`ACTIVE_ROADMAP.md` Phase 0 still lists three open items:

1. Restrict FastAPI to a trusted network boundary.
2. Authenticate benchmark and CLI-import/preview endpoints.
3. Remove arbitrary `filepath` support.

Audit of the code:

| Roadmap item | Code state | Evidence |
|---|---|---|
| Restrict to trusted network boundary | **Partial.** `optimizer_host()` defaults to `127.0.0.1` (`runtime_config.py:5`) and `main.py:112` binds to it. No explicit docs/guard for non-loopback. | `test_phase0_containment.py::test_optimizer_host_defaults_to_loopback` |
| Authenticate benchmark + CLI endpoints | **Done, but fail-open when `INTERNAL_API_KEY` unset.** Router-level `Depends(require_internal_api_key)` on `benchmark.py:34`; CLI routes have per-endpoint deps. But `auth.py:11-13` returns **allow** when the env var is missing — any deployment without the key configured is wide open (can start benchmark runs and preview/import CLI result files). | `test_api_hardening_phase0.py` (403 path only when key is set), `test_phase0_containment.py::test_internal_key_is_optional_but_rejects_mismatch` |
| Remove arbitrary `filepath` | **Done.** `_resolve_cli_filename` restricts to `CLI_RESULTS_DIR` / `CLI_RESULTS_NUMBA_DIR`, rejects traversal and symlink escape; listing returns basenames only. | `test_phase0_containment.py` (5 file-path tests) |

The one real security hole is **fail-open authentication**: absent `INTERNAL_API_KEY` the benchmark surface (run, import, stop, results read, CLI files/preview/import) is unauthenticated. That contradicts the Phase 0 acceptance line: *"no unauthenticated endpoint can read caller-selected files or start unbounded compute."*

The user-facing routers (`/optimize`, `/compare`, `/vehicle-calculator`, `/extract-time-windows`, `/schedule-to-students`) are **intentionally public** for the frontend and the `/strategies` list is pinned open by `test_api_hardening_phase0.py::test_b1_public_strategies_endpoint_remains_open`. Gating those is out of scope (Phase 4 frontend auth, Phase 2 service auth).

## Scope (this package only)

- `optimizer_api/auth.py`: make `require_internal_api_key` **fail closed** — reject every request unless the internal API key env var is present and matches. When unset, deny (503 "auth not configured" is wrong; use 403 to keep semantics uniform — decide via `INTERNAL_API_KEY` presence at app startup and refuse to start in non-test servers; tests set the key explicitly).
  - Concretely: `expected = os.getenv("INTERNAL_API_KEY")`; if `expected is None` → `HTTPException(403, "Forbidden")` (deny) rather than allow. This keeps the dev story: developers set `INTERNAL_API_KEY` in `.env` (already loaded in `main.py:29`).
  - Update `test_phase0_containment.py::test_internal_key_is_optional_but_rejects_mismatch` to assert **deny when unset**.
  - Add a startup guard: `main.py` refuses to boot if `INTERNAL_API_KEY` is unset and not in a test/dev override, or logs a hard warning + fails fast. Simpler and testable: assert at import of `auth` module? No — tests import it. Do it in `main.py` module import (behind `APP_ENV != "test"`), and add a test that a sentinel-app without the key rejects benchmark calls.
- `runtime_config.py` / `main.py`: document loopback default; no bind change (already correct). Add a guard that refuses `OPTIMIZER_HOST` non-loopback unless `ALLOW_PUBLIC_BIND=1` (defense-in-depth for the "trusted network boundary" item) — with tests.
- `ACTIVE_ROADMAP.md`: mark the three Phase-0 items done after this lands.
- Docs: this design, plan, roadmap.

Explicitly OUT of scope: gating public `/optimize` etc. (Phase 2/4), TLS/certs, and full auth architecture (Phase 2).

## Design

### 1. `require_internal_api_key` fails closed

```python
async def require_internal_api_key(x_api_key=Header(default=None, alias="X-Internal-Api-Key")):
    expected = os.getenv("INTERNAL_API_KEY")
    if expected is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
```

Status code: **403** (matches existing benchmark rejection tests that assert `{"detail": "Forbidden"}`), not 503.

### 2. Startup guard (network boundary + key)

In `main.py`: refuse to boot unless `INTERNAL_API_KEY` is set or
`UNIRIDE_DISABLE_AUTH=1` (explicit dev/test opt-out) is present. This makes
misconfiguration loud instead of silent.

### 3. Bind guard

`runtime_config.optimizer_host()` already returns `127.0.0.1` by default. Add
`runtime_config.allow_public_bind()` returning `os.getenv("ALLOW_PUBLIC_BIND") == "1"`. In
`main.py` `__main__`, if a non-loopback host is requested without `ALLOW_PUBLIC_BIND=1`, raise
`SystemExit` with a clear diagnostic.

## Verification gates

- `test_phase0_containment.py` updated: fail-closed when key unset; loopback default preserved.
- New `optimizer_api/tests/test_phase0_auth_guard.py`: (a) benchmark endpoints 403 when key set but request lacks header — already covered; (b) request with correct key passes; (c) `main` module refuses to import (startup) without key; (d) bind guard raises on non-loopback.
- Full regression still green (`optimizer_api/tests`, `uniride_core/tests`, `academic_benchmark/tests`).
- `git diff --check` clean.
- FF-merge into WIP, push origin/WIP, CI green on `WIP`.

## Done when

- `ACTIVE_ROADMAP.md` Phase 0 items 1-3 show `[x]` with evidence notes.
- Removing `INTERNAL_API_KEY` from the env yields 403 on benchmark/CLL routes in tests, not allow.