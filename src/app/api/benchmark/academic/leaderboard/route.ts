import { NextRequest, NextResponse } from "next/server";
import { optimizerFetch } from "@/lib/optimizer-server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    for (const key of ["algorithm", "category", "limit"]) {
      const value = searchParams.get(key);
      if (value) params.set(key, value);
    }

    const response = await optimizerFetch(
      `/api/v1/benchmark/academic/leaderboard${params.toString() ? `?${params.toString()}` : ""}`,
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
    console.error("[Academic Leaderboard API] Error:", error);
    return NextResponse.json(
      { detail: "Akademik sonuçlar alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
