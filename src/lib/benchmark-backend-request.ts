type BenchmarkAlgorithmInput = {
  id?: string;
  name?: string;
  params?: Record<string, unknown>;
};

type BenchmarkSettingsInput = {
  n_runs?: number;
  nRuns?: number;
  workers?: number;
  seed?: number;
  skip_cached?: boolean;
  skipCached?: boolean;
  execution_mode?: string;
  executionMode?: string;
};

type BenchmarkRequestBody = {
  algorithms: BenchmarkAlgorithmInput[];
  problems: string[];
  settings?: BenchmarkSettingsInput;
};

export type BenchmarkBackendRequest = {
  run_id: string;
  algorithms: Array<{
    id: string | undefined;
    params: Record<string, unknown>;
  }>;
  problems: string[];
  settings: {
    n_runs: number;
    workers: number;
    seed: number;
    skip_cached: boolean;
    execution_mode?: "matrix_native" | "academic_matrix";
  };
};

function clampInteger(value: unknown, fallback: number, min: number, max: number): number {
  const numeric = typeof value === "number" && Number.isFinite(value) ? Math.trunc(value) : fallback;
  return Math.max(min, Math.min(max, numeric));
}

export function buildBenchmarkBackendRequest(body: BenchmarkRequestBody, runId: string): BenchmarkBackendRequest {
  const settings = body.settings || {};
  const nRuns = clampInteger(settings.n_runs ?? settings.nRuns, 3, 1, 10);
  const workers = clampInteger(settings.workers, 4, 1, 8);
  const seed = clampInteger(settings.seed, 42, Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER);
  const executionMode = settings.execution_mode ?? settings.executionMode;

  const backendSettings: BenchmarkBackendRequest["settings"] = {
    n_runs: nRuns,
    workers,
    seed,
    skip_cached: Boolean(settings.skip_cached ?? settings.skipCached ?? false),
  };

  if (executionMode === "matrix_native" || executionMode === "academic_matrix") {
    backendSettings.execution_mode = executionMode;
  }

  return {
    run_id: runId,
    algorithms: body.algorithms.map((algo) => ({
      id: algo.id ?? algo.name,
      params: algo.params || {},
    })),
    problems: body.problems,
    settings: backendSettings,
  };
}

