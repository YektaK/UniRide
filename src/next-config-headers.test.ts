import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadHeaders() {
  const mod = await import("../next.config");
  const config = mod.default as { headers?: () => Promise<Array<{ source: string; headers: Array<{ key: string; value: string }> }>> };
  return (await config.headers!()).flatMap((rule) => rule.headers.map((h) => ({ ...h, source: rule.source })));
}

describe("next.config headers()", () => {
  it("sends HSTS for every path in production, without preload", async () => {
    vi.stubEnv("NODE_ENV", "production");
    const headers = await loadHeaders();
    const hsts = headers.filter((h) => h.key.toLowerCase() === "strict-transport-security");
    expect(hsts).toHaveLength(1);
    expect(hsts[0].source).toBe("/(.*)");
    expect(hsts[0].value).toBe("max-age=63072000; includeSubDomains");
  });

  it("sends no HSTS outside production", async () => {
    vi.stubEnv("NODE_ENV", "development");
    const headers = await loadHeaders();
    expect(headers.some((h) => h.key.toLowerCase() === "strict-transport-security")).toBe(false);
  });

  it("does not set a static CSP (the proxy owns the nonce CSP)", async () => {
    vi.stubEnv("NODE_ENV", "production");
    const headers = await loadHeaders();
    expect(headers.some((h) => h.key.toLowerCase() === "content-security-policy")).toBe(false);
  });
});
