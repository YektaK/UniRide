import { describe, expect, it } from "vitest";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

/** The CLI exactly as the npm script `experiments:fleet` starts its script: node --conditions=react-server --import tsx. */
const ROOT = path.resolve(__dirname, "..", "..");
const CLI = path.join(ROOT, "scripts", "verify-typed-selection.ts");

const large = { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 };
const sedan = { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 };
const stepsFor = (arcs: number[]) => arcs.map((duration, i) => ({
  location1: i === 0 ? "D.Kampus" : `N${i}`, location2: i === arcs.length - 1 ? "D.Kampus" : `N${i + 1}`, duration, distance: 0,
}));
const route = (sw: number, so: number, arcs: number[], label: "large" | "car", python: Record<string, number | boolean> = {}) => {
  const total = arcs.reduce((a, b) => a + b, 0);
  return {
    route_details: stepsFor(arcs), student_ids: Array.from({ length: sw + so }, (_, i) => `s${i}`), sw_count: sw, so_count: so,
    total_duration_minutes: total, label,
    python: { start: (765 - total) * 100, end: 76500, minutes: total, large_ok: true, car_ok: sw === 0, ...python },
  };
};
const make = (caseId: string, routes: ReturnType<typeof route>[], maxLarge: number) => ({
  caseId, timeScale: 100, fixedType: large, minimiseType: sedan, limits: { maxRideTimeMinutes: 90, maxTourMinutes: 120 },
  maxLarge, maxCars: null, pythonCooldowns: { large: 1000, car: 1000 },
  waves: [{ waveId: "w1", direction: "pickup", anchorMinutes: 765, routes }],
});

function runCli(payload: unknown) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "verify-typed-"));
  try {
    const input = path.join(dir, "in.json");
    fs.writeFileSync(input, typeof payload === "string" ? payload : JSON.stringify(payload));
    const run = spawnSync(process.execPath, ["--conditions=react-server", "--import", "tsx", CLI, input], {
      cwd: ROOT, encoding: "utf8", timeout: 60_000,
    });
    return { status: run.status, stdout: run.stdout, stderr: run.stderr };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

describe("scripts/verify-typed-selection.ts", () => {
  it("answers good input, too many cars of a type and an interval mismatch as JSON results", { timeout: 90_000 }, () => {
    const res = runCli({ cases: [
      make("good", [route(0, 1, [10, 11], "car"), route(2, 0, [20, 30, 32], "large")], 1),
      make("too_many_large", [route(1, 0, [10, 11], "large"), route(1, 0, [20, 21], "large")], 1),
      make("mismatch", [route(0, 1, [10, 11], "car", { start: 74401 })], 1),
    ] });
    expect(res.status).toBe(0);
    const out = JSON.parse(res.stdout) as { results: Array<{ caseId: string; ok: boolean; assignment: { status: string }; intervalDifferences: Array<{ field: string }> }> };
    const byId = Object.fromEntries(out.results.map((r) => [r.caseId, r]));
    expect(byId.good).toMatchObject({ ok: true, assignment: { status: "proven" }, intervalDifferences: [] });
    expect(byId.too_many_large).toMatchObject({ ok: false, assignment: { status: "infeasible_for_L" } });
    expect(byId.mismatch!.ok).toBe(false);
    expect(byId.mismatch!.intervalDifferences.map((d) => d.field)).toEqual(["start"]);
  });

  it("exits 2 with a JSON error on malformed input and prints no results", { timeout: 60_000 }, () => {
    const res = runCli("{ not json");
    expect(res.status).toBe(2);
    expect(res.stdout).toBe("");
    expect(JSON.parse(res.stderr).error).toEqual(expect.any(String));
  });
});
