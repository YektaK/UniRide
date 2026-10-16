import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({})); // audit L4: admin helpers import server-only

const { compareAllAlgorithmsMock, requireAdminMock } = vi.hoisted(() => ({
  compareAllAlgorithmsMock: vi.fn(),
  requireAdminMock: vi.fn(),
}));

vi.mock("@/services/optimizer-service", () => ({ compareAllAlgorithms: compareAllAlgorithmsMock }));
vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, requireAdmin: requireAdminMock };
});

const student = { id: "s1", location_code: "L1", disability_type: "So" };

const request = (body: Record<string, unknown> = {}) =>
  new Request("http://localhost/api/compare-algorithms", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ students: [student], ...body }),
  });

const okResult = {
  success: true,
  results: [],
  best_algorithm: "ga",
  fastest_algorithm: "ga",
  summary: {},
};

beforeEach(() => {
  vi.resetAllMocks();
  requireAdminMock.mockResolvedValue({ id: "admin-1" });
  compareAllAlgorithmsMock.mockResolvedValue(okResult);
});
afterEach(() => vi.clearAllMocks());

describe("POST /api/compare-algorithms clusteringAlgorithm validation (H12 follow-up)", () => {
  it("rejects an unknown clustering algorithm with 400 in the route's error format and never calls the optimizer", async () => {
    const { POST } = await import("./route");
    const response = await POST(request({ clusteringAlgorithm: "not_a_real_algorithm" }));
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.error).toBe("Invalid request body");
    expect(body.details.fieldErrors.clusteringAlgorithm).toBeTruthy();
    expect(compareAllAlgorithmsMock).not.toHaveBeenCalled();
  });

  it.each(["sweep", "clarke_wright", "k_medoids", "fuzzy_cmeans", "fuzzy_cmeans_enhanced", "hierarchical_fcm", "kmeans"])(
    "accepts the allowlisted name %s and forwards it",
    async (name) => {
      const { POST } = await import("./route");
      const response = await POST(request({ clusteringAlgorithm: name }));

      expect(response.status).toBe(200);
      expect(compareAllAlgorithmsMock.mock.calls[0][2]).toEqual({ clustering_algorithm: name });
    }
  );

  it("keeps the field optional and defaults to sweep", async () => {
    const { POST } = await import("./route");
    const response = await POST(request());

    expect(response.status).toBe(200);
    expect(compareAllAlgorithmsMock.mock.calls[0][2]).toEqual({ clustering_algorithm: "sweep" });
  });
});
