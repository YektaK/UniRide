import { NextRequest, NextResponse } from 'next/server';
import { generateBenchmarkRunId, isValidBenchmarkRunId } from '@/lib/benchmark-run-id';

const BACKEND_URL = process.env.OPTIMIZER_API_URL || 'http://localhost:8000';

/**
 * POST /api/benchmark/run
 * 
 * Start a new benchmark experiment.
 * 
 * Request body:
 * {
 *   "algorithms": [
 *     { "id": "genetic_algorithm", "params": { ... } },
 *     { "id": "pso", "params": { ... } }
 *   ],
 *   "problems": [
 *     "tsp_50_1",
 *     "tsp_100_1"
 *   ],
 *   "settings": {
 *     "nRuns": 3,
 *     "workers": 4,
 *     "seed": 42,
 *     "skipCached": false
 *   }
 * }
 * 
 * Response:
 * {
 *   "runId": "20260410_144734_abc123",
 *   "totalExperiments": 12,
 *   "status": "running",
 *   "message": "Benchmark başlatıldı"
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate algorithms
    if (!body.algorithms || !Array.isArray(body.algorithms) || body.algorithms.length === 0) {
      return NextResponse.json(
        { error: 'En az bir algoritma seçilmelidir' },
        { status: 400 }
      );
    }

    // Validate problems
    if (!body.problems || !Array.isArray(body.problems) || body.problems.length === 0) {
      return NextResponse.json(
        { error: 'En az bir problem seçilmelidir' },
        { status: 400 }
      );
    }

    // Validate settings
    const settings = body.settings || {};
    const nRuns = Math.max(1, Math.min(10, settings.nRuns ?? 3));
    const workers = Math.max(1, Math.min(8, settings.workers ?? 4));
    const seed = settings.seed ?? 42;
    const skipCached = Boolean(settings.skipCached ?? false);

    // Use caller-provided run ID if available; otherwise generate one
    const now = new Date();
    const providedRunIdRaw = body.run_id ?? body.runId;
    const providedRunId = typeof providedRunIdRaw === 'string' ? providedRunIdRaw.trim() : '';
    if (providedRunId && !isValidBenchmarkRunId(providedRunId)) {
      return NextResponse.json(
        {
          error: 'Geçersiz run_id formatı. Sadece harf, rakam, "_" ve "-" kullanılabilir (maksimum 64 karakter).',
        },
        { status: 400 }
      );
    }

    if (providedRunId) {
      try {
        const statusResponse = await fetch(
          `${BACKEND_URL}/api/v1/benchmark/status?run_id=${encodeURIComponent(providedRunId)}`,
          { method: 'GET' }
        );

        if (statusResponse.ok) {
          return NextResponse.json(
            { error: 'Bu run_id zaten kullanılıyor. Lütfen farklı bir run_id deneyin.' },
            { status: 409 }
          );
        }

        if (statusResponse.status !== 404) {
          return NextResponse.json(
            { error: 'run_id doğrulaması sırasında backend erişim hatası oluştu.' },
            { status: 502 }
          );
        }
      } catch {
        return NextResponse.json(
          { error: 'run_id doğrulaması sırasında backend erişim hatası oluştu.' },
          { status: 502 }
        );
      }
    }

    const runId = providedRunId || generateBenchmarkRunId(now);

    // Build benchmark request for Python backend
    const benchmarkRequest = {
      run_id: runId,
      algorithms: body.algorithms.map((algo: any) => ({
        id: algo.id,
        params: algo.params || {},
      })),
      problems: body.problems,
      settings: {
        n_runs: nRuns,
        workers: workers,
        seed: seed,
        skip_cached: skipCached,
      },
    };

    // Forward to Python backend
    console.log(`[Benchmark /api/benchmark/run] Starting: ${runId}`);
    
    const response = await fetch(`${BACKEND_URL}/api/v1/benchmark/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(benchmarkRequest),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      console.error(`[Benchmark] Backend error:`, error);
      return NextResponse.json(
        { 
          error: error.error || 'Benchmark servisine bağlanılamadı',
          code: error.code 
        },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      run_id: runId,
      total_experiments: body.algorithms.length * body.problems.length * nRuns,
      problems_count: body.problems.length,
      algorithms_count: body.algorithms.length,
      n_runs: nRuns,
      status: 'running',
      message: 'Benchmark başlatıldı',
      start_time: now.toISOString(),
    });

  } catch (error: any) {
    console.error('[API /api/benchmark/run] Error:', error);
    return NextResponse.json(
      { 
        error: error?.message || 'Benchmark başlatılamadı',
        details: error?.toString?.()
      },
      { status: 500 }
    );
  }
}
