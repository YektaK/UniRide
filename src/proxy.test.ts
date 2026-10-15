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
  it("gives every page response a fresh nonce and forwards it to the request in production", async () => {
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
      // HSTS is sent once, by next.config.ts headers(), not by the proxy.
      expect(first.headers.get("strict-transport-security")).toBeNull();
      expect(createClientMock).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("keeps the permissive script policy in development", async () => {
    vi.stubEnv("NODE_ENV", "development");
    try {
      const { proxy } = await import("./proxy");
      const res = await proxy(new NextRequest("http://x/"));
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

describe("proxy CSP does not leak the server-only optimizer URL", () => {
  it("omits OPTIMIZER_API_URL but includes NEXT_PUBLIC_OPTIMIZER_API_URL", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("OPTIMIZER_API_URL", "https://internal-optimizer.corp.example");
    vi.stubEnv("NEXT_PUBLIC_OPTIMIZER_API_URL", "https://public-optimizer.example.com");
    try {
      const { proxy } = await import("./proxy");
      const res = await proxy(new NextRequest("http://x/"));
      const csp = res.headers.get("content-security-policy") ?? "";
      expect(csp).not.toContain("internal-optimizer.corp.example");
      expect(csp).toContain("https://public-optimizer.example.com");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("adds no optimizer origin when only the server-only variable is set", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("OPTIMIZER_API_URL", "https://internal-optimizer.corp.example");
    vi.stubEnv("NEXT_PUBLIC_OPTIMIZER_API_URL", "");
    try {
      const { proxy } = await import("./proxy");
      const res = await proxy(new NextRequest("http://x/"));
      expect(res.headers.get("content-security-policy")).not.toContain("internal-optimizer");
    } finally {
      vi.unstubAllEnvs();
    }
  });
});

describe("proxy bearer gate", () => {
  it.each(["/api/benchmark", "/api/benchmark/run", "/api/admin", "/api/admin/users"])(
    "returns 401 without a token for %s and never builds a Supabase client",
    async (path) => {
      const { proxy } = await import("./proxy");
      const res = await proxy(new NextRequest(`http://x${path}`));
      expect(res.status).toBe(401);
      expect(createClientMock).not.toHaveBeenCalled();
    }
  );

  it("does not gate look-alike prefixes such as /api/benchmarkX", async () => {
    const { proxy } = await import("./proxy");
    const res = await proxy(new NextRequest("http://x/api/benchmarkX"));
    expect(res.status).toBe(200);
  });

  function stubAnonClient(result: { data: { user: { id: string } | null }; error: unknown }) {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://abcdefgh.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "anon";
    const getUser = vi.fn().mockResolvedValue(result);
    createClientMock.mockReturnValue({ auth: { getUser } });
    return getUser;
  }

  it("returns 401 when Supabase reports an error for the token", async () => {
    const getUser = stubAnonClient({ data: { user: { id: "u1" } }, error: { message: "bad jwt" } });
    const { proxy } = await import("./proxy");
    const res = await proxy(
      new NextRequest("http://x/api/benchmark/run", { headers: { authorization: "Bearer bad" } })
    );
    expect(getUser).toHaveBeenCalledWith("bad");
    expect(res.status).toBe(401);
  });

  it("returns 401 when Supabase returns no user for the token", async () => {
    stubAnonClient({ data: { user: null }, error: null });
    const { proxy } = await import("./proxy");
    const res = await proxy(
      new NextRequest("http://x/api/admin/users", { headers: { authorization: "Bearer ghost" } })
    );
    expect(res.status).toBe(401);
  });

  it("forwards x-user-id and a CSP for a valid token", async () => {
    stubAnonClient({ data: { user: { id: "user-42" } }, error: null });
    const { proxy } = await import("./proxy");
    const res = await proxy(
      new NextRequest("http://x/api/benchmark/run", { headers: { authorization: "Bearer good" } })
    );
    expect(res.status).toBe(200);
    expect(res.headers.get("x-middleware-request-x-user-id")).toBe("user-42");
  });
});
