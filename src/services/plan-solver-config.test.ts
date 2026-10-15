import { describe, expect, it } from "vitest";
import { buildPlanSolverConfig, collectSolverConfig, solverSourceLabelKey } from "./plan-solver-config";

describe("collectSolverConfig (H17: which settings and seed produced the plan)", () => {
  it("returns null when no optimizer call was made", () => {
    expect(collectSolverConfig([])).toBeNull();
  });

  it("collects the distinct source and seed values of the optimizer calls", () => {
    expect(collectSolverConfig([
      { effective_config_source: "default", effective_seed: 42 },
      { effective_config_source: "default", effective_seed: 42 },
    ])).toEqual({ sources: ["default"], seeds: [42] });
  });

  it("keeps different values apart and marks a call that reported nothing as null", () => {
    expect(collectSolverConfig([
      { effective_config_source: "default", effective_seed: 42 },
      { effective_config_source: "promoted", effective_seed: 7 },
      {},
    ])).toEqual({ sources: ["default", "promoted", null], seeds: [42, 7, null] });
  });
});

describe("buildPlanSolverConfig", () => {
  it("is null for a response without the field (older server) and when nothing was reported", () => {
    expect(buildPlanSolverConfig(undefined)).toBeNull();
    expect(buildPlanSolverConfig(null)).toBeNull();
    expect(buildPlanSolverConfig({ sources: [null], seeds: [null] })).toBeNull();
    expect(buildPlanSolverConfig({ sources: [], seeds: [] })).toBeNull();
  });

  it("reports a single source and seed", () => {
    expect(buildPlanSolverConfig({ sources: ["default"], seeds: [42] })).toEqual({
      source: { kind: "single", value: "default" },
      seed: { kind: "single", value: 42 },
    });
  });

  it("reports mixed when calls differ, never picks one", () => {
    expect(buildPlanSolverConfig({ sources: ["default", "promoted"], seeds: [42] })).toEqual({
      source: { kind: "mixed" },
      seed: { kind: "single", value: 42 },
    });
    expect(buildPlanSolverConfig({ sources: ["default"], seeds: [42, 43] })?.seed).toEqual({ kind: "mixed" });
  });

  it("reports mixed when only some calls reported a value", () => {
    expect(buildPlanSolverConfig({ sources: ["default", null], seeds: [42, null] })).toEqual({
      source: { kind: "mixed" },
      seed: { kind: "mixed" },
    });
  });

  it("keeps a field on its own when the other one is missing", () => {
    expect(buildPlanSolverConfig({ sources: ["promoted"], seeds: [null] })).toEqual({
      source: { kind: "single", value: "promoted" },
      seed: null,
    });
  });
});

describe("solverSourceLabelKey", () => {
  it.each([
    ["default", "default"], ["request", "request"], ["promoted", "promoted"], ["promoted+request", "promotedRequest"],
  ])("maps the optimizer value %s to %s", (raw, key) => {
    expect(solverSourceLabelKey(raw)).toBe(key);
  });

  it("returns null for an unknown value so the page shows the raw text", () => {
    expect(solverSourceLabelKey("experimental")).toBeNull();
  });
});
