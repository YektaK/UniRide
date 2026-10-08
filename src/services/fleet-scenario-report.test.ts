import { describe, expect, it } from "vitest";
import {
  aggregateFleetWeeks, carWindowRows, clock, fleetDailyRows, fleetManifestSchema, manifestRun, type FleetDailyRow, type FleetManifest,
} from "./fleet-scenario-report";
import type { FleetScenarioDay, ScenarioResult } from "./fleet-scenario-run";

const result = (scenario: "A" | number, over: Partial<ScenarioResult> = {}): ScenarioResult => ({
  scenario, largeLimit: scenario === "A" ? 2 : scenario, status: "ok", reasonCodes: [], cars: scenario === "A" ? 0 : 1,
  carsStatus: scenario === "A" ? null : "proven_over_menu", largeVehicles: 2, largeVehiclesProven: scenario === "A" ? true : null,
  routes: [], largeRoutes: 3, carRoutes: 1, minutesByType: { large: 100, sedan: 20 }, totalVehicleMinutes: 120,
  ride: { passengers: 4, mean: 10, median: 9, p90: 15, max: 16 },
  carUsageWindows: scenario === "A" ? [] : [{ carId: "C1", windowStartMinutes: 500, windowEndMinutes: 620.5, busyMinutes: 40, routeCount: 2, waves: ["w1", "w2"] }],
  selection: scenario === "A" ? null : { status: "optimal", cars: 1, carMinutes: 20, claim: null, optionByWave: {}, diagnostics: {}, stats: {} },
  assignment: scenario === "A" ? null : { status: "proven", reasonCodes: [], nodes: 4, lowerBoundsByType: {}, problems: [] },
  ...over,
});
const day = (date: string, scenarios: ScenarioResult[], status: FleetScenarioDay["status"] = "ready"): FleetScenarioDay => ({
  serviceDate: date, status, reasonCodes: [], dbVehiclesConsulted: false, limits: { maxRideTimeMinutes: 60, maxTourMinutes: 150 },
  students: 5, legs: 10, waves: 4, occurrenceLabels: {}, matrix: null, menu: [], scenarios,
});
const fixed = { typeId: "large" }, minimise = { typeId: "sedan" };
const WEEK = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"];

describe("fleet scenario tables", () => {
  it("formats clock times and car usage windows", () => {
    expect(clock(500)).toBe("08:20");
    expect(clock(620.5)).toBe("10:20:30");
    const rows = carWindowRows(day(WEEK[0], [result(1)]), 60);
    expect(rows).toEqual([{ date: WEEK[0], ride_limit: 60, scenario: "L1", car_id: "C1", window_start: "08:20", window_end: "10:20:30", busy_minutes: 40, routes: 2, waves: ["w1", "w2"] }]);
  });
  it("derives daily rows with minutes by type, ride statistics and car windows", () => {
    const [a, l1] = fleetDailyRows(day(WEEK[0], [result("A"), result(1)]), ["A", 1], 60, 150, fixed, minimise);
    expect(a).toMatchObject({ scenario: "A", cars: 0, large_vehicles: 2, large_vehicles_proven: true, car_first_start: null });
    expect(l1).toMatchObject({
      scenario: "L1", weekday: "monday", cars: 1, cars_status: "proven_over_menu", large_vehicle_minutes: 100, car_vehicle_minutes: 20,
      total_vehicle_minutes: 120, ride_mean: 10, ride_p90: 15, car_first_start: "08:20", car_last_end: "10:20:30", car_busy_minutes: 40,
      selection_status: "optimal", assignment_status: "proven",
    });
  });
  it("keeps one row per requested scenario for blocked days and infeasible results", () => {
    const blocked = day(WEEK[0], [], "blocked_data");
    expect(fleetDailyRows(blocked, ["A", 1], 60, 150, fixed, minimise).map((r) => [r.scenario, r.status, r.cars])).toEqual([["A", "blocked_data", null], ["L1", "blocked_data", null]]);
    const infeasible = day(WEEK[0], [result(1, { status: "infeasible_for_L", cars: null, reasonCodes: ["SW_DEMAND_EXCEEDS_LARGE_CAPACITY"] })]);
    expect(fleetDailyRows(infeasible, [1], 60, 150, fixed, minimise)[0]).toMatchObject({ status: "infeasible_for_L", reason_codes: ["SW_DEMAND_EXCEEDS_LARGE_CAPACITY"] });
  });

  const weekRows = (carsPerDay: number[], proven = true): FleetDailyRow[] => WEEK.flatMap((date, i) =>
    fleetDailyRows(day(date, [result(1, { cars: carsPerDay[i], carsStatus: proven ? "proven_over_menu" : "witness" })]), [1], 60, 150, fixed, minimise));
  it("reports weekly cars as the max over days and also the per-day need (Q5)", () => {
    const [week] = aggregateFleetWeeks(weekRows([0, 2, 1, 3, 0]));
    expect(week).toMatchObject({
      week_of: "2026-10-05", ride_limit: 60, scenario: "L1", weekly_cars: 3, cars_day_sum: 6,
      monday_cars: 0, tuesday_cars: 2, wednesday_cars: 1, thursday_cars: 3, friday_cars: 0,
      complete_week: true, all_proven: true, total_vehicle_minutes: 600, ride_passengers: 20, ride_mean: 10, ride_max: 16,
    });
    expect(aggregateFleetWeeks(weekRows([0, 2, 1, 3, 0], false))[0].all_proven).toBe(false);
  });
  it("does not report weekly figures for an incomplete or blocked week", () => {
    const rows = weekRows([1, 1, 1, 1, 1]).slice(0, 4);
    expect(aggregateFleetWeeks(rows)[0]).toMatchObject({ complete_week: false, weekly_cars: null, cars_day_sum: null, total_vehicle_minutes: null });
    const blocked = [...weekRows([1, 1, 1, 1, 1]).slice(0, 4),
      ...fleetDailyRows(day(WEEK[4], [], "blocked_data"), [1], 60, 150, fixed, minimise)];
    expect(aggregateFleetWeeks(blocked)[0]).toMatchObject({ complete_week: false, weekly_cars: null });
  });
});

describe("fleet manifest schema", () => {
  const manifest = (): FleetManifest => ({
    git_commit: "a".repeat(40), dirty_working_tree: false, timestamp: "2026-10-08T10:00:00.000Z",
    parameters: { dates: WEEK, ride_limits: [60], tour_limit: 150, scenarios: ["A", "L1"], max_cars: null, node_budget: 200000, selection_time_limit_seconds: 30, admission_mode: "assume_confirmed" },
    fleet_types: [{ typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 }, { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 }],
    fleet_types_source: "cli", fixed_type: "large", minimize_type: "sedan", db_vehicles_consulted: false,
    algorithms: { baseline: "ga_split", menu: "ga_split_hf" }, termination_protocol: "native",
    ga_defaults: {}, ga_effective_configuration: {}, effective_seed: 42, hf_effective_configuration: {}, hf_effective_seed: 42,
    selection_solver: { name: "cp-sat", version: "9.x", random_seed: 20261008, num_workers: 1, time_limit_seconds: 30 },
    vehicle_count_scope: "scope", weekly_cars_definition: "definition",
    runs: [manifestRun(day(WEEK[0], [result("A"), result(1)]), 60, ["f.json"], "m.json", { sha256: "x" }, [], [])],
    state: "completed", completed_at: "2026-10-08T10:05:00.000Z",
  });
  it("accepts a complete manifest and records the per-run statuses", () => {
    const value = manifest();
    expect(() => fleetManifestSchema.parse(value)).not.toThrow();
    expect(value.runs[0].scenarios).toEqual([
      { scenario: "A", status: "ok", cars: 0, cars_status: null, selection_status: null, assignment_status: null },
      { scenario: "L1", status: "ok", cars: 1, cars_status: "proven_over_menu", selection_status: "optimal", assignment_status: "proven" },
    ]);
  });
  it("rejects a manifest that claims the DB vehicles were consulted or lacks the fleet types", () => {
    expect(() => fleetManifestSchema.parse({ ...manifest(), db_vehicles_consulted: true })).toThrow();
    expect(() => fleetManifestSchema.parse({ ...manifest(), fleet_types: [] })).toThrow();
    expect(() => fleetManifestSchema.parse({ ...manifest(), fleet_types_source: "db" })).toThrow();
    const { fleet_types: _omit, ...rest } = manifest();
    void _omit;
    expect(() => fleetManifestSchema.parse(rest)).toThrow();
  });
});
