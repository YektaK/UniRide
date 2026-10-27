import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";

// MT6F-08 (audit L3-a, L3-c; DECISION_LOG A21 OQ-F6 b): unused frontend code is removed.
vi.mock("server-only", () => ({}));
vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: vi.fn() }));
vi.mock("@/lib/supabase-admin", () => ({ getSupabaseAdmin: vi.fn() }));

const root = process.cwd();

describe("MT6F-08 dead frontend code is gone", () => {
  it("vehicle-planning-page.tsx (never imported, L3-a) does not exist", () => {
    expect(existsSync(join(root, "src/app/(app)/admin/vehicle-planning/vehicle-planning-page.tsx"))).toBe(false);
    expect(existsSync(join(root, "src/app/(app)/admin/vehicle-planning/vehicle-planning-page.test.tsx"))).toBe(false);
    // The live route stays.
    expect(existsSync(join(root, "src/app/(app)/admin/vehicle-planning/page.tsx"))).toBe(true);
  });

  it("src/app/api/sandbox/route.ts exports only POST (L3-c)", async () => {
    const route = await import("./route");
    const handlers = Object.keys(route).filter((key) => /^[A-Z]+$/.test(key));
    expect(handlers).toEqual(["POST"]);
  });

  it("src/services/sandbox-api.ts (no importer, L3-c) does not exist", () => {
    expect(existsSync(join(root, "src/services/sandbox-api.ts"))).toBe(false);
  });
});
