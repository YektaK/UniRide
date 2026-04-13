/**
 * Benchmark Service
 * TSPLIB benchmark suite service for running systematic algorithm comparisons
 * All API calls use relative paths with ?XTransformPort=8000 for gateway proxy
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

const PYTHON_API_BASE = "/api/v1/benchmark";

/**
 * Fetch available TSPLIB problems
 */
export async function fetchProblems(category?: string): Promise<BenchmarkProblem[]> {
  const params = new URLSearchParams();
  params.set("XTransformPort", "8099");
  if (category) {
    params.set("category", category);
  }

  const response = await fetch(`${PYTHON_API_BASE}/problems?${params.toString()}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(15000),
  });

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
  const params = new URLSearchParams();
  params.set("XTransformPort", "8099");

  const response = await fetch(`/api/v1/strategies?${params.toString()}`, {
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
 * Start a benchmark run
 */
export async function startBenchmark(
  algorithms: BenchmarkAlgorithm[],
  problems: string[],
  settings: BenchmarkRunSettings
): Promise<BenchmarkRunResponse> {
  const runId = `bench_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const params = new URLSearchParams();
  params.set("XTransformPort", "8099");
  params.set("run_id", runId);

  const response = await fetch(`${PYTHON_API_BASE}/run?${params.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
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
  params.set("XTransformPort", "8099");
  params.set("run_id", runId);

  const response = await fetch(`${PYTHON_API_BASE}/status?${params.toString()}`, {
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
  const params = new URLSearchParams();
  params.set("XTransformPort", "8099");
  params.set("run_id", runId);

  const response = await fetch(`${PYTHON_API_BASE}/stop?${params.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const params = new URLSearchParams();
  params.set("XTransformPort", "8099");

  const response = await fetch(`${PYTHON_API_BASE}/results/${runId}?${params.toString()}`, {
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
