import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.OPTIMIZER_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const runId = searchParams.get("run_id");

    if (!runId) {
      return NextResponse.json(
        { detail: "run_id parametresi gerekli" },
        { status: 400 }
      );
    }

    const params = new URLSearchParams();
    params.set("run_id", runId);
    const url = `${BACKEND_URL}/api/v1/benchmark/status?${params.toString()}`;

    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      return NextResponse.json(
        { detail: `Python API error: ${response.status}`, error: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Benchmark Status API] Error:", error);
    return NextResponse.json(
      { detail: "Benchmark durumu alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
