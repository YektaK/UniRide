import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { requireAdminMock, optimizerFetchMock } = vi.hoisted(() => ({
  requireAdminMock: vi.fn(),
  optimizerFetchMock: vi.fn(),
}));

vi.mock("@/lib/admin-auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/admin-auth")>("@/lib/admin-auth");
  return { ...actual, requireAdmin: requireAdminMock };
});

vi.mock("@/lib/optimizer-server", () => ({ optimizerFetch: optimizerFetchMock }));

import { AppError } from "@/lib/admin-auth";

type Handler = (request: NextRequest, context?: never) => Promise<Response>;

interface RouteCase {
  readonly name: string;
  readonly method: "GET" | "POST";
  readonly url: string;
  readonly body?: unknown;
  readonly load: () => Promise<Record<string, unknown>>;
  readonly context?: unknown;
}

const RUN_BODY = { algorithms: [{ id: "greedy" }], problems: ["eil51"], settings: {} };

const ROUTES: readonly RouteCase[] = [
  { name: "academic/best", method: "GET", url: "/api/benchmark/academic/best?problem=a", load: () => import("./academic/best/route") },
  { name: "academic/leaderboard", method: "GET", url: "/api/benchmark/academic/leaderboard", load: () => import("./academic/leaderboard/route") },
  { name: "academic/problems", method: "GET", url: "/api/benchmark/academic/problems", load: () => import("./academic/problems/route") },
  { name: "health", method: "GET", url: "/api/benchmark/health", load: () => import("./health/route") },
  { name: "param-spaces", method: "GET", url: "/api/benchmark/param-spaces", load: () => import("./param-spaces/route") },
  { name: "problems", method: "GET", url: "/api/benchmark/problems", load: () => import("./problems/route") },
  {
    name: "results/[runId]", method: "GET", url: "/api/benchmark/results/run_1",
    load: () => import("./results/[runId]/route"),
    context: { params: Promise.resolve({ runId: "run_1" }) },
  },
  { name: "run", method: "POST", url: "/api/benchmark/run", body: RUN_BODY, load: () => import("./run/route") },
  { name: "run/status", method: "GET", url: "/api/benchmark/run/status?runId=run_1", load: () => import("./run/status/route") },
  { name: "run/stop", method: "POST", url: "/api/benchmark/run/stop", body: { runId: "run_1" }, load: () => import("./run/stop/route") },
  { name: "status", method: "GET", url: "/api/benchmark/status?run_id=run_1", load: () => import("./status/route") },
  { name: "stop", method: "POST", url: "/api/benchmark/stop", body: { run_id: "run_1" }, load: () => import("./stop/route") },
  { name: "strategies", method: "GET", url: "/api/benchmark/strategies", load: () => import("./strategies/route") },
];

async function call(route: RouteCase): Promise<Response> {
  const mod = await route.load();
  const handler = mod[route.method] as Handler;
  const request = new NextRequest(`http://localhost${route.url}`, {
    method: route.method,
    headers: { "Content-Type": "application/json" },
    body: route.body === undefined ? undefined : JSON.stringify(route.body),
  });
  return handler(request, route.context as never);
}

describe("benchmark BFF routes require admin", () => {
  beforeEach(() => {
    requireAdminMock.mockReset();
    optimizerFetchMock.mockReset();
    optimizerFetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
  });

  it("covers every route.ts under /api/benchmark", async () => {
    const { globSync } = await import("node:fs");
    const found = globSync("**/route.ts", { cwd: __dirname }).length;
    expect(found).toBe(ROUTES.length);
  });

  it.each(ROUTES)("$name: anonymous call is 401 and never reaches the optimizer", async (route) => {
    requireAdminMock.mockRejectedValue(AppError.unauthorized());
    const response = await call(route);
    expect(response.status).toBe(401);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it.each(ROUTES)("$name: non-admin call is 403 and never reaches the optimizer", async (route) => {
    requireAdminMock.mockRejectedValue(AppError.forbidden());
    const response = await call(route);
    expect(response.status).toBe(403);
    expect(optimizerFetchMock).not.toHaveBeenCalled();
  });

  it.each(ROUTES)("$name: admin call passes through to the optimizer", async (route) => {
    requireAdminMock.mockResolvedValue({ id: "u1", email: "a@b.c", role: "admin" });
    const response = await call(route);
    expect(requireAdminMock).toHaveBeenCalledTimes(1);
    expect(response.status).toBe(200);
    expect(optimizerFetchMock).toHaveBeenCalled();
  });
});

describe("benchmark run error mapping", () => {
  it("surfaces a FastAPI detail (429) instead of the generic fallback", async () => {
    requireAdminMock.mockResolvedValue({ id: "u1", email: "a@b.c", role: "admin" });
    optimizerFetchMock.mockReset();
    optimizerFetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Too many benchmark runs" }), { status: 429 }),
    );
    const response = await call(ROUTES.find((r) => r.name === "run")!);
    expect(response.status).toBe(429);
    const json = (await response.json()) as { error: string };
    expect(json.error).toBe("Too many benchmark runs");
  });
});
