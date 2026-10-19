import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: vi.fn() }));
vi.mock("./supabase-admin", () => ({ getSupabaseAdmin: vi.fn() }));
vi.mock("@supabase/supabase-js", () => ({ createClient: vi.fn() }));

import { AppError, handleApiError } from "./admin-auth";

afterEach(() => vi.restoreAllMocks());

describe("handleApiError (L5)", () => {
  it("returns a fixed 500 body for an unexpected Error and logs the details server-side", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const res = handleApiError(new Error('relation "users" does not exist at db-host-7'));
    expect(res.status).toBe(500);
    await expect(res.json()).resolves.toEqual({ error: "Internal server error" });
    expect(spy).toHaveBeenCalled();
  });

  it("still passes AppError status and message through", async () => {
    const res = handleApiError(AppError.forbidden());
    expect(res.status).toBe(403);
    await expect(res.json()).resolves.toEqual({ error: "Forbidden: Admin access required" });
  });
});
