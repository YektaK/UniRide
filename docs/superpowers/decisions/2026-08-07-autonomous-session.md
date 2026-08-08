# Autonomous Work Session — Decision Log (DTOP Log)

Date: 2026-08-07
Scope: authorized autonomous continuation on `codex/phase2-matrix-repository-20260807` from origin/WIP `1a19261`.
Rule set: minimal code, explicit tradeoffs, durable decision record to prevent rework.

Each entry follows: **Context → Options → Chosen → Rationale → Evidence**.

---

## D1. Geo-distance "failure" — triage outcome

- **Context:** `uniride_core/tests/test_distance_properties.py::TestTSPLIB_GEO::test_max_range` failed in earlier full runs (and still failed on `1b2ac03`, the untouched base).
- **Options:**
  - A. Treat as a real production bug → fix `tsplib_geo_distance`.
  - B. Treat as a test-constant bug → correct the bound constant.
- **Chosen:** B (test-only fix, one line).
- **Rationale:** `tsplib_geo_distance` is byte-for-byte the canonical tsplib95 GEO formula
  (`int(RRR*acos(param)+1)`, `RRR=6378.388`, degree/minutes→DD.MM→radians; verified
  `_geo_convert` equivalently). The audit's/prod concern is *production* travel time;
  TSPLIB GEO only surfaces in the academic benchmark path, whose matrices are built by
  the same function (so a "fix" here would change benchmark values, not production route
  costs). The true antipodal max on R=6378.388 is `int(pi*R + 1) = 20039` (verified:
  `(0,0)->(0,180)=20039`, `(90,0)->(-90,0)=20039`, `(45,0)->(45,180)=10020`). The test
  asserted `<= 20000`, which is unconditionally below the physical maximum for any two
  legitimate GEO coordinates. Implementation correct; assertion too strict.
- **Change:** `TSPLIB_GEO_MAX = int(math.pi * 6378.388) + 1` (self-documenting, derived
  from the radius the formula itself uses). Full module: 45 passed; GEO subclass: 5 passed.
- **Risk if wrong:** If someone later argues GEO should be capped, it is an academic-metric
  decision, not a latent corruption — a change belongs with TSPLIB provenance work, not here.
- **Status 2026-08-07:** SHIPPED on `2B` branch (test-only commit).

---

## D2. Roadmap item 3: "Reject missing or invalid off-diagonal arcs"

- **Context:** Phase 2 hardening item. Audit P0 "Travel matrix corruption" lists three
  independent leak paths; two are already closed, one was open.
  - Path 1 "missing pairs may remain zero and become free arcs" → **open** via
    `TimeMatrixRepository.get_submatrix`/`get_duration` (0.0 for unknown/invalid pair).
  - Path 2 "lat/lng processed as abstract Euclidean" → separate issue (roadmap item 4).
  - Path 3 "generic 15-minute fallback" → **open** in `route_metrics.DEFAULT_TRAVEL_FALLBACK_MINUTES`
    = 15.0, used by `get_duration`/`calculate_route_duration` consumer (strategies).
- **Options:**
  - A. Raise a typed error inside the repository on *any* missing/invalid arc at lookup time.
  - B. Also make `route_metrics.get_duration` raise instead of 15-minute fallback.
  - C. Leave `route_metrics` as is; only fix the repository.
- **Chosen:** A + (for now, NOT B).
- **Rationale:**
  - The repository is the single owned boundary for the loaded travel-time matrix;
    strategies already call `get_submatrix` with (or without) coordinates, so
    fail-closed there covers the production path.
  - Narrowing to the repository = smallest diff; `route_metrics` fallback is a separate
    wide-affecting contract (used by many strategies/reporters with a DEFAULT parameter),
    changing it risks broad regressions and is better scoped as its own item (documented
    in ACTIVE_ROADMAP Phase 2 as "label fallback").
  - `get_submatrix` (all strategies) and `get_duration` (repo-level) both gate on it.
- **Evidence:** see new tests in `test_matrix_repository.py` (missing arc → raises;
  source==target still 0.0; coordinate path unchanged).
- **Tradeoff accepted:** strategies that previously received 0.0 for an unknown pair now
  fail the request. This is the intended fail-closed behavior; hot-covered by provider
  completeness (Supabase must yield a full matrix). No caller in tests relies on 0.0.
- **Status 2026-08-07:** SHIPPED on `2B`. `IncompleteTravelMatrixError(LookupError)`
  added in `matrix_repository.py`, re-exported via `data_loader`; `get_duration` and
  `get_submatrix` now reject missing/zero/negative/non-finite off-diagonal arcs
  (`_arc_value` helper); `source==target` remains 0.0; coordinate/fallback path untouched.
  Tests: `test_missing_arc_raises`, `test_zero_or_negative_arc_raises`.

---

## Issue 3a. Where to place the typed error

- **Options:**
  1. `optimizer_api/utils/matrix_repository.py` (new `IncompleteArcError(IncompleteTravelMatrixError?)`...).
  2. `uniride_core` so academic path can catch the same type.
- **Chosen:** repository module, re-exported from `data_loader` (keeps current imports working).
- **Rationale:** the repository is an *optimizer_api* (production) concept; academic path has
  its own handling. Single, near-zero-churn location. If academic needs the same later, it is a
  one-line import; not reworked now to stay minimal.

---

## D2. Roadmap item 2: provider timeout & last-known-good

- **Context:** audit P1: `SupabaseTimeMatrixProvider`/`create_client` has no explicit timeout;
  a stalled external request blocks startup/refresh. Also `refresh()` failure clears the cache
  to empty (no last-known-good).
- **Options:**
  1. Pass a timeout into the supabase client constructor (library-level; version-dependent).
  2. Wrap provider network call in a socket/thread timeout at the repository/provider seam.
  3. Do both: a configurable timeout constant + retry-safe load that keeps the previous matrix.
- **Chosen:** 3, minimal:
  - `SupabaseTimeMatrixProvider(**timeout**=SEMANTIC) with explicit `timeout` on the request call if
    the SDK supports it; else optional env `TIME_MATRIX_PROVIDER_TIMEOUT_SECONDS`.
  - `TimeTimeMatrixRepository.refresh()` failure via `load()`: if a matrix is already present,
    keep it and record `last_error`/staleness instead of clearing.
- **Rationale:** last-known-good is the cheaper, safer behavior change and is fully testable
  with the injected provider seam (no network in tests). The SDK-native timeout is best-effort
  and version-guarded (supabase client signatures vary); exact wiring documented, with env
  override and default.
- **Trade-off accepted:** if the SDK doesn't honor the kwarg, we remain at system default
  timeout; acceptance of that is documented and explicitly noted in roadmap open risks
  (rather than forcing an unstable postgrest hack).
- **Status 2026-08-07:** SHIPPED on `2B`. `SupabaseTimeMatrixProvider` accepts
  `timeout_seconds` (version-guarded `ClientOptions(postgrest_client_timeout=...)` with
  fallback to SDK default); `DataLoader` reads `TIME_MATRIX_PROVIDER_TIMEOUT_SECONDS`
  (default 10.0s) and passes it through; `TimeMatrixRepository.load()` now preserves a
  previously loaded matrix on refresh failure (last-known-good; health shows stale +
  `last_error`) while first-load failure still falls back to coordinates. Tests:
  `test_last_known_good_matrix_survives_failed_refresh`,
  `test_first_load_failure_still_falls_back`,
  `test_provider_timeout_plumbed_into_sdk_client` (skipped where `supabase` absent).

---

## D3. Audit follow-ups (2026-08-08): backoff, re-export, env guard, Path-3 strict

- **Context:** External-auditor rerun of the 2B shipment produced three low/moderate
  findings (no retry backoff → fetch storm; doc claimed `IncompleteTravelMatrixError`
  re-export that did not exist; unguarded env float parse) and re-opened audit Path 3
  (`route_metrics` 15-minute generic fallback still silently fabricates durations).
- **Chosen:** fix all four, minimal, with pinned tests.
  - F1: failed `load()` arms `_next_retry_at = clock + TTL`; `refresh()` skips the
    fetch while in backoff (force bypasses). LKG still served; storm gone.
  - F2: `data_loader` now re-exports `IncompleteTravelMatrixError` (doc claim true).
  - F3: TTL/timeout env parse wrapped in `ValueError` fallback to defaults.
  - Path-3: `route_metrics.get_duration`/`calculate_route_duration` gained
    `strict=False`; strict raises `TravelTimeUnavailableError` instead of the
    generic 15-minute estimate. `base_strategy._get_duration` (production seam)
    passes `strict=True`; academic default unchanged.
- **Evidence:** `test_retry_backoff_prevents_fetch_storm`,
  `test_force_refresh_bypasses_backoff`, `test_env_timeout_garbage_falls_back_to_default`,
  `test_get_duration_strict_raises_when_unavailable` (+ matrix/coordinate-hit and
  non-strict back-compat cases in `test_route_metrics.py`).
- **Tradeoff accepted:** strategies that previously received a fabricated 15-minute
  value for an unanswerable pair now fail the request deterministically. The full
  optimizer suite (427) and academic suite (338 core / 153 CI) stayed green, so no
  current caller depends on the fabrication.
- **Status 2026-08-08:** SHIPPED on `2B` (commits `f8a6b51`, Path-3 commit).

- No changes to `uniride_core` algorithms beyond: (a) the documented test-constant fix (D1);
  no solver/decode semantics changed.
- All new failure semantics are opt-in at the repository boundary or typed and testable.
- Each decision above is either implemented with pinned tests or registered as an open item
  with owner and evidence.
- Full scoped regression (3 dirs) stays green within the pre-existing status; any new red is
  only allowed if it also reds on base (documented).