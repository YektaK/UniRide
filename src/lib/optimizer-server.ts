import "server-only";

import { OPTIMIZER_API_URL } from "@/lib/config";

export async function optimizerFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const key = process.env.OPTIMIZER_INTERNAL_API_KEY;
  if (!key) throw new Error("Optimizer service is not configured");

  const headers = new Headers(init.headers);
  headers.set("X-Internal-API-Key", key);
  return fetch(`${OPTIMIZER_API_URL}${path}`, { ...init, headers });
}
