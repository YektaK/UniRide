import { NextResponse } from 'next/server';

const BENCHMARK_SERVICE_URL = 'http://localhost:3003';

export async function GET() {
  try {
    const response = await fetch(`${BENCHMARK_SERVICE_URL}/status`, {
      method: 'GET',
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || 'Durum alınamadı' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('[API /benchmark/run/status] Error:', error);
    return NextResponse.json(
      { error: 'Benchmark servisine bağlanılamadı' },
      { status: 503 }
    );
  }
}
