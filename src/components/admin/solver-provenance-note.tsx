"use client";

import { useTranslations } from "next-intl";
import { solverSourceLabelKey } from "@/services/plan-solver-config";
import type { SolverProvenance } from "@/services/solver-provenance";

/**
 * Which algorithm settings, seed and fallback produced a calculated or saved plan (H17, M26;
 * DECISION_LOG S08). Reuses the daily-plan wording for source and seed. Null/absent
 * provenance (old plan, older optimizer) renders nothing; nothing is inferred.
 */
export function SolverProvenanceNote({ provenance }: { provenance?: SolverProvenance | null }) {
  const tConfig = useTranslations("page.admin.dailyPlan.solverConfig");
  const t = useTranslations("page.admin.vehiclePlanning.solverProvenance");
  if (!provenance) return null;

  const settings: string[] = [];
  if (provenance.effective_config_source) {
    const key = solverSourceLabelKey(provenance.effective_config_source);
    settings.push(key ? tConfig(`sources.${key}`) : provenance.effective_config_source);
  }
  if (provenance.effective_seed !== undefined) {
    settings.push(tConfig("seed", { seed: String(provenance.effective_seed) }));
  }

  const sentences: string[] = [];
  if (settings.length > 0) sentences.push(tConfig("line", { details: settings.join(" · ") }));
  if (provenance.fallback_reason) {
    sentences.push(t("fallback", { used: provenance.algorithm_used ?? "greedy_fallback", reason: provenance.fallback_reason }));
  }
  if (sentences.length === 0) return null;

  return (
    <p data-testid="solver-provenance" className="text-sm text-muted-foreground">
      {sentences.join(" ")}
    </p>
  );
}
