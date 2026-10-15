import { describe, expect, it } from "vitest";
import {
  SOLVER_PROVENANCE_KEYS,
  buildSolverProvenance,
  solverProvenanceSchema,
} from "./solver-provenance";

describe("solverProvenanceSchema (what a client may store)", () => {
  it("accepts the allowlisted keys", () => {
    const value = {
      algorithm_requested: "ga_split",
      algorithm_used: "ga_split",
      fallback_reason: "solver_error",
      effective_config_source: "promoted+request",
      effective_seed: 42,
    };
    expect(solverProvenanceSchema.parse(value)).toEqual(value);
  });

  it("accepts a subset (missing fields are simply absent)", () => {
    expect(solverProvenanceSchema.parse({ effective_seed: 7 })).toEqual({ effective_seed: 7 });
  });

  it("rejects unknown keys", () => {
    expect(solverProvenanceSchema.safeParse({ effective_seed: 1, note: "x" }).success).toBe(false);
  });

  it("rejects an empty object", () => {
    expect(solverProvenanceSchema.safeParse({}).success).toBe(false);
  });

  it.each([
    ["non-integer seed", { effective_seed: 1.5 }],
    ["string seed", { effective_seed: "42" }],
    ["null seed", { effective_seed: null }],
    ["overlong algorithm", { algorithm_used: "a".repeat(65) }],
    ["overlong fallback reason", { fallback_reason: "r".repeat(201) }],
    ["empty string", { algorithm_requested: "" }],
    ["markup in a string", { effective_config_source: "<script>alert(1)</script>" }],
    ["nested object", { algorithm_used: { a: 1 } }],
  ])("rejects %s", (_label, value) => {
    expect(solverProvenanceSchema.safeParse(value).success).toBe(false);
  });

  it("lists exactly the allowlisted keys", () => {
    expect([...SOLVER_PROVENANCE_KEYS].sort()).toEqual([
      "algorithm_requested",
      "algorithm_used",
      "effective_config_source",
      "effective_seed",
      "fallback_reason",
    ]);
  });
});

describe("buildSolverProvenance", () => {
  it("reads the BFF meta of a calculation", () => {
    expect(
      buildSolverProvenance(
        {
          meta: {
            algorithmRequested: "ga_split",
            effectiveConfigSource: "default",
            effectiveSeed: 42,
          },
        },
        "ga_split",
      ),
    ).toEqual({
      algorithm_requested: "ga_split",
      algorithm_used: "ga_split",
      effective_config_source: "default",
      effective_seed: 42,
    });
  });

  it("prefers the optimizer-reported algorithm that ran over the caller's selection", () => {
    expect(
      buildSolverProvenance(
        { meta: { algorithmUsed: "ga_split", effectiveSeed: 42 } },
        "genetic_algorithm",
      ),
    ).toEqual({ algorithm_used: "ga_split", effective_seed: 42 });
  });

  it("falls back to the caller's calculation-time choice when the optimizer did not report it", () => {
    expect(buildSolverProvenance({ meta: { effectiveSeed: 42 } }, "genetic_algorithm")).toEqual({
      algorithm_used: "genetic_algorithm",
      effective_seed: 42,
    });
  });

  it("reads the raw optimizer fields too", () => {
    expect(
      buildSolverProvenance(
        { algorithm_requested: "e2bso", fallback_reason: "solver_error" },
        "greedy_fallback",
      ),
    ).toEqual({
      algorithm_requested: "e2bso",
      algorithm_used: "greedy_fallback",
      fallback_reason: "solver_error",
    });
  });

  it("omits what the optimizer did not report and never invents a key", () => {
    const value = buildSolverProvenance({ meta: { effectiveSeed: 3 } }, "ga_split");
    expect(value).toEqual({ algorithm_used: "ga_split", effective_seed: 3 });
    expect(value).not.toHaveProperty("fallback_reason");
    expect(value).not.toHaveProperty("effective_config_source");
    expect(value).not.toHaveProperty("algorithm_requested");
  });

  it("is null when the optimizer reported no provenance (older optimizer)", () => {
    expect(buildSolverProvenance({ meta: { algorithmUsed: "ga" } }, "ga")).toBeNull();
    expect(buildSolverProvenance({}, "ga")).toBeNull();
  });

  it("drops a malformed reported field instead of storing it", () => {
    const value = buildSolverProvenance(
      { meta: { effectiveSeed: 1.5, effectiveConfigSource: "default" } },
      "ga_split",
    );
    expect(value).toEqual({ algorithm_used: "ga_split", effective_config_source: "default" });
  });

  it("is null when every reported field is malformed", () => {
    expect(buildSolverProvenance({ meta: { effectiveSeed: "x" } }, "ga")).toBeNull();
  });
});
