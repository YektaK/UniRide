import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { typeAccepts } from "@/services/fleet-scenario-run";
import { verifyTypedSelection, type VerifyCase } from "@/services/typed-selection-verify";

const large = { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 };
const sedan = { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 };

/** A pickup route D -> stop -> D with the given arc minutes; the interval is [anchor - total, anchor]. */
function route(opts: { id: string; sw: number; so: number; arcs: number[]; anchor: number; label: "large" | "car";
  python?: Partial<{ start: number; end: number; minutes: number; large_ok: boolean; car_ok: boolean }> }) {
  const total = opts.arcs.reduce((a, b) => a + b, 0);
  const stops = ["D.Kampus", ...opts.arcs.slice(1).map((_, i) => `N${opts.id}${i}`), "D.Kampus"];
  const students = Array.from({ length: opts.sw + opts.so }, (_, i) => `${opts.id}-s${i}`);
  const start = Math.round((opts.anchor - total) * 100);
  const carOk = opts.sw === 0 && opts.so <= 4;
  return {
    route_details: opts.arcs.map((duration, i) => ({ location1: stops[i]!, location2: stops[i + 1]!, duration, distance: 0 })),
    student_ids: students, sw_count: opts.sw, so_count: opts.so, total_duration_minutes: total, label: opts.label,
    python: { start, end: Math.round(opts.anchor * 100), minutes: total, large_ok: true, car_ok: carOk, ...opts.python },
  };
}

function baseCase(routes: ReturnType<typeof route>[], maxLarge: number): VerifyCase {
  return {
    caseId: "c1", timeScale: 100, fixedType: large, minimiseType: sedan,
    limits: { maxRideTimeMinutes: 90, maxTourMinutes: 120 }, maxLarge, maxCars: null,
    pythonCooldowns: { large: 1000, car: 1000 },
    waves: [{ waveId: "w1", direction: "pickup", anchorMinutes: 765, routes }],
  };
}

describe("verifyTypedSelection", () => {
  it("confirms a good selection: no interval difference, proven assignment, empty problems", () => {
    const res = verifyTypedSelection(baseCase([
      route({ id: "a", sw: 0, so: 1, arcs: [10, 11], anchor: 765, label: "car" }),
      route({ id: "b", sw: 2, so: 0, arcs: [20, 30, 32], anchor: 765, label: "large" }),
    ], 1));
    expect(res.intervalDifferences).toEqual([]);
    expect(res.problems).toEqual([]);
    expect(res.recheck.failures).toEqual([]);
    expect(res.recheck.routesChecked).toBe(2);
    expect(res.assignment.status).toBe("proven");
    expect(res.assignment.cars).toBe(1);
    expect(res.assignment.countsByType).toEqual({ large: 1, sedan: 1 });
    expect(res.ok).toBe(true);
  });

  it("fails a selection that needs more vehicles of the fixed type than L", () => {
    // two overlapping Sw routes: only the large type fits a Sw student, L = 1 is too small
    const res = verifyTypedSelection(baseCase([
      route({ id: "a", sw: 1, so: 0, arcs: [10, 11], anchor: 765, label: "large" }),
      route({ id: "b", sw: 1, so: 0, arcs: [20, 21], anchor: 765, label: "large" }),
    ], 1));
    expect(res.assignment.status).toBe("infeasible_for_L");
    expect(res.ok).toBe(false);
  });

  it("reports every difference between its own intervals and the Python intervals", () => {
    const res = verifyTypedSelection(baseCase([
      route({ id: "a", sw: 0, so: 1, arcs: [10, 11], anchor: 765, label: "car", python: { start: 74401 } }), // one centi-minute off
      route({ id: "b", sw: 2, so: 0, arcs: [20, 30, 32], anchor: 765, label: "large", python: { car_ok: true } }),
    ], 1));
    const fields = res.intervalDifferences.map((d) => `${d.waveId}#${d.routeIndex}.${d.field}`);
    expect(fields).toContain("w1#0.start");
    expect(fields).toContain("w1#1.car_ok");
    expect(res.intervalDifferences.find((d) => d.field === "start")).toMatchObject({ python: 74401, typescript: 74400 });
    expect(res.ok).toBe(false);
  });

  it("refuses an endpoint off the centi-minute grid instead of rounding it", () => {
    const res = verifyTypedSelection(baseCase([
      route({ id: "a", sw: 0, so: 1, arcs: [10.005, 11], anchor: 765, label: "car" }),
    ], 1));
    expect(res.problems.join("|")).toContain("SELECTION_INTERVAL_PRECISION");
    expect(res.ok).toBe(false);
  });

  it("flags a label that the type does not accept", () => {
    const res = verifyTypedSelection(baseCase([
      route({ id: "a", sw: 2, so: 0, arcs: [20, 30, 32], anchor: 765, label: "car" }),
    ], 1));
    expect(res.problems.join("|")).toContain("label car");
    expect(res.ok).toBe(false);
  });

  it("verifies a batch of cases independently", () => {
    const good = baseCase([route({ id: "a", sw: 0, so: 1, arcs: [10, 11], anchor: 765, label: "car" })], 1);
    const bad = { ...baseCase([route({ id: "b", sw: 1, so: 0, arcs: [10, 11], anchor: 765, label: "large" }),
      route({ id: "c", sw: 1, so: 0, arcs: [10, 11], anchor: 765, label: "large" })], 1), caseId: "c2" };
    expect([good, bad].map((c) => verifyTypedSelection(c).ok)).toEqual([true, false]);
  });
});

describe("typeAccepts named export", () => {
  it("is the producer's function: pools, total capacity, tour and ride limits", () => {
    const facts = (sw: number, so: number, minutes: number, durations: number[]) => ({
      interval: { jobId: "j", routeIndex: 0, vehicleId: "v", direction: "pickup" as const, startMinutes: 0, endMinutes: minutes,
        occurrenceIds: [], swCount: sw, soCount: so },
      route: { vehicle_id: "v", route_details: durations.map((duration) => ({ location1: "a", location2: "b", duration, distance: 0 })),
        total_duration_minutes: minutes, sw_count: sw, so_count: so, student_ids: [] },
      minutes, direction: "pickup" as const,
    });
    const params = { maxRideTimeMinutes: 90, maxTourMinutes: 120 } as never;
    expect(typeAccepts(large, facts(4, 5, 100, [30, 30, 40]), params)).toBe(true);
    expect(typeAccepts(sedan, facts(1, 0, 10, [5, 5]), params)).toBe(false);
    expect(typeAccepts({ ...large, totalCapacity: 3 }, facts(2, 2, 10, [5, 5]), params)).toBe(false);
    expect(typeAccepts(large, facts(1, 0, 121, [60, 61]), params)).toBe(false);
    expect(typeAccepts({ ...large, rideLimit: 20 }, facts(1, 0, 100, [10, 30, 60]), params)).toBe(false);
  });
});
