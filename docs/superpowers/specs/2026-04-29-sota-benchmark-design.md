# SOTA Benchmark Rebuild Design (2026-04-29)

## Goal
Rebuild the SOTA benchmark around the academic_benchmark loader to ensure:
- TSPLIB problems are loaded from local .tsp files (downloaded if missing).
- Edge weight types are honored when computing distances.
- Optimal values are computed from .opt.tour when available (downloaded if missing).
- Historical benchmark results are kept only if recalculable under the corrected logic.
- The SOTA benchmark script is moved under academic_benchmark without breaking optimizer_api/UniRide.

## Scope
- Replace the current SOTA benchmark workflow with a loader-driven workflow in academic_benchmark.
- Add metric-aware distance computation and tour validation.
- Migrate or preserve historical CSV/summary files per the recalculation rules.
- Keep optimizer_api runtime behavior intact (no breaking changes to UniRide app).

## Non-Goals
- No changes to algorithm implementations beyond how they are invoked in SOTA benchmark.
- No changes to public APIs in optimizer_api.

## Approach Summary
- Recommended approach A: rebuild SOTA benchmark around academic_benchmark loader.
- Use TSPLIB file metadata (EDGE_WEIGHT_TYPE, DIMENSION, TYPE) to compute distances.
- Compute optimal from .opt.tour where possible; fall back to hardcoded optimals only when opt.tour is unavailable.

## Architecture
### New script location
- Move SOTA benchmark entry point to: academic_benchmark/run_sota_benchmark.py
- Keep an optional thin shim at optimizer_api/run_sota_benchmark.py that forwards to the new entry point (to avoid breaking existing usages).

### Data flow
1. Problem selection
   - Use academic_benchmark.dataset_loader.BenchmarkDatasetLoader.
   - Ensure .tsp files are present locally; download missing files from GitHub mirror (raw.githubusercontent.com/mastqe/tsplib).
2. Problem metadata and coordinates
   - Parse .tsp file to retrieve: name, dimension, edge_weight_type, coordinates.
3. Optimal computation
   - If .opt.tour exists locally, compute optimal from the tour using the correct edge weight function.
   - If .opt.tour is missing, download from the same GitHub mirror.
   - If still missing, set optimal to unknown and mark optimal_source accordingly.
4. Benchmark run
   - Use the same algorithm runners as current SOTA benchmark.
   - Use edge-weight-aware distance computation for every tour.
5. Result output
   - Store CSV + summary files in academic_benchmark/ (new location).
   - Include metadata fields such as edge_weight_type and optimal_source.

## Edge Weight Handling
Add a unified distance function that supports:
- EUC_2D: NINT(sqrt(dx^2+dy^2))
- CEIL_2D: ceil(sqrt(dx^2+dy^2))
- ATT: TSPLIB ATT formula
- GEO: TSPLIB GEO formula
Unsupported types should log and skip the problem.

## Tour Validation
Before scoring:
- Verify the tour is a permutation of all nodes (length == dimension, unique nodes).
- If invalid, mark result as failed and exclude from gap stats.

## Historical Data Policy
For each historical benchmark CSV/summary:
- Recalculate if the corresponding problems are fully reproducible (tsp + edge_weight + opt.tour available).
- If recalculation is possible, regenerate corrected files (same filenames or a _recalc suffix).
- If not possible, delete the historical files as requested.
- Emit a short audit log of kept/recalculated/deleted files.

## Compatibility
- Do not change optimizer_api public interfaces.
- Keep any previous references working via shim or compatibility wrapper.

## Testing Plan
- Run a small SOTA benchmark subset (2-3 problems) and verify:
  - No negative gaps
  - No NaN gaps when opt.tour exists
  - Edge weight types are honored
- Validate historical recalculation behavior on one existing CSV set.

## Open Questions
- None (requirements confirmed by user).
