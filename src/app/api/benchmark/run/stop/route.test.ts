import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("POST /api/benchmark/run/stop", () => {
  it("forwards the owner token and sends run_id as a query param", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, opts?: RequestInit) => {
        capturedUrl = url;
        capturedHeaders = (opts?.headers as Record<string, string>) || {};
        return {
          ok: true,
          status: 200,
          json: async () => ({ run_id: "run-1", results_collected: 5 }),
          text: async () => "",
        };
      })
    );

    const req = new NextRequest("http://x/api/benchmark/run/stop", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        cookie: "benchmark_owner_stop-1=STOPTOKEN",
      },
      body: JSON.stringify({ runId: "stop-1" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(capturedUrl).toContain("/api/v1/benchmark/stop?run_id=stop-1");
    expect(capturedHeaders["X-Benchmark-Owner-Token"]).toBe("STOPTOKEN");
  });
});
