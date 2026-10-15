import { describe, expect, it } from "vitest";
import { BENCHMARK_CSV_HEADERS, benchmarkCsvRow, buildBenchmarkCsv, escapeCSV } from "./benchmark-csv";

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

describe("CSV formula injection (OWASP CSV Injection)", () => {
  it.each(["=1+1", "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd", "=HYPERLINK(\"http://x\",\"y\")"])(
    "prefixes the text cell %j with a single quote",
    (text) => {
      const cell = escapeCSV(text);
      const unquoted = cell.startsWith('"') ? cell.slice(1, -1).replace(/""/g, '"') : cell;
      expect(unquoted).toBe(`'${text}`);
    }
  );

  it("quotes after prefixing when the value also needs CSV quoting", () => {
    expect(escapeCSV("=A1,B1")).toBe('"\'=A1,B1"');
    expect(escapeCSV('=HYPERLINK("u")')).toBe('"\'=HYPERLINK(""u"")"');
  });

  it("leaves harmless text and quoting behaviour unchanged", () => {
    expect(escapeCSV("berlin52")).toBe("berlin52");
    expect(escapeCSV("a,b")).toBe('"a,b"');
    expect(escapeCSV("2026-10-15T10:00:00Z")).toBe("2026-10-15T10:00:00Z");
    expect(escapeCSV("sota_fallback:solver_error")).toBe("sota_fallback:solver_error");
    expect(escapeCSV("a=b")).toBe("a=b");
    expect(escapeCSV(null)).toBe("");
    expect(escapeCSV(undefined)).toBe("");
  });

  it("keeps numbers and booleans unchanged, including negative numbers", () => {
    expect(escapeCSV(-5)).toBe("-5");
    expect(escapeCSV(-0.25)).toBe("-0.25");
    expect(escapeCSV(0)).toBe("0");
    expect(escapeCSV(false)).toBe("false");
  });

  it("defuses text columns of a benchmark row but not its numeric columns", () => {
    const line = benchmarkCsvRow({
      algorithm: "=cmd|' /C calc'!A0",
      problem: "@evil",
      run_number: 1,
      tour_length: -1,
      elapsed_ms: 5,
      gap_percent: -0.5,
      timestamp: "2026-10-15T10:00:00Z",
      metadata: { execution_failed: true, error_reason: "+SUM(1)" },
    });

    expect(line).toBe("'=cmd|' /C calc'!A0,'@evil,1,-1,5,-0.5,2026-10-15T10:00:00Z,true,'+SUM(1)");
  });
});
