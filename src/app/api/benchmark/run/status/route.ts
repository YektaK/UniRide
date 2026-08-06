import { NextRequest, NextResponse } from 'next/server';
import { getOwnerToken } from '@/lib/benchmark-owner-cookie';

const BACKEND_URL = process.env.OPTIMIZER_API_URL || 'http://localhost:8000';

/**
 * GET /api/benchmark/run/status?runId=xyz
 * 
 * Get the status of a running benchmark.
 * 
 * Response:
 * {
 *   "runId": "20260410_144734_abc123",
 *   "status": "running|completed|failed",
 *   "progress": {
 *     "completed": 8,
 *     "total": 12,
 *     "percentCompleted": 66.7
 *   },
 *   "resultsCount": 8,
 *   "message": "8/12 experiment tamamlandı"
 * }
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const runId = searchParams.get('runId');

    if (!runId) {
      return NextResponse.json(
        { error: 'runId parametresi gerekli' },
        { status: 400 }
      );
    }

    // Forward to Python backend
    const ownerToken = getOwnerToken(request, runId);
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (ownerToken) headers['X-Benchmark-Owner-Token'] = ownerToken;

    const response = await fetch(
      `${BACKEND_URL}/api/v1/benchmark/status?run_id=${encodeURIComponent(runId)}`,
      { headers }
    );

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Benchmark çalışması bulunamadı' },
          { status: 404 }
        );
      }
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.error || 'Durum alınamadı' },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      runId: runId,
      status: data.status || 'running',
      progress: {
        completed: data.completed_experiments || 0,
        total: data.total_experiments || 0,
        percentCompleted: data.total_experiments 
          ? Math.round((data.completed_experiments || 0) / data.total_experiments * 100)
          : 0
      },
      resultsCount: data.results_count || 0,
      message: data.message || 'Çalışıyor...',
      lastUpdate: new Date().toISOString(),
    });

  } catch (error: any) {
    console.error('[API /api/benchmark/run/status] Error:', error);
    return NextResponse.json(
      { error: error?.message || 'Durum sorgulanılamadı' },
      { status: 500 }
    );
  }
}
