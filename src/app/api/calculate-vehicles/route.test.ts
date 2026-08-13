import { afterEach, describe, expect, it, vi } from "vitest";

const { optimizeRoutesMock, requireAdminMock } = vi.hoisted(() => ({
  optimizeRoutesMock: vi.fn(),
  requireAdminMock: vi.fn(),
}));

vi.mock("@/services/optimizer-service", () => ({ optimizeRoutes: optimizeRoutesMock }));
vi.mock("@/lib/admin-auth", () => ({ requireAdmin: requireAdminMock }));

const validRequest = () => new Request("http://localhost/api/calculate-vehicles", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({
    students: [{ id: "student-1", location_code: "L1", disability_type: "So" }],
  }),
});

afterEach(() => vi.clearAllMocks());

describe("POST /api/calculate-vehicles", () => {
  it("preserves deliberate solver failure metadata", async () => {
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
    const response = await POST(validRequest() as never);

    expect(response.status).toBe(500);
    expect(await response.json()).toMatchObject({
      algorithm_requested: "requested-ga",
      feasibility_certificate: { feasible: false },
      applied_policy: { profile_id: "small", limits: {} },
      error: "infeasible",
    });
  });
});