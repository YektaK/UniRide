import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const optimizerFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: optimizerFetchMock }));

import { fetchWithRetry } from "./multi-vehicle-routing";

describe("DouBus optimizer retry transport", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.useRealTimers());
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
  it("retries a rejected authenticated request without changing request options", async () => {
    vi.useFakeTimers();
    optimizerFetchMock
      .mockRejectedValueOnce(new Error("temporary failure"))
      .mockResolvedValueOnce(new Response(null, { status: 200 }));
    const request: RequestInit = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    };

    const result = fetchWithRetry("/api/v1/optimize", request, 10_000, 1);
    await vi.runAllTimersAsync();
    await expect(result).resolves.toMatchObject({ status: 200 });

    expect(optimizerFetchMock).toHaveBeenCalledTimes(2);
    for (const [, init] of optimizerFetchMock.mock.calls as [string, RequestInit][]) {
      expect(init).toMatchObject({ method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    }
  });

  it("does not retry after caller cancellation", async () => {
    const caller = new AbortController();
    caller.abort();
    optimizerFetchMock.mockRejectedValue(new Error("caller cancelled"));

    await expect(fetchWithRetry("/api/v1/optimize", { signal: caller.signal }, 10_000, 2)).rejects.toThrow("API request failed");

    expect(optimizerFetchMock).toHaveBeenCalledTimes(1);
  });
});