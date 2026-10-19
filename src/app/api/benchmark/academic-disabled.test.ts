import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { GET as academicBest } from "./academic/best/route";
import { GET as academicLeaderboard } from "./academic/leaderboard/route";
import { GET as academicProblems } from "./academic/problems/route";
import { GET as paramSpaces } from "./param-spaces/route";
import { GET as problems } from "./problems/route";
import { GET as results } from "./results/[runId]/route";
import { POST as run } from "./run/route";
import { GET as runStatus } from "./run/status/route";
import { POST as runStop } from "./run/stop/route";
import { GET as status } from "./status/route";
import { POST as stop } from "./stop/route";

// H8: with UNIRIDE_ACADEMIC_PROCESS unset the optimizer does not mount the benchmark
// router, so every benchmark call answers FastAPI's default 404 {"detail":"Not Found"}.
// The BFF must turn that into a clear 503 with a fixed code.

vi.mock("@/lib/benchmark-auth", () => ({ denyUnlessBenchmarkAdmin: async () => null }));
vi.mock("server-only", () => ({}));

beforeEach(() => {
  process.env.OPTIMIZER_INTERNAL_API_KEY = "test-key";
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete process.env.OPTIMIZER_INTERNAL_API_KEY;
});

function stubOptimizer(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }))
  );
}

function get(path: string) {
  return new NextRequest(`http://x${path}`);
}

function post(path: string, body: unknown) {
  return new NextRequest(`http://x${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

const runBody = { algorithms: [{ id: "ga", params: {} }], problems: ["berlin52"], settings: { n_runs: 1 } };

const cases: Array<[string, () => Promise<Response>]> = [
  ["academic/best", () => academicBest(get("/api/benchmark/academic/best?problem=a&algorithm=b"))],
  ["academic/leaderboard", () => academicLeaderboard(get("/api/benchmark/academic/leaderboard"))],
  ["academic/problems", () => academicProblems(get("/api/benchmark/academic/problems"))],
  ["param-spaces", () => paramSpaces(get("/api/benchmark/param-spaces"))],
  ["problems", () => problems(get("/api/benchmark/problems"))],
  ["results/[runId]", () => results(get("/api/benchmark/results/r1"), { params: Promise.resolve({ runId: "r1" }) })],
  ["run", () => run(post("/api/benchmark/run", runBody))],
  ["run/status", () => runStatus(get("/api/benchmark/run/status?runId=r1"))],
  ["run/stop", () => runStop(post("/api/benchmark/run/stop", { runId: "r1" }))],
  ["status", () => status(get("/api/benchmark/status?run_id=r1"))],
  ["stop", () => stop(post("/api/benchmark/stop", { run_id: "r1" }))],
];

describe("benchmark BFF when the academic router is not mounted (optimizer 404 Not Found)", () => {
  it.each(cases)("%s answers 503 ACADEMIC_SERVICE_DISABLED", async (_name, call) => {
    stubOptimizer(404, { detail: "Not Found" });
    const res = await call();
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.code).toBe("ACADEMIC_SERVICE_DISABLED");
    expect(typeof body.error).toBe("string");
  });

  it("keeps a genuine run-not-found 404 as 404 (only the router-missing 404 is translated)", async () => {
    stubOptimizer(404, { detail: "Benchmark run r1 not found" });
    const res = await status(get("/api/benchmark/status?run_id=r1"));
    expect(res.status).toBe(404);
    expect((await res.json()).code).not.toBe("ACADEMIC_SERVICE_DISABLED");
  });
});

describe("POST /api/benchmark/run error text (L5)", () => {
  it("does not return raw exception text to the client", async () => {
    const res = await run(
      new NextRequest("http://x/api/benchmark/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{ not json C:\\secret\\path",
      })
    );
    expect(res.status).toBeGreaterThanOrEqual(400);
    const text = JSON.stringify(await res.json());
    expect(text).not.toMatch(/JSON|Unexpected|secret|SyntaxError/i);
  });
});
