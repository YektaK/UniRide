import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { runDailyPlan } from "@/services/daily-plan-run";
import { runFleetScenarioDay, scenarioResponse } from "@/services/fleet-scenario-run";
import type { FleetTypeSpec } from "@/services/fleet-scenario-args";
import {
  DATE, large, sedan, rows, reader, transport, pickSelection, params,
  type OptimizeBody, type SelectionRequest,
} from "./fleet-scenario-fixtures";
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

describe("MT1-04: one offset meaning and the server schedule cross-check", () => {
  type StubRoute = { total_duration_minutes: number } & Record<string, unknown>;
  // Decorates the scripted optimizer: `stamp` returns the schedule fields for a route of a request, or null for none.
  const withSchedule = (
    inner: ReturnType<typeof transport>,
    stamp: (body: { direction: "pickup" | "dropoff"; target_time: string }, total: number) => Record<string, number> | null,
  ) => {
    const fetch = async (path: string, init?: RequestInit): Promise<Response> => {
      const response = await inner.fetch(path, init);
      if (!path.endsWith("/v1/optimize")) return response;
      const body = JSON.parse(String(init!.body)) as { direction: "pickup" | "dropoff"; target_time: string };
      const json = await response.json() as { routes: StubRoute[] };
      json.routes = json.routes.map((r) => ({ ...r, ...(stamp(body, r.total_duration_minutes) ?? {}) }));
      return Response.json(json);
    };
    return { fetch, calls: inner.calls };
  };
  const anchorOf = (targetTime: string) => Number(targetTime.slice(0, 2)) * 60 + Number(targetTime.slice(3, 5));
  const exact = (body: { direction: "pickup" | "dropoff"; target_time: string }, total: number) => {
    const anchor = anchorOf(body.target_time);
    return body.direction === "pickup"
      ? { schedule_start_minutes: anchor - total, schedule_end_minutes: anchor }
      : { schedule_start_minutes: anchor, schedule_end_minutes: anchor + total };
  };

  it("sends offset_minutes 0 in every /optimize request (baseline ga_split and the ga_split_hf menu calls)", async () => {
    const db = reader(rows());
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params());
    const optimizeBodies = t.calls.filter((c) => c.path.endsWith("/v1/optimize")).map((c) => c.body as Record<string, unknown>);
    expect(optimizeBodies.some((b) => b.algorithm === "ga_split")).toBe(true);
    expect(optimizeBodies.some((b) => b.algorithm === "ga_split_hf")).toBe(true);
    for (const body of optimizeBodies) expect(body.offset_minutes).toBe(0);
  });

  it("accepts responses whose certified schedule equals the plan interval", async () => {
    const db = reader(rows());
    const t = withSchedule(transport({ selection: pickSelection("q1", () => ["large", "car"]) }), exact);
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params());
    expect(day.status).toBe("ready");
    expect(day.reasonCodes).not.toContain("SCHEDULE_MISMATCH");
  });

  it("blocks the day with SCHEDULE_MISMATCH when the baseline schedule is shifted", async () => {
    const db = reader(rows());
    const t = withSchedule(transport({ selection: pickSelection("q1", () => ["large", "car"]) }), (body, total) => {
      const right = exact(body, total);
      return { schedule_start_minutes: right.schedule_start_minutes - 15, schedule_end_minutes: right.schedule_end_minutes - 15 };
    });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params());
    expect(day.status).toBe("blocked_data");
    expect(day.reasonCodes).toContain("SCHEDULE_MISMATCH");
  });

  it("still accepts archived-shape responses without the exact schedule fields", async () => {
    const db = reader(rows());
    const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
    const day = await runFleetScenarioDay({ reader: db.client, optimizerFetch: t.fetch, clock }, params());
    expect(day.status).toBe("ready");
  });
});