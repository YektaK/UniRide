# 1C — Split-Decoder / ATSP Repairs + Certificate Wiring (plan)

Status: PLANNED
Date: 2026-08-06
Branch: `codex/phase1-1c-split-decoder-20260806` (from origin/WIP @ `eb7b5dc`)
Design: `docs/superpowers/specs/2026-08-06-1c-split-decoder-atsp-repairs-design.md`

## Package principle

Evidence-gated, one serial workstream, focused commits, tests first. Every
change that alters decoder behavior ships with its regression in the same
commit. Full regression runs at the end; anything that breaks an existing test
that asserted the OLD fabricating behavior is updated only where the old
assertion is wrong under the strict contract (each such update named in review).

## Tasks (serial)

1. **Task A — reject missing directed arcs**
   - `linear_split_decoder.py`: add `is_asymmetric` param; `_get_distance` returns
     `math.inf` on absent directed arc (reverse lookup only when symmetric).
   - `string_split_decoder.py::_get_dist`: same rule; `inf` on absent.
   - `cvrptw_decoder.py::is_feasible`: missing arc → `(False, "missing arc ...")`.
   - Tests (new `uniride_core/tests/test_split_decoder_atsp_strict.py`):
     incomplete ATSP matrix → inf, never 15.0 fabrication; complete → normal.
2. **Task B — strict vs soft TW modes**
   - `string_split_decoder.py::SplitDecoder` gains `strict_time_windows=False`;
     strict drops trips with `time_window_violations > 0`.
   - `LinearSplitDecoder` `allow_time_warp` modes pinned by tests.
   - Tests: strict rejects violating prefix; soft accepts with violations.
3. **Task C — enumerate pickup prefixes + separate violation kinds**
   - PICKUP branch appends every capacity-feasible prefix `i..k`.
   - `LinearSplitResult` + schedules gain `duration_excess`; `PenaltyConfig`
     gains `duration_penalty_rate`; duration excess never mixed into
     `time_warp_mins`/`tw_penalty`.
   - Tests: [A,B,C] cap-2 pickup yields [A,B] and [A] trips; duration-excess
     vs TW separation.
4. **Task D — depot-revisit predecessor handling**
   - `decode` (both decoders) strips interior depot from giant tour.
   - Test: directed matrix, tour [A,DEPOT,B] → `[[A,B]]`, directed arcs.
5. **Task E — certificate wiring**
   - NEW `optimizer_api/verification/response_certifier.py`
     (`certify_benchmark_response` → JSON-safe dict).
   - `benchmark_runner._run_single_experiment` attaches
     `metadata["feasibility_certificate"]`, never raises.
   - Tests (new `optimizer_api/tests/test_response_certifier.py`): greedy on
     small TSP → feasible; incomplete ATSP → missing-arc violations surfaced.
6. **Task F — regression + roadmap**
   - Full: `pytest optimizer_api/tests uniride_core/tests academic_benchmark/tests/test_atsp_integration.py`
   - `git diff --check`, strategy smoke `test_all_strategies_smoke.py`.
   - Update `ACTIVE_ROADMAP.md` (1A/1B done, 1C in progress).
7. **Merge**: FF into WIP, push; verify CI.

## Risks / mitigations

- `inf` propagation in GA hot loops: DP objective only ever compares finite
  candidates against `inf`; unreachable states stay `inf` (no crash).
- Existing tests relying on 15.0 fallback: grep for `15.0`/`DEFAULT_TRAVEL_FALLBACK`
  in tests; only rewrite assertions that encode fabrication; review lists them.
- Certificate conversion failures: wrapped, recorded as `certify_error`, never
  fail the run.

## Verification commands

```
python -m pytest uniride_core/tests/test_split_decoder_atsp_strict.py -q
python -m pytest optimizer_api/tests/test_response_certifier.py -q
python -m pytest optimizer_api/tests uniride_core/tests academic_benchmark/tests/test_atsp_integration.py -q
git diff --check
```
