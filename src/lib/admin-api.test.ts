import { afterEach, describe, expect, it, vi } from "vitest";
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";

const { getSupabaseClientMock } = vi.hoisted(() => ({
  getSupabaseClientMock: vi.fn(),
}));

vi.mock("./supabase", () => ({
  getSupabaseClient: getSupabaseClientMock,
}));

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((next, fail) => {
    resolve = next;
    reject = fail;
  });
  return { promise, reject, resolve };
}

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

describe("getAuthToken cache invalidation", () => {
  it("ignores an old acquisition without overwriting or detaching the current generation", async () => {
    const oldSession = deferred<{
      data: { session: { access_token: string; expires_at: number } };
      error: null;
    }>();
    const newSession = deferred<{
      data: { session: { access_token: string; expires_at: number } };
      error: null;
    }>();
    const getSession = vi.fn()
      .mockReturnValueOnce(oldSession.promise)
      .mockReturnValueOnce(newSession.promise);
    getSupabaseClientMock.mockReturnValue({
      auth: { getSession, refreshSession: vi.fn() },
    });
    const { clearAuthTokenCache, getAuthToken } = await import("./admin-api");
    clearAuthTokenCache();

    const oldAcquisition = getAuthToken();
    clearAuthTokenCache();
    const currentAcquisition = getAuthToken();

    oldSession.resolve({
      data: {
        session: {
          access_token: "old-token",
          expires_at: Math.floor(Date.now() / 1000) + 3600,
        },
      },
      error: null,
    });
    await expect(oldAcquisition).resolves.toBeNull();

    const sharedCurrentAcquisition = getAuthToken();
    expect(getSession).toHaveBeenCalledTimes(2);

    newSession.resolve({
      data: {
        session: {
          access_token: "new-token",
          expires_at: Math.floor(Date.now() / 1000) + 3600,
        },
      },
      error: null,
    });
    await expect(currentAcquisition).resolves.toBe("new-token");
    await expect(sharedCurrentAcquisition).resolves.toBe("new-token");
    await expect(getAuthToken()).resolves.toBe("new-token");
    expect(getSession).toHaveBeenCalledTimes(2);
  });
});

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

  it("removes the token-wait abort listener after token acquisition settles", async () => {
    const addEventListener = vi.fn();
    const removeEventListener = vi.fn();
    const signal = {
      aborted: false,
      reason: undefined,
      addEventListener,
      removeEventListener,
    } as unknown as AbortSignal;
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout").mockReturnValue(signal);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validReadinessReport,
    }));
    const adminApi = await readinessApi();

    await adminApi.readiness.getDudullu();

    expect(addEventListener).toHaveBeenCalledWith("abort", expect.any(Function), { once: true });
    expect(removeEventListener).toHaveBeenCalledWith("abort", addEventListener.mock.calls[0][1]);
    timeoutSpy.mockRestore();
  });

  it("rejects an already-aborted readiness signal without calling fetch", async () => {
    const controller = new AbortController();
    controller.abort(new Error("sensitive abort reason"));
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
    const getSession = vi.fn().mockReturnValue(new Promise(() => undefined));
    getSupabaseClientMock.mockReturnValue({ auth: { getSession } });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { adminApi, clearAuthTokenCache } = await import("./admin-api");
    clearAuthTokenCache();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });
    expect(fetchMock).not.toHaveBeenCalled();

    clearAuthTokenCache();
    timeoutSpy.mockRestore();
  });

  it("cleans up the signal listener when token acquisition rejects", async () => {
    const controller = new AbortController();
    const addEventListener = vi.spyOn(controller.signal, "addEventListener");
    const removeEventListener = vi.spyOn(controller.signal, "removeEventListener");
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
    getSupabaseClientMock.mockImplementationOnce(() => {
      throw new Error("sensitive client initialization failure");
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { adminApi, clearAuthTokenCache } = await import("./admin-api");
    clearAuthTokenCache();

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });

    expect(addEventListener).toHaveBeenCalledWith("abort", expect.any(Function), { once: true });
    expect(removeEventListener).toHaveBeenCalledWith("abort", addEventListener.mock.calls[0][1]);
    expect(fetchMock).not.toHaveBeenCalled();
    timeoutSpy.mockRestore();
  });

  it.each(["resolve", "reject"] as const)(
    "keeps one redacted abort outcome when token acquisition later %ss",
    async (settlement) => {
      const session = deferred<{
        data: { session: { access_token: string; expires_at: number } };
        error: null;
      }>();
      getSupabaseClientMock.mockReturnValue({
        auth: { getSession: vi.fn().mockReturnValue(session.promise) },
      });
      const controller = new AbortController();
      const addEventListener = vi.spyOn(controller.signal, "addEventListener");
      const removeEventListener = vi.spyOn(controller.signal, "removeEventListener");
      const timeoutSpy = vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const { adminApi, clearAuthTokenCache } = await import("./admin-api");
      clearAuthTokenCache();

      const outcomes: string[] = [];
      const outcome = adminApi.readiness.getDudullu().then(
        () => {
          outcomes.push("resolved");
          return undefined;
        },
        (error) => {
          outcomes.push("rejected");
          return error;
        },
      );

      controller.abort(new Error("sensitive abort reason"));
      if (settlement === "resolve") {
        session.resolve({
          data: {
            session: {
              access_token: "late-token",
              expires_at: Math.floor(Date.now() / 1000) + 3600,
            },
          },
          error: null,
        });
      } else {
        session.reject(new Error("late token acquisition failure"));
      }

      await expect(outcome).resolves.toMatchObject({
        kind: "configuration",
        message: "Dudullu readiness request failed",
      });
      await Promise.resolve();
      await Promise.resolve();

      expect(outcomes).toEqual(["rejected"]);
      expect(fetchMock).not.toHaveBeenCalled();
      expect(removeEventListener).toHaveBeenCalledWith("abort", addEventListener.mock.calls[0][1]);

      clearAuthTokenCache();
      consoleErrorSpy.mockRestore();
      timeoutSpy.mockRestore();
    },
  );

  it("classifies a missing session as an authorization failure", async () => {
    const adminApi = await readinessApi(false);

    await expect(adminApi.readiness.getDudullu()).rejects.toMatchObject({
      kind: "authorization",
      message: "Dudullu readiness request failed",
    });
  });

  it("bounds unresolved token acquisition with the readiness deadline", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const timeoutSpy = vi.spyOn(AbortSignal, "timeout").mockImplementation((milliseconds) => {
      setTimeout(() => controller.abort(), milliseconds);
      return controller.signal;
    });
    const getSession = vi.fn().mockReturnValue(new Promise(() => undefined));
    getSupabaseClientMock.mockReturnValue({
      auth: { getSession },
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { adminApi, clearAuthTokenCache } = await import("./admin-api");
    clearAuthTokenCache();

    let settled = false;
    let failure: unknown;
    void adminApi.readiness.getDudullu().then(
      () => { settled = true; },
      (error) => { settled = true; failure = error; },
    );

    await vi.advanceTimersByTimeAsync(14_999);
    expect(settled).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    expect(settled).toBe(true);
    expect(failure).toMatchObject({
      kind: "configuration",
      message: "Dudullu readiness request failed",
    });
    expect(fetchMock).not.toHaveBeenCalled();
    timeoutSpy.mockRestore();
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

describe("adminApi.vehicles.calculate", () => {
  const validStudent = {
    id: "student-1",
    name: "Student One",
    location_code: "Sw1",
    disability_type: "Sw",
  };

  const calculationResult = (direction: "pickup" | "dropoff") => ({
    success: true,
    direction,
    requiredVehicles: 1,
    assignments: [{
      vehicleIndex: 1,
      students: [validStudent],
      route: [],
      totalDuration: 30,
      swCount: 1,
      soCount: 0,
    }],
    totalDuration: 30,
    message: "1 vehicle(s) used for optimization",
    meta: {
      calculationTimeMs: 12,
      inputStudentCount: 1,
      validStudentCount: 1,
      algorithmUsed: "genetic_algorithm",
      executionTimeSeconds: 0.1,
      options: {
        maxTourTime: 120,
        swCapacity: 4,
        soCapacity: 5,
        strategy: "genetic_algorithm",
        clusteringAlgorithm: "sweep",
      },
    },
  });

  it.each(["pickup", "dropoff"] as const)("sends %s calculations with bearer authentication", async (direction) => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => calculationResult(direction),
    });
    vi.stubGlobal("fetch", fetchMock);
    const adminApi = await readinessApi();

    await expect(adminApi.vehicles.calculate({
      students: [validStudent],
      direction,
    })).resolves.toEqual(calculationResult(direction));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/calculate-vehicles",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      }),
    );
    expect(fetchMock.mock.calls[0][1].headers).toEqual(expect.objectContaining({
      "Content-Type": "application/json",
    }));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      students: [validStudent],
      direction,
    });
  });

  it("preserves compatibility for calculations without a direction", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => calculationResult("pickup"),
    });
    vi.stubGlobal("fetch", fetchMock);
    const adminApi = await readinessApi();

    await expect(adminApi.vehicles.calculate({ students: [validStudent] })).resolves.toEqual(calculationResult("pickup"));

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ students: [validStudent] });
  });

  it("rejects calculations without an authenticated session", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const adminApi = await readinessApi(false);

    await expect(adminApi.vehicles.calculate({ students: [validStudent] })).rejects.toMatchObject({
      name: "AdminApiAuthenticationError",
      message: "Not authenticated",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a non-OK calculation response", async () => {
    const json = vi.fn().mockResolvedValue({ error: "internal optimizer secret" });
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, json });
    vi.stubGlobal("fetch", fetchMock);
    const adminApi = await readinessApi();

    const error = await adminApi.vehicles.calculate({ students: [validStudent] }).catch((caught) => caught as Error);
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe("Vehicle calculation failed");
    expect(error.message).not.toContain("internal optimizer secret");
    expect(json).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
