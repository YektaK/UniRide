import { NextResponse } from "next/server";
import { optimizerFetch } from "@/lib/optimizer-server";

export async function GET() {
  try {
    const response = await optimizerFetch(`/health`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", message: `Python API error: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Health Proxy API] Error:", error);
    return NextResponse.json(
      { 
        status: "down", 
        message: "Python API is not reachable",
        error: error instanceof Error ? error.message : "Unknown error" 
      },
      { status: 503 }
    );
  }
}
