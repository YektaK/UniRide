import { afterEach, describe, expect, it, vi } from "vitest";

import { optimizeRoutes } from "./optimizer-service";

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
});
