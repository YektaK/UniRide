import "server-only";

import { NextResponse } from "next/server";

import { OPTIMIZER_API_URL } from "@/lib/config";

export async function optimizerFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const key = process.env.OPTIMIZER_INTERNAL_API_KEY;
  if (!key?.trim()) throw new Error("Optimizer service is not configured");

  try {
    const headers = new Headers(init.headers);
    headers.set("X-Internal-API-Key", key);
    const baseUrl = OPTIMIZER_API_URL.replace(/\/+$/, "");
    const endpoint = path.startsWith("/") ? path : `/${path}`;
    return await fetch(`${baseUrl}${endpoint}`, { ...init, headers, redirect: "error" });
  } catch {
    throw new Error("Optimizer service request failed");
  }
}
/** Fixed error code for "the optimizer process does not host the academic/benchmark router" (audit H8). */
export const ACADEMIC_SERVICE_DISABLED = "ACADEMIC_SERVICE_DISABLED";

/**
 * The optimizer mounts its benchmark router only when UNIRIDE_ACADEMIC_PROCESS=1.
 * Unmounted, every benchmark path answers FastAPI's default 404 {"detail":"Not Found"}
 * (the router's own 404s carry a different detail, e.g. "Benchmark run x not found").
 * Returns a 503 with a fixed code for that case, otherwise null so the caller continues.
 * The body is read from a clone, so the caller can still consume the original response.
 */
export async function academicServiceDisabledResponse(response: Response): Promise<NextResponse | null> {
  if (response.status !== 404) return null;
  try {
    const source = typeof response.clone === "function" ? response.clone() : response;
    const body = (await source.json()) as { detail?: unknown } | null;
    if (body?.detail !== "Not Found") return null;
  } catch {
    return null;
  }
  return NextResponse.json(
    {
      code: ACADEMIC_SERVICE_DISABLED,
      error: "Academic benchmark service is disabled on this server",
      detail: "Academic benchmark service is disabled on this server",
    },
    { status: 503 }
  );
}
