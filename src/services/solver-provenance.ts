/**
 * Solver provenance saved with a route plan (DECISION_LOG S08; audit H17/M26).
 *
 * `route_plans.solver_provenance` is a JSON object with only the keys the optimizer reported
 * when the plan was calculated. NULL (no key, old row) means unknown: nothing is inferred,
 * defaulted or backfilled. The same schema validates the client request on the server, so a
 * client can store nothing but these keys, as short plain tokens.
 */

import { z } from "zod";

/** Algorithm ids, config sources ("promoted+request") and reason codes: short plain tokens. */
const TOKEN = /^[A-Za-z0-9_.+\-]+$/;

const token = (max: number) => z.string().min(1).max(max).regex(TOKEN);

const fieldSchemas = {
  algorithm_requested: token(64),
  algorithm_used: token(64),
  fallback_reason: token(200),
  effective_config_source: token(64),
  effective_seed: z.number().int(),
} as const;

export const SOLVER_PROVENANCE_KEYS = Object.keys(fieldSchemas) as ReadonlyArray<keyof typeof fieldSchemas>;

export const solverProvenanceSchema = z
  .object({
    algorithm_requested: fieldSchemas.algorithm_requested.optional(),
    algorithm_used: fieldSchemas.algorithm_used.optional(),
    fallback_reason: fieldSchemas.fallback_reason.optional(),
    effective_config_source: fieldSchemas.effective_config_source.optional(),
    effective_seed: fieldSchemas.effective_seed.optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length > 0, { message: "solverProvenance must not be empty" });

export type SolverProvenance = z.infer<typeof solverProvenanceSchema>;

/** What a calculation result may carry: the raw optimizer fields and/or the BFF `meta` copy. */
export interface SolverProvenanceSource {
  readonly algorithm_requested?: unknown;
  readonly fallback_reason?: unknown;
  readonly effective_config_source?: unknown;
  readonly effective_seed?: unknown;
  readonly meta?: {
    readonly algorithmUsed?: unknown;
    readonly algorithmRequested?: unknown;
    readonly fallbackReason?: unknown;
    readonly effectiveConfigSource?: unknown;
    readonly effectiveSeed?: unknown;
  } | null;
}

/**
 * Null when the optimizer reported no provenance (older optimizer): the algorithm name alone is
 * already stored in `route_plans.algorithm_used`. Otherwise the reported fields that pass the
 * field schema (a malformed value is dropped, never repaired) plus `algorithm_used`: the
 * optimizer-reported `meta.algorithmUsed` when present (the truth for an M26 fallback), else
 * `calculationAlgorithm`, the choice captured when the calculation ran (never the dropdown at
 * save time). Nothing else is inferred.
 */
export function buildSolverProvenance(source: SolverProvenanceSource, calculationAlgorithm: string): SolverProvenance | null {
  const meta = source.meta ?? undefined;
  const reported: Partial<Record<keyof typeof fieldSchemas, unknown>> = {
    algorithm_requested: meta?.algorithmRequested ?? source.algorithm_requested,
    fallback_reason: meta?.fallbackReason ?? source.fallback_reason,
    effective_config_source: meta?.effectiveConfigSource ?? source.effective_config_source,
    effective_seed: meta?.effectiveSeed ?? source.effective_seed,
  };

  const value: Record<string, string | number> = {};
  for (const key of Object.keys(reported) as Array<keyof typeof reported>) {
    if (reported[key] === undefined || reported[key] === null) continue;
    const parsed = fieldSchemas[key].safeParse(reported[key]);
    if (parsed.success) value[key] = parsed.data;
  }
  if (Object.keys(value).length === 0) return null;

  const reportedUsed = fieldSchemas.algorithm_used.safeParse(meta?.algorithmUsed);
  const used = reportedUsed.success ? reportedUsed : fieldSchemas.algorithm_used.safeParse(calculationAlgorithm);
  if (used.success) value.algorithm_used = used.data;
  return value as SolverProvenance;
}
