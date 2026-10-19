import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { fleetManifestSchema } from "@/services/fleet-scenario-report";
import { extendedFleetManifestSchema } from "@/services/fleet-scenario-archive";
import { HISTORICAL_ARCHIVE_DIRS, assertOutsideHistoricalArchives } from "../fleet-archive-guard";

// Research test: the historical-archive guard of the WP-E10 CLI and the historical manifests it protects. Moved from
// src/services/fleet-scenario-archive.test.ts without change of content; it lives outside src/ because it names the
// academic result folders, which the web application's source tree must not do.

describe("WP-E10 manifest: old format stays readable, new format is strict", () => {
  const results = path.resolve(process.cwd(), "docs/paper/results");
  const oldManifests = [
    "week-2026-10-05-fleet/run_manifest.json",
    "week-2026-10-05-fleet/extra/minivan-cap3/run_manifest.json",
    "week-2026-10-05-4sw5so/run_manifest.json",
  ];
  it.each(oldManifests.slice(0, 2))("the historical manifest %s still parses with the base schema but not as a v2 archive", (file) => {
    const value = JSON.parse(fs.readFileSync(path.join(results, file), "utf8"));
    expect(() => fleetManifestSchema.parse(value)).not.toThrow();
    expect(() => extendedFleetManifestSchema.parse(value)).toThrow();
  });
  it("the historical archive directories are refused as an output location (g)", () => {
    expect(HISTORICAL_ARCHIVE_DIRS.length).toBeGreaterThanOrEqual(3);
    for (const dir of HISTORICAL_ARCHIVE_DIRS) {
      expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), dir))).toThrow();
      expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), dir, "rerun"))).toThrow();
    }
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), "docs/paper/results/week-2026-10-05-fleet-rerun"))).not.toThrow();
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), ".temp/experiments/x"))).not.toThrow();
    // P-1: a run worktree writes its campaign and a rule (e) second run below docs/paper/results, next to (not inside) the historical archives
    const results = "docs/paper/results";
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), results, "week-2026-10-05-fleet-rerun-large-sedan"))).not.toThrow();
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), results, "week-2026-10-05-fleet-rerun-large-sedan/rule_e_second_run_2026-10-05"))).not.toThrow();
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), results, "week-2026-10-05-fleet/rule_e_second_run_2026-10-05"))).toThrow();
  });
});
