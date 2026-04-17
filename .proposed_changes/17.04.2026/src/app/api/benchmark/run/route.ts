import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const RunBenchmarkRequestSchema = z.object({
  run_id: z.string().min(1, "run_id gerekli"),
  algorithms: z.array(z.object({
    id: z.string().min(1, "Algoritma ID gerekli"),
    params: z.record(z.unknown()).optional(),
  })).min(1, "En az bir algoritma seçilmeli"),
  problems: z.array(z.string().min(1, "Problem adı gerekli")).min(1, "En az bir problem seçilmeli"),
  settings: z.object({
    n_runs: z.number().int().min(1).max(100).default(3),
    seed: z.number().int().default(42),
    skip_cached: z.boolean().default(false),
  }).default({}),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = RunBenchmarkRequestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { detail: "Geçersiz istek", errors: parsed.error.flatten().fieldErrors },
        { status: 400 }
      );
    }

    const { run_id, algorithms, problems, settings } = parsed.data;

    // Use gateway proxy: relative path + XTransformPort for Python API (port 8000)
    const params = new URLSearchParams();
    params.set("run_id", run_id);

    const pythonPath = `/api/v1/benchmark/run?${params.toString()}&XTransformPort=8099`;

    const response = await fetch(pythonPath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id,
        algorithms,
        problems,
        settings,
      }),
      signal: AbortSignal.timeout(30000),
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
    console.error("[Benchmark Run API] Error:", error);
    return NextResponse.json(
      { detail: "Benchmark başlatılamadı", error: error instanceof Error ? error.message : "Unknown" },
      { status: 503 }
    );
  }
}
