import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

vi.mock("server-only", () => ({}));

beforeEach(() => {
  process.env.OPTIMIZER_INTERNAL_API_KEY = "test-key";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete process.env.OPTIMIZER_INTERNAL_API_KEY;
});

describe("POST /api/benchmark/stop", () => {
  it("forwards the owner token, injects the internal key, and sends run_id as a query param", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, opts?: RequestInit) => {
        capturedUrl = url;
        capturedHeaders = Object.fromEntries(new Headers(opts?.headers).entries());
        return { ok: true, status: 200, json: async () => ({ run_id: "run-1", status: "stopped" }), text: async () => "" };
      })
    );

    const req = new NextRequest("http://x/api/benchmark/stop", {
      method: "POST",
      headers: { "content-type": "application/json", cookie: "benchmark_owner_stop-1=STOPTOKEN" },
      body: JSON.stringify({ run_id: "stop-1" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(capturedUrl).toContain("/api/v1/benchmark/stop?run_id=stop-1");
    expect(capturedHeaders["x-benchmark-owner-token"]).toBe("STOPTOKEN");
    expect(capturedHeaders["x-internal-api-key"]).toBe("test-key");
  });
});
