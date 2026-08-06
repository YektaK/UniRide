# P3 — Benchmark Run Ownership (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Owner-gate `/stop`, `/status`, and `/results/{run_id}` with a server-issued per-run bearer token, held by the Next.js proxies in a per-run HttpOnly cookie.

**Architecture:** `create_run`/`import_run` mint `secrets.token_urlsafe(32)` and store only its SHA-256 hash on `BenchmarkRunState`; the token is returned once in the creation response. A FastAPI dependency `require_run_owner` validates the `X-Benchmark-Owner-Token` header on the three gated endpoints. The Next.js `/run` proxy stores the token in an HttpOnly cookie per run_id; the stop/status/results proxies read that cookie and forward the header.

**Tech Stack:** Python 3.14 / FastAPI / pytest. Next.js App Router route handlers / TypeScript / vitest (node env, `@` → `src`).

**Spec:** `docs/superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md`

**Python test runner:** `C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest ...` run from repo root `C:\tmp\UniRide-phase1-occurrence`. Frontend runner: `npm test` (vitest) from repo root.

---

### Task 1: Backend — token hash / verify helpers + `owner_token_hash` field

**Files:**
- Create: `optimizer_api/tests/test_p3_owner_tokens.py`
- Modify: `optimizer_api/benchmark_state.py` (add `import hashlib`; add field; add helpers; export helpers in `__all__`)

- [ ] **Step 1: Write the failing test**

Create `optimizer_api/tests/test_p3_owner_tokens.py`:

```python
"""Phase 3 — benchmark run ownership (P3) tests.

See docs/superpowers/specs/2026-08-06-p3-benchmark-run-owner-tokens-design.md
"""

import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from optimizer_api.benchmark_state import (
    BenchmarkRunState,
    BenchmarkStateManager,
    hash_owner_token,
    verify_owner_token,
)
from optimizer_api.routers import benchmark

API_HEADERS = {"X-Internal-Api-Key": "phase3-test-key"}


def _state_with_hash(token_plain):
    return BenchmarkRunState(
        run_id="st",
        owner_token_hash=hash_owner_token(token_plain),
    )


def test_hash_owner_token_is_sha256_hex():
    assert hash_owner_token("tok") == hashlib.sha256(b"tok").hexdigest()


def test_verify_owner_token_correct_wrong_missing():
    st = _state_with_hash("secret")
    assert verify_owner_token(st, "secret") is True
    assert verify_owner_token(st, "wrong") is False
    assert verify_owner_token(st, None) is False


def test_verify_owner_token_missing_hash_is_false():
    st = BenchmarkRunState(run_id="x")
    assert verify_owner_token(st, "anything") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api/tests/test_p3_owner_tokens.py -q`
Expected: FAIL with `ImportError: cannot import name 'hash_owner_token'`

- [ ] **Step 3: Write minimal implementation**

In `optimizer_api/benchmark_state.py`:
- Add `import hashlib` after `import threading`.
- Add field to `BenchmarkRunState` dataclass after `results`:
  `owner_token_hash: Optional[str] = None`
- Add module-level helpers after the dataclass:

```python
def hash_owner_token(token: str) -> str:
    """SHA-256 hex digest of an owner token (never stored in plaintext)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_owner_token(state: "BenchmarkRunState", provided: Optional[str]) -> bool:
    """True only if state has a stored hash and provided matches it."""
    if state.owner_token_hash is None or provided is None:
        return False
    import secrets
    return secrets.compare_digest(
        state.owner_token_hash,
        hash_owner_token(provided),
    )
```

- Add `"hash_owner_token"` and `"verify_owner_token"` to the `__all__` list.

- [ ] **Step 4: Run test to verify it passes**

Run: `C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api/tests/test_p3_owner_tokens.py::test_hash_owner_token_is_sha256_hex -v` then the other three.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizer_api/benchmark_state.py optimizer_api/tests/test_p3_owner_tokens.py
git commit -m "feat(benchmark): add owner-token hash/verify helpers"
```

---

### Task 2: Backend — `create_run` / `import_run` return `(state, owner_token)`

**Files:**
- Modify: `optimizer_api/benchmark_state.py` (`create_run`, `import_run`, `Tuple` import)
- Modify: `optimizer_api/tests/test_api_hardening_phase0.py` (update P1/P2/D3 tests to unpack tuple)
- Modify: `optimizer_api/tests/test_p3_owner_tokens.py`

- [ ] **Step 1: Add failing tests**

Append to `optimizer_api/tests/test_p3_owner_tokens.py`:

```python
def test_create_run_returns_state_and_token():
    mgr = BenchmarkStateManager()
    state, token = mgr.create_run("create-tok", 5, {"alg": "ga"})
    assert state is not None
    assert state.run_id == "create-tok"
    assert isinstance(token, str) and len(token) >= 20
    assert state.owner_token_hash == hash_owner_token(token)
    assert token not in state.parameters.values()


def test_create_run_rejection_returns_none_none():
    mgr = BenchmarkStateManager()
    s1, t1 = mgr.create_run("create-dup", 2, {})
    assert s1 is not None and t1 is not None
    s2, t2 = mgr.create_run("create-dup", 2, {})
    assert s2 is None and t2 is None


def test_import_run_returns_state_and_token():
    mgr = BenchmarkStateManager()
    state, token = mgr.import_run(
        "import-tok",
        {"results": [], "total_experiments": 0, "parameters": {}},
    )
    assert state is not None
    assert isinstance(token, str) and len(token) >= 20
    assert state.owner_token_hash == hash_owner_token(token)
    assert token not in state.parameters


def test_import_run_duplicate_returns_none_none():
    mgr = BenchmarkStateManager()
    data = {"results": [], "total_experiments": 0, "parameters": {}}
    s1, _t1 = mgr.import_run("import-dup", data)
    assert s1 is not None
    s2, t2 = mgr.import_run("import-dup", data)
    assert s2 is None and t2 is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe -m pytest optimizer_api/tests/test_p3_owner_tokens.py -k "create_run or import_run" -v`
Expected: FAIL — `create_run` still returns a single `BenchmarkRunState`, so `state, token = ...` raises `TypeError: cannot unpack non-iterable ...`.

- [ ] **Step 3: Implement tuple returns**

In `optimizer_api/benchmark_state.py`:
- Change import to `from typing import Dict, Optional, List, Any, Tuple`.
- Add `import secrets` at top.
- `hash_owner_token` becomes:

```python
def hash_owner_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _mint_owner_token() -> str:
    return secrets.token_urlsafe(32)
```

`verify_owner_token` no longer needs a local import (keep `secrets` top-level).

- `create_run` docstring/signature:

```python
def create_run(self, run_id: str, total_experiments: int, parameters: Dict) -> Tuple[Optional[BenchmarkRunState], Optional[str]]:
    """Create a new benchmark run; returns (state, owner_token), or (None, None)."""
    with self._lock:
        self._evict_expired()
        if run_id in self._runs:
            return (None, None)
        running_count = len([
            s for s in self._runs.values()
            if s.status == BenchmarkStatus.RUNNING
        ])
        if running_count >= MAX_CONCURRENT_BENCHMARKS:
            return (None, None)
        token = _mint_owner_token()
        state = BenchmarkRunState(
            run_id=run_id,
            total_experiments=total_experiments,
            parameters=parameters,
            owner_token_hash=hash_owner_token(token),
        )
        self._runs[run_id] = state
        return (state, token)
```

- `import_run` returns `Tuple[Optional[BenchmarkRunState], Optional[str]]`, gains `owner_token_hash=hash_owner_token(token)` and returns `(state, token)`; duplicate branch returns `(None, None)`.

- [ ] **Step 4: Update existing P1/P2/D3 tests in `test_api_hardening_phase0.py`**

Change every `X = mgr.create_run(...)` / `X = mgr.import_run(...)` to unpack the tuple, and every use of `X` that was the state to the first element. The four D3 tests and the P2 test:

```python
def test_p2_create_run_returns_none_when_limit_hit_then_accepts_after_complete(
    monkeypatch,
):
    from optimizer_api.benchmark_state import BenchmarkStateManager

    monkeypatch.setattr("optimizer_api.benchmark_state.MAX_CONCURRENT_BENCHMARKS", 1)

    mgr = BenchmarkStateManager()

    s1, _t1 = mgr.create_run("p2-run-1", 5, {})
    assert s1 is not None

    s2, _t2 = mgr.create_run("p2-run-2", 5, {})
    assert s2 is None

    mgr.complete_run("p2-run-1", 5, "done")
    s3, _t3 = mgr.create_run("p2-run-3", 5, {})
    assert s3 is not None


def test_d3_create_run_rejects_duplicate_run_id():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    s1, _t1 = mgr.create_run("dup-create-1", 5, {"alg": "ga"})
    assert s1 is not None

    s2, _t2 = mgr.create_run("dup-create-1", 5, {"alg": "pso"})
    assert s2 is None
    assert mgr.get_run("dup-create-1") is s1


def test_d3_import_run_rejects_duplicate_run_id():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    data = {"results": [], "total_experiments": 0, "parameters": {}}

    s1, _t1 = mgr.import_run("dup-import-1", data)
    assert s1 is not None

    s2, _t2 = mgr.import_run("dup-import-1", data)
    assert s2 is None
    assert mgr.get_run("dup-import-1") is s1


def test_d3_create_then_import_same_run_id_rejected():
    from optimizer_api.benchmark_state import BenchmarkStateManager

    mgr = BenchmarkStateManager()
    s1, _t1 = mgr.create_run("mixed-dupe-1", 3, {})
    assert s1 is not None

    s2, _t2 = mgr.import_run("mixed-dupe-1", {"results": [], "total_experiments": 0, "parameters": {}})
    assert s2 is None
```

And `test_p1_import_run_unit`: unpack `state, _token = mgr.import_run("unit-import-1", {...})` and keep the existing assertions on `state`.

- [ ] **Step 5: Run the full hardening + P3 suites**

Run: `pytest tests/test_api_hardening_phase0.py tests/test_p3_owner_tokens.py -q`
Expected: PASS (existing 49 + new P3 unit tests).

- [ ] **Step 6: Commit**

```bash
git add optimizer_api/benchmark_state.py optimizer_api/tests/test_api_hardening_phase0.py optimizer_api/tests/test_p3_owner_tokens.py
git commit -m "feat(benchmark): return (state, owner_token) from run creation methods"
```

---

### Task 3: Backend — gate endpoints + include token in creation responses

**Files:**
- Modify: `optimizer_api/routers/benchmark.py`
- Modify: `optimizer_api/tests/test_p3_owner_tokens.py`

- [ ] **Step 1: Add failing router tests**

Append to `optimizer_api/tests/test_p3_owner_tokens.py`:

```python
def _valid_payload(**overrides):
    payload = {
        "run_id": "p3-router-run",
        "algorithms": [{"id": "ga", "params": {"seed": 7, "max_iterations": 20}}],
        "problems": ["berlin52"],
        "settings": {"n_runs": 1, "seed": 7},
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "phase3-test-key")
    app = FastAPI()
    app.include_router(benchmark.router)
    return TestClient(app)


class _NoopRunner:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, problems=None, algorithms=None, n_runs=1, seed=None, skip_cached=False):
        pass


class _FakeProblem:
    name = "berlin52"


def test_run_response_includes_owner_token(client, monkeypatch):
    monkeypatch.setattr(benchmark, "_load_benchmark_problem", lambda name: _FakeProblem())
    monkeypatch.setattr(benchmark, "BenchmarkRunner", _NoopRunner)
    resp = client.post(
        "/api/v1/benchmark/run",
        json=_valid_payload(run_id="p3-run-tok"),
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    token = body.get("owner_token")
    assert token and isinstance(token, str)
    state = benchmark.benchmark_state_manager.get_run("p3-run-tok")
    assert state.owner_token_hash == hash_owner_token(token)
    benchmark.benchmark_state_manager.complete_run("p3-run-tok", 0, "done")


def test_import_response_includes_owner_token(client):
    resp = client.post(
        "/api/v1/benchmark/import",
        json={"run_id": "p3-import-token", "results": [], "total_experiments": 0, "parameters": {}},
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json().get("owner_token"), str)


def test_cli_import_response_includes_owner_token(client, monkeypatch):
    monkeypatch.setattr(benchmark, "_resolve_cli_filename", lambda f: "dummy.json")
    monkeypatch.setattr(benchmark, "_load_and_validate_cli_json", lambda f: [{"problem": "P1", "strategy": "A", "n_runs": 1}])
    monkeypatch.setattr(benchmark, "_convert_cli_record_to_web", lambda rec, run_number: {"algorithm": "ga", "problem": "P1", "run_number": run_number})
    resp = client.post(
        "/api/v1/benchmark/cli/import?filename=dummy.json&run_id=p3-cli-token",
        headers={"X-Internal-Api-Key": "phase3-test-key"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json().get("owner_token"), str)


@pytest.mark.parametrize("method,path_fn", [
    ("get", lambda rid: ("/api/v1/benchmark/status", {"params": {"run_id": rid}})),
    ("post", lambda rid: ("/api/v1/benchmark/stop", {"params": {"run_id": rid}})),
    ("get", lambda rid: (f"/api/v1/benchmark/results/{rid}", {})),
])
def test_owner_gated_endpoints(method, path_fn, client, monkeypatch):
    state, token = benchmark.benchmark_state_manager.create_run("p3-gate", 2, {})
    assert state is not None
    try:
        path, kwargs = path_fn("p3-gate")
        base = {"X-Internal-Api-Key": "phase3-test-key"}

        no_tok = getattr(client, method)(path, headers=base, **kwargs)
        assert no_tok.status_code == 403

        wrong = getattr(client, method)(path, headers={**base, "X-Benchmark-Owner-Token": "wrong"}, **kwargs)
        assert wrong.status_code == 403

        ok = getattr(client, method)(path, headers={**base, "X-Benchmark-Owner-Token": token}, **kwargs)
        assert ok.status_code == 200
    finally:
        benchmark.benchmark_state_manager.complete_run("p3-gate", 2, "done")


def test_owner_404_when_run_missing(client):
    cases = [
        ("get", "/api/v1/benchmark/status?run_id=nope", {}),
        ("post", "/api/v1/benchmark/stop?run_id=nope", {}),
        ("get", "/api/v1/benchmark/results/nope", {}),
    ]
    for method, path, kwargs in cases:
        resp = getattr(client, method)(
            path,
            headers={"X-Internal-Api-Key": "phase3-test-key", "X-Benchmark-Owner-Token": "whatever"},
            **kwargs,
        )
        assert resp.status_code == 404


def test_owner_403_when_run_has_no_hash(client, monkeypatch):
    state, _tok = benchmark.benchmark_state_manager.create_run("p3-nohash", 1, {})
    state.owner_token_hash = None
    resp = client.get(
        "/api/v1/benchmark/status?run_id=p3-nohash",
        headers={"X-Internal-Api-Key": "phase3-test-key", "X-Benchmark-Owner-Token": "x"},
    )
    assert resp.status_code == 403
    benchmark.benchmark_state_manager.complete_run("p3-nohash", 1, "done")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_p3_owner_tokens.py -q`
Expected: FAIL — `Owner token missing` 200s (no gate yet), `owner_token` absent from `/run` response.

- [ ] **Step 3: Implement**

In `optimizer_api/routers/benchmark.py`:
- Change imports: `from typing import Any, List, Dict, Optional, Annotated`; add `Header` to the fastapi import line.
- Add `verify_owner_token` to the `benchmark_state` import (line 21).
- Add the dependency after the router definition:

```python
def require_run_owner(
    run_id: str,
    x_benchmark_owner_token: Annotated[str | None, Header()] = None,
) -> None:
    """Gate /status, /stop, /results on the per-run owner token."""
    state = benchmark_state_manager.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    if not verify_owner_token(state, x_benchmark_owner_token):
        raise HTTPException(status_code=403, detail="Forbidden: missing or invalid owner token")
```

- Apply to the three endpoints by adding `dependencies=[Depends(require_run_owner)]` to each `@router.get("/status")`, `@router.post("/stop")`, `@router.get("/results/{run_id}")`. Their handler bodies stay unchanged.

- Unpack token in the two `/run` impls:

`_start_benchmark_impl` (line ~275):
```python
        state, owner_token = benchmark_state_manager.create_run(
            run_id=run_id, total_experiments=total_experiments,
            parameters={"algorithms": algorithms, "problems": problems, "settings": settings}
        )
        if state is None:
            raise HTTPException(
                status_code=429,
                detail={"error": "Maximum concurrent benchmarks reached", "max_concurrent": MAX_CONCURRENT_BENCHMARKS}
            )
```
and add `"owner_token": owner_token,` to its return dict.

`_start_matrix_native_benchmark_impl` (line ~351): unpack `state, owner_token = ...`, same 429 branch, and add `"owner_token": owner_token,` to the return dict (line 425).

- `import_benchmark` (line ~481): `state, owner_token = ...`; `if state is None:` 409 branch unchanged; add `"owner_token": owner_token` to the return dict.

- `import_cli_benchmark_results` (line ~656): `state, owner_token = benchmark_state_manager.create_run(...)`; add `"owner_token": owner_token` to its return dict.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_p3_owner_tokens.py -q`
Expected: PASS.

- [ ] **Step 5: Run hardening suite + codebase regression**

Run: `pytest tests/test_api_hardening_phase0.py -q` then full `pytest tests -q -p no:cacheprovider` (expect ~320, ~3–4 min).
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add optimizer_api/routers/benchmark.py optimizer_api/tests/test_p3_owner_tokens.py
git commit -m "feat(benchmark): owner-gate status/stop/results with per-run token"
```

---

### Task 4: Frontend — cookie helper

**Files:**
- Create: `src/lib/benchmark-owner-cookie.ts`
- Create: `src/lib/benchmark-owner-cookie.test.ts`

- [ ] **Step 1: Write failing test**

`src/lib/benchmark-owner-cookie.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { NextRequest, NextResponse } from "next/server";
import {
  getOwnerToken,
  ownerCookieName,
  setOwnerCookie,
} from "./benchmark-owner-cookie";

describe("benchmark owner cookie", () => {
  it("builds a run-scoped cookie name", () => {
    expect(ownerCookieName("run-1")).toBe("benchmark_owner_run-1");
  });

  it("round-trips the token via the cookie", () => {
    const res = NextResponse.json({ ok: true });
    setOwnerCookie(res, "run-1", "TOKEN");
    const cookie = res.cookies.get("benchmark_owner_run-1");
    expect(cookie?.value).toBe("TOKEN");
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.maxAge).toBe(7200);
    expect(cookie?.sameSite).toBe("lax");
    expect(cookie?.path).toBe("/api/benchmark");

    const req = new NextRequest("http://x/api/benchmark/status", {
      headers: { cookie: "benchmark_owner_run-1=TOKEN" },
    });
    expect(getOwnerToken(req, "run-1")).toBe("TOKEN");
    expect(getOwnerToken(req, "run-2")).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/benchmark-owner-cookie.test.ts`
Expected: FAIL — module does not exist / import error.

- [ ] **Step 3: Implement**

Create `src/lib/benchmark-owner-cookie.ts`:

```ts
import type { NextRequest, NextResponse } from "next/server";

export const OWNER_COOKIE_PREFIX = "benchmark_owner_";
export const OWNER_COOKIE_MAX_AGE = 7200;

export function ownerCookieName(runId: string): string {
  return `${OWNER_COOKIE_PREFIX}${runId}`;
}

export function getOwnerToken(
  request: NextRequest,
  runId: string
): string | undefined {
  return request.cookies.get(ownerCookieName(runId))?.value;
}

export function setOwnerCookie(
  response: NextResponse,
  runId: string,
  token: string
): void {
  response.cookies.set(ownerCookieName(runId), token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/api/benchmark",
    maxAge: OWNER_COOKIE_MAX_AGE,
  });
}

export function isRunExistsStatus(status: number): boolean {
  return status === 200 || status === 403;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/benchmark-owner-cookie.test.ts` (from repo root `C:\tmp\UniRide-phase1-occurrence`)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/benchmark-owner-cookie.ts src/lib/benchmark-owner-cookie.test.ts
git commit -m "feat(benchmark): add owner-cookie helper for run ownership"
```

---

### Task 5: Frontend — `/run` proxy sets cookie, strips token, precheck treats 403 as exists

**Files:**
- Modify: `src/app/api/benchmark/run/route.ts`
- Create: `src/app/api/benchmark/run/route.test.ts`

- [ ] **Step 1: Write failing test**

Create `src/app/api/benchmark/run/route.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

type FetchResponse = { status: number; json: unknown };

function stubFetch(responses: FetchResponse[]) {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      const r = responses[Math.min(i, responses.length - 1)];
      i += 1;
      return {
        ok: r.status >= 200 && r.status < 300,
        status: r.status,
        json: async () => r.json,
        text: async () => JSON.stringify(r.json),
      };
    })
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function runRequest(runId?: string) {
  return new NextRequest("http://x/api/benchmark/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      ...(runId ? { run_id: runId } : {}),
      algorithms: [{ id: "ga", params: {} }],
      problems: ["berlin52"],
      settings: { n_runs: 1 },
    }),
  });
}

describe("POST /api/benchmark/run", () => {
  it("sets the owner cookie and does not leak owner_token to the browser", async () => {
    stubFetch([
      { status: 404, json: { detail: "not found" } }, // duplicate pre-check
      {
        status: 200,
        json: {
          run_id: "heap-run-1",
          status: "running",
          total_experiments: 1,
          start_time: "now",
          owner_token: "HEAPTOKEN",
        },
      },
    ]);
    const res = await POST(runRequest("heap-run-1"));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.owner_token).toBeUndefined();
    expect(res.cookies.get("benchmark_owner_heap-run-1")?.value).toBe(
      "HEAPTOKEN"
    );
  });

  it("treats precheck 403 (exists, owned by someone else) as a conflict", async () => {
    stubFetch([{ status: 403, json: { detail: "Forbidden" } }]);
    const res = await POST(runRequest("taken-run"));
    expect(res.status).toBe(409);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/app/api/benchmark/run/route.test.ts`
Expected: FAIL — cookie `benchmark_owner_heap-run-1` undefined; owner_token leaked; 403 precheck returns 502.

- [ ] **Step 3: Implement**

In `src/app/api/benchmark/run/route.ts`:
- Import: `import { getOwnerToken, setOwnerCookie, isRunExistsStatus } from "@/lib/benchmark-owner-cookie";`
- Compute `const runId = providedRunId || generateBenchmarkRunId(now);` before the precheck (move up). Precheck becomes:

```ts
    const token = getOwnerToken(request, runId);
    const precheckHeaders: Record<string, string> = {};
    if (token) precheckHeaders["X-Benchmark-Owner-Token"] = token;

    const statusResponse = await fetch(
      `${BACKEND_URL}/api/v1/benchmark/status?run_id=${encodeURIComponent(runId)}`,
      { method: "GET", headers: precheckHeaders }
    );

    if (isRunExistsStatus(statusResponse.status)) {
      return NextResponse.json(
        { error: "Bu run_id zaten kullanılıyor. Lütfen farklı bir run_id deneyin." },
        { status: 409 }
      );
    }

    if (statusResponse.status !== 404) {
      return NextResponse.json(
        { error: "run_id doğrulaması sırasında backend erişim hatası oluştu." },
        { status: 502 }
      );
    }
```
- Keep the `providedRunId`-is-present guard: the precheck should only run when `providedRunId` was supplied (the current code only does duplicate-check for provided ids). Use `providedRunId` (the raw trimmed id) as the id for the precheck — as today.

- After the successful backend POST, replace the final `return NextResponse.json({...})` with:

```ts
    const browserResponse = NextResponse.json({
      run_id: runId,
      total_experiments: body.algorithms.length * body.problems.length * benchmarkRequest.settings.n_runs,
      problems_count: body.problems.length,
      algorithms_count: body.algorithms.length,
      n_runs: benchmarkRequest.settings.n_runs,
      status: "running",
      message: "Benchmark başlatıldı",
      start_time: now.toISOString(),
    });

    if (data.owner_token) {
      setOwnerCookie(browserResponse, runId, data.owner_token);
    }

    return browserResponse;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/app/api/benchmark/run/route.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/benchmark/run/route.ts src/app/api/benchmark/run/route.test.ts
git commit -m "feat(benchmark): set owner cookie on run start, treat 403 precheck as exists"
```

---

### Task 6: Frontend — stop/status/results proxies forward the owner token

**Files:**
- Modify: `src/app/api/benchmark/stop/route.ts`
- Modify: `src/app/api/benchmark/status/route.ts`
- Modify: `src/app/api/benchmark/run/status/route.ts`
- Modify: `src/app/api/benchmark/results/[runId]/route.ts`
- Create: `src/app/api/benchmark/stop/route.test.ts`

- [ ] **Step 1: Write failing test**

Create `src/app/api/benchmark/stop/route.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("POST /api/benchmark/stop", () => {
  it("forwards the owner token and sends run_id as a query param", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, opts?: RequestInit) => {
        capturedUrl = url;
        capturedHeaders = (opts?.headers as Record<string, string>) || {};
        return { ok: true, status: 200, json: async () => ({ run_id: "run-1", status: "stopped" }), text: async () => "" };
      })
    );

    const req = new NextRequest("http://x/api/benchmark/stop", {
      method: "POST",
      headers: { "content-type": "application/json", cookie: "benchmark_owner_stop-1=STOPTOKEN" },
      body: JSON.stringify({ runId: "stop-1" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(capturedUrl).toContain("/api/v1/benchmark/stop?run_id=stop-1");
    expect(capturedHeaders["X-Benchmark-Owner-Token"]).toBe("STOPTOKEN");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/app/api/benchmark/stop/route.test.ts`
Expected: FAIL — header missing; captured URL contains `/stop` JSON body form, not query param.

- [ ] **Step 3: Implement**

- `src/app/api/benchmark/stop/route.ts`:
  - Add `import { getOwnerToken } from "@/lib/benchmark-owner-cookie";`
  - Build headers with owner token and POST to query-param URL by runId:

```ts
    const ownerToken = getOwnerToken(request, runId);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (ownerToken) headers["X-Benchmark-Owner-Token"] = ownerToken;

    const response = await fetch(
      `${BACKEND_URL}/api/v1/benchmark/stop?run_id=${encodeURIComponent(runId)}`,
      { method: "POST", headers }
    );
```
  - Update the `.json({ run_id: runId, ... })` call to `body: JSON.stringify({})` (or drop the body entirely — the backend takes no body). Keep the existing error handling.

- `src/app/api/benchmark/status/route.ts` (the `GET /api/benchmark/status` proxy):
  - `const ownerToken = getOwnerToken(request as NextRequest, runId);`
  - add `...(ownerToken ? { "X-Benchmark-Owner-Token": ownerToken } : {})` to the fetch headers.

- `src/app/api/benchmark/run/status/route.ts`:
  - same pattern: `getOwnerToken(request, runId)` and add header to the `fetch(...)`.

- `src/app/api/benchmark/results/[runId]/route.ts`:
  - rename `_request` to `request`; `const ownerToken = getOwnerToken(request, runId);`; add header to fetch.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/app/api/benchmark/stop/route.test.ts`
Expected: PASS.

- [ ] **Step 5: Run the full frontend suite**

Run: `npm test`
Expected: PASS (all existing vitest tests + new ones).

- [ ] **Step 6: Commit**

```bash
git add src/app/api/benchmark/stop/route.ts src/app/api/benchmark/status/route.ts src/app/api/benchmark/run/status/route.ts "src/app/api/benchmark/results/[runId]/route.ts" src/app/api/benchmark/stop/route.test.ts
git commit -m "feat(benchmark): forward owner token from stop/status/results proxies"
```

---

### Task 7: Full regression + docs

**Files:**
- Verify only (no new code)

- [ ] **Step 1: Backend full suites**

Run: `pytest tests -q -p no:cacheprovider` (optimizer_api; ~3–4 min, includes the slow smoke test) and `pytest ../academic_benchmark/tests/test_atsp_integration.py -q` and `pytest ../uniride_core -q`.
Expected: all PASS.

- [ ] **Step 2: Frontend full suite**

Run: `npm test`
Expected: PASS.

- [ ] **Step 3: Whitespace + status check**

Run: `git diff --check` and `git status --short`
Expected: clean, no whitespace errors, working tree contains only intended changes.

- [ ] **Step 4: Commit any stragglers**

If anything uncommitted remains, commit with a message matching the work.

---

## Self-review notes

- Spec coverage: §2.1 (helpers+field) → Task 1; §2.2 (tuple returns) → Task 2; §2.3/§2.4 (responses + gate) → Task 3; §3.1 (helper) → Task 4; §3.2 `/run` → Task 5; §3.2 stop/status/results + `/stop` query-param fix → Task 6; §5.3 regression → Task 7. No section left uncovered.
- Type consistency: `require_run_owner(run_id, x_benchmark_owner_token)` dependency, `verify_owner_token(state, provided)`, helper returns, and the `(state, token)` tuples are consistent across all tasks.
- `/stop` still has its body removed — the frontend proxy now uses a query param exactly matching the backend contract verified in `test_b1_benchmark_endpoints_reject_missing_key` (`params={"run_id": ...}`).