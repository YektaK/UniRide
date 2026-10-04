import type { DailyTripDemand, TripDirection } from "./daily-planning";
import { DUDULLU_CAMPUS } from "./dudullu-campus";

const DEPOT_CODE = DUDULLU_CAMPUS.code;
const SERVICE_DAY_END_MINUTES = 24 * 60;
const ASSIGNMENT_SEARCH_NODE_BUDGET = 50_000;
const ADMITTED = new Set(["confirmed", "approved"]);

export interface MatrixArc {
  readonly origin_code: string;
  readonly destination_code: string;
  readonly duration_minutes: number;
}

export interface MatrixSnapshot {
  readonly id: string;
  readonly version: string;
  readonly sha256: string;
  readonly source: string;
  readonly arcs: readonly MatrixArc[];
}

export type PreviewDemand = DailyTripDemand & {
  readonly disabilityType: "Sw" | "So";
};

export interface PreviewRouteStep {
  readonly location1: string;
  readonly location2: string;
  readonly duration: number;
  readonly distance: number;
}

export interface PreviewRoute {
  readonly vehicle_id: string;
  readonly route_details: readonly PreviewRouteStep[];
  readonly total_duration_minutes: number;
  readonly total_distance_km?: number;
  readonly sw_count: number;
  readonly so_count: number;
  readonly student_ids: readonly string[];
}

export interface PreviewOptimizationResult {
  readonly success: boolean;
  readonly routes: readonly PreviewRoute[];
  readonly total_duration_minutes?: number;
  readonly feasibility_certificate?: unknown;
}

export interface PreviewVehicle {
  readonly vehicleId: string;
  readonly swCapacity: number;
  readonly soCapacity: number;
  readonly cooldownMinutes?: number;
}

export interface PreviewAssignment extends PreviewRouteInterval {
  readonly physicalVehicleId: string;
}

export interface PreviewJobInput {
  readonly id: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly anchorMinutes: number;
  readonly demands: readonly PreviewDemand[];
  readonly nodeToLocation: ReadonlyMap<string, string>;
  readonly nodeToOccurrence: ReadonlyMap<string, string>;
  readonly result: PreviewOptimizationResult;
}

export type PreviewReasonCode =
  | "ASSIGNMENT_SEARCH_INDETERMINATE"
  | "CERTIFICATE_INVALID"
  | "CLOSING_DEPOT_ARC_MISSING"
  | "DUPLICATE_MATRIX_ARC"
  | "DUPLICATE_OCCURRENCE_COVERAGE"
  | "FLEET_INVALID"
  | "FLEET_SHORTAGE"
  | "JOB_CONTRACT_MISMATCH"
  | "LEGACY_AMBIGUOUS_CONFIRMATION"
  | "MATRIX_ARC_MISMATCH"
  | "MATRIX_SNAPSHOT_INVALID"
  | "MATRIX_UNAVAILABLE"
  | "MISSING_OCCURRENCE_COVERAGE"
  | "NO_ADMITTED_DEMAND"
  | "NO_ROUTE_STEPS"
  | "OPTIMIZATION_NOT_SUCCESSFUL"
  | "PENDING_STUDENT_CONFIRMATION"
  | "ROUTE_OUTSIDE_SERVICE_DAY"
  | "ROUTE_LOAD_MISMATCH"
  | "ROUTE_TOTAL_MISMATCH"
  | "SCHEDULE_DATA_INVALID"
  | "UNKNOWN_OCCURRENCE"
  | "UNKNOWN_ROUTE_NODE";

export interface PreviewRouteInterval {
  readonly jobId: string;
  readonly routeIndex: number;
  readonly vehicleId: string;
  readonly direction: TripDirection;
  readonly startMinutes: number;
  readonly endMinutes: number;
  readonly occurrenceIds: readonly string[];
  readonly swCount: number;
  readonly soCount: number;
}

export interface VerifiedPreviewJob {
  readonly id: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly anchorMinutes: number;
  readonly result: PreviewOptimizationResult;
  readonly intervals: readonly PreviewRouteInterval[];
}

export interface HourlyDemandSummary {
  readonly pickup: { Sw: number; So: number };
  readonly dropoff: { Sw: number; So: number };
}

export interface PreviewJobRouteCount {
  readonly jobId: string;
  readonly direction: TripDirection;
  readonly anchorMinutes: number;
  readonly routeCount: number;
  readonly studentCount: number;
}

/**
 * Fleet summary for the solver's fixed routes. `minimumProven` only says that the
 * physical-vehicle assignment is minimal for these routes. It is not a claim about
 * the global minimum number of vehicles, because the route count itself is the
 * solver's choice and is not proven minimal.
 */
export interface PreviewVehicleSummary {
  /** Distinct physical vehicles in the best assignment found; null when none was found. */
  readonly minimumVehicles: number | null;
  /** True only when the search finished (or met the lower bound) with an assignment. */
  readonly minimumProven: boolean;
  /** Peak number of routes that must run on different vehicles, cooldown included. */
  readonly lowerBound: number;
  /** Peak number of simultaneously running routes, without cooldown. */
  readonly peakConcurrentRoutes: number;
  readonly activeFleetSize: number;
  readonly routesPerJob: readonly PreviewJobRouteCount[];
}

export interface DudulluPreviewResult {
  readonly status: "preview_ready" | "shortage" | "blocked_data" | "indeterminate";
  readonly publishable: false;
  readonly serviceDate: string;
  readonly matrix: Omit<MatrixSnapshot, "arcs"> | null;
  readonly hourlyDemand: Readonly<Record<string, HourlyDemandSummary>>;
  readonly jobs: readonly VerifiedPreviewJob[];
  readonly routeIntervals: readonly PreviewRouteInterval[];
  readonly assignments: readonly PreviewAssignment[];
  readonly hourlyOccupiedVehicles: Readonly<Record<string, number>>;
  readonly unassignedOccurrenceIds: readonly string[];
  readonly reasonCodes: readonly PreviewReasonCode[];
  /** Null when the preview is blocked before a fleet assignment is attempted. */
  readonly vehicleSummary: PreviewVehicleSummary | null;
}

export interface BuildDudulluPreviewInput {
  readonly serviceDate: string;
  readonly demands: readonly PreviewDemand[];
  readonly vehicles: readonly PreviewVehicle[];
  readonly matrix: MatrixSnapshot | null | undefined;
  readonly jobs: readonly PreviewJobInput[];
  /** Overrides the assignment search node budget; intended for tests. */
  readonly assignmentSearchNodeBudget?: number;
}

class PreviewValidationError extends Error {
  constructor(readonly code: PreviewReasonCode) {
    super(code);
  }
}

function fail(code: PreviewReasonCode): never {
  throw new PreviewValidationError(code);
}

function roundToTwo(value: number): number {
  return Math.round(value * 100) / 100;
}

function hasFeasibleCertificate(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "is_feasible" in value &&
    (value as { is_feasible?: unknown }).is_feasible === true
  );
}

function matrixMetadata(matrix: MatrixSnapshot | null | undefined): Omit<MatrixSnapshot, "arcs"> | null {
  if (!matrix) return null;
  const { arcs: _arcs, ...metadata } = matrix;
  return metadata;
}

function makeBlockedResult(
  serviceDate: string,
  matrix: MatrixSnapshot | null | undefined,
  reasonCodes: readonly PreviewReasonCode[],
  hourlyDemand: Readonly<Record<string, HourlyDemandSummary>> = {},
  unassignedOccurrenceIds: readonly string[] = [],
): DudulluPreviewResult {
  return {
    status: "blocked_data",
    publishable: false,
    serviceDate,
    matrix: matrixMetadata(matrix),
    hourlyDemand,
    jobs: [],
    routeIntervals: [],
    assignments: [],
    hourlyOccupiedVehicles: {},
    unassignedOccurrenceIds,
    reasonCodes: [...new Set(reasonCodes)],
    vehicleSummary: null,
  };
}

function buildArcMap(matrix: MatrixSnapshot | null | undefined): ReadonlyMap<string, number> {
  if (!matrix || matrix.source !== "supabase" || !Array.isArray(matrix.arcs) || matrix.arcs.length === 0) {
    fail("MATRIX_UNAVAILABLE");
  }

  const arcs = new Map<string, number>();
  for (const arc of matrix.arcs) {
    if (
      typeof arc.origin_code !== "string" ||
      typeof arc.destination_code !== "string" ||
      !Number.isFinite(arc.duration_minutes) ||
      arc.duration_minutes < 0
    ) {
      fail("MATRIX_SNAPSHOT_INVALID");
    }

    const key = JSON.stringify([arc.origin_code, arc.destination_code]);
    const previous = arcs.get(key);
    if (previous !== undefined && previous !== arc.duration_minutes) {
      fail("DUPLICATE_MATRIX_ARC");
    }
    arcs.set(key, arc.duration_minutes);
  }
  return arcs;
}

export function verifiedArcMinutes(
  step: Pick<PreviewRouteStep, "location1" | "location2" | "duration">,
  nodeToLocation: ReadonlyMap<string, string>,
  arcByPair: ReadonlyMap<string, number>,
): number {
  const from = nodeToLocation.get(step.location1);
  const to = nodeToLocation.get(step.location2);
  if (from === undefined || to === undefined) fail("UNKNOWN_ROUTE_NODE");

  if (from === to) {
    if (
      from === DEPOT_CODE ||
      step.location1 === step.location2 ||
      !Number.isFinite(step.duration) ||
      Math.abs(step.duration) > 0.005000001
    ) {
      fail("MATRIX_ARC_MISMATCH");
    }
    return 0;
  }

  const source = arcByPair.get(JSON.stringify([from, to]));
  if (
    source === undefined ||
    !Number.isFinite(source) ||
    source <= 0 ||
    !Number.isFinite(step.duration) ||
    Math.abs(step.duration - source) > 0.005000001
  ) {
    fail("MATRIX_ARC_MISMATCH");
  }
  return source;
}

function hourlyDemand(demands: readonly PreviewDemand[]): Readonly<Record<string, HourlyDemandSummary>> {
  const output: Record<string, HourlyDemandSummary> = {};
  for (const demand of demands) {
    const hour = `${String(Math.floor(demand.classBoundaryMinutes / 60)).padStart(2, "0")}:00`;
    const current = output[hour] ?? {
      pickup: { Sw: 0, So: 0 },
      dropoff: { Sw: 0, So: 0 },
    };
    current[demand.direction][demand.disabilityType] += 1;
    output[hour] = current;
  }
  return output;
}

function validateRoute(
  job: PreviewJobInput,
  route: PreviewRoute,
  routeIndex: number,
  arcByPair: ReadonlyMap<string, number>,
  jobOccurrenceIds: ReadonlySet<string>,
): PreviewRouteInterval {
  const steps = route.route_details;
  if (!Array.isArray(steps) || steps.length === 0) fail("NO_ROUTE_STEPS");
  if (!Array.isArray(route.student_ids)) fail("MISSING_OCCURRENCE_COVERAGE");

  const firstOrigin = job.nodeToLocation.get(steps[0].location1);
  const lastDestination = job.nodeToLocation.get(steps[steps.length - 1].location2);
  if (firstOrigin === undefined || lastDestination === undefined) fail("UNKNOWN_ROUTE_NODE");
  if (firstOrigin !== DEPOT_CODE || lastDestination !== DEPOT_CODE) {
    fail("CLOSING_DEPOT_ARC_MISSING");
  }

  let sourceTotal = 0;
  const internalOccurrences = new Set<string>();
  for (let index = 0; index < steps.length; index += 1) {
    const step = steps[index];
    if (index > 0 && steps[index - 1].location2 !== step.location1) {
      fail("CLOSING_DEPOT_ARC_MISSING");
    }
    const fromLocation = job.nodeToLocation.get(step.location1);
    const toLocation = job.nodeToLocation.get(step.location2);
    if (index < steps.length - 1 && toLocation === DEPOT_CODE) {
      fail("CLOSING_DEPOT_ARC_MISSING");
    }
    if (fromLocation === toLocation && fromLocation !== DEPOT_CODE) {
      const fromOccurrence = job.nodeToOccurrence.get(step.location1);
      const toOccurrence = job.nodeToOccurrence.get(step.location2);
      if (fromOccurrence === undefined || toOccurrence === undefined) fail("UNKNOWN_ROUTE_NODE");
      if (fromOccurrence === toOccurrence) fail("MATRIX_ARC_MISMATCH");
    }
    sourceTotal += verifiedArcMinutes(step, job.nodeToLocation, arcByPair);

    for (const node of [step.location1, step.location2]) {
      if (job.nodeToLocation.get(node) === DEPOT_CODE) continue;
      const occurrenceId = job.nodeToOccurrence.get(node);
      if (occurrenceId === undefined) fail("UNKNOWN_ROUTE_NODE");
      if (!jobOccurrenceIds.has(occurrenceId)) fail("UNKNOWN_OCCURRENCE");
      if (node === step.location2 && internalOccurrences.has(occurrenceId)) {
        fail("DUPLICATE_OCCURRENCE_COVERAGE");
      }
      internalOccurrences.add(occurrenceId);
    }
  }

  if (
    !Number.isFinite(route.total_duration_minutes) ||
    Math.abs(roundToTwo(route.total_duration_minutes) - roundToTwo(sourceTotal)) > 0.000001
  ) {
    fail("ROUTE_TOTAL_MISMATCH");
  }

  const listedOccurrences = [...route.student_ids];
  if (new Set(listedOccurrences).size !== listedOccurrences.length) {
    fail("DUPLICATE_OCCURRENCE_COVERAGE");
  }
  for (const occurrenceId of listedOccurrences) {
    if (!jobOccurrenceIds.has(occurrenceId)) fail("UNKNOWN_OCCURRENCE");
  }
  const expectedLoad = { Sw: 0, So: 0 };
  for (const occurrenceId of listedOccurrences) {
    const demand = job.demands.find((item) => item.occurrenceId === occurrenceId);
    if (!demand || !(demand.disabilityType in expectedLoad)) fail("ROUTE_LOAD_MISMATCH");
    expectedLoad[demand.disabilityType] += 1;
  }
  if (
    !Number.isInteger(route.sw_count) ||
    !Number.isInteger(route.so_count) ||
    route.sw_count < 0 ||
    route.so_count < 0 ||
    route.sw_count !== expectedLoad.Sw ||
    route.so_count !== expectedLoad.So
  ) {
    fail("ROUTE_LOAD_MISMATCH");
  }
  if (
    listedOccurrences.length !== internalOccurrences.size ||
    listedOccurrences.some((occurrenceId) => !internalOccurrences.has(occurrenceId))
  ) {
    fail("MISSING_OCCURRENCE_COVERAGE");
  }

  const startMinutes = job.direction === "pickup"
    ? job.anchorMinutes - sourceTotal
    : job.anchorMinutes;
  const endMinutes = job.direction === "pickup"
    ? job.anchorMinutes
    : job.anchorMinutes + sourceTotal;
  if (
    !Number.isFinite(startMinutes) ||
    !Number.isFinite(endMinutes) ||
    startMinutes < 0 ||
    endMinutes > SERVICE_DAY_END_MINUTES
  ) {
    fail("ROUTE_OUTSIDE_SERVICE_DAY");
  }

  return {
    jobId: job.id,
    routeIndex,
    vehicleId: route.vehicle_id,
    direction: job.direction,
    startMinutes,
    endMinutes,
    occurrenceIds: listedOccurrences,
    swCount: route.sw_count,
    soCount: route.so_count,
  };
}

function validateJob(
  job: PreviewJobInput,
  serviceDate: string,
  admittedIds: ReadonlySet<string>,
  arcByPair: ReadonlyMap<string, number>,
): VerifiedPreviewJob {
  if (
    job.serviceDate !== serviceDate ||
    !Number.isFinite(job.anchorMinutes) ||
    job.anchorMinutes < 0 ||
    job.anchorMinutes > SERVICE_DAY_END_MINUTES ||
    job.demands.length === 0
  ) {
    fail("JOB_CONTRACT_MISMATCH");
  }

  const jobOccurrenceIds = new Set<string>();
  for (const demand of job.demands) {
    if (!admittedIds.has(demand.occurrenceId)) fail("UNKNOWN_OCCURRENCE");
    if (jobOccurrenceIds.has(demand.occurrenceId)) fail("DUPLICATE_OCCURRENCE_COVERAGE");
    if (
      demand.serviceDate !== serviceDate ||
      demand.direction !== job.direction ||
      demand.anchorMinutes !== job.anchorMinutes ||
      (job.direction === "pickup" && demand.hardDeadlineMinutes !== job.anchorMinutes) ||
      (job.direction === "dropoff" && demand.hardReadyMinutes !== job.anchorMinutes)
    ) {
      fail("JOB_CONTRACT_MISMATCH");
    }
    jobOccurrenceIds.add(demand.occurrenceId);
  }

  if (!job.result.success) fail("OPTIMIZATION_NOT_SUCCESSFUL");
  if (!hasFeasibleCertificate(job.result.feasibility_certificate)) fail("CERTIFICATE_INVALID");

  const intervals: PreviewRouteInterval[] = [];
  const covered = new Set<string>();
  for (const [routeIndex, route] of job.result.routes.entries()) {
    const interval = validateRoute(job, route, routeIndex, arcByPair, jobOccurrenceIds);
    for (const occurrenceId of interval.occurrenceIds) {
      if (covered.has(occurrenceId)) fail("DUPLICATE_OCCURRENCE_COVERAGE");
      covered.add(occurrenceId);
    }
    intervals.push(interval);
  }

  const resultTotal = job.result.total_duration_minutes;
  if (resultTotal !== undefined && (
    !Number.isFinite(resultTotal) ||
    Math.abs(roundToTwo(resultTotal) - roundToTwo(job.result.routes.reduce(
      (sum, route) => sum + route.total_duration_minutes, 0,
    ))) > 0.000001
  )) fail("ROUTE_TOTAL_MISMATCH");

  if (covered.size !== jobOccurrenceIds.size) fail("MISSING_OCCURRENCE_COVERAGE");
  return {
    id: job.id,
    serviceDate: job.serviceDate,
    direction: job.direction,
    anchorMinutes: job.anchorMinutes,
    result: job.result,
    intervals,
  };
}

interface NormalizedPreviewVehicle extends PreviewVehicle {
  readonly cooldownMinutes: number;
}

interface FleetAssignmentResult {
  readonly status: "preview_ready" | "shortage" | "blocked_data" | "indeterminate";
  readonly assignments: readonly PreviewAssignment[];
  readonly hourlyOccupiedVehicles: Readonly<Record<string, number>>;
  readonly unassignedOccurrenceIds: readonly string[];
  readonly reasonCodes: readonly PreviewReasonCode[];
  readonly minimumVehicles: number | null;
  readonly minimumProven: boolean;
  readonly lowerBound: number;
  readonly peakConcurrentRoutes: number;
  readonly activeFleetSize: number;
}

function normalizeVehicles(vehicles: readonly PreviewVehicle[]): NormalizedPreviewVehicle[] | null {
  const seen = new Set<string>();
  const normalized: NormalizedPreviewVehicle[] = [];
  for (const vehicle of vehicles) {
    const cooldownMinutes = vehicle.cooldownMinutes ?? 0;
    if (
      typeof vehicle.vehicleId !== "string" ||
      vehicle.vehicleId.length === 0 ||
      seen.has(vehicle.vehicleId) ||
      !Number.isFinite(vehicle.swCapacity) ||
      !Number.isFinite(vehicle.soCapacity) ||
      !Number.isFinite(cooldownMinutes) ||
      vehicle.swCapacity < 0 ||
      vehicle.soCapacity < 0 ||
      cooldownMinutes < 0
    ) {
      return null;
    }
    seen.add(vehicle.vehicleId);
    normalized.push({ ...vehicle, cooldownMinutes });
  }
  return normalized.sort((left, right) => left.vehicleId < right.vehicleId ? -1 : 1);
}

function canAssign(
  vehicle: NormalizedPreviewVehicle,
  route: PreviewRouteInterval,
  assigned: readonly PreviewRouteInterval[],
): boolean {
  return route.swCount <= vehicle.swCapacity &&
    route.soCount <= vehicle.soCapacity &&
    assigned.every((other) =>
      other.endMinutes + vehicle.cooldownMinutes <= route.startMinutes ||
      route.endMinutes + vehicle.cooldownMinutes <= other.startMinutes
    );
}

function hourlyOccupiedVehicles(assignments: readonly PreviewAssignment[]): Readonly<Record<string, number>> {
  const occupied: Record<string, Set<string>> = {};
  for (const assignment of assignments) {
    const firstHour = Math.floor(assignment.startMinutes / 60);
    const lastHour = Math.floor(Math.max(assignment.startMinutes, assignment.endMinutes - 0.000000001) / 60);
    for (let hour = firstHour; hour <= lastHour; hour += 1) {
      const key = `${String(hour).padStart(2, "0")}:00`;
      (occupied[key] ??= new Set()).add(assignment.physicalVehicleId);
    }
  }
  return Object.fromEntries(Object.entries(occupied).map(([hour, ids]) => [hour, ids.size]));
}

function vehicleSignature(vehicle: NormalizedPreviewVehicle): string {
  return `${vehicle.swCapacity}|${vehicle.soCapacity}|${vehicle.cooldownMinutes}`;
}

interface IntervalBounds {
  /** Peak number of simultaneously running routes (no cooldown). */
  readonly peakConcurrentRoutes: number;
  /**
   * Peak number of routes that pairwise conflict on every vehicle. Each route is
   * extended by the smallest fleet cooldown, so two routes that overlap after the
   * extension cannot share any vehicle. Capped at 0 for an empty route list.
   */
  readonly lowerBound: number;
  /** True when some set of mutually conflicting routes cannot be matched to compatible vehicles. */
  readonly capacityInfeasible: boolean;
}

function maxDepthAtStarts(
  intervals: readonly PreviewRouteInterval[],
  extension: number,
): { depth: number; cliques: PreviewRouteInterval[][] } {
  let depth = 0;
  const cliques: PreviewRouteInterval[][] = [];
  const seenStarts = new Set<number>();
  for (const probe of intervals) {
    if (seenStarts.has(probe.startMinutes)) continue;
    seenStarts.add(probe.startMinutes);
    const clique = intervals.filter((item) =>
      item.startMinutes <= probe.startMinutes && probe.startMinutes < item.endMinutes + extension
    );
    if (clique.length > depth) depth = clique.length;
    cliques.push(clique);
  }
  return { depth, cliques };
}

/**
 * Can every route of a clique get its own distinct vehicle with enough Sw/So capacity?
 * Vehicles are grouped by capacity signature and capped at the clique size, which keeps
 * the augmenting-path matching small even for large (virtual) fleets.
 */
function cliqueHasCapacityMatching(
  clique: readonly PreviewRouteInterval[],
  vehicles: readonly NormalizedPreviewVehicle[],
): boolean {
  const perSignature = new Map<string, number>();
  const pool: NormalizedPreviewVehicle[] = [];
  for (const vehicle of vehicles) {
    const key = `${vehicle.swCapacity}|${vehicle.soCapacity}`;
    const count = perSignature.get(key) ?? 0;
    if (count >= clique.length) continue;
    perSignature.set(key, count + 1);
    pool.push(vehicle);
  }

  const owner = new Array<number>(pool.length).fill(-1);
  const tryRoute = (routeIndex: number, visited: boolean[]): boolean => {
    const route = clique[routeIndex];
    for (let vehicleIndex = 0; vehicleIndex < pool.length; vehicleIndex += 1) {
      const vehicle = pool[vehicleIndex];
      if (visited[vehicleIndex] || route.swCount > vehicle.swCapacity || route.soCount > vehicle.soCapacity) continue;
      visited[vehicleIndex] = true;
      if (owner[vehicleIndex] === -1 || tryRoute(owner[vehicleIndex], visited)) {
        owner[vehicleIndex] = routeIndex;
        return true;
      }
    }
    return false;
  };
  for (let routeIndex = 0; routeIndex < clique.length; routeIndex += 1) {
    if (!tryRoute(routeIndex, new Array<boolean>(pool.length).fill(false))) return false;
  }
  return true;
}

function computeIntervalBounds(
  intervals: readonly PreviewRouteInterval[],
  vehicles: readonly NormalizedPreviewVehicle[],
): IntervalBounds {
  if (intervals.length === 0) {
    return { peakConcurrentRoutes: 0, lowerBound: 0, capacityInfeasible: false };
  }
  const minimumCooldown = vehicles.reduce(
    (smallest, vehicle) => Math.min(smallest, vehicle.cooldownMinutes),
    Number.POSITIVE_INFINITY,
  );
  const extension = Number.isFinite(minimumCooldown) ? minimumCooldown : 0;
  const peak = maxDepthAtStarts(intervals, 0).depth;
  const { depth, cliques } = maxDepthAtStarts(intervals, extension);
  // A zero-length route is never "inside" any interval at its own start, but it still
  // needs one vehicle, so the bound never drops below 1.
  const lowerBound = Math.max(depth, 1);
  const capacityInfeasible = cliques.some((clique) => !cliqueHasCapacityMatching(clique, vehicles));
  return { peakConcurrentRoutes: Math.max(peak, 1), lowerBound, capacityInfeasible };
}

function assignPhysicalVehicles(
  intervals: readonly PreviewRouteInterval[],
  vehicles: readonly PreviewVehicle[],
  nodeBudget: number = ASSIGNMENT_SEARCH_NODE_BUDGET,
): FleetAssignmentResult {
  const normalizedVehicles = normalizeVehicles(vehicles);
  const allOccurrenceIds = [...new Set(intervals.flatMap((interval) => interval.occurrenceIds))];
  const noAssignment = {
    assignments: [] as PreviewAssignment[],
    hourlyOccupiedVehicles: {},
    unassignedOccurrenceIds: allOccurrenceIds,
    minimumVehicles: null,
    minimumProven: false,
  };
  if (normalizedVehicles === null) {
    return {
      ...noAssignment,
      status: "blocked_data",
      reasonCodes: ["FLEET_INVALID"],
      lowerBound: 0,
      peakConcurrentRoutes: 0,
      activeFleetSize: 0,
    };
  }
  const availableVehicles = normalizedVehicles;
  const bounds = computeIntervalBounds(intervals, availableVehicles);
  const summaryBase = {
    lowerBound: bounds.lowerBound,
    peakConcurrentRoutes: bounds.peakConcurrentRoutes,
    activeFleetSize: availableVehicles.length,
  };
  if (
    availableVehicles.length === 0 ||
    bounds.lowerBound > availableVehicles.length ||
    bounds.capacityInfeasible
  ) {
    return { ...noAssignment, ...summaryBase, status: "shortage", reasonCodes: ["FLEET_SHORTAGE"] };
  }

  const orderedIntervals = intervals
    .map((interval, originalIndex) => ({ interval, originalIndex }))
    .sort((left, right) =>
      left.interval.startMinutes - right.interval.startMinutes ||
      left.interval.endMinutes - right.interval.endMinutes ||
      (left.interval.jobId < right.interval.jobId ? -1 : left.interval.jobId > right.interval.jobId ? 1 : 0) ||
      left.interval.routeIndex - right.interval.routeIndex
    );
  const current = new Map<number, string>();
  const assignedByVehicle = new Map<string, PreviewRouteInterval[]>();
  let best: Map<number, string> | null = null;
  let bestVehicleCount = Number.POSITIVE_INFINITY;
  let nodes = 0;
  let exhausted = false;
  let reachedLowerBound = false;

  // Routes are visited in start order, so a vehicle matters for the remaining routes
  // only through the time it becomes free again. Vehicles with the same capacity,
  // cooldown and free time are interchangeable, and so are all unused vehicles of one
  // signature. Trying one of each removes the permutation blow-up of identical fleets.
  function candidateVehicles(interval: PreviewRouteInterval): NormalizedPreviewVehicle[] {
    const used: NormalizedPreviewVehicle[] = [];
    const unused: NormalizedPreviewVehicle[] = [];
    const seen = new Set<string>();
    for (const vehicle of availableVehicles) {
      const assigned = assignedByVehicle.get(vehicle.vehicleId);
      if (assigned === undefined) {
        const key = vehicleSignature(vehicle);
        if (seen.has(`new|${key}`)) continue;
        seen.add(`new|${key}`);
        unused.push(vehicle);
        continue;
      }
      const freeAt = Math.max(
        Math.max(...assigned.map((item) => item.endMinutes)) + vehicle.cooldownMinutes,
        interval.startMinutes,
      );
      const key = `${vehicleSignature(vehicle)}|${freeAt}`;
      if (seen.has(`used|${key}`)) continue;
      seen.add(`used|${key}`);
      used.push(vehicle);
    }
    return [...used, ...unused];
  }

  function search(index: number): void {
    if (exhausted || reachedLowerBound || assignedByVehicle.size >= bestVehicleCount) return;
    if (nodes >= nodeBudget) {
      exhausted = true;
      return;
    }
    nodes += 1;
    if (index === orderedIntervals.length) {
      best = new Map(current);
      bestVehicleCount = new Set(current.values()).size;
      if (bestVehicleCount <= bounds.lowerBound) reachedLowerBound = true;
      return;
    }

    const { interval, originalIndex } = orderedIntervals[index];
    for (const vehicle of candidateVehicles(interval)) {
      const assigned = assignedByVehicle.get(vehicle.vehicleId) ?? [];
      if (!canAssign(vehicle, interval, assigned)) continue;
      current.set(originalIndex, vehicle.vehicleId);
      assignedByVehicle.set(vehicle.vehicleId, [...assigned, interval]);
      search(index + 1);
      current.delete(originalIndex);
      if (assigned.length === 0) assignedByVehicle.delete(vehicle.vehicleId);
      else assignedByVehicle.set(vehicle.vehicleId, assigned);
      if (exhausted || reachedLowerBound) return;
    }
  }

  search(0);
  const assignments = best === null
    ? []
    : intervals.map((interval, originalIndex) => ({
      ...interval,
      physicalVehicleId: best?.get(originalIndex) ?? "",
    }));
  const assignedOccurrenceIds = new Set(assignments.flatMap((assignment) => assignment.occurrenceIds));
  const unassignedOccurrenceIds = allOccurrenceIds.filter((occurrenceId) => !assignedOccurrenceIds.has(occurrenceId));
  const status = exhausted ? "indeterminate" : best === null ? "shortage" : "preview_ready";
  return {
    status,
    assignments,
    hourlyOccupiedVehicles: hourlyOccupiedVehicles(assignments),
    unassignedOccurrenceIds,
    reasonCodes: status === "preview_ready"
      ? []
      : [status === "shortage" ? "FLEET_SHORTAGE" : "ASSIGNMENT_SEARCH_INDETERMINATE"],
    ...summaryBase,
    minimumVehicles: best === null ? null : bestVehicleCount,
    minimumProven: status === "preview_ready",
  };
}

export function buildDudulluPreview(input: BuildDudulluPreviewInput): DudulluPreviewResult {
  const admitted = input.demands.filter((item) => ADMITTED.has(item.admission));
  const demandSummary = hourlyDemand(admitted);
  if (admitted.length === 0) {
    return makeBlockedResult(input.serviceDate, input.matrix, ["NO_ADMITTED_DEMAND"], demandSummary);
  }
  if (admitted.some((item) => item.serviceDate !== input.serviceDate)) {
    return makeBlockedResult(input.serviceDate, input.matrix, ["JOB_CONTRACT_MISMATCH"], demandSummary);
  }

  const admittedIds = new Set<string>();
  for (const demand of admitted) {
    if (admittedIds.has(demand.occurrenceId)) {
      return makeBlockedResult(input.serviceDate, input.matrix, ["DUPLICATE_OCCURRENCE_COVERAGE"], demandSummary);
    }
    admittedIds.add(demand.occurrenceId);
  }

  let arcByPair: ReadonlyMap<string, number>;
  try {
    arcByPair = buildArcMap(input.matrix);
  } catch (error) {
    if (error instanceof PreviewValidationError) {
      return makeBlockedResult(input.serviceDate, input.matrix, [error.code], demandSummary);
    }
    throw error;
  }

  const assigned = new Set<string>();
  const verifiedJobs: VerifiedPreviewJob[] = [];
  try {
    for (const job of input.jobs) {
      for (const demand of job.demands) {
        if (!admittedIds.has(demand.occurrenceId)) fail("UNKNOWN_OCCURRENCE");
        if (assigned.has(demand.occurrenceId)) fail("DUPLICATE_OCCURRENCE_COVERAGE");
        assigned.add(demand.occurrenceId);
      }
      verifiedJobs.push(validateJob(job, input.serviceDate, admittedIds, arcByPair));
    }
    if (assigned.size !== admittedIds.size) fail("MISSING_OCCURRENCE_COVERAGE");
  } catch (error) {
    if (error instanceof PreviewValidationError) {
      return makeBlockedResult(input.serviceDate, input.matrix, [error.code], demandSummary);
    }
    throw error;
  }

  const fleet = assignPhysicalVehicles(
    verifiedJobs.flatMap((job) => job.intervals),
    input.vehicles,
    input.assignmentSearchNodeBudget,
  );
  if (fleet.status === "blocked_data") {
    return makeBlockedResult(
      input.serviceDate,
      input.matrix,
      fleet.reasonCodes,
      demandSummary,
      fleet.unassignedOccurrenceIds,
    );
  }

  return {
    status: fleet.status,
    publishable: false,
    serviceDate: input.serviceDate,
    matrix: matrixMetadata(input.matrix),
    hourlyDemand: demandSummary,
    jobs: verifiedJobs,
    routeIntervals: verifiedJobs.flatMap((job) => job.intervals),
    assignments: fleet.assignments,
    hourlyOccupiedVehicles: fleet.hourlyOccupiedVehicles,
    unassignedOccurrenceIds: fleet.unassignedOccurrenceIds,
    reasonCodes: fleet.reasonCodes,
    vehicleSummary: {
      minimumVehicles: fleet.minimumVehicles,
      minimumProven: fleet.minimumProven,
      lowerBound: fleet.lowerBound,
      peakConcurrentRoutes: fleet.peakConcurrentRoutes,
      activeFleetSize: fleet.activeFleetSize,
      routesPerJob: verifiedJobs.map((job) => ({
        jobId: job.id,
        direction: job.direction,
        anchorMinutes: job.anchorMinutes,
        routeCount: job.intervals.length,
        studentCount: job.intervals.reduce((sum, interval) => sum + interval.occurrenceIds.length, 0),
      })),
    },
  };
}
