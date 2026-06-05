import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/benchmark-run-id", () => ({
  generateBenchmarkRunId: () => "bench-test-run",
}));

import {
  checkBenchmarkApiHealth,
  fetchAcademicBestResult,
  fetchAcademicLeaderboard,
  fetchAcademicProblems,
  fetchResults,
  pollStatus,
  startBenchmark,
} from "./benchmark-service";

describe("benchmark-service academic problems", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("checks benchmark API health through the Next proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await expect(checkBenchmarkApiHealth()).resolves.toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/health",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("reports benchmark API health as false when proxy fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(checkBenchmarkApiHealth()).resolves.toBe(false);
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

  it("starts benchmark runs with generated run id and requested payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        run_id: "bench-test-run",
        status: "queued",
        message: "queued",
        total_experiments: 2,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await startBenchmark(
      [{ id: "Core-Greedy-Routing", params: { max_iterations: 10 } }],
      ["smoke-cvrp"],
      { n_runs: 2, seed: 42 }
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          run_id: "bench-test-run",
          algorithms: [{ id: "Core-Greedy-Routing", params: { max_iterations: 10 } }],
          problems: ["smoke-cvrp"],
          settings: { n_runs: 2, seed: 42 },
        }),
      })
    );
    expect(result.run_id).toBe("bench-test-run");
  });

  it("polls status with URL-encoded run id", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        run_id: "run id/1",
        status: "running",
        total_experiments: 1,
        completed_experiments: 0,
        results_count: 0,
        message: "running",
        progress_percent: 0,
        start_time: "2026-06-01T00:00:00Z",
        end_time: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await pollStatus("run id/1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/status?run_id=run+id%2F1",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("throws API detail when starting a benchmark fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "invalid benchmark request" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      startBenchmark([{ id: "Core-Greedy-Routing" }], ["missing"], { n_runs: 1, seed: 1 })
    ).rejects.toThrow("invalid benchmark request");
  });

  it("throws API detail when fetching benchmark results fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "run not found" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchResults("missing/run")).rejects.toThrow("run not found");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/results/missing%2Frun",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("fetches academic leaderboard with optional filters", async () => {
    const payload = {
      source: "academic_db",
      count: 1,
      results: [
        {
          problem: "ulysses22",
          algorithm: "Core-TwoOpt-TSP",
          category: "small",
          best_gap: 0.1,
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAcademicLeaderboard({
      algorithm: "Core TwoOpt/TSP",
      category: "small",
      limit: 25,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/academic/leaderboard?algorithm=Core+TwoOpt%2FTSP&category=small&limit=25",
      expect.objectContaining({ method: "GET" })
    );
    expect(result).toEqual(payload);
  });

  it("throws status error when academic leaderboard fetch fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchAcademicLeaderboard()).rejects.toThrow("Akademik leaderboard alınamadı: 503");
  });

  it("fetches academic best result with encoded problem and algorithm", async () => {
    const payload = {
      source: "academic_db",
      problem: "solomon/r101",
      algorithm: "OR-Tools",
      result: { objective_cost: 123.4 },
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAcademicBestResult("solomon/r101", "OR Tools");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/benchmark/academic/best?problem=solomon%2Fr101&algorithm=OR+Tools",
      expect.objectContaining({ method: "GET" })
    );
    expect(result).toEqual(payload);
  });

  it("throws status error when academic best result fetch fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchAcademicBestResult("missing", "algorithm")).rejects.toThrow(
      "Akademik sonuç alınamadı: 404"
    );
  });
});
