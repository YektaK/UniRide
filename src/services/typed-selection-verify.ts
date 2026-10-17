import "server-only";
import { z } from "zod";
import type { PreviewRouteInterval } from "@/services/dudullu-preview";
import type { FleetScenarioParams } from "@/services/fleet-scenario-run";
import { typeAccepts } from "@/services/fleet-scenario-run";
import {
  assignTypedVehicles,
  verifyTypedAssignment,
  type TypedFleetType,
} from "@/services/typed-fleet-assignment";

/**
 * WP-E4b: independent TypeScript confirmation of one day selection over typed menus
 * (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 1.5, "Independent confirmation").
 *
 * The input is route data (route_details, student_ids, class counts), the vehicle types and limits, and the
 * selection (the chosen option's routes per wave, each with its label). Intervals and route facts are rebuilt
 * here from `route_details`, the anchor and the direction exactly as `buildDudulluPreview` and `scenarioL`
 * do; the Python values travel along only to be compared. Then the producer's own checks run:
 * `assignTypedVehicles`, `verifyTypedAssignment` and the `typeAccepts` recheck of every assigned route
 * (`fleet-scenario-run.ts` confirmation flow). Pure and read-only: no I/O, no clock.
 */

const TIME_SCALE_DEFAULT = 100;
const CENTI_TOLERANCE = 1e-6;
const SERVICE_DAY_END_MINUTES = 24 * 60;

const typeSchema = z.object({
  typeId: z.string().min(1),
  swCapacity: z.number(),
  soCapacity: z.number(),
  totalCapacity: z.number().optional(),
  cooldownMinutes: z.number(),
  rideLimit: z.number().optional(),
  tourLimit: z.number().optional(),
});

const pythonRouteSchema = z.object({
  start: z.number(), end: z.number(), minutes: z.number(), large_ok: z.boolean(), car_ok: z.boolean(),
});

const routeSchema = z.object({
  route_details: z.array(z.object({
    location1: z.string(), location2: z.string(), duration: z.number(), distance: z.number().optional(),
  })),
  student_ids: z.array(z.string()),
  sw_count: z.number(),
  so_count: z.number(),
  total_duration_minutes: z.number(),
  label: z.enum(["large", "car"]),
  python: pythonRouteSchema,
});

export const verifyCaseSchema = z.object({
  caseId: z.string(),
  timeScale: z.number().int().positive().default(TIME_SCALE_DEFAULT),
  fixedType: typeSchema,
  minimiseType: typeSchema,
  limits: z.object({ maxRideTimeMinutes: z.number(), maxTourMinutes: z.number() }),
  maxLarge: z.number().int().nonnegative(),
  maxCars: z.number().int().nonnegative().nullable().optional(),
  nodeBudget: z.number().int().positive().optional(),
  pythonCooldowns: z.object({ large: z.number(), car: z.number() }).optional(),
  waves: z.array(z.object({
    waveId: z.string(),
    direction: z.enum(["pickup", "dropoff"]),
    anchorMinutes: z.number(),
    routes: z.array(routeSchema),
  })),
});

export type VerifyCase = z.input<typeof verifyCaseSchema>;

export interface IntervalDifference {
  readonly waveId: string;
  readonly routeIndex: number | null;
  readonly field: string;
  readonly python: number | boolean;
  readonly typescript: number | boolean;
}

export interface VerifyResult {
  readonly caseId: string;
  /** True only when there is no problem, no recheck failure, no interval difference and the assignment is proven or a witness. */
  readonly ok: boolean;
  readonly assignment: {
    readonly status: string;
    readonly reasonCodes: readonly string[];
    readonly cars: number | null;
    readonly countsByType: Readonly<Record<string, number>>;
    readonly nodes: number;
  };
  /** Structural problems (precision, service day, labels) and the problems of `verifyTypedAssignment`. */
  readonly problems: readonly string[];
  /** The `typeAccepts` recheck of each assigned route. */
  readonly recheck: { readonly routesChecked: number; readonly failures: readonly string[] };
  readonly intervalDifferences: readonly IntervalDifference[];
}

interface BuiltRoute {
  readonly waveId: string;
  readonly routeIndex: number;
  readonly interval: PreviewRouteInterval;
  readonly minutes: number;
  readonly direction: "pickup" | "dropoff";
  readonly source: z.infer<typeof routeSchema>;
}

const round6 = (value: number) => Math.round(value * 1_000_000) / 1_000_000;

export function verifyTypedSelection(raw: VerifyCase): VerifyResult {
  const input = verifyCaseSchema.parse(raw);
  const problems: string[] = [];
  const differences: IntervalDifference[] = [];
  const scale = input.timeScale;
  const centi = (value: number, where: string): number => {
    const scaled = value * scale;
    const rounded = Math.round(scaled);
    if (!Number.isFinite(scaled) || Math.abs(scaled - rounded) > CENTI_TOLERANCE) {
      problems.push(`SELECTION_INTERVAL_PRECISION: ${where} ${value} is not on the 1/${scale}-minute grid`);
    }
    return Math.max(0, rounded);
  };
  const params = { maxRideTimeMinutes: input.limits.maxRideTimeMinutes, maxTourMinutes: input.limits.maxTourMinutes } as FleetScenarioParams;

  const built: BuiltRoute[] = [];
  for (const wave of input.waves) {
    wave.routes.forEach((route, routeIndex) => {
      const where = `${wave.waveId}#${routeIndex}`;
      const total = route.route_details.reduce((sum, step) => sum + step.duration, 0);
      const startMinutes = wave.direction === "pickup" ? wave.anchorMinutes - total : wave.anchorMinutes;
      const endMinutes = wave.direction === "pickup" ? wave.anchorMinutes : wave.anchorMinutes + total;
      if (route.route_details.length === 0) problems.push(`${where}: NO_ROUTE_STEPS`);
      if (!(startMinutes >= 0 && endMinutes <= SERVICE_DAY_END_MINUTES)) problems.push(`${where}: ROUTE_OUTSIDE_SERVICE_DAY`);
      built.push({
        waveId: wave.waveId, routeIndex, minutes: endMinutes - startMinutes, direction: wave.direction, source: route,
        interval: {
          jobId: wave.waveId, routeIndex, vehicleId: `${wave.waveId}-r${routeIndex}`, direction: wave.direction,
          startMinutes, endMinutes, occurrenceIds: route.student_ids, swCount: route.sw_count, soCount: route.so_count,
        },
      });
    });
  }

  const factsOf = (item: BuiltRoute) => ({
    interval: item.interval,
    route: {
      vehicle_id: item.interval.vehicleId, route_details: item.source.route_details.map((s) => ({ ...s, distance: s.distance ?? 0 })),
      total_duration_minutes: item.source.total_duration_minutes, sw_count: item.source.sw_count, so_count: item.source.so_count,
      student_ids: item.source.student_ids,
    },
    minutes: item.minutes, direction: item.direction,
  });
  const compare = (item: BuiltRoute, field: string, python: number | boolean, typescript: number | boolean) => {
    if (python !== typescript) differences.push({ waveId: item.waveId, routeIndex: item.routeIndex, field, python, typescript });
  };
  for (const item of built) {
    const facts = factsOf(item);
    const start = centi(item.interval.startMinutes, `${item.waveId}#${item.routeIndex} start`);
    const end = Math.max(start + 1, centi(item.interval.endMinutes, `${item.waveId}#${item.routeIndex} end`));
    const largeOk = typeAccepts(input.fixedType, facts, params);
    const carOk = typeAccepts(input.minimiseType, facts, params);
    const py = item.source.python;
    compare(item, "start", py.start, start);
    compare(item, "end", py.end, end);
    compare(item, "minutes", py.minutes, round6(item.minutes));
    compare(item, "large_ok", py.large_ok, largeOk);
    compare(item, "car_ok", py.car_ok, carOk);
    if (item.source.label === "large" && !largeOk) problems.push(`${item.waveId}#${item.routeIndex}: label large but the fixed type does not accept the route`);
    if (item.source.label === "car" && !carOk) problems.push(`${item.waveId}#${item.routeIndex}: label car but the minimised type does not accept the route`);
    // route_details are the verified steps: the stated total must be their sum (buildDudulluPreview: ROUTE_TOTAL_MISMATCH)
    const stepSum = item.source.route_details.reduce((sum, step) => sum + step.duration, 0);
    if (Math.abs(Math.round(item.source.total_duration_minutes * 100) / 100 - Math.round(stepSum * 100) / 100) > 0.000001) {
      problems.push(`${item.waveId}#${item.routeIndex}: ROUTE_TOTAL_MISMATCH`);
    }
  }
  if (input.pythonCooldowns !== undefined) {
    const caseId = input.caseId;
    const cl = centi(input.fixedType.cooldownMinutes, "cooldown_large");
    const cc = centi(input.minimiseType.cooldownMinutes, "cooldown_car");
    if (input.pythonCooldowns.large !== cl) differences.push({ waveId: caseId, routeIndex: null, field: "cooldown_large", python: input.pythonCooldowns.large, typescript: cl });
    if (input.pythonCooldowns.car !== cc) differences.push({ waveId: caseId, routeIndex: null, field: "cooldown_car", python: input.pythonCooldowns.car, typescript: cc });
  }

  const fleet: TypedFleetType[] = [
    { typeId: input.fixedType.typeId, swCapacity: input.fixedType.swCapacity, soCapacity: input.fixedType.soCapacity,
      ...(input.fixedType.totalCapacity === undefined ? {} : { totalCapacity: input.fixedType.totalCapacity }),
      cooldownMinutes: input.fixedType.cooldownMinutes, role: "fixed", count: input.maxLarge, idPrefix: "L" },
    { typeId: input.minimiseType.typeId, swCapacity: input.minimiseType.swCapacity, soCapacity: input.minimiseType.soCapacity,
      ...(input.minimiseType.totalCapacity === undefined ? {} : { totalCapacity: input.minimiseType.totalCapacity }),
      cooldownMinutes: input.minimiseType.cooldownMinutes, role: "minimise", idPrefix: "C",
      ...(input.maxCars === null || input.maxCars === undefined ? {} : { maxCount: input.maxCars }) },
  ];
  const assignment = assignTypedVehicles({
    intervals: built.map((item) => item.interval), types: fleet,
    ...(input.nodeBudget === undefined ? {} : { nodeBudget: input.nodeBudget }),
  });
  const summary = {
    status: assignment.status, reasonCodes: assignment.reasonCodes, cars: assignment.minimumCount,
    countsByType: assignment.countsByType, nodes: assignment.nodes,
  };
  const failures: string[] = [];
  let checked = 0;
  if (assignment.status === "proven" || assignment.status === "witness") {
    problems.push(...verifyTypedAssignment(assignment.assignments, fleet));
    const factsByKey = new Map(built.map((item) => [`${item.interval.jobId}#${item.interval.routeIndex}`, factsOf(item)] as const));
    for (const item of assignment.assignments) {
      const type = item.vehicleType === input.fixedType.typeId ? input.fixedType : input.minimiseType;
      const facts = factsByKey.get(`${item.jobId}#${item.routeIndex}`);
      checked += 1;
      if (!facts || !typeAccepts(type, facts, params)) failures.push(`route ${item.jobId}#${item.routeIndex} violates ${type.typeId} limits`);
    }
  }
  const ok = problems.length === 0 && failures.length === 0 && differences.length === 0 &&
    (assignment.status === "proven" || assignment.status === "witness");
  return { caseId: input.caseId, ok, assignment: summary, problems, recheck: { routesChecked: checked, failures }, intervalDifferences: differences };
}
