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
