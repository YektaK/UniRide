# MT1 first close record (merge-now set): evidence

Plan: `docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md`, sections 2.2 (merge-now split) and 7.2 (demo acceptance). Decisions and merge notes: `docs/DECISION_LOG.md` O09 (2026-10-27 notes). This file records facts only; the second close record (MT1-13, after the paper campaign and lane B) is not written yet.

## 1. Scope of this record

The merge-now set of plan section 2.2: MT1-01, -02, -03, -04, -07, -08, -10, plus the H16 dashboard note (this branch, `docs/mt1-13-first-close`). Not in scope and not merged: MT1-05, -06, -09, -11, -12 (they change study-imported modules and wait for the paper campaign, section 2.2 and A21 OQ-F7).

## 2. Merged items and the lead's post-merge test results

| Item | Merge commit | Content (DECISION_LOG O09 notes) | Lead's post-merge run |
|---|---|---|---|
| MT1-10 | `8ad1b94b` | honest fleet wording; `NO_ACTIVE_VEHICLES` reason | vitest 95 files, 1195 passed; `tsc` clean |
| MT1-08 | `0fc7bc7b` | window direction; 422 `use_time_windows requires target_time`; implicit window deleted; `/compare` optional `target_time`; benchmark runner refuses CVRPTW rows (`cvrptw_refused_h16_mt1_11`) | optimizer_api + registry snapshot: 2852 passed |
| MT1-07 | `a74aff76` | split fallback reported; `strategy_error` in the error JSON for allow-listed codes | 2872 passed |
| MT1-01 | `7584f2fa` | route simulator `uniride_core/algorithms/route_schedule.py` | uniride_core: 2740 passed, 7 skipped, 42 deselected |
| MT1-02 | `8513c2b6` | production certificate simulates every route on the captured arcs when `target_time` is set | optimizer_api + registry snapshot + exact-certification callers: 3112 passed, 8 deselected |
| MT1-03 | `f9bf58f6` | returned schedule = certified schedule (exact `schedule_start_minutes`, `schedule_end_minutes`, `arrival_minutes`); certificate `schedule_mismatch`; `calculate_scheduled_times` removed | optimizer_api + uniride_core + exact callers: 5761 passed, 7 skipped |
| MT1-04 | `ac22a383` | daily plan and fleet runner send `offset_minutes` 0 and cross-check their interval against the certified `schedule_start/end_minutes`; mismatch blocks the plan with `SCHEDULE_MISMATCH` | vitest 1211 of 1212 passed; `tsc` clean; research tests 6 files, 55 passed |
| H16 note | this branch | one warning line in the CVRP/CVRPTW diagnostics tab of `academic_benchmark/dashboard.py` when CVRPTW rows are present; test `academic_benchmark/tests/test_h16_dashboard_cvrptw_note.py` | see section 5 |

MT1-04 test note: the one failing test is `typed-selection-verify-cli.test.ts`. It is an environment effect: Node v26.12.1 with tsx prints a DEP0205 warning to stderr; reproduced on the base commit (before MT1-04).

Reviewers recorded in DECISION_LOG O09: MT1-01 Opus ONAY round 1; MT1-02 Opus ONAY round 2; MT1-03 Opus ONAY round 1; MT1-04 Sonnet ONAY (merge subject of `ac22a383`). MT1-07, -08 and -10 reviewer names are not recorded in the O09 notes that were read.

## 3. Demo acceptance (plan section 7.2 items 1, 2, 3, 4a)

Source: `C:\wt\mt1-demo\result.md` (outside the repository). These are acceptance numbers, not paper evidence; no claim about algorithm quality or superiority follows.

### 3.1 Commits and method

- Before: `5e8a8637` (WIP before any MT1 merge). After: `ac22a383` (WIP after MT1-01..04, -07, -08, -10). Two clean detached worktrees; main checkout untouched.
- Python: `.venv-jit` interpreter; the script asserts that `uniride_core` and `routers.optimization` load from the worktree under test.
- Requests were reconstructed from the archive `docs/paper/results/week-2026-10-05-4sw5so/` (20 runs, 228 waves), because the archive holds responses and matrices, not request bodies. The reconstruction mirrors the `/optimize` body of `src/services/daily-plan-run.ts` (identical at both commits except `offset_minutes`): API default `ga_split`, mode sandbox, `use_time_windows` false, `max_travel_time` 150, `max_ride_time` = R, depot `D.Kampus`, the virtual fleet of 54 copies of the 4 Sw / 5 So / cooldown 10 template (first `min(legs, 50)` per call). Every response reports `effective_seed` 42 (228/228, both commits).
- Offset: before, no `offset_minutes` sent (API default 15, `schemas.py:274`); after, `offset_minutes: 0` (`daily-plan-run.ts:661`, MT1-04).
- Matrix: the archived per-run `*.matrix.json` is served in memory through `routers.optimization._matrix_snapshot_for_request` and a strict arc loader; no database, no network. FastAPI `TestClient`, in process.
- Runtime: whole replay 20.6 s before, 20.5 s after.

### 3.2 Items 1-3 results

- Item 1 (replay): 228/228 waves HTTP 200, `success` true, certificate `is_feasible` true, at both commits (0 failures, 0 violations). Before vs after: identical number of routes, total duration, route and stop order and vehicle ids in all 228 waves (0 differences). After vs archive: identical number of routes, total duration and stop order in all 228 waves (0 differences). The archive was produced on commit `6be127d` (dirty tree) with the same `ga_split` defaults.
- Item 2 (schedule check, after only): 358 routes, 0 violations. `schedule_start_minutes` and `schedule_end_minutes` equal the TypeScript interval within 1e-6 (pickup `[anchor - total, anchor]`, drop-off `[anchor, anchor + total]`); every pickup ends at its anchor; no route outside 00:00-24:00. They also equal the archive's own `routeIntervals` start and end in 358/358 routes (maximum absolute difference 0.0 minutes).
- Item 3 (known numbers): 2026-10-05, ride limit R50/60/70/90, peak-wave routes 6/5/4/4 (identical before, after and archive), matching `summary.csv` `vehicles_required` 6/5/4/4; `summary.csv` also gives `vehicle_count_proven` true and `capacity_floor` 3 (read from the archive, not recomputed).
- Note on `vehicles_required` vs peak-wave routes: on 10-06..10-09 `summary.csv` `vehicles_required` is larger than the peak-wave route count (for example 10-07 R50: 6 vs 4). It is the physical vehicle count after the app's cross-wave interval assignment (cooldown, concurrent waves), not routes per wave. The TypeScript assignment was not re-run; the route intervals it consumes are identical to the archive's (358/358). On 10-05 the two numbers coincide.
- `offset_minutes` 15 (before) and 0 (after) give the same result here because `use_time_windows=false`; the before run has no exact schedule fields (MT1-03 is not in it), so no schedule check was made there.

### 3.3 Item 4a, windowed sanity set (after only, real `ga_split` through `/optimize`)

Scenarios built from the audit text (H2 ~694, H3 ~720, H4 ~740, N1 at 2416); the audit gives only some arcs, the rest are filled with a stated constant. N1's arcs are the replay author's construction (the audit gives only the outcome), so N1 is indicative, not a reproduction of the reviewer's case. Observed:

| Scenario | Plan 7.2 4a expectation | Observed |
|---|---|---|
| H2 (target 08:30, offset 15, both pickup 08:30, D-LA 10, LA-LB 20, LB-D 20, other arcs 60) | rejected or refused | `success=false`; certificate infeasible `time_window_violation` ("Route 0 reaches the school at 520.00, after the deadline 495.00") plus `hard_violation`. Same with other arcs 20 and with offset 0 (deadline 510). As expected. |
| H3 at offset 15 (target 08:30, A pickup 08:00, B none, D-A 10, A-B 5, B-D 10, other arcs 100) | 07:50 / 08:00 / 08:05 / 08:15 | `success=true`, certified; departure 07:50, A 08:00, B 08:05, school 08:15; exact `schedule_start/end` 470/495; `arrival_minutes` A 480, B 485. As expected. |
| H3 at offset 0 (the value of the MT1-03 test) | same times | DEVIATION: `success=false`; real `ga_split` returned two singleton routes and the certificate rejected them (school 550 > deadline 510, duration 150 > 120). The 07:50 / 08:00 / 08:05 / 08:15 times appear at offset 0 only in the MT1-03 test, which stubs the strategy. Hypothesis, not verified (decoder not instrumented): the legacy windowed decoder anchors the pickup start at `target - cost - offset`; this is the decoder-side defect of the H4 class, left to MT1-05. |
| H4 scenario 1 (arcs 10.9 / 10.9 / 10.2, A pickup 07:53, target 08:15, offset 0, other arcs 100) | still `success=false` | DEVIATION: `success=true`, certified, one route, departure 07:42, schedule 462.1 -> 494.1, arrivals A 473.0, B 483.9. Since MT1-02 the certificate uses the latest-start simulation (test `test_h4_scenario_certifies_feasible_on_the_latest_start_schedule`) and the strategy result is then certified. |
| H4 scenario 2 (one student pickup 07:30, no `target_time`, windows on; `ga_split` and `genetic_algorithm`, offsets 0 and 15) | ga_split fails, genetic_algorithm certifies | DEVIATION: refused before any solve with HTTP 422 `use_time_windows requires target_time` (all four calls; MT1-08). Not reproducible as written. |
| N1 (drop-off, target 16:00, offset 0, S1/S2/S3 drop-off 16:10/16:20/16:30, `max_ride_time` 45, arcs D-S1 5, S1-S2 12, S2-S3 25, S3-D 10, other arcs 30, windows on) | more than one vehicle (unchanged) | `success=true`, certified, 2 routes ([S1,S2] and [S3]). Control with `use_time_windows=false`: 1 route [S1,S2,S3] (ride 42), certified. With offset 15: also 2 routes. As expected (N1 unchanged). |

The plan text for 4a is not rewritten; the two plan-expectation deviations (H4 scenario 1 now certified; H4 scenario 2 refused 422) and the H3 offset-0 failure are the observations above. 4b (after lane B) remains to be run.

Rule slip reported by the replay author: two read-only `python -c` one-liners and one `-I -c "print(1)"` with the venv interpreter; no side effects.

## 4. What remains open

- MT1-05 (decoder time-window branch), MT1-06 (search key), MT1-09 (OR-Tools/PyVRP), MT1-11 (H16 forward CVRPTW profile), MT1-12 (L12 capacity contract): after the paper campaign (plan section 2.2; they import study-closure modules). H4 search part, H2 decoder part, N1-b and H16 stay open until then.
- Plan 7.2 second demo acceptance and 4b after lane B.
- MT1-13 final close (second record).
- Follow-ups recorded earlier: `ga_split_hf_strategy.py` :99 and :229 still return `success=True` (O09 note at the MT1-07 merge); `arrival_minutes` is the arrival before any wait, whether users should see the service start instead is an open owner question (O09 note at MT1-03); the certificate does not cross-check HH:MM strings against the exact fields, and a successful response with `target_time` but no exact fields is not flagged (O09 note at MT1-03).

## 5. H16 dashboard note: red/green and checks

- Check: `academic_benchmark/dashboard.py` is launched only as a Streamlit script (`cli_engine.py:2526`, `smart_benchmark.py:1338`, `__main__.py:16`); no module under `academic_benchmark/studies`, `fair_pilot.py` or the study run imports it.
- Red commit `6b520c72` (test only, 1 failed, 1 passed); fix commit `9e6a208d`.
- Result after the fix: `test_h16_dashboard_cvrptw_note.py` 2 passed. With the fix reverted in the working tree the shown-note test fails again (1 failed, 1 passed). Dashboard tests (`test_h16_dashboard_cvrptw_note`, `test_c5_dashboard_no_inference`, `test_c5f1_descriptive_labels`, `test_cx02_dashboard_obsolete_csv`, `test_dashboard_utils`, `test_gate_d_reporting_sweep`) plus `test_production_registry_snapshot.py`: 69 passed, 3 skipped (the three skips are the `test_cx02_dashboard_obsolete_csv.py` cases that need `streamlit`).
