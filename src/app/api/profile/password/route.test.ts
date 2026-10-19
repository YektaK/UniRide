import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: vi.fn() }));

const mocks = vi.hoisted(() => ({
  getSupabaseAdmin: vi.fn(),
  requireAuthenticatedUser: vi.fn(),
}));

vi.mock("@/lib/supabase-admin", () => ({ getSupabaseAdmin: mocks.getSupabaseAdmin }));
vi.mock("@/lib/admin-auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-auth")>("@/lib/admin-auth");
  return { ...actual, requireAuthenticatedUser: mocks.requireAuthenticatedUser };
});

import { AppError } from "@/lib/admin-auth";
import { NextRequest } from "next/server";
import { PATCH } from "./route";

function patch(body: unknown) {
  return PATCH(
    new NextRequest("http://x/api/profile/password", { method: "PATCH", body: JSON.stringify(body) })
  );
}

function adminWithAuthError(error: unknown) {
  mocks.getSupabaseAdmin.mockReturnValue({
    auth: { admin: { updateUserById: vi.fn(async () => ({ error })) } },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  mocks.getSupabaseAdmin.mockReset();
  mocks.requireAuthenticatedUser.mockReset();
});

describe("PATCH /api/profile/password status mapping (M10)", () => {
  it("returns 401, not 500, when the caller is not authenticated", async () => {
    mocks.requireAuthenticatedUser.mockRejectedValue(AppError.unauthorized());
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await patch({ newPassword: "abcdef" });
    expect(res.status).toBe(401);
  });

  it.each([
    ["weak password (422)", { status: 422, code: "weak_password", message: "Password should contain at least one digit: provider detail" }, 400],
    ["same password (422)", { status: 422, code: "same_password", message: "New password should be different from the old password." }, 400],
    ["bad request (400)", { status: 400, code: "validation_failed", message: "provider detail 400" }, 400],
    ["provider says 401", { status: 401, message: "JWT expired provider detail" }, 401],
    ["provider says 403", { status: 403, message: "not allowed provider detail" }, 403],
    ["user not found (404)", { status: 404, code: "user_not_found", message: "User not found provider detail" }, 401],
  ])("maps a provider auth error: %s with a fixed message", async (_label, providerError, status) => {
    mocks.requireAuthenticatedUser.mockResolvedValue({ id: "u1", email: "u@x", role: "student" });
    adminWithAuthError(providerError);
    const logSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await patch({ newPassword: "abcdef" });
    expect(res.status).toBe(status);
    const body = (await res.json()) as { error: string };
    expect(body.error).not.toContain("provider detail");
    expect(logSpy).toHaveBeenCalled();
  });

  it("returns a fixed 500 for an unrecognised provider failure", async () => {
    mocks.requireAuthenticatedUser.mockResolvedValue({ id: "u1", email: "u@x", role: "student" });
    adminWithAuthError({ status: 500, message: "upstream gotrue exploded at 10.0.0.5" });
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await patch({ newPassword: "abcdef" });
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error: string };
    expect(body.error).not.toContain("10.0.0.5");
  });

  it("does not leak an unexpected thrown error message", async () => {
    mocks.requireAuthenticatedUser.mockRejectedValue(new Error("secret internal host db-7"));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await patch({ newPassword: "abcdef" });
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error: string };
    expect(body.error).not.toContain("db-7");
  });

  it("does not leak a users-table error when saving the hint", async () => {
    mocks.requireAuthenticatedUser.mockResolvedValue({ id: "u1", email: "u@x", role: "student" });
    const eq = vi.fn(async () => ({ error: { message: "column password_hint violates policy p9" } }));
    mocks.getSupabaseAdmin.mockReturnValue({ from: vi.fn(() => ({ update: vi.fn(() => ({ eq })) })) });
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await patch({ passwordHint: "x" });
    expect(res.status).toBe(500);
    const body = (await res.json()) as { error: string };
    expect(body.error).not.toContain("p9");
  });

  it("still succeeds on the happy path", async () => {
    mocks.requireAuthenticatedUser.mockResolvedValue({ id: "u1", email: "u@x", role: "student" });
    adminWithAuthError(null);
    const res = await patch({ newPassword: "abcdef" });
    expect(res.status).toBe(200);
  });
});
