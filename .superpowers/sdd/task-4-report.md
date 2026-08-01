# Task 4 Report — Frontend Lint Gate and Hydration-Safe Mobile Hook

## Outcome

Restored the direct ESLint command and implemented both duplicate `useIsMobile()` modules with `React.useSyncExternalStore`. The focused contract and viewport-update tests pass.

## RED evidence

- `.\\node_modules\\.bin\\vitest.cmd run src/hooks/use-mobile.test.tsx`: 1 failed / 1 passed. The direct contract failed because the legacy hook source did not contain `useSyncExternalStore`; resize behavior alone passed.
- `.\\node_modules\\.bin\\eslint.cmd src --ext .ts,.tsx`: 24 errors, 7 warnings (31 problems).

## Changes

- Declared ESLint 9 and `eslint-config-next`; regenerated only `package-lock.json` with `npm install --package-lock-only --ignore-scripts`.
- Replaced the legacy config with the two Next flat configs, unused-disable reporting, a global `@typescript-eslint/no-explicit-any: warn`, required hook/general error rules, and only `react/no-unescaped-entities` disabled.
- Reconstructed only accepted `1e42652` TS/TSX lint hunks, applied the hydration-safe external-store hook in both duplicate modules, and restored six approved sandbox encoding literals.

## GREEN evidence

- Focused hook test: 2 passed.
- `npm run lint`: exit 0, 0 errors, 159 warnings.
- `npm run typecheck`: exit 0.
- `npm test -- --run`: 4 files / 17 tests passed.
- `git diff --check`: exit 0.

## Warning-debt correction

The original cap of seven warnings cannot coexist with the brief-mandated global `@typescript-eslint/no-explicit-any: warn` in the current source tree and the binding 21-file reconstruction boundary. ESLint now reports 159 non-blocking warnings: 69 `@typescript-eslint/no-unused-vars`, 67 `@typescript-eslint/no-explicit-any`, 19 `react-hooks/exhaustive-deps`, and 4 `react-hooks/incompatible-library`. No rules were suppressed to meet the old cap; Task 6 must carry this debt explicitly.

## Scope statement

Only Task 4's authorized package/config files, exact admitted UI lint paths, duplicated hook modules, hook test, manifest, and this ignored report were changed. No unrelated user changes, generated artifacts, API or academic code, refs/remotes, branches, workflow, roadmap, or worklog were modified.
