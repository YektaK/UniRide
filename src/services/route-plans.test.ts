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

  it("saves the algorithm that actually ran when the optimizer served a fallback (M26)", () => {
    const fallbackResult = {
      ...validResult,
      algorithm_used: "greedy_fallback",
      algorithm_requested: "e2bso",
      fallback_reason: "solver_error",
    };

    const saved = formatRoutePlanForSave(fallbackResult, "2026-09-08", "pickup", "e2bso", "sweep");

    expect(saved.algorithmUsed).toBe("greedy_fallback");
  });

  it("saves the algorithm that actually ran from the BFF meta of a fallback", () => {
    const bffResult = {
      ...validResult,
      meta: { algorithmUsed: "greedy_fallback", algorithmRequested: "e2bso", fallbackReason: "solver_error" },
    } as unknown as Parameters<typeof formatRoutePlanForSave>[0];

    const saved = formatRoutePlanForSave(bffResult, "2026-09-08", "pickup", "e2bso", "sweep");

    expect(saved.algorithmUsed).toBe("greedy_fallback");
  });

  it("keeps the selected strategy when no fallback happened", () => {
    const saved = formatRoutePlanForSave(
      { ...validResult, meta: { algorithmUsed: "e2bso" } } as unknown as Parameters<typeof formatRoutePlanForSave>[0],
      "2026-09-08", "pickup", "e2bso", "sweep",
    );

    expect(saved.algorithmUsed).toBe("e2bso");
  });
});
