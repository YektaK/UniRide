# 2A-MATRIX-REPO — Injectable Matrix Repository (plan)

Status: COMPLETE
Date: 2026-08-07
Package: phase2 item 1 (first serial workstream of Phase 2)
Branch: `codex/phase2-matrix-repository-20260807` (from origin/WIP @ 1b2ac03)
Docs: `docs/superpowers/specs/2026-08-07-2a-matrix-repository-design.md`

## Steps

1. **Docs first** (this plan + design doc committed on the branch).
2. **NEW `utils/matrix_repository.py`:**
   - `TravelTimeProvider` protocol (`fetch_rows()`).
   - `SupabaseTimeMatrixProvider` (logic moved verbatim from
     `DataLoader._load_from_supabase`).
   - `TimeMatrixRepository` (state, lifecycle, health, TTL w/ injected clock).
3. **Refactor `utils/data_loader.py`:** `DataLoader` keeps `SingletonMeta` +
   `get_instance()`, composes a `TimeMatrixRepository`, delegates
   `get_submatrix`/`get_duration`/`has_location`/`refresh`. Static builders
   stay. Optional `DataLoader(repository=...)` injection seam pre-singleton.
4. **NEW `optimizer_api/tests/test_matrix_repository.py`:** provider seam,
   TTL with fake clock, force refresh, health metadata, close/reset, DataLoader
   delegation.
5. **ROADMAP:** mark Phase 2 item 1 `[x]` with evidence after merge.
6. **Verify:** full regression (`optimizer_api/tests`, `uniride_core/tests`,
   `academic_benchmark/tests`), `git diff --check` clean.
7. **Merge:** FF-merge into WIP worktree, push origin/WIP, CI green.

## Evidence gates

- `test_matrix_repository.py` green with injected clock + fake provider,
  never touching the network.
- All existing `DataLoader` callers/tests pass unchanged (singleton and
  `get_instance` intact).
- `health()` distinguishes fresh / stale / coordinate-fallback / counts.
- Full regression green; `git diff --check` clean.

## Done when

- Singleton preserved; repository injectable; lifecycle + cache-health +
  provider seam pinned by tests.