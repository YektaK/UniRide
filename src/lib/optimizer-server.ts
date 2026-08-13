import "server-only";

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