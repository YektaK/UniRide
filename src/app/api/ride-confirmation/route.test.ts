import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getCurrentUserFromRequest: vi.fn(),
  getSupabaseAdmin: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, getCurrentUserFromRequest: mocks.getCurrentUserFromRequest };
});

vi.mock("@/lib/supabase-admin", () => ({
  getSupabaseAdmin: mocks.getSupabaseAdmin,
}));

function confirmationRequest() {
  return new Request("http://localhost/api/ride-confirmation", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      action: "confirm",
      rideDate: "2099-01-01",
      pickupTime: "08:00",
      dropoffTime: "17:00",
    }),
  });
}

function createAdminClient() {
  const insert = vi.fn();
  const select = vi.fn();
  const eq = vi.fn();
  const gte = vi.fn();
  const lt = vi.fn();
  const single = vi.fn()
    .mockResolvedValueOnce({ data: null, error: { code: "PGRST116" } })
    .mockResolvedValueOnce({
      data: { home_address: "Student home", home_coordinates: { lat: 41.0, lng: 29.0 } },
      error: null,
    })
    .mockResolvedValueOnce({ data: { id: "ride-1" }, error: null });
  const query = { insert, select, eq, gte, lt, single };

  for (const method of [insert, select, eq, gte, lt]) {
    method.mockReturnValue(query);
  }

  return { client: { from: vi.fn().mockReturnValue(query) }, insert };
}

describe("POST /api/ride-confirmation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("persists the canonical Dudullu campus as a confirmed ride dropoff", async () => {
    const { client, insert } = createAdminClient();
    mocks.getCurrentUserFromRequest.mockResolvedValue({ id: "student-1" });
    mocks.getSupabaseAdmin.mockReturnValue(client);

    const { POST } = await import("./route");
    const response = await POST(confirmationRequest() as never);

    expect(response.status).toBe(200);
    expect(insert).toHaveBeenCalledWith(expect.objectContaining({
      dropoff_location: {
        address: "Doğuş Üniversitesi, Dudullu Kampüsü",
        coordinates: { lat: 41.001, lng: 29.177 },
      },
    }));
  });
});
