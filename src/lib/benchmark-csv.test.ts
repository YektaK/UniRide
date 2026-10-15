import { describe, expect, it } from "vitest";
import { BENCHMARK_CSV_HEADERS, buildBenchmarkCsv } from "./benchmark-csv";

const base = {
  algorithm: "e2bso",
  problem: "berlin52",
  run_number: 1,
  tour_length: 7542 as number | null,
  elapsed_ms: 120,
  gap_percent: 0 as number | null,
  timestamp: "2026-10-15T10:00:00Z",
};

describe("buildBenchmarkCsv (M26 follow-up)", () => {
  it("keeps the existing column order and appends execution_failed and error_reason at the end", () => {
    expect(BENCHMARK_CSV_HEADERS).toEqual([
      "algorithm", "problem", "run_number", "tour_length", "elapsed_ms", "gap_percent", "timestamp",
      "execution_failed", "error_reason",
    ]);
  });

  it("marks a sota_fallback run as failed with its reason instead of a bare algorithm name", () => {
    const csv = buildBenchmarkCsv([
      { ...base, tour_length: null, gap_percent: null, metadata: { execution_failed: true, error_reason: "sota_fallback:solver_error" } },
    ]);
    const [header, line] = csv.split("\n");

    expect(header).toBe(BENCHMARK_CSV_HEADERS.join(","));
    expect(line).toBe("e2bso,berlin52,1,,120,,2026-10-15T10:00:00Z,true,sota_fallback:solver_error");
  });

  it("writes execution_failed=false and an empty reason for a successful run", () => {
    const csv = buildBenchmarkCsv([{ ...base, metadata: { execution_failed: false } }]);

    expect(csv.split("\n")[1]).toBe("e2bso,berlin52,1,7542,120,0,2026-10-15T10:00:00Z,false,");
  });

  it("leaves both new columns empty when the run carries no metadata, and escapes the reason", () => {
    const csv = buildBenchmarkCsv([
      base,
      { ...base, run_number: 2, metadata: { execution_failed: true, error_reason: 'bad, "quoted"' } },
    ]);
    const lines = csv.split("\n");

    expect(lines[1]).toBe("e2bso,berlin52,1,7542,120,0,2026-10-15T10:00:00Z,,");
    expect(lines[2]).toBe('e2bso,berlin52,2,7542,120,0,2026-10-15T10:00:00Z,true,"bad, ""quoted"""');
  });
});
