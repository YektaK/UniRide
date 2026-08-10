import { afterEach, describe, expect, it, vi } from "vitest";

const { getSupabaseAdminMock, requireRoleMock } = vi.hoisted(() => ({
  getSupabaseAdminMock: vi.fn(),
  requireRoleMock: vi.fn(),
}));

vi.mock("@/lib/admin-auth", () => ({
  requireRole: requireRoleMock,
}));

vi.mock("@/lib/supabase-admin", () => ({
  getSupabaseAdmin: getSupabaseAdminMock,
}));

function assignmentClient() {
  const queryResult = Promise.resolve({ data: [], error: null });
  const query = {
    select: vi.fn(),
    order: vi.fn(() => query),
    eq: vi.fn(() => queryResult),
  };
  query.select.mockReturnValue(query);
  return { from: vi.fn(() => query) };
}

afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

describe("GET /api/driver/assignments", () => {
  it("defers the admin client until after successful role authentication", async () => {
    getSupabaseAdminMock.mockReturnValue(assignmentClient());
    requireRoleMock.mockResolvedValue({ id: "driver-1", role: "driver" });

    const { GET } = await import("./route");
    expect(getSupabaseAdminMock).not.toHaveBeenCalled();

    const response = await GET(new Request("http://x/api/driver/assignments"));

    expect(response.status).toBe(200);
    expect(requireRoleMock).toHaveBeenCalledWith(
      expect.any(Request),
      ["driver", "admin"]
    );
    expect(getSupabaseAdminMock).toHaveBeenCalledTimes(1);
  });

  it("returns a generic 500 when the admin credentials are absent after successful authentication", async () => {
    requireRoleMock.mockResolvedValue({ id: "driver-1", role: "driver" });
    getSupabaseAdminMock.mockImplementation(() => {
      throw new Error("Missing Supabase admin credentials");
    });

    const { GET } = await import("./route");
    const response = await GET(new Request("http://x/api/driver/assignments"));

    expect(getSupabaseAdminMock).toHaveBeenCalledTimes(1);
    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({
      error: "Internal server error",
    });
  });
});
