import { NextRequest, NextResponse } from 'next/server';

const BENCHMARK_SERVICE_URL = 'http://localhost:3003';

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
    const nRuns = settings.nRuns ?? 3;
    const workers = settings.workers ?? 4;
    const seed = settings.seed ?? 42;
    const skipCached = settings.skipCached ?? true;

    // Build the config for the mini-service
    const config = {
      algorithms: body.algorithms.map((algo: { id: string; params?: Record<string, number | string> }) => ({
        id: algo.id,
        params: algo.params || {},
      })),
      problems: body.problems,
      settings: {
        n_runs: Number(nRuns),
        workers: Number(workers),
        seed: Number(seed),
        skip_cached: Boolean(skipCached),
      },
    };

    // Forward to benchmark runner mini-service
    const response = await fetch(`${BENCHMARK_SERVICE_URL}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || 'Deney başlatılamadı', code: data.code },
        { status: response.status }
      );
    }

    return NextResponse.json({
      runId: data.runId,
      totalExperiments: data.totalExperiments,
      status: data.status,
      message: data.message,
    });
  } catch (error) {
    console.error('[API /benchmark/run] Error:', error);
    return NextResponse.json(
      { error: 'Benchmark servisine bağlanılamadı' },
      { status: 503 }
    );
  }
}
