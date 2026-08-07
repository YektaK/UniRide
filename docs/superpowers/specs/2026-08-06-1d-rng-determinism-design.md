# 1D-RNG — Seed / RNG Determinism Contract (design)

Status: PROPOSED
Date: 2026-08-06
Package: phase1 item 1D, first of two serial workstreams (1D-RNG, then 1D-objective)
Branch: `codex/phase1-1d-rng-determinism-20260806` (from origin/WIP)
Owner: coordinator-package 1D-RNG

## Why (evidence)

The 2026-08-06 jury/roadmap conformance review (§4.5: "PSO depends on
RNG-only reproducibility; GA on objective-only. Both depend on 1D.") plus
`ACTIVE_ROADMAP.md` ("Objective and RNG consistency") agree on four RNG
defects that silently break determinism:

1. **Seed `0` is destroyed.** All 9 strategy files resolve their seed with
   `self.seed = self.config.get("seed") or int(time.time() * 1000)`
   (`ga_strategy.py:54`, `pso_strategy.py:54`, `two_opt_strategy.py:59`,
   `gwo_strategy.py`, `gwo_split_strategy.py`, `hho_strategy.py`,
   `hho_split_strategy.py`, `ga_split_strategy.py`, `pso_split_strategy.py`).
   Because `0` is falsy, `seed=0` silently falls through to a wall-clock
   timestamp — the one value the roadmap's acceptance gate ("seed replay")
   must reproduce cannot be replayed.
2. **Wall-clock fallback is non-deterministic.** When the caller omits the
   seed, the fallback `int(time.time() * 1000)` makes two identical requests
   produce different results. `ACTIVE_ROADMAP.md` requires "Replace PSO's
   wall-clock fallback seed with a deterministic caller/default contract and
   test omitted-seed plus seed-`0` replay."
3. **Request-override reseeding destroys `0` too.** `random.Random(
   effective_config.get("seed", self.seed))` (`ga_strategy.py:114`,
   `pso_strategy.py:108`, `two_opt_strategy.py:127`) returns `None` when the
   request config carries `"seed": None`, and `random.Random(None)` seeds from
   OS entropy — nondeterministic by accident. PSO's `_rng_for_config`
   (`pso_strategy.py:69`) uses `(config or self.config).get("seed") or
   self.seed`, which also destroys `0`.
4. **Process-global reseeding survives in stochastic components.** Three
   sites mutate the process-global RNG, so concurrent jobs reseed one another
   (`ACTIVE_ROADMAP.md` line 118: "concurrent jobs cannot reseed one another"):
   - `benchmark_runner.py:257-258`: `random.seed(seed)` + `np.random.seed(seed)`
     at the top of every `run()`.
   - `fcm_split_engine.py:176-187`: lock + `random.getstate()`/`random.seed(seed)`/
     `random.setstate(state)` around `fuzzy_c_means_with_membership`, which
     itself consumes the global RNG in `_initialize_membership_matrix`
     (`fuzzy_cmeans_enhanced.py:145`: `random.random()`).
   - `numba_metaheuristics.py:351`: `random.seed(seed)` + `random.shuffle(indices)`
     in `run_single_test` (no state restore).

Already-compliant reference: `matrix_builder.py:226` uses
`np.random.default_rng(seed)` — a request-local NumPy generator. Strategy
internal pipelines (`tsp_meta_engines.py`) already take an explicit
`rng: random.Random` parameter, so the fix is confined to seed *resolution*
and the three global-reseed sites above.

## Scope (this package only)

Files to modify:

- NEW `optimizer_api/strategies/seed_utils.py` — `DEFAULT_SEED`, `resolve_seed`,
  `make_rng` (single source of truth for the seed contract).
- `optimizer_api/strategies/{ga,ga_split,gwo,gwo_split,hho,hho_split,pso,pso_split,two_opt}_strategy.py`
  — replace wall-clock fallback and `or`-style resolution (Tasks A).
- `optimizer_api/benchmark_runner.py` — remove process-global reseeding; thread
  a deterministic per-experiment seed into request configs (Task B).
- `uniride_core/algorithms/fcm_split_engine.py` + `clustering_strategies/fuzzy_cmeans_enhanced.py`
  — request-local RNG through FCM; drop the global save/restore dance (Task B).
- `uniride_core/algorithms/numba_metaheuristics.py` — request-local RNG in
  `run_single_test` initial-shuffle (Task B).
- Tests: NEW `optimizer_api/tests/test_seed_contract.py`; extend
  `optimizer_api/tests/test_strategy_rng_state.py` with seed-`0` replay.
- Docs: this file, `docs/superpowers/plans/2026-08-06-1d-rng-determinism.md`,
  `ACTIVE_ROADMAP.md` (mark the four RNG items done; leave objective/ALNS
  items open under a new "1D-objective (tracked separately)" note).

Explicitly OUT of scope (next serial workstream, 1D-objective): use one
objective for fitness/incumbent/reporting, lexicographic
feasibility/vehicle-count/travel-cost ordering, cyclic ALNS insertion deltas.

## Design

### Task A — shared seed contract

- `seed_utils.py`:
  - `DEFAULT_SEED = 42` — deterministic default when the caller omits a seed
    (matches `benchmark_runner.run`'s existing `seed: int = 42` default).
  - `resolve_seed(config, default=DEFAULT_SEED) -> int`: returns
    `config["seed"]` when it is an int (preserving `0`); returns `default`
    when absent or `None`. Non-int seeds are coerced via `int()` so
    `resolve_seed` never raises on schema-legal input.
  - `make_rng(config, default=DEFAULT_SEED) -> random.Random`:
    `random.Random(resolve_seed(config, default))`.
- In each of the 9 strategy files:
  - `self.seed = self.config.get("seed") or int(time.time() * 1000)` →
    `self.seed = resolve_seed(self.config)`.
  - `random.Random(effective_config.get("seed", self.seed))` →
    `make_rng(effective_config, default=self.seed)` (fixes the `None`-key
    entropy path too).
  - PSO `_rng_for_config`: `make_rng(config or self.config, default=self.seed)`.
  - Drop `import time` where it becomes unused; keep `random` imports.
- Behavioral contract: same config dict → same `self.seed`; `seed=0` → `0`;
  omitted/`None` → `42`.

### Task B — request-local RNGs; no process-global reseeding

- `benchmark_runner.run`: delete `random.seed(seed)` and `np.random.seed(seed)`.
  Thread determinism through the request instead:
  - `_run_single_experiment(problem, algorithm, run_num, run_seed)` — the
    runner's `seed` parameter is passed in; per-experiment seed is
    `run_seed + run_num - 1` (distinct, deterministic per repetition).
  - `_apply_algorithm_params`: inject `"seed": run_seed + run_num - 1` into the
    algorithm's request config **only when the caller's `algorithm.params` does
    not already carry a `seed`** (caller contract wins).
  - Result: a runner-level `seed` still fully determines every experiment
    (replay gate preserved), while no process-global RNG state is touched, so
    concurrent benchmark jobs cannot reseed one another.
- `fuzzy_cmeans_enhanced.py`: `_initialize_membership_matrix(n, k, rng)` uses
  `rng.random()`; `fuzzy_c_means_with_membership(...)` gains
  `rng: Optional[random.Random] = None` (`rng or random.Random()`), passing it
  to the initializer.
- `fcm_split_engine._cluster_node_indices`: build `rng = random.Random(seed)`
  and pass it through `fuzzy_c_means_with_membership`; delete the
  `_FCM_LOCK`/`getstate`/`seed`/`setstate` block (its only purpose was guarding
  global RNG mutation; `_FCM_LOCK` and its import may be removed only if no
  other usage remains).
- `numba_metaheuristics.run_single_test`: `rng = random.Random(seed);
  rng.shuffle(indices)` instead of `random.seed(seed)`.

### Task C — tests

- `optimizer_api/tests/test_seed_contract.py` (NEW):
  - `resolve_seed`/`make_rng` unit tests: `{"seed": 0}` → 0; `{}`/`{"seed": None}`
    → 42; int passthrough; `make_rng` returns `random.Random`.
  - Seed-`0` replay for every one of the 9 strategies: two `optimize()` calls
    with the same request and `seed=0` produce identical route sequences;
    `seed=0` differs from `seed=1` (using the existing `_small_request`/
    fake-data-loader pattern from `test_strategy_rng_state.py`).
  - Omitted-seed determinism: same config twice (no seed) → identical results
    (pin the deterministic default, not the wall clock).
  - PSO `_rng_for_config`: `seed=0` honored; request `pso_config={"seed": 0}`
    honored without mutating strategy defaults (mirror
    `test_pso_request_config_is_passed_without_mutating_strategy_defaults`).
- Extend `test_strategy_rng_state.py`: instance-RNG hygiene holds with `seed=0`
  and with omitted seed.
- Runner-level replay: two `BenchmarkRunner.run(..., seed=42)` calls on a tiny
  fixture produce identical `tour_length`s per experiment; `seed=0` also
  replays; and after `run()`, `random.getstate()`/`np.random.get_state()`
  equal their pre-run values (no process-global reseeding).
- Concurrency isolation: two strategies with different seeds optimized in
  interleaved threads each produce exactly their sequential output (gate
  "concurrent jobs cannot reseed one another").
- FCM: same seed → identical cluster assignments; global `random.getstate()`
  unchanged after `_cluster_node_indices`/engine call.
- numba: `run_single_test` same seed → identical tours; global state unchanged.

### Acceptance gate

`ACTIVE_ROADMAP.md` items checked: "Preserve seed `0`", "Replace PSO's
wall-clock fallback seed with a deterministic caller/default contract and test
omitted-seed plus seed-`0` replay", "Pass request-local Python and NumPy RNGs
through all stochastic components", "Remove process-global reseeding from
concurrent jobs". Full regression suite green; `git diff --check` clean.
