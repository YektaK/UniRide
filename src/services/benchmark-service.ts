import { generateBenchmarkRunId } from "@/lib/benchmark-run-id";

/**
 * Benchmark Service
 * TSPLIB benchmark suite service for running systematic algorithm comparisons
 * All API calls use relative paths with ?XTransformPort for gateway proxy
 */

// ============================================================
// Types
// ============================================================

export interface BenchmarkProblem {
  name: string;
  dimension: number;
  optimal: number | null;
  category: "small" | "medium" | "large";
  problem_type: string;
  edge_weight_type: string;
  available: boolean;
  comment?: string;
}

export interface BenchmarkAlgorithm {
  id: string;
  params?: Record<string, unknown>;
}

export interface BenchmarkParamSpec {
  type: "bool" | "int" | "float" | "string";
  default?: unknown;
  doe?: unknown[];
  optuna?: [number, number] | null;
  source?: string;
}

export type BenchmarkParamSpace = Record<string, BenchmarkParamSpec>;

export interface BenchmarkParamSpacesResponse {
  spaces: Record<string, BenchmarkParamSpace>;
  production_spaces?: Record<string, BenchmarkParamSpace>;
  academic_spaces?: Record<string, BenchmarkParamSpace>;
}

export interface BenchmarkRunSettings {
  n_runs: number;
  seed: number;
}

export interface BenchmarkStatus {
  run_id: string;
  status: "running" | "completed" | "failed" | "stopped" | "queued";
  total_experiments: number;
  completed_experiments: number;
  results_count: number;
  message: string;
  progress_percent: number;
  start_time: string;
  end_time: string | null;
}

export interface BenchmarkResult {
  algorithm: string;
  problem: string;
  run_number: number;
  tour_length: number;
  elapsed_ms: number;
  gap_percent: number | null;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface AcademicBenchmarkResult {
  id: number;
  problem: string;
  algorithm: string;
  params: Record<string, unknown>;
  tour: number[];
  tour_length: number;
  gap: number | null;
  dimension?: number | null;
  category?: string | null;
  timestamp: string;
}

export interface AcademicLeaderboardResponse {
  source: "academic_db";
  count: number;
  limit: number;
  results: AcademicBenchmarkResult[];
}

export interface AcademicBestResultResponse {
  source: "academic_db";
  problem: string;
  algorithm: string;
  result: AcademicBenchmarkResult | null;
}

export interface BenchmarkResultsResponse {
  run_id: string;
  status: string;
  total_experiments: number;
  results: BenchmarkResult[];
  summary?: {
    algorithms: Record<string, {
      avg_gap: number;
      min_gap: number;
      max_gap: number;
      avg_time_ms: number;
      best_known: number;
      success_rate: number;
    }>;
    problems: Record<string, {
      best_algorithm: string;
      best_tour_length: number;
      optimal?: number;
      gap_from_optimal: number | null;
    }>;
  };
}

export interface BenchmarkRunResponse {
  run_id: string;
  status: string;
  message: string;
  total_experiments: number;
}

// ============================================================
// API Functions
// ============================================================

// All benchmark calls go through Next.js API routes which proxy to OPTIMIZER_API_URL.
// No XTransformPort gateway pattern needed here.
const BENCHMARK_API_BASE = "/api/benchmark";

/**
 * Fetch available TSPLIB problems
 */
export async function fetchProblems(category?: string): Promise<BenchmarkProblem[]> {
  const params = new URLSearchParams();
  if (category) {
    params.set("category", category);
  }

  const response = await fetch(
    `${BENCHMARK_API_BASE}/problems${params.toString() ? `?${params.toString()}` : ""}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(15000),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail || `Problemler alınamadı: ${response.status}`
    );
  }

  const data = await response.json();
  return (data.problems || data || []) as BenchmarkProblem[];
}

/**
 * Fetch available strategies from Python API
 */
export async function fetchStrategies(): Promise<string[]> {
  const response = await fetch(`${BENCHMARK_API_BASE}/strategies`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    throw new Error("Stratejiler alınamadı");
  }

  const data = await response.json();
  // The strategies endpoint may return an array of objects or strings
  if (Array.isArray(data)) {
    return data.map((s: string | { name: string }) => typeof s === "string" ? s : s.name);
  }
  if (data.strategies && Array.isArray(data.strategies)) {
    return data.strategies.map((s: string | { name: string }) => typeof s === "string" ? s : s.name);
  }
  return [];
}

/**
 * Fetch editable algorithm parameter spaces for quick benchmark runs
 */
export async function fetchParamSpaces(): Promise<BenchmarkParamSpacesResponse> {
  const response = await fetch(`${BENCHMARK_API_BASE}/param-spaces`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    throw new Error("Parametre alanları alınamadı");
  }

  const data = await response.json();
  return {
    spaces: data.spaces || {},
    production_spaces: data.production_spaces || {},
    academic_spaces: data.academic_spaces || {},
  };
}

/**
 * Start a benchmark run
 */
export async function startBenchmark(
  algorithms: BenchmarkAlgorithm[],
  problems: string[],
  settings: BenchmarkRunSettings
): Promise<BenchmarkRunResponse> {
  const runId = generateBenchmarkRunId();

  const response = await fetch(`${BENCHMARK_API_BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_id: runId,
      algorithms,
      problems,
      settings,
    }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail || `Benchmark başlatılamadı: ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Poll benchmark status
 */
export async function pollStatus(runId: string): Promise<BenchmarkStatus> {
  const params = new URLSearchParams();
  params.set("run_id", runId);

  const response = await fetch(`${BENCHMARK_API_BASE}/status?${params.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail || `Durum alınamadı: ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Stop a running benchmark
 */
export async function stopBenchmark(runId: string): Promise<void> {
  const response = await fetch(`${BENCHMARK_API_BASE}/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId }),
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail || `Benchmark durdurulamadı: ${response.status}`
    );
  }
}

/**
 * Fetch benchmark results
 */
export async function fetchResults(runId: string): Promise<BenchmarkResultsResponse> {
  const response = await fetch(`${BENCHMARK_API_BASE}/results/${encodeURIComponent(runId)}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      (errorData as { detail?: string }).detail || `Sonuçlar alınamadı: ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Fetch read-only academic DB leaderboard results
 */
export async function fetchAcademicLeaderboard(options: {
  algorithm?: string;
  category?: string;
  limit?: number;
} = {}): Promise<AcademicLeaderboardResponse> {
  const params = new URLSearchParams();
  if (options.algorithm) params.set("algorithm", options.algorithm);
  if (options.category) params.set("category", options.category);
  if (options.limit) params.set("limit", String(options.limit));

  const response = await fetch(
    `${BENCHMARK_API_BASE}/academic/leaderboard${params.toString() ? `?${params.toString()}` : ""}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(10000),
    }
  );

  if (!response.ok) {
    throw new Error(`Akademik leaderboard alınamadı: ${response.status}`);
  }

  return await response.json();
}

/**
 * Fetch the academic DB best known result for a problem/algorithm pair
 */
export async function fetchAcademicBestResult(
  problem: string,
  algorithm: string
): Promise<AcademicBestResultResponse> {
  const params = new URLSearchParams({ problem, algorithm });
  const response = await fetch(`${BENCHMARK_API_BASE}/academic/best?${params.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    throw new Error(`Akademik sonuç alınamadı: ${response.status}`);
  }

  return await response.json();
}
