# P3 — Benchmark Run Ownership (Phase 1) — Design (2026-08-06)

Branch: `codex/phase0-api-hardening-20260805` (phase0 hardening already merged into this PR).
Context: `docs/superpowers/specs/2026-08-05-phase0-api-hardening-audit.md` — P3 documented residual:
`run_id` is caller-supplied and the only key for `/status`, `/stop`, `/results`; any authed caller
can stop/read anyone's run by guessing the `run_id`.

Approved approach (brainstorming session): **server-issued bearer token + per-run HttpOnly cookie**.
Scope decision: owner-gate `/stop` + `/status` + `/results/{run_id}`. Frontend scope: include the
Next.js proxies, token held server-side in an HttpOnly cookie set by the `/run` proxy.

## 1. Threat model

- All authed callers share `INTERNAL_API_KEY`; there is no per-caller identity today.
- P3 adds per-run ownership: a caller may only `stop` / `status` / `results` runs it created
  (it holds the `owner_token` the server issued at creation).
- The `owner_token` is a bearer secret. The server stores only its SHA-256 digest, so a state
  dump cannot be used to impersonate the owner.

## 2. Backend changes (`optimizer_api`)

### 2.1 State model (`optimizer_api/benchmark_state.py`)

- Add field to `BenchmarkRunState`:
  `owner_token_hash: Optional[str] = None`
  It is never copied into any response payload, `parameters`, or `results`.
- New module helpers:
  - `hash_owner_token(token: str) -> str` — `hashlib.sha256(token.encode()).hexdigest()`.
  - `verify_owner_token(state, provided: Optional[str]) -> bool` — compares
    `secrets.compare_digest(state.owner_token_hash, hash_owner_token(provided))`;
    returns `False` when `state.owner_token_hash` is `None` (strict) or `provided` is `None`.

### 2.2 Creation methods return the token

- `create_run(...) -> Tuple[Optional[BenchmarkRunState], Optional[str]]`
- `import_run(...) -> Tuple[Optional[BenchmarkRunState], Optional[str]]`
- On success: mint `token = secrets.token_urlsafe(32)`, store `hash_owner_token(token)` on the
  state, return `(state, token)`.
- On rejection (duplicate `run_id` in D3 guard, or `create_run` concurrency limit):
  return `(None, None)`.
- **Test impact:** existing P2/D3 unit tests in `test_api_hardening_phase0.py` that call
  `mgr.create_run(...)` / `mgr.import_run(...)` and assert on the single return value must be
  updated to unpack the tuple. This is an intentional, contained change.

### 2.3 Router call sites (`optimizer_api/routers/benchmark.py`)

All four creation paths include `owner_token` in their success responses:

1. `_start_benchmark_impl` (`/run`) — already returns `state`; add `"owner_token": token`.
2. `_start_matrix_native_benchmark_impl` (matrix `/run`) — same.
3. `import_benchmark` (`/import`) — add `"owner_token": token`.
4. `import_cli_benchmark_results` (`/cli/import`) — add `"owner_token": token`.

`None` handling is unchanged: rejected create still maps to 409 (duplicate) / 429 (concurrency),
now via the unpacked `(None, None)`.

### 2.4 Owner-gated endpoints

New dependency in `optimizer_api/routers/benchmark.py`:

```
def require_run_owner(
    run_id: str,
    x_benchmark_owner_token: Annotated[str | None, Header()] = None,
) -> None
```

- Fetches `benchmark_state_manager.get_run(run_id)`.
- Run absent → `HTTPException(404)` (unchanged semantics).
- `verify_owner_token(state, x_benchmark_owner_token)` false → `HTTPException(403)`.
  A run with no stored hash is therefore always 403 (strict; cannot happen for post-deploy runs
  because state is in-memory and cleared on restart).

Apply as `dependencies=[Depends(require_run_owner)]` to:

- `GET /status` (run_id is a query param — FastAPI resolves it for the dependency)
- `POST /stop` (query param)
- `GET /results/{run_id}` (path param)

Response bodies of these three endpoints are unchanged apart from the auth gate.

## 3. Frontend changes (`src/`)

### 3.1 New helper `src/lib/benchmark-owner-cookie.ts`

- `OWNER_COOKIE_PREFIX = "benchmark_owner_"`
- `ownerCookieName(runId: string): string` → prefix + runId.
  run_id is validated `[A-Za-z0-9_-]` ≤ 64 chars, so the cookie name is always well-formed.
- `setOwnerCookie(runId: string, token: string)`: `Response.cookies.set(name, token, {
  httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production",
  path: "/api/benchmark", maxAge: 7200 })` — 7200 matches `BenchmarkStateManager.DEFAULT_TTL_SECONDS`.
- `getOwnerToken(request: NextRequest, runId: string): string | undefined` → `request.cookies.get(name)`.

### 3.2 Proxy route updates

- `src/app/api/benchmark/run/route.ts`:
  - Forward `X-Benchmark-Owner-Token` on the duplicate-precheck `/status` call when the cookie
    exists. Interpret the precheck response as "exists" when status is `200` or `403`
    (403 means a run with that id exists but is owned by someone else); `404` means available;
    anything else still returns 502 as today.
  - On successful backend `/run` response: `setOwnerCookie(runId, data.owner_token)`,
    then strip `owner_token` from the browser-facing response.
- `src/app/api/benchmark/run/status/route.ts` and `src/app/api/benchmark/status/route.ts`:
  read cookie by runId, add header to backend call.
- `src/app/api/benchmark/stop/route.ts`:
  - Align run_id transport to the backend contract (backend reads `run_id` as a query param):
    call `POST /api/v1/benchmark/stop?run_id=...` with the owner-token header (fixes the
    currently-broken web stop; in scope because this route is being rewired anyway).
- `src/app/api/benchmark/results/[runId]/route.ts`: read cookie by the path runId, add header.

## 4. Error handling / edge cases

- `owner_token` is returned exactly once (at creation). It is never retrievable afterwards,
  never stored in `parameters`/`results`, never echoed by status/results/stop responses.
- Expired cookie → no header → 403. Acceptable; the run is also evicted after the same TTL.
- Concurrent runs: one cookie per run_id.
- Strict enforcement: any run without a stored hash is 403 on the gated endpoints.
- No change to public surface (`/health`, `/strategies`, `/optimize`) or to 401/403 semantics
  for the shared API key.

## 5. Testing

### 5.1 Backend (pytest) — new `optimizer_api/tests/test_p3_owner_tokens.py`

- Unit: `create_run`/`import_run` return `(state, token)`; token non-empty URL-safe string;
  `state.owner_token_hash == sha256(token)`; raw token absent from `state.parameters`/`state.results`.
- Unit: `verify_owner_token` true for correct token, false for wrong token / `None` /
  missing hash.
- Unit: rejected create returns `(None, None)`.
- Router: `/run`, `/import`, `/cli/import` responses include a non-empty `owner_token`.
- Router: `/status`, `/stop`, `/results/{run_id}` → 404 when run absent (with a token);
  403 without header; 403 with wrong header; 200 with correct header.
- Router: gated endpoint on a run created before this change (no hash, simulated by directly
  constructing state) → 403.
- Update existing P2/D3 unit tests in `test_api_hardening_phase0.py` to unpack the tuple.

### 5.2 Frontend (vitest) — extend `src/services/benchmark-service.test.ts` or a new test file

- `setOwnerCookie` / `getOwnerToken` round-trip; cookie attributes (httpOnly, sameSite, path,
  maxAge).
- `/run` proxy: sets the cookie from backend `owner_token`; response to browser omits it;
  precheck treats 403 as "exists" → 409.
- `/stop` proxy: forwards `X-Benchmark-Owner-Token` and sends `run_id` as a query param.

### 5.3 Regression

- `optimizer_api/tests/test_api_hardening_phase0.py` (49 tests) + `test_p3_owner_tokens.py`.
- Full `optimizer_api/tests`, `uniride_core`, `academic_benchmark/tests/test_atsp_integration.py`.
- Frontend `npm test` (vitest).

## 6. Out of scope (later phases)

- P4 (academic endpoints leak internal DB details via 503).
- Per-user/multi-tenant API keys.
- Persistence of runs/owner tokens across process restarts.
