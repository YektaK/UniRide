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

type QueryResult = { data: unknown; error: { message: string } | null };
type QueryTrace = {
  table: string;
  columns?: string;
  filters: Array<{ method: string; args: unknown[] }>;
};

function adminClient(
  rows: Record<string, unknown[]> = {},
  failedTable?: string,
) {
  const queries: QueryTrace[] = [];
  const from = vi.fn((table: string) => {
    const trace: QueryTrace = { table, filters: [] };
    queries.push(trace);
    const result: QueryResult = {
      data: rows[table] ?? [],
      error: table === failedTable ? { message: "SUPABASE-SECRET-DIAGNOSTIC" } : null,
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
  return { from, queries };
}

function setAdmin(rows: Record<string, unknown[]> = {}, failedTable?: string) {
  const client = adminClient(rows, failedTable);
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
    expect(body.reasonCodes).toContain("NO_ADMITTED_DEMAND");
    expect(client.queries.map((query) => query.table)).not.toContain("vehicles");
    expect(optimizerFetchMock).not.toHaveBeenCalled();
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
