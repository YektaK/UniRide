import { NextResponse } from "next/server";

const BACKEND_URL = process.env.OPTIMIZER_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/strategies`, {
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
    console.error("[Benchmark Strategies API] Error:", error);
    return NextResponse.json(
      { detail: "Strateji listesi alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
