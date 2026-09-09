import { describe, expect, it } from "vitest";
import type { OptimizationResult } from "@/services/optimizer-service";
import { formatRoutePlanForSave } from "./route-plans";

const validResult: OptimizationResult = {
  success: true,
  algorithm_used: "ga",
  routes: [{ vehicle_id: "vehicle-1", route_details: [], total_duration_minutes: 30, total_distance_km: 5, sw_count: 0, so_count: 1, student_ids: ["student-1"] }],
  total_vehicles: 1,
  total_duration_minutes: 30,
  execution_time_seconds: 1,
  direction: "pickup",
};

describe("formatRoutePlanForSave", () => {
  it.each(["pickup", "dropoff"] as const)("uses a valid matching %s result direction", (direction) => {
    const result = formatRoutePlanForSave(
      { ...validResult, direction },
      "2026-09-08",
      direction,
      "ga",
      "sweep",
    );

    expect(result.direction).toBe(direction);
  });

  it("blocks a result without a direction", () => {
    const { direction: _, ...resultWithoutDirection } = validResult;

    expect(() => formatRoutePlanForSave(
      resultWithoutDirection,
      "2026-09-08",
      "pickup",
      "ga",
      "sweep",
    )).toThrow("Calculation result has no valid direction; save is blocked");
  });

  it("blocks an invalid result direction", () => {
    type SaveInput = Parameters<typeof formatRoutePlanForSave>[0];
    const malformed = { ...validResult, direction: "sideways" } as unknown as SaveInput;

    expect(() => formatRoutePlanForSave(
      malformed,
      "2026-09-08",
      "pickup",
      "ga",
      "sweep",
    )).toThrow("Calculation result has no valid direction; save is blocked");
  });

  it("blocks a result direction that conflicts with the requested direction", () => {
    expect(() => formatRoutePlanForSave(
      { ...validResult, direction: "dropoff" },
      "2026-09-08",
      "pickup",
      "ga",
      "sweep",
    )).toThrow("Calculation result direction does not match the requested direction");
  });
});
