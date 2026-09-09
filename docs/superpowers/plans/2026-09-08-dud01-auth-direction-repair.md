# DUD-01 Authentication and Direction Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make administrator vehicle calculation authenticated and prevent saving a result under an unverified direction.

**Architecture:** Reuse adminFetch, normalize request direction at the BFF, require explicit matching direction in successful optimizer responses, and preserve calculation-time direction through serialization. Keep existing solver failure metadata unchanged.

**Tech Stack:** Next.js, TypeScript, Vitest, React Testing Library.

## Global Constraints

- Approved specification: `docs/superpowers/specs/2026-09-08-dud01-auth-direction-repair-design.md`.
- No merge, push, live-data mutation, solver changes, or daily-planner redesign.
- Preserve unrelated checkout changes. No dependency changes or secret copying.
- External staging files are proposals, not verified code. Never copy whole files over newer source.
- Production direction types remain pickup/dropoff; malformed data is represented explicitly only in negative tests.

## Workspace and baseline

- [ ] Verify current HEAD, status, and worktrees. Expected review base is `0345e64a322ebac0255b387b12198230275c7097`; stop and reconcile if affected code has changed.
- [ ] Create an isolated branch using the already ignored `.temp/worktrees` directory; do not modify the dirty root ignore file:

```powershell
git worktree add -b codex/dud01-auth-direction-20260908 .temp/worktrees/dud01-repair-20260908 WIP
```

- [ ] Read applicable instructions in the new worktree. Attempt CodeGraph refresh when indexed; record the existing lock failure if still blocked, without deleting the index or stopping another process.
- [ ] Verify dependency availability and run baseline `npm test -- --run src/app/api/calculate-vehicles/route.test.ts` and `npm run typecheck`. Record environment failures separately; do not install or copy environments without checking existing repository setup guidance.

## Task 1: BFF authentication and direction contract

**Modify:** `src/app/api/calculate-vehicles/route.ts`, `src/app/api/calculate-vehicles/route.test.ts`.

**Consumes:** `requireAdmin(request)`, `handleApiError(error)`, `optimizeRoutes(students, depot, options)`.
**Produces:** Successful BFF JSON with an explicit validated `direction`; invalid requests return 400; invalid successful upstream direction returns 502; 401/403 remain 401/403.

- [ ] Add failing cases for pickup/dropoff forwarding, omitted request becoming pickup, malformed explicit request, missing/null/invalid/mismatched successful backend direction, and 401/403 authorization errors. Preserve the existing deliberate solver failure metadata test. Reset mock implementations between cases and partially mock admin-auth so the real error handler is exercised.

Core regression assertion, using a valid student request and successful solver fixture:

```ts
optimizeRoutesMock.mockResolvedValue({ success: true, routes: [], total_vehicles: 0 });
const response = await POST(calculateRequest({ direction: "dropoff" }) as never);
expect(response.status).toBe(502);
expect(await response.json()).toEqual({ success: false, error: "Invalid optimization direction" });
```

- [ ] Run `npm test -- --run src/app/api/calculate-vehicles/route.test.ts`; record failures attributable to the missing contract.
- [ ] Add `direction?: unknown` to the request shape. Validate after authorization and body parsing:

```ts
if (body.direction !== undefined && body.direction !== "pickup" && body.direction !== "dropoff") {
    return NextResponse.json({ error: "Invalid direction" }, { status: 400 });
}
const requestedDirection = body.direction ?? "pickup";
```

- [ ] Pass `direction: requestedDirection` to optimizeRoutes. After the existing unsuccessful-result branch, before transforming successful output, enforce:

```ts
if ((result.direction !== "pickup" && result.direction !== "dropoff") || result.direction !== requestedDirection) {
    return NextResponse.json(
        { success: false, error: "Invalid optimization direction" },
        { status: 502 },
    );
}
```

- [ ] Include `direction: result.direction` in successful JSON. Import and use `handleApiError(error)` in catch instead of converting authentication errors to 500. Do not include malformed backend values in contract-error output or logs.
- [ ] Rerun the route tests and inspect the diff before Task 2.

## Task 2: Authenticated client and calculation-time persistence

**Modify:** `src/lib/admin-api.ts`, `src/lib/admin-api.test.ts`, `src/services/route-plans.ts`.
**Create:** `src/services/route-plans.test.ts` if absent; otherwise extend it.

**Consumes:** Existing private adminFetch and existing serializer arguments.
**Produces:** `adminApi.vehicles.calculate(input)` and a serializer that refuses missing/invalid/conflicting direction.

- [ ] Add client tests proving bearer transport, selected direction in JSON, unauthenticated rejection, and non-OK response rejection. Use existing auth mock setup; never real Supabase.
- [ ] Add serializer tests for valid matching directions, missing and invalid result direction, and disagreement. Represent the deliberately malformed test input at one explicit boundary:

```ts
type SaveInput = Parameters<typeof formatRoutePlanForSave>[0];
const malformed = { ...validResult, direction: "sideways" } as unknown as SaveInput;
expect(() => formatRoutePlanForSave(malformed, "2026-09-08", "pickup", "ga", "sweep")).toThrow();
```

- [ ] Run client and serializer tests to observe the missing behavior.
- [ ] Add calculate under the existing vehicles object, accepting students and the existing optional request configuration including `direction?: "pickup" | "dropoff"`. Reuse adminFetch rather than duplicating token acquisition:

```ts
const response = await adminFetch("/api/calculate-vehicles", {
    method: "POST",
    body: JSON.stringify(input),
});
if (!response.ok) throw new Error("Vehicle calculation failed");
return response.json();
```

- [ ] Rename the serializer direction parameter to requestedDirection and check the returned direction before constructing the save DTO:

```ts
const returned = optimizationResult.direction;
if (returned !== "pickup" && returned !== "dropoff") {
    throw new Error("Calculation result has no valid direction; save is blocked");
}
if (returned !== requestedDirection) {
    throw new Error("Calculation result direction does not match the requested direction");
}
```

Use `direction: returned` in the returned DTO; preserve the other mapping fields.
- [ ] Rerun both focused test files and typecheck.

## Task 3: Active page integration and full validation

**Modify:** `src/app/(app)/admin/vehicle-planning/page.tsx`.
**Create/extend:** `src/app/(app)/admin/vehicle-planning/page.test.tsx`.

**Consumes:** authenticated calculate helper and the real serializer.
**Produces:** Calculation uses selected direction; later selector changes cannot relabel the completed result.

- [ ] Add failing page tests using mocked network boundaries but the real serializer: both direction submissions, pickup calculation followed by dropoff selector change still saving pickup, and missing/invalid/conflicting result never reaching saveRoutePlan. Do not mock the serializer guard.
- [ ] Verify current selectors against live markup. The current calculate button uses the misleading `selectAll` message key; do not infer it calls the select-all handler or expand scope into translation repairs.
- [ ] Observe focused RED before changing page production code.
- [ ] Capture direction at calculation dispatch, use `adminApi.vehicles.calculate`, and associate the captured value only with the completed result:

```ts
const requestedDirection = direction;
const data = await adminApi.vehicles.calculate({
    students: activeStudents, maxTourTime, swCapacity, soCapacity,
    strategy, clusteringAlgorithm, direction: requestedDirection,
});
setCalculationDirection(requestedDirection);
setResult(data);
```

Initialize calculationDirection as a pickup/dropoff state. Clear the prior result when recalculating as the current code does. Pass calculationDirection, not the live selector, to formatRoutePlanForSave. Preserve existing error display and scheduling fields.
- [ ] Run the following in the isolated worktree:

```powershell
npm test -- --run src/app/api/calculate-vehicles/route.test.ts src/lib/admin-api.test.ts src/services/route-plans.test.ts "src/app/(app)/admin/vehicle-planning/page.test.tsx"
npm run typecheck
npm test -- --run
git diff --check
git status --short --branch
```

- [ ] Inspect route-to-client-to-page-to-serializer behavior jointly, not just individually mocked passing tests. Confirm unsuccessful solver metadata is retained and direction is never reconstructed from a successful response missing it.
- [ ] Report actual RED/GREEN evidence, exact changed files, test counts, and blockers. Leave changes reviewable without commit, merge, or push unless separately authorized. Do not call unexecuted tests passing.
