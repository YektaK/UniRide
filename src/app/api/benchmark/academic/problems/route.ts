import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.OPTIMIZER_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    for (const key of ["problem_type", "category", "max_dim", "limit"]) {
      const value = searchParams.get(key);
      if (value) params.set(key, value);
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/benchmark/academic/problems${params.toString() ? `?${params.toString()}` : ""}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        signal: AbortSignal.timeout(10000),
      }
    );

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      return NextResponse.json(
        { detail: `Python API error: ${response.status}`, error: errorText },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("[Academic Problems API] Error:", error);
    return NextResponse.json(
      { detail: "Akademik problem listesi alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
