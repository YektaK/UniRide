import { afterEach, describe, expect, it, vi } from "vitest";

const { optimizeRoutesMock, requireAdminMock } = vi.hoisted(() => ({
  optimizeRoutesMock: vi.fn(),
  requireAdminMock: vi.fn(),
}));

vi.mock("@/services/optimizer-service", () => ({
  optimizeRoutes: optimizeRoutesMock,
  getAvailableStrategies: vi.fn(),
}));

vi.mock("@/lib/admin-auth", () => ({
  requireAdmin: requireAdminMock,
}));

afterEach(() => {
  vi.clearAllMocks();
});

const validRequest = (localSearchType: string) =>
  new Request("http://localhost/api/optimize-route", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      students: [{ id: "student-1", location_code: "Sw1" }],
      depot: { id: "D.Kampus", lat: 41.001, lng: 29.177 },
      local_search_type: localSearchType,
    }),
  });

describe("POST /api/optimize-route", () => {
  it("forwards a validated local search type after admin authentication", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1" });
    optimizeRoutesMock.mockResolvedValue({ success: true, routes: [] });
    const { POST } = await import("./route");

    const response = await POST(validRequest("or_opt"));

    expect(response.status).toBe(200);
    expect(requireAdminMock).toHaveBeenCalledWith(expect.any(Request));
    expect(optimizeRoutesMock).toHaveBeenCalledWith(
      expect.any(Array),
      expect.any(Object),
      expect.objectContaining({ local_search_type: "or_opt" })
    );
  });

  it("rejects an invalid local search type without calling the optimizer", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1" });
    const { POST } = await import("./route");

    const response = await POST(validRequest("invalid"));

    expect(response.status).toBe(400);
    expect(optimizeRoutesMock).not.toHaveBeenCalled();
  });

  it("returns solver failure metadata without exposing transport details", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1" });
    optimizeRoutesMock.mockResolvedValue({
      success: false,
      algorithm_used: "ga",
      algorithm_requested: "requested-ga",
      feasibility_certificate: { feasible: false },
      applied_policy: { profile_id: "small", limits: {} },
      error_message: "infeasible",
    });
    const { POST } = await import("./route");
    const response = await POST(validRequest("or_opt"));
    expect(await response.json()).toMatchObject({ algorithm_requested: "requested-ga", feasibility_certificate: { feasible: false }, error: "infeasible" });
  });
});
