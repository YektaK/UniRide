import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

const optimizerFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: optimizerFetchMock }));

import { fetchWithRetry } from "./multi-vehicle-routing";

describe("DouBus optimizer retry transport", () => {
  it("preserves an already-aborted caller signal and request options", async () => {
    const caller = new AbortController();
    caller.abort();
    optimizerFetchMock.mockResolvedValue(new Response(null, { status: 200 }));

    await fetchWithRetry(
      "/api/v1/optimize",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}", signal: caller.signal },
      1000,
      0,
    );

    const [, init] = optimizerFetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe("{}");
    expect(init.signal?.aborted).toBe(true);
  });

  it("uses native timeout signals instead of retaining manual timeout controllers", () => {
    const source = readFileSync("src/services/doubus/multi-vehicle-routing.ts", "utf8");
    const retrySource = source.slice(source.indexOf("async function fetchWithRetry"), source.indexOf("/**", source.indexOf("async function fetchWithRetry") + 1));

    expect(retrySource).toContain("AbortSignal.timeout");
    expect(retrySource).toContain("AbortSignal.any");
    expect(retrySource).not.toContain("new AbortController");
    expect(retrySource).not.toContain("clearTimeout(timeoutId)");
  });
});