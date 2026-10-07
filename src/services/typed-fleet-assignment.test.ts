import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import type { PreviewRouteInterval } from "./dudullu-preview";
import {
  assignTypedVehicles,
  verifyTypedAssignment,
  type TypedFleetType,
} from "./typed-fleet-assignment";

function route(
  index: number,
  start: number,
  end: number,
  sw: number,
  so: number,
  jobId = "job",
): PreviewRouteInterval {
  return {
    jobId,
    routeIndex: index,
    vehicleId: "V",
    direction: "pickup",
    startMinutes: start,
    endMinutes: end,
    occurrenceIds: [`${jobId}:${index}`],
    swCount: sw,
    soCount: so,
  };
}

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

describe("assignTypedVehicles unit cases", () => {
  it("puts overlapping So routes on L large + the minimum cars, with deterministic ids", () => {
    const intervals = [route(0, 0, 30, 0, 2), route(1, 5, 35, 0, 2), route(2, 10, 40, 0, 2)];
    const result = assignTypedVehicles({ intervals, types: [large(1), sedan()] });
    expect(result.status).toBe("proven");
    expect(result.minimumCount).toBe(2);
    expect(result.countsByType).toEqual({ large: 1, car: 2 });
    expect(verifyTypedAssignment(result.assignments, [large(1), sedan()])).toEqual([]);
    expect(result.assignments.map((item) => item.physicalVehicleId).sort()).toEqual(["C1", "C2", "L1"]);
    expect(assignTypedVehicles({ intervals, types: [large(1), sedan()] })).toEqual(result);
  });

  it("is infeasible_for_L when Sw routes overlap and L is too small", () => {
    const intervals = [route(0, 0, 30, 1, 0), route(1, 10, 40, 2, 1), route(2, 50, 60, 0, 1)];
    const result = assignTypedVehicles({ intervals, types: [large(1), sedan()] });
    expect(result.status).toBe("infeasible_for_L");
    expect(result.reasonCodes).toEqual(["FIXED_TYPE_TOO_SMALL"]);
    expect(assignTypedVehicles({ intervals, types: [large(0), sedan()] }).status).toBe("infeasible_for_L");
    expect(assignTypedVehicles({ intervals, types: [large(2), sedan()] }).status).toBe("proven");
  });

  it("never labels an Sw route as a car and blocks routes no type can carry", () => {
    const sw = assignTypedVehicles({ intervals: [route(0, 0, 10, 1, 0)], types: [large(1), sedan()] });
    expect(sw.assignments[0].vehicleType).toBe("large");
    expect(sw.minimumCount).toBe(0);
    const blocked = assignTypedVehicles({ intervals: [route(0, 0, 10, 5, 0)], types: [large(3), sedan()] });
    expect(blocked.status).toBe("blocked_data");
    expect(blocked.reasonCodes).toEqual(["TYPE_CAPACITY_UNCOVERED"]);
    expect(assignTypedVehicles({ intervals: [], types: [] }).reasonCodes).toEqual(["FLEET_INVALID"]);
  });

  it("applies the per-type cooldown and half-open end boundaries", () => {
    const touching = [route(0, 0, 10, 0, 1), route(1, 20, 30, 0, 1)];
    expect(assignTypedVehicles({ intervals: touching, types: [large(0), sedan(10)] }).minimumCount).toBe(1);
    expect(assignTypedVehicles({ intervals: touching, types: [large(0), sedan(11)] }).minimumCount).toBe(2);
  });

  it("supports an optional cap on cars", () => {
    const intervals = [route(0, 0, 30, 0, 1), route(1, 5, 35, 0, 1), route(2, 10, 40, 0, 1)];
    const capped = assignTypedVehicles({ intervals, types: [large(1), sedan(10, 1)] });
    expect(capped.status).toBe("infeasible_for_L");
    expect(capped.reasonCodes).toEqual(["MINIMISE_CAP_EXCEEDED"]);
    expect(assignTypedVehicles({ intervals, types: [large(1), sedan(10, 2)] }).minimumCount).toBe(2);
  });

  it("minimises car minutes after the car count", () => {
    const intervals = [route(0, 0, 50, 0, 1), route(1, 5, 8, 0, 1)];
    const result = assignTypedVehicles({ intervals, types: [large(1), sedan()] });
    expect(result.minimumCount).toBe(1);
    expect(result.minimiseMinutes).toBe(3);
    expect(result.minimiseMinutesProven).toBe(true);
    expect(result.usageWindows).toEqual([
      { vehicleId: "C1", firstStartMinutes: 5, lastEndMinutes: 8, busyMinutes: 3, routeCount: 1, jobIds: ["job"] },
    ]);
    expect(result.hourlyOccupiedVehiclesByType).toEqual({ large: { "00:00": 1 }, car: { "00:00": 1 } });
  });

  it("never reports proven after a node budget hit", () => {
    const intervals = Array.from({ length: 12 }, (_, i) => route(i, i * 3, i * 3 + 25, 0, 1));
    const tight = assignTypedVehicles({ intervals, types: [large(1), sedan()], nodeBudget: 3 });
    expect(["witness", "indeterminate"]).toContain(tight.status);
    expect(tight.status).not.toBe("proven");
    const loose = assignTypedVehicles({ intervals, types: [large(1), sedan()] });
    expect(loose.status).toBe("proven");
  });

  it("reports witness when a smaller car count hits the budget and the next count succeeds", () => {
    const data: [number, number, number, number][] = [
      [46, 67, 0, 1], [68, 95, 0, 3], [68, 77, 0, 1], [34, 39, 1, 2], [32, 52, 1, 2], [28, 43, 0, 3],
      [55, 63, 0, 2], [6, 35, 0, 2], [9, 37, 0, 2], [7, 19, 0, 1], [79, 85, 0, 3], [77, 101, 1, 2], [6, 21, 1, 1],
    ];
    const intervals = data.map(([start, end, sw, so], i) => route(i, start, end, sw, so));
    const types = [large(2), sedan()];
    const exact = assignTypedVehicles({ intervals, types });
    expect(exact.status).toBe("proven");
    expect(exact.lowerBoundsByType.car).toBe(3);
    expect(exact.minimumCount).toBe(3);
    // Budget 15 (found by hand) is exhausted at 3 cars and sufficient at 4.
    const tight = assignTypedVehicles({ intervals, types, nodeBudget: 15 });
    expect(tight.status).toBe("witness");
    expect(tight.minimumCount).toBe(4);
    expect(tight.minimumCount).toBeGreaterThan(tight.lowerBoundsByType.car);
    expect(verifyTypedAssignment(tight.assignments, types)).toEqual([]);
  });

  it("handles zero cooldown and a zero-duration route", () => {
    const zero = (cooldown: number) => [large(0, cooldown), sedan(cooldown)];
    const chain = [route(0, 0, 10, 0, 1), route(1, 10, 10, 0, 1), route(2, 10, 20, 0, 1)];
    const shared = assignTypedVehicles({ intervals: chain, types: zero(0) });
    expect(shared.status).toBe("proven");
    expect(shared.minimumCount).toBe(1);
    expect(verifyTypedAssignment(shared.assignments, zero(0))).toEqual([]);
    const inside = [route(0, 5, 15, 0, 1), route(1, 10, 10, 0, 1)];
    expect(assignTypedVehicles({ intervals: inside, types: zero(0) }).minimumCount).toBe(2);
    const lone = assignTypedVehicles({ intervals: [route(0, 7, 7, 0, 1)], types: zero(0) });
    expect(lone.minimumCount).toBe(1);
    expect(lone.minimiseMinutes).toBe(0);
  });
});

// ---------------------------------------------------------------------------------------
// Brute force on tiny seeded instances.

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Peak of [start, end + cooldown) intervals; valid for durations >= 1 and cooldown >= 1. */
function peak(items: readonly PreviewRouteInterval[], cooldown: number): number {
  let best = 0;
  for (const probe of items) {
    const count = items.filter((item) =>
      item.startMinutes <= probe.startMinutes && probe.startMinutes < item.endMinutes + cooldown
    ).length;
    best = Math.max(best, count);
  }
  return best;
}

describe("assignTypedVehicles brute force", () => {
  it("matches enumeration of all labellings (seeded)", () => {
    const random = mulberry32(20261008);
    let compared = 0;
    let infeasible = 0;
    for (let trial = 0; trial < 300; trial += 1) {
      const n = 1 + Math.floor(random() * 9);
      const intervals = Array.from({ length: n }, (_, i) => {
        const start = Math.floor(random() * 40);
        const sw = random() < 0.35 ? 1 + Math.floor(random() * 2) : 0;
        return route(i, start, start + 1 + Math.floor(random() * 14), sw, Math.floor(random() * 6));
      }).filter((item) => item.soCount <= 5 && item.swCount <= 2);
      const cdLarge = 1 + Math.floor(random() * 10);
      const cdCar = 1 + Math.floor(random() * 10);
      const bigCount = Math.floor(random() * 4);
      const types: TypedFleetType[] = [
        large(bigCount, cdLarge, 2, 5),
        { ...sedan(cdCar, undefined, 3) },
      ];
      const result = assignTypedVehicles({ intervals, types });
      if (intervals.length === 0) continue;

      // Enumerate every labelling over eligible types.
      let bestCars = Number.POSITIVE_INFINITY;
      let bestMinutes = Number.POSITIVE_INFINITY;
      let coverable = true;
      const labels = new Array<number>(intervals.length).fill(0);
      const carOk = intervals.map((item) => item.swCount === 0 && item.soCount <= 3);
      const bigOk = intervals.map((item) => item.swCount <= 2 && item.soCount <= 5);
      const walk = (index: number): void => {
        if (index === intervals.length) {
          const big = intervals.filter((_, i) => labels[i] === 0);
          const car = intervals.filter((_, i) => labels[i] === 1);
          if (peak(big, cdLarge) > bigCount) return;
          const cars = peak(car, cdCar);
          const minutes = car.reduce((sum, item) => sum + item.endMinutes - item.startMinutes, 0);
          if (cars < bestCars || (cars === bestCars && minutes < bestMinutes)) {
            bestCars = cars;
            bestMinutes = minutes;
          }
          return;
        }
        for (const label of [0, 1]) {
          if (label === 0 ? !bigOk[index] : !carOk[index]) continue;
          labels[index] = label;
          walk(index + 1);
        }
      };
      if (intervals.some((_, i) => !bigOk[i] && !carOk[i])) coverable = false;
      if (!coverable) {
        expect(result.status).toBe("blocked_data");
        continue;
      }
      walk(0);
      compared += 1;
      if (!Number.isFinite(bestCars)) {
        infeasible += 1;
        expect(result.status).toBe("infeasible_for_L");
        continue;
      }
      expect(result.status).toBe("proven");
      expect(result.minimumCount).toBe(bestCars);
      expect(result.minimiseMinutes).toBe(bestMinutes);
      expect(result.minimiseMinutesProven).toBe(true);
      expect(verifyTypedAssignment(result.assignments, types)).toEqual([]);
      expect(result.countsByType.large ?? 0).toBeLessThanOrEqual(bigCount);
      expect(result.countsByType.car ?? 0).toBe(bestCars);
    }
    expect(compared).toBeGreaterThan(250);
    expect(infeasible).toBeGreaterThan(0);
  });
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
