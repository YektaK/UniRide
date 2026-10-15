/**
 * Benchmark results CSV export.
 *
 * `execution_failed` and `error_reason` come from the per-run `metadata` the
 * JSON export already carries (optimizer_api/benchmark_runner.py), so a failed
 * run or a `sota_fallback:*` run is visibly failed instead of looking like a
 * normal row with an empty tour_length.
 */

export interface BenchmarkCsvRow {
  algorithm: string;
  problem: string;
  run_number: number;
  tour_length: number | null;
  elapsed_ms: number;
  gap_percent: number | null;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

export const BENCHMARK_CSV_HEADERS = [
  "algorithm",
  "problem",
  "run_number",
  "tour_length",
  "elapsed_ms",
  "gap_percent",
  "timestamp",
  "execution_failed",
  "error_reason",
] as const;

/**
 * One CSV cell. Decided by the runtime type of the value, not by looking at the
 * text: numbers (including negative numbers) and booleans are written as is;
 * TEXT cells that begin with `=`, `+`, `-`, `@`, TAB or CR get a leading single
 * quote so a spreadsheet app shows them as text instead of running them as a
 * formula (OWASP "CSV Injection"). Only pass real numbers for numeric columns.
 */
export function escapeCSV(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return "";
  let str = String(value);
  if (typeof value === "string" && /^[=+\-@\t\r]/.test(str)) {
    str = `'${str}`;
  }
  if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function benchmarkCsvRow(r: BenchmarkCsvRow): string {
  const failed = r.metadata?.execution_failed;
  const reason = r.metadata?.error_reason;
  return [
    escapeCSV(r.algorithm),
    escapeCSV(r.problem),
    escapeCSV(r.run_number),
    escapeCSV(r.tour_length),
    escapeCSV(r.elapsed_ms),
    escapeCSV(r.gap_percent),
    escapeCSV(r.timestamp),
    escapeCSV(typeof failed === "boolean" ? failed : null),
    escapeCSV(typeof reason === "string" ? reason : null),
  ].join(",");
}

export function buildBenchmarkCsv(results: readonly BenchmarkCsvRow[]): string {
  return [BENCHMARK_CSV_HEADERS.join(","), ...results.map(benchmarkCsvRow)].join("\n");
}
