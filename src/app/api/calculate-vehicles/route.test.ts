import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppError } from "@/lib/admin-auth";

const { optimizeRoutesMock, requireAdminMock } = vi.hoisted(() => ({
  optimizeRoutesMock: vi.fn(),
  requireAdminMock: vi.fn(),
}));

vi.mock("@/services/optimizer-service", () => ({ optimizeRoutes: optimizeRoutesMock }));
// Keep the real AppError/status helpers while only replacing the auth gate.
vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, requireAdmin: requireAdminMock };
});

const student = { id: "student-1", location_code: "L1", disability_type: "So" };

const validRequest = (body: Record<string, unknown> = {}) =>
  new Request("http://localhost/api/calculate-vehicles", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ students: [student], ...body }),
  });

const happySolverResult = (overrides: Record<string, unknown> = {}) => ({
  success: true,
  algorithm_used: "ga",
  routes: [],
  total_vehicles: 1,
  total_duration_minutes: 10,
  execution_time_seconds: 0.5,
  ...overrides,
});

beforeEach(() => vi.resetAllMocks());
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

  it.each([
    ["pickup", "pickup"],
    ["dropoff", "dropoff"],
  ] as const)(
    "forwards the normalized %s direction and returns it on success",
    async (requested, returned) => {
      requireAdminMock.mockResolvedValue({ id: "admin-1", email: "admin@test", role: "admin" });
      optimizeRoutesMock.mockResolvedValue(happySolverResult({ direction: returned }));

      const { POST } = await import("./route");
      const response = await POST(validRequest({ direction: requested }) as never);

      expect(optimizeRoutesMock).toHaveBeenCalledWith(
        expect.any(Array),
        expect.any(Object),
        expect.objectContaining({ direction: requested })
      );
      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toMatchObject({ success: true, direction: returned });
    }
  );

  it("normalizes an omitted request direction to pickup", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1", email: "admin@test", role: "admin" });
    optimizeRoutesMock.mockResolvedValue(happySolverResult({ direction: "pickup" }));

    const { POST } = await import("./route");
    const response = await POST(validRequest() as never);

    expect(optimizeRoutesMock).toHaveBeenCalledWith(
      expect.any(Array),
      expect.any(Object),
      expect.objectContaining({ direction: "pickup" })
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ direction: "pickup" });
  });

  it("rejects a malformed direction with 400 before running the solver", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1", email: "admin@test", role: "admin" });

    const { POST } = await import("./route");
    // Runtime-malformed value; cast at the test boundary to pass the JSON body.
    const response = await POST(validRequest({ direction: "sideways" }) as never);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "Invalid direction" });
    expect(optimizeRoutesMock).not.toHaveBeenCalled();
  });

  it("returns 401 for missing authentication and 403 for non-admin instead of 500", async () => {
    const { POST } = await import("./route");

    requireAdminMock.mockRejectedValue(new AppError("Unauthorized: Not logged in", 401));
    const unauthorized = await POST(validRequest({ direction: "sideways" }) as never);
    expect(unauthorized.status).toBe(401);
    expect(await unauthorized.json()).toEqual({ error: "Unauthorized: Not logged in" });

    requireAdminMock.mockRejectedValue(new AppError("Forbidden: Admin access required", 403));
    const forbidden = await POST(validRequest() as never);
    expect(forbidden.status).toBe(403);
    expect(await forbidden.json()).toEqual({ error: "Forbidden: Admin access required" });
  });

  it.each([undefined, null, "sideways"])(
    "returns the contract-error 502 for a successful result with direction %s",
    async (returnedDirection) => {
      requireAdminMock.mockResolvedValue({ id: "admin-1", email: "admin@test", role: "admin" });
      optimizeRoutesMock.mockResolvedValue(happySolverResult({ direction: returnedDirection }));

      const { POST } = await import("./route");
      const response = await POST(validRequest({ direction: "pickup" }) as never);

      expect(response.status).toBe(502);
      expect(await response.json()).toEqual({ success: false, error: "Invalid optimization direction" });
    }
  );

  it("returns the contract-error 502 when the successful result direction mismatches the request", async () => {
    requireAdminMock.mockResolvedValue({ id: "admin-1", email: "admin@test" });
    optimizeRoutesMock.mockResolvedValue(happySolverResult({ direction: "dropoff" }));

    const { POST } = await import("./route");
    const response = await POST(validRequest({ direction: "pickup" }) as never);

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ success: false, error: "Invalid optimization direction" });
  });
});
