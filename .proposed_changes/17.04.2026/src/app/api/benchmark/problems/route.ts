import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");

    // Build query params - forward category filter
    const params = new URLSearchParams();
    if (category) params.set("category", category);

    // Use gateway proxy: relative path + XTransformPort for Python API (port 8000)
    const pythonPath = `/api/v1/benchmark/problems${params.toString() ? `?${params.toString()}&` : "?"}XTransformPort=8099`;

    const response = await fetch(pythonPath, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(15000),
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
    console.error("[Benchmark Problems API] Error:", error);
    return NextResponse.json(
      { detail: "Benchmark sunucusuna ulaşılamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
