import { NextResponse } from "next/server";
import { optimizerFetch } from "@/lib/optimizer-server";

export async function GET() {
  try {
    const response = await optimizerFetch(`/api/v1/benchmark/param-spaces`, {
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
    console.error("[Benchmark Param Spaces API] Error:", error);
    return NextResponse.json(
      { detail: "Benchmark parametreleri alınamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
