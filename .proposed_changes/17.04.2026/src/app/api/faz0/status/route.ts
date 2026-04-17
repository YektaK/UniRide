import { NextResponse } from "next/server";

export async function GET() {
  try {
    // Check optimizer API health
    let apiOnline = false;
    try {
      const healthRes = await fetch(
        "http://localhost:8099/health",
        {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        }
      );
      apiOnline = healthRes.ok;
    } catch {
      apiOnline = false;
    }

    const faz0Modules = [
      "MultiStartInitializer",
      "MultiLayerLS",
      "PenaltyManager",
      "AcceptanceCriterion",
      "DestroyOperators",
      "RepairOperators",
      "DiversityController",
      "sota_common",
    ];

    return NextResponse.json({
      api_online: apiOnline,
      faz0_modules: faz0Modules,
      version: "0.1.0",
    });
  } catch {
    return NextResponse.json(
      { error: "Status check failed" },
      { status: 500 }
    );
  }
}
