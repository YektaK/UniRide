import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
process.env.OPTIMIZER_INTERNAL_API_KEY = "server-secret";

import { compareAllAlgorithms, optimizeRoutes } from "./optimizer-service";

describe("optimizer-service optimizeRoutes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves IE raw data returned by the optimizer API", async () => {
    const ieData = {
      hourly_demand: {
        "08:00": {
          sw: { pickup: 1 },
          so: { dropoff: 2 },
        },
      },
      bottlenecks: [{ time: "08:00", type: "infeasible", reason: "capacity" }],
      time_shift_suggestions: [{ student_id: "s1", current_time: "08:00", suggested_time: "08:15" }],
      standard_vehicles_needed: 3,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        algorithm_used: "genetic_algorithm",
        routes: [],
        total_vehicles: 1,
        total_duration_minutes: 20,
        execution_time_seconds: 0.5,
        ie_data: ieData,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await optimizeRoutes(
      [
        {
          id: "s1",
          name: "Student 1",
          location_code: "L1",
          disability_type: "Sw",
        },
      ],
      { id: "depot", lat: 40, lng: 29 }
    );

    expect(result.ie_data).toEqual(ieData);
  });

  it("preserves optimizer metadata for optimized routes", async () => {
    const metadata = {
      algorithm_requested: "ga",
      feasibility_certificate: { feasible: true },
      applied_policy: { profile_id: "default", student_count: 1, vehicle_count: 1, cancellation_mode: "none", limits: {} },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "genetic_algorithm", routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5, ...metadata }),
    }));

    const result = await optimizeRoutes([{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" }], { id: "depot", lat: 40, lng: 29 });

    expect(result).toMatchObject(metadata);
  });

  it("sanitizes transport failures while retaining backend solver certificates", async () => {
    const secret = "server-secret";
    vi.stubGlobal("fetch", vi.fn()
      .mockRejectedValueOnce(new Error(`connection refused at http://internal.example with ${secret}`))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          algorithm_used: "ga",
          routes: [],
          total_vehicles: 0,
          total_duration_minutes: 0,
          execution_time_seconds: 0,
          error_message: "infeasible",
          algorithm_requested: "requested-ga",
          feasibility_certificate: { feasible: false },
          applied_policy: { profile_id: "small", student_count: 1, vehicle_count: 1, cancellation_mode: "none", limits: {} },
        }),
      }));
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const input = [{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" as const }];
    const depot = { id: "depot", lat: 40, lng: 29 };

    const unavailable = await optimizeRoutes(input, depot);
    const infeasible = await optimizeRoutes(input, depot);

    expect(unavailable).toMatchObject({ success: false, error_message: "Optimization unavailable" });
    expect(JSON.stringify(unavailable)).not.toContain(secret);
    expect(JSON.stringify(unavailable)).not.toContain("internal.example");
    expect(infeasible).toMatchObject({
      success: false,
      error_message: "infeasible",
      algorithm_requested: "requested-ga",
      feasibility_certificate: { feasible: false },
    });
  });
  it.each([
    [503, "travel-time matrix unavailable", "travel_time_matrix_unavailable"],
    [422, "requested locations are missing from the travel-time matrix", "travel_time_matrix_locations_missing"],
  ])("maps the optimizer's fail-closed %i matrix response to an explicit redacted error", async (status, detail, code) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: async () => ({ detail }),
    }));
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    const result = await optimizeRoutes([{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" }], { id: "depot", lat: 40, lng: 29 });

    expect(result).toMatchObject({ success: false, routes: [], total_vehicles: 0, error_code: code });
    expect(result.error_message).not.toBe("Optimization unavailable");
    expect(result.error_message).toBeTruthy();
    expect(JSON.stringify(result)).not.toContain("L1");
  });

  it("keeps other 422 and 503 optimizer errors on the generic unavailable path", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ detail: "students cannot exceed 60" }) })
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: "something else" }) }));
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const input = [{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" as const }];
    const depot = { id: "depot", lat: 40, lng: 29 };

    const policy = await optimizeRoutes(input, depot);
    const other = await optimizeRoutes(input, depot);

    expect(policy).toMatchObject({ success: false, error_message: "Optimization unavailable" });
    expect(policy.error_code).toBeUndefined();
    expect(other.error_code).toBeUndefined();
  });

  it("maps a fail-closed matrix response from /compare to an explicit error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "travel-time matrix unavailable" }),
    }));
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    const result = await compareAllAlgorithms([{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" }], { id: "depot", lat: 40, lng: 29 });

    expect(result).toMatchObject({ success: false, results: [], error_code: "travel_time_matrix_unavailable" });
    expect(result.error_message).toBeTruthy();
  });

  it("preserves optimizer metadata for algorithm comparisons", async () => {
    const metadata = {
      algorithm_requested: "gwo",
      feasibility_certificate: { feasible: true },
      applied_policy: { profile_id: "default", student_count: 1, vehicle_count: 1, cancellation_mode: "none", limits: {} },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, results: [{ algorithm: "gwo", success: true, routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5, ...metadata }], best_algorithm: "gwo", fastest_algorithm: "gwo", summary: {}, ...metadata }),
    }));

    const result = await compareAllAlgorithms([{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" }], { id: "depot", lat: 40, lng: 29 });

    expect(result).toMatchObject(metadata);
    expect(result.results[0]).toMatchObject(metadata);
  });
});

describe("optimizer-service SOTA fallback labelling (M26)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const students = [{ id: "s1", name: "Student 1", location_code: "L1", disability_type: "Sw" as const }];
  const depot = { id: "depot", lat: 40, lng: 29 };

  it("surfaces greedy_fallback and the reason code from the optimizer", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        algorithm_used: "greedy_fallback",
        algorithm_requested: "e2bso",
        fallback_reason: "solver_error",
        routes: [],
        total_vehicles: 1,
        total_duration_minutes: 20,
        execution_time_seconds: 0.5,
      }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).toMatchObject({
      algorithm_used: "greedy_fallback",
      algorithm_requested: "e2bso",
      fallback_reason: "solver_error",
    });
  });

  it("forwards the effective config source and seed when the optimizer reports them (H17)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "ga_split", effective_config_source: "default", effective_seed: 42, routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5 }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).toMatchObject({ effective_config_source: "default", effective_seed: 42 });
  });

  it("forwards termination_reason and solver_code_version when the optimizer reports them (A20 L2/L3)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "e2bso", termination_reason: "wall_clock_deadline", solver_code_version: "3f2a9c1", routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5 }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).toMatchObject({ termination_reason: "wall_clock_deadline", solver_code_version: "3f2a9c1" });
  });

  it("omits termination_reason and solver_code_version when the optimizer reports none", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "ga", routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5 }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).not.toHaveProperty("termination_reason");
    expect(result).not.toHaveProperty("solver_code_version");
  });

  it("omits the effective config keys when the optimizer reports none", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "ga", routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5 }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).not.toHaveProperty("effective_config_source");
    expect(result).not.toHaveProperty("effective_seed");
  });

  it("omits fallback_reason when the requested algorithm ran", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, algorithm_used: "e2bso", routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5 }),
    }));

    const result = await optimizeRoutes(students, depot);

    expect(result).not.toHaveProperty("fallback_reason");
  });

  it("surfaces the executed algorithm for a fallback comparison result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        results: [{ algorithm: "e2bso", success: true, routes: [], total_vehicles: 1, total_duration_minutes: 20, execution_time_seconds: 0.5, algorithm_executed: "greedy_fallback", fallback_reason: "solver_error" }],
        best_algorithm: "",
        fastest_algorithm: "",
        summary: {},
      }),
    }));

    const result = await compareAllAlgorithms(students, depot);

    expect(result.results[0]).toMatchObject({ algorithm: "e2bso", algorithm_executed: "greedy_fallback", fallback_reason: "solver_error" });
  });
});
