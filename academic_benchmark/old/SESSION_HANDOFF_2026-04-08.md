# Session Handoff — 2026-04-08

## Status
- **Branch**: WIP
- **Commits this session**: 0
- **Uncommitted changes**: benchmark runner, benchmark documentation, local search files, plus this handoff file
- **Tests**: syntax validation passed for the edited benchmark files; full benchmark rerun still pending after the last documentation update

## What's Done
- Added a `BENCHMARK_PROFILE` switch to the Numba benchmark runner.
- Added `baseline` and `quality_first` tuning paths for meta-heuristics.
- Increased default benchmark budgets and added a final local-search refinement step for meta-heuristics.
- Updated `academic_benchmark/BENCHMARK_DOKUMANTASYON.md` with profile usage instructions and PowerShell examples.

## What's In Progress
- Re-run the benchmark with both profiles and compare quality/runtime results.
- Confirm the classic heuristics still behave as expected under the new profile switch.

## What's Pending
- Optional: expose benchmark profile selection in the interactive menu instead of only via environment variable.
- Optional: wire enhanced split strategies into the benchmark if the paper needs a stronger head-to-head comparison.

## Key Decisions Made
- Use `quality_first` as the default profile because the current goal is solution quality, not minimum runtime.
- Keep `baseline` available so the paper can show a clear comparison against a conservative setup.
- Keep the change localized to the benchmark runner and documentation instead of refactoring the strategy modules.

## Learnings Captured
- [Benchmarking] Meta-heuristics need size-aware budgets and final local search to stay competitive on TSPLIB TSP instances.
- [Benchmarking] `BENCHMARK_PROFILE` is the cleanest way to switch between baseline and quality-first tuning without code changes.

## Files Touched
- [academic_benchmark/BENCHMARK_DOKUMANTASYON.md](academic_benchmark/BENCHMARK_DOKUMANTASYON.md) — documented benchmark profiles and `BENCHMARK_PROFILE` usage.
- [academic_benchmark/run_smart_benchmark_numba.py](academic_benchmark/run_smart_benchmark_numba.py) — updated visible benchmark defaults to match the new quality-first setup.
- [optimizer_api/tests/run_interactive_benchmark_v2_numba.py](optimizer_api/tests/run_interactive_benchmark_v2_numba.py) — added profile-aware tuning, stronger defaults, and final local-search refinement.
- [academic_benchmark/SESSION_HANDOFF_2026-04-08.md](academic_benchmark/SESSION_HANDOFF_2026-04-08.md) — session handoff for the next run.

## Gotchas for Next Session
- The working tree already contains unrelated untracked review/test artifacts; do not delete them unless the user asks.
- The benchmark profile is environment-driven, so a new terminal is required after `setx`.

## Resume Command
> Continue on branch WIP. Re-run the TSPLIB benchmark with `BENCHMARK_PROFILE=baseline` and `BENCHMARK_PROFILE=quality_first`, compare gap/runtime results, and decide whether the enhanced split strategies should be added next.
