import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

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

describe("driver assignments error mapping (L5)", () => {
  afterEach(() => vi.restoreAllMocks());

  async function loadWithRealAuthErrors() {
    vi.doMock("@/lib/admin-auth", async () => {
      const actual = await vi.importActual<typeof import("@/lib/admin-auth")>("@/lib/admin-auth");
      return { ...actual, requireRole: requireRoleMock };
    });
    return import("./route");
  }

  function failingQueryClient(message: string) {
    const result = Promise.resolve({ data: null, error: { message } });
    const query = {
      select: vi.fn(),
      order: vi.fn(() => query),
      eq: vi.fn(() => result),
    };
    query.select.mockReturnValue(query);
    return { from: vi.fn(() => query) };
  }

  it.each([
    ["unauthenticated", "unauthorized", 401],
    ["forbidden", "forbidden", 403],
  ] as const)("GET keeps the %s status instead of reporting 500", async (_label, factory, status) => {
    const { AppError } = await vi.importActual<typeof import("@/lib/admin-auth")>("@/lib/admin-auth");
    requireRoleMock.mockRejectedValue(AppError[factory]());
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { GET } = await loadWithRealAuthErrors();
    const response = await GET(new Request("http://x/api/driver/assignments"));
    expect(response.status).toBe(status);
  });

  it("GET does not leak a database error message", async () => {
    requireRoleMock.mockResolvedValue({ id: "driver-1", role: "driver" });
    getSupabaseAdminMock.mockReturnValue(failingQueryClient('relation "route_assignments" does not exist'));
    const logSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { GET } = await loadWithRealAuthErrors();
    const response = await GET(new Request("http://x/api/driver/assignments"));
    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({ error: "Internal server error" });
    expect(logSpy).toHaveBeenCalled();
  });

  it("PUT does not leak a database error message", async () => {
    requireRoleMock.mockResolvedValue({ id: "driver-1", role: "driver" });
    const builder: Record<string, unknown> = {};
    for (const name of ["select", "eq", "update"]) builder[name] = vi.fn(() => builder);
    let call = 0;
    builder.single = vi.fn(async () =>
      ++call === 1
        ? { data: { driver_id: "driver-1" }, error: null }
        : { data: null, error: { message: "duplicate key value violates unique constraint pk_7" } }
    );
    getSupabaseAdminMock.mockReturnValue({ from: vi.fn(() => builder) });
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { PUT } = await loadWithRealAuthErrors();
    const response = await PUT(
      new Request("http://x/api/driver/assignments", {
        method: "PUT",
        body: JSON.stringify({ id: "a1", status: "completed" }),
      })
    );
    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({ error: "Internal server error" });
  });
});
