# DUD-01 final verification — 2026-09-09

Status: code and automated verification complete in `codex/dud01-auth-direction-20260908`, based on `0345e64a322ebac0255b387b12198230275c7097`. Changes remain uncommitted; WIP integration and publication have not occurred.

## Verified behavior

The active administrator vehicle-planning page calls the authenticated calculation client and sends the selected trip direction. The BFF normalizes an omitted request to pickup, preserves authorization failures, and rejects missing, invalid, or conflicting successful optimizer directions. The serializer requires an explicit direction matching the calculation-time direction. Changing the selector after either pickup or dropoff calculation cannot relabel the saved plan.

The final scoped review checked the page/client/serializer diff and corrected the page test that requested dropoff but returned a pickup fixture. That test now saves a dropoff result after changing the selector to pickup. A further page case rejects a result whose valid direction conflicts with the request. No production changes were required in this final pass.

## Current evidence

- `npm.cmd test -- --run`: **33 files, 210 tests passed**, exit 0, 26.77 seconds. Includes 6 vehicle-planning page tests and the Task 1/2 tests.
- `npm.cmd run typecheck`: `tsc --noEmit` completed without diagnostics.
- `git diff --check`: no whitespace errors; LF/CRLF normalization warnings remain.
- Test output includes existing auth diagnostics, missing Supabase configuration warnings, and a React DOM-nesting warning from a Badge rendered inside a paragraph. These were not test failures and were not repaired in this scoped pass.

Historical RED claims in external task reports were not reconstructed or independently certified in this pass. This evidence concerns the current working-tree implementation. Full Python suites, production build, live optimization, and live database operations were not run.

## Next operational gate

1. Review/commit and integrate this verified change into WIP when Git integration is authorized; do not switch a running service to an unreviewed worktree.
2. Start the local stack from the intended credential-bearing checkout with `npm run dev:dudullu`.
3. Sign in as administrator and open `/admin/readiness`. Capture only aggregate readiness status and reason codes; do not copy tokens, student identities, or raw records into reports.
4. Resolve any reported configuration/data blockers before claiming readiness for the daily planner or adding subsequent operational features.

Both `http://127.0.0.1:8000/health` and `http://127.0.0.1:9002/admin/readiness` were unavailable during the 2026-09-09 probe (HttpRequestException). No live readiness verdict or current student/matrix count is established.

The earlier Task 2/3 reports under `.superpowers/sdd` are ignored scratch artifacts. This document is the portable verification record intended to accompany the code changes.
