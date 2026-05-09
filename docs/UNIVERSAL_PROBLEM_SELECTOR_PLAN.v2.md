## Plan: Universal Problem Selector

Build a shared problem-selection utility in `academic_benchmark/benchmark_utils.py` and wire it into `master_sota_engine.py` and `master_numba_engine.py`. This iteration explicitly excludes `bildiri2026`; that keeps the scope aligned with the code paths that already share the same dataclass-style problem models and CLI structure. The selector should support exact names, 1-based indices, inclusive ranges, category aliases, exclusion with `!`, and a reusable interactive/CLI path. It should reuse existing category logic instead of duplicating thresholds.

**Steps**
1. Confirm the shared selection contract in `benchmark_utils.py` *depends on no code changes yet*.
- Reuse `categorize_dimension()` for small/medium/large classification instead of creating a second threshold helper.
- Add lightweight adapter helpers that read `name`, `dimension`, and `optimal` from either dict-like or dataclass-like problem objects.
- Keep the selector grammar intentionally small: `all`, `small`, `medium`, `large`, exact name, 1-based index, inclusive range `N-M`, and exclusion `!token`.
- Define evaluation clearly as left-to-right over the token list: bare tokens add to the current set, `!token` removes from it.

2. Implement `ProblemSelector` in `benchmark_utils.py` *depends on step 1*.
- Build a stable sorted index of problems by normalized name.
- Precompute name-to-index lookup and category-to-index lookup.
- Add `resolve_tokens()` for comma-separated expressions and `quick_select()` for CLI use.
- Add `interactive_select()` for the menu flow with display, warnings, and iterative refinement.
- Keep invalid tokens non-fatal: warn, skip, and continue unless nothing valid remains.

3. Wire `master_sota_engine.py` to the shared selector *depends on step 2*.
- Add a `--select` argument.
- Use priority order `--select` > `--problems` > `--size-limit` > interactive.
- Replace `_select_problem_scope()` with `ProblemSelector.interactive_select()` in the interactive branch.
- Keep existing benchmark execution, mode handling, and result writing unchanged.

4. Wire `master_numba_engine.py` to the shared selector *depends on step 2*.
- Add the same `--select` argument and the same priority order.
- Replace the current two-choice problem selection block with the shared selector.
- Preserve the existing algorithm selection, run count selection, and tuning/default execution paths.

5. Add focused tests under `academic_benchmark/tests` *parallel with steps 2-4 once the selector API is stable*.
- Test adapter helpers for dict and dataclass inputs.
- Test category boundaries and sorted index behavior.
- Test token parsing for `all`, category aliases, indices, ranges, reversed ranges, names, exclusions, deduplication, and warnings.
- Add narrow integration tests for SOTA and Numba argument priority so regressions in `--select`, `--problems`, and `--size-limit` are caught.

6. Validate the slice *depends on steps 2-5*.
- Run the selector test file first.
- Run narrow engine tests or focused checks for the touched CLI code paths.
- Manually confirm the old `--problems` and `--size-limit` behaviors still work after introducing `--select`.

**Relevant files**
- `c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/benchmark_utils.py` — add adapters and `ProblemSelector`; reuse `categorize_dimension()`.
- `c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/master_sota_engine.py` — add `--select`, replace category-only scope selection, preserve current benchmark flow.
- `c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/master_numba_engine.py` — add `--select`, replace the interactive problem chooser, preserve tuning/default flows.
- `c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/tests/test_problem_selector.py` — new focused tests for adapters, parsing, and engine wiring.
- `c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/academic_benchmark/tests/conftest.py` — reuse existing import setup for the test package.

**Verification**
1. Run `pytest academic_benchmark/tests/test_problem_selector.py -v` and confirm the selector unit coverage passes.
2. Run focused engine checks for SOTA and Numba selection paths, especially `--select`, `--problems`, and `--size-limit` priority.
3. Confirm interactive selection still returns the same problem objects the engines already expect.
4. Check for syntax or import errors in the touched files before considering the slice done.

**Decisions**
- `bildiri2026` is excluded from this iteration.
- No glob patterns, dimension operators, optimal-value filters, presets, or save/load selection state in this pass.
- The selector should evaluate tokens left-to-right and treat `!token` as subtraction from the current selection.
- The shared category helper in `benchmark_utils.py` should be the source of truth for thresholds.

**Further Considerations**
1. If you want the selector UX to be stricter, we can change empty interactive input from “select all” to “reprompt,” but the current plan keeps the least-surprise default.
2. If later you want bildiri2026 unified, it should be a separate follow-up slice because its dict-shaped problem list needs metadata enrichment first.
