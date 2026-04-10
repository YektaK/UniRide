import { NextResponse } from 'next/server';

const BENCHMARK_SERVICE_URL = 'http://localhost:3003';

export async function POST() {
  try {
    const response = await fetch(`${BENCHMARK_SERVICE_URL}/stop`, {
      method: 'POST',
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || 'Deney durdurulamadı', code: data.code },
        { status: response.status }
      );
    }

    return NextResponse.json({
      status: data.status,
      runId: data.runId,
      completedExperiments: data.completedExperiments,
      totalExperiments: data.totalExperiments,
      message: data.message,
    });
  } catch (error) {
    console.error('[API /benchmark/run/stop] Error:', error);
    return NextResponse.json(
      { error: 'Benchmark servisine bağlanılamadı' },
      { status: 503 }
    );
  }
}
