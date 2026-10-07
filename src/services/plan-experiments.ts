import { z } from "zod";
import { isRealServiceDate } from "./istanbul-service-date";
import { buildDailyPlanView } from "./daily-plan-view";
import { parseDudulluPreviewResponse } from "./dudullu-preview-response";
import type { MatrixArc } from "./dudullu-preview";

export interface ExperimentArgs {
  dates: string[];
  rideLimits: number[];
  tourLimit: number;
  fleet: "virtual" | "live";
  repeat: number;
  out: string;
}
const weekdayNames = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const dateObject = (date: string) => new Date(`${date}T00:00:00Z`);
const isoDate = (date: Date) => date.toISOString().slice(0, 10);
const addDays = (date: string, days: number) => {
  const value = dateObject(date);
  value.setUTCDate(value.getUTCDate() + days);
  return isoDate(value);
};

export function parseExperimentArgs(argv: readonly string[], now = new Date()): ExperimentArgs {
  const allowed = new Set(["--week-of", "--dates", "--ride-limits", "--tour-limit", "--fleet", "--out", "--repeat"]);
  const args = new Map<string, string>();
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i], value = argv[i + 1];
    if (!allowed.has(key) || args.has(key) || !value?.trim() || value.startsWith("--")) throw new Error("Invalid or duplicate experiment argument");
    args.set(key, value.trim());
  }
  if (args.has("--dates") === args.has("--week-of")) throw new Error("Provide exactly one of --week-of or --dates");
  const realDate = (date: string) => /^\d{4}-\d{2}-\d{2}$/.test(date) && isRealServiceDate(date);
  let dates: string[];
  if (args.has("--week-of")) {
    const monday = args.get("--week-of")!;
    if (!realDate(monday) || dateObject(monday).getUTCDay() !== 1) throw new Error("--week-of must be a real Monday");
    dates = Array.from({ length: 5 }, (_, i) => addDays(monday, i));
  } else dates = args.get("--dates")!.split(",").map(value => value.trim());
  if (!dates.every(realDate) || new Set(dates).size !== dates.length) throw new Error("Dates must be real and distinct");
  const integer = (value: string, min: number, max: number) => {
    if (!/^\d+$/.test(value) || Number(value) < min || Number(value) > max) throw new Error("Experiment limit outside accepted range");
    return Number(value);
  };
  const rideLimits = (args.get("--ride-limits") ?? "50,60,70,90").split(",").map(value => integer(value.trim(), 15, 240));
  if (new Set(rideLimits).size !== rideLimits.length) throw new Error("Ride limits must be distinct");
  const fleet = args.get("--fleet") ?? "virtual";
  if (fleet !== "virtual" && fleet !== "live") throw new Error("Fleet must be virtual or live");
  return {
    dates: dates.sort(), rideLimits, fleet,
    tourLimit: integer(args.get("--tour-limit") ?? "150", 30, 300),
    repeat: integer(args.get("--repeat") ?? "1", 1, 2),
    out: args.get("--out") ?? `.temp/experiments/${now.toISOString().replace(/[:.]/g, "-")}`,
  };
}

const digest = z.string().regex(/^[0-9a-f]{64}$/);
const matrixSchema = z.object({
  id: z.string(), version: digest, sha256: digest, source: z.literal("supabase"),
  provenance: z.object({
    source: z.literal("supabase"), sha256: digest,
    location_count: z.number().int().positive(), loaded_at: z.string().datetime({ offset: true }),
  }),
  arcs: z.array(z.object({
    origin_code: z.string().min(1), destination_code: z.string().min(1), duration_minutes: z.number().finite().positive(),
  })),
});
export type ExperimentMatrix = z.infer<typeof matrixSchema>;
export function captureMatrixSnapshot(value: unknown): ExperimentMatrix {
  const matrix = matrixSchema.parse(value);
  if (matrix.id !== `time_matrix:sha256:${matrix.sha256}` || matrix.version !== matrix.sha256 || matrix.provenance.sha256 !== matrix.sha256) {
    throw new Error("Matrix snapshot provenance mismatch");
  }
  return matrix;
}

interface MetricJob {
  direction: "pickup" | "dropoff";
  result: { routes: readonly {
    student_ids: readonly string[]; sw_count: number; so_count: number;
    route_details: readonly { location1: string; location2: string }[];
  }[] };
}
const round = (value: number) => Math.round(value * 1_000_000) / 1_000_000;
export function routeMetrics(jobs: readonly MetricJob[], arcs: readonly MatrixArc[]) {
  const costs = new Map<string, number>();
  for (const arc of arcs) {
    const key = JSON.stringify([arc.origin_code, arc.destination_code]);
    if (costs.has(key) || !Number.isFinite(arc.duration_minutes) || arc.duration_minutes <= 0) throw new Error("Invalid authoritative arc");
    costs.set(key, arc.duration_minutes);
  }
  let totalVehicleMinutes = 0, rideSum = 0, passengers = 0;
  for (const job of jobs) for (const route of job.result.routes) {
    const steps = route.route_details;
    if (steps.length < 2 || steps.length - 1 !== route.student_ids.length || route.student_ids.length !== route.sw_count + route.so_count) {
      throw new Error("Passenger coverage mismatch");
    }
    const depot = steps[0].location1;
    if (steps.at(-1)!.location2 !== depot) throw new Error("Tour is not closed");
    const durations = steps.map((step, i) => {
      if (i > 0 && steps[i - 1].location2 !== step.location1) throw new Error("Disconnected route");
      if (i < steps.length - 1 && step.location2 === depot) throw new Error("Interior depot visit");
      const value = step.location1 === step.location2 ? 0 : costs.get(JSON.stringify([step.location1, step.location2]));
      if (value === undefined) throw new Error("Authoritative route cost missing");
      return value;
    });
    const total = durations.reduce((sum, value) => sum + value, 0);
    totalVehicleMinutes += total;
    let elapsed = 0;
    for (let i = 0; i < durations.length - 1; i++) {
      elapsed += durations[i];
      rideSum += job.direction === "pickup" ? total - elapsed : elapsed;
      passengers++;
    }
  }
  return { meanRideMinutes: passengers ? round(rideSum / passengers) : null, totalVehicleMinutes: round(totalVehicleMinutes) };
}

export interface ExperimentSummary {
  date: string; weekday: string; ride_limit: number; tour_limit: number;
  students: number | null; legs: number | null; waves: number | null; routes: number | null;
  vehicles_required: number | null; vehicle_count_proven: boolean; capacity_floor: number | null; floor_gap: number | null;
  max_ride_min: number | null; mean_ride_min: number | null; total_vehicle_minutes: number | null;
  status: string; reason_codes: string[]; repeat_index: number; is_empty_day: boolean;
}
export function summarizePlan(value: unknown, matrix: ExperimentMatrix | null, date: string, ride: number, tour: number, repeat: number): ExperimentSummary {
  const base = { date, weekday: weekdayNames[dateObject(date).getUTCDay()], ride_limit: ride, tour_limit: tour, repeat_index: repeat };
  if (typeof value === "object" && value !== null && "error" in value) return {
    ...base, students: null, legs: null, waves: null, routes: null, vehicles_required: null, vehicle_count_proven: false,
    capacity_floor: null, floor_gap: null, max_ride_min: null, mean_ride_min: null, total_vehicle_minutes: null,
    status: "preview_unavailable", reason_codes: ["PREVIEW_UNAVAILABLE"], is_empty_day: false,
  };
  const response = parseDudulluPreviewResponse(value);
  const view = buildDailyPlanView(response);
  if (response.serviceDate !== date || response.limits.maxRideTimeMinutes !== ride || response.limits.maxTourMinutes !== tour) throw new Error("Run contract mismatch");
  let metrics: { meanRideMinutes: number | null; totalVehicleMinutes: number | null } = { meanRideMinutes: null, totalVehicleMinutes: view.isEmptyDay ? 0 : null };
  if (response.jobs.length) {
    if (!matrix || !value || typeof value !== "object" || !("matrix" in value) ||
      (value.matrix as { sha256?: string } | null)?.sha256 !== matrix.sha256) throw new Error("Run matrix provenance missing");
    metrics = routeMetrics(response.jobs, matrix.arcs);
  }
  return {
    ...base, students: view.summary.students, legs: view.summary.trips,
    waves: view.sections.reduce((sum, section) => sum + section.waves.length, 0), routes: view.summary.routes,
    vehicles_required: view.summary.neededVehicles, vehicle_count_proven: response.vehicleSummary?.minimumProven ?? false,
    capacity_floor: view.summary.capacityFloor?.vehicles ?? null,
    floor_gap: view.summary.neededVehicles === null || view.summary.capacityFloor === null ? null : view.summary.neededVehicles - view.summary.capacityFloor.vehicles,
    max_ride_min: view.summary.maxRideMinutes, mean_ride_min: metrics.meanRideMinutes,
    total_vehicle_minutes: metrics.totalVehicleMinutes, status: response.status, reason_codes: [...response.reasonCodes], is_empty_day: view.isEmptyDay,
  };
}

export function summariesMatch(a: ExperimentSummary, b: ExperimentSummary) {
  return JSON.stringify({ ...a, repeat_index: 0 }) === JSON.stringify({ ...b, repeat_index: 0 });
}
export function aggregateWeeks(rows: readonly ExperimentSummary[]) {
  const groups = new Map<string, ExperimentSummary[]>();
  for (const row of rows.filter(row => row.repeat_index === 1)) {
    const monday = addDays(row.date, -((dateObject(row.date).getUTCDay() + 6) % 7));
    const key = `${monday}:${row.ride_limit}:${row.tour_limit}`;
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return [...groups.values()].map(group => {
    const first = group[0];
    const monday = addDays(first.date, -((dateObject(first.date).getUTCDay() + 6) % 7));
    const count = (row: ExperimentSummary | undefined) => row?.is_empty_day ? 0 : row?.vehicles_required ?? null;
    const daily = Array.from({ length: 5 }, (_, i) => group.find(row => row.date === addDays(monday, i)));
    const complete = daily.every(row => row && count(row) !== null && (row.is_empty_day || ["preview_ready", "indeterminate"].includes(row.status)));
    const known = group.map(count).filter((value): value is number => value !== null);
    const knownMinutes = group.map(row => row.total_vehicle_minutes).filter((value): value is number => value !== null);
    const observedMinutes = knownMinutes.length ? round(knownMinutes.reduce((sum, value) => sum + value, 0)) : null;
    return {
      week_of: monday, ride_limit: first.ride_limit, tour_limit: first.tour_limit,
      weekly_fleet_need: complete ? Math.max(...daily.map(row => count(row)!)) : null,
      max_observed_vehicles: known.length ? Math.max(...known) : null,
      vehicle_count_proven: complete && daily.every(row => row!.is_empty_day || row!.vehicle_count_proven), complete_week: complete,
      monday_vehicles: count(daily[0]), tuesday_vehicles: count(daily[1]), wednesday_vehicles: count(daily[2]), thursday_vehicles: count(daily[3]), friday_vehicles: count(daily[4]),
      total_vehicle_minutes: complete && daily.every(row => row!.total_vehicle_minutes !== null)
        ? round(daily.reduce((sum, row) => sum + row!.total_vehicle_minutes!, 0)) : null,
      observed_vehicle_minutes: observedMinutes,
      per_day: Object.fromEntries(group.map(row => [row.date, { vehicles: count(row), status: row.status, proven: row.vehicle_count_proven }])),
    };
  });
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
export function anonymizeResponse(value: unknown): unknown {
  const replacements = new Map<string, string>();
  const labels = record(value) && record(value.occurrenceLabels) ? value.occurrenceLabels : {};
  const byLocation = new Map<string, Set<string>>();
  for (const [occurrence, location] of Object.entries(labels)) {
    const match = occurrence.match(/^(\d{4}-\d{2}-\d{2}):(pickup|dropoff):(.+)$/);
    if (match && typeof location === "string") {
      const ids = byLocation.get(location) ?? new Set<string>();
      ids.add(match[3]); byLocation.set(location, ids);
    }
  }
  for (const [location, ids] of byLocation) [...ids].sort().forEach((id, i) => replacements.set(id, `${location}~${i + 1}`));
  for (const occurrence of Object.keys(labels)) {
    const match = occurrence.match(/^(\d{4}-\d{2}-\d{2}):(pickup|dropoff):(.+)$/);
    if (match && replacements.has(match[3])) replacements.set(occurrence, `${match[1]}:${match[2]}:${replacements.get(match[3])}`);
  }
  const vehicles = new Set<string>();
  const collect = (item: unknown, key = "") => {
    if (["vehicle_id", "vehicleId", "physicalVehicleId"].includes(key) && typeof item === "string") vehicles.add(item);
    if (key === "activeVehicleIds" && Array.isArray(item)) item.forEach(id => { if (typeof id === "string") vehicles.add(id); });
    if (Array.isArray(item)) item.forEach(child => collect(child));
    else if (record(item)) Object.entries(item).forEach(([name, child]) => collect(child, name));
  };
  collect(value);
  [...vehicles].sort().forEach((id, i) => replacements.set(id, `Vehicle${i + 1}`));
  const pairs = [...replacements].sort((a, b) => b[0].length - a[0].length);
  const otherIds = new Map<string, string>();
  const clean = (text: string) => {
    let output = text;
    for (const [id, alias] of pairs) output = output.split(id).join(alias);
    return output.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted]")
      .replace(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi, id => {
        if (!otherIds.has(id)) otherIds.set(id, `Id${otherIds.size + 1}`);
        return otherIds.get(id)!;
      });
  };
  const visit = (item: unknown): unknown => {
    if (typeof item === "string") return clean(item);
    if (Array.isArray(item)) return item.map(visit);
    if (record(item)) return Object.fromEntries(Object.entries(item).map(([key, child]) => [clean(key),
      /^(name|email|full_name|first_name|last_name)$/i.test(key) ? "[redacted]" : visit(child)]));
    return item;
  };
  return visit(value);
}

export function toCsv(rows: readonly object[], columns: readonly string[]): string {
  const cell = (value: unknown) => {
    const text = value === null || value === undefined ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  return [columns.join(","), ...rows.map(row => columns.map(key => cell((row as Record<string, unknown>)[key])).join(","))].join("\n") + "\n";
}
export const SUMMARY_COLUMNS = ["date", "weekday", "ride_limit", "tour_limit", "students", "legs", "waves", "routes", "vehicles_required", "vehicle_count_proven", "capacity_floor", "floor_gap", "max_ride_min", "mean_ride_min", "total_vehicle_minutes", "status", "reason_codes", "repeat_index", "is_empty_day"] as const;
