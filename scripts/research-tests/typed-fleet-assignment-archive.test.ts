import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import type { PreviewRouteInterval } from "@/services/dudullu-preview";
import {
  assignTypedVehicles,
  verifyTypedAssignment,
  type TypedFleetType,
} from "@/services/typed-fleet-assignment";

// Research test (reads the historical week-2026-10-05 result archive), kept outside src/ so the web application's source
// tree names no academic result folder. Moved from src/services/typed-fleet-assignment.test.ts without change of content.

const large = (count: number, cooldownMinutes = 10, sw = 4, so = 10): TypedFleetType => ({
  typeId: "large",
  swCapacity: sw,
  soCapacity: so,
  cooldownMinutes,
  role: "fixed",
  count,
});
const sedan = (cooldownMinutes = 10, maxCount?: number, so = 4): TypedFleetType => ({
  typeId: "car",
  swCapacity: 0,
  soCapacity: so,
  cooldownMinutes,
  role: "minimise",
  ...(maxCount === undefined ? {} : { maxCount }),
});


// ---------------------------------------------------------------------------------------
// T6 / T7 on the archived week-2026-10-05 routes (4 Sw / 10 So large, 0 Sw / 4 So car,
// both with a 10 minute cooldown; the same types as scripts/plan_fleet_mix.py).

const ARCHIVE = join(process.cwd(), "docs", "paper", "results", "week-2026-10-05");

interface ArchivedRun {
  readonly key: string;
  readonly date: string;
  readonly rideLimit: number;
  readonly intervals: PreviewRouteInterval[];
  readonly minimumVehicles: number;
  readonly assignedVehicleCount: number;
}

function loadArchive(): ArchivedRun[] {
  return readdirSync(ARCHIVE)
    .filter((name) => /^\d{4}-\d\d-\d\d_R\d+_repeat1\.response\.json$/.test(name))
    .sort()
    .map((name) => {
      const match = /^(\d{4}-\d\d-\d\d)_R(\d+)_/.exec(name);
      const data = JSON.parse(readFileSync(join(ARCHIVE, name), "utf-8")) as {
        routeIntervals: PreviewRouteInterval[];
        assignments: { physicalVehicleId: string }[];
        vehicleSummary: { minimumVehicles: number };
      };
      return {
        key: `${match?.[1]}|${match?.[2]}`,
        date: match?.[1] ?? "",
        rideLimit: Number(match?.[2]),
        intervals: data.routeIntervals,
        minimumVehicles: data.vehicleSummary.minimumVehicles,
        assignedVehicleCount: new Set(data.assignments.map((item) => item.physicalVehicleId)).size,
      };
    });
}

describe("archived week-2026-10-05 routes", () => {
  const runs = loadArchive();

  it("loads all 20 archived runs", () => {
    expect(runs).toHaveLength(20);
  });

  it("T6: a single minimise type equals the archived assignPhysicalVehicles minimum", () => {
    for (const run of runs) {
      const single: TypedFleetType = { ...large(0), role: "minimise", count: undefined };
      const result = assignTypedVehicles({ intervals: run.intervals, types: [single], nodeBudget: 2_000_000 });
      expect(result.status, run.key).toBe("proven");
      expect(result.minimumCount, run.key).toBe(run.minimumVehicles);
      expect(result.countsByType.large, run.key).toBe(run.assignedVehicleCount);
    }
  });

  it("T7: reproduces every (L, C, proven) row of fleet_mix.csv", () => {
    const rows = readFileSync(join(ARCHIVE, "fleet_mix.csv"), "utf-8")
      .trim()
      .split("\n")
      .slice(1)
      .map((line) => line.split(","))
      .filter((cells) => cells[0] === "day")
      .map((cells) => ({
        key: `${cells[1]}|${cells[2]}`,
        L: Number(cells[3]),
        C: Number(cells[4]),
        proven: cells[5] === "yes",
        largeMinutes: Number(cells[6]),
        carMinutes: Number(cells[7]),
      }));
    expect(rows.length).toBe(50);
    const byKey = new Map(runs.map((run) => [run.key, run]));
    for (const row of rows) {
      const run = byKey.get(row.key);
      expect(run, row.key).toBeDefined();
      const types = [large(row.L), sedan()];
      const result = assignTypedVehicles({ intervals: run?.intervals ?? [], types, nodeBudget: 2_000_000 });
      const label = `${row.key} L=${row.L}`;
      expect(result.minimumCount, label).toBe(row.C);
      expect(result.status === "proven", label).toBe(row.proven);
      const total = (run?.intervals ?? []).reduce((sum, item) => sum + item.endMinutes - item.startMinutes, 0);
      expect(row.largeMinutes + row.carMinutes, label).toBe(total);
      // The archive reports one witness split; ours is the proven minimum car-minutes.
      expect(result.minimiseMinutes ?? Infinity, label).toBeLessThanOrEqual(row.carMinutes);
      expect(verifyTypedAssignment(result.assignments, types), label).toEqual([]);
    }
  });

  it("T7: L just below the forced-large peak is infeasible_for_L", () => {
    const rowsByKey = new Map<string, number>();
    for (const line of readFileSync(join(ARCHIVE, "fleet_mix.csv"), "utf-8").trim().split("\n").slice(1)) {
      const cells = line.split(",");
      if (cells[0] !== "day") continue;
      const key = `${cells[1]}|${cells[2]}`;
      rowsByKey.set(key, Math.min(rowsByKey.get(key) ?? Infinity, Number(cells[3])));
    }
    for (const run of runs) {
      const lmin = rowsByKey.get(run.key) ?? 0;
      if (lmin < 1) continue;
      const result = assignTypedVehicles({ intervals: run.intervals, types: [large(lmin - 1), sedan()] });
      expect(result.status, run.key).toBe("infeasible_for_L");
    }
  });
});
