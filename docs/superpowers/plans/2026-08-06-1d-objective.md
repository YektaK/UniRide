# 1D-OBJECTIVE — One Objective for Fitness, Incumbent, and Reporting (plan)

Status: PROPOSED
Date: 2026-08-06
Package: phase1 item 1D (second serial workstream)
Branch: `codex/phase1-1d-objective-20260806` (from origin/WIP)
Docs: `docs/superpowers/specs/2026-08-06-1d-objective-design.md`

## Steps

1. **Docs first** (this plan + design doc committed on the branch).
2. **Task 0 — ALNS (item 3) evidence recording.** No code change: confirm
   `academic_benchmark/tests/test_alns_c3_evidence.py` boundary-delta test
   passes (54 tests). Record in `ACTIVE_ROADMAP.md` that C3 already fixed
   cyclic ALNS insertion deltas.
3. **Task A — objective key**
   - NEW `uniride_core/algorithms/objective_rank.py`:
     `objective_key(result)`, `is_better(a, b)`, `fitness_from_key(key)`,
     `report_key_from_routes(...)`.
   - `ga_split_engine`: evaluate computes key; tournament, diversify,
     incumbent sort by key lexicographic min.
   - `gwo_split_engine`: alpha/beta/delta + `_to_wolf` by key/is_better.
   - `hho_split_engine`: prey/hawk updates by is_better.
   - `pso_split_engine`: global/personal best by is_better (drop
     `+50*v` scalar in selection; keep `split_penalized_cost` exported).
4. **Task B — reporting-is-ranking**: `report_key_from_routes` + consistency
   test wiring in the split strategies (assert only, no wire-format change).
5. **Task C — tests**: NEW `uniride_core/tests/test_objective_rank.py`
   (dominance table); per-engine ranking tests (GA tournament, GWO leaders,
   HHO prey, PSO global best); regression that decoded routes of the
   winning candidate match key order; extend `test_ga_split_engine.py` where
   the old fitness assertions now assert key order.
6. **Verify**: full regression (`optimizer_api/tests`, `uniride_core/tests`,
   `alns_c3_evidence`), `git diff --check` clean.
7. **Docs**: `ACTIVE_ROADMAP.md` — mark all 3 objective items done; note ALNS
   evidence path.
8. **Merge**: FF-merge into WIP worktree, push origin/WIP, verify CI green.

## Evidence gates

- Dominance table: feasibility dominates vehicle count; vehicle count
  dominates travel cost — in `objective_rank` unit tests.
- Each split engine selects incumbents/leaders/prey/global-best with the
  shared key (not a cost+50*v or raw-cost divergence).
- Full regression green; `alns_c3_evidence` still 54 passed (ALNS unchanged).