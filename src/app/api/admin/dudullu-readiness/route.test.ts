import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { requireAdminMock, getSupabaseAdminMock, optimizerFetchMock } = vi.hoisted(() => ({
  requireAdminMock: vi.fn(),
  getSupabaseAdminMock: vi.fn(),
  optimizerFetchMock: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-auth")>(
    "@/lib/admin-auth",
  );
  return { ...actual, requireAdmin: requireAdminMock };
});

vi.mock("@/lib/supabase-admin", () => ({
  getSupabaseAdmin: getSupabaseAdminMock,
}));

vi.mock("@/lib/optimizer-server", () => ({
  optimizerFetch: optimizerFetchMock,
}));

import { AppError } from "@/lib/admin-auth";

const USER_SELECT = "id, role, location_code, disability_type, weekly_schedule_id";
const SCHEDULE_SELECT = "id, user_id, entries";
const VEHICLE_SELECT = "status, wheelchair_capacity, seating_capacity";

const UNAVAILABLE = { ready: false, reasonCodes: ["dependency_unavailable"] };

function validSummary(requiredLocationCount = 2, overrides: object = {}): object {
  const arcs = requiredLocationCount * (requiredLocationCount - 1);
  return {
    source: "supabase",
    loaded: true,
    stale: false,
    hasError: false,
    matrixLocationCount: 29,
    requiredLocationCount,
    missingRequiredLocationCount: 0,
    expectedRequiredDirectedArcCount: arcs,
    validRequiredDirectedArcCount: arcs,
    invalidOrMissingRequiredDirectedArcCount: 0,
    depotPresent: true,
    complete: true,
    ready: true,
    ...overrides,
  };
}

function adminClient(
  rows: { users?: unknown[]; schedules?: unknown[]; vehicles?: unknown[] } = {},
) {
  const selects: Array<{ table: string; columns: string }> = [];
  const from = vi.fn((table: string) => {
    return {
      select: vi.fn(
        (columns: string): Promise<{ data: unknown; error: unknown }> => {
          selects.push({ table, columns });
          const resolved =
            table === "weekly_schedules"
              ? (rows.schedules ?? [])
              : table === "vehicles"
                ? (rows.vehicles ?? [])
                : (rows.users ?? []);
          return Promise.resolve({ data: resolved, error: null });
        },
      ),
    };
  });
  return { from, selects };
}

function happyRows() {
  return {
    users: [
      {
        id: "stu-SENTINEL-9f2a",
        role: "student",
        location_code: "Sw9f2aSECRET",
        disability_type: "Sw",
        weekly_schedule_id: "sch-SENTINEL-9f2a",
      },
      { id: "drv-SENTINEL-9f2a", role: "driver", location_code: null, disability_type: null, weekly_schedule_id: null },
    ],
    schedules: [
      {
        id: "sch-SENTINEL-9f2a",
        user_id: "stu-SENTINEL-9f2a",
        entries: [
          {
            id: "cl-SENTINEL-9f2a",
            dayOfWeek: "wednesday",
            startTime: "09:00",
            endTime: "10:00",
            location: "Dudullu",
          },
        ],
      },
    ],
    vehicles: [{ status: "active", wheelchair_capacity: 1, seating_capacity: 7 }],
  };
}

function setUpForSuccess(responseBody: object = validSummary()) {
  const client = adminClient(happyRows());
  getSupabaseAdminMock.mockReturnValue(client);
  optimizerFetchMock.mockResolvedValue(
    new Response(JSON.stringify(responseBody), { status: 200 }),
  );
  requireAdminMock.mockResolvedValue({ id: "adm-SENTINEL", role: "admin" });
  return client;
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
  vi.restoreAllMocks();
});

describe("GET /api/admin/dudullu-readiness", () => {
  it("runs requireAdmin before creating the service-role client or calling FastAPI", async () => {
    const client = setUpForSuccess();
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    expect(optimizerFetchMock).not.toHaveBeenCalled();

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(200);
    expect(requireAdminMock).toHaveBeenCalledWith(expect.any(Request));
    expect(getSupabaseAdminMock).toHaveBeenCalledTimes(1);
    expect(optimizerFetchMock).toHaveBeenCalledTimes(1);
    expect(client.from).toHaveBeenCalledWith("users");
    expect(client.from).toHaveBeenCalledWith("weekly_schedules");
    expect(client.from).toHaveBeenCalledWith("vehicles");
  });

  it("returns 401 for a missing bearer token with zero Supabase/optimizer calls", async () => {
    requireAdminMock.mockRejectedValue(AppError.unauthorized());

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness"));

    expect(response.status).toBe(401);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("returns 403 for an authenticated non-admin user with zero Supabase/optimizer calls", async () => {
    requireAdminMock.mockRejectedValue(AppError.forbidden());

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer non-admin-token" },
    }));

    expect(response.status).toBe(403);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("uses the exact narrow read-only selections", async () => {
    const client = setUpForSuccess();
    const { GET } = await import("./route");
    await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    const selectNames = client.selects.map((s) => s.columns);
    expect(selectNames).toEqual([USER_SELECT, SCHEDULE_SELECT, VEHICLE_SELECT]);
    expect(selectNames).not.toContain("*");
  });

  it("sends only server-derived distinct location codes in the internal POST body", async () => {
    setUpForSuccess();
    const { GET } = await import("./route");
    await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    const [path, init] = optimizerFetchMock.mock.calls[0];
    expect(path).toBe("/api/v1/internal/readiness/time-matrix");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body);
    expect(body).toEqual({ student_location_codes: ["Sw9f2aSECRET"] });
  });

  it("signals the optimizer call with a bounded timeout", async () => {
    setUpForSuccess();
    const { GET } = await import("./route");
    await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    const [, init] = optimizerFetchMock.mock.calls[0];
    expect(init.signal).toBeInstanceOf(AbortSignal);
    expect(init.signal.aborted).toBe(false);
  });

  it("returns 200 with ready:false for ordinary data deficiencies without calling the optimizer", async () => {
    getSupabaseAdminMock.mockReturnValue(
      adminClient({
        users: [
          {
            id: "drv-DEF-9f2a",
            role: "driver",
            location_code: null,
            disability_type: null,
            weekly_schedule_id: null,
          },
        ],
        vehicles: [{ status: "active", wheelchair_capacity: 1, seating_capacity: 7 }],
      }),
    );
    requireAdminMock.mockResolvedValue({ id: "adm-x", role: "admin" });

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(200);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
    const body = await response.json();
    expect(body.ready).toBe(false);
    expect(body.reasonCodes).toEqual([
      "no_dudullu_students",
      "matrix_unavailable",
      "matrix_location_mismatch",
    ]);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("skips the optimizer and returns a deterministic 200 when zero Dudullu targets exist", async () => {
    getSupabaseAdminMock.mockReturnValue(
      adminClient({
        users: [
          {
            id: "stu-NO-9f2a",
            role: "student",
            location_code: "Çengelköy",
            disability_type: "So",
            weekly_schedule_id: "sch-NO-9f2a",
          },
          {
            id: "drv-NO-9f2a",
            role: "driver",
            location_code: null,
            disability_type: null,
            weekly_schedule_id: null,
          },
        ],
        schedules: [
          {
            id: "sch-NO-9f2a",
            user_id: "stu-NO-9f2a",
            entries: [
              {
                id: "cl-NO-9f2a",
                dayOfWeek: "wednesday",
                startTime: "10:00",
                endTime: "11:00",
                location: "Çengelköy",
              },
            ],
          },
        ],
        vehicles: [{ status: "active", wheelchair_capacity: 1, seating_capacity: 7 }],
      }),
    );
    requireAdminMock.mockResolvedValue({ id: "adm-x", role: "admin" });

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(200);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
    const body = await response.json();
    expect(body.ready).toBe(false);
    expect(body.reasonCodes).toContain("no_dudullu_students");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("sets Cache-Control to private, no-store", async () => {
    setUpForSuccess();
    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("returns the fixed redacted 503 when a Supabase query fails", async () => {
    const client = adminClient({});
    client.from.mockImplementation((_table: string) => ({
      select: vi.fn(() =>
        Promise.resolve({ data: null, error: { message: "SUPABASE-SECRET-DIAGNOSTIC" } }),
      ),
    }));
    getSupabaseAdminMock.mockReturnValue(client);
    requireAdminMock.mockResolvedValue({ id: "adm-x", role: "admin" });

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    await expect(response.json()).resolves.toEqual(UNAVAILABLE);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it("returns the fixed redacted 503 when the optimizer transport fails", async () => {
    setUpForSuccess();
    optimizerFetchMock.mockRejectedValue(new Error("OPTIMIZER-SECRET-DIAGNOSTIC"));

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    await expect(response.json()).resolves.toEqual(UNAVAILABLE);
  });

  it("returns the fixed redacted 503 when the optimizer responds non-OK", async () => {
    setUpForSuccess(validSummary());
    optimizerFetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: "X" }), { status: 422 }));

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    await expect(response.json()).resolves.toEqual(UNAVAILABLE);
  });

  it("rejects unknown and malicious upstream fields with the same redacted 503", async () => {
    for (const payload of [
      validSummary(2, { error: "BOOM" }),
      validSummary(2, { locations: ["Sw9f2aSECRET"] }),
      validSummary(2, { url: "http://secret" }),
      validSummary(2, { source: "malicious" }),
      validSummary(2, { loaded: "yes" }),
      validSummary(2, { requiredLocationCount: -1 }),
      validSummary(2, { expectedRequiredDirectedArcCount: 1.5 }),
    ]) {
      setUpForSuccess(payload);
      const { GET } = await import("./route");
      const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
        headers: { authorization: "Bearer adm-token" },
      }));

      expect(response.status).toBe(503);
      await expect(response.json()).resolves.toEqual(UNAVAILABLE);
      vi.clearAllMocks();
      vi.resetModules();
    }
  });

  it("accepts and reconstructs an exact valid summary", async () => {
    const payload = validSummary(2, { matrixLocationCount: 2 });
    setUpForSuccess(payload);

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.ready).toBe(true);
    expect(body.reasonCodes).toEqual([]);
    expect(body.students.allAccounts).toBe(1);
    expect(body.students.dudulluTarget).toBe(1);
    expect(body.historicalExpectation.isWithinDeviation).toBeUndefined();
    expect(body.matrix.requiredLocationCount).toBe(2);
    expect(body.matrix.matrixLocationCount).toBe(2);
    expect(body.matrix.expectedRequiredDirectedArcCount).toBe(2);
    expect(body.matrix.validRequiredDirectedArcCount).toBe(2);
    expect(body.matrix.depotPresent).toBe(true);
    expect(body.historicalExpectation.matchesMatrixNodeCount).toBe(false);
  });

  it("never leaks sentinel identities, locations, URLs, keys, or raw errors", async () => {
    const client = adminClient(happyRows());
    const failingClient = adminClient({});
    let supabaseCalls = 0;
    getSupabaseAdminMock.mockImplementation(() => {
      supabaseCalls += 1;
      return supabaseCalls === 1 ? client : failingClient;
    });
    optimizerFetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ...validSummary(2), error: "RAW-SUPABASE-SECRET" }), {
        status: 200,
      }),
    );
    requireAdminMock.mockResolvedValue({ id: "adm-SENTINEL", role: "admin" });

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/admin/dudullu-readiness", {
      headers: { authorization: "Bearer adm-token" },
    }));

    expect(response.status).toBe(503);
    const serialized = JSON.stringify(await response.json());
    const logs = (console.error as ReturnType<typeof vi.fn>).mock.calls
      .flat()
      .join("\n");

    for (const forbidden of [
      "stu-SENTINEL-9f2a",
      "drv-SENTINEL-9f2a",
      "adm-SENTINEL",
      "Sw9f2aSECRET",
      "sch-SENTINEL-9f2a",
      "cl-SENTINEL-9f2a",
      "http://secret",
      "RAW-SUPABASE-SECRET",
      "readyness-key",
    ]) {
      expect(serialized).not.toContain(forbidden);
      expect(logs).not.toContain(forbidden);
    }
  });
});