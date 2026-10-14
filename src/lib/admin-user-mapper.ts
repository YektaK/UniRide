import type { User } from "@/types";

/**
 * Raw row shape returned by GET /api/admin/users (`select("*")` on `users`,
 * see src/app/api/admin/users/route.ts and src/types/db.ts). The API contract
 * is snake_case; some older callers/fixtures may already carry camelCase.
 */
export type AdminUserRow = Partial<User> & {
  disability_type?: "Sw" | "So" | null;
  location_code?: string | null;
};

/**
 * Boundary mapper: normalises one admin users-API row so consumers can read
 * `disabilityType` / `locationCode`. Original fields are preserved (the
 * optimizer BFF accepts both spellings). Audit finding H15.
 */
export function normalizeAdminUser(row: AdminUserRow): User {
  const disabilityType = row.disability_type ?? row.disabilityType ?? null;
  const locationCode = row.location_code ?? row.locationCode ?? undefined;
  return { ...(row as User), disabilityType, locationCode };
}
