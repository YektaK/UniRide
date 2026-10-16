import { beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({})); // audit L4: admin helpers import server-only

const { requireAdminMock, getSupabaseAdminMock, insertMock } = vi.hoisted(() => ({
  requireAdminMock: vi.fn(),
  getSupabaseAdminMock: vi.fn(),
  insertMock: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/admin-auth")>();
  return { ...actual, requireAdmin: requireAdminMock };
});
vi.mock("@/lib/supabase-admin", () => ({ getSupabaseAdmin: getSupabaseAdminMock }));

import { GET, POST } from "./route";

const basePlan = {
  planDate: "2026-10-15",
  direction: "pickup",
  algorithmUsed: "ga_split",
  totalVehicles: 1,
  totalDurationMinutes: 30,
  routes: [],
  studentCount: 0,
};

const post = (body: Record<string, unknown>) =>
  POST(new Request("http://localhost/api/route-plans", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ...basePlan, ...body }),
  }) as never);

beforeEach(() => {
  vi.resetAllMocks();
  requireAdminMock.mockResolvedValue({ id: "admin-1" });
  insertMock.mockReturnValue({
    select: () => ({ single: async () => ({ data: { id: "plan-1" }, error: null }) }),
  });
  getSupabaseAdminMock.mockReturnValue({
    schema: () => ({ from: () => ({ insert: insertMock }) }),
  });
});

describe("POST /api/route-plans solver provenance", () => {
  it("stores a valid solverProvenance as solver_provenance", async () => {
    const solverProvenance = {
      algorithm_requested: "ga_split",
      algorithm_used: "ga_split",
      effective_config_source: "default",
      effective_seed: 42,
    };

    const response = await post({ solverProvenance });

    expect(response.status).toBe(201);
    expect(insertMock).toHaveBeenCalledTimes(1);
    expect(insertMock.mock.calls[0]![0].solver_provenance).toEqual(solverProvenance);
  });

  it("leaves the column out when the client sent none (old rows and older optimizers stay null)", async () => {
    const response = await post({});

    expect(response.status).toBe(201);
    expect(insertMock.mock.calls[0]![0]).not.toHaveProperty("solver_provenance");
  });

  it.each([
    ["an unknown key", { effective_seed: 1, sql: "drop table" }],
    ["an arbitrary string field", { algorithm_used: "x".repeat(65) }],
    ["a non-integer seed", { effective_seed: 1.5 }],
    ["an empty object", {}],
    ["an array", [1, 2]],
    ["a string", "free text"],
  ])("rejects %s with 400 and writes nothing", async (_label, solverProvenance) => {
    const response = await post({ solverProvenance });

    expect(response.status).toBe(400);
    expect(insertMock).not.toHaveBeenCalled();
  });

  it("does not let a client smuggle solver_provenance past the allowlist", async () => {
    const response = await post({ solver_provenance: { anything: true } });

    expect(response.status).toBe(201);
    expect(insertMock.mock.calls[0]![0]).not.toHaveProperty("solver_provenance");
  });
});

describe("GET /api/route-plans", () => {
  it("returns solver_provenance with each plan", async () => {
    const rows = [
      { id: "a", solver_provenance: { effective_seed: 42 } },
      { id: "b", solver_provenance: null },
    ];
    const builder: Record<string, unknown> = {};
    const selectMock = vi.fn(() => builder);
    builder.select = selectMock;
    builder.order = () => Promise.resolve({ data: rows, error: null });
    getSupabaseAdminMock.mockReturnValue({ from: () => builder });

    const response = await GET(new Request("http://localhost/api/route-plans") as never);

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual(rows);
    expect(selectMock).toHaveBeenCalledWith("*");
  });
});
