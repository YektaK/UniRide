import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { runDailyPlan, type DailyPlanReader } from "@/services/daily-plan-run";
import { runFleetScenarioDay, scenarioResponse, type FleetScenarioParams } from "@/services/fleet-scenario-run";
import type { FleetTypeSpec } from "@/services/fleet-scenario-args";

const DATE = "2026-09-30"; // a Wednesday
const hash = "a".repeat(64);
const nodes = ["D.Kampus", "Sw1", "So1", "So2"];
const matrixOf = (duration: number) => ({
  id: `time_matrix:sha256:${hash}`, version: hash, sha256: hash, source: "supabase",
  arcs: nodes.flatMap((a) => nodes.filter((b) => b !== a).map((b) => ({ origin_code: a, destination_code: b, duration_minutes: duration }))),
});
const matrix = matrixOf(5);

const large: FleetTypeSpec = { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 };
const sedan: FleetTypeSpec = { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 };

function rows() {
  const student = (id: string, code: string, type: "Sw" | "So") => ({
    id, role: "student", location_code: code, disability_type: type, weekly_schedule_id: `sch-${id}`,
  });
  const schedule = (id: string) => ({
    id: `sch-${id}`, user_id: id,
    entries: [{ id: "c1", dayOfWeek: "wednesday", startTime: "09:00", endTime: "10:00", location: "Dudullu" }],
  });
  return {
    users: [student("s-sw", "Sw1", "Sw"), student("s-so1", "So1", "So"), student("s-so2", "So2", "So")],
    weekly_schedules: [schedule("s-sw"), schedule("s-so1"), schedule("s-so2")],
    student_leg_decisions: [], ride_requests: [], vehicles: [{ id: "db-1", wheelchair_capacity: 4, seating_capacity: 10, cooldown_minutes: 10, status: "active" }],
  } as Record<string, unknown[]>;
}

function reader(data: Record<string, unknown[]>) {
  const tables: string[] = [];
  const writes: string[] = [];
  const from = (table: string) => {
    tables.push(table);
    const query: Record<string, unknown> = {};
    for (const method of ["select", "eq", "in", "or"]) query[method] = () => query;
    for (const method of ["insert", "update", "upsert", "delete"]) query[method] = () => { writes.push(`${table}.${method}`); return query; };
    query.then = (ok: (value: unknown) => unknown, bad: (reason: unknown) => unknown) =>
      Promise.resolve({ data: data[table] ?? [], error: null }).then(ok, bad);
    return query;
  };
  return { client: { from } as unknown as DailyPlanReader, tables, writes };
}

interface OptimizeBody {
  algorithm: string; direction: "pickup" | "dropoff"; students: Array<{ id: string; disability_type: "Sw" | "So"; location_code: string }>;
  vehicle_types?: Array<{ type_id: string; max_routes?: number; total_capacity?: number }>;
}
const steps = (locations: string[], d = 5) => {
  const path = ["D.Kampus", ...locations, "D.Kampus"];
  return path.slice(1).map((to, i) => ({ location1: path[i], location2: to, duration: d, distance: 0 }));
};
const round2 = (x: number) => Math.round(x * 100) / 100;
const route = (students: OptimizeBody["students"], vehicleId: string, type?: string, d = 5) => ({
  vehicle_id: vehicleId, route_details: steps(students.map((s) => s.location_code), d),
  total_duration_minutes: round2(d * (students.length + 1)), sw_count: students.filter((s) => s.disability_type === "Sw").length,
  so_count: students.filter((s) => s.disability_type === "So").length, student_ids: students.map((s) => s.id),
  ...(type ? { vehicle_type: type } : {}),
});

type SelectionRequest = {
  waves: Array<{ wave_id: string; options: Array<{ option_id: string; baseline: boolean; routes: Array<{ start: number; end: number; minutes: number; large_ok: boolean; car_ok: boolean }> }> }>;
  max_large: number;
  time_scale?: number; cooldown_large: number; cooldown_car: number;
};

function transport(options: { selection?: (request: SelectionRequest) => { status: number; body: unknown }; duration?: number } = {}) {
  const d = options.duration ?? 5;
  const calls: Array<{ path: string; body: unknown }> = [];
  const fetch = async (path: string, init?: RequestInit): Promise<Response> => {
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    calls.push({ path, body });
    if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrixOf(d));
    if (path === "/api/v1/optimize") {
      const request = body as OptimizeBody;
      const all = request.students;
      if (request.algorithm === "ga_split") {
        return Response.json({ success: true, routes: [route(all, "V1", undefined, d)], total_duration_minutes: round2(d * (all.length + 1)), feasibility_certificate: { is_feasible: true } });
      }
      const quota = request.vehicle_types!.find((t) => t.type_id === "large")!.max_routes!;
      const sw = all.filter((s) => s.disability_type === "Sw");
      const so = all.filter((s) => s.disability_type === "So");
      if (quota === 0 && sw.length > 0) {
        return Response.json({ success: false, routes: [], feasibility_certificate: { is_feasible: false } });
      }
      const routes = [...(sw.length ? [route(sw, "H1", "large", d)] : []), ...(so.length ? [route(so, "H2", "sedan", d)] : [])];
      return Response.json({ success: true, routes, total_duration_minutes: round2(routes.reduce((s, r) => s + r.total_duration_minutes, 0)), feasibility_certificate: { is_feasible: true } });
    }
    if (path === "/api/v1/internal/fleet-selection") {
      const scripted = options.selection?.(body as SelectionRequest);
      if (!scripted) return new Response("{}", { status: 503 });
      return Response.json(scripted.body, { status: scripted.status });
    }
    throw new Error("unexpected path");
  };
  return { fetch, calls };
}

const pickSelection = (optionId: string, labelsFor: (routes: number) => string[]) => (request: SelectionRequest) => ({
  status: 200,
  body: {
    status: "optimal", cars: 1, large_peak: 1, car_minutes: 15, total_minutes: 25,
    selection: Object.fromEntries(request.waves.map((wave) => {
      const option = wave.options.find((o) => o.option_id === optionId)!;
      return [wave.wave_id, { option_id: optionId, option_index: wave.options.indexOf(option), labels: labelsFor(option.routes.length) }];
    })),
    diagnostics: { claim: "minimum cars over the given menus only" }, stats: { random_seed: 20261008, num_workers: 1 },
  },
});

const params = (overrides: Partial<FleetScenarioParams> = {}): FleetScenarioParams => ({
  serviceDate: DATE, maxRideTimeMinutes: 60, maxTourMinutes: 150, fixedType: large, minimiseType: sedan,
  scenarios: ["A", 1, 2], ...overrides,
});
const clock = () => new Date("2026-09-30T00:00:00Z");

describe("runFleetScenarioDay", () => {
  it("builds the menu, selects, verifies and reports per-type results without touching the vehicles table", async () => {
    const db = reader(rows());
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params());

    expect(day.status).toBe("ready");
    expect(day.dbVehiclesConsulted).toBe(false);
    expect(db.tables).not.toContain("vehicles");
    expect(db.writes).toEqual([]);
    expect(day).toMatchObject({ students: 3, legs: 6, waves: 2 });

    // menu: baseline + q1 (q0 infeasible because a Sw student cannot ride the sedan, q2 duplicates q1)
    for (const wave of day.menu) {
      const byId = Object.fromEntries(wave.options.map((o) => [o.optionId, o.status]));
      expect(byId).toEqual({ base: "included", q0: "skipped_infeasible", q1: "included", q2: "skipped_duplicate" });
    }
    // The hf calls carry the types and the large quota; the selection request flags sedan-ineligible routes.
    const hf = t.calls.filter((c) => (c.body as OptimizeBody | null)?.algorithm === "ga_split_hf");
    expect(hf).toHaveLength(2 * 3);
    expect((hf[0].body as OptimizeBody).vehicle_types!.map((v) => v.type_id)).toEqual(["large", "sedan"]);
    const selectionRequest = t.calls.find((c) => c.path === "/api/v1/internal/fleet-selection")!.body as SelectionRequest;
    const q1 = selectionRequest.waves[0].options.find((o) => o.option_id === "q1")!;
    expect(q1.routes.map((r) => [r.large_ok, r.car_ok])).toEqual([[true, false], [true, true]]);
    expect(selectionRequest.waves[0].options.find((o) => o.option_id === "base")!.baseline).toBe(true);

    const [a, l1, l2] = day.scenarios;
    expect(a).toMatchObject({ scenario: "A", status: "ok", cars: 0, largeVehicles: 1, largeVehiclesProven: true });
    // L = 1: the Sw route and the So route of one wave are concurrent, so one car is needed.
    expect(l1).toMatchObject({ scenario: 1, status: "ok", cars: 1, carsStatus: "proven_over_menu", largeVehicles: 1, carRoutes: 2, largeRoutes: 2 });
    expect(l1.carUsageWindows).toHaveLength(1);
    expect(l1.carUsageWindows[0].routeCount).toBe(2);
    expect(l1.minutesByType.large).toBeGreaterThan(0);
    expect(l1.totalVehicleMinutes).toBeCloseTo((l1.minutesByType.large ?? 0) + (l1.minutesByType.sedan ?? 0), 5);
    expect(l1.ride).toMatchObject({ passengers: 6 });
    expect(l1.assignment).toMatchObject({ status: "proven", problems: [] });
    // L = 2: the independent typed assignment needs no car even though the scripted selection labelled one.
    expect(l2).toMatchObject({ scenario: 2, status: "ok", cars: 0, carRoutes: 0 });
    expect(l2.routes.some((r) => r.selectionLabel === "car")).toBe(true);
    for (const result of day.scenarios) {
      expect(result.routes.every((r) => r.physicalVehicleId !== "")).toBe(true);
    }
    // the response JSON carries types and labels
    const json = scenarioResponse(day, l1);
    expect(JSON.stringify(json)).toContain("\"vehicleType\":\"sedan\"");
  });

  it("CX-01: sends exact centi-minute intervals (time_scale 100) so fractional routes are not widened into a false infeasible day", async () => {
    const db = reader(rows());
    // 5.25-minute arcs: a dropoff wave of n legs spans anchor .. anchor + 5.25 * (n + 1), a fractional end.
    const t = transport({ duration: 5.25, selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params({ scenarios: [1] }));
    const request = t.calls.find((c) => c.path === "/api/v1/internal/fleet-selection")!.body as SelectionRequest;
    expect(request.time_scale).toBe(100);
    expect(request.cooldown_large).toBe(1000);
    expect(request.cooldown_car).toBe(1000);
    const routes = request.waves.flatMap((w) => w.options.flatMap((o) => o.routes));
    expect(routes.length).toBeGreaterThan(0);
    for (const r of routes) {
      expect(Number.isInteger(r.start) && Number.isInteger(r.end)).toBe(true);
      expect(r.start % 100 === 0 || r.end % 100 === 0).toBe(true); // the anchored endpoint is a whole minute
    }
    // exact, not ceil-widened: some endpoint carries a fractional part (e.g. 60525, not 60600)
    expect(routes.some((r) => r.start % 100 !== 0 || r.end % 100 !== 0)).toBe(true);
    expect(day.scenarios[0]).toMatchObject({ status: "ok" });
  });

  it("CX-01: endpoints with more than two decimals are refused, never rounded", async () => {
    const db = reader(rows());
    const t = transport({ duration: 5.123, selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params({ scenarios: [1] }));
    expect(t.calls.map((c) => c.path)).not.toContain("/api/v1/internal/fleet-selection");
    expect(day.scenarios[0]).toMatchObject({ status: "blocked_data", reasonCodes: ["SELECTION_INTERVAL_PRECISION"] });
  });

  it("CX-01: an off-grid cooldown is refused, never rounded", async () => {
    const db = reader(rows());
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay(
      { reader: db.client, optimizerFetch: t.fetch, clock },
      params({ scenarios: [1], fixedType: { ...large, cooldownMinutes: 10.005 } }),
    );
    expect(t.calls.map((c) => c.path)).not.toContain("/api/v1/internal/fleet-selection");
    expect(day.scenarios[0]).toMatchObject({ status: "blocked_data", reasonCodes: ["SELECTION_INTERVAL_PRECISION"] });
  });

  it("reports infeasible_for_L with the selection diagnostics", async () => {
    const db = reader(rows());
    const t = transport({
      selection: () => ({
        status: 200,
        body: {
          status: "infeasible_for_L", cars: null, large_peak: null, car_minutes: null, total_minutes: null, selection: {},
          diagnostics: { reason: "SW_DEMAND_EXCEEDS_LARGE_CAPACITY", lower_bound_L: 1, waves_exceeding_L: ["w"] }, stats: {},
        },
      }),
    });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params({ scenarios: [0] }));
    expect(day.scenarios[0]).toMatchObject({
      scenario: 0, status: "infeasible_for_L", cars: null, reasonCodes: ["SW_DEMAND_EXCEEDS_LARGE_CAPACITY"],
      selection: { status: "infeasible_for_L", diagnostics: { lower_bound_L: 1 } },
    });
  });

  it("fails closed when the selection response does not match the menu or the endpoint is down", async () => {
    const mismatch = transport({ selection: pickSelection("q1", () => ["large"]) });
    const day = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: mismatch.fetch, clock }, params({ scenarios: [1] }));
    expect(day.scenarios[0]).toMatchObject({ status: "verification_failed", reasonCodes: ["SELECTION_RESPONSE_MISMATCH"] });

    const down = transport();
    const unavailable = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: down.fetch, clock }, params({ scenarios: [1] }));
    expect(unavailable.scenarios[0]).toMatchObject({ status: "selection_unavailable", reasonCodes: ["SELECTION_HTTP_503"] });
  });

  it("does not call the menu or selection endpoints for scenario A only", async () => {
    const t = transport();
    const day = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: t.fetch, clock },
      params({ scenarios: ["A"], minimiseType: null }));
    expect(day.scenarios).toHaveLength(1);
    expect(t.calls.map((c) => c.path)).not.toContain("/api/v1/internal/fleet-selection");
    expect(t.calls.some((c) => (c.body as OptimizeBody | null)?.algorithm === "ga_split_hf")).toBe(false);
  });

  it("fails closed when a baseline route exceeds a shared total capacity of the fixed type", async () => {
    const capped: FleetTypeSpec = { ...large, totalCapacity: 2 };
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: t.fetch, clock },
      params({ fixedType: capped }));
    expect(day).toMatchObject({ status: "blocked_data", reasonCodes: ["BASELINE_TOTAL_CAPACITY_EXCEEDED"], scenarios: [] });
    expect(t.calls.map((c) => c.path)).not.toContain("/api/v1/internal/fleet-selection");
  });

  it("forwards total_capacity to ga_split_hf only for capped types", async () => {
    const capped: FleetTypeSpec = { ...sedan, totalCapacity: 3 };
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: t.fetch, clock },
      params({ minimiseType: capped, scenarios: [1] }));
    const hf = t.calls.filter((c) => (c.body as OptimizeBody | null)?.algorithm === "ga_split_hf");
    expect(hf.length).toBeGreaterThan(0);
    for (const call of hf) {
      const types = (call.body as OptimizeBody).vehicle_types!;
      expect(types.find((v) => v.type_id === "sedan")!.total_capacity).toBe(3);
      expect(types.find((v) => v.type_id === "large")).not.toHaveProperty("total_capacity");
    }
  });

  it("blocks the day when the matrix is unavailable and reports an empty day", async () => {
    const down = async (path: string) => path === "/api/v1/internal/matrix-snapshot" ? new Response("{}", { status: 503 }) : Response.json({});
    const blocked = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: down, clock }, params());
    expect(blocked).toMatchObject({ status: "blocked_data", reasonCodes: ["MATRIX_UNAVAILABLE"], scenarios: [] });

    const empty = await runFleetScenarioDay({ reader: reader({ ...rows(), users: [] }).client, optimizerFetch: down, clock }, params());
    expect(empty.status).toBe("empty_day");
    expect(empty.scenarios.map((s) => s.cars)).toEqual([0, 0, 0]);
  });
});

describe("R1: single-type scenario A equals runDailyPlan", () => {
  it("reproduces the daily plan vehicles, routes and optimizer requests with the same template", async () => {
    const dbA = reader({ ...rows(), vehicles: [] });
    const tPlan = transport();
    const plan = await runDailyPlan({ reader: dbA.client, optimizerFetch: tPlan.fetch, clock }, {
      serviceDate: DATE, admissionMode: "assume_confirmed", fleetMode: "virtual", maxRideTimeMinutes: 60, maxTourMinutes: 150,
    });
    const dbB = reader(rows());
    const tFleet = transport();
    const day = await runFleetScenarioDay({ reader: dbB.client, optimizerFetch: tFleet.fetch, clock },
      params({ scenarios: ["A"], minimiseType: null }));

    expect(plan.fleet.template).toEqual({ swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 });
    const a = day.scenarios[0];
    expect(a.largeVehicles).toBe(plan.vehicleSummary!.minimumVehicles);
    expect(a.largeVehiclesProven).toBe(plan.vehicleSummary!.minimumProven);
    expect(a.routes.length).toBe(plan.routeIntervals.length);
    expect(a.routes.map((r) => [r.startMinutes, r.endMinutes])).toEqual(plan.routeIntervals.map((r) => [r.startMinutes, r.endMinutes]));
    // identical /optimize requests (same bodies, same order) and the same matrix call
    expect(tFleet.calls).toEqual(tPlan.calls);
    // the daily plan is the one that reads the vehicles table for its template; the fleet run never does
    expect(dbA.tables).toContain("vehicles");
    expect(dbB.tables).not.toContain("vehicles");
  });
});
