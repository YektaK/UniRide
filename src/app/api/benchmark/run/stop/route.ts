import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.OPTIMIZER_API_URL || 'http://localhost:8000';

/**
 * POST /api/benchmark/run/stop
 * 
 * Stop a running benchmark.
 * 
 * Request body:
 * {
 *   "runId": "20260410_144734_abc123"
 * }
 * 
 * Response:
 * {
 *   "runId": "20260410_144734_abc123",
 *   "status": "stopped",
 *   "resultsCollected": 8,
 *   "message": "Benchmark durduruldu"
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const { runId } = await request.json();

    if (!runId) {
      return NextResponse.json(
        { error: 'runId gerekli' },
        { status: 400 }
      );
    }

    // Forward to Python backend
    const response = await fetch(`${BACKEND_URL}/api/v1/benchmark/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_id: runId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.error || 'Durdurma başarısız' },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      runId: runId,
      status: 'stopped',
      resultsCollected: data.results_collected || 0,
      message: 'Benchmark durduruldu',
      stoppedAt: new Date().toISOString(),
    });

  } catch (error: any) {
    console.error('[API /api/benchmark/run/stop] Error:', error);
    return NextResponse.json(
      { error: error?.message || 'Durdurma işlemi başarısız' },
      { status: 500 }
    );
  }
}
