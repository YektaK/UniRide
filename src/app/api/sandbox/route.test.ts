import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
