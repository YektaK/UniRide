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
