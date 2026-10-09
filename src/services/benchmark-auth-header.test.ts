import { afterEach, describe, expect, it, vi } from "vitest";

const { getAuthTokenMock } = vi.hoisted(() => ({ getAuthTokenMock: vi.fn() }));
vi.mock("@/lib/admin-api", () => ({ getAuthToken: getAuthTokenMock }));

import { checkBenchmarkApiHealth, fetchProblems, startBenchmark } from "./benchmark-service";

describe("benchmark service sends the admin bearer token", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    getAuthTokenMock.mockReset();
  });

  it("adds Authorization to GET and POST calls", async () => {
    getAuthTokenMock.mockResolvedValue("tok-123");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await checkBenchmarkApiHealth();
    await fetchProblems();
    await startBenchmark([], ["eil51"], {} as never);

    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const call of fetchMock.mock.calls) {
      expect((call[1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer tok-123" });
    }
  });

  it("makes no network call without a session", async () => {
    getAuthTokenMock.mockResolvedValue(null);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(checkBenchmarkApiHealth()).resolves.toBe(false);
    await expect(fetchProblems()).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
