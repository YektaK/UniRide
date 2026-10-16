import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({})); // audit L4: admin helpers import server-only

const { optimizerFetchMock, requireAdminMock } = vi.hoisted(() => ({
  optimizerFetchMock: vi.fn(),
  requireAdminMock: vi.fn(),
}));

vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: optimizerFetchMock }));
vi.mock("@/lib/supabase-admin", () => ({ getSupabaseAdmin: vi.fn() }));
vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, requireAdmin: requireAdminMock };
});

const sandboxRequest = () =>
  new Request("http://localhost/api/sandbox", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      students: [{ id: "s1", location_code: "SECRET-LOC-1", disability_type: "So" }],
      vehicles: [{ name: "V1", swCapacity: 4, soCapacity: 5 }],
    }),
  });

beforeEach(() => {
  vi.resetAllMocks();
  requireAdminMock.mockResolvedValue({ id: "admin-1" });
});
afterEach(() => vi.clearAllMocks());

describe("POST /api/sandbox (fail-closed travel-time matrix)", () => {
  it.each([
    [503, "travel-time matrix unavailable", "travel_time_matrix_unavailable"],
    [422, "requested locations are missing from the travel-time matrix", "travel_time_matrix_locations_missing"],
  ])("maps the optimizer's %i matrix response to a redacted error with the same status", async (status, detail, code) => {
    optimizerFetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail }), { status, headers: { "content-type": "application/json" } })
    );

    const { POST } = await import("./route");
    const response = await POST(sandboxRequest() as never);
    const body = await response.json();

    expect(response.status).toBe(status);
    expect(body.code).toBe(code);
    expect(typeof body.error).toBe("string");
    expect(JSON.stringify(body)).not.toContain("SECRET-LOC-1");
    expect(body.routes).toBeUndefined();
    expect(body.ieData).toBeUndefined();
  });

  it("keeps the generic error for other optimizer failures", async () => {
    optimizerFetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "students cannot exceed 60" }), { status: 422 })
    );

    const { POST } = await import("./route");
    const response = await POST(sandboxRequest() as never);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ error: "Optimization failed" });
  });
});

describe("POST /api/sandbox clusteringAlgorithm allowlist", () => {
  const withAlgo = (value?: unknown) =>
    new Request("http://localhost/api/sandbox", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        students: [{ id: "s1", location_code: "L1", disability_type: "So" }],
        vehicles: [{ name: "V1", swCapacity: 4, soCapacity: 5 }],
        ...(value === undefined ? {} : { clusteringAlgorithm: value }),
      }),
    });

  it.each(["not_a_real_algo", "", "SWEEP", 7, null])(
    "rejects %j with 400 before the optimizer is called",
    async (bad) => {
      const { POST } = await import("./route");
      const response = await POST(withAlgo(bad) as never);

      expect(response.status).toBe(400);
      expect(await response.json()).toEqual({ error: "Invalid clusteringAlgorithm" });
      expect(optimizerFetchMock).not.toHaveBeenCalled();
    }
  );

  it.each(["kmeans", "fuzzy_cmeans", "fuzzy_cmeans_enhanced", "hierarchical_fcm", "k_medoids", "sweep", "clarke_wright"])(
    "forwards the known name %s unchanged",
    async (name) => {
      optimizerFetchMock.mockResolvedValue(new Response(JSON.stringify({ routes: [] }), { status: 200 }));

      const { POST } = await import("./route");
      const response = await POST(withAlgo(name) as never);

      expect(response.status).toBe(200);
      expect(JSON.parse(optimizerFetchMock.mock.calls[0][1].body).clustering_algorithm).toBe(name);
    }
  );

  it("defaults to sweep when the field is absent", async () => {
    optimizerFetchMock.mockResolvedValue(new Response(JSON.stringify({ routes: [] }), { status: 200 }));

    const { POST } = await import("./route");
    await POST(withAlgo() as never);

    expect(JSON.parse(optimizerFetchMock.mock.calls[0][1].body).clustering_algorithm).toBe("sweep");
  });
});
