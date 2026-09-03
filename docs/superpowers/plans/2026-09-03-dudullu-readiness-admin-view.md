# Dudullu Readiness Admin View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give authenticated administrators a PII-safe `/admin/readiness` page that calls the existing Dudullu aggregate readiness endpoint without manual bearer-token handling.

**Architecture:** Keep the existing Next.js BFF and readiness analyzer unchanged. Add one runtime-validated response boundary beside the readiness service, expose it through the existing authenticated `adminApi`, clear the token cache on authentication transitions, and render a small read-only page linked from the admin sidebar.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Zod, next-intl, Vitest, Testing Library, existing shadcn/ui components.

## Global Constraints

- No new endpoint, dependency, database table, Supabase mutation, optimizer call, or backend behavior.
- Never expose student identifiers, names, addresses, raw schedules, access tokens, raw matrices, or backend response bodies.
- Parse response JSON as `unknown`; strip unexpected fields and reject missing or invalid required fields.
- Bound the readiness client request with a fixed 15,000 ms timeout.
- Allow only reason codes emitted by `src/services/dudullu-readiness.ts`.
- HTTP 200 with `ready=false` is BLOCKED-DATA, not a request error.
- Clear the cached admin token on explicit logout and every observed authentication-state change.
- Keep `/` routing, production solvers, academic code, and daily-planning domain unchanged.
- Use RED-to-GREEN TDD and one reviewable commit per task.

---

## File map

- Create `src/services/dudullu-readiness-response.ts`: runtime schema, reason-code allowlist, parser.
- Create `src/services/dudullu-readiness-response.test.ts`: schema and PII-stripping tests.
- Modify `src/lib/admin-api.ts` and `src/lib/admin-api.test.ts`: authenticated readiness method and stable errors.
- Modify `src/contexts/auth-context.tsx`; create `src/contexts/auth-context.test.tsx`: cache invalidation.
- Create `src/app/(app)/admin/readiness/page.tsx` and `page.test.tsx`: read-only UI.
- Modify `src/components/layout/app-sidebar.tsx` and `src/i18n/sidebar-messages.test.ts`: admin-only link.
- Create `src/i18n/dudullu-readiness-messages.test.ts`; modify `messages/en.json` and `messages/tr.json`: complete bilingual copy.

### Task 1: Runtime-validated authenticated client

**Files:**
- Create: `src/services/dudullu-readiness-response.ts`
- Create: `src/services/dudullu-readiness-response.test.ts`
- Modify: `src/lib/admin-api.ts:9-10,122-140,144-430`
- Modify: `src/lib/admin-api.test.ts:1-49`

**Interfaces:**
- Produces: `DUDULLU_REASON_CODES`
- Produces: `parseDudulluReadinessReport(input: unknown): DudulluReadinessReport`
- Produces: `AdminApiAuthenticationError` for a missing session at the shared authenticated boundary
- Produces: `DudulluReadinessRequestError.kind: "authorization" | "configuration"`
- Produces: `adminApi.readiness.getDudullu(): Promise<DudulluReadinessReport>`

- [ ] **Step 1: Write the failing parser tests**

Create a complete valid fixture using every field of `DudulluReadinessReport`. Assert that it parses, nested extras such as `homeAddresses` and top-level `studentNames` are stripped, and each of these inputs throws `Invalid Dudullu readiness response`: unknown reason code, negative count, non-integer count, unknown matrix source, missing fleet, missing nested field.

```typescript
const parsed = parseDudulluReadinessReport({
  ...validReport,
  studentNames: ["must-not-cross-boundary"],
  students: { ...validReport.students, homeAddresses: ["secret"] },
});
expect(parsed).toEqual(validReport);
expect(parsed).not.toHaveProperty("studentNames");
expect(parsed.students).not.toHaveProperty("homeAddresses");
```

- [ ] **Step 2: Run the parser test and verify RED**

```powershell
npm test -- --run src/services/dudullu-readiness-response.test.ts
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the complete runtime schema**

```typescript
import { z } from "zod";
import type { DudulluReadinessReport } from "./dudullu-readiness";

export const DUDULLU_REASON_CODES = [
  "no_dudullu_students",
  "target_profile_incomplete",
  "schedule_classification_incomplete",
  "schedule_data_invalid",
  "no_configured_driver",
  "no_usable_active_vehicle",
  "matrix_unavailable",
  "matrix_stale",
  "matrix_incomplete",
  "matrix_location_mismatch",
] as const;

const count = z.number().int().nonnegative();

export const dudulluReadinessReportSchema = z.object({
  ready: z.boolean(),
  reasonCodes: z.array(z.enum(DUDULLU_REASON_CODES)),
  students: z.object({
    allAccounts: count,
    dudulluTarget: count,
    nonDudulluScheduled: count,
    unclassifiedSchedule: count,
    completeTargetProfiles: count,
    targetMissingLocation: count,
    targetMissingDisabilityType: count,
    scheduleLinkMismatch: count,
    distinctTargetLocations: count,
  }),
  schedules: z.object({
    total: count,
    empty: count,
    malformed: count,
    orphanedRows: count,
    duplicateRowsForStudent: count,
  }),
  fleet: z.object({
    configuredDrivers: count,
    vehicles: count,
    activeVehicles: count,
    usableActiveVehicles: count,
  }),
  matrix: z.object({
    source: z.enum(["supabase", "empty", "coordinates"]),
    loaded: z.boolean(),
    stale: z.boolean(),
    hasError: z.boolean(),
    matrixLocationCount: count,
    complete: z.boolean(),
    ready: z.boolean(),
    requiredLocationCount: count,
    expectedRequiredDirectedArcCount: count,
    validRequiredDirectedArcCount: count,
    missingRequiredLocationCount: count,
    invalidOrMissingRequiredDirectedArcCount: count,
    depotPresent: z.boolean(),
  }),
  historicalExpectation: z.object({
    studentCount: count,
    matrixNodeCount: count,
    matchesStudentCount: z.boolean(),
    matchesMatrixNodeCount: z.boolean(),
  }),
}) satisfies z.ZodType<DudulluReadinessReport>;

export function parseDudulluReadinessReport(input: unknown): DudulluReadinessReport {
  const parsed = dudulluReadinessReportSchema.safeParse(input);
  if (!parsed.success) throw new Error("Invalid Dudullu readiness response");
  return parsed.data;
}
```

Use ordinary `z.object()`; its default stripping behavior is required. Do not use `.passthrough()`.

- [ ] **Step 4: Run the parser test and verify GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Write failing client tests**

Extend `src/lib/admin-api.test.ts` using its existing Supabase and fetch mocks. Test:

```typescript
const report = await adminApi.readiness.getDudullu();
expect(fetchMock).toHaveBeenCalledWith(
  "/api/admin/dudullu-readiness",
  expect.objectContaining({
    method: "GET",
    cache: "no-store",
    headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
  })
);
expect(report).toEqual(validReport);
```

Also assert:

- a missing session, 401, and 403 reject with `{kind:"authorization", message:"Dudullu readiness request failed"}`;
- fetch rejection, timeout abort, 500, and 503 reject with `kind:"configuration"`;
- malformed JSON and schema failure reject with `kind:"configuration"`;
- no failing response body is parsed or included in the thrown error.

- [ ] **Step 6: Run the client test and verify RED**

```powershell
npm test -- --run src/lib/admin-api.test.ts
```

Expected: FAIL because `adminApi.readiness` does not exist.

- [ ] **Step 7: Implement the minimal client boundary**

Add to `src/lib/admin-api.ts`:

```typescript
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";
import { parseDudulluReadinessReport } from "@/services/dudullu-readiness-response";

export class AdminApiAuthenticationError extends Error {
  constructor() {
    super("Not authenticated");
    this.name = "AdminApiAuthenticationError";
  }
}

export class DudulluReadinessRequestError extends Error {
  constructor(public readonly kind: "authorization" | "configuration") {
    super("Dudullu readiness request failed");
    this.name = "DudulluReadinessRequestError";
  }
}

// Replace the existing generic Error in adminFetch:
if (!token) throw new AdminApiAuthenticationError();

const DUDULLU_READINESS_TIMEOUT_MS = 15_000;
async function getDudulluReadiness(): Promise<DudulluReadinessReport> {
  let response: Response;
  try {
    response = await adminFetch("/api/admin/dudullu-readiness", {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(DUDULLU_READINESS_TIMEOUT_MS),
    });
  } catch (error) {
    throw new DudulluReadinessRequestError(
      error instanceof AdminApiAuthenticationError
        ? "authorization"
        : "configuration"
    );
  }
  if (response.status === 401 || response.status === 403) {
    throw new DudulluReadinessRequestError("authorization");
  }
  if (!response.ok) throw new DudulluReadinessRequestError("configuration");

  try {
    return parseDudulluReadinessReport(await response.json());
  } catch {
    throw new DudulluReadinessRequestError("configuration");
  }
}

// Inside adminApi:
readiness: { getDudullu: getDudulluReadiness },
```

Do not parse or log an error response body.

- [ ] **Step 8: Verify and commit Task 1**

```powershell
npm test -- --run src/services/dudullu-readiness-response.test.ts src/lib/admin-api.test.ts
git diff --check
git add src/services/dudullu-readiness-response.ts src/services/dudullu-readiness-response.test.ts src/lib/admin-api.ts src/lib/admin-api.test.ts
git commit -m "feat(runtime): validate Dudullu readiness client"
```

Expected: tests pass and diff check exits 0.

### Task 2: Authentication cache invalidation

**Files:**
- Modify: `src/contexts/auth-context.tsx:7,23-31,50-59`
- Create: `src/contexts/auth-context.test.tsx`

**Interfaces:**
- Consumes: existing `clearAuthTokenCache(): void`
- Preserves: existing `AuthContextType`

- [ ] **Step 1: Write failing behavioral tests**

Create a jsdom test. Hoist mocks for `signIn`, `signOutUser`, `onAuthStateChange`, and `clearAuthTokenCache`. Capture the callback passed to `onAuthStateChange`. Render `AuthProvider` with a context consumer exposing a logout button.

```tsx
it("clears the cache on every observed auth-state change", () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  const callback = mocks.onChange.mock.calls[0][0];
  act(() => callback(null));
  expect(mocks.clearToken).toHaveBeenCalledTimes(1);
});

it("clears the cache after explicit logout", async () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  fireEvent.click(screen.getByRole("button", { name: "logout" }));
  await waitFor(() => expect(mocks.signOut).toHaveBeenCalledTimes(1));
  expect(mocks.clearToken).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run the auth test and verify RED**

```powershell
npm test -- --run src/contexts/auth-context.test.tsx
```

Expected: FAIL because the provider never calls `clearAuthTokenCache()`.

- [ ] **Step 3: Add fail-closed invalidation**

```tsx
import { clearAuthTokenCache } from "@/lib/admin-api";

// First lines of the existing auth-state callback:
clearAuthTokenCache();
setUser(user);
setIsLoading(false);

// After successful signOutUser():
await signOutUser();
clearAuthTokenCache();
setUser(null);
```

Do not alter login, routing, user mapping, or context shape.

- [ ] **Step 4: Verify and commit Task 2**

```powershell
npm test -- --run src/contexts/auth-context.test.tsx src/lib/admin-api.test.ts
git diff --check
git add src/contexts/auth-context.tsx src/contexts/auth-context.test.tsx
git commit -m "fix(auth): invalidate cached admin token"
```

### Task 3: Read-only administrator page

**Files:**
- Create: `src/app/(app)/admin/readiness/page.tsx`
- Create: `src/app/(app)/admin/readiness/page.test.tsx`

**Interfaces:**
- Consumes: `adminApi.readiness.getDudullu()`
- Consumes: `DudulluReadinessRequestError.kind`
- Produces: `/admin/readiness`

- [ ] **Step 1: Write failing page tests**

Mock `next-intl` to return keys and mock `adminApi.readiness.getDudullu`. Use a complete aggregate fixture without row-level data. Assert:

```tsx
expect(await screen.findByText("status.passTitle")).toBeTruthy();
expect(await screen.findByText("status.blockedDataTitle")).toBeTruthy();
expect(screen.getByText("reasons.matrix_incomplete")).toBeTruthy();
expect(await screen.findByText("errors.authorization")).toBeTruthy();
expect(await screen.findByText("errors.configuration")).toBeTruthy();
```

For a never-resolving request, assert the refresh button is disabled and clicking it does not create a second call.

- [ ] **Step 2: Run the page test and verify RED**

```powershell
npm test -- --run "src/app/(app)/admin/readiness/page.test.tsx"
```

Expected: FAIL because the page does not exist.

- [ ] **Step 3: Implement the page**

Use this explicit state:

```tsx
type ViewState =
  | { kind: "loading" }
  | { kind: "report"; report: DudulluReadinessReport }
  | { kind: "error"; error: "authorization" | "configuration" };
```

The component must:

1. call `getDudullu()` on mount;
2. guard duplicate calls with `useRef<boolean>`;
3. disable “Yenile” while loading;
4. render PASS when `report.ready`, otherwise BLOCKED-DATA;
5. render returned reasons as `t(`reasons.${code}`)`;
6. map any unknown failure to configuration;
7. use `aria-live="polite"`;
8. render fixed rows, never enumerate arbitrary response properties.

Render these fixed aggregates:

- students: allAccounts, dudulluTarget, completeTargetProfiles, unclassifiedSchedule;
- schedules: total, empty, malformed;
- fleet: configuredDrivers, activeVehicles, usableActiveVehicles;
- matrix: source, matrixLocationCount, requiredLocationCount, validRequiredDirectedArcCount, expectedRequiredDirectedArcCount;
- historical: expected students/nodes and both match booleans.

Use existing `Card` and `Button`. Do not add charts, tabs, polling, exports, remediation controls, or shared presentation abstractions.

- [ ] **Step 4: Verify and commit Task 3**

```powershell
npm test -- --run "src/app/(app)/admin/readiness/page.test.tsx" src/services/dudullu-readiness-response.test.ts src/lib/admin-api.test.ts
git diff --check
git add "src/app/(app)/admin/readiness/page.tsx" "src/app/(app)/admin/readiness/page.test.tsx"
git commit -m "feat(admin): show Dudullu readiness"
```

### Task 4: Admin navigation, bilingual copy, and release gate

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx:14-67`
- Modify: `src/i18n/sidebar-messages.test.ts:67-71`
- Create: `src/i18n/dudullu-readiness-messages.test.ts`
- Modify: `messages/en.json`
- Modify: `messages/tr.json`

**Interfaces:**
- Produces: `common.sidebar.dudulluReadiness`
- Produces: complete `page.admin.readiness` in English and Turkish

- [ ] **Step 1: Write failing i18n tests**

Update the sidebar contract:

```typescript
expect(sidebarKeys).toHaveLength(23);
expect(sidebarKeys).toContain("dudulluReadiness");
```

Create a recursive catalog-key test. For both locales, require identical, non-empty values for this exact key set:

```typescript
const expectedKeys = [
  "boolean.no", "boolean.yes", "description",
  "errors.authorization", "errors.configuration",
  "labels.activeVehicles", "labels.allAccounts", "labels.completeTargetProfiles",
  "labels.configuredDrivers", "labels.dudulluTarget", "labels.expectedArcCount",
  "labels.expectedMatrixNodes", "labels.expectedStudents", "labels.matrixLocationCount",
  "labels.matrixSource", "labels.matchesMatrix", "labels.matchesStudents",
  "labels.requiredLocationCount", "labels.scheduleEmpty", "labels.scheduleMalformed",
  "labels.scheduleTotal", "labels.unclassifiedSchedule",
  "labels.usableActiveVehicles", "labels.validArcCount", "loading",
  "matrixSources.coordinates", "matrixSources.empty", "matrixSources.supabase",
  "reasons.matrix_incomplete", "reasons.matrix_location_mismatch",
  "reasons.matrix_stale", "reasons.matrix_unavailable",
  "reasons.no_configured_driver", "reasons.no_dudullu_students",
  "reasons.no_usable_active_vehicle", "reasons.schedule_classification_incomplete",
  "reasons.schedule_data_invalid", "reasons.target_profile_incomplete",
  "refresh", "sections.fleet", "sections.historical", "sections.matrix",
  "sections.schedules", "sections.students", "status.blockedConfigTitle",
  "status.blockedDataTitle", "status.passTitle", "title",
].sort();
```

- [ ] **Step 2: Run i18n tests and verify RED**

```powershell
npm test -- --run src/i18n/sidebar-messages.test.ts src/i18n/dudullu-readiness-messages.test.ts
```

Expected: FAIL because the link and catalogs do not exist.

- [ ] **Step 3: Add the admin-only link**

Import `Activity` from `lucide-react` and add only to `adminMenuItems`:

```tsx
{ href: "/admin/readiness", labelKey: "dudulluReadiness", icon: Activity },
```

- [ ] **Step 4: Add complete English and Turkish copy**

Under existing `common.sidebar`, add `dudulluReadiness`. Under `page.admin`, add `readiness` with exactly the Step 1 keys. Keep technical status labels PASS, BLOCKED-DATA, and BLOCKED-CONFIG; localize every description, action, metric, matrix source, boolean, error, and reason.

Required Turkish status/error copy:

```json
{
  "status": {
    "passTitle": "PASS — Planlamaya hazır",
    "blockedDataTitle": "BLOCKED-DATA — Veri düzeltmesi gerekli",
    "blockedConfigTitle": "BLOCKED-CONFIG — Yapılandırma veya servis sorunu"
  },
  "errors": {
    "authorization": "Yönetici oturumu doğrulanamadı. Yeniden giriş yapın.",
    "configuration": "Hazırlık raporu alınamadı. Yerel servisleri ve yapılandırmayı kontrol edip yeniden deneyin."
  }
}
```

- [ ] **Step 5: Run the focused release gate**

```powershell
npm test -- --run src/services/dudullu-readiness-response.test.ts src/lib/admin-api.test.ts src/contexts/auth-context.test.tsx "src/app/(app)/admin/readiness/page.test.tsx" src/i18n/sidebar-messages.test.ts src/i18n/dudullu-readiness-messages.test.ts src/app/api/admin/dudullu-readiness/route.test.ts src/services/dudullu-readiness.test.ts
npm run typecheck
npm run lint -- --quiet
git diff --check
```

Expected: all focused tests pass; typecheck, lint, and diff check exit 0.

- [ ] **Step 6: Run the full frontend gate**

```powershell
npm test -- --run
```

Expected: zero failures. Record current counts; never reuse historical counts.

- [ ] **Step 7: Commit Task 4**

```powershell
git add src/components/layout/app-sidebar.tsx src/i18n/sidebar-messages.test.ts src/i18n/dudullu-readiness-messages.test.ts messages/en.json messages/tr.json
git commit -m "feat(admin): link Dudullu readiness"
git status --short --branch
```

Expected: clean feature worktree.

- [ ] **Step 8: Review and integration gate**

Use `requesting-code-review`. Verify no response-body relay, no PII fields, complete reason-code allowlist/localization, cache invalidation, admin-only link, and unchanged root/backend contracts. Fix only verified findings through new RED-to-GREEN commits, then repeat Steps 5 and 6.

After explicit integration authorization, fast-forward merge into WIP while preserving its user-owned `.gitignore` modification. Start the local stack, sign in as administrator, open `http://127.0.0.1:9002/admin/readiness`, and record only classification, aggregate counts, reason codes, and startup/UI failures.

A BLOCKED-DATA result feeds a separate data-remediation plan. A PASS result opens Package 1 of the approved Dudullu daily-operations plan. Push WIP only with explicit authorization.
