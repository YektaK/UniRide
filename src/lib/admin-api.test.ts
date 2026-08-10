import { afterEach, describe, expect, it, vi } from "vitest";

const { getSupabaseClientMock } = vi.hoisted(() => ({
  getSupabaseClientMock: vi.fn(),
}));

vi.mock("./supabase", () => ({
  getSupabaseClient: getSupabaseClientMock,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("adminApi.routes.optimize", () => {
  it("preserves local search settings in the authenticated BFF request", async () => {
    getSupabaseClientMock.mockReturnValue({
      auth: {
        getSession: vi.fn().mockResolvedValue({
          data: {
            session: {
              access_token: "test-token",
              expires_at: Math.floor(Date.now() / 1000) + 3600,
            },
          },
          error: null,
        }),
      },
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { adminApi, clearAuthTokenCache } = await import("./admin-api");
    clearAuthTokenCache();

    await adminApi.routes.optimize({
      start: "D.Kampus",
      end: "D.Kampus",
      waypoints: ["Sw1"],
      strategy: "genetic_algorithm",
      local_search_type: "or_opt",
      max_travel_time: 180,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/optimize-route",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      local_search_type: "or_opt",
      max_travel_time: 180,
    });
  });
});
