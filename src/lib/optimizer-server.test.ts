import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

async function loadOptimizerFetch(baseUrl = DEFAULT_BASE_URL) {
  vi.resetModules();
  vi.doMock("server-only", () => ({}));
  vi.doMock("@/lib/config", () => ({ OPTIMIZER_API_URL: baseUrl }));
  return (await import("./optimizer-server")).optimizerFetch;
}

describe("optimizerFetch", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    process.env.OPTIMIZER_INTERNAL_API_KEY = "server-secret";
  });

  afterEach(() => vi.resetModules());

  it("injects the key without changing caller headers", async () => {
    const optimizerFetch = await loadOptimizerFetch();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const callerHeaders = new Headers({ "Content-Type": "application/json" });
    await optimizerFetch("/api/v1/optimize", { method: "POST", headers: callerHeaders });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Internal-API-Key")).toBe("server-secret");
    expect(callerHeaders.get("X-Internal-API-Key")).toBeNull();
  });

  it("fails before fetch when the server key is missing", async () => {
    const optimizerFetch = await loadOptimizerFetch();
    delete process.env.OPTIMIZER_INTERNAL_API_KEY;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(optimizerFetch("/api/v1/optimize", { method: "POST" }))
      .rejects.toThrow("Optimizer service is not configured");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("overrides a hostile caller key and rejects redirects without mutating the caller", async () => {
    const optimizerFetch = await loadOptimizerFetch();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const callerHeaders = new Headers({ "X-Internal-API-Key": "hostile" });
    await optimizerFetch("/api/v1/optimize", { headers: callerHeaders, redirect: "follow" });
    const init = fetchMock.mock.calls[0][1];
    expect((init.headers as Headers).get("X-Internal-API-Key")).toBe("server-secret");
    expect(callerHeaders.get("X-Internal-API-Key")).toBe("hostile");
    expect(init.redirect).toBe("error");
  });

  it("rejects whitespace keys before fetch", async () => {
    const optimizerFetch = await loadOptimizerFetch();
    process.env.OPTIMIZER_INTERNAL_API_KEY = "   ";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(optimizerFetch("/api/v1/optimize")).rejects.toThrow("Optimizer service is not configured");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("normalizes a configured trailing base slash to exactly one path separator", async () => {
    const optimizerFetch = await loadOptimizerFetch("http://optimizer.internal/");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    await optimizerFetch("/api/v1/optimize");
    expect(fetchMock.mock.calls[0][0]).toBe("http://optimizer.internal/api/v1/optimize");
  });

  it("does not leak a malformed internal key when header construction fails", async () => {
    const optimizerFetch = await loadOptimizerFetch();
    const secret = "bad\nsecret";
    process.env.OPTIMIZER_INTERNAL_API_KEY = secret;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(optimizerFetch("/api/v1/optimize")).rejects.toThrow("Optimizer service request failed");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not leak a malformed internal base URL", async () => {
    const malformedBaseUrl = "http://[internal-host";
    const optimizerFetch = await loadOptimizerFetch(malformedBaseUrl);

    await expect(optimizerFetch("/api/v1/optimize")).rejects.toThrow("Optimizer service request failed");
  });
});