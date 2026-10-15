/**
 * Security response headers (audit M8 / QW8).
 *
 * Production: per-request nonce CSP (no 'unsafe-eval', no 'unsafe-inline'
 * for scripts, no loopback origins) plus HSTS.
 * Development: permissive script/connect policy because HMR needs eval and
 * localhost websockets.
 *
 * style-src keeps 'unsafe-inline' on purpose: React `style={{}}` attributes,
 * Radix/shadcn primitives, recharts, the landing-page animation <style> tag
 * and the driver-PDF print window (about:blank, inherits this policy) all
 * rely on inline styles. Script execution is the XSS-critical surface and is
 * nonce-gated.
 */

export interface CspOptions {
  nonce: string;
  isProduction: boolean;
  /** NEXT_PUBLIC_SUPABASE_URL (REST + realtime origins are derived from it). */
  supabaseUrl?: string;
  /** Optimizer API URLs from env; loopback entries are ignored in production. */
  optimizerUrls?: ReadonlyArray<string | undefined>;
}

const HSTS_VALUE = "max-age=63072000; includeSubDomains";

export function generateNonce(): string {
  return btoa(crypto.randomUUID());
}

export function buildHstsHeader(isProduction: boolean): string | null {
  return isProduction ? HSTS_VALUE : null;
}

function isLoopbackHost(hostname: string): boolean {
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]" ||
    hostname.endsWith(".localhost")
  );
}

function parseHttpOrigin(value: string | undefined): URL | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url : null;
  } catch {
    return null;
  }
}

function productionConnectSources(options: CspOptions): string[] {
  const sources = ["'self'"];
  const supabase = parseHttpOrigin(options.supabaseUrl);
  if (supabase && !isLoopbackHost(supabase.hostname)) {
    sources.push(supabase.origin);
    sources.push(`${supabase.protocol === "https:" ? "wss:" : "ws:"}//${supabase.host}`);
  }
  for (const raw of options.optimizerUrls ?? []) {
    const optimizer = parseHttpOrigin(raw);
    if (optimizer && !isLoopbackHost(optimizer.hostname) && !sources.includes(optimizer.origin)) {
      sources.push(optimizer.origin);
    }
  }
  return sources;
}

export function buildContentSecurityPolicy(options: CspOptions): string {
  const { nonce, isProduction } = options;

  if (isProduction) {
    return [
      "default-src 'self'",
      `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self'",
      "img-src 'self' data: https://placehold.co",
      `connect-src ${productionConnectSources(options).join(" ")}`,
      "frame-ancestors 'none'",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; ");
  }

  const supabase = parseHttpOrigin(options.supabaseUrl);
  const supabaseSources = supabase
    ? [supabase.origin, `${supabase.protocol === "https:" ? "wss:" : "ws:"}//${supabase.host}`]
    : ["https://*.supabase.co", "wss://*.supabase.co"];
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob: https://placehold.co",
    [
      "connect-src 'self'",
      ...supabaseSources,
      "http://localhost:8000",
      "http://localhost:9002",
      "http://127.0.0.1:8000",
      "http://127.0.0.1:9002",
      "ws://localhost:*",
      "ws://127.0.0.1:*",
    ].join(" "),
    "frame-ancestors 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}
