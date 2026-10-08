import "server-only";
import { z } from "zod";
import type { PreviewDemand } from "@/services/dudullu-preview";
import {
  buildDudulluPreview,
  buildVirtualFleet,
  longestStudentRideMinutes,
  type MatrixSnapshot,
  type PreviewJobInput,
  type PreviewReasonCode,
  type PreviewRouteInterval,
  type VerifiedPreviewJob,
  type VirtualFleetTemplate,
} from "@/services/dudullu-preview";
import {
  OPTIMIZER_MAX_VEHICLES,
  createDailyPlanDemandState,
  exactClock,
  fetchMatrixSnapshot,
  groupWaves,
  loadDailyPlanDemand,
  nodeMaps,
  violatesRideTime,
  type DailyPlanDeps,
} from "@/services/daily-plan-run";
import {
  assignTypedVehicles,
  verifyTypedAssignment,
  type TypedAssignment,
  type TypedAssignmentResult,
  type TypedFleetType,
} from "@/services/typed-fleet-assignment";
import { rideStatistics, routeRideProfile, type FleetTypeSpec, type RideStatistics, type ScenarioKey } from "@/services/fleet-scenario-args";
import { DUDULLU_DEPOT } from "@/services/dudullu-campus";

/**
 * Orchestrator of one (day, R) heterogeneous-fleet run (docs/designs/HETEROGENEOUS_FLEET_DESIGN.md
 * sections 2, 3.3, 4, 6, 8). READ-ONLY: demand and matrix are loaded exactly as `runDailyPlan`
 * does, the vehicles table is never queried (fleet types are parameters), nothing is written.
 *
 *   per wave:  baseline option = ga_split all-large routes (scenario A)
 *              + hf options q = 0..L: /optimize ga_split_hf with a quota of q large routes
 *   per L:     /internal/fleet-selection (CP-SAT over the menus) -> chosen option per wave
 *              -> TS assignTypedVehicles (independent proof / witness) + verifyTypedAssignment
 */

export const MENU_MAX_QUOTA = 4;

export interface FleetScenarioParams {
  readonly serviceDate: string;
  readonly maxRideTimeMinutes: number;
  readonly maxTourMinutes: number;
  /** The type of scenario A and the fixed-count type of scenarios 1..L. */
  readonly fixedType: FleetTypeSpec;
  /** The minimised (borrowed) type; null for single-type runs (scenario A only). */
  readonly minimiseType: FleetTypeSpec | null;
  readonly scenarios: readonly ScenarioKey[];
  readonly maxCars?: number | null;
  readonly nodeBudget?: number;
  readonly selectionTimeLimitSeconds?: number;
}

export type ScenarioStatus =
  | "ok"
  | "infeasible_for_L"
  | "blocked_data"
  | "indeterminate"
  | "selection_unavailable"
  | "verification_failed";
export type CarsStatus = "proven_over_menu" | "witness" | "indeterminate";

export interface ScenarioRoute {
  readonly jobId: string;
  readonly routeIndex: number;
  readonly direction: "pickup" | "dropoff";
  readonly anchorMinutes: number;
  readonly startMinutes: number;
  readonly endMinutes: number;
  readonly minutes: number;
  readonly swCount: number;
  readonly soCount: number;
  readonly vehicleType: string;
  readonly physicalVehicleId: string;
  /** Label the day selection chose (null for scenario A). */
  readonly selectionLabel: "large" | "car" | null;
  readonly occurrenceIds: readonly string[];
  readonly steps: readonly { location1: string; location2: string; duration: number }[];
}

export interface CarUsageWindow {
  readonly carId: string;
  readonly windowStartMinutes: number;
  readonly windowEndMinutes: number;
  readonly busyMinutes: number;
  readonly routeCount: number;
  readonly waves: readonly string[];
}

export interface ScenarioResult {
  readonly scenario: ScenarioKey;
  /** Fixed L (scenarios 1..); for A the minimum number of large vehicles found. */
  readonly largeLimit: number | null;
  readonly status: ScenarioStatus;
  readonly reasonCodes: readonly string[];
  readonly cars: number | null;
  readonly carsStatus: CarsStatus | null;
  /** Large vehicles actually used. */
  readonly largeVehicles: number | null;
  /** Scenario A only: the minimum large count is proven for the solver's fixed routes. */
  readonly largeVehiclesProven: boolean | null;
  readonly routes: readonly ScenarioRoute[];
  readonly largeRoutes: number;
  readonly carRoutes: number;
  readonly minutesByType: Readonly<Record<string, number>>;
  readonly totalVehicleMinutes: number | null;
  readonly ride: RideStatistics | null;
  readonly carUsageWindows: readonly CarUsageWindow[];
  readonly selection: {
    readonly status: string;
    readonly cars: number | null;
    readonly carMinutes: number | null;
    readonly claim: unknown;
    readonly optionByWave: Readonly<Record<string, string>>;
    readonly diagnostics: unknown;
    readonly stats: unknown;
  } | null;
  readonly assignment: {
    readonly status: string;
    readonly reasonCodes: readonly string[];
    readonly nodes: number;
    readonly lowerBoundsByType: Readonly<Record<string, number>>;
    readonly problems: readonly string[];
  } | null;
}

export interface MenuOptionRecord {
  readonly optionId: string;
  readonly kind: "baseline" | "quota";
  readonly quota: number | null;
  readonly status: "included" | "skipped_infeasible" | "skipped_duplicate" | "skipped_invalid" | "skipped_http_error";
  readonly routes: number | null;
  readonly reason: string | null;
}
export interface MenuWaveRecord {
  readonly waveId: string;
  readonly direction: "pickup" | "dropoff";
  readonly anchorMinutes: number;
  readonly legs: number;
  readonly options: readonly MenuOptionRecord[];
}

export interface FleetScenarioDay {
  readonly serviceDate: string;
  readonly status: "ready" | "empty_day" | "blocked_data";
  readonly reasonCodes: readonly string[];
  readonly dbVehiclesConsulted: false;
  readonly limits: { readonly maxRideTimeMinutes: number; readonly maxTourMinutes: number };
  readonly students: number;
  readonly legs: number;
  readonly waves: number;
  readonly occurrenceLabels: Readonly<Record<string, string>>;
  readonly matrix: MatrixSnapshot | null;
  readonly menu: readonly MenuWaveRecord[];
  readonly scenarios: readonly ScenarioResult[];
}

const routeSchema = z.object({
  vehicle_id: z.string(),
  route_details: z.array(z.object({ location1: z.string(), location2: z.string(), duration: z.number(), distance: z.number() })),
  total_duration_minutes: z.number(), total_distance_km: z.number().optional(),
  sw_count: z.number(), so_count: z.number(), student_ids: z.array(z.string()),
  vehicle_type: z.string().optional(),
});
const optimizeResultSchema = z.object({
  success: z.boolean(),
  routes: z.array(routeSchema),
  total_duration_minutes: z.number().optional(), feasibility_certificate: z.unknown().optional(),
});
type OptimizeResult = z.infer<typeof optimizeResultSchema>;

const selectionResponseSchema = z.object({
  status: z.enum(["optimal", "feasible", "infeasible_for_L", "infeasible_data", "indeterminate"]),
  cars: z.number().nullable(),
  large_peak: z.number().nullable(),
  car_minutes: z.number().nullable(),
  total_minutes: z.number().nullable(),
  selection: z.record(z.string(), z.object({
    option_id: z.string(), option_index: z.number(), labels: z.array(z.enum(["large", "car"])),
  })),
  diagnostics: z.unknown(),
  stats: z.unknown(),
});

const round6 = (value: number) => Math.round(value * 1_000_000) / 1_000_000;

function template(type: FleetTypeSpec): VirtualFleetTemplate {
  return { swCapacity: type.swCapacity, soCapacity: type.soCapacity, cooldownMinutes: type.cooldownMinutes };
}

function fits(type: FleetTypeSpec, sw: number, so: number): boolean {
  return sw <= type.swCapacity && so <= type.soCapacity;
}

interface RouteFacts {
  readonly interval: PreviewRouteInterval;
  readonly route: OptimizeResult["routes"][number];
  readonly minutes: number;
  readonly direction: "pickup" | "dropoff";
}

/** Whether the route respects the type's capacity pools and its own ride/tour limits. */
function typeAccepts(type: FleetTypeSpec, facts: RouteFacts, limits: FleetScenarioParams): boolean {
  if (!fits(type, facts.interval.swCount, facts.interval.soCount)) return false;
  const ride = type.rideLimit ?? limits.maxRideTimeMinutes;
  const tour = type.tourLimit ?? limits.maxTourMinutes;
  return facts.minutes <= tour + 1e-9 &&
    longestStudentRideMinutes(facts.route.route_details, facts.direction) <= ride + 1e-9;
}

interface WaveMenu {
  readonly waveId: string;
  readonly group: PreviewDemand[];
  readonly job: PreviewJobInput;
  readonly options: Array<{ optionId: string; baseline: boolean; verified: VerifiedPreviewJob }>;
  readonly record: MenuOptionRecord[];
}

function signature(job: VerifiedPreviewJob): string {
  return JSON.stringify(job.intervals.map((interval) => [...interval.occurrenceIds].sort()).sort());
}

function windowsFromAssignment(
  result: TypedAssignmentResult,
): CarUsageWindow[] {
  const waveOf = new Map<string, Set<string>>();
  for (const item of result.assignments) {
    if (item.vehicleType !== result.minimiseTypeId) continue;
    const set = waveOf.get(item.physicalVehicleId) ?? new Set<string>();
    set.add(item.jobId);
    waveOf.set(item.physicalVehicleId, set);
  }
  return result.usageWindows.map((window) => ({
    carId: window.vehicleId,
    windowStartMinutes: window.firstStartMinutes,
    windowEndMinutes: window.lastEndMinutes,
    busyMinutes: round6(window.busyMinutes),
    routeCount: window.routeCount,
    waves: [...(waveOf.get(window.vehicleId) ?? new Set<string>())].sort(),
  }));
}

export async function runFleetScenarioDay(
  deps: DailyPlanDeps,
  params: FleetScenarioParams,
): Promise<FleetScenarioDay> {
  const { serviceDate, maxRideTimeMinutes, maxTourMinutes, fixedType, minimiseType } = params;
  const { reader, optimizerFetch } = deps;
  const dayBase = {
    serviceDate, dbVehiclesConsulted: false as const,
    limits: { maxRideTimeMinutes, maxTourMinutes },
  };
  const integerScenarios = params.scenarios.filter((value): value is number => value !== "A");
  if (integerScenarios.length > 0 && minimiseType === null) throw new Error("Fixed-L scenarios need a minimise type");
  const blocked = (reasonCodes: readonly string[], extra: Partial<FleetScenarioDay> = {}): FleetScenarioDay => ({
    ...dayBase, status: "blocked_data", reasonCodes, students: 0, legs: 0, waves: 0,
    occurrenceLabels: {}, matrix: null, menu: [], scenarios: [], ...extra,
  });

  // ---- demand: exactly as the daily plan loads it (read-only, K1 admission assumption) ----
  const state = createDailyPlanDemandState(true);
  const loaded = await loadDailyPlanDemand(reader, serviceDate, true, state);
  if (loaded.kind === "blocked") return blocked([...new Set([...state.extraReasons, "LEG_DECISIONS_UNAVAILABLE"])]);
  if (loaded.kind === "empty" && state.extraReasons.includes("SCHEDULE_DATA_INVALID")) {
    // Invalid schedule data is not a healthy empty day.
    return blocked([...new Set(state.extraReasons)]);
  }
  if (loaded.kind === "empty") {
    const zero = (scenario: ScenarioKey): ScenarioResult => ({
      scenario, largeLimit: scenario === "A" ? 0 : scenario, status: "ok", reasonCodes: [], cars: 0,
      carsStatus: scenario === "A" ? null : "proven_over_menu", largeVehicles: 0,
      largeVehiclesProven: scenario === "A" ? true : null, routes: [], largeRoutes: 0, carRoutes: 0,
      minutesByType: {}, totalVehicleMinutes: 0, ride: null, carUsageWindows: [], selection: null, assignment: null,
    });
    return {
      ...dayBase, status: "empty_day", reasonCodes: [...new Set([...state.extraReasons, "NO_ADMITTED_DEMAND"])],
      students: 0, legs: 0, waves: 0, occurrenceLabels: {}, matrix: null, menu: [],
      scenarios: params.scenarios.map(zero),
    };
  }
  const admitted = loaded.admitted;
  const students = new Set(admitted.map((demand) => demand.studentId)).size;
  const counts = { students, legs: admitted.length };

  const matrix = await fetchMatrixSnapshot(optimizerFetch, admitted);
  if (matrix === null) {
    return blocked(["MATRIX_UNAVAILABLE"], { ...counts, occurrenceLabels: state.occurrenceLabels, waves: groupWaves(admitted).length });
  }
  const groups = groupWaves(admitted);
  const common = { occurrenceLabels: state.occurrenceLabels, matrix, waves: groups.length, ...counts };

  const postJson = async (path: string, body: unknown): Promise<{ status: number; json: unknown } | null> => {
    try {
      const response = await optimizerFetch(path, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
      });
      if (!response.ok) return { status: response.status, json: null };
      return { status: response.status, json: await response.json() };
    } catch {
      return null;
    }
  };
  const optimize = async (body: unknown): Promise<{ result: OptimizeResult } | { error: string }> => {
    const reply = await postJson("/api/v1/optimize", body);
    if (reply === null) return { error: "transport" };
    if (reply.json === null) return { error: `http_${reply.status}` };
    const parsed = optimizeResultSchema.safeParse(reply.json);
    return parsed.success ? { result: parsed.data } : { error: "invalid_result" };
  };

  const waveBase = (group: PreviewDemand[]) => {
    const first = group[0]!;
    return {
      mode: "sandbox", service_date: serviceDate, direction: first.direction,
      target_time: exactClock(first.anchorMinutes), expected_matrix_sha256: matrix.sha256,
      use_time_windows: false, is_asymmetric: true,
      depot: DUDULLU_DEPOT,
      students: group.map((demand) => ({
        id: demand.occurrenceId, occurrence_id: demand.occurrenceId,
        name: demand.studentId, location_code: demand.locationCode,
        disability_type: demand.disabilityType,
      })),
    };
  };
  const makeJob = (group: PreviewDemand[], result: OptimizeResult): PreviewJobInput => {
    const first = group[0]!;
    return {
      id: `${serviceDate}:${first.direction}:${first.anchorMinutes}`,
      serviceDate, direction: first.direction, anchorMinutes: first.anchorMinutes,
      demands: group, ...nodeMaps(group), result,
    };
  };

  // ---- baseline: scenario A routes per wave, request identical to runDailyPlan (virtual) ----
  const fixedTemplate = template(fixedType);
  const fixedVehicles = buildVirtualFleet(fixedTemplate, admitted.length);
  const baselineJobs: PreviewJobInput[] = [];
  for (const group of groups) {
    const first = group[0]!;
    const waveVehicles = fixedVehicles.slice(0, Math.min(group.length, OPTIMIZER_MAX_VEHICLES));
    const reply = await optimize({
      algorithm: "ga_split", mode: "sandbox", service_date: serviceDate,
      direction: first.direction, target_time: exactClock(first.anchorMinutes),
      expected_matrix_sha256: matrix.sha256, use_time_windows: false,
      is_asymmetric: true,
      max_travel_time: fixedType.tourLimit ?? maxTourMinutes, max_ride_time: fixedType.rideLimit ?? maxRideTimeMinutes,
      sw_capacity: Math.max(0, ...waveVehicles.map((vehicle) => vehicle.swCapacity)),
      so_capacity: Math.max(0, ...waveVehicles.map((vehicle) => vehicle.soCapacity)),
      depot: DUDULLU_DEPOT,
      students: waveBase(group).students,
      vehicles: waveVehicles.map((vehicle) => ({
        vehicle_id: vehicle.vehicleId, sw_capacity: vehicle.swCapacity,
        so_capacity: vehicle.soCapacity, cooldown_minutes: vehicle.cooldownMinutes,
      })),
    });
    if ("error" in reply) return blocked(["OPTIMIZATION_NOT_SUCCESSFUL"], common);
    if (!reply.result.success && violatesRideTime(reply.result.feasibility_certificate)) {
      return blocked(["RIDE_TIME_LIMIT_INFEASIBLE"], common);
    }
    baselineJobs.push(makeJob(group, reply.result));
  }
  const baselinePreview = buildDudulluPreview({
    serviceDate, demands: admitted, vehicles: fixedVehicles, matrix, jobs: baselineJobs,
  });
  if (baselinePreview.status === "blocked_data") {
    return blocked([...new Set(baselinePreview.reasonCodes)] as string[], common);
  }

  // ---- facts per verified route ------------------------------------------------------------
  const factsOf = (job: VerifiedPreviewJob): RouteFacts[] =>
    job.intervals.map((interval, index) => ({
      interval, route: job.result.routes[index] as OptimizeResult["routes"][number],
      minutes: interval.endMinutes - interval.startMinutes, direction: job.direction,
    }));

  // ---- scenario results --------------------------------------------------------------------
  const scenarioResults: ScenarioResult[] = [];
  const profileJobs = (jobs: readonly VerifiedPreviewJob[]) =>
    jobs.map((job) => ({ direction: job.direction, result: job.result }));

  const buildResult = (
    scenario: ScenarioKey,
    jobs: readonly VerifiedPreviewJob[],
    typeOf: (interval: PreviewRouteInterval) => { vehicleType: string; physicalVehicleId: string },
    labelOf: (interval: PreviewRouteInterval) => "large" | "car" | null,
    extra: Pick<ScenarioResult, "status" | "reasonCodes" | "cars" | "carsStatus" | "largeVehicles" | "largeVehiclesProven" | "largeLimit" | "carUsageWindows" | "selection" | "assignment">,
  ): ScenarioResult => {
    const flatJobs = jobs;
    const profile = routeRideProfile(profileJobs(flatJobs), matrix.arcs);
    const routes: ScenarioRoute[] = [];
    const minutesByType: Record<string, number> = {};
    const rides: number[] = [];
    let k = 0;
    for (const job of flatJobs) {
      for (const [index, interval] of job.intervals.entries()) {
        const assigned = typeOf(interval);
        const source = job.result.routes[index]!;
        const routeProfile = profile[k++]!;
        minutesByType[assigned.vehicleType] = (minutesByType[assigned.vehicleType] ?? 0) + routeProfile.routeMinutes;
        rides.push(...routeProfile.rides);
        routes.push({
          jobId: interval.jobId, routeIndex: interval.routeIndex, direction: interval.direction,
          anchorMinutes: job.anchorMinutes, startMinutes: interval.startMinutes, endMinutes: interval.endMinutes,
          minutes: round6(routeProfile.routeMinutes), swCount: interval.swCount, soCount: interval.soCount,
          vehicleType: assigned.vehicleType, physicalVehicleId: assigned.physicalVehicleId,
          selectionLabel: labelOf(interval), occurrenceIds: interval.occurrenceIds,
          steps: source.route_details.map((step) => ({ location1: step.location1, location2: step.location2, duration: step.duration })),
        });
      }
    }
    const rounded = Object.fromEntries(Object.entries(minutesByType).map(([id, value]) => [id, round6(value)]));
    const carId = minimiseType?.typeId ?? null;
    return {
      scenario, ...extra, routes,
      largeRoutes: routes.filter((route) => route.vehicleType === fixedType.typeId).length,
      carRoutes: routes.filter((route) => carId !== null && route.vehicleType === carId).length,
      minutesByType: rounded,
      totalVehicleMinutes: round6(Object.values(minutesByType).reduce((sum, value) => sum + value, 0)),
      ride: rideStatistics(rides),
    };
  };
  const failedScenario = (
    scenario: ScenarioKey, status: ScenarioStatus, reasonCodes: readonly string[],
    selection: ScenarioResult["selection"], assignment: ScenarioResult["assignment"] = null,
  ): ScenarioResult => ({
    scenario, largeLimit: scenario === "A" ? null : scenario, status, reasonCodes, cars: null, carsStatus: null,
    largeVehicles: null, largeVehiclesProven: null, routes: [], largeRoutes: 0, carRoutes: 0, minutesByType: {},
    totalVehicleMinutes: null, ride: null, carUsageWindows: [], selection, assignment,
  });

  // Scenario A: the existing single-type path (assignPhysicalVehicles through buildDudulluPreview).
  const baselineVerified = baselinePreview.jobs;
  const scenarioA = (): ScenarioResult => {
    const summary = baselinePreview.vehicleSummary;
    const byKey = new Map(baselinePreview.assignments.map((item) => [`${item.jobId}#${item.routeIndex}`, item]));
    const minimum = summary?.minimumVehicles ?? null;
    const result = buildResult(
      "A", baselineVerified,
      (interval) => ({
        vehicleType: fixedType.typeId,
        physicalVehicleId: byKey.get(`${interval.jobId}#${interval.routeIndex}`)?.physicalVehicleId ?? "",
      }),
      () => null,
      {
        status: baselinePreview.status === "preview_ready" ? "ok" : "indeterminate",
        reasonCodes: baselinePreview.reasonCodes, cars: 0, carsStatus: null, largeVehicles: minimum,
        largeVehiclesProven: summary?.minimumProven ?? false, largeLimit: minimum, carUsageWindows: [],
        selection: null, assignment: null,
      },
    );
    return result;
  };

  // ---- menu (only when a fixed-L scenario is requested) -----------------------------------
  const menu: WaveMenu[] = [];
  let menuRecords: MenuWaveRecord[] = [];
  const maxL = integerScenarios.length ? Math.max(...integerScenarios) : -1;
  if (integerScenarios.length > 0 && minimiseType !== null) {
    const maxCaps = {
      swCapacity: Math.max(fixedType.swCapacity, minimiseType.swCapacity),
      soCapacity: Math.max(fixedType.soCapacity, minimiseType.soCapacity), cooldownMinutes: 0,
    };
    for (const [waveIndex, group] of groups.entries()) {
      const baseJob = baselineJobs[waveIndex]!;
      const record: MenuOptionRecord[] = [];
      const entry: WaveMenu = { waveId: baseJob.id, group, job: baseJob, options: [], record };
      const seen = new Set<string>();
      const baseVerified = baselineVerified[waveIndex]!;
      entry.options.push({ optionId: "base", baseline: true, verified: baseVerified });
      seen.add(signature(baseVerified));
      record.push({ optionId: "base", kind: "baseline", quota: null, status: "included", routes: baseVerified.intervals.length, reason: null });
      for (let q = 0; q <= Math.min(maxL, group.length, MENU_MAX_QUOTA); q++) {
        const optionId = `q${q}`;
        const skip = (status: MenuOptionRecord["status"], reason: string, routes: number | null = null) =>
          record.push({ optionId, kind: "quota", quota: q, status, routes, reason });
        const specs = [fixedType, minimiseType].map((type) => ({
          type_id: type.typeId, sw_capacity: type.swCapacity, so_capacity: type.soCapacity,
          ...(type.rideLimit === undefined ? {} : { max_ride_time: type.rideLimit }),
          ...(type.tourLimit === undefined ? {} : { max_travel_time: type.tourLimit }),
          ...(type === fixedType ? { max_routes: q } : {}),
        }));
        const reply = await optimize({
          algorithm: "ga_split_hf", ...waveBase(group),
          max_travel_time: maxTourMinutes, max_ride_time: maxRideTimeMinutes,
          vehicle_types: specs, minimize_type: minimiseType.typeId,
        });
        if ("error" in reply) { skip(reply.error.startsWith("http_") ? "skipped_http_error" : "skipped_invalid", reply.error); continue; }
        if (!reply.result.success) { skip("skipped_infeasible", "optimizer reported no feasible typed split"); continue; }
        const job = makeJob(group, reply.result);
        const verified = buildDudulluPreview({
          serviceDate, demands: group, vehicles: buildVirtualFleet(maxCaps, group.length), matrix, jobs: [job],
        });
        if (verified.status === "blocked_data" || verified.jobs.length !== 1) {
          skip("skipped_invalid", verified.reasonCodes.join("|") || "verification failed");
          continue;
        }
        const option = verified.jobs[0]!;
        const sig = signature(option);
        if (seen.has(sig)) { skip("skipped_duplicate", "same route partition as an earlier option", option.intervals.length); continue; }
        seen.add(sig);
        entry.options.push({ optionId, baseline: false, verified: option });
        record.push({ optionId, kind: "quota", quota: q, status: "included", routes: option.intervals.length, reason: null });
      }
      menu.push(entry);
    }
    menuRecords = menu.map((entry) => ({
      waveId: entry.waveId, direction: entry.group[0]!.direction, anchorMinutes: entry.group[0]!.anchorMinutes,
      legs: entry.group.length, options: entry.record,
    }));
  }

  const types = (count: number): TypedFleetType[] => [
    { typeId: fixedType.typeId, swCapacity: fixedType.swCapacity, soCapacity: fixedType.soCapacity,
      cooldownMinutes: fixedType.cooldownMinutes, role: "fixed", count, idPrefix: "L" },
    { typeId: minimiseType!.typeId, swCapacity: minimiseType!.swCapacity, soCapacity: minimiseType!.soCapacity,
      cooldownMinutes: minimiseType!.cooldownMinutes, role: "minimise", idPrefix: "C",
      ...(params.maxCars === null || params.maxCars === undefined ? {} : { maxCount: params.maxCars }) },
  ];

  const scenarioL = async (limit: number): Promise<ScenarioResult> => {
    const toInt = (value: number, how: "floor" | "ceil") => Math.max(0, how === "floor" ? Math.floor(value) : Math.ceil(value));
    const request = {
      waves: menu.map((entry) => ({
        wave_id: entry.waveId,
        options: entry.options.map((option) => ({
          option_id: option.optionId, baseline: option.baseline,
          routes: factsOf(option.verified).map((facts) => {
            const start = toInt(facts.interval.startMinutes, "floor");
            return {
              start, end: Math.max(start + 1, toInt(facts.interval.endMinutes, "ceil")),
              minutes: round6(facts.minutes),
              large_ok: typeAccepts(fixedType, facts, params), car_ok: typeAccepts(minimiseType!, facts, params),
            };
          }),
        })),
      })),
      max_large: limit,
      ...(params.maxCars === null || params.maxCars === undefined ? {} : { max_cars: params.maxCars }),
      cooldown_large: fixedType.cooldownMinutes, cooldown_car: minimiseType!.cooldownMinutes,
      time_limit_seconds: params.selectionTimeLimitSeconds ?? 30,
    };
    const reply = await postJson("/api/v1/internal/fleet-selection", request);
    const parsed = reply?.json === null || reply === null ? null : selectionResponseSchema.safeParse(reply.json);
    if (!parsed?.success) {
      return failedScenario(limit, "selection_unavailable", [reply === null ? "SELECTION_TRANSPORT_ERROR" : `SELECTION_HTTP_${reply.status}`], null);
    }
    const sel = parsed.data;
    const optionByWave = Object.fromEntries(Object.entries(sel.selection).map(([wave, item]) => [wave, item.option_id]));
    const selectionInfo: NonNullable<ScenarioResult["selection"]> = {
      status: sel.status, cars: sel.cars, carMinutes: sel.car_minutes,
      claim: (sel.diagnostics as { claim?: unknown } | null)?.claim ?? null,
      optionByWave, diagnostics: sel.diagnostics, stats: sel.stats,
    };
    if (sel.status === "infeasible_for_L") {
      const reason = (sel.diagnostics as { reason?: string } | null)?.reason ?? "INFEASIBLE_FOR_L";
      return failedScenario(limit, "infeasible_for_L", [reason], selectionInfo);
    }
    if (sel.status === "infeasible_data") return failedScenario(limit, "blocked_data", ["SELECTION_DATA_INFEASIBLE"], selectionInfo);
    if (sel.status === "indeterminate") return failedScenario(limit, "indeterminate", ["SELECTION_INDETERMINATE"], selectionInfo);

    const chosen: VerifiedPreviewJob[] = [];
    const labels = new Map<string, "large" | "car">();
    for (const entry of menu) {
      const pick = sel.selection[entry.waveId];
      const option = entry.options.find((candidate) => candidate.optionId === pick?.option_id);
      if (!pick || !option || pick.labels.length !== option.verified.intervals.length) {
        return failedScenario(limit, "verification_failed", ["SELECTION_RESPONSE_MISMATCH"], selectionInfo);
      }
      chosen.push(option.verified);
      option.verified.intervals.forEach((interval, index) => labels.set(`${interval.jobId}#${interval.routeIndex}`, pick.labels[index]!));
    }
    const intervals = chosen.flatMap((job) => job.intervals);
    const fleet = types(limit);
    const assignment = assignTypedVehicles({ intervals, types: fleet, ...(params.nodeBudget === undefined ? {} : { nodeBudget: params.nodeBudget }) });
    const assignmentInfo = (problems: readonly string[]): NonNullable<ScenarioResult["assignment"]> => ({
      status: assignment.status, reasonCodes: assignment.reasonCodes, nodes: assignment.nodes,
      lowerBoundsByType: assignment.lowerBoundsByType, problems,
    });
    if (assignment.status === "infeasible_for_L") {
      // The independent verifier does not confirm the selection's feasibility: report, never trust CP alone.
      return failedScenario(limit, "verification_failed", ["ASSIGNMENT_DISAGREES_WITH_SELECTION", ...assignment.reasonCodes], selectionInfo, assignmentInfo([]));
    }
    if (assignment.status === "blocked_data" || assignment.status === "indeterminate" || assignment.minimumCount === null) {
      return failedScenario(limit, assignment.status === "indeterminate" ? "indeterminate" : "blocked_data",
        assignment.reasonCodes.length ? assignment.reasonCodes : ["ASSIGNMENT_INDETERMINATE"], selectionInfo, assignmentInfo([]));
    }
    const problems = verifyTypedAssignment(assignment.assignments, fleet);
    const factsByKey = new Map(chosen.flatMap((job) => factsOf(job).map((facts) => [`${facts.interval.jobId}#${facts.interval.routeIndex}`, facts] as const)));
    for (const item of assignment.assignments) {
      const type = item.vehicleType === fixedType.typeId ? fixedType : minimiseType!;
      const facts = factsByKey.get(`${item.jobId}#${item.routeIndex}`);
      if (!facts || !typeAccepts(type, facts, params)) problems.push(`route ${item.jobId}#${item.routeIndex} violates ${type.typeId} limits`);
    }
    if (problems.length > 0) {
      return failedScenario(limit, "verification_failed", ["TYPED_ASSIGNMENT_VERIFICATION_FAILED"], selectionInfo, assignmentInfo(problems));
    }
    const byKey = new Map<string, TypedAssignment>(assignment.assignments.map((item) => [`${item.jobId}#${item.routeIndex}`, item]));
    const carsStatus: CarsStatus = sel.status === "optimal" && assignment.status === "proven"
      ? "proven_over_menu" : "witness";
    return buildResult(
      limit, chosen,
      (interval) => {
        const item = byKey.get(`${interval.jobId}#${interval.routeIndex}`)!;
        return { vehicleType: item.vehicleType, physicalVehicleId: item.physicalVehicleId };
      },
      (interval) => labels.get(`${interval.jobId}#${interval.routeIndex}`) ?? null,
      {
        status: "ok", reasonCodes: assignment.reasonCodes, cars: assignment.minimumCount, carsStatus,
        largeVehicles: assignment.countsByType[fixedType.typeId] ?? 0, largeVehiclesProven: null, largeLimit: limit,
        carUsageWindows: windowsFromAssignment(assignment), selection: selectionInfo, assignment: assignmentInfo([]),
      },
    );
  };

  for (const scenario of params.scenarios) {
    scenarioResults.push(scenario === "A" ? scenarioA() : await scenarioL(scenario));
  }
  return {
    ...dayBase, status: "ready", reasonCodes: [...new Set([...state.extraReasons])] as PreviewReasonCode[],
    students, legs: admitted.length, waves: groups.length,
    occurrenceLabels: state.occurrenceLabels, matrix, menu: menuRecords, scenarios: scenarioResults,
  };
}

/** Plain JSON for one scenario (anonymised by the CLI before it is written). */
export function scenarioResponse(day: FleetScenarioDay, scenario: ScenarioResult) {
  return {
    serviceDate: day.serviceDate, dayStatus: day.status, limits: day.limits,
    dbVehiclesConsulted: day.dbVehiclesConsulted,
    matrix: day.matrix ? { id: day.matrix.id, version: day.matrix.version, sha256: day.matrix.sha256, source: day.matrix.source } : null,
    scenario, occurrenceLabels: day.occurrenceLabels, menu: day.menu,
  };
}
