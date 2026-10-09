import { parseExperimentArgs } from "./plan-experiments";
import type { MatrixArc } from "./dudullu-preview";

// Heterogeneous fleet scenarios (design section 8). Fleet types come ONLY from the command
// line (design section 1, "Fleet source"); nothing here reads the vehicles table.

export interface FleetTypeSpec {
  typeId: string;
  swCapacity: number;
  soCapacity: number;
  /** Optional shared seat limit (`:capN`): Sw + So <= totalCapacity. */
  totalCapacity?: number;
  cooldownMinutes: number;
  /** Per-type ride limit; defaults to the experiment ride limit when absent. */
  rideLimit?: number;
  /** Per-type tour limit; defaults to the experiment tour limit when absent. */
  tourLimit?: number;
}
/** "A" = minimum all-large; an integer is the fixed number of large vehicles L. */
export type ScenarioKey = "A" | number;

export interface FleetArgs {
  dates: string[];
  rideLimits: number[];
  tourLimit: number;
  fleetTypes: FleetTypeSpec[];
  fixedTypeId: string;
  minimizeTypeId: string | null;
  scenarios: ScenarioKey[];
  maxCars: number | null;
  nodeBudget: number;
  selectionTimeLimitSeconds: number;
  out: string;
}

/** Largest fixed L: the menu holds quota options q = 0..L plus the baseline (router cap: 6 options). */
export const MAX_FLEET_SCENARIO_L = 4;
const TYPE_ID = /^[a-z][a-z0-9_-]{0,31}$/;

/** Grammar: `<id>:<n>sw<m>so[:capN][:cd<min>][:r<R>][:t<T>]`, each optional part at most once. */
export function parseFleetType(text: string): FleetTypeSpec {
  const [typeId, capacity, ...options] = text.trim().split(":");
  const match = capacity?.match(/^(\d{1,3})sw(\d{1,3})so$/);
  if (!typeId || !TYPE_ID.test(typeId) || !match) throw new Error("Invalid fleet type");
  const spec: FleetTypeSpec = { typeId, swCapacity: Number(match[1]), soCapacity: Number(match[2]), cooldownMinutes: 10 };
  if (spec.swCapacity + spec.soCapacity < 1) throw new Error("Invalid fleet type");
  const seen = new Set<string>();
  for (const option of options) {
    const m = option.match(/^(cap|cd|r|t)(\d{1,3})$/);
    if (!m || seen.has(m[1])) throw new Error("Invalid fleet type");
    seen.add(m[1]);
    const value = Number(m[2]);
    if (m[1] === "cap") {
      if (value < 1 || value > spec.swCapacity + spec.soCapacity) throw new Error("Invalid fleet type");
      spec.totalCapacity = value;
    } else if (m[1] === "cd") {
      if (value > 240) throw new Error("Invalid fleet type");
      spec.cooldownMinutes = value;
    } else if (m[1] === "r") {
      if (value < 15 || value > 240) throw new Error("Invalid fleet type");
      spec.rideLimit = value;
    } else {
      if (value < 30 || value > 300) throw new Error("Invalid fleet type");
      spec.tourLimit = value;
    }
  }
  return spec;
}

export function parseFleetArgs(argv: readonly string[], now = new Date()): FleetArgs {
  const shared = new Set(["--week-of", "--dates", "--ride-limits", "--tour-limit", "--out"]);
  const own = new Set([
    "--fleet-types", "--fixed-type", "--minimize-type", "--scenarios", "--max-cars", "--node-budget", "--selection-time-limit",
  ]);
  const base: string[] = [];
  const args = new Map<string, string>();
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i], value = argv[i + 1];
    if (!(shared.has(key) || own.has(key)) || args.has(key) || !value?.trim() || value.startsWith("--")) {
      throw new Error("Invalid or duplicate fleet argument");
    }
    args.set(key, value.trim());
    if (shared.has(key)) base.push(key, value);
  }
  // Dates, ride limits, tour limit and --out follow the plan-experiment rules exactly.
  const common = parseExperimentArgs(base, now);
  const integer = (value: string, min: number, max: number) => {
    if (!/^\d+$/.test(value) || Number(value) < min || Number(value) > max) throw new Error("Fleet limit outside accepted range");
    return Number(value);
  };
  if (!args.has("--fleet-types")) throw new Error("--fleet-types is required");
  const fleetTypes = args.get("--fleet-types")!.split(",").map(parseFleetType);
  if (fleetTypes.length > 2) throw new Error("At most two fleet types are supported (one fixed, one minimised)");
  if (new Set(fleetTypes.map((type) => type.typeId)).size !== fleetTypes.length) throw new Error("Duplicate fleet type id");
  for (const type of fleetTypes) {
    if ((type.rideLimit ?? 0) > Math.min(...common.rideLimits) || (type.tourLimit ?? 0) > common.tourLimit) {
      throw new Error("Per-type limits cannot exceed the experiment limits");
    }
  }
  const known = (id: string) => fleetTypes.some((type) => type.typeId === id);
  let fixedTypeId = args.get("--fixed-type");
  if (fixedTypeId === undefined) {
    if (fleetTypes.length !== 1) throw new Error("--fixed-type is required with several fleet types");
    fixedTypeId = fleetTypes[0].typeId;
  }
  if (!known(fixedTypeId)) throw new Error("Unknown fixed type");
  const scenarios: ScenarioKey[] = (args.get("--scenarios") ?? "A,1,2,3").split(",").map((value) => {
    const text = value.trim();
    return text === "A" ? "A" : integer(text, 0, MAX_FLEET_SCENARIO_L);
  });
  if (new Set(scenarios).size !== scenarios.length) throw new Error("Duplicate scenario");
  const hasFixedL = scenarios.some((value) => value !== "A");
  const minimizeTypeId = args.get("--minimize-type") ?? null;
  if (fleetTypes.length === 2) {
    if (minimizeTypeId === null) throw new Error("--minimize-type is required with two fleet types");
    if (!known(minimizeTypeId) || minimizeTypeId === fixedTypeId) throw new Error("Unknown minimise type");
  } else if (minimizeTypeId !== null || hasFixedL) {
    throw new Error("Fixed-L scenarios and --minimize-type need two fleet types");
  }
  return {
    dates: common.dates, rideLimits: common.rideLimits, tourLimit: common.tourLimit, out: common.out,
    fleetTypes, fixedTypeId, minimizeTypeId, scenarios,
    maxCars: args.has("--max-cars") ? integer(args.get("--max-cars")!, 0, 50) : null,
    nodeBudget: integer(args.get("--node-budget") ?? "200000", 1000, 5_000_000),
    selectionTimeLimitSeconds: integer(args.get("--selection-time-limit") ?? "30", 1, 600),
  };
}

interface ProfileJob {
  direction: "pickup" | "dropoff";
  result: { routes: readonly {
    student_ids: readonly string[]; sw_count: number; so_count: number;
    route_details: readonly { location1: string; location2: string }[];
  }[] };
}
export interface RouteRideProfile { routeMinutes: number; rides: number[] }

/**
 * Per-route vehicle minutes and per-passenger pure travel minutes on the authoritative arcs, in
 * the order of `jobs` then `routes`. Same definitions and fail-closed checks as `routeMetrics`.
 */
export function routeRideProfile(jobs: readonly ProfileJob[], arcs: readonly MatrixArc[]): RouteRideProfile[] {
  const costs = new Map<string, number>();
  for (const arc of arcs) {
    const key = JSON.stringify([arc.origin_code, arc.destination_code]);
    if (costs.has(key) || !Number.isFinite(arc.duration_minutes) || arc.duration_minutes <= 0) throw new Error("Invalid authoritative arc");
    costs.set(key, arc.duration_minutes);
  }
  const profile: RouteRideProfile[] = [];
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
    const rides: number[] = [];
    let elapsed = 0;
    for (let i = 0; i < durations.length - 1; i++) {
      elapsed += durations[i];
      rides.push(job.direction === "pickup" ? total - elapsed : elapsed);
    }
    profile.push({ routeMinutes: total, rides });
  }
  return profile;
}

const round6 = (value: number) => Math.round(value * 1_000_000) / 1_000_000;
/** Nearest-rank percentile of a non-empty sorted list (p in (0,1]). */
export function nearestRank(sorted: readonly number[], p: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(p * sorted.length) - 1))];
}
export interface RideStatistics { passengers: number; mean: number; median: number; p90: number; max: number }
export function rideStatistics(rides: readonly number[]): RideStatistics | null {
  if (rides.length === 0) return null;
  const sorted = [...rides].sort((a, b) => a - b);
  const middle = sorted.length >> 1;
  return {
    passengers: sorted.length,
    mean: round6(sorted.reduce((sum, value) => sum + value, 0) / sorted.length),
    median: round6(sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2),
    p90: round6(nearestRank(sorted, 0.9)),
    max: round6(sorted[sorted.length - 1]),
  };
}
