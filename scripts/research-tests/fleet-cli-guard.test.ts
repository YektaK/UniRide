import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { assertOutsideHistoricalArchives } from "../fleet-archive-guard";
import { cliGuardDeps } from "../fleet-cli-guard";

// E1: the output guard is an injected dependency of runFleetRerun, so the CLI must inject the real one.
describe("the fleet re-run CLI injects the real historical-archive guard", () => {
  it("the CLI guard dependency is assertOutsideHistoricalArchives itself", () => {
    expect(cliGuardDeps().assertOutputAllowed).toBe(assertOutsideHistoricalArchives);
  });

  it("scripts/run-fleet-scenarios.ts takes its guard from cliGuardDeps() and defines no guard of its own", () => {
    const text = fs.readFileSync(path.join(__dirname, "..", "run-fleet-scenarios.ts"), "utf8");
    expect(text).toMatch(/\.\.\.cliGuardDeps\(\)/);
    expect(text).not.toMatch(/assertOutputAllowed\s*[:=]/);
    expect(text).not.toMatch(/assertOutsideHistoricalArchives/);
  });
});
