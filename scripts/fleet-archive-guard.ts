import path from "node:path";

// Output-directory guard of the WP-E10 fleet re-run CLI (scripts/run-fleet-scenarios.ts). It names the historical
// academic result folders, so it lives here and is injected into the run (`RerunDeps.assertOutputAllowed`); nothing
// under src/ knows these folders (the served web application must not depend on academic result artifacts).

/** Historical campaigns (rule (g)): never written to, never a target of a re-run. Paths relative to the repository root. */
export const HISTORICAL_ARCHIVE_DIRS = [
  "docs/paper/results/week-2026-10-05",
  "docs/paper/results/week-2026-10-05-4sw5so",
  "docs/paper/results/week-2026-10-05-fleet",
] as const;

/** Refuses an output directory that is, or lies inside, a historical archive directory. */
export function assertOutsideHistoricalArchives(out: string, root = process.cwd()): void {
  const target = path.resolve(out);
  for (const dir of HISTORICAL_ARCHIVE_DIRS) {
    const relative = path.relative(path.resolve(root, dir), target);
    if (relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative))) {
      throw new Error("Output directory lies inside a historical archive; choose a new directory.");
    }
  }
}
