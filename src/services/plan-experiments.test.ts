import { describe, expect, it } from "vitest";
import {
  parseExperimentArgs, routeMetrics, aggregateWeeks, anonymizeResponse,
  summariesMatch, captureMatrixSnapshot, summarizePlan, toCsv, fetchWithRateLimitRetry, type ExperimentSummary,
} from "./plan-experiments";

describe("plan experiments", () => {
  it("expands a Monday into five weekdays and preserves page limits", () => {
    expect(parseExperimentArgs(["--week-of", "2026-10-05"])).toMatchObject({
      dates: ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"],
      rideLimits: [50, 60, 70, 90], tourLimit: 150, fleet: "virtual", repeat: 1,
    });
  });
  it("accepts explicit dates, limits, live fleet and repetition", () => {
    expect(parseExperimentArgs(["--dates", "2026-10-05,2026-10-09", "--ride-limits", "90", "--tour-limit", "150", "--fleet", "live", "--repeat", "2", "--out", ".temp/demo"])).toMatchObject({
      dates: ["2026-10-05", "2026-10-09"], rideLimits: [90], fleet: "live", repeat: 2, out: ".temp/demo",
    });
  });
  it.each([
    [], ["--week-of", "2026-10-06"], ["--dates", "2026-02-30"],
    ["--dates", "2026-10-05,2026-10-05"], ["--dates", "2026-10-05", "--week-of", "2026-10-05"],
    ["--week-of", "2026-10-05", "--ride-limits", "14"],
    ["--week-of", "2026-10-05", "--ride-limits", "50,50"],
    ["--week-of", "2026-10-05", "--tour-limit", "301"],
    ["--week-of", "2026-10-05", "--repeat", "3"],
    ["--week-of", "2026-10-05", "--fleet", "other"],
    ["--week-of", "2026-10-05", "--unknown", "x"],
    ["--week-of"], ["--dates", "2026-10-05", "--out", ""],
  ].map(args => [args] as [string[]]))("rejects invalid arguments %j before any service call", (args) => {
    expect(() => parseExperimentArgs(args)).toThrow();
  });

  const step = (location1: string, location2: string) => ({ location1, location2, duration: 999, distance: 0 });
  const jobs = [
    { direction: "pickup" as const, result: { routes: [{ student_ids: ["a", "b"], sw_count: 2, so_count: 0,
      route_details: [step("D", "A"), step("A", "B"), step("B", "D")] }] } },
    { direction: "dropoff" as const, result: { routes: [{ student_ids: ["c"], sw_count: 0, so_count: 1,
      route_details: [step("D", "C"), step("C", "D")] }] } },
  ];
  const arcs = [
    { origin_code: "D", destination_code: "A", duration_minutes: 10 },
    { origin_code: "A", destination_code: "B", duration_minutes: 20 },
    { origin_code: "B", destination_code: "D", duration_minutes: 30 },
    { origin_code: "D", destination_code: "C", duration_minutes: 5 },
    { origin_code: "C", destination_code: "D", duration_minutes: 100 },
  ];
  it("uses authoritative closed-tour costs and weights mean by passenger legs", () => {
    expect(routeMetrics(jobs, arcs)).toEqual({ meanRideMinutes: 28.333333, totalVehicleMinutes: 165 });
  });
  it("counts repeated physical stops as distinct passengers with a zero hop", () => {
    const repeated = [{ direction: "pickup" as const, result: { routes: [{ student_ids: ["a", "b"], sw_count: 2, so_count: 0,
      route_details: [step("D", "B"), step("B", "B"), step("B", "D")] }] } }];
    expect(routeMetrics(repeated, [...arcs, { origin_code: "D", destination_code: "B", duration_minutes: 20 }]))
      .toEqual({ meanRideMinutes: 30, totalVehicleMinutes: 50 });
  });
  it("fails closed on missing matrix costs or passenger coverage", () => {
    expect(() => routeMetrics(jobs, [])).toThrow();
    expect(() => routeMetrics([{ ...jobs[0], result: { routes: [{ ...jobs[0].result.routes[0], student_ids: ["a"] }] } }], arcs)).toThrow();
  });
  it("keeps response matrix provenance rather than inferring it from exported arcs", () => {
    const hash = "a".repeat(64);
    const matrix = { id: `time_matrix:sha256:${hash}`, version: hash, sha256: hash, source: "supabase",
      provenance: { source: "supabase", sha256: hash, location_count: 29, loaded_at: "2026-10-07T10:00:00+00:00" }, arcs };
    expect(captureMatrixSnapshot(matrix).provenance.location_count).toBe(29);
    expect(() => captureMatrixSnapshot({ ...matrix, provenance: { ...matrix.provenance, sha256: "b".repeat(64) } })).toThrow();
  });
  it("distinguishes a healthy empty day from blocked or unavailable computation", () => {
    const empty = { status: "blocked_data", publishable: false, hypothetical: true, serviceDate: "2026-10-05",
      admissionMode: "assume_confirmed", fleetMode: "virtual", reasonCodes: ["NO_ADMITTED_DEMAND", "ADMISSION_ASSUMED"],
      candidateSummary: { dudulluStudents: 0, legsByAdmission: {}, invalidStudentRecords: 0 },
      fleet: { mode: "virtual", assignmentFleetSize: null, liveActiveFleetSize: null, template: null, maxCapacity: null },
      limits: { maxRideTimeMinutes: 90, maxTourMinutes: 150, minimumFeasibleRideMinutes: null },
      vehicleSummary: null, jobs: [], routeIntervals: [], assignments: [], hourlyOccupiedVehicles: {}, occurrenceLabels: {} };
    expect(summarizePlan(empty, null, "2026-10-05", 90, 150, 1)).toMatchObject({ total_vehicle_minutes: 0, mean_ride_min: null, is_empty_day: true });
    expect(summarizePlan({ ...empty, reasonCodes: ["SCHEDULE_DATA_INVALID"] }, null, "2026-10-05", 90, 150, 1)).toMatchObject({ total_vehicle_minutes: null, is_empty_day: false });
    expect(summarizePlan({ error: "PREVIEW_UNAVAILABLE" }, null, "2026-10-05", 90, 150, 1)).toMatchObject({ status: "preview_unavailable", students: null, total_vehicle_minutes: null });
  });
  it("escapes nested reason arrays and blank unknown values in CSV", () => {
    expect(toCsv([{ reason: ["A", "B"], minutes: null }], ["reason", "minutes"]))
      .toBe('reason,minutes\n"[""A"",""B""]",\n');
  });
  it("respects a rejected compute request's Retry-After before retrying the same payload", async () => {
    const calls: Array<[string, RequestInit | undefined]> = [], waits: number[] = [];
    const transport = async (path: string, init?: RequestInit) => {
      calls.push([path, init]);
      return new Response(null, calls.length === 1 ? { status: 429, headers: { "Retry-After": "2" } } : { status: 200 });
    };
    const init = { method: "POST", body: "same-payload" };
    const response = await fetchWithRateLimitRetry(transport, "/api/v1/optimize", init, { sleep: async ms => { waits.push(ms); } });
    expect(response.status).toBe(200);
    expect(calls).toEqual([["/api/v1/optimize", init], ["/api/v1/optimize", init]]);
    expect(waits).toEqual([2000]);
  });
  it("bounds retries and does not retry authentication failures or long windows", async () => {
    let calls = 0;
    const transport = async () => { calls++; return new Response(null, { status: 429, headers: { "Retry-After": "1" } }); };
    expect((await fetchWithRateLimitRetry(transport, "path", undefined, { sleep: async () => {} })).status).toBe(429);
    expect(calls).toBe(3);
    const sleep = async () => { throw new Error("must not sleep"); };
    expect((await fetchWithRateLimitRetry(async () => new Response(null, { status: 401 }), "path", undefined, { sleep })).status).toBe(401);
    expect((await fetchWithRateLimitRetry(async () => new Response(null, { status: 429, headers: { "Retry-After": "120" } }), "path", undefined, { sleep })).status).toBe(429);
  });

  const row = (date: string, vehicles: number | null, repeat_index = 1): ExperimentSummary => ({
    date, weekday: "monday", ride_limit: 90, tour_limit: 150, students: 27, legs: 54,
    waves: 12, routes: 16, vehicles_required: vehicles, vehicle_count_proven: vehicles !== null,
    capacity_floor: 3, floor_gap: vehicles === null ? null : vehicles - 3,
    max_ride_min: 89, mean_ride_min: 40, total_vehicle_minutes: 100,
    status: vehicles === null ? "blocked_data" : "preview_ready", reason_codes: [], repeat_index, is_empty_day: false,
  });
  it("aggregates the primary repeat without doubling minutes", () => {
    const dates = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"];
    const rows = dates.flatMap((date, i) => [row(date, i + 1), row(date, i + 1, 2)]);
    expect(aggregateWeeks(rows)[0]).toMatchObject({
      weekly_fleet_need: 5, max_observed_vehicles: 5, total_vehicle_minutes: 500,
      complete_week: true, vehicle_count_proven: true, monday_vehicles: 1, friday_vehicles: 5,
    });
  });
  it("does not certify partial or blocked weeks", () => {
    expect(aggregateWeeks([row("2026-10-05", 3)])[0]).toMatchObject({ weekly_fleet_need: null, complete_week: false, total_vehicle_minutes: null });
    const rows = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"].map((date, i) => row(date, i === 2 ? null : 3));
    expect(aggregateWeeks(rows)[0]).toMatchObject({ weekly_fleet_need: null, complete_week: false, vehicle_count_proven: false });
  });
  it("keeps weekend observations out of certified weekday fleet and minutes", () => {
    const rows = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"].map(date => row(date, 3));
    rows.push({ ...row("2026-10-10", 10), total_vehicle_minutes: 200 });
    expect(aggregateWeeks(rows)[0]).toMatchObject({ weekly_fleet_need: 3, total_vehicle_minutes: 500, max_observed_vehicles: 10, observed_vehicle_minutes: 700 });
  });
  it("keeps entirely unknown observed duration unknown", () => {
    expect(aggregateWeeks([{ ...row("2026-10-05", null), total_vehicle_minutes: null }])[0])
      .toMatchObject({ observed_vehicle_minutes: null, total_vehicle_minutes: null });
  });
  it("ignores only the repeat index when comparing summaries", () => {
    expect(summariesMatch(row("2026-10-05", 3), row("2026-10-05", 3, 2))).toBe(true);
    expect(summariesMatch(row("2026-10-05", 3), row("2026-10-05", 4, 2))).toBe(false);
  });
  it("anonymizes nested values and keys, IDs embedded in synthetic nodes, and vehicles", () => {
    const id = "2026-10-05:pickup:private-student";
    const other = "2026-10-05:pickup:private-second";
    const raw = { occurrenceLabels: { [id]: "Sw1", [other]: "Sw1" }, fleet: { activeVehicleIds: ["private-vehicle"] },
      assignments: [{ physicalVehicleId: "private-vehicle", occurrenceIds: [id, other] }],
      jobs: [{ result: { routes: [{ vehicle_id: "private-vehicle", student_ids: [id, other] }] } }],
      certificate: { [id]: `Sw1#${id}`, nested: { name: "Secret Person", email: "private@example.org", student_id: "private-student" } } };
    const output = JSON.stringify(anonymizeResponse(raw));
    expect(output).not.toMatch(/private-student|private-second|private-vehicle|Secret Person|private@example/);
    expect(output).toContain("Sw1");
    expect(Object.keys((anonymizeResponse(raw) as typeof raw).occurrenceLabels)).toHaveLength(2);
  });
});
