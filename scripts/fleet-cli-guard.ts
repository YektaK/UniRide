import type { RerunDeps } from "../src/services/fleet-rerun-run";
import { assertOutsideHistoricalArchives } from "./fleet-archive-guard";

/**
 * The output-directory guard that scripts/run-fleet-scenarios.ts injects into runFleetRerun. Kept in one place so a test
 * can pin that the CLI uses the real historical-archive refusal (the run module itself names no result folder).
 */
export function cliGuardDeps(): Pick<RerunDeps, "assertOutputAllowed"> {
  return { assertOutputAllowed: assertOutsideHistoricalArchives };
}
