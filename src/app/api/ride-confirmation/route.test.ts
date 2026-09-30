import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getCurrentUserFromRequest: vi.fn(),
  getSupabaseAdmin: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, getCurrentUserFromRequest: mocks.getCurrentUserFromRequest };
});

vi.mock("@/lib/supabase-admin", () => ({
  getSupabaseAdmin: mocks.getSupabaseAdmin,
}));

function confirmationRequest() {
  return new Request("http://localhost/api/ride-confirmation", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      action: "confirm",
      rideDate: "2026-09-30",
      direction: "pickup",
    }),
  });
}

describe("POST /api/ride-confirmation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("rejects an unauthenticated request before creating a data client", async () => {
    mocks.getCurrentUserFromRequest.mockResolvedValue(null);

    const { POST } = await import("./route");
    const response = await POST(confirmationRequest() as never);

    expect(response.status).toBe(401);
    expect(mocks.getSupabaseAdmin).not.toHaveBeenCalled();
  });
});

const date = "2026-09-30";
const validBody = { action: "confirm", rideDate: date, direction: "pickup" };
const student = { id: "student-1", role: "student" };
const schedule = { id: "schedule-1", user_id: student.id, entries: [{ dayOfWeek: "wednesday", location: "Dudullu" }] };

function post(body: object) {
  return new Request("http://localhost/api/ride-confirmation", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
}

function get(serviceDate = date) {
  return new Request(`http://localhost/api/ride-confirmation?date=${serviceDate}`);
}

function mockData(rows: Record<string, Record<string, unknown>[]> = {}, failure?: string) {
  const data = { users: [{ id: student.id, weekly_schedule_id: schedule.id }], weekly_schedules: [schedule], student_leg_decisions: [], ride_requests: [], ...rows };
  const calls: Array<{ table: string; op: string; args: unknown[] }> = [];
  const from = vi.fn((table: string) => {
    const filters: Array<(row: Record<string, unknown>) => boolean> = [];
    const result = () => ({
      data: ((data as Record<string, Record<string, unknown>[]>)[table] ?? []).filter((row) => filters.every((f) => f(row))),
      error: table === failure ? { message: "SECRET_PROVIDER_DETAIL" } : null,
    });
    const query = {
      select(columns: string) { calls.push({ table, op: "select", args: [columns] }); return query; },
      eq(column: string, value: unknown) { calls.push({ table, op: "eq", args: [column, value] }); filters.push((row) => row[column] === value); return query; },
      gte(column: string, value: string) { calls.push({ table, op: "gte", args: [column, value] }); filters.push((row) => String(row[column]) >= value); return query; },
      lt(column: string, value: string) { calls.push({ table, op: "lt", args: [column, value] }); filters.push((row) => String(row[column]) < value); return query; },
      or(value: string) { calls.push({ table, op: "or", args: [value] }); return query; },
      single: vi.fn(async () => { const r = result(); return { data: r.data[0] ?? null, error: r.error ?? (r.data.length ? null : { code: "PGRST116" }) }; }),
      maybeSingle: vi.fn(async () => { const r = result(); return { data: r.data[0] ?? null, error: r.error }; }),
      upsert: vi.fn(async (value: Record<string, unknown>, options: unknown) => { calls.push({ table, op: "upsert", args: [value, options] }); return { error: table === failure ? { message: "SECRET_PROVIDER_DETAIL" } : null }; }),
      update: vi.fn((value: Record<string, unknown>) => { calls.push({ table, op: "update", args: [value] }); return query; }),
      then(onfulfilled: (value: ReturnType<typeof result>) => unknown) { return Promise.resolve(result()).then(onfulfilled); },
    };
    return query;
  });
  mocks.getSupabaseAdmin.mockReturnValue({ from });
  mocks.getCurrentUserFromRequest.mockResolvedValue(student);
  return { from, calls };
}

describe("student leg BFF", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  it.each([
    { action: "confirm", rideDate: date },
    { ...validBody, userId: "other" },
    { ...validBody, unexpected: true },
    { ...validBody, rideDate: "2026-02-30" },
    { ...validBody, direction: "both" },
    { ...validBody, flexibilityMinutes: -1 },
    { ...validBody, flexibilityMinutes: 1440 },
    { action: "change", rideDate: date, userId: "other" },
    { action: "change", rideDate: "2026-02-30" },
  ])("rejects malformed input before auth or protected reads: %j", async (body) => {
    const client = mockData();
    const { POST } = await import("./route");
    expect((await POST(post(body) as never)).status).toBe(400);
    expect(mocks.getCurrentUserFromRequest).not.toHaveBeenCalled();
    expect(client.calls).toEqual([]);
  });

  it("requires a student role before decision or legacy access", async () => {
    const client = mockData();
    mocks.getCurrentUserFromRequest.mockResolvedValue({ id: student.id, role: "admin" });
    const { GET, POST } = await import("./route");
    expect((await GET(get() as never)).status).toBe(403);
    expect((await POST(post(validBody) as never)).status).toBe(403);
    expect(client.calls).toEqual([]);
  });

  it("rejects all writes before protected reads when the linked Dudullu service is absent", async () => {
    const client = mockData({ weekly_schedules: [{ ...schedule, entries: [] }] });
    const { POST } = await import("./route");
    for (const body of [validBody, { action: "change", rideDate: date, notes: "later" }]) {
      const response = await POST(post(body) as never);
      expect(response.status).toBe(409);
      expect(await response.json()).toEqual({ error: "NO_DUDULLU_SERVICE" });
    }
    expect(client.calls.some((c) => ["student_leg_decisions", "ride_requests"].includes(c.table))).toBe(false);
  });

  it("rejects a linked schedule owned by another student", async () => {
    const client = mockData({ weekly_schedules: [{ ...schedule, user_id: "other" }] });
    const { POST } = await import("./route");
    expect((await POST(post(validBody) as never)).status).toBe(409);
    expect(client.calls.some((c) => ["student_leg_decisions", "ride_requests"].includes(c.table))).toBe(false);
  });

  it("writes one pickup key without touching dropoff or legacy requests", async () => {
    const client = mockData({ student_leg_decisions: [{ user_id: student.id, service_date: date, direction: "dropoff", decision: "cancelled", flexibility_minutes: 0 }] });
    const { POST } = await import("./route");
    expect((await POST(post({ ...validBody, flexibilityMinutes: 15 }) as never)).status).toBe(200);
    expect(client.calls.filter((c) => c.op === "upsert")).toEqual([{ table: "student_leg_decisions", op: "upsert", args: [
      { user_id: student.id, service_date: date, direction: "pickup", decision: "confirmed", flexibility_minutes: 15 },
      { onConflict: "user_id,service_date,direction" },
    ] }]);
    expect(client.calls.some((c) => c.table === "ride_requests")).toBe(false);
  });

  it("skips identical retries and stores zero flexibility for cancellations", async () => {
    const client = mockData({ student_leg_decisions: [{ user_id: student.id, service_date: date, direction: "pickup", decision: "confirmed", flexibility_minutes: 15, decided_at: "2026-09-29T18:00:00Z" }] });
    const { POST } = await import("./route");
    expect((await POST(post({ ...validBody, flexibilityMinutes: 15 }) as never)).status).toBe(200);
    expect(client.calls.some((c) => c.op === "upsert")).toBe(false);
    expect((await POST(post({ ...validBody, action: "cancel", flexibilityMinutes: 15 }) as never)).status).toBe(200);
    expect(client.calls.find((c) => c.op === "upsert")?.args[0]).toEqual({ user_id: student.id, service_date: date, direction: "pickup", decision: "cancelled", flexibility_minutes: 0 });
  });

  it("GET returns only caller legs and legacy blocker without a schedule gate", async () => {
    const client = mockData({
      student_leg_decisions: [
        { user_id: student.id, service_date: date, direction: "pickup", decision: "confirmed", flexibility_minutes: 0, decided_at: "2026-09-29T19:30:00.000Z" },
        { user_id: "other", service_date: date, direction: "dropoff", decision: "confirmed", flexibility_minutes: 0, decided_at: "2026-09-29T18:00:00.000Z" },
      ],
      ride_requests: [{ user_id: student.id, requested_pickup_time: "2026-09-30T06:00:00.000Z", status: "pending_admin_approval" }],
    });
    const { GET } = await import("./route");
    const response = await GET(get() as never);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      legs: { pickup: { decision: "confirmed", admission: "pending_admin_approval" }, dropoff: { decision: "pending", admission: "pending_student_confirmation" } },
      legacyBlocker: true,
    });
    expect(client.calls.some((c) => c.table === "weekly_schedules")).toBe(false);
    expect(client.calls).toContainEqual({ table: "student_leg_decisions", op: "eq", args: ["user_id", student.id] });
    expect(client.calls).toContainEqual({ table: "student_leg_decisions", op: "eq", args: ["service_date", date] });
    expect(client.calls).toContainEqual({ table: "ride_requests", op: "eq", args: ["user_id", student.id] });
    expect(client.calls).toContainEqual({ table: "ride_requests", op: "or", args: [
      "and(requested_pickup_time.gte.2026-09-29T21:00:00.000Z,requested_pickup_time.lt.2026-09-30T21:00:00.000Z)," +
      "and(requested_dropoff_time.gte.2026-09-29T21:00:00.000Z,requested_dropoff_time.lt.2026-09-30T21:00:00.000Z)",
    ] });
  });

  it("GET validates its date before authentication", async () => {
    const client = mockData();
    const { GET } = await import("./route");
    expect((await GET(get("2026-02-30") as never)).status).toBe(400);
    expect(mocks.getCurrentUserFromRequest).not.toHaveBeenCalled();
    expect(client.calls).toEqual([]);
  });

  it("GET projects a cancelled leg and ignores nonblocking legacy statuses", async () => {
    mockData({
      student_leg_decisions: [{ user_id: student.id, service_date: date, direction: "dropoff", decision: "cancelled", flexibility_minutes: 0, decided_at: "2026-09-28T18:00:00.000Z" }],
      ride_requests: [{ user_id: student.id, status: "completed", requested_pickup_time: "2026-09-30T06:00:00.000Z" }],
    });
    const { GET } = await import("./route");
    expect(await (await GET(get() as never)).json()).toEqual({
      legs: { pickup: { decision: "pending", admission: "pending_student_confirmation" }, dropoff: { decision: "cancelled", admission: "cancelled" } },
      legacyBlocker: false,
    });
  });

  it("fails closed on an unknown legacy status in the student view", async () => {
    mockData({
      ride_requests: [{ user_id: student.id, status: "future_status", requested_pickup_time: "2026-09-30T06:00:00.000Z" }],
    });
    const { GET } = await import("./route");

    const body = await (await GET(get() as never)).json();

    expect(body).toMatchObject({ legacyBlocker: true });
  });

  it("preserves change as legacy review without a decision write", async () => {
    const client = mockData({ ride_requests: [{ id: "ride-1", user_id: student.id, requested_pickup_time: "2026-09-30T06:00:00.000Z", notes: null }] });
    const { POST } = await import("./route");
    expect((await POST(post({ action: "change", rideDate: date, notes: "later" }) as never)).status).toBe(200);
    expect(client.calls).toContainEqual({ table: "ride_requests", op: "update", args: [expect.objectContaining({ status: "pending_admin_approval", notes: "later" })] });
    expect(client.calls.some((c) => c.table === "student_leg_decisions")).toBe(false);
  });

  it("returns a fixed redacted provider error", async () => {
    mockData({}, "student_leg_decisions");
    const { GET } = await import("./route");
    const response = await GET(get() as never);
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain("SECRET_PROVIDER_DETAIL");
  });
});
