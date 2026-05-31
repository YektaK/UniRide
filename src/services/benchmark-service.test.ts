import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchAcademicProblems } from "./benchmark-service";

describe("benchmark-service academic problems", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches academic DB problems with routing metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        source: "academic_db",
        count: 1,
        limit: 10,
        results: [
          {
            name: "solomon-r101",
            dimension: 101,
            optimal: null,
            category: "medium",
            edge_weight_type: "EUC_2D",
            problem_type: "CVRPTW",
            matrix_kind: "coordinates",
            has_time_windows: true,
            has_service_times: true,
            num_vehicles: 25,
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const problems = await fetchAcademicProblems({
      problem_type: "CVRPTW",
      category: "medium",
      limit: 10,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/academic/problems?problem_type=CVRPTW&category=medium&limit=10",
      expect.objectContaining({ method: "GET" })
    );
    expect(problems).toHaveLength(1);
    expect(problems[0]).toMatchObject({
      name: "solomon-r101",
      problem_type: "CVRPTW",
      matrix_kind: "coordinates",
      has_time_windows: true,
      num_vehicles: 25,
      source: "academic_db",
      available: true,
    });
  });
});
