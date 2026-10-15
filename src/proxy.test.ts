import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { createClientMock } = vi.hoisted(() => ({
  createClientMock: vi.fn(),
}));

vi.mock("@supabase/supabase-js", () => ({
  createClient: createClientMock,
}));

const credentialNames = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
  "SUPABASE_SERVICE_ROLE_KEY",
] as const;

const originalCredentials = Object.fromEntries(
  credentialNames.map((name) => [name, process.env[name]])
);

function clearCredentials() {
  for (const name of credentialNames) {
    delete process.env[name];
  }
}

afterEach(() => {
  for (const name of credentialNames) {
    const value = originalCredentials[name];
    if (value === undefined) {
      delete process.env[name];
    } else {
      process.env[name] = value;
    }
  }
  vi.clearAllMocks();
  vi.resetModules();
});

describe("proxy", () => {
  it("does not construct an anon client without public credentials and returns a sanitized 503 for a bearer request", async () => {
    clearCredentials();
    const { proxy } = await import("./proxy");

    expect(createClientMock).not.toHaveBeenCalled();

    const response = await proxy(
      new NextRequest("http://x/api/admin/users", {
        headers: { authorization: "Bearer token" },
      })
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      error: "Authentication service unavailable",
    });
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("keeps missing bearer requests unauthorized when public credentials are absent", async () => {
    clearCredentials();
    const { proxy } = await import("./proxy");

    const response = await proxy(new NextRequest("http://x/api/admin/users"));

    expect(response.status).toBe(401);
    expect(createClientMock).not.toHaveBeenCalled();
  });
});

describe("proxy page responses (CSP)", () => {
  it("gives every page response a fresh nonce, forwards it to the request and sets HSTS in production", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://abcdefgh.supabase.co");
    try {
      const { proxy } = await import("./proxy");
      const first = await proxy(new NextRequest("http://x/admin/benchmark"));
      const second = await proxy(new NextRequest("http://x/"));

      const csp1 = first.headers.get("content-security-policy") ?? "";
      const csp2 = second.headers.get("content-security-policy") ?? "";
      const nonce1 = /'nonce-([^']+)'/.exec(csp1)?.[1];
      const nonce2 = /'nonce-([^']+)'/.exec(csp2)?.[1];
      expect(nonce1).toBeTruthy();
      expect(nonce2).toBeTruthy();
      expect(nonce1).not.toBe(nonce2);
      expect(csp1).not.toContain("unsafe-eval");

      // Next.js reads the nonce from the *request* CSP header.
      expect(first.headers.get("x-middleware-request-content-security-policy")).toBe(csp1);
      expect(first.headers.get("x-middleware-request-x-nonce")).toBe(nonce1);
      expect(first.headers.get("strict-transport-security")).toBe(
        "max-age=63072000; includeSubDomains"
      );
      expect(createClientMock).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("sends no HSTS and keeps the permissive script policy in development", async () => {
    vi.stubEnv("NODE_ENV", "development");
    try {
      const { proxy } = await import("./proxy");
      const res = await proxy(new NextRequest("http://x/"));
      expect(res.headers.get("strict-transport-security")).toBeNull();
      expect(res.headers.get("content-security-policy")).toContain("'unsafe-eval'");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("keeps API auth gating for /api/admin (no CSP bypass of the 401)", async () => {
    const { proxy } = await import("./proxy");
    const res = await proxy(new NextRequest("http://x/api/admin/users"));
    expect(res.status).toBe(401);
  });

  it("exports a matcher covering pages but not static assets", async () => {
    const { config } = await import("./proxy");
    const sources = config.matcher.map((m: string | { source: string }) =>
      typeof m === "string" ? m : m.source
    );
    expect(sources).toContain("/api/admin/:path*");
    expect(sources).toContain("/api/benchmark/:path*");
    const page = sources.find((s: string) => s.includes("_next/static"));
    expect(page).toBeTruthy();
  });
});
