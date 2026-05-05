# Task: SOTA TSP parity hardening + benchmark robustness fixes

## Phases
- [x] Phase 1: Research and diff current implementations
- [x] Phase 2: Confirm scope with user (Option B + extra fixes)
- [x] Phase 3: Add/adjust tests for new behavior
- [x] Phase 4: Implement code changes
- [x] Phase 5: Validate with targeted benchmark runs
- [x] Phase 6: Apply academic_benchmark_fix_report.md fixes (2026-05-06)

## Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
| Follow Option B | Increase parity between `optimizer_api/sota_common` and `academic_benchmark/sota_tsp` without full architecture migration | 2026-04-30 |
| Include two cross-cut fixes | User explicitly requested Numba fallback worker import fix and deterministic seed generation | 2026-04-30 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| TDD skill local path missing | Read local skill path under project | Read global skill path under `C:\Users\yektakayman\.claude\skills` |

## Benchmark Fix Report Status (2026-05-06)
| Phase | Issues | Status |
|-------|--------|--------|
| Phase 1: Critical (C1-C5) | 5 issues | ✅ ALL FIXED |
| Phase 2: Consolidation (M1-M3) | 3 issues | ✅ ALL FIXED |
| Phase 3: Data Integrity (D2, D4, D5) | 3 issues | ✅ ALL FIXED |
| Phase 4: Dashboard (H2, H3, M6) | 3 issues | ✅ ALL FIXED |
| Phase 5: Testing (T1-T4) | 4 issues | ✅ ALL FIXED |
| Hygiene (M7) | 1 issue | ✅ FIXED |
| **Total** | **19 issues** | **✅ ALL RESOLVED** |
