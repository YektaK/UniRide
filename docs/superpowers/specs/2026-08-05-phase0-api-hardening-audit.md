# Phase 0 — API Hardening Audit (2026-08-05)

Branch: `codex/phase0-api-hardening-20260805` (from `origin/WIP` @ `936cfb1`)
Scope: `optimizer_api` — 6 required behaviors. Evidence lines verified against working tree at time of writing.
No security code has been changed yet; this document is the audit + per-behavior test requirements.

## Behavior 1 — Unauthenticated callers cannot start benchmark jobs or read arbitrary files

### Findings

| Endpoint | Location | Auth | Verdict |
|---|---|---|---|
| `POST /api/v1/benchmark/run` | `optimizer_api/routers/benchmark.py:246-248` | none | **GAP** — starts background jobs (daemon thread, `benchmark.py:293-294`; matrix path `:309-418`) |
| `POST /api/v1/benchmark/download/{problem_name}` | `benchmark.py:504-522` | none | **GAP** — triggers external HTTP download (see B4) |
| `GET /api/v1/benchmark/status`, `/results/{run_id}`, `/stop` | `benchmark.py:229-244, 476-502` | none | GAP (read/stop state; `/stop` can kill anyone's run) |
| `POST /api/v1/benchmark/import` | `benchmark.py:463-474` | none | GAP (state injection) |
| `GET /param-spaces`, `/academic/*`, `/problems*` | `benchmark.py:106-227` | none | GAP (read-only data) |
| `POST /cli/import`, `GET /cli/files`, `/cli/preview` | `benchmark.py:616, 625, 652` | `Depends(require_internal_api_key)` | OK — existing pattern to replicate |

- Arbitrary-file read via `/problems/{name}` is NOT currently reachable: `get_problem_by_name` (`uniride_core/algorithms/tsplib_parser.py:307-311`) matches against parsed problem names from a directory scan of `TSPLIB_DATA_DIR` (`:276-304`); there is no caller-controlled path join in that path.
- `run_id` is caller-supplied (`schemas.py:399`) and is the only key for `/status`, `/stop`, `/results` — auth on those matters.

### Test requirements (RED)
1. `POST /benchmark/run` without `X-Internal-Api-Key` (env `INTERNAL_API_KEY` set) → **403**, and no state entry created in `benchmark_state_manager`.
2. `POST /benchmark/run` with correct key → 200/202-style "running" response (existing behavior preserved).
3. `POST /benchmark/download/{name}`, `GET /benchmark/problems`, `GET /benchmark/problems/{name}`, `GET /benchmark/status`, `POST /benchmark/stop`, `POST /benchmark/import`, `GET /benchmark/param-spaces` without key → **403**.
4. `GET /benchmark/cli/files`, `POST /benchmark/cli/preview` without key → **403** (already true; guard against regression).
5. `GET /health`, `GET /strategies`, `POST /optimize` remain **unauthenticated** (public API surface unchanged).

## Behavior 2 — Remove / reject caller-controlled file paths

### Findings
- `_resolve_cli_filename` (`benchmark.py:584-599`) already rejects absolute paths, `path.name != filename`, and verifies `candidate.relative_to(root)` under both configured result dirs — **OK, keep**.
- `download_tsplib_problem(name)` (`uniride_core/algorithms/tsplib_parser.py:365-387`) — **GAP**: `name` is only `lower().strip()`-ed (`:366`). It flows into `os.path.join(dest_dir, f"{name}.tsp")` (`:370`, `:386`) and `_extract_tgz_to_dest` copy target `os.path.join(dest_dir, f"{problem_name}.tsp")` (`:356`), so `../`-style names can escape `dest_dir` if the fetch succeeds. It also interpolates into fixed-host URLs (`:373`, `:380`).
- Tar-slip protection in `_extract_tgz_to_dest` (`:340-348`) — **OK, keep** (realpath + commonpath filter).
- `get_problem_by_name` / `load_problem_coordinates` (`:307-319`) — no caller-controlled path join — OK.

### Test requirements (RED)
1. `download_tsplib_problem("../../escape")` (or with mock fetch returning bytes) must **not** create/write any file outside `TSPLIB_DATA_DIR`; assert 403/400 at router layer for names containing `/`, `\`, `..`, or not matching `[A-Za-z0-9_-]`.
2. `_resolve_cli_filename("../evil.json")`, absolute paths, and `"a/b.json"` → 400 (existing behavior; regression guard).
3. Router `/benchmark/download/{problem_name}` with traversal payload → 400 (no network call attempted).

## Behavior 3 — Bounds: problems, algorithms, workers, repetitions, iterations

### Findings
- `BenchmarkRunRequest` (`schemas.py:397-440`): `run_id` bounded (`max_length=128`, `:399`); `algorithms`/`problems` have `min_length=1` but **no max_length / no list-size cap** (`:400-401`).
- `n_runs`: type-checked and `>= 1` (`:424-426`) but **no upper bound** → unbounded loop `range(1, n_runs + 1)` (`benchmark_runner.py:272`).
- `workers`: type-checked `>= 1` (`:428-430`) but **no upper bound**.
- `iterations` / algorithm params: no cap. Params flow from `algorithms[i].params` (arbitrary dict) via `_apply_algorithm_params` (`benchmark_runner.py:366`) into strategy configs (e.g., GA generations/population); no ceiling anywhere in the request path.
- `seed`/`skip_cached` type-checked (`:432-438`) — OK.
- Existing good examples: `limit` Query bounds `le=1000` (`benchmark.py:122`) / `le=5000` (`:181`); `future.result(timeout=120)` (`optimization.py:168`).

### Test requirements (RED)
1. `n_runs = 0`, `n_runs = "3"`, `n_runs = True` → 422 (existing); **new**: `n_runs = 1_000_000` → 422 (upper bound, e.g. `le=100`).
2. `workers = 10_000` → 422 (upper bound).
3. `algorithms` list of 500 entries / `problems` list of 1000 entries → 422 (list-size cap).
4. Algorithm `params` containing `max_iterations: 10**9` (and generation/population fields) → 422 (bounded at schema or router).
5. Unbounded iteration params must also be rejected in `POST /compare` and `POST /optimize` ga_config path (same validator reused).

## Behavior 4 — Explicit external-provider timeouts

### Findings
- **Exists**: `_DOWNLOAD_TIMEOUT = 30` (`uniride_core/algorithms/tsplib_parser.py:41`), passed to `urlopen(req, timeout=timeout)` in `_fetch_url` (`:322-329`). Two sequential URLs ⇒ worst case 60 s per download request.
- No other external HTTP in `optimizer_api` (grep for `httpx|requests|urlopen` shows only test scripts with their own 30 s timeouts; `requests` not even installed in verify env).
- `future.result(timeout=120)` covers in-process algorithm execution (`optimization.py:168`).

### Test requirements (RED)
1. Unit: `_fetch_url` with a hanging mock server returns within ≤ 30 s (timeout parameter is honored); `download_tsplib_problem` returns `None` (no hang) when both URLs time out.
2. Router `POST /benchmark/download/{name}` against a blackhole URL (mocked) completes < 5 s total (i.e., 403/400 before any fetch, per B1/B2).

## Behavior 5 — No shared-mutable strategy config under concurrency

### Findings
- `STRATEGY_REGISTRY` holds **module-level singletons** (`strategies/__init__.py:79-98`), shared by: `/optimize` (`optimization.py:32`), `/compare` via `ThreadPoolExecutor(max_workers=len(algorithms))` (`optimization.py:161-164`), and benchmark daemon threads (`benchmark.py:288`).
- Config mutation: `self.config = {...}` only in constructors (`ga_strategy.py:53`, `pso:53`, `gwo:63`, `hho:65`, `two_opt:58`, `ga_split:77`, `pso_split:97`, `gwo_split:97`, `hho_split:98`). Optimize paths write only to a **local** `effective_config = dict(self.config)` (`ga_strategy.py:111,120`, `pso_strategy.py:112`). No `self.config[...] =` in any optimize path (grep-verified) → **config is not mutated per-request; OK**.
- Residual: per-run instance state on singletons (e.g., `self.seed` fixed at construction, `ga_strategy.py:54`) is shared; currently deterministic, not a race. Guard with a test.

### Test requirements (RED)
1. Concurrent (threaded) calls of the same singleton strategy with different `ga_config` values return results whose config values do not leak across responses (no cross-talk).
2. After any number of requests, `strategy.config is registry_config` and its contents are unchanged (no mutation).
3. Two concurrent `/compare` and one `/benchmark/run` (mocked runner) on the same algorithms complete without exception/state corruption.

## Behavior 6 — Preserve existing 401/403 semantics

### Findings
- `require_internal_api_key` (`auth.py:8-15`): returns 403 (`:15`) on missing/mismatched key; **fails open** when `INTERNAL_API_KEY` is unset (`:12-13`) — intentional dev mode, must be preserved.
- 401 is used nowhere in `optimizer_api` (grep: only `auth.py:15` 403). Keep 403-only semantics; do not introduce 401.

### Test requirements (RED)
1. Env set + correct key → pass (all newly-protected endpoints).
2. Env set + wrong key → 403; env set + no header → 403.
3. Env **unset** → endpoints still accessible (fail-open preserved, incl. newly-protected ones).
4. Response body shape unchanged: `{"detail": "Forbidden"}`.

## Notes / exclusions
- Excluded per task: solver math, benchmarks, frontend, DB, dependency changes, unrelated dirty files.
- Implementation order after audit confirmation: write failing tests per behavior (RED), then minimal hardening (auth deps on benchmark router endpoints, name validation in tsplib download, bounds in `BenchmarkRunRequest` + param caps), then run full suite green in verify env (`C:\tmp\UniRide-occurrence-verify-20260805\Scripts\python.exe`).
