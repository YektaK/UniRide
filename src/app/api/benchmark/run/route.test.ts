import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

vi.mock("server-only", () => ({}));

beforeEach(() => {
  process.env.OPTIMIZER_INTERNAL_API_KEY = "test-key";
});

type FetchResponse = { status: number; json: unknown };

function stubFetch(responses: FetchResponse[]) {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      const r = responses[Math.min(i, responses.length - 1)];
      i += 1;
      return {
        ok: r.status >= 200 && r.status < 300,
        status: r.status,
        json: async () => r.json,
        text: async () => JSON.stringify(r.json),
      };
    })
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete process.env.OPTIMIZER_INTERNAL_API_KEY;
});

function runRequest(runId?: string) {
  return new NextRequest("http://x/api/benchmark/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      ...(runId ? { run_id: runId } : {}),
      algorithms: [{ id: "ga", params: {} }],
      problems: ["berlin52"],
      settings: { n_runs: 1 },
    }),
  });
}

describe("POST /api/benchmark/run", () => {
  it("sets the owner cookie and does not leak owner_token to the browser", async () => {
    stubFetch([
      { status: 404, json: { detail: "not found" } }, // duplicate pre-check
      {
        status: 200,
        json: {
          run_id: "heap-run-1",
          status: "running",
          total_experiments: 1,
          start_time: "now",
          owner_token: "HEAPTOKEN",
        },
      },
    ]);
    const res = await POST(runRequest("heap-run-1"));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.owner_token).toBeUndefined();
    expect(res.cookies.get("benchmark_owner_heap-run-1")?.value).toBe(
      "HEAPTOKEN"
    );
  });

  it("treats precheck 403 (exists, owned by someone else) as a conflict", async () => {
    stubFetch([{ status: 403, json: { detail: "Forbidden" } }]);
    const res = await POST(runRequest("taken-run"));
    expect(res.status).toBe(409);
  });
});