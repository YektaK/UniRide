import { describe, expect, it } from "vitest";

import { buildBenchmarkBackendRequest } from "./benchmark-backend-request";

describe("buildBenchmarkBackendRequest", () => {
  it("forwards snake_case web benchmark settings to the Python backend", () => {
    const request = buildBenchmarkBackendRequest(
      {
        algorithms: [{ id: "Core-PSO-TSP", params: { population_size: 6 } }],
        problems: ["eil51"],
        settings: {
          n_runs: 2,
          workers: 6,
          seed: 123,
          skip_cached: true,
          execution_mode: "matrix_native",
        },
      },
      "run-1"
    );

    expect(request).toEqual({
      run_id: "run-1",
      algorithms: [{ id: "Core-PSO-TSP", params: { population_size: 6 } }],
      problems: ["eil51"],
      settings: {
        n_runs: 2,
        workers: 6,
        seed: 123,
        skip_cached: true,
        execution_mode: "matrix_native",
      },
    });
  });

  it("keeps camelCase compatibility for older callers", () => {
    const request = buildBenchmarkBackendRequest(
      {
        algorithms: [{ name: "Core-Greedy-Routing" }],
        problems: ["tiny-cvrp"],
        settings: {
          nRuns: 4,
          seed: 7,
          skipCached: true,
          executionMode: "academic_matrix",
        },
      },
      "run-2"
    );

    expect(request.algorithms).toEqual([{ id: "Core-Greedy-Routing", params: {} }]);
    expect(request.settings).toEqual({
      n_runs: 4,
      workers: 4,
      seed: 7,
      skip_cached: true,
      execution_mode: "academic_matrix",
    });
  });

  it("does not forward unsupported execution modes to the backend schema", () => {
    const request = buildBenchmarkBackendRequest(
      {
        algorithms: [{ id: "Core-GA-TSP" }],
        problems: ["eil51"],
        settings: { n_runs: 1, seed: 42, execution_mode: "production_request" },
      },
      "run-3"
    );

    expect(request.settings).toEqual({
      n_runs: 1,
      workers: 4,
      seed: 42,
      skip_cached: false,
    });
  });
});

