/**
 * Which algorithm settings and seed produced a daily plan (H17, DECISION_LOG A12).
 *
 * The optimizer reports `effective_config_source` ("default", "request", "promoted",
 * "promoted+request") and `effective_seed` on every ga_split answer. A plan can come from
 * several optimizer calls (one per wave); the server keeps the distinct values per call
 * (`null` = that call reported nothing, e.g. an older optimizer) and the view decides
 * between "single", "mixed" and "nothing". Nothing is inferred or computed here.
 */

export interface SolverConfigReport {
  readonly effective_config_source?: string | null;
  readonly effective_seed?: number | null;
}

/** Wire format: distinct values over the optimizer calls, `null` for a call that reported none. */
export interface SolverConfigSummary {
  readonly sources: readonly (string | null)[];
  readonly seeds: readonly (number | null)[];
}

function distinct<T>(values: readonly T[]): T[] {
  return [...new Set(values)];
}

/** Null when no optimizer call was made (blocked plan, empty day). */
export function collectSolverConfig(results: readonly SolverConfigReport[]): SolverConfigSummary | null {
  if (results.length === 0) return null;
  return {
    sources: distinct(results.map((result) => result.effective_config_source ?? null)),
    seeds: distinct(results.map((result) => result.effective_seed ?? null)),
  };
}

export type SolverConfigField<T> = { readonly kind: "single"; readonly value: T } | { readonly kind: "mixed" };

export interface PlanSolverConfig {
  readonly source: SolverConfigField<string> | null;
  readonly seed: SolverConfigField<number> | null;
}

/** Null: nothing reported. Several distinct values, or some calls silent: mixed. */
function buildField<T>(values: readonly (T | null)[]): SolverConfigField<T> | null {
  const reported = values.filter((value): value is T => value !== null);
  if (reported.length === 0) return null;
  if (reported.length === values.length && values.length === 1) return { kind: "single", value: reported[0]! };
  return { kind: "mixed" };
}

export function buildPlanSolverConfig(summary: SolverConfigSummary | null | undefined): PlanSolverConfig | null {
  if (!summary) return null;
  const source = buildField(summary.sources);
  const seed = buildField(summary.seeds);
  return source === null && seed === null ? null : { source, seed };
}

const SOURCE_LABEL_KEYS: Readonly<Record<string, string>> = {
  default: "default",
  request: "request",
  promoted: "promoted",
  "promoted+request": "promotedRequest",
};

/** i18n key of a known optimizer source value; null for an unknown value (the page shows it raw). */
export function solverSourceLabelKey(source: string): string | null {
  return Object.hasOwn(SOURCE_LABEL_KEYS, source) ? SOURCE_LABEL_KEYS[source]! : null;
}
