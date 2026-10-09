import { NextResponse } from "next/server";
import { handleApiError, requireAdmin } from "@/lib/admin-auth";

/**
 * Gate for every /api/benchmark/* handler (audit C4, BFF half).
 * Returns null when the caller is an admin; otherwise the same error
 * body/status the /api/admin/* routes produce (401 anonymous, 403 non-admin).
 */
export async function denyUnlessBenchmarkAdmin(request: Request): Promise<NextResponse | null> {
  try {
    await requireAdmin(request);
    return null;
  } catch (error) {
    const failure = handleApiError(error);
    return NextResponse.json(await failure.json(), { status: failure.status });
  }
}
