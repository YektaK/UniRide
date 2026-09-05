import { afterEach, describe, expect, it, vi } from "vitest";
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";

const { getSupabaseClientMock } = vi.hoisted(() => ({
  getSupabaseClientMock: vi.fn(),
}));

vi.mock("./supabase", () => ({
  getSupabaseClient: getSupabaseClientMock,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("adminApi.routes.optimize", () => {
  it("preserves local search settings in the authenticated BFF request", async () => {
    getSupabaseClientMock.mockReturnValue({
      auth: {
        getSession: vi.fn().mockResolvedValue({
          data: {
            session: {
              access_token: "test-token",
              expires_at: Math.floor(Date.now() / 1000) + 3600,
            },
          },
          error: null,
        }),
      },
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { adminApi, clearAuthTokenCache } = await import("./admin-api");
    clearAuthTokenCache();

    await adminApi.routes.optimize({
      start: "D.Kampus",
      end: "D.Kampus",
      waypoints: ["Sw1"],
      strategy: "genetic_algorithm",
      local_search_type: "or_opt",
      max_travel_time: 180,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/optimize-route",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      local_search_type: "or_opt",
      max_travel_time: 180,
    });
  });
});

const validReadinessReport: DudulluReadinessReport = {
  ready: true,
  reasonCodes: [],
  students: {
    allAccounts: 28,
    dudulluTarget: 28,
    nonDudulluScheduled: 0,
    unclassifiedSchedule: 0,
    completeTargetProfiles: 28,
    targetMissingLocation: 0,
    targetMissingDisabilityType: 0,
    scheduleLinkMismatch: 0,
    distinctTargetLocations: 28,
  },
  schedules: {
    total: 28,
    empty: 0,
    malformed: 0,
    orphanedRows: 0,
    duplicateRowsForStudent: 0,
  },
  fleet: {
    configuredDrivers: 1,
    vehicles: 1,
    activeVehicles: 1,
    usableActiveVehicles: 1,
  },
  matrix: {
    source: "supabase",
    loaded: true,
    stale: false,
    hasError: false,
    matrixLocationCount: 29,
    complete: true,
    ready: true,
    requiredLocationCount: 29,
    expectedRequiredDirectedArcCount: 812,
    validRequiredDirectedArcCount: 812,
    missingRequiredLocationCount: 0,
    invalidOrMissingRequiredDirectedArcCount: 0,
    depotPresent: true,
  },
  historicalExpectation: {
    studentCount: 28,
    matrixNodeCount: 29,
    matchesStudentCount: true,
    matchesMatrixNodeCount: true,
  },
};

async function readinessApi(session = true) {
  getSupabaseClientMock.mockReturnValue({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: session
            ? {
                access_token: "test-token",
                expires_at: Math.floor(Date.now() / 1000) + 3600,
              }
            : null,
        },
        error: null,
      }),
    },
  });
  const { adminApi, clearAuthTokenCache } = await import("./admin-api");
  clearAuthTokenCache();
  return adminApi;
}

describe("adminApi.readiness.getDudullu", () => {
  it("uses an authenticated no-store request and validates the report", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validReadinessReport,
    });
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout");
    vi.stubGlobal("fetch", fetchMock);
    const adminApi = await readinessApi();

    await expect(adminApi.readiness.getDudullu()).resolves.toEqual(validReadinessReport);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/dudullu-readiness",
      expect.objectContaining({
        method: "GET",
        cache: "no-store",
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      }),
    );
    expect(timeoutSpy).toHaveBeenCalledWith(15_000);
    timeoutSpy.mockRestore();
  });

  it("classifies a missing session as an authorization failure", async () => {
    const adminApi = await readinessApi(false);

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "authorization",
      message: "Dudullu readiness request failed",
    });
  });

  it.each([401, 403])("classifies HTTP %i as an authorization failure without parsing its body", async (status) => {
    const json = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status, json }));
    const adminApi = await readinessApi();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "authorization",
      message: "Dudullu readiness request failed",
    });
    expect(json).not.toHaveBeenCalled();
  });

  it.each([500, 503])("classifies HTTP %i as a configuration failure without parsing its body", async (status) => {
    const json = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status, json }));
    const adminApi = await readinessApi();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });
    expect(json).not.toHaveBeenCalled();
  });

  it.each([
    new Error("network unavailable"),
    new DOMException("request aborted", "AbortError"),
  ])("classifies fetch failures as configuration failures", async (error) => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
    const adminApi = await readinessApi();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });
  });

  it.each([
    async () => {
      throw new SyntaxError("invalid JSON");
    },
    async () => ({ ...validReadinessReport, reasonCodes: ["unexpected_reason"] }),
  ])("classifies invalid successful response content as a configuration failure", async (json) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json }));
    const adminApi = await readinessApi();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });
  });
});
