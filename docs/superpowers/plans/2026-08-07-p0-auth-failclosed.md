# P0-AUTH — Close the Benchmark/CLI Authentication Gap (plan)

Status: COMPLETE (implemented directly; small single-owner change)
Date: 2026-08-07
Package: phase0 hardening follow-up (serial workstream after 1D-objective)
Branch: `codex/phase1-p0-auth-failclosed-20260807` (from origin/WIP @ f07a80c)
Docs: `docs/superpowers/specs/2026-08-07-p0-auth-failclosed-design.md`

## Status notes

- Implemented directly (single-owner change, no subagent dispatch needed).
- `require_internal_api_key` fails closed: missing key ⇒ 403, never allow.
- Startup guard in `main.py` refuses to boot without `INTERNAL_API_KEY`
  (or `UNIRIDE_DISABLE_AUTH=1`); `validate_bind_host` rejects non-loopback
  binds without `ALLOW_PUBLIC_BIND=1`.
- `test_phase0_containment.py` updated to the fail-closed contract; NEW
  `optimizer_api/tests/test_phase0_auth_guard.py` (G1-G4: missing-key 403 on
  benchmark/CLI routes, correct-key pass, startup guard, bind guard).
- Full regression: **1632+ tests green**; `git diff --check` clean.

## Steps

1. **Docs first** (this plan + design doc committed on the branch).
2. **Fail-closed auth** — `optimizer_api/auth.py::require_internal_api_key`
   returns 403 when `INTERNAL_API_KEY` is unset instead of allowing.
3. **Startup guard** — `main.py` refuses to boot without `INTERNAL_API_KEY`
   unless `UNIRIDE_DISABLE_AUTH=1`; non-loopback bind requires
   `ALLOW_PUBLIC_BIND=1` (defense-in-depth for the trusted-boundary item).
4. **Tests** — update `test_phase0_containment.py::test_internal_key_is_optional_but_rejects_mismatch`
   to fail-closed; NEW `optimizer_api/tests/test_phase0_auth_guard.py`:
   startup guard, bind guard, correct-key pass, missing-key 403.
5. **Roadmap** — `ACTIVE_ROADMAP.md`: mark the three Phase-0 items `[x]`
   with evidence notes.
6. **Verify** — full regression (`optimizer_api/tests`, `uniride_core/tests`,
   `academic_benchmark/tests`), `git diff --check` clean.
7. **Merge** — FF-merge into WIP worktree, push origin/WIP, verify CI green.

## Evidence gates

- Removing `INTERNAL_API_KEY` from the environment yields 403 on benchmark
  and CLI routes in tests, never allow.
- Correct key yields 200 on authenticated benchmark routes (existing
  `test_api_hardening_phase0.py` still passes).
- `/optimize`, `/strategies`, etc. stay public (pinned by existing tests).
- `main` fails fast at import without key / with public bind opt-in missing.
- Full regression green; `git diff --check` clean.

## Done when

- `ACTIVE_ROADMAP.md` Phase 0 items 1-3 show `[x]`.
- Fail-closed behavior is pinned by tests in both auth-unit and router-level
  form.