/**
 * Travel-time matrix age (M4 / MT2 staleness half, DECISION_LOG T09).
 * Owner decision 2026-10-14: the C2 gate stays fail-closed. A stale or refresh-failed matrix
 * blocks the plan (`MATRIX_STALE`); when a plan is produced the matrix is fresh and its load
 * time and age are shown.
 */

export interface MatrixAge {
  readonly loadedAt: string | null;
  readonly ageSeconds: number | null;
}

export interface MatrixProvenanceInput {
  readonly loaded_at?: string | null;
  readonly age_seconds?: number | null;
}

/** Null when the optimizer sent no provenance (older optimizer). */
export function buildMatrixAge(provenance: MatrixProvenanceInput | undefined): MatrixAge | null {
  if (!provenance) return null;
  return { loadedAt: provenance.loaded_at ?? null, ageSeconds: provenance.age_seconds ?? null };
}
