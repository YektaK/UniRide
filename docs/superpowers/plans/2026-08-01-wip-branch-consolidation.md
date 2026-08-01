# WIP Branch Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `WIP` the authoritative UniRide development branch by advancing the validated C1 spine, selectively reconstructing proven Phase 0 behavior, and promoting only a fully verified fast-forward head.

**Architecture:** Start from C1 `0882081`, which already contains Package A and Package B. Preserve the old WIP and local-only rescue heads remotely, then recreate current-context behavior in atomic test-first commits rather than merging or range-cherry-picking the rescue branch. Record every admitted and rejected hunk in a root manifest and move `WIP` only after identical baseline/final gates show no regression.

**Tech Stack:** Git worktrees and annotated tags, Python 3.14, pytest, FastAPI, Pydantic, Next.js 16, React 19, TypeScript, ESLint 9, Vitest, GitHub Actions.

## Global Constraints

- Work only in `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.temp\worktrees\wip-consolidation-20260801` on `codex/wip-consolidation-20260801`.
- The original checkout at `C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide` is dirty and must not be edited, staged, cleaned, reset, or used for commits.
- C1 `08820813a4657d62bb81c44a6a671984c846e28b` is the immutable academic spine.
- Never merge or range-cherry-pick `codex/local-rescue-20260721`.
- Unclassified rescue content defaults to `reject`.
- No `uniride_core/algorithms/tsplib_parser.py` rescue hunk may be reconstructed without a newly reproduced C1 defect and separate user authorization.
- Do not import `.numba_cache/`, `*.nbc`, `*.nbi`, dirty-checkout files, generated runtime results, audit-only branches, or `origin/main` changes.
- Preserve pre-existing C1 benchmark evidence byte-for-byte and hash it in the consolidation manifest.
- Use test-first red/green/refactor for every behavior change.
- Baseline and final gates must use the same commands and environment; functional failures always block promotion, and failures or unexpected skips may not increase.
- Environment-only waivers require explicit user acceptance before `WIP` moves.
- Promotion must be a normal fast-forward push; force-push, `reset --hard`, and history rewriting are prohibited.
- Do not delete any source branch in this package.

---

### Task 1: Durable Preservation, Baseline, and Admission Ledger

**Files:**
- Create: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`
- Reference: `docs/superpowers/specs/2026-08-01-wip-branch-consolidation-design.md`

**Interfaces:**
- Consumes: current local/remote refs and C1 tracked evidence files.
- Produces: remotely verified recovery tags, exact baseline results, evidence hashes, and a complete rescue path/hunk ledger used by Tasks 2–5.

- [ ] **Step 1: Fetch without integrating and assert the branch base**

```powershell
git fetch --prune origin
git status --short --branch
git merge-base --is-ancestor 08820813a4657d62bb81c44a6a671984c846e28b HEAD
git merge-base --is-ancestor origin/WIP HEAD
```

Expected: clean tracked worktree; both ancestry commands exit `0`.

- [ ] **Step 2: Record and protect exact source heads**

```powershell
git rev-parse origin/WIP
git rev-parse codex/local-rescue-20260721
git tag -a archive/pre-wip-consolidation-20260801 a44d50631d826f81fd2a6bb1b73baa4a46e5fa1f -m "Pre-consolidation WIP 2026-08-01"
git tag -a archive/local-rescue-20260721 e0824b42d2251cfd479207d756798913a2313b31 -m "Preserve local rescue before WIP consolidation"
git push origin refs/tags/archive/pre-wip-consolidation-20260801 refs/tags/archive/local-rescue-20260721
git ls-remote --tags origin archive/pre-wip-consolidation-20260801 archive/local-rescue-20260721
```

Before creating a tag, if its name exists, peel it with `git rev-parse <tag>^{}` and stop unless it resolves to the required commit.

- [ ] **Step 3: Create the manifest skeleton with exact classifications**

The manifest must contain these tables and initial decisions:

```markdown
# WIP Consolidation Manifest — 2026-08-01

## Immutable heads
| Ref | Full SHA | Treatment |
|---|---|---|

## Rescue admission ledger
| Commit | Path/hunk | Decision | Live evidence | Validation |
|---|---|---|---|---|
| 3eea998 | all academic hunks | superseded | Package B/C1 ancestry | academic baseline |
| 092efe3 | entire patch | superseded | git cherry reports patch-equivalent | none |
| 253155c | entire patch | superseded | git cherry reports patch-equivalent | none |
| 61c36c1 | optimizer API localhost binding | admit | C1 binds 0.0.0.0 | runtime config tests |
| 61c36c1 | CLI arbitrary-path removal | admit | C1 accepts filepath | containment tests |
| 61c36c1 | optional CLI internal key | admit | C1 CLI endpoints unguarded | auth tests |
| 61c36c1 | src/proxy.ts internal-key forwarding | reject | header is not forwarded by Next route fetches | source trace |
| dcd5896 | Pydantic pair alignment | admit | pyproject pinned, optimizer requirements broad | dependency tests |
| dcd5896 | NumPy/Numba minimums | admit | pyproject names unbounded | dependency tests |
| ea75581 | direct ESLint gate and declared packages | admit | next lint script is invalid on Next 16 | npm/lint gate |
| 1e42652 | requirements-lock.txt | reject | historical platform lock is not independently required | manifest check |
| 1e42652 | optimizer_api/routers/benchmark.py | reject as a historical hunk | Task 2 recreates tested security behavior | containment tests |
| 1e42652 | uniride_core/algorithms/tsplib_parser.py | reject | canonical C1 academic spine | unchanged hash |
| 1e42652 | ACTIVE_ROADMAP.md and WORKLOG.md | reject | stale historical text | current manifest only |
| 1e42652 | CI, flat ESLint config, bounded UI lint hunks | admit per listed path | reproducible lint errors | lint/type/test gates |
| e0824b4 | use-mobile hydration fix | admit | current hook mutates state in effect and differs on SSR | hook test and lint |
| e0824b4 | sandbox encoding repair | admit only for six verified mojibake literals | current source reproduces the text corruption | focused diff and typecheck |
```

- [ ] **Step 4: Hash all pre-existing C1 benchmark evidence**

```powershell
git ls-tree -r --name-only 0882081 -- academic_benchmark/numba_results academic_benchmark/sota_results |
  ForEach-Object { $hash = git show "0882081:$_" | git hash-object --stdin; "| ``$_`` | ``$hash`` |" }
```

Paste every row into `## C1 evidence inventory`. These Git blob hashes are the immutable comparison baseline.

- [ ] **Step 5: Run and record the exact Python baseline**

```powershell
$JIT_PY='C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe'
& $JIT_PY -m pip check
& $JIT_PY -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
& $JIT_PY -m pytest uniride_core/tests optimizer_api/tests -q -p no:cacheprovider --tb=short
```

Record exact pass/fail/skip/warning counts and environment output in the manifest.

- [ ] **Step 6: Run and record frontend baseline diagnostics**

Use the ignored `node_modules` junction only for diagnostics; do not run `npm ci` through the junction.

```powershell
.\node_modules\.bin\eslint.cmd src --ext .ts,.tsx
.\node_modules\.bin\tsc.cmd --noEmit
.\node_modules\.bin\vitest.cmd run
```

Expected lint baseline: `24 errors, 7 warnings`. Record exact typecheck/test results separately.

- [ ] **Step 7: Commit the manifest baseline**

```powershell
git add WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "docs: record WIP consolidation baseline"
```

### Task 2: Reconstruct Optimizer API Containment

**Files:**
- Create: `optimizer_api/auth.py`
- Create: `optimizer_api/runtime_config.py`
- Create: `optimizer_api/tests/test_phase0_containment.py`
- Modify: `optimizer_api/main.py`
- Modify: `optimizer_api/routers/benchmark.py`
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`

**Interfaces:**
- Produces: `require_internal_api_key(x_internal_api_key)`, `optimizer_host()`, and `_resolve_cli_filename(filename)`.
- Preserves: existing `/api/v1/benchmark/cli/*` response shapes except removal of absolute filepath input/output.

- [ ] **Step 1: Write failing containment tests**

```python
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from optimizer_api.auth import require_internal_api_key
from optimizer_api.runtime_config import optimizer_host
from optimizer_api.routers import benchmark


def test_optimizer_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("OPTIMIZER_HOST", raising=False)
    assert optimizer_host() == "127.0.0.1"


def test_internal_key_is_optional_but_rejects_mismatch(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    asyncio.run(require_internal_api_key(None))
    monkeypatch.setenv("INTERNAL_API_KEY", "expected")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_internal_api_key("wrong"))
    assert exc.value.status_code == 403


def test_cli_filename_cannot_escape_result_roots(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    (root / "valid.json").write_text("[]", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))
    assert benchmark._resolve_cli_filename("valid.json") == str((root / "valid.json").resolve())
    with pytest.raises(HTTPException):
        benchmark._resolve_cli_filename("../outside.json")


def test_cli_file_listing_does_not_expose_absolute_paths(tmp_path, monkeypatch):
    root = tmp_path / "results"
    root.mkdir()
    (root / "valid.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(benchmark, "CLI_RESULTS_DIR", str(root))
    monkeypatch.setattr(benchmark, "CLI_RESULTS_NUMBA_DIR", str(tmp_path / "missing"))
    rows = benchmark._find_cli_json_files()
    assert rows[0]["filename"] == "valid.json"
    assert "filepath" not in rows[0]
```

- [ ] **Step 2: Verify RED**

```powershell
$JIT_PY='C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe'
& $JIT_PY -m pytest optimizer_api/tests/test_phase0_containment.py -q -p no:cacheprovider --tb=short
```

Expected: collection or assertion failure because the new modules/functions do not exist and C1 exposes `filepath`.

- [ ] **Step 3: Implement minimal dynamic authentication and host configuration**

```python
# optimizer_api/auth.py
import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException


async def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("INTERNAL_API_KEY")
    if expected is None:
        return
    if x_internal_api_key is None or not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
```

```python
# optimizer_api/runtime_config.py
import os


def optimizer_host() -> str:
    return os.getenv("OPTIMIZER_HOST", "127.0.0.1")
```

Use `optimizer_host()` in `optimizer_api/main.py`. In the benchmark router, accept only `filename`, resolve it through `Path.resolve()` plus `relative_to()` against the two configured roots, remove absolute paths from listings, and add `Depends(require_internal_api_key)` to `/cli/files`, `/cli/import`, and `/cli/preview`.

- [ ] **Step 4: Verify GREEN and regressions**

```powershell
& $JIT_PY -m pytest optimizer_api/tests/test_phase0_containment.py optimizer_api/tests/test_benchmark_router_problem_loading.py -q -p no:cacheprovider --tb=short
```

Expected: all pass.

- [ ] **Step 5: Record admitted/rejected security hunks and commit**

Explicitly record that `src/proxy.ts` internal-key forwarding was rejected because the historical header did not reach Python backend fetches.

```powershell
git add optimizer_api/auth.py optimizer_api/runtime_config.py optimizer_api/main.py optimizer_api/routers/benchmark.py optimizer_api/tests/test_phase0_containment.py WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "fix(api): reconstruct Phase 0 containment"
```

### Task 3: Align Python Dependency Contracts

**Files:**
- Modify: `academic_benchmark/tests/test_dependency_manifest.py`
- Modify: `optimizer_api/requirements.txt`
- Modify: `pyproject.toml`
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`

**Interfaces:**
- Produces: one compatible Pydantic pair across package manifests and explicit NumPy/Numba minimum versions.
- Does not produce: `requirements-lock.txt`.

- [ ] **Step 1: Add failing manifest assertions**

```python
def test_pyproject_declares_supported_numpy_numba_floors():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(data["project"]["dependencies"])
    assert "numpy>=1.24.0" in dependencies
    assert "numba>=0.58.0" in dependencies


def test_optimizer_requirements_match_pydantic_pair():
    requirements = (PROJECT_ROOT / "optimizer_api" / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "pydantic==2.13.4" in requirements
    assert "pydantic-core==2.46.4" in requirements
```

- [ ] **Step 2: Verify RED**

```powershell
& $JIT_PY -m pytest academic_benchmark/tests/test_dependency_manifest.py -q -p no:cacheprovider --tb=short
```

Expected: the new floor and optimizer-pair assertions fail.

- [ ] **Step 3: Make the minimal manifest changes**

In `pyproject.toml`, replace `numpy` and `numba` with `numpy>=1.24.0` and `numba>=0.58.0`. In `optimizer_api/requirements.txt`, replace the broad Pydantic entry with:

```text
pydantic==2.13.4
pydantic-core==2.46.4
```

Do not create or copy `requirements-lock.txt`.

- [ ] **Step 4: Verify GREEN and environment consistency**

```powershell
& $JIT_PY -m pytest academic_benchmark/tests/test_dependency_manifest.py -q -p no:cacheprovider --tb=short
& $JIT_PY -m pip check
```

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml optimizer_api/requirements.txt academic_benchmark/tests/test_dependency_manifest.py WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "build: align Python dependency contracts"
```

### Task 4: Restore the Frontend Lint Gate and Hydration-Safe Mobile Hook

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `eslint.config.mjs`
- Delete: `.eslintrc.json`
- Create: `src/hooks/use-mobile.test.tsx`
- Modify: `src/hooks/use-mobile.ts`
- Modify: `src/hooks/use-mobile.tsx`
- Modify only as required by the accepted `1e42652` lint hunks: the 22 TS/TSX files listed by `git show --name-only 1e42652 -- src`
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`

**Interfaces:**
- Produces: `npm run lint` backed by ESLint 9 and a hydration-stable `useIsMobile()` implemented with `useSyncExternalStore`.
- Preserves: UI behavior; lint refactors may not alter API payloads, routing, or academic code.

- [ ] **Step 1: Add the failing hook test**

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useIsMobile } from "./use-mobile";

describe("useIsMobile", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true });
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: () => ({
        matches: false,
        media: "",
        onchange: null,
        addEventListener: (_type: string, callback: () => void) => window.addEventListener("resize", callback),
        removeEventListener: (_type: string, callback: () => void) => window.removeEventListener("resize", callback),
        dispatchEvent: () => true,
      }),
    });
  });

  it("updates from the external viewport store without effect-driven state", () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
    act(() => {
      window.innerWidth = 640;
      window.dispatchEvent(new Event("resize"));
    });
    expect(result.current).toBe(true);
  });
});
```

- [ ] **Step 2: Verify RED and capture the lint RED state**

```powershell
.\node_modules\.bin\vitest.cmd run src/hooks/use-mobile.test.tsx
.\node_modules\.bin\eslint.cmd src --ext .ts,.tsx
```

Expected: hook test fails to update; lint reports `24 errors, 7 warnings`.

- [ ] **Step 3: Declare the real lint toolchain and regenerate only the lockfile**

Set:

```json
"lint": "eslint src/ --ext .ts,.tsx"
```

Add `eslint: ^9.39.5` and `eslint-config-next: ^16.2.12` to `devDependencies`. Remove `.eslintrc.json`. Run `npm install --package-lock-only --ignore-scripts` from the worktree; never copy the rescue lockfile wholesale.

- [ ] **Step 4: Apply the approved flat-config policy**

Use the two Next flat configs, set `reportUnusedDisableDirectives` to `warn`, set `@typescript-eslint/no-explicit-any` to `warn`, enforce `react-hooks/set-state-in-effect`, `react-hooks/purity`, `no-fallthrough`, and `no-unreachable` as errors, and retain only `react/no-unescaped-entities` as disabled. Do not retain the C1 blanket disabling block.

- [ ] **Step 5: Implement the hydration-safe hook in both duplicate modules**

```tsx
import * as React from "react"

const MOBILE_BREAKPOINT = 768

function subscribe(onStoreChange: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener("change", onStoreChange)
  return () => mql.removeEventListener("change", onStoreChange)
}

function getSnapshot() {
  return window.innerWidth < MOBILE_BREAKPOINT
}

function getServerSnapshot() {
  return false
}

export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
```

- [ ] **Step 6: Reconstruct only the accepted lint-error hunks**

Use `git show 1e42652 -- <path>` as evidence, then use `apply_patch` on current files. The allowed paths are exactly the TS/TSX paths emitted by `git show --name-only 1e42652 -- src`, excluding `uniride_core/algorithms/tsplib_parser.py`. Each hunk must correspond to one of the captured 24 lint errors: declaration-before-use, synchronous effect state, purity, fallthrough, unreachable code, or manual memoization preservation. Do not import roadmap, worklog, API router, or academic hunks.

- [ ] **Step 7: Verify GREEN**

```powershell
.\node_modules\.bin\vitest.cmd run src/hooks/use-mobile.test.tsx
npm run lint
npm run typecheck
npm test -- --run
```

Expected: zero lint errors; warnings may not exceed the seven recorded baseline warnings; typecheck and tests pass.

- [ ] **Step 8: Commit**

```powershell
git add package.json package-lock.json eslint.config.mjs .eslintrc.json src WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "fix(frontend): restore lint and hydration gates"
```

### Task 5: Add WIP-Centered Continuous Integration

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `academic_benchmark/tests/test_ci_contract.py`
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`

**Interfaces:**
- Produces: CI for pushes and pull requests targeting `WIP`, without the rejected historical `requirements-lock.txt`.

- [ ] **Step 1: Write the failing workflow contract test**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ci_targets_wip_and_uses_declared_install_contracts():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "branches: [WIP]" in text
    assert 'npm ci' in text
    assert 'npm run lint' in text
    assert 'npm run typecheck' in text
    assert 'npm test -- --run' in text
    assert 'pip install -e ".[test]" -c academic_benchmark/jit-benchmark-constraints.txt' in text
    assert 'requirements-lock.txt' not in text
```

- [ ] **Step 2: Verify RED**

```powershell
& $JIT_PY -m pytest academic_benchmark/tests/test_ci_contract.py -q -p no:cacheprovider --tb=short
```

Expected: fail because `.github/workflows/ci.yml` does not exist.

- [ ] **Step 3: Create the minimal workflow**

Create frontend and Python jobs on `ubuntu-latest`. Both push and pull-request triggers use `branches: [WIP]`. Frontend uses Node 22, `npm ci`, lint, typecheck, and `npm test -- --run`. Python uses Python 3.14, installs `-e ".[test]"` through `academic_benchmark/jit-benchmark-constraints.txt`, runs `pip check`, then runs collection plus focused academic/core/API tests. Keep `.github/workflows/benchmark.yml` unchanged.

- [ ] **Step 4: Verify GREEN**

```powershell
& $JIT_PY -m pytest academic_benchmark/tests/test_ci_contract.py -q -p no:cacheprovider --tb=short
```

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/ci.yml academic_benchmark/tests/test_ci_contract.py WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "ci: validate the WIP integration branch"
```

### Task 6: Final Evidence, Full Validation, and Independent Review

**Files:**
- Modify: `WIP_CONSOLIDATION_MANIFEST_2026-08-01.md`

**Interfaces:**
- Consumes: all Task 1 baseline commands and evidence inventory.
- Produces: final pass/fail comparison, artifact proof, branch diff review, and promotion decision.

- [ ] **Step 1: Prove artifact and academic-spine integrity**

```powershell
git diff --name-only 0882081..HEAD | rg -i "(^|/)(\.numba_cache|__pycache__|\.pytest_cache|\.next|node_modules|\.venv)(/|$)|\.(nbc|nbi|pyc)$"
git diff --exit-code 0882081..HEAD -- uniride_core/algorithms/tsplib_parser.py
git diff --check
git merge-base --is-ancestor origin/WIP HEAD
```

Expected: artifact search prints nothing; parser diff is empty; checks exit `0`.

- [ ] **Step 2: Re-run the exact Python baseline commands**

```powershell
& $JIT_PY -m pip check
& $JIT_PY -m pytest academic_benchmark/tests -q -p no:cacheprovider --tb=short
& $JIT_PY -m pytest uniride_core/tests optimizer_api/tests -q -p no:cacheprovider --tb=short
```

Final failures and unexpected skips must not exceed Task 1.

- [ ] **Step 3: Validate through a clean frontend install**

Remove only the verified worktree `node_modules` junction, then run:

```powershell
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

A functional failure blocks promotion. An environment-only build blocker must be recorded and explicitly accepted by the user.

- [ ] **Step 4: Verify C1 evidence hashes and finalize the manifest**

Recompute every Task 1 blob hash from the working tree and compare it with the manifest. Add exact final commands, counts, skips, warnings, environment facts, commit range, admitted/rejected hunk decisions, and the open post-consolidation audit backlog.

- [ ] **Step 5: Commit final evidence**

```powershell
git add WIP_CONSOLIDATION_MANIFEST_2026-08-01.md
git diff --cached --check
git commit -m "docs: finalize WIP consolidation evidence"
```

- [ ] **Step 6: Run whole-branch review**

Review both ranges:

```powershell
git log --oneline 0882081..HEAD
git diff --stat 0882081..HEAD
git diff --check
git status --short --branch
```

No unresolved Critical or Important review finding may remain.

### Task 7: Push, Fast-Forward WIP, and Smoke the Remote Head

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: Task 6 green promotion decision.
- Produces: `origin/WIP` at the validated consolidation SHA and a clean cross-machine starting point.

- [ ] **Step 1: Re-fetch and prove the push remains fast-forward**

```powershell
git fetch --prune origin
git merge-base --is-ancestor origin/WIP HEAD
git status --short --branch
```

Stop if the remote moved incompatibly or the worktree is dirty.

- [ ] **Step 2: Push the consolidation branch**

```powershell
git push -u origin codex/wip-consolidation-20260801
```

- [ ] **Step 3: Fast-forward WIP without force**

```powershell
git push origin HEAD:WIP
git fetch origin WIP
git rev-parse HEAD
git rev-parse origin/WIP
```

Expected: both SHAs are identical.

- [ ] **Step 4: Create a fresh remote-WIP smoke worktree**

```powershell
git worktree add --detach C:\tmp\UniRide-wip-smoke-20260801 origin/WIP
$JIT_PY='C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide\.venv-jit\Scripts\python.exe'
& $JIT_PY -m pytest C:\tmp\UniRide-wip-smoke-20260801\academic_benchmark\tests\test_manifest_contracts.py C:\tmp\UniRide-wip-smoke-20260801\academic_benchmark\tests\test_algorithm_capability_catalog.py C:\tmp\UniRide-wip-smoke-20260801\optimizer_api\tests\test_phase0_containment.py -q -p no:cacheprovider --tb=short
```

Expected: all smoke tests pass.

- [ ] **Step 5: Report branch retirement candidates without deleting them**

Recommend retirement for exact duplicate or contained branches only after the user reviews the final manifest. Do not delete branches or tags in this package.
