import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
import { optimizerFetch } from "./optimizer-server";

describe("optimizerFetch", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    process.env.OPTIMIZER_INTERNAL_API_KEY = "server-secret";
  });

  it("injects the key without changing caller headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    await optimizerFetch("/api/v1/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Internal-API-Key")).toBe("server-secret");
  });

  it("fails before fetch when the server key is missing", async () => {
    delete process.env.OPTIMIZER_INTERNAL_API_KEY;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(optimizerFetch("/api/v1/optimize", { method: "POST" }))
      .rejects.toThrow("Optimizer service is not configured");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
