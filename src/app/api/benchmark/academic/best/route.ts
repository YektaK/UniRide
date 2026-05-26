import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.OPTIMIZER_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    const problem = searchParams.get("problem");
    const algorithm = searchParams.get("algorithm");
    if (problem) params.set("problem", problem);
    if (algorithm) params.set("algorithm", algorithm);

    const response = await fetch(`${BACKEND_URL}/api/v1/benchmark/academic/best?${params.toString()}`, {
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

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("[Academic Best Result API] Error:", error);
    return NextResponse.json(
      { detail: "Akademik en iyi sonuç alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
