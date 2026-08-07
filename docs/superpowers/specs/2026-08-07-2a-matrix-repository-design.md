# 2A-MATRIX-REPO — Injectable Matrix Repository (design)

Status: PROPOSED
Date: 2026-08-07
Package: phase2 item 1 (first serial workstream of Phase 2)
Branch: `codex/phase2-matrix-repository-20260807` (from origin/WIP @ 1b2ac03)
Docs: `docs/superpowers/plans/2026-08-07-2a-matrix-repository.md`

## Why (evidence against WIP @ 1b2ac03)

`ACTIVE_ROADMAP.md` Phase 2, item 1:

> Preserve the verified process-level singleton while extracting an injectable
> matrix repository with explicit lifecycle, cache-health, and test boundaries.

Current state: `DataLoader` (`optimizer_api/utils/data_loader.py`) is a
`SingletonMeta` class that:
- builds the NxN travel-time matrix from Supabase at construction
  (`data_loader.py:43-51`), falling back to coordinate-based distance;
- exposes cache TTL + staleness (`_cache_ttl_seconds`, `_is_cache_stale`,
  `refresh`) — good;
- mixes four concerns in one class: provider I/O (`_load_from_supabase`),
  cache state (`_loaded_at`, `time_matrix`, `_use_coordinates`), lifecycle
  (`refresh`), and matrix construction (`build_*_matrix` + `get_submatrix`).

Problems with the current shape:

1. **Not injectable.** The singleton is `DataLoader` itself. Tests that need a
   fake must monkeypatch `DataLoader.get_instance` (12 call sites in
   `test_strategy_rng_state.py`, `test_seed_contract.py`, etc.), and the fake
   must re-implement the whole `get_submatrix` surface. There is no seam to
   inject a repository with controlled provider/cache behavior.
2. **No explicit lifecycle.** `__init__` performs network I/O as a side
   effect; there is no `close`/`reset` boundary, so test isolation between
   cases depends on module-global singleton state.
3. **No health metadata.** Callers cannot query whether the cache is fresh,
   how old it is, how many locations/edges are loaded, or whether the fallback
   coordinate path is active.

## Scope (this package only)

- `optimizer_api/utils/matrix_repository.py` (NEW):
  - `TimeMatrixRepository` — plain (non-singleton) class owning cache state,
    provider hook, lifecycle, and health.
  - `TravelTimeProvider` protocol — `fetch_rows() -> List[Row]` so Supabase
    and test doubles share one seam.
  - `SupabaseTimeMatrixProvider` — the existing `_load_from_supabase` logic,
    moved verbatim.
- `optimizer_api/utils/data_loader.py`: `DataLoader` keeps
  `SingletonMeta` (the verified process-level singleton) but composes a
  `TimeMatrixRepository` and delegates `get_submatrix`, `get_duration`,
  `has_location`, `refresh`, staleness to it. `get_instance()` alias stays.
  Static builders (`build_euclidean_matrix`, `build_haversine_matrix`) stay.
- `optimizer_api/utils/patterns.py`: unchanged.
- Tests: NEW `optimizer_api/tests/test_matrix_repository.py`:
  - provider seam (fake provider rows → matrix build);
  - cache TTL staleness with injected clock;
  - `refresh(force=True)` reloads;
  - `health()` metadata (fresh, stale, coordinate-fallback, counts);
  - `close()`/`reset()` clears state (lifecycle/test boundary);
  - DataLoader composes repository: singleton delegation + `get_instance`
    back-compat still passes existing suites.
- Docs: this design, plan, `ACTIVE_ROADMAP.md` mark item done (after merge).

Explicitly OUT of scope (later Phase 2 items): provider timeouts/retry
(item 2), matrix provenance/arc validation (item 3), separating production
travel time from academic metrics (item 4), bounded typed configs (item 5).

## Design

### `TimeMatrixRepository`

```python
class TimeMatrixRepository:
    def __init__(self, provider, ttl_seconds=600, clock=time.time, rng=None):
        self._provider = provider
        self._ttl = ttl_seconds
        self._clock = clock
        self._locations = []
        self._loc_to_idx = {}
        self._time_matrix = None
        self._loaded_at = None
        self._use_coordinates = True
        self._last_error = None

    def load(self) -> None            # one-shot initial load; sets fallback on failure
    def refresh(self, force=False)    # double-checked TTL refresh
    def close(self) -> None           # clear cache + state (test boundary)
    def health(self) -> Dict          # loaded, stale, age_seconds, locations, edges,
                                      # source: "supabase"|"coordinates"|"empty", last_error
    def get_submatrix(...)            # moved verbatim from DataLoader
    def get_duration(...)
    def has_location(...)
```

- `provider` is a `TravelTimeProvider` with a single `fetch_rows()`; the
  Supabase provider builds rows from the `time_matrix` table. A test provider
  returns fixed rows; a failing provider triggers the coordinate fallback and
  records `last_error`.
- `clock` is injected so TTL tests advance time deterministically.
- `load()` is called from `DataLoader.__init__` (same eager behavior), and
  `refresh()` keeps the existing double-checked-lock semantics.

### `DataLoader` (kept singleton, now a facade)

- `__init__` builds `self._repository` from `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`
  env or a coordinate-only repo; delegates public methods.
- Keeps `get_instance()` and `SingletonMeta` unchanged — all 12+ strategy
  call sites and monkeypatch-based tests keep passing untouched.
- Optional constructor seam: `DataLoader(repository=...)` is honored only
  when the singleton has not yet been created, giving direct-injection tests
  a clean boundary without monkeypatching.

## Verification gates

- NEW `test_matrix_repository.py` green (provider seam, TTL clock, force
  refresh, health, close, DataLoader delegation).
- Existing suites untouched and green: `test_data_loader_matrix_helpers.py`,
  `test_strategy_rng_state.py`, `test_seed_contract.py`, occurrence-identity
  suites (they patch `DataLoader.get_instance`, which still exists).
- Full regression green (`optimizer_api/tests`, `uniride_core/tests`,
  `academic_benchmark/tests`).
- `git diff --check` clean.
- FF-merge into WIP, push origin/WIP, CI green on `WIP`.

## Done when

- `DataLoader` delegates to an injectable `TimeMatrixRepository`; the
  singleton is preserved and all existing callers/tests pass unchanged.
- Cache-health (`health()`), lifecycle (`load`/`refresh`/`close`), and the
  provider seam are pinned by tests with an injected clock and a fake
  provider (no network in tests).