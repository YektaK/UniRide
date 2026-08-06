import { describe, expect, it } from "vitest";
import { NextRequest, NextResponse } from "next/server";
import {
  getOwnerToken,
  ownerCookieName,
  setOwnerCookie,
} from "./benchmark-owner-cookie";

describe("benchmark owner cookie", () => {
  it("builds a run-scoped cookie name", () => {
    expect(ownerCookieName("run-1")).toBe("benchmark_owner_run-1");
  });

  it("round-trips the token via the cookie", () => {
    const res = NextResponse.json({ ok: true });
    setOwnerCookie(res, "run-1", "TOKEN");
    const cookie = res.cookies.get("benchmark_owner_run-1");
    expect(cookie?.value).toBe("TOKEN");
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.maxAge).toBe(7200);
    expect(cookie?.sameSite).toBe("lax");
    expect(cookie?.path).toBe("/api/benchmark");

    const req = new NextRequest("http://x/api/benchmark/status", {
      headers: { cookie: "benchmark_owner_run-1=TOKEN" },
    });
    expect(getOwnerToken(req, "run-1")).toBe("TOKEN");
    expect(getOwnerToken(req, "run-2")).toBeUndefined();
  });
});
