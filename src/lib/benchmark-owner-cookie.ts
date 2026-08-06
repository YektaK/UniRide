import type { NextRequest, NextResponse } from "next/server";

export const OWNER_COOKIE_PREFIX = "benchmark_owner_";
export const OWNER_COOKIE_MAX_AGE = 7200;

export function ownerCookieName(runId: string): string {
  return `${OWNER_COOKIE_PREFIX}${runId}`;
}

export function getOwnerToken(
  request: NextRequest,
  runId: string
): string | undefined {
  return request.cookies.get(ownerCookieName(runId))?.value;
}

export function setOwnerCookie(
  response: NextResponse,
  runId: string,
  token: string
): void {
  response.cookies.set(ownerCookieName(runId), token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/api/benchmark",
    maxAge: OWNER_COOKIE_MAX_AGE,
  });
}

export function isRunExistsStatus(status: number): boolean {
  return status === 200 || status === 403;
}
