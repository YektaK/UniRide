import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const StopBenchmarkRequestSchema = z.object({
  run_id: z.string().min(1, "run_id gerekli"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = StopBenchmarkRequestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { detail: "Geçersiz istek", errors: parsed.error.flatten().fieldErrors },
        { status: 400 }
      );
    }

    const { run_id } = parsed.data;

    // Use gateway proxy: relative path + XTransformPort for Python API (port 8000)
    const params = new URLSearchParams();
    params.set("run_id", run_id);
    const pythonPath = `/api/v1/benchmark/stop?${params.toString()}&XTransformPort=8099`;

    const response = await fetch(pythonPath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id }),
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
    console.error("[Benchmark Stop API] Error:", error);
    return NextResponse.json(
      { detail: "Benchmark durdurulamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
