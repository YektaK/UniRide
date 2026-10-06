import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { requireAdminMock, getSupabaseAdminMock, optimizerFetchMock } = vi.hoisted(() => ({
  requireAdminMock: vi.fn(),
  getSupabaseAdminMock: vi.fn(),
  optimizerFetchMock: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-auth")>("@/lib/admin-auth");
  return { ...actual, requireAdmin: requireAdminMock };
});

vi.mock("@/lib/supabase-admin", () => ({ getSupabaseAdmin: getSupabaseAdminMock }));
vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: optimizerFetchMock }));

import { AppError } from "@/lib/admin-auth";

type QueryResult = { data: unknown; error: { message: string; code?: string } | null };
type QueryTrace = {
  table: string;
  columns?: string;
  filters: Array<{ method: string; args: unknown[] }>;
};

function adminClient(
  rows: Record<string, unknown[]> = {},
  failedTable?: string,
  failureCode?: string,
) {
  const queries: QueryTrace[] = [];
  // Every mutating entry point records its call so tests can prove the preview is read-only.
  const writes: string[] = [];
  const from = vi.fn((table: string) => {
    const trace: QueryTrace = { table, filters: [] };
    queries.push(trace);
    const result: QueryResult = {
      data: rows[table] ?? [],
      error: table === failedTable
        ? { message: "SUPABASE-SECRET-DIAGNOSTIC", ...(failureCode ? { code: failureCode } : {}) }
        : null,
    };
    const query = {} as {
      select(columns: string): typeof query;
      eq(column: string, value: unknown): typeof query;
      in(column: string, values: readonly unknown[]): typeof query;
      or(filters: string): typeof query;
      then<TResult1 = QueryResult, TResult2 = never>(
        onfulfilled?: ((value: QueryResult) => TResult1 | PromiseLike<TResult1>) | null,
        onrejected?: ((reason: unknown) => TResult2 | PromiseLike<TResult2>) | null,
      ): PromiseLike<TResult1 | TResult2>;
    };
    for (const method of ["insert", "update", "upsert", "delete"]) {
      Object.assign(query, {
        [method]: vi.fn(() => {
          writes.push(`${table}.${method}`);
          return query;
        }),
      });
    }
    Object.assign(query, {
      select: vi.fn((columns: string) => {
        trace.columns = columns;
        return query;
      }),
      eq: vi.fn((column: string, value: unknown) => {
        trace.filters.push({ method: "eq", args: [column, value] });
        return query;
      }),
      in: vi.fn((column: string, values: readonly unknown[]) => {
        trace.filters.push({ method: "in", args: [column, [...values]] });
        return query;
      }),
      or: vi.fn((filters: string) => {
        trace.filters.push({ method: "or", args: [filters] });
        return query;
      }),
      then: <TResult1 = QueryResult, TResult2 = never>(
        onfulfilled?: ((value: QueryResult) => TResult1 | PromiseLike<TResult1>) | null,
        onrejected?: ((reason: unknown) => TResult2 | PromiseLike<TResult2>) | null,
      ): PromiseLike<TResult1 | TResult2> => Promise.resolve(result).then(onfulfilled, onrejected),
    });
    return query;
  });
  const rpc = vi.fn((name: string) => {
    writes.push(`rpc.${name}`);
    return Promise.resolve({ data: null, error: null });
  });
  return { from, rpc, queries, writes };
}

function setAdmin(rows: Record<string, unknown[]> = {}, failedTable?: string, failureCode?: string) {
  const client = adminClient(rows, failedTable, failureCode);
  getSupabaseAdminMock.mockReturnValue(client);
  requireAdminMock.mockResolvedValue({ id: "admin-1", role: "admin" });
  return client;
}

function post(body: string | object) {
  return new Request("http://localhost/api/admin/dudullu-preview", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

function legacyRows() {
  return {
    users: [{
      id: "student-1",
      role: "student",
      location_code: "Sw1",
      disability_type: "Sw",
      weekly_schedule_id: "schedule-1",
    }],
    weekly_schedules: [{
      id: "schedule-1",
      user_id: "student-1",
      entries: [{
        id: "class-1",
        dayOfWeek: "wednesday",
        startTime: "09:00",
        endTime: "10:00",
        location: "Dudullu",
      }],
    }],
    ride_requests: [{
      id: "request-1",
      user_id: "student-1",
      requested_pickup_time: "2026-09-30T06:00:00.000Z",
      requested_dropoff_time: "2026-09-30T14:00:00.000Z",
      status: "confirmed",
    }],
  };
}

const onTimePickup = {
  user_id: "student-1",
  service_date: "2026-09-30",
  direction: "pickup",
  decision: "confirmed",
  decided_at: "2026-09-29T18:00:00.000Z",
  flexibility_minutes: 0,
};

const matrix = {
  id: `time_matrix:sha256:${"a".repeat(64)}`,
  version: "a".repeat(64),
  sha256: "a".repeat(64),
  source: "supabase",
  arcs: [
    { origin_code: "D.Kampus", destination_code: "Sw1", duration_minutes: 5 },
    { origin_code: "Sw1", destination_code: "D.Kampus", duration_minutes: 6 },
  ],
};

function admittedRows(decisions: object[] = [onTimePickup]) {
  return {
    ...legacyRows(),
    ride_requests: [],
    student_leg_decisions: decisions,
    vehicles: [{ id: "vehicle-1", wheelchair_capacity: 2, seating_capacity: 2, cooldown_minutes: 10, status: "active" }],
  };
}

function solverResult(occurrenceId: string) {
  const steps = [{ location1: "D.Kampus", location2: "Sw1", duration: 5, distance: 0 }, { location1: "Sw1", location2: "D.Kampus", duration: 6, distance: 0 }];
  return {
    success: true,
    routes: [{ vehicle_id: "V1", route_details: steps, total_duration_minutes: 11, sw_count: 1, so_count: 0, student_ids: [occurrenceId] }],
    total_duration_minutes: 11,
    feasibility_certificate: { is_feasible: true },
  };
}

function mockTransport(results: unknown[]) {
  optimizerFetchMock.mockImplementation(async (path: string) => {
    if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrix);
    if (path === "/api/v1/optimize") return Response.json(results.shift());
    throw new Error("unexpected optimizer path");
  });
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.resetAllMocks();
  vi.resetModules();
  vi.restoreAllMocks();
});

describe("POST /api/admin/dudullu-preview", () => {
  it("skips fleet, matrix, and solver for zero admitted demand", async () => {
    const client = setAdmin(admittedRows([]));
    const { POST } = await import("./route");
    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();
    expect(body).toMatchObject({ status: "blocked_data", publishable: false, jobs: [] });
    expect(body.vehicleSummary).toBeNull();
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(client.queries.map((query) => query.table)).not.toContain("vehicles");
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("fails closed before matrix and solver calls when the active fleet is empty", async () => {
    const rows = admittedRows();
    const client = setAdmin({ ...rows, vehicles: [] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(optimizerFetchMock).not.toHaveBeenCalled();
    expect(body).toMatchObject({ status: "blocked_data", publishable: false, jobs: [] });
    expect(body.vehicleSummary).toBeNull();
    expect(body.reasonCodes).toContain("FLEET_SHORTAGE");
    expect(client.queries.map((query) => query.table)).toContain("vehicles");
  });

  it("solves one exact admitted anchor with a bound matrix and verified result", async () => {
    const client = setAdmin(admittedRows());
    mockTransport([solverResult("2026-09-30:pickup:student-1")]);
    const { POST } = await import("./route");
    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();
    const calls = optimizerFetchMock.mock.calls;
    expect(calls.map(([path]) => path)).toEqual(["/api/v1/internal/matrix-snapshot", "/api/v1/optimize"]);
    expect(JSON.parse(calls[0][1].body)).toEqual({ student_location_codes: ["Sw1"] });
    expect(JSON.parse(calls[1][1].body)).toMatchObject({
      algorithm: "ga_split", service_date: "2026-09-30", direction: "pickup", target_time: "08:45",
      expected_matrix_sha256: matrix.sha256,
      students: [{ id: "2026-09-30:pickup:student-1", location_code: "Sw1", disability_type: "Sw" }],
    });
    expect(client.queries.map((query) => query.table)).toContain("vehicles");
    expect(body).toMatchObject({ status: "preview_ready", publishable: false });
    expect(body.jobs).toHaveLength(1);
    expect(body.assignments).toHaveLength(1);
    expect(body.vehicleSummary).toEqual({
      minimumVehicles: 1,
      minimumProven: true,
      lowerBound: 1,
      peakConcurrentRoutes: 1,
      activeFleetSize: 1,
      routesPerJob: [{
        jobId: body.jobs[0].id,
        direction: "pickup",
        anchorMinutes: 525,
        routeCount: 1,
        studentCount: 1,
      }],
    });
  });

  it("skips an unscheduled student without blocking admitted scheduled demand", async () => {
    const rows = admittedRows();
    setAdmin({ ...rows, users: [...rows.users, {
      id: "student-2", role: "student", location_code: "So2",
      disability_type: "So", weekly_schedule_id: null,
    }] });
    mockTransport([solverResult("2026-09-30:pickup:student-1")]);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.status).toBe("preview_ready");
    expect(body.reasonCodes).not.toContain("SCHEDULE_DATA_INVALID");
    expect(optimizerFetchMock.mock.calls.map(([path]) => path)).toContain("/api/v1/optimize");
  });

  it.each([
    ["duplicate unscheduled ID", [null, null]],
    ["malformed schedule ID", [42]],
    ["dangling schedule ID", ["missing-schedule"]],
    ["mismatched schedule owner", ["schedule-1"]],
  ])("fails closed on %s", async (_label, scheduleIds) => {
    const rows = admittedRows();
    setAdmin({ ...rows, users: [
      ...rows.users,
      ...scheduleIds.map((scheduleId) => ({
        id: "student-2", role: "student", location_code: "So2",
        disability_type: "So", weekly_schedule_id: scheduleId,
      })),
    ] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("solves two admitted exact anchors sequentially", async () => {
    setAdmin(admittedRows([onTimePickup, { ...onTimePickup, direction: "dropoff" }]));
    mockTransport([
      solverResult("2026-09-30:pickup:student-1"),
      solverResult("2026-09-30:dropoff:student-1"),
    ]);
    const { POST } = await import("./route");
    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();
    const calls = optimizerFetchMock.mock.calls.filter(([path]) => path === "/api/v1/optimize");
    expect(calls).toHaveLength(2);
    const requests = calls.map(([, init]) => JSON.parse(init.body));
    expect(requests.map((item) => [item.direction, item.target_time])).toEqual([["pickup", "08:45"], ["dropoff", "10:15"]]);
    expect(requests.every((item) => item.expected_matrix_sha256 === matrix.sha256 && item.students.length === 1)).toBe(true);
    // Owner decision 2026-10-04: tour upper bound 150 min, student ride limit 90 min by default.
    expect(requests.map((item) => [item.service_date, item.use_time_windows, item.max_travel_time, item.max_ride_time])).toEqual([
      ["2026-09-30", false, 150, 90], ["2026-09-30", false, 150, 90],
    ]);
    expect(requests.every((item) => item.students.every((student: Record<string, unknown>) =>
      !("pickup_time" in student) && !("dropoff_time" in student)))).toBe(true);
    expect(body).toMatchObject({ status: "preview_ready", publishable: false });
    expect(body.jobs).toHaveLength(2);
  });

  it.each(["snapshot", "optimizer", "solver_failure", "certificate", "invalid_result"])("fails closed on %s failure", async (failure) => {
    setAdmin(admittedRows());
    const result = solverResult("2026-09-30:pickup:student-1");
    if (failure === "solver_failure") result.success = false;
    if (failure === "certificate") delete (result as { feasibility_certificate?: unknown }).feasibility_certificate;
    if (failure === "invalid_result") result.routes[0].route_details[0].duration = 99;
    mockTransport([result]);
    if (failure === "snapshot") optimizerFetchMock.mockResolvedValueOnce(Response.json({ error: "secret" }, { status: 503 }));
    if (failure === "optimizer") optimizerFetchMock.mockImplementationOnce(async () => Response.json(matrix))
      .mockResolvedValueOnce(Response.json({ error: "secret" }, { status: 503 }));
    const { POST } = await import("./route");
    const response = await POST(post({ serviceDate: "2026-09-30" }));
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.publishable).toBe(false);
    expect(["blocked_data", "indeterminate"]).toContain(body.status);
    expect(body.jobs).toEqual([]);
    if (failure === "certificate") expect(body.reasonCodes).toContain("CERTIFICATE_INVALID");
    if (failure === "invalid_result") expect(body.reasonCodes).toContain("MATRIX_ARC_MISMATCH");
    if (failure === "solver_failure") expect(body.reasonCodes).toContain("OPTIMIZATION_NOT_SUCCESSFUL");
    expect(JSON.stringify(body)).not.toContain("secret");
  });
  it("authenticates before parsing the body or creating downstream clients", async () => {
    requireAdminMock.mockRejectedValue(AppError.forbidden());
    const { POST } = await import("./route");

    const response = await POST(post("{invalid-json"));

    expect(response.status).toBe(403);
    expect(await response.json()).toEqual({ error: "ADMIN_REQUIRED" });
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it.each(["2026-02-30", "2026-9-30", "2026-09-30T00:00:00Z"])(
    "rejects invalid service date %s before reading data",
    async (serviceDate) => {
      setAdmin();
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate }));

      expect(response.status).toBe(400);
      expect(await response.json()).toEqual({ error: "INVALID_SERVICE_DATE" });
      expect(getSupabaseAdminMock).not.toHaveBeenCalled();
      expect(optimizerFetchMock).not.toHaveBeenCalled();
    },
  );

  it("rejects unknown request fields before reading data", async () => {
    setAdmin();
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30", direction: "pickup" }));

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "INVALID_SERVICE_DATE" });
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
  });

  it("does not treat a Dudullu schedule as a confirmed leg", async () => {
    const rows = { ...legacyRows(), ride_requests: [] };
    const client = setAdmin(rows);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.status).toBe("blocked_data");
    expect(body.reasonCodes).toContain("PENDING_STUDENT_CONFIRMATION");
    expect(body.reasonCodes).not.toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hourlyDemand).toEqual({});
    expect(optimizerFetchMock).not.toHaveBeenCalled();
    expect(client.queries.map((query) => query.table)).not.toContain("vehicles");
    expect(client.queries.map((query) => query.table)).toContain("student_leg_decisions");
    const decisionQuery = client.queries.find((query) => query.table === "student_leg_decisions");
    expect(decisionQuery?.filters).toContainEqual({ method: "in", args: ["user_id", ["student-1"]] });
    expect(decisionQuery?.filters).toContainEqual({ method: "eq", args: ["service_date", "2026-09-30"] });
  });

  it("skips decision reads when no schedule has Dudullu on the service day", async () => {
    const rows = legacyRows();
    rows.weekly_schedules[0].entries[0].location = "Other";
    const client = setAdmin(rows);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));

    expect((await response.json()).reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(client.queries.map((query) => query.table)).not.toContain("student_leg_decisions");
  });

  it("admits only an on-time confirmed pickup when dropoff is cancelled", async () => {
    const rows = { ...legacyRows(), ride_requests: [], student_leg_decisions: [
      onTimePickup,
      { ...onTimePickup, direction: "dropoff", decision: "cancelled" },
    ] };
    const client = setAdmin({ ...rows, vehicles: admittedRows().vehicles });
    mockTransport([solverResult("2026-09-30:pickup:student-1")]);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));
    const body = await response.json();

    expect(body.hourlyDemand["09:00"]).toEqual({ pickup: { Sw: 1, So: 0 }, dropoff: { Sw: 0, So: 0 } });
    expect(body.hourlyDemand["10:00"]).toBeUndefined();
    expect(body.reasonCodes).not.toContain("NO_ADMITTED_DEMAND");
    const calls = optimizerFetchMock.mock.calls.filter(([path]) => path === "/api/v1/optimize");
    expect(calls).toHaveLength(1);
    expect(JSON.parse(calls[0][1].body).students.map((student: { id: string }) => student.id))
      .toEqual(["2026-09-30:pickup:student-1"]);
    expect(client.queries.map((query) => query.table)).toContain("vehicles");
  });

  it("keeps a late explicit confirmation pending administrator approval", async () => {
    setAdmin({ ...legacyRows(), ride_requests: [], student_leg_decisions: [
      { ...onTimePickup, decided_at: "2026-09-29T19:00:00.000001+00:00" },
    ] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hourlyDemand).toEqual({});
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("never promotes a directionless confirmed request into demand", async () => {
    const client = setAdmin(legacyRows());
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    const body = await response.json();
    expect(body).toMatchObject({ status: "blocked_data", publishable: false, jobs: [] });
    expect(body.reasonCodes).toEqual(expect.arrayContaining([
      "PENDING_STUDENT_CONFIRMATION",
      "NO_ADMITTED_DEMAND",
    ]));
    expect(body.reasonCodes).not.toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
    expect(optimizerFetchMock).not.toHaveBeenCalled();
    expect(client.queries.map((query) => query.table)).toEqual([
      "users",
      "weekly_schedules",
      "student_leg_decisions",
      "ride_requests",
    ]);
    expect(client.queries.map((query) => query.columns)).toEqual([
      "id, role, location_code, disability_type, weekly_schedule_id",
      "id, user_id, entries",
      "user_id, service_date, direction, decision, decided_at, flexibility_minutes",
      "id, user_id, requested_pickup_time, requested_dropoff_time, status",
    ]);
    expect(client.queries[0]?.filters).toContainEqual({ method: "eq", args: ["role", "student"] });
    expect(client.queries[1]?.filters).toContainEqual({ method: "in", args: ["id", ["schedule-1"]] });
    expect(client.queries[3]?.filters).toContainEqual({ method: "in", args: ["user_id", ["student-1"]] });
    const requestDateFilter = client.queries[3]?.filters.find((filter) => filter.method === "or");
    expect(requestDateFilter?.args[0]).toContain("requested_pickup_time.gte.2026-09-29T21:00:00.000Z");
    expect(requestDateFilter?.args[0]).toContain("requested_dropoff_time.lt.2026-09-30T21:00:00.000Z");
  });

  it.each(["pending_admin_approval", "cancelled_by_admin", "in_progress"])(
    "blocks both explicit legs for legacy status %s",
    async (status) => {
      const rows = { ...legacyRows(), student_leg_decisions: [
        onTimePickup,
        { ...onTimePickup, direction: "dropoff" },
      ] };
      rows.ride_requests[0].status = status;
      setAdmin(rows);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.reasonCodes).toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
      expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
      expect(body.hourlyDemand).toEqual({});
      expect(optimizerFetchMock).not.toHaveBeenCalled();
    },
  );

  it.each(["confirmed", "pending_student_confirmation", "cancelled_by_student", "completed"])(
    "does not let legacy status %s override an explicit pickup decision",
    async (status) => {
      const rows = { ...legacyRows(), student_leg_decisions: [onTimePickup] };
      rows.ride_requests[0].status = status;
      setAdmin(rows);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.hourlyDemand["09:00"]?.pickup.Sw).toBe(1);
      expect(body.hourlyDemand["10:00"]).toBeUndefined();
      expect(body.reasonCodes).not.toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
    },
  );

  it.each(["confirmed", "pending_student_confirmation", "cancelled_by_student", "completed"])(
    "does not create demand from legacy status %s without a decision",
    async (status) => {
      const rows = legacyRows();
      rows.ride_requests[0].status = status;
      setAdmin(rows);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
      expect(body.hourlyDemand).toEqual({});
    },
  );

  it("fails closed on an unrecognized legacy status", async () => {
    const rows = legacyRows();
    rows.ride_requests[0].status = "future_status";
    setAdmin({ ...rows, student_leg_decisions: [onTimePickup] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hourlyDemand).toEqual({});
  });

  it.each([
    { direction: "sideways" },
    { user_id: "other-student" },
    { service_date: "2026-10-01" },
    { flexibility_minutes: -1 },
    { decided_at: "invalid" },
  ])("fails closed on a malformed decision row %j", async (change) => {
    setAdmin({ ...legacyRows(), ride_requests: [], student_leg_decisions: [{ ...onTimePickup, ...change }] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hourlyDemand).toEqual({});
  });

  it("returns the fixed 503 when the decision read fails", async () => {
    setAdmin(legacyRows(), "student_leg_decisions");
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ error: "PREVIEW_UNAVAILABLE" });
  });

  it("fails closed on duplicate student or decision rows", async () => {
    for (const change of [
      { users: [legacyRows().users[0], legacyRows().users[0]], student_leg_decisions: [] },
      { student_leg_decisions: [onTimePickup, onTimePickup] },
    ]) {
      setAdmin({ ...legacyRows(), ride_requests: [], ...change });
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
      expect(body.hourlyDemand).toEqual({});
      vi.resetModules();
    }
  });

  it("marks malformed schedules invalid and admits no demand", async () => {
    const rows = legacyRows();
    rows.weekly_schedules[0].entries[0].startTime = "25:00";
    setAdmin({ ...rows, ride_requests: [], student_leg_decisions: [onTimePickup] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hourlyDemand).toEqual({});
  });

  it("a legacy blocker applies only to its own student's legs", async () => {
    const rows = legacyRows();
    rows.users.push({ ...rows.users[0], id: "student-2", weekly_schedule_id: "schedule-2" });
    rows.weekly_schedules.push({ ...rows.weekly_schedules[0], id: "schedule-2", user_id: "student-2" });
    const client = setAdmin({
      ...rows,
      student_leg_decisions: [onTimePickup, { ...onTimePickup, user_id: "student-2" }],
      ride_requests: [{ ...rows.ride_requests[0], status: "in_progress" }],
    });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("LEGACY_AMBIGUOUS_CONFIRMATION");
    expect(body.hourlyDemand["09:00"]?.pickup.Sw).toBe(1);
    expect(client.queries.find((query) => query.table === "student_leg_decisions")?.filters)
      .toContainEqual({ method: "in", args: ["user_id", ["student-1", "student-2"]] });
  });

  it("returns the fixed redacted 503 when a Supabase read fails", async () => {
    setAdmin({}, "users");
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30" }));

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    const serialized = JSON.stringify(await response.json());
    expect(serialized).toBe('{"error":"PREVIEW_UNAVAILABLE"}');
    expect(serialized).not.toContain("SUPABASE-SECRET-DIAGNOSTIC");
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------------------
// Demo modes (D1c). K1: `assume_confirmed` is a deliberate, owner-approved, preview-only and
// non-publishable exception to ACTIVE_ROADMAP.md's "do not infer consent". K2: virtual fleet.
// ---------------------------------------------------------------------------------------

type OptimizeBody = {
  students: Array<{ id: string; location_code: string; disability_type: string }>;
  vehicles: Array<{ vehicle_id: string; sw_capacity: number; so_capacity: number; cooldown_minutes: number }>;
  sw_capacity: number;
  so_capacity: number;
};

function crowd(count: number, extra: Record<string, unknown> = {}) {
  const ids = Array.from({ length: count }, (_, index) => index + 1);
  return {
    users: ids.map((n) => ({
      id: `student-${n}`, role: "student", location_code: `Sw${n}`, disability_type: "Sw",
      weekly_schedule_id: `schedule-${n}`, ...extra,
    })),
    weekly_schedules: ids.map((n) => ({
      id: `schedule-${n}`, user_id: `student-${n}`,
      entries: [{ id: `class-${n}`, dayOfWeek: "wednesday", startTime: "09:00", endTime: "10:00", location: "Dudullu" }],
    })),
    ride_requests: [] as unknown[],
    student_leg_decisions: [] as unknown[],
    vehicles: [] as unknown[],
  };
}

const vehicleRow = (id: string, sw: number, so: number, cooldown: number) =>
  ({ id, wheelchair_capacity: sw, seating_capacity: so, cooldown_minutes: cooldown, status: "active" });

function matrixFor(count: number) {
  const arcs: Array<{ origin_code: string; destination_code: string; duration_minutes: number }> = [];
  for (let n = 1; n <= count; n += 1) {
    arcs.push({ origin_code: "D.Kampus", destination_code: `Sw${n}`, duration_minutes: 5 });
    arcs.push({ origin_code: `Sw${n}`, destination_code: "D.Kampus", duration_minutes: 6 });
  }
  return { ...matrix, arcs };
}

/** Matrix + an optimizer that returns one single-student route per student; records every /optimize body. */
function mockCrowdTransport(count: number) {
  const bodies: OptimizeBody[] = [];
  optimizerFetchMock.mockImplementation(async (path: string, init?: { body: string }) => {
    if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrixFor(count));
    if (path !== "/api/v1/optimize") throw new Error("unexpected optimizer path");
    const body = JSON.parse(init!.body) as OptimizeBody;
    bodies.push(body);
    return Response.json({
      success: true,
      routes: body.students.map((student) => ({
        vehicle_id: body.vehicles[0]!.vehicle_id,
        route_details: [
          { location1: "D.Kampus", location2: student.location_code, duration: 5, distance: 0 },
          { location1: student.location_code, location2: "D.Kampus", duration: 6, distance: 0 },
        ],
        total_duration_minutes: 11, sw_count: 1, so_count: 0, student_ids: [student.id],
      })),
      total_duration_minutes: 11 * body.students.length,
      feasibility_certificate: { is_feasible: true },
    });
  });
  return bodies;
}

const confirmedLeg = (n: number, direction: "pickup" | "dropoff" = "pickup") =>
  ({ ...onTimePickup, user_id: `student-${n}`, direction });

function expectReadOnly(client: ReturnType<typeof adminClient>) {
  expect(client.writes).toEqual([]);
  expect(client.rpc).not.toHaveBeenCalled();
  expect(client.queries.length).toBeGreaterThan(0);
  expect(client.queries.every((query) => query.columns !== undefined)).toBe(true);
}

describe("POST /api/admin/dudullu-preview demo modes", () => {
  it("never writes in either admission mode", async () => {
    for (const admissionMode of ["recorded", "assume_confirmed"] as const) {
      const rows = crowd(2);
      const client = setAdmin({
        ...rows, vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)],
        student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)],
      });
      mockCrowdTransport(2);
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", admissionMode }));

      expect(response.status).toBe(200);
      expectReadOnly(client);
      vi.resetModules();
    }
  });

  it("never writes when the preview is blocked or the table is missing", async () => {
    const client = setAdmin(crowd(1), "student_leg_decisions", "42P01");
    const { POST } = await import("./route");
    const response = await POST(post({
      serviceDate: "2026-09-30", admissionMode: "assume_confirmed", fleetMode: "virtual",
    }));
    expect(response.status).toBe(200);
    expectReadOnly(client);
  });

  it("defaults to recorded and live and labels the response as not hypothetical", async () => {
    setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], student_leg_decisions: [confirmedLeg(1)] });
    mockCrowdTransport(1);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body).toMatchObject({
      admissionMode: "recorded", fleetMode: "live", hypothetical: false, publishable: false,
    });
    expect(body.reasonCodes).not.toContain("ADMISSION_ASSUMED");
    expect(body.fleet).toEqual({
      mode: "live", assignmentFleetSize: 1, liveActiveFleetSize: 1, template: null,
      activeVehicleIds: ["v1"],
      maxCapacity: { swCapacity: 2, soCapacity: 2 },
    });
  });

  it("assume_confirmed admits every scheduled leg without decision rows and stays hypothetical", async () => {
    const client = setAdmin({ ...crowd(2), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] });
    const bodies = mockCrowdTransport(2);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body).toMatchObject({
      status: "preview_ready", publishable: false, hypothetical: true,
      admissionMode: "assume_confirmed", fleetMode: "live",
    });
    expect(body.reasonCodes).toContain("ADMISSION_ASSUMED");
    expect(body.reasonCodes).not.toContain("PENDING_STUDENT_CONFIRMATION");
    expect(body.reasonCodes).not.toContain("NO_ADMITTED_DEMAND");
    expect(bodies.map((item) => item.students.length).sort()).toEqual([2, 2]);
    expect(body.candidateSummary).toEqual({
      dudulluStudents: 2,
      legsByAdmission: {
        confirmed: 4, approved: 0, pending_student_confirmation: 0, pending_admin_approval: 0, cancelled: 0,
      },
      invalidStudentRecords: 0,
    });
    expectReadOnly(client);
  });

  it("the same data stays blocked in recorded mode", async () => {
    setAdmin({ ...crowd(2), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "recorded" }))).json();

    expect(body.status).toBe("blocked_data");
    expect(body.reasonCodes).toContain("PENDING_STUDENT_CONFIRMATION");
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(body.hypothetical).toBe(false);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("assume_confirmed still honours a recorded cancellation and a late confirmation counts as confirmed", async () => {
    setAdmin({
      ...crowd(2), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)],
      student_leg_decisions: [
        { ...confirmedLeg(1, "dropoff"), decision: "cancelled" },
        { ...confirmedLeg(2, "pickup"), decided_at: "2026-09-29T19:00:00.000001+00:00" },
      ],
    });
    const bodies = mockCrowdTransport(2);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }))).json();

    expect(body.candidateSummary.legsByAdmission).toMatchObject({ confirmed: 3, cancelled: 1 });
    const dropoff = bodies.find((item) => item.students.some((student) => student.id.includes(":dropoff:")));
    expect(dropoff?.students.map((student) => student.id)).toEqual(["2026-09-30:dropoff:student-2"]);
    expect(body.status).toBe("preview_ready");
  });

  it("assume_confirmed includes legacy-blocked students and keeps the info code", async () => {
    const rows = crowd(1);
    rows.ride_requests = [{
      id: "request-1", user_id: "student-1", requested_pickup_time: "2026-09-30T06:00:00.000Z",
      requested_dropoff_time: "2026-09-30T14:00:00.000Z", status: "in_progress",
    }];
    setAdmin({ ...rows, vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] });
    mockCrowdTransport(1);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }))).json();

    expect(body.status).toBe("preview_ready");
    expect(body.reasonCodes).toEqual(expect.arrayContaining(["LEGACY_AMBIGUOUS_CONFIRMATION", "ADMISSION_ASSUMED"]));
    expect(body.candidateSummary.legsByAdmission.confirmed).toBe(2);
  });

  describe("missing student_leg_decisions table", () => {
    it.each(["42P01", "PGRST205"])("recorded mode returns a clear blocked result for %s", async (code) => {
      const client = setAdmin(crowd(1), "student_leg_decisions", code);
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30" }));
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body).toMatchObject({ status: "blocked_data", publishable: false, jobs: [] });
      expect(body.reasonCodes).toEqual(["LEG_DECISIONS_UNAVAILABLE"]);
      expect(JSON.stringify(body)).not.toContain("SUPABASE-SECRET-DIAGNOSTIC");
      expect(client.queries.map((query) => query.table)).not.toContain("vehicles");
      expect(optimizerFetchMock).not.toHaveBeenCalled();
    });

    it("assume_confirmed proceeds without the table and reports the code as information", async () => {
      setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] }, "student_leg_decisions", "42P01");
      mockCrowdTransport(1);
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }));
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.status).toBe("preview_ready");
      expect(body.reasonCodes).toEqual(expect.arrayContaining(["LEG_DECISIONS_UNAVAILABLE", "ADMISSION_ASSUMED"]));
    });

    it.each(["recorded", "assume_confirmed"])("keeps failing closed on other read errors in %s mode", async (admissionMode) => {
      setAdmin(crowd(1), "student_leg_decisions", "XX000");
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", admissionMode }));

      expect(response.status).toBe(503);
      expect(await response.json()).toEqual({ error: "PREVIEW_UNAVAILABLE" });
    });

    it("does not treat a missing relation other than the decisions table as recoverable", async () => {
      setAdmin(crowd(1), "ride_requests", "42P01");
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }));

      expect(response.status).toBe(503);
    });
  });

  describe("virtual fleet", () => {
    it("caps every /optimize vehicle list at 50 while the assignment fleet covers all 60 legs", async () => {
      setAdmin({
        ...crowd(60), vehicles: [vehicleRow("v1", 2, 2, 10)],
        student_leg_decisions: Array.from({ length: 60 }, (_, index) => confirmedLeg(index + 1)),
      });
      const bodies = mockCrowdTransport(60);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(bodies).toHaveLength(1);
      expect(bodies.every((item) => item.vehicles.length <= 50)).toBe(true);
      expect(bodies[0]!.vehicles).toHaveLength(50);
      expect(new Set(bodies[0]!.vehicles.map((item) => `${item.sw_capacity}|${item.so_capacity}|${item.cooldown_minutes}`)).size).toBe(1);
      expect(body).toMatchObject({ status: "preview_ready", fleetMode: "virtual", hypothetical: true, publishable: false });
      expect(body.vehicleSummary.activeFleetSize).toBeGreaterThanOrEqual(60);
      expect(body.vehicleSummary).toMatchObject({ minimumVehicles: 60, minimumProven: true });
      expect(body.fleet).toMatchObject({ mode: "virtual", assignmentFleetSize: 60, liveActiveFleetSize: 1 });
      expect(new Set(body.assignments.map((item: { physicalVehicleId: string }) => item.physicalVehicleId)).size).toBe(60);
      expect(body.assignments.every((item: { physicalVehicleId: string }) => item.physicalVehicleId.startsWith("virtual:"))).toBe(true);
    });

    it("sizes the fleet by all admitted legs of the day and sends at most the wave size per call", async () => {
      setAdmin({ ...crowd(3), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] });
      const bodies = mockCrowdTransport(3);
      const { POST } = await import("./route");

      const body = await (await POST(post({
        serviceDate: "2026-09-30", admissionMode: "assume_confirmed", fleetMode: "virtual",
      }))).json();

      expect(body.status).toBe("preview_ready");
      expect(bodies.map((item) => item.vehicles.length)).toEqual([3, 3]);
      expect(body.fleet).toEqual({
        mode: "virtual", assignmentFleetSize: 6, liveActiveFleetSize: 2,
        activeVehicleIds: ["v1", "v2"],
        template: { swCapacity: 2, soCapacity: 2, cooldownMinutes: 10 },
        maxCapacity: { swCapacity: 2, soCapacity: 2 },
      });
      expect(body.vehicleSummary).toMatchObject({ activeFleetSize: 6, minimumVehicles: 3, minimumProven: true });
    });

    it("proves 3 vehicles are needed for a 3-route wave although only 2 are live", async () => {
      setAdmin({
        ...crowd(3), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)],
        student_leg_decisions: [confirmedLeg(1), confirmedLeg(2), confirmedLeg(3)],
      });
      mockCrowdTransport(3);
      const { POST } = await import("./route");

      const live = await (await POST(post({ serviceDate: "2026-09-30" }))).json();
      const virtual = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(live.status).toBe("shortage");
      expect(virtual.status).toBe("preview_ready");
      expect(virtual.vehicleSummary.minimumVehicles).toBe(3);
      expect(virtual.fleet.liveActiveFleetSize).toBe(2);
    });

    it("uses the most common live signature as the template", async () => {
      setAdmin({
        ...crowd(2), student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)],
        vehicles: [vehicleRow("a", 4, 12, 5), vehicleRow("b", 2, 8, 10), vehicleRow("c", 2, 8, 10)],
      });
      const bodies = mockCrowdTransport(2);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(body.fleet.template).toEqual({ swCapacity: 2, soCapacity: 8, cooldownMinutes: 10 });
      expect(bodies[0]!.vehicles.every((item) =>
        item.sw_capacity === 2 && item.so_capacity === 8 && item.cooldown_minutes === 10)).toBe(true);
      expect(body.fleet.liveActiveFleetSize).toBe(3);
    });

    it("falls back to the default template (Sw 4 / So 10 / cooldown 10) when no vehicle is active", async () => {
      setAdmin({ ...crowd(2), student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)] });
      mockCrowdTransport(2);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(body.status).toBe("preview_ready");
      expect(body.fleet).toEqual({
        mode: "virtual", assignmentFleetSize: 2, liveActiveFleetSize: 0,
        activeVehicleIds: [],
        template: { swCapacity: 4, soCapacity: 10, cooldownMinutes: 10 },
        maxCapacity: { swCapacity: 4, soCapacity: 10 },
      });
    });

    it("reports the largest Sw and So capacity of the live fleet, each pool on its own", async () => {
      setAdmin({
        ...crowd(2), student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)],
        vehicles: [vehicleRow("a", 4, 6, 5), vehicleRow("b", 2, 12, 10)],
      });
      mockCrowdTransport(2);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.fleet.maxCapacity).toEqual({ swCapacity: 4, soCapacity: 12 });
    });

    it("reports the template capacity for the virtual fleet and null when no fleet was built", async () => {
      setAdmin({ ...crowd(1), vehicles: [vehicleRow("a", 4, 6, 5), vehicleRow("b", 2, 12, 10)] });
      mockCrowdTransport(1);
      const { POST } = await import("./route");

      const virtual = await (await POST(post({
        serviceDate: "2026-09-30", admissionMode: "assume_confirmed", fleetMode: "virtual",
      }))).json();
      expect(virtual.fleet.maxCapacity).toEqual({
        swCapacity: virtual.fleet.template.swCapacity, soCapacity: virtual.fleet.template.soCapacity,
      });

      setAdmin({ ...crowd(1) });
      const noFleet = await (await POST(post({ serviceDate: "2026-09-30" }))).json();
      expect(noFleet.fleet.maxCapacity).toBeNull();
    });

    it("still fails closed on an invalid live fleet row", async () => {
      setAdmin({
        ...crowd(1), student_leg_decisions: [confirmedLeg(1)],
        vehicles: [{ ...vehicleRow("v1", 2, 2, 10), cooldown_minutes: null }],
      });
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(body.reasonCodes).toContain("FLEET_INVALID");
      expect(optimizerFetchMock).not.toHaveBeenCalled();
    });
  });

  describe("live fleet shortage", () => {
    it("reports FLEET_SHORTAGE when the optimizer certificate says routes exceed vehicles", async () => {
      setAdmin({
        ...crowd(2), vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)],
        student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)],
      });
      optimizerFetchMock.mockImplementation(async (path: string) => {
        if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrixFor(2));
        return Response.json({
          success: false, routes: [],
          feasibility_certificate: {
            is_feasible: false, violation_count: 1,
            violations: [{ type: "fleet_size_violation", severity: "error", details: "2 routes but 1 vehicle" }],
          },
        });
      });
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

      expect(body.status).toBe("shortage");
      expect(body.reasonCodes).toContain("FLEET_SHORTAGE");
      expect(body.reasonCodes).not.toContain("OPTIMIZATION_NOT_SUCCESSFUL");
      expect(body.publishable).toBe(false);
    });

    it("keeps OPTIMIZATION_NOT_SUCCESSFUL for the same fleet_size_violation in virtual mode", async () => {
      setAdmin({
        ...crowd(2), vehicles: [vehicleRow("v1", 2, 2, 10)],
        student_leg_decisions: [confirmedLeg(1), confirmedLeg(2)],
      });
      optimizerFetchMock.mockImplementation(async (path: string) => {
        if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrixFor(2));
        return Response.json({
          success: false, routes: [],
          feasibility_certificate: {
            is_feasible: false, violation_count: 1,
            violations: [{ type: "fleet_size_violation", severity: "error", details: "2 routes but 1 vehicle" }],
          },
        });
      });
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", fleetMode: "virtual" }))).json();

      expect(body.status).not.toBe("shortage");
      expect(body.reasonCodes).toContain("OPTIMIZATION_NOT_SUCCESSFUL");
      expect(body.reasonCodes).not.toContain("FLEET_SHORTAGE");
      expect(body.publishable).toBe(false);
    });
  });

  describe("invalid student records", () => {
    const withInvalidProfile = (change: Record<string, unknown>) => {
      const rows = crowd(2);
      rows.users[1] = { ...rows.users[1]!, ...change };
      return { ...rows, vehicles: [vehicleRow("v1", 2, 2, 10), vehicleRow("v2", 2, 2, 10)] };
    };

    it.each([
      ["missing location_code", { location_code: null }],
      ["missing disability_type", { disability_type: null }],
    ])("excludes and counts a student with %s in assume_confirmed mode only", async (_label, change) => {
      setAdmin(withInvalidProfile(change));
      mockCrowdTransport(2);
      const { POST } = await import("./route");

      const assumed = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }))).json();

      expect(assumed.status).toBe("preview_ready");
      expect(assumed.reasonCodes).not.toContain("SCHEDULE_DATA_INVALID");
      expect(assumed.candidateSummary).toMatchObject({ dudulluStudents: 1, invalidStudentRecords: 1 });
      expect(assumed.candidateSummary.legsByAdmission.confirmed).toBe(2);

      vi.resetModules();
      setAdmin(withInvalidProfile(change));
      const { POST: recordedPost } = await import("./route");
      const recorded = await (await recordedPost(post({ serviceDate: "2026-09-30" }))).json();
      expect(recorded.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
      expect(recorded.candidateSummary.invalidStudentRecords).toBe(0);
    });

    it("still blocks the whole day on integrity errors in assume_confirmed mode", async () => {
      for (const change of [
        { users: [crowd(1).users[0], crowd(1).users[0]] },
        { weekly_schedules: [{ ...crowd(1).weekly_schedules[0], user_id: "someone-else" }] },
      ]) {
        setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], ...change });
        const { POST } = await import("./route");

        const body = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }))).json();

        expect(body.reasonCodes).toContain("SCHEDULE_DATA_INVALID");
        expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
        expect(optimizerFetchMock).not.toHaveBeenCalled();
        vi.resetModules();
      }
    });
  });

  describe("display labels", () => {
    it("returns no user name and labels occurrences with the location code", async () => {
      const rows = crowd(2, { name: "Ayse Yilmaz-PRIVATE" });
      const client = setAdmin({ ...rows, vehicles: [vehicleRow("v1", 2, 2, 10)] });
      mockCrowdTransport(2);
      const { POST } = await import("./route");

      const body = await (await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }))).json();

      expect(JSON.stringify(body)).not.toContain("PRIVATE");
      expect(JSON.stringify(body)).not.toMatch(/"name"/);
      expect(client.queries[0]?.columns).not.toContain("name");
      expect(body.occurrenceLabels).toEqual({
        "2026-09-30:pickup:student-1": "Sw1", "2026-09-30:dropoff:student-1": "Sw1",
        "2026-09-30:pickup:student-2": "Sw2", "2026-09-30:dropoff:student-2": "Sw2",
      });
    });
  });

  describe("request contract", () => {
    it.each([
      { admissionMode: "everyone" },
      { fleetMode: "huge" },
      { admissionMode: null },
    ])("rejects %j before reading data", async (extra) => {
      setAdmin();
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", ...extra }));

      expect(response.status).toBe(400);
      expect(await response.json()).toEqual({ error: "INVALID_MODE" });
      expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    });

    it("still requires the administrator before looking at the new fields", async () => {
      requireAdminMock.mockRejectedValue(AppError.forbidden());
      const { POST } = await import("./route");

      const response = await POST(post({ serviceDate: "2026-09-30", admissionMode: "assume_confirmed" }));

      expect(response.status).toBe(403);
      expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    });
  });
});

// ---------------------------------------------------------------------------------------
// Owner decision (2026-10-04): the limit is the time a STUDENT stays in the vehicle
// (`max_ride_time`, default 90 min); the vehicle tour (`max_travel_time`) gets an upper bound
// (default 150 min). Both are adjustable per request.
// ---------------------------------------------------------------------------------------

type LimitBody = OptimizeBody & { max_ride_time?: unknown; max_travel_time?: unknown };

/** Like `mockCrowdTransport`, but with a custom matrix; every /optimize body is recorded. */
function mockLimitTransport(arcs: Array<{ origin_code: string; destination_code: string; duration_minutes: number }>) {
  const bodies: LimitBody[] = [];
  optimizerFetchMock.mockImplementation(async (path: string, init?: { body: string }) => {
    if (path === "/api/v1/internal/matrix-snapshot") return Response.json({ ...matrix, arcs });
    if (path !== "/api/v1/optimize") throw new Error("unexpected optimizer path");
    const body = JSON.parse(init!.body) as LimitBody;
    bodies.push(body);
    return Response.json({
      success: true,
      routes: body.students.map((student) => ({
        vehicle_id: body.vehicles[0]!.vehicle_id,
        route_details: [
          { location1: "D.Kampus", location2: student.location_code, duration: 5, distance: 0 },
          { location1: student.location_code, location2: "D.Kampus", duration: 6, distance: 0 },
        ],
        total_duration_minutes: 11, sw_count: 1, so_count: 0, student_ids: [student.id],
      })),
      total_duration_minutes: 11 * body.students.length,
      feasibility_certificate: { is_feasible: true },
    });
  });
  return bodies;
}

const SHORT_ARCS = [
  { origin_code: "D.Kampus", destination_code: "Sw1", duration_minutes: 5 },
  { origin_code: "Sw1", destination_code: "D.Kampus", duration_minutes: 6 },
];
/** Pickup arc Sw1 -> campus is 40 min; the dropoff arc campus -> Sw1 stays 5 min. */
const LONG_PICKUP_ARCS = [
  { origin_code: "D.Kampus", destination_code: "Sw1", duration_minutes: 5 },
  { origin_code: "Sw1", destination_code: "D.Kampus", duration_minutes: 40 },
];

const oneStudentRows = () => ({
  ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], student_leg_decisions: [confirmedLeg(1)],
});

describe("POST /api/admin/dudullu-preview time limits", () => {
  it("forwards the defaults (90 min ride, 150 min tour) and echoes them", async () => {
    setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], student_leg_decisions: [confirmedLeg(1), confirmedLeg(1, "dropoff")] });
    const bodies = mockLimitTransport(SHORT_ARCS);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(bodies).toHaveLength(2);
    expect(bodies.map((item) => [item.max_ride_time, item.max_travel_time])).toEqual([[90, 150], [90, 150]]);
    expect(body.limits).toEqual({ maxRideTimeMinutes: 90, maxTourMinutes: 150, minimumFeasibleRideMinutes: null });
    expect(body.status).toBe("preview_ready");
  });

  it("forwards custom limits to every /optimize call and echoes them", async () => {
    setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], student_leg_decisions: [confirmedLeg(1), confirmedLeg(1, "dropoff")] });
    const bodies = mockLimitTransport(SHORT_ARCS);
    const { POST } = await import("./route");

    const body = await (await POST(post({
      serviceDate: "2026-09-30", maxRideTimeMinutes: 60, maxTourMinutes: 200,
    }))).json();

    expect(bodies).toHaveLength(2);
    expect(bodies.every((item) => item.max_ride_time === 60 && item.max_travel_time === 200)).toBe(true);
    expect(body.limits).toEqual({ maxRideTimeMinutes: 60, maxTourMinutes: 200, minimumFeasibleRideMinutes: null });
  });

  it("applies one limit and defaults the other", async () => {
    setAdmin(oneStudentRows());
    const bodies = mockLimitTransport(SHORT_ARCS);
    const { POST } = await import("./route");

    await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 45 }));

    expect(bodies.map((item) => [item.max_ride_time, item.max_travel_time])).toEqual([[45, 150]]);
  });

  it.each([
    [{ maxRideTimeMinutes: 15 }, 15, 150],
    [{ maxRideTimeMinutes: 240 }, 240, 150],
    [{ maxTourMinutes: 30 }, 90, 30],
    [{ maxTourMinutes: 300 }, 90, 300],
  ])("accepts the boundary %j", async (extra, ride, tour) => {
    setAdmin(oneStudentRows());
    const bodies = mockLimitTransport(SHORT_ARCS);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30", ...extra }));

    expect(response.status).toBe(200);
    expect(bodies.map((item) => [item.max_ride_time, item.max_travel_time])).toEqual([[ride, tour]]);
  });

  it.each([
    { maxRideTimeMinutes: 14 },
    { maxRideTimeMinutes: 241 },
    { maxRideTimeMinutes: 45.5 },
    { maxRideTimeMinutes: "60" },
    { maxRideTimeMinutes: null },
    { maxRideTimeMinutes: 0 },
    { maxTourMinutes: 29 },
    { maxTourMinutes: 301 },
    { maxTourMinutes: -5 },
    { maxTourMinutes: 120.5 },
    { maxRideTimeMinutes: 10, maxTourMinutes: 500 },
  ])("rejects %j with INVALID_LIMIT before reading data", async (extra) => {
    setAdmin();
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30", ...extra }));

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "INVALID_LIMIT" });
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("keeps INVALID_MODE ahead of INVALID_LIMIT and rejects unknown fields as before", async () => {
    setAdmin();
    const { POST } = await import("./route");

    const both = await POST(post({ serviceDate: "2026-09-30", fleetMode: "huge", maxRideTimeMinutes: 1 }));
    expect(await both.json()).toEqual({ error: "INVALID_MODE" });
    const unknown = await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 1, extra: true }));
    expect(await unknown.json()).toEqual({ error: "INVALID_SERVICE_DATE" });
    const badDate = await POST(post({ serviceDate: "2026-02-30", maxRideTimeMinutes: 1 }));
    expect(await badDate.json()).toEqual({ error: "INVALID_SERVICE_DATE" });
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
  });

  it("reports RIDE_TIME_LIMIT_INFEASIBLE with the minimum feasible limit and never calls the optimizer", async () => {
    const client = setAdmin(oneStudentRows());
    mockLimitTransport(LONG_PICKUP_ARCS);
    const { POST } = await import("./route");

    const response = await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 30 }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body).toMatchObject({ status: "blocked_data", publishable: false, jobs: [] });
    expect(body.reasonCodes).toContain("RIDE_TIME_LIMIT_INFEASIBLE");
    expect(body.reasonCodes).not.toContain("OPTIMIZATION_NOT_SUCCESSFUL");
    expect(body.limits).toEqual({ maxRideTimeMinutes: 30, maxTourMinutes: 150, minimumFeasibleRideMinutes: 40 });
    expect(optimizerFetchMock.mock.calls.map(([path]) => path)).toEqual(["/api/v1/internal/matrix-snapshot"]);
    expectReadOnly(client);
  });

  it("rounds the minimum feasible limit up", async () => {
    setAdmin(oneStudentRows());
    mockLimitTransport([LONG_PICKUP_ARCS[0]!, { ...LONG_PICKUP_ARCS[1]!, duration_minutes: 40.2 }]);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 30 }))).json();

    expect(body.limits.minimumFeasibleRideMinutes).toBe(41);
  });

  it("lets a limit equal to the direct ride through", async () => {
    setAdmin(oneStudentRows());
    const bodies = mockLimitTransport(LONG_PICKUP_ARCS.map((item) => ({ ...item })));
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 40 }))).json();

    expect(bodies).toHaveLength(1);
    expect(body.reasonCodes).not.toContain("RIDE_TIME_LIMIT_INFEASIBLE");
  });

  it("checks the arc in the wave's own direction (a long pickup arc does not block a dropoff)", async () => {
    setAdmin({ ...crowd(1), vehicles: [vehicleRow("v1", 2, 2, 10)], student_leg_decisions: [confirmedLeg(1, "dropoff")] });
    const bodies = mockLimitTransport(LONG_PICKUP_ARCS);
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30", maxRideTimeMinutes: 30 }))).json();

    expect(bodies).toHaveLength(1);
    expect(body.reasonCodes).not.toContain("RIDE_TIME_LIMIT_INFEASIBLE");
  });

  it("maps an optimizer ride_time_violation certificate to RIDE_TIME_LIMIT_INFEASIBLE", async () => {
    setAdmin(oneStudentRows());
    optimizerFetchMock.mockImplementation(async (path: string) => {
      if (path === "/api/v1/internal/matrix-snapshot") return Response.json({ ...matrix, arcs: SHORT_ARCS });
      return Response.json({
        success: false, routes: [],
        feasibility_certificate: {
          is_feasible: false, violation_count: 1,
          violations: [{ type: "ride_time_violation", severity: "error", details: "ride 95 exceeds max 90" }],
        },
      });
    });
    const { POST } = await import("./route");

    const body = await (await POST(post({ serviceDate: "2026-09-30" }))).json();

    expect(body.reasonCodes).toContain("RIDE_TIME_LIMIT_INFEASIBLE");
    expect(body.reasonCodes).not.toContain("OPTIMIZATION_NOT_SUCCESSFUL");
    expect(body.status).toBe("blocked_data");
    expect(body.limits.minimumFeasibleRideMinutes).toBeNull();
  });

  it("stays read-only and carries the limits on blocked responses too", async () => {
    const client = setAdmin(crowd(1), "student_leg_decisions", "42P01");
    const { POST } = await import("./route");

    const response = await POST(post({
      serviceDate: "2026-09-30", admissionMode: "recorded", maxRideTimeMinutes: 75, maxTourMinutes: 180,
    }));
    const body = await response.json();

    expect(body.limits).toEqual({ maxRideTimeMinutes: 75, maxTourMinutes: 180, minimumFeasibleRideMinutes: null });
    expectReadOnly(client);
  });
});
