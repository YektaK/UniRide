import { NextRequest, NextResponse } from 'next/server';
import { getOwnerToken } from '@/lib/benchmark-owner-cookie';
import { optimizerFetch } from "@/lib/optimizer-server";

/**
 * GET /api/benchmark/results/[runId]
 *
 * Fetch the full results of a completed benchmark run.
 * Proxies to Python: GET /api/v1/benchmark/results/{run_id}
 *
 * Response (from Python):
 * {
 *   "run_id": "benchmark_20260414_xxxxx",
 *   "status": "completed",
 *   "results_count": 12,
 *   "total_experiments": 12,
 *   "message": "...",
 *   "parameters": { ... },
 *   "results": [ { ... }, ... ]
 * }
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;

  if (!runId || typeof runId !== 'string') {
    return NextResponse.json(
      { error: 'Geçersiz benchmark run ID' },
      { status: 400 }
    );
  }

  try {
    const ownerToken = getOwnerToken(request, runId);
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (ownerToken) headers['X-Benchmark-Owner-Token'] = ownerToken;

    const response = await optimizerFetch(
      `/api/v1/benchmark/results/${encodeURIComponent(runId)}`,
      {
        method: 'GET',
        headers,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || 'Benchmark sonuçları alınamadı' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error(`[API /api/benchmark/results/${runId}] Error:`, error);
    return NextResponse.json(
      {
        error: 'Benchmark sonuçlarına ulaşılamadı',
        details: error?.message,
      },
      { status: 500 }
    );
  }
}
