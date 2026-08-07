# 1D-RNG — Seed / RNG Determinism Contract (plan)

Status: PROPOSED
Date: 2026-08-06
Package: phase1 item 1D (first of two: 1D-RNG, then 1D-objective)
Branch: `codex/phase1-1d-rng-determinism-20260806` (from origin/WIP)
Docs: `docs/superpowers/specs/2026-08-06-1d-rng-determinism-design.md`

## Steps

1. **Docs first** (this plan + design doc committed on the branch).
2. **Task A — shared seed contract**
   - NEW `optimizer_api/strategies/seed_utils.py`: `DEFAULT_SEED = 42`,
     `resolve_seed(config, default=DEFAULT_SEED)`, `make_rng(config, default)`.
   - 9 strategy files: replace `self.config.get("seed") or int(time.time()*1000)`
     with `resolve_seed(self.config)`; replace
     `random.Random(effective_config.get("seed", self.seed))` with
     `make_rng(effective_config, default=self.seed)`; PSO `_rng_for_config`
     via `make_rng`; drop unused `import time`.
3. **Task B — request-local RNGs; no process-global reseeding**
   - `benchmark_runner.py`: remove `random.seed(seed)`/`np.random.seed(seed)`
     from `run()`; pass `run_seed` into `_run_single_experiment`; inject
     `"seed": run_seed + run_num - 1` into request config only when
     `algorithm.params` has no `seed`.
   - `fuzzy_cmeans_enhanced.py`: `rng` param through
     `_initialize_membership_matrix`/`fuzzy_c_means_with_membership`.
   - `fcm_split_engine.py`: request-local `random.Random(seed)`; remove the
     `_FCM_LOCK`/getstate/setstate block if lock usage disappears.
   - `numba_metaheuristics.py`: local `rng.shuffle` in `run_single_test`.
4. **Task C — tests**
   - NEW `optimizer_api/tests/test_seed_contract.py` (resolve_seed units;
     seed-0 replay for all 9 strategies; omitted-seed determinism; PSO
     `_rng_for_config`; runner-level replay; no-global-reseed assertions;
     thread interleaving isolation; FCM/numba determinism + global-state
     checks).
   - Extend `test_strategy_rng_state.py` (seed-0 and omitted-seed hygiene).
5. **Verify**: full regression suite (optimizer_api + uniride_core) green,
   `git diff --check` clean.
6. **Docs**: update `ACTIVE_ROADMAP.md` (four RNG items done; add "1D-objective
   (tracked separately)" note for the remaining three items).
7. **Merge**: FF-merge into WIP worktree, push origin/WIP, verify CI green.

## Evidence gates

- Seed-0 replay: identical results across two calls with `seed=0` for all 9
  strategies, and across two `BenchmarkRunner.run(seed=0)` calls.
- Deterministic default: omitted seed → identical results across calls (pinned
  to 42, not wall clock).
- No process-global reseeding: `random.getstate()`/`np.random.get_state()`
  unchanged after runner run and after FCM/numba calls.
- Concurrency isolation: interleaved threads with different seeds each match
  their sequential output.
