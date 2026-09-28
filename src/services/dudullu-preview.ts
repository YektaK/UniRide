import type { DailyTripDemand, TripDirection } from "./daily-planning";
import { DUDULLU_CAMPUS } from "./dudullu-campus";

const DEPOT_CODE = DUDULLU_CAMPUS.code;
const SERVICE_DAY_END_MINUTES = 24 * 60;
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
  | "CERTIFICATE_INVALID"
  | "CLOSING_DEPOT_ARC_MISSING"
  | "DUPLICATE_MATRIX_ARC"
  | "DUPLICATE_OCCURRENCE_COVERAGE"
  | "JOB_CONTRACT_MISMATCH"
  | "MATRIX_ARC_MISMATCH"
  | "MATRIX_SNAPSHOT_INVALID"
  | "MATRIX_UNAVAILABLE"
  | "MISSING_OCCURRENCE_COVERAGE"
  | "NO_ADMITTED_DEMAND"
  | "NO_ROUTE_STEPS"
  | "OPTIMIZATION_NOT_SUCCESSFUL"
  | "ROUTE_OUTSIDE_SERVICE_DAY"
  | "ROUTE_TOTAL_MISMATCH"
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

export interface DudulluPreviewResult {
  readonly status: "preview_ready" | "blocked_data";
  readonly publishable: false;
  readonly serviceDate: string;
  readonly matrix: Omit<MatrixSnapshot, "arcs"> | null;
  readonly hourlyDemand: Readonly<Record<string, HourlyDemandSummary>>;
  readonly jobs: readonly VerifiedPreviewJob[];
  readonly routeIntervals: readonly PreviewRouteInterval[];
  readonly assignments: readonly unknown[];
  readonly unassignedOccurrenceIds: readonly string[];
  readonly reasonCodes: readonly PreviewReasonCode[];
}

export interface BuildDudulluPreviewInput {
  readonly serviceDate: string;
  readonly demands: readonly PreviewDemand[];
  readonly vehicles: readonly PreviewVehicle[];
  readonly matrix: MatrixSnapshot | null | undefined;
  readonly jobs: readonly PreviewJobInput[];
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
    unassignedOccurrenceIds: [],
    reasonCodes: [...new Set(reasonCodes)],
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

  return {
    status: "preview_ready",
    publishable: false,
    serviceDate: input.serviceDate,
    matrix: matrixMetadata(input.matrix),
    hourlyDemand: demandSummary,
    jobs: verifiedJobs,
    routeIntervals: verifiedJobs.flatMap((job) => job.intervals),
    assignments: [],
    unassignedOccurrenceIds: [],
    reasonCodes: [],
  };
}
