# Dudullu Readiness Admin View Design

**Date:** 2026-09-03
**Status:** Approved for planning
**Scope:** A minimal authenticated administrator view for the existing Package 0 readiness contract

## 1. Purpose

Package 0 already exposes `GET /api/admin/dudullu-readiness`, but no active administrator page calls it. The live readiness gate therefore cannot be run through the product without manually handling a bearer token. Add the smallest durable operator surface that calls the existing protected endpoint through the existing authenticated client and displays only its redacted aggregate response.

This view is diagnostic. It does not create schedules, repair matrices, mutate Supabase data, launch optimization, or replace the daily-operations UI planned in Package 4.

## 2. Selected approach

Add a dedicated `/admin/readiness` page and one administrator navigation entry named “Dudullu Hazırlık”. The page loads the report on entry and provides a manual refresh action.

Rejected alternatives:

- Embedding the report in Settings mixes operational readiness with configuration ownership.
- A developer-console command is not an auditable product workflow and requires unsafe manual token handling.
- Building a broad monitoring dashboard exceeds the immediate Package 0 gate.

## 3. Architecture and data flow

1. The page calls a new `adminApi.readiness.getDudullu()` method.
2. That method reuses the existing private `adminFetch()` helper, so authentication, refresh, and the bearer header remain centralized.
3. The client parses response JSON as `unknown` through a runtime schema for the complete aggregate DTO. The schema accepts only the documented enum values and reason codes, requires all documented fields, validates counts as nonnegative integers, and strips unexpected fields before presentation.
4. Logout and authentication-state changes clear the existing admin token cache before another request can reuse it.
5. The Next.js route continues to enforce `requireAdmin()` before querying Supabase or FastAPI.
6. The page renders the validated aggregate readiness DTO. It must not request or render student identifiers, names, addresses, raw schedules, tokens, or matrix contents.
7. `cache-control: private, no-store` remains owned by the existing API route. The client also treats every refresh as a fresh request.

No new endpoint, dependency, database table, or backend behavior is introduced.

## 4. Presentation and states

The page presents one status banner and compact aggregate sections for students, schedules, vehicles, matrix coverage, and historical expectations already present in the DTO.

The operator-facing classification is:

- **PASS:** `ready === true`.
- **BLOCKED-DATA:** HTTP 200 with `ready === false`; show the returned reason codes and aggregates.
- **BLOCKED-CONFIG:** authentication, dependency, network, timeout, or malformed-response failure; show a redacted retryable error without internal exception text.

Loading and refresh states disable duplicate requests. The page has a single “Yenile” action. Raw JSON, row-level drill-down, automatic polling, export, and remediation controls are deliberately excluded.

## 5. Navigation and routing boundary

Add “Dudullu Hazırlık” to the administrator sidebar and add a complete `page.admin.readiness` namespace to both Turkish and English catalogs. Status names, aggregate labels, known reason codes, authorization/configuration errors, and the refresh action must all be localized. The existing `/` route that opens the Benchmark Suite is acknowledged as separate product-entry routing debt and is not changed in this work package.

## 6. Error and security behavior

- A missing session follows the existing authenticated application behavior; no token is logged or displayed.
- Logout or account switching clears cached authentication state before subsequent admin calls.
- HTTP 401/403 is mapped to a stable authorization error without displaying the response body.
- HTTP 503, transport, timeout, malformed JSON, or runtime-schema failure is mapped to a stable BLOCKED-CONFIG error without displaying internal exception text or the response body.
- HTTP 200 with `ready=false` remains a successful diagnostic response and is rendered as BLOCKED-DATA, not as a request error.
- Unexpected fields, including hostile PII-shaped additions, are stripped by the runtime presentation boundary; missing or invalid required fields fail closed to the redacted error state.
- Console output must not contain access tokens, Supabase secrets, student rows, or raw backend error bodies.

## 7. Testing

Use RED-to-GREEN tests for:

1. the authenticated client method and endpoint path;
2. token-cache invalidation on logout and authentication-state changes;
3. runtime validation for the complete aggregate DTO, including nonnegative integer counts, enum fields, the fixed reason-code allowlist, missing/wrong fields, and stripping hostile extra PII fields;
4. stable redacted mapping for 401, 403, 503, transport, timeout, malformed JSON, and runtime-schema failures;
5. PASS, BLOCKED-DATA, and BLOCKED-CONFIG rendering;
6. localized reason-code and aggregate rendering without row-level fields;
7. loading/refresh behavior and duplicate-request prevention;
8. administrator sidebar link, the sidebar test's expected key set/count, and complete `page.admin.readiness` Turkish/English translation-key parity.

Run focused Vitest tests, the full frontend suite, TypeScript typecheck, ESLint with zero errors, and `git diff --check`. After merge, run the page against the local stack with an authenticated administrator and record the aggregate gate result separately from automated test evidence.

## 8. Acceptance criteria

- An authenticated administrator can open `/admin/readiness` and obtain the live aggregate Dudullu readiness report without copying a token.
- The view truthfully distinguishes PASS, BLOCKED-DATA, and BLOCKED-CONFIG.
- Every response crosses a runtime-validated, allowlisted aggregate DTO boundary before rendering.
- Logout or account switching cannot reuse the cached bearer token.
- No PII, secret, raw schedule, or raw matrix content is exposed.
- Existing Package 0 route tests and frontend regression gates remain green.
- No production solver, academic benchmark, daily-planning domain, database, or root-route behavior changes.
