import { describe, expect, it } from "vitest";
import {
  buildContentSecurityPolicy,
  buildHstsHeader,
  generateNonce,
} from "./security-headers";

const SUPABASE = "https://abcdefgh.supabase.co";

function directives(csp: string): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const part of csp.split(";")) {
    const [name, ...values] = part.trim().split(/\s+/);
    if (name) out[name] = values;
  }
  return out;
}

describe("generateNonce", () => {
  it("returns a fresh base64 value on every call", () => {
    const a = generateNonce();
    const b = generateNonce();
    expect(a).not.toBe(b);
    expect(a).toMatch(/^[A-Za-z0-9+/]+=*$/);
    expect(a.length).toBeGreaterThanOrEqual(22);
  });
});

describe("buildContentSecurityPolicy (production)", () => {
  const csp = buildContentSecurityPolicy({
    nonce: "NONCE123",
    isProduction: true,
    supabaseUrl: SUPABASE,
    optimizerUrls: ["https://optimizer.example.com/path"],
  });
  const d = directives(csp);

  it("allows scripts only via self, the nonce and strict-dynamic", () => {
    expect(d["script-src"]).toEqual(["'self'", "'nonce-NONCE123'", "'strict-dynamic'"]);
  });

  it("has no unsafe-eval anywhere and no unsafe-inline for scripts", () => {
    expect(csp).not.toContain("unsafe-eval");
    expect(d["script-src"]).not.toContain("'unsafe-inline'");
  });

  it("has no localhost or loopback entries", () => {
    expect(csp).not.toMatch(/localhost|127\.0\.0\.1|\[::1\]/);
  });

  it("limits connect-src to self, Supabase (https + wss) and the optimizer origin", () => {
    expect(d["connect-src"]).toEqual([
      "'self'",
      "https://abcdefgh.supabase.co",
      "wss://abcdefgh.supabase.co",
      "https://optimizer.example.com",
    ]);
  });

  it("sets the hardening directives", () => {
    expect(d["frame-ancestors"]).toEqual(["'none'"]);
    expect(d["base-uri"]).toEqual(["'self'"]);
    expect(d["object-src"]).toEqual(["'none'"]);
    expect(d["form-action"]).toEqual(["'self'"]);
    expect(d["default-src"]).toEqual(["'self'"]);
  });

  it("keeps style-src unsafe-inline (React style attributes, Radix, recharts)", () => {
    expect(d["style-src"]).toContain("'unsafe-inline'");
  });

  it("drops loopback optimizer URLs and falls back to a wildcard-free connect-src without Supabase", () => {
    const local = buildContentSecurityPolicy({
      nonce: "N",
      isProduction: true,
      optimizerUrls: ["http://127.0.0.1:8000", "http://localhost:8000", undefined, "not a url"],
    });
    expect(local).not.toMatch(/localhost|127\.0\.0\.1/);
    expect(directives(local)["connect-src"]).toEqual(["'self'"]);
    expect(local).not.toContain("*");
  });
});

describe("buildContentSecurityPolicy (development)", () => {
  const csp = buildContentSecurityPolicy({
    nonce: "NONCE123",
    isProduction: false,
    supabaseUrl: SUPABASE,
  });
  const d = directives(csp);

  it("stays permissive for HMR", () => {
    expect(d["script-src"]).toEqual(["'self'", "'unsafe-inline'", "'unsafe-eval'"]);
    expect(d["connect-src"]).toContain("http://localhost:8000");
    expect(d["connect-src"]).toContain("ws://localhost:*");
  });

  it("keeps the non-script hardening directives", () => {
    expect(d["frame-ancestors"]).toEqual(["'none'"]);
    expect(d["object-src"]).toEqual(["'none'"]);
  });
});

describe("buildHstsHeader", () => {
  it("is set in production without preload", () => {
    expect(buildHstsHeader(true)).toBe("max-age=63072000; includeSubDomains");
  });
  it("is absent outside production", () => {
    expect(buildHstsHeader(false)).toBeNull();
  });
});
