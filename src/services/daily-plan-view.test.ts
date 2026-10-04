import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  KNOWN_REASON_CODES,
  buildDailyPlanView,
  computeCapacityFloor,
  describeReason,
  formatMinutesOfDay,
  nodeLocationCode,
} from "./daily-plan-view";
import {
  blockedResponse,
  emptyDayResponse,
  indeterminateResponse,
  peakWaveResponse,
  readyResponse,
  rideLimitInfeasibleResponse,
  shortageResponse,
} from "./daily-plan-fixtures";
import { parseDudulluPreviewResponse } from "./dudullu-preview-response";

describe("formatMinutesOfDay", () => {
  it.each([
    [0, "00:00"],
    [525, "08:45"],
    [1020, "17:00"],
    [498.4, "08:18"],
    [498.6, "08:19"],
    [1440, "24:00"],
    [-3, "00:00"],
  ])("formats %s as %s", (minutes, label) => {
    expect(formatMinutesOfDay(minutes)).toBe(label);
  });
});

describe("nodeLocationCode", () => {
  it("drops the #occurrence suffix and keeps plain codes", () => {
    expect(nodeLocationCode("So3#occ-c")).toBe("So3");
    expect(nodeLocationCode("So3#occ-c#2")).toBe("So3");
    expect(nodeLocationCode("D.Kampus")).toBe("D.Kampus");
  });
});

describe("buildDailyPlanView - ready plan", () => {
  const view = buildDailyPlanView(readyResponse());

  it("groups jobs into pickup then dropoff sections with HH:MM anchors", () => {
    expect(view.sections.map((section) => section.direction)).toEqual(["pickup", "dropoff"]);
    const [morning] = view.sections[0].waves;
    expect(morning.anchorLabel).toBe("08:45");
    expect(morning.routeCount).toBe(2);
    expect(morning.studentCount).toBe(3);
    expect(morning.swCount).toBe(1);
    expect(morning.soCount).toBe(2);
    expect(view.sections[1].waves[0].anchorLabel).toBe("17:00");
  });

  it("sorts waves by anchor inside a direction", () => {
    const response = readyResponse();
    const early = structuredClone(response.jobs[0]);
    early.id = "2026-10-05:pickup:420";
    early.anchorMinutes = 420;
    early.intervals = early.intervals.map((interval) => ({
      ...interval,
      jobId: early.id,
      startMinutes: interval.startMinutes - 105,
      endMinutes: interval.endMinutes - 105,
    }));
    const sorted = buildDailyPlanView({ ...response, jobs: [response.jobs[0], early, response.jobs[1]] });
    expect(sorted.sections[0].waves.map((wave) => wave.anchorLabel)).toEqual(["07:00", "08:45"]);
  });

  it("merges jobs with the same direction and anchor into one wave", () => {
    const response = readyResponse();
    const twin = structuredClone(response.jobs[0]);
    twin.id = "twin";
    twin.intervals = twin.intervals.map((interval) => ({ ...interval, jobId: "twin" }));
    const merged = buildDailyPlanView({ ...response, jobs: [response.jobs[0], twin] });
    expect(merged.sections).toHaveLength(1);
    expect(merged.sections[0].waves).toHaveLength(1);
    expect(merged.sections[0].waves[0].routeCount).toBe(4);
  });

  it("orders routes by departure and computes stop arrival times from the interval start", () => {
    const [first, second] = view.sections[0].waves[0].routes;
    expect(first.number).toBe(1);
    expect(first.startLabel).toBe("08:18");
    expect(first.endLabel).toBe("08:45");
    expect(first.totalMinutes).toBe(27);
    expect(first.stops.map((stop) => [stop.code, stop.arrivalLabel, stop.offsetMinutes, stop.legMinutes])).toEqual([
      ["D.Kampus", "08:18", 0, 0],
      ["So1", "08:28", 10, 10],
      ["Sw2", "08:33", 15, 5],
      ["D.Kampus", "08:45", 27, 12],
    ]);
    expect(first.stops.map((stop) => stop.kind)).toEqual(["campus", "student", "student", "campus"]);
    expect(first.stops.map((stop) => stop.disability)).toEqual([null, "So", "Sw", null]);
    expect(first.swCount).toBe(1);
    expect(first.soCount).toBe(1);
    expect(second.number).toBe(2);
    expect(second.startLabel).toBe("08:25");
  });

  it("strips the occurrence suffix from stop codes", () => {
    const second = view.sections[0].waves[0].routes[1];
    expect(second.stops.map((stop) => stop.code)).toEqual(["D.Kampus", "So3", "D.Kampus"]);
  });

  it("starts a dropoff route at the anchor", () => {
    const route = view.sections[1].waves[0].routes[0];
    expect(route.startLabel).toBe("17:00");
    expect(route.endLabel).toBe("17:16");
    expect(route.stops.map((stop) => stop.arrivalLabel)).toEqual(["17:00", "17:08", "17:16"]);
  });

  it("lists physical vehicles numbered by first departure with routes in time order", () => {
    expect(view.vehicles.map((vehicle) => vehicle.label)).toEqual(["Araç 1", "Araç 2"]);
    const [first, second] = view.vehicles;
    expect(first.routes.map((slot) => [slot.direction, slot.anchorLabel, slot.startLabel, slot.endLabel])).toEqual([
      ["pickup", "08:45", "08:18", "08:45"],
      ["dropoff", "17:00", "17:00", "17:16"],
    ]);
    expect(first.busyMinutes).toBe(43);
    expect(second.routes).toHaveLength(1);
    expect(view.sections[0].waves[0].routes[0].vehicleLabel).toBe("Araç 1");
    expect(view.sections[0].waves[0].routes[1].vehicleLabel).toBe("Araç 2");
  });

  it("never exposes backend vehicle ids", () => {
    expect(JSON.stringify(view.vehicles)).not.toContain("virtual:");
  });

  it("positions vehicle slots on an hourly timeline", () => {
    expect(view.timeline?.startMinutes).toBe(8 * 60);
    expect(view.timeline?.endMinutes).toBe(18 * 60);
    const slot = view.vehicles[0].routes[0];
    expect(slot.leftPercent).toBeCloseTo(((498 - 480) / 600) * 100, 1);
    expect(slot.widthPercent).toBeCloseTo((27 / 600) * 100, 1);
    expect(view.timeline?.ticks[0]).toEqual({ label: "08:00", leftPercent: 0 });
    expect(view.timeline?.ticks.at(-1)).toEqual({ label: "18:00", leftPercent: 100 });
  });

  it("summarises vehicles, students, routes and the real fleet", () => {
    expect(view.summary.status).toBe("preview_ready");
    expect(view.summary.tone).toBe("success");
    expect(view.summary.neededVehicles).toBe(2);
    expect(view.summary.neededAtMost).toBe(false);
    expect(view.summary.students).toBe(4);
    expect(view.summary.trips).toBe(4);
    expect(view.summary.routes).toBe(3);
    expect(view.summary.peakConcurrentRoutes).toBe(2);
    expect(view.summary.fleet).toEqual({
      needed: 2, neededAtMost: false, liveFleet: 1, difference: 1, state: "missing", amount: 1,
    });
  });

  it("labels the demo as hypothetical with its assumptions", () => {
    expect(view.hypothetical).toBe(true);
    expect(view.assumedAdmission).toBe(true);
    expect(view.virtualFleet).toBe(true);
    expect(view.virtualTemplate).toEqual({ swCapacity: 4, soCapacity: 10, cooldownMinutes: 10 });
    expect(view.isEmptyDay).toBe(false);
  });

  it("reports a sufficient real fleet with its spare vehicles", () => {
    const response = readyResponse();
    const enough = buildDailyPlanView({ ...response, fleet: { ...response.fleet, liveActiveFleetSize: 5 } });
    expect(enough.summary.fleet).toMatchObject({ difference: -3, state: "enough", amount: 3 });
    const exact = buildDailyPlanView({ ...response, fleet: { ...response.fleet, liveActiveFleetSize: 2 } });
    expect(exact.summary.fleet).toMatchObject({ difference: 0, state: "enough", amount: 0 });
  });

  it("does not know the difference when the live fleet size is missing", () => {
    const response = readyResponse();
    const unknown = buildDailyPlanView({ ...response, fleet: { ...response.fleet, liveActiveFleetSize: null } });
    expect(unknown.summary.fleet).toMatchObject({ liveFleet: null, difference: null, state: "unknown" });
  });

  it("contains no name-like data beyond location codes", () => {
    const text = JSON.stringify(view);
    expect(text).not.toMatch(/occ-/);
  });
});

describe("buildDailyPlanView - indeterminate", () => {
  const view = buildDailyPlanView(indeterminateResponse());

  it("marks the vehicle count as an upper bound", () => {
    expect(view.summary.status).toBe("indeterminate");
    expect(view.summary.tone).toBe("warning");
    expect(view.summary.neededVehicles).toBe(3);
    expect(view.summary.neededAtMost).toBe(true);
    expect(view.summary.lowerBound).toBe(2);
    expect(view.summary.fleet.neededAtMost).toBe(true);
  });

  it("keeps the routes and flags the unfinished search", () => {
    expect(view.summary.routes).toBe(3);
    expect(view.reasons.map((reason) => reason.code)).toContain("ASSIGNMENT_SEARCH_INDETERMINATE");
  });

  it("has no upper-bound badge when no assignment was found", () => {
    const response = indeterminateResponse();
    const none = buildDailyPlanView({
      ...response,
      assignments: [],
      vehicleSummary: { ...response.vehicleSummary!, minimumVehicles: null },
    });
    expect(none.summary.neededVehicles).toBeNull();
    expect(none.summary.neededAtMost).toBe(false);
    expect(none.vehicles).toEqual([]);
    expect(none.timeline).toBeNull();
  });
});

describe("buildDailyPlanView - shortage", () => {
  const view = buildDailyPlanView(shortageResponse());

  it("shows the routes but no vehicle count or assignment", () => {
    expect(view.summary.status).toBe("shortage");
    expect(view.summary.tone).toBe("danger");
    expect(view.summary.neededVehicles).toBeNull();
    expect(view.summary.lowerBound).toBe(2);
    expect(view.summary.fleet.state).toBe("unknown");
    expect(view.sections).toHaveLength(2);
    expect(view.vehicles).toEqual([]);
    expect(view.sections[0].waves[0].routes.every((route) => route.vehicleLabel === null)).toBe(true);
  });

  it("is not hypothetical when recorded admission and the live fleet are used", () => {
    expect(view.hypothetical).toBe(false);
    expect(view.assumedAdmission).toBe(false);
    expect(view.virtualFleet).toBe(false);
    expect(view.virtualTemplate).toBeNull();
    expect(view.reasons).toEqual([{ code: "FLEET_SHORTAGE", messageKey: "FLEET_SHORTAGE", severity: "problem" }]);
  });
});

describe("buildDailyPlanView - blocked and empty days", () => {
  it("shows a blocked response with reasons and no plan", () => {
    const view = buildDailyPlanView(blockedResponse(["MATRIX_UNAVAILABLE", "SCHEDULE_DATA_INVALID"]));
    expect(view.summary.status).toBe("blocked_data");
    expect(view.summary.tone).toBe("danger");
    expect(view.sections).toEqual([]);
    expect(view.vehicles).toEqual([]);
    expect(view.summary.neededVehicles).toBeNull();
    expect(view.summary.routes).toBe(0);
    expect(view.summary.fleet).toMatchObject({ liveFleet: 2, state: "unknown" });
    expect(view.isEmptyDay).toBe(false);
    expect(view.reasons.map((reason) => reason.severity)).toEqual(["problem", "problem"]);
  });

  it("recognises an empty day", () => {
    const view = buildDailyPlanView(emptyDayResponse());
    expect(view.isEmptyDay).toBe(true);
    expect(view.summary.students).toBe(0);
    expect(view.summary.routes).toBe(0);
    expect(view.sections).toEqual([]);
  });

  it("shows a neutral status for an empty day", () => {
    expect(buildDailyPlanView(emptyDayResponse()).summary.tone).toBe("neutral");
  });

  it("does not call a response without NO_ADMITTED_DEMAND an empty day", () => {
    const view = buildDailyPlanView({ ...emptyDayResponse(), reasonCodes: [] });
    expect(view.isEmptyDay).toBe(false);
  });

  it("keeps SCHEDULE_DATA_INVALID visible even though the route also adds NO_ADMITTED_DEMAND", () => {
    const response = { ...emptyDayResponse(), reasonCodes: ["ADMISSION_ASSUMED", "SCHEDULE_DATA_INVALID", "NO_ADMITTED_DEMAND"] };
    const view = buildDailyPlanView(response);
    expect(view.isEmptyDay).toBe(false);
    expect(view.summary.tone).toBe("danger");
    expect(view.reasons.find((reason) => reason.code === "SCHEDULE_DATA_INVALID")?.severity).toBe("problem");
  });

  it("keeps recorded-mode LEG_DECISIONS_UNAVAILABLE visible instead of an empty day", () => {
    const response = {
      ...emptyDayResponse(),
      admissionMode: "recorded" as const,
      reasonCodes: ["LEG_DECISIONS_UNAVAILABLE", "NO_ADMITTED_DEMAND"],
    };
    const view = buildDailyPlanView(response);
    expect(view.isEmptyDay).toBe(false);
    expect(view.reasons.map((reason) => reason.severity)).toEqual(["problem", "problem"]);
  });

  it("still treats assume_confirmed LEG_DECISIONS_UNAVAILABLE as an empty day (informational)", () => {
    const response = { ...emptyDayResponse(), reasonCodes: ["ADMISSION_ASSUMED", "LEG_DECISIONS_UNAVAILABLE", "NO_ADMITTED_DEMAND"] };
    expect(buildDailyPlanView(response).isEmptyDay).toBe(true);
  });

  it.each(["FLEET_SHORTAGE", "MATRIX_UNAVAILABLE", "OPTIMIZATION_NOT_SUCCESSFUL", "SOMETHING_NEW"])(
    "keeps %s visible next to NO_ADMITTED_DEMAND",
    (code) => {
      const view = buildDailyPlanView({ ...emptyDayResponse(), reasonCodes: [code, "NO_ADMITTED_DEMAND"] });
      expect(view.isEmptyDay).toBe(false);
    },
  );

  it("does not call a blocked day with admitted trips empty", () => {
    const view = buildDailyPlanView(blockedResponse(["MATRIX_UNAVAILABLE"]));
    expect(view.isEmptyDay).toBe(false);
  });
});

describe("describeReason", () => {
  it("treats demo-preparation codes as informational", () => {
    expect(describeReason("ADMISSION_ASSUMED", true).severity).toBe("info");
    expect(describeReason("PENDING_STUDENT_CONFIRMATION", false).severity).toBe("info");
    expect(describeReason("LEG_DECISIONS_UNAVAILABLE", true).severity).toBe("info");
    expect(describeReason("LEG_DECISIONS_UNAVAILABLE", false).severity).toBe("problem");
    expect(describeReason("MATRIX_UNAVAILABLE", true).severity).toBe("problem");
  });

  it("falls back to the unknown message for codes without copy", () => {
    expect(describeReason("SOMETHING_NEW", false)).toEqual({
      code: "SOMETHING_NEW", messageKey: "unknown", severity: "problem",
    });
  });
});

describe("buildDailyPlanView - student ride time", () => {
  it("derives each route's longest student ride per direction and the day's maximum", () => {
    const view = buildDailyPlanView(readyResponse());
    const [morning] = view.sections[0].waves;
    // pickup: total - outbound arc (first student rides longest): 27 - 10, 20 - 10.
    expect(morning.routes.map((route) => [route.totalMinutes, route.maxRideMinutes])).toEqual([[27, 17], [20, 10]]);
    // dropoff: total - closing arc (last student rides longest): 16 - 8.
    expect(view.sections[1].waves[0].routes[0].maxRideMinutes).toBe(8);
    expect(view.summary.maxRideMinutes).toBe(17);
  });

  it("uses the closing arc for dropoff and the outbound arc for pickup on an asymmetric route", () => {
    const response = readyResponse();
    const steps = [
      { location1: "D.Kampus", location2: "Sw4", duration: 8, distance: 0 },
      { location1: "Sw4", location2: "So5", duration: 7, distance: 0 },
      { location1: "So5", location2: "D.Kampus", duration: 20, distance: 0 },
    ];
    response.jobs[1].result.routes[0].route_details = steps;
    response.jobs[0].result.routes[0].route_details = steps;
    const view = buildDailyPlanView(response);
    // dropoff: 8 + 7 = 15; pickup: 7 + 20 = 27.
    expect(view.sections[1].waves[0].routes[0].maxRideMinutes).toBe(15);
    expect(view.sections[0].waves[0].routes.map((route) => route.maxRideMinutes)).toContain(27);
  });

  it("has no day maximum when there is no route and carries the limits", () => {
    const view = buildDailyPlanView(blockedResponse());
    expect(view.summary.maxRideMinutes).toBeNull();
    expect(view.limits).toEqual({ maxRideTimeMinutes: 90, maxTourMinutes: 150, minimumFeasibleRideMinutes: null });
    expect(buildDailyPlanView(rideLimitInfeasibleResponse()).limits.minimumFeasibleRideMinutes).toBe(23);
  });

  it("treats RIDE_TIME_LIMIT_INFEASIBLE as a known problem code", () => {
    expect(describeReason("RIDE_TIME_LIMIT_INFEASIBLE", false)).toEqual({
      code: "RIDE_TIME_LIMIT_INFEASIBLE", messageKey: "RIDE_TIME_LIMIT_INFEASIBLE", severity: "problem",
    });
  });

  it("rejects a response without the limits echo", () => {
    const withoutLimits: Partial<ReturnType<typeof readyResponse>> = readyResponse();
    delete withoutLimits.limits;
    expect(() => parseDudulluPreviewResponse(withoutLimits)).toThrow();
  });
});

describe("reason code copy", () => {
  type Messages = { page: { admin: { dailyPlan?: { reasons?: Record<string, string>; status?: Record<string, string> } } } };
  const load = (name: string) =>
    JSON.parse(readFileSync(new URL(`../../messages/${name}.json`, import.meta.url), "utf8")) as Messages;

  it.each(["tr", "en"])("has plain text for every reason code and status in %s", (locale) => {
    const plan = load(locale).page.admin.dailyPlan;
    for (const code of [...KNOWN_REASON_CODES, "unknown"]) {
      expect(plan?.reasons?.[code]?.trim(), `${locale} reason ${code}`).toBeTruthy();
    }
    for (const status of ["preview_ready", "shortage", "blocked_data", "indeterminate"]) {
      expect(plan?.status?.[status]?.trim(), `${locale} status ${status}`).toBeTruthy();
    }
  });

  it("has the same keys in Turkish and English and copy for every client error kind", () => {
    const flatten = (value: unknown, prefix = ""): string[] =>
      typeof value === "string"
        ? [prefix]
        : Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
            flatten(child, prefix ? `${prefix}.${key}` : key));
    const tr = load("tr").page.admin.dailyPlan;
    const en = load("en").page.admin.dailyPlan;
    expect(flatten(en).sort()).toEqual(flatten(tr).sort());
    const errors = (tr as { errors?: Record<string, string> }).errors ?? {};
    for (const kind of ["authorization", "invalidDate", "invalidLimit", "unavailable", "timeout", "network", "invalidResponse"]) {
      expect(errors[kind]?.trim(), `error ${kind}`).toBeTruthy();
    }
  });

  it("covers every code of the backend PreviewReasonCode union", () => {
    const source = readFileSync(new URL("./dudullu-preview.ts", import.meta.url), "utf8");
    const union = /export type PreviewReasonCode =([\s\S]*?);/.exec(source)?.[1] ?? "";
    const backendCodes = [...union.matchAll(/"([A-Z_]+)"/g)].map((match) => match[1]).sort();
    expect(backendCodes.length).toBeGreaterThan(20);
    expect([...KNOWN_REASON_CODES].sort()).toEqual(backendCodes);
  });
});

describe("parseDudulluPreviewResponse", () => {
  it("accepts the fixture shapes", () => {
    for (const response of [
      readyResponse(), shortageResponse(), blockedResponse(), emptyDayResponse(), rideLimitInfeasibleResponse(),
    ]) {
      expect(() => parseDudulluPreviewResponse(response)).not.toThrow();
    }
  });

  it("rejects a publishable or malformed response", () => {
    expect(() => parseDudulluPreviewResponse({ ...readyResponse(), publishable: true })).toThrow();
    expect(() => parseDudulluPreviewResponse({ ...readyResponse(), status: "ok" })).toThrow();
    expect(() => parseDudulluPreviewResponse({ error: "PREVIEW_UNAVAILABLE" })).toThrow();
    expect(() => parseDudulluPreviewResponse(null)).toThrow();
  });
});

describe("computeCapacityFloor", () => {
  const wave = (direction: "pickup" | "dropoff", anchorMinutes: number, swCount: number, soCount: number) => ({
    direction,
    anchorMinutes,
    anchorLabel: formatMinutesOfDay(anchorMinutes),
    swCount,
    soCount,
  });
  const capacity = { swCapacity: 4, soCapacity: 10 };

  it("is bound by the So pool when So students need more vehicles (5 Sw, 15 So -> 2)", () => {
    expect(computeCapacityFloor([wave("pickup", 525, 5, 15)], capacity)).toEqual({
      vehicles: 2, direction: "pickup", anchorLabel: "08:45", studentCount: 20, swCount: 5, soCount: 15,
      swCapacity: 4, soCapacity: 10,
    });
  });

  it("is bound by the Sw pool when Sw students need more vehicles", () => {
    expect(computeCapacityFloor([wave("pickup", 525, 9, 3)], capacity)?.vehicles).toBe(3);
  });

  it("checks Sw and So separately instead of adding them", () => {
    // 4 Sw + 10 So fit one vehicle although 14 > 10.
    expect(computeCapacityFloor([wave("pickup", 525, 4, 10)], capacity)?.vehicles).toBe(1);
    expect(computeCapacityFloor([wave("pickup", 525, 5, 10)], capacity)?.vehicles).toBe(2);
  });

  it("takes the busiest wave of the day, whatever the direction", () => {
    const floor = computeCapacityFloor(
      [wave("pickup", 480, 1, 10), wave("dropoff", 1020, 0, 21), wave("pickup", 525, 5, 15)],
      capacity,
    );
    expect(floor).toMatchObject({ vehicles: 3, direction: "dropoff", anchorLabel: "17:00", soCount: 21 });
  });

  it("breaks ties by student count, then by the earlier wave", () => {
    const byStudents = computeCapacityFloor([wave("pickup", 480, 0, 11), wave("pickup", 525, 0, 20)], capacity);
    expect(byStudents).toMatchObject({ vehicles: 2, anchorLabel: "08:45" });
    const byTime = computeCapacityFloor([wave("dropoff", 1020, 0, 15), wave("pickup", 525, 0, 15)], capacity);
    expect(byTime).toMatchObject({ vehicles: 2, anchorLabel: "08:45" });
  });

  it("uses the given capacities, not the default template", () => {
    expect(computeCapacityFloor([wave("pickup", 525, 5, 15)], { swCapacity: 2, soCapacity: 5 })?.vehicles).toBe(3);
  });

  it("returns null without capacities, without students or when a needed seat pool is empty", () => {
    expect(computeCapacityFloor([wave("pickup", 525, 5, 15)], null)).toBeNull();
    expect(computeCapacityFloor([wave("pickup", 525, 5, 15)], undefined)).toBeNull();
    expect(computeCapacityFloor([], capacity)).toBeNull();
    expect(computeCapacityFloor([wave("pickup", 525, 0, 0)], capacity)).toBeNull();
    expect(computeCapacityFloor([wave("pickup", 525, 2, 0)], { swCapacity: 0, soCapacity: 10 })).toBeNull();
    // An empty pool is fine when nobody needs it.
    expect(computeCapacityFloor([wave("pickup", 525, 0, 3)], { swCapacity: 0, soCapacity: 10 })?.vehicles).toBe(1);
  });
});

describe("buildDailyPlanView - capacity floor", () => {
  it("derives the floor from the response waves and fleet capacity", () => {
    const view = buildDailyPlanView(peakWaveResponse(3));
    expect(view.summary.capacityFloor).toMatchObject({
      vehicles: 2, direction: "pickup", anchorLabel: "08:45", studentCount: 20, swCount: 5, soCount: 15,
      swCapacity: 4, soCapacity: 10,
    });
    expect(view.summary.neededVehicles).toBe(3);
  });

  it("is null for an older response without fleet capacities and for a plan without routes", () => {
    const old = peakWaveResponse();
    const fleet = { ...old.fleet, maxCapacity: undefined };
    expect(buildDailyPlanView({ ...old, fleet }).summary.capacityFloor).toBeNull();
    expect(buildDailyPlanView(blockedResponse()).summary.capacityFloor).toBeNull();
    expect(buildDailyPlanView(emptyDayResponse()).summary.capacityFloor).toBeNull();
  });

  it("still parses through the zod contract with and without the new field", () => {
    const withField = peakWaveResponse();
    expect(parseDudulluPreviewResponse(withField).fleet.maxCapacity).toEqual({ swCapacity: 4, soCapacity: 10 });
    const { maxCapacity: _omit, ...fleet } = withField.fleet;
    void _omit;
    expect(parseDudulluPreviewResponse({ ...withField, fleet }).fleet.maxCapacity).toBeUndefined();
    expect(parseDudulluPreviewResponse({ ...withField, fleet: { ...fleet, maxCapacity: null } }).fleet.maxCapacity).toBeNull();
  });
});
