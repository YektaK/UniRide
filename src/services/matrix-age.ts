/**
 * Travel-time matrix age (M4 / MT2 staleness half, DECISION_LOG T09).
 * Owner decision 2026-10-13: a stale matrix is kept but flagged. The plan shows its age and
 * warns above a configurable threshold; nothing here ever blocks or fails a plan.
 */

export const MATRIX_MAX_AGE_ENV = "UNIRIDE_MATRIX_MAX_AGE_SECONDS";
export const DEFAULT_MATRIX_MAX_AGE_SECONDS = 24 * 60 * 60;

export interface MatrixAge {
  readonly loadedAt: string | null;
  readonly ageSeconds: number | null;
  /** True when the matrix served is the last-known-good one kept after a failed refresh. */
  readonly refreshFailed: boolean;
  readonly maxAgeSeconds: number;
}

/** Positive whole seconds from the server-side env value; anything else is the 24 h default. */
export function resolveMatrixMaxAgeSeconds(raw: string | undefined): number {
  const text = raw?.trim() ?? "";
  if (!/^\d{1,9}$/.test(text)) return DEFAULT_MATRIX_MAX_AGE_SECONDS;
  const seconds = Number(text);
  return seconds > 0 ? seconds : DEFAULT_MATRIX_MAX_AGE_SECONDS;
}

export interface MatrixProvenanceInput {
  readonly loaded_at?: string | null;
  readonly age_seconds?: number | null;
  readonly refresh_failed?: boolean;
}

/** Null when the optimizer sent no provenance (older optimizer). */
export function buildMatrixAge(
  provenance: MatrixProvenanceInput | undefined,
  maxAgeSeconds: number,
): MatrixAge | null {
  if (!provenance) return null;
  return {
    loadedAt: provenance.loaded_at ?? null,
    ageSeconds: provenance.age_seconds ?? null,
    refreshFailed: provenance.refresh_failed === true,
    maxAgeSeconds,
  };
}
