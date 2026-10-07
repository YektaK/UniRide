import { DUDULLU_CAMPUS } from "./dudullu-campus";
import { longestStudentRideMinutes } from "./dudullu-preview";
import type { DudulluPreviewJobView, DudulluPreviewResponse } from "./dudullu-preview-response";

/**
 * Pure view model for the admin daily-plan page. Everything is derived from the
 * /api/admin/dudullu-preview response; times are minutes of day in the Europe/Istanbul
 * service day, exactly as the backend uses them. No student names exist in the response:
 * stops are shown by location code only (K4).
 */

type Mutable<T> = { -readonly [K in keyof T]: T[K] };

export type PlanDirection = "pickup" | "dropoff";
export type PlanStatus = DudulluPreviewResponse["status"];
export type PlanTone = "success" | "warning" | "danger" | "neutral";

/** Reason codes the page has Turkish/English copy for (mirrors `PreviewReasonCode`). */
export const KNOWN_REASON_CODES = [
  "ADMISSION_ASSUMED",
  "ASSIGNMENT_SEARCH_INDETERMINATE",
  "CERTIFICATE_INVALID",
  "CLOSING_DEPOT_ARC_MISSING",
  "DUPLICATE_MATRIX_ARC",
  "DUPLICATE_OCCURRENCE_COVERAGE",
  "FLEET_INVALID",
  "FLEET_SHORTAGE",
  "JOB_CONTRACT_MISMATCH",
  "LEG_DECISIONS_UNAVAILABLE",
  "LEGACY_AMBIGUOUS_CONFIRMATION",
  "MATRIX_ARC_MISMATCH",
  "MATRIX_SNAPSHOT_INVALID",
  "MATRIX_UNAVAILABLE",
  "MISSING_OCCURRENCE_COVERAGE",
  "NO_ADMITTED_DEMAND",
  "NO_ROUTE_STEPS",
  "OPTIMIZATION_NOT_SUCCESSFUL",
  "PENDING_STUDENT_CONFIRMATION",
  "RIDE_TIME_LIMIT_INFEASIBLE",
  "ROUTE_OUTSIDE_SERVICE_DAY",
  "ROUTE_LOAD_MISMATCH",
  "ROUTE_TOTAL_MISMATCH",
  "SCHEDULE_DATA_INVALID",
  "UNKNOWN_OCCURRENCE",
  "UNKNOWN_ROUTE_NODE",
] as const;

export type KnownReasonCode = (typeof KNOWN_REASON_CODES)[number];

const KNOWN_REASON_SET: ReadonlySet<string> = new Set(KNOWN_REASON_CODES);

/** Codes that only describe how the demo was prepared, not a problem with the plan. */
const INFORMATIONAL_CODES: ReadonlySet<string> = new Set([
  "ADMISSION_ASSUMED",
  "PENDING_STUDENT_CONFIRMATION",
  "LEGACY_AMBIGUOUS_CONFIRMATION",
]);

export interface PlanReason {
  /** Original backend code. */
  readonly code: string;
  /** Message-catalog key under `reasons.*`; `unknown` for codes without copy. */
  readonly messageKey: KnownReasonCode | "unknown";
  readonly severity: "info" | "problem";
}

export interface PlanStop {
  readonly order: number;
  readonly kind: "campus" | "student";
  /** Location code (`So1`, `Sw3`) or the campus code; never a person's name. */
  readonly code: string;
  readonly disability: "Sw" | "So" | null;
  /** Minutes from route start at which the vehicle reaches this stop. */
  readonly offsetMinutes: number;
  readonly arrivalMinutes: number;
  readonly arrivalLabel: string;
  /** Driving time of the leg that ends at this stop (0 for the first stop). */
  readonly legMinutes: number;
}

export interface PlanRoute {
  readonly id: string;
  readonly number: number;
  readonly startMinutes: number;
  readonly endMinutes: number;
  readonly startLabel: string;
  readonly endLabel: string;
  readonly totalMinutes: number;
  /** Longest time any student of this route stays in the vehicle (rounded to a minute). */
  readonly maxRideMinutes: number;
  readonly swCount: number;
  readonly soCount: number;
  readonly studentCount: number;
  readonly stops: readonly PlanStop[];
  /** "Araç N" label of the assigned physical vehicle, or null when no assignment exists. */
  readonly vehicleLabel: string | null;
}

export interface PlanWave {
  readonly id: string;
  readonly direction: PlanDirection;
  readonly anchorMinutes: number;
  readonly anchorLabel: string;
  readonly routeCount: number;
  readonly studentCount: number;
  readonly swCount: number;
  readonly soCount: number;
  readonly routes: readonly PlanRoute[];
}

export interface PlanSection {
  readonly direction: PlanDirection;
  readonly waves: readonly PlanWave[];
}

export interface VehicleRouteSlot {
  readonly routeId: string;
  readonly direction: PlanDirection;
  readonly anchorLabel: string;
  readonly routeNumber: number;
  readonly startMinutes: number;
  readonly endMinutes: number;
  readonly startLabel: string;
  readonly endLabel: string;
  readonly swCount: number;
  readonly soCount: number;
  /** Position on the timeline, percent of its width. */
  readonly leftPercent: number;
  readonly widthPercent: number;
}

export interface VehicleRow {
  /** "Araç 1 .. Araç K", numbered by first departure; opaque ids are never shown. */
  readonly label: string;
  readonly routes: readonly VehicleRouteSlot[];
  readonly busyMinutes: number;
}

export interface VehicleTimeline {
  readonly startMinutes: number;
  readonly endMinutes: number;
  readonly ticks: readonly { readonly label: string; readonly leftPercent: number }[];
}

export type FleetState = "enough" | "missing" | "unknown";

export interface FleetComparison {
  readonly needed: number | null;
  readonly neededAtMost: boolean;
  readonly liveFleet: number | null;
  /** Count comparison only: template vehicles minus live vehicles is not a feasibility proof. */
  readonly difference: number | null;
  readonly state: FleetState;
  /** Retained for API compatibility; exact shortage/spare counts are not established. */
  readonly amount: number;
}

/** The wave that sets the capacity-only lower bound on the number of vehicles. */
export interface CapacityFloor {
  /** max over waves of max(ceil(Sw / swCapacity), ceil(So / soCapacity)). */
  readonly vehicles: number;
  readonly direction: PlanDirection;
  readonly anchorLabel: string;
  readonly studentCount: number;
  readonly swCount: number;
  readonly soCount: number;
  /** Largest Sw / So capacity of the fleet the plan used. */
  readonly swCapacity: number;
  readonly soCapacity: number;
}

export interface PlanSummary {
  readonly status: PlanStatus;
  readonly tone: PlanTone;
  readonly neededVehicles: number | null;
  /** True when the vehicle count is only an upper bound (assignment search not finished). */
  readonly neededAtMost: boolean;
  readonly lowerBound: number | null;
  readonly peakConcurrentRoutes: number | null;
  /** Capacity-only lower bound with its binding wave; null when it cannot be computed. */
  readonly capacityFloor: CapacityFloor | null;
  readonly students: number;
  readonly trips: number;
  readonly routes: number;
  readonly invalidStudentRecords: number;
  readonly fleet: FleetComparison;
  /** Longest student ride of the whole day (minutes); null when the plan has no route. */
  readonly maxRideMinutes: number | null;
}

export interface DailyPlanView {
  readonly serviceDate: string;
  readonly hypothetical: boolean;
  readonly assumedAdmission: boolean;
  readonly virtualFleet: boolean;
  readonly virtualTemplate: DudulluPreviewResponse["fleet"]["template"];
  /** The ride and tour limits the optimizer was given (minutes). */
  readonly limits: DudulluPreviewResponse["limits"];
  readonly summary: PlanSummary;
  readonly reasons: readonly PlanReason[];
  /** True when no admitted trip exists on that day (nothing to plan). */
  readonly isEmptyDay: boolean;
  readonly sections: readonly PlanSection[];
  readonly vehicles: readonly VehicleRow[];
  readonly timeline: VehicleTimeline | null;
}

/** `HH:MM` for a minute-of-day value (rounded to the nearest minute, 1440 -> "24:00"). */
export function formatMinutesOfDay(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/** Location code of a route node: the `#occurrence` suffix the backend adds is dropped. */
export function nodeLocationCode(node: string): string {
  const hash = node.indexOf("#");
  return hash === -1 ? node : node.slice(0, hash);
}

function disabilityOf(code: string): "Sw" | "So" | null {
  if (code.startsWith("Sw")) return "Sw";
  if (code.startsWith("So")) return "So";
  return null;
}

function statusTone(status: PlanStatus): PlanTone {
  switch (status) {
    case "preview_ready": return "success";
    case "indeterminate": return "warning";
    case "shortage": return "danger";
    case "blocked_data": return "danger";
  }
}

export function describeReason(code: string, assumedAdmission: boolean): PlanReason {
  const known = KNOWN_REASON_SET.has(code);
  const informational =
    INFORMATIONAL_CODES.has(code) || (code === "LEG_DECISIONS_UNAVAILABLE" && assumedAdmission);
  return {
    code,
    messageKey: known ? (code as KnownReasonCode) : "unknown",
    severity: informational ? "info" : "problem",
  };
}

function buildStops(
  steps: DudulluPreviewJobView["result"]["routes"][number]["route_details"],
  startMinutes: number,
): PlanStop[] {
  if (steps.length === 0) return [];
  const campus = DUDULLU_CAMPUS.code;
  const kindOf = (code: string): "campus" | "student" => (code === campus ? "campus" : "student");
  const makeStop = (order: number, node: string, offset: number, leg: number): PlanStop => {
    const code = nodeLocationCode(node);
    return {
      order,
      kind: kindOf(code),
      code,
      disability: disabilityOf(code),
      offsetMinutes: offset,
      arrivalMinutes: startMinutes + offset,
      arrivalLabel: formatMinutesOfDay(startMinutes + offset),
      legMinutes: leg,
    };
  };
  const stops: PlanStop[] = [makeStop(0, steps[0].location1, 0, 0)];
  let offset = 0;
  steps.forEach((step, index) => {
    offset += step.duration;
    stops.push(makeStop(index + 1, step.location2, offset, step.duration));
  });
  return stops;
}

function routeKey(jobId: string, routeIndex: number): string {
  return `${jobId}#${routeIndex}`;
}

function buildVehicles(
  response: DudulluPreviewResponse,
  routeById: ReadonlyMap<string, { route: PlanRoute; direction: PlanDirection; anchorLabel: string }>,
): { rows: VehicleRow[]; labelByRouteId: Map<string, string>; timeline: VehicleTimeline | null } {
  const byVehicle = new Map<string, { startMinutes: number; endMinutes: number; routeId: string }[]>();
  for (const assignment of response.assignments) {
    if (assignment.physicalVehicleId === "") continue;
    const routeId = routeKey(assignment.jobId, assignment.routeIndex);
    if (!routeById.has(routeId)) continue;
    const list = byVehicle.get(assignment.physicalVehicleId) ?? [];
    list.push({ startMinutes: assignment.startMinutes, endMinutes: assignment.endMinutes, routeId });
    byVehicle.set(assignment.physicalVehicleId, list);
  }

  const ordered = [...byVehicle.entries()]
    .map(([id, slots]) => ({ id, slots: [...slots].sort((a, b) => a.startMinutes - b.startMinutes || a.endMinutes - b.endMinutes) }))
    .sort((a, b) =>
      a.slots[0].startMinutes - b.slots[0].startMinutes || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  if (ordered.length === 0) return { rows: [], labelByRouteId: new Map(), timeline: null };

  const allSlots = ordered.flatMap((vehicle) => vehicle.slots);
  const firstHour = Math.floor(Math.min(...allSlots.map((slot) => slot.startMinutes)) / 60);
  const lastHour = Math.ceil(Math.max(...allSlots.map((slot) => slot.endMinutes)) / 60);
  const timelineStart = firstHour * 60;
  const timelineEnd = Math.max(lastHour, firstHour + 1) * 60;
  const span = timelineEnd - timelineStart;
  const percent = (minutes: number) => Math.round(((minutes - timelineStart) / span) * 10_000) / 100;

  const labelByRouteId = new Map<string, string>();
  const rows = ordered.map((vehicle, index): VehicleRow => {
    const label = `Araç ${index + 1}`;
    const routes = vehicle.slots.map((slot): VehicleRouteSlot => {
      labelByRouteId.set(slot.routeId, label);
      const info = routeById.get(slot.routeId)!;
      return {
        routeId: slot.routeId,
        direction: info.direction,
        anchorLabel: info.anchorLabel,
        routeNumber: info.route.number,
        startMinutes: slot.startMinutes,
        endMinutes: slot.endMinutes,
        startLabel: formatMinutesOfDay(slot.startMinutes),
        endLabel: formatMinutesOfDay(slot.endMinutes),
        swCount: info.route.swCount,
        soCount: info.route.soCount,
        leftPercent: percent(slot.startMinutes),
        widthPercent: Math.max(0.5, Math.round(((slot.endMinutes - slot.startMinutes) / span) * 10_000) / 100),
      };
    });
    return {
      label,
      routes,
      busyMinutes: Math.round(routes.reduce((sum, slot) => sum + (slot.endMinutes - slot.startMinutes), 0)),
    };
  });

  const ticks: { label: string; leftPercent: number }[] = [];
  const step = (lastHour - firstHour) > 12 ? 2 : 1;
  for (let hour = firstHour; hour <= timelineEnd / 60; hour += step) {
    ticks.push({ label: formatMinutesOfDay(hour * 60), leftPercent: percent(hour * 60) });
  }
  return { rows, labelByRouteId, timeline: { startMinutes: timelineStart, endMinutes: timelineEnd, ticks } };
}

/** Check the producer's complete witness, without repeating its capacity/cooldown solver. */
function hasCompleteRouteEvidence(response: DudulluPreviewResponse, requireAssignment: boolean): boolean {
  const intervals = response.jobs.flatMap((job) => job.intervals);
  const routeCount = response.jobs.reduce((sum, job) => sum + job.result.routes.length, 0);
  if (routeCount === 0 || intervals.length !== routeCount
    || response.routeIntervals.length !== routeCount || (requireAssignment && response.assignments.length !== routeCount)
    || new Set(response.jobs.map((job) => job.id)).size !== response.jobs.length) return false;
  const signature = (interval: DudulluPreviewResponse["routeIntervals"][number]) => JSON.stringify([
    interval.jobId, interval.routeIndex, interval.vehicleId, interval.direction,
    interval.startMinutes, interval.endMinutes, interval.swCount, interval.soCount,
    [...interval.occurrenceIds].sort(),
  ]);
  const expected = new Map<string, string>();
  const occurrences = new Set<string>();
  for (const job of response.jobs) {
    if (!job.result.success || job.serviceDate !== response.serviceDate
      || job.intervals.length !== job.result.routes.length) return false;
    for (const interval of job.intervals) {
      const route = job.result.routes[interval.routeIndex];
      const key = routeKey(interval.jobId, interval.routeIndex);
      if (!route || interval.jobId !== job.id || interval.direction !== job.direction
        || interval.vehicleId !== route.vehicle_id || interval.swCount !== route.sw_count
        || interval.soCount !== route.so_count || interval.endMinutes <= interval.startMinutes
        || interval.occurrenceIds.length !== interval.swCount + interval.soCount
        || interval.occurrenceIds.length === 0
        || JSON.stringify([...interval.occurrenceIds].sort()) !== JSON.stringify([...route.student_ids].sort())
        || expected.has(key)) return false;
      for (const id of interval.occurrenceIds) {
        if (!id || occurrences.has(id)) return false;
        occurrences.add(id);
      }
      expected.set(key, signature(interval));
    }
  }
  for (const entries of requireAssignment ? [response.routeIntervals, response.assignments] : [response.routeIntervals]) {
    const seen = new Set<string>();
    for (const entry of entries) {
      const key = routeKey(entry.jobId, entry.routeIndex);
      if (seen.has(key) || expected.get(key) !== signature(entry)) return false;
      seen.add(key);
    }
  }
  if (!requireAssignment) return true;
  const byVehicle = new Map<string, typeof response.assignments>();
  for (const assignment of response.assignments) {
    const slots = byVehicle.get(assignment.physicalVehicleId) ?? [];
    if (slots.some((slot) => assignment.startMinutes < slot.endMinutes && slot.startMinutes < assignment.endMinutes)) return false;
    byVehicle.set(assignment.physicalVehicleId, [...slots, assignment]);
  }
  const vehicleIds = new Set(response.assignments.map((assignment) => assignment.physicalVehicleId));
  if (vehicleIds.has("") || [...vehicleIds].some((id) => id.trim() === "")) return false;
  if (response.fleet.activeVehicleIds && [...vehicleIds].some((id) => !response.fleet.activeVehicleIds!.includes(id))) return false;
  return [response.fleet.liveActiveFleetSize, response.fleet.assignmentFleetSize, response.vehicleSummary?.activeFleetSize]
    .every((size) => size == null || vehicleIds.size <= size);
}

function compareFleet(
  needed: number | null,
  neededAtMost: boolean,
  response: DudulluPreviewResponse,
): FleetComparison {
  const liveFleet = response.fleet.liveActiveFleetSize;
  const state = response.fleetMode !== "live" || response.fleet.mode !== "live" ? "unknown"
    // The optimizer's FLEET_SHORTAGE certificate means it could not fit the routes into the live fleet.
    // The API then returns no jobs/route intervals, so an empty route list is accepted as that evidence;
    // a partial or inconsistent route list is not. No numeric shortfall is derived from it.
    : response.status === "shortage" && response.assignments.length === 0
      && response.reasonCodes.includes("FLEET_SHORTAGE")
      && ((response.jobs.length === 0 && response.routeIntervals.length === 0) || hasCompleteRouteEvidence(response, false)) ? "missing"
    : (response.status === "preview_ready" || response.status === "indeterminate") && response.vehicleSummary !== null
      && hasCompleteRouteEvidence(response, true) ? "enough"
    : "unknown";
  return {
    needed,
    neededAtMost,
    liveFleet,
    difference: needed === null || liveFleet === null ? null : needed - liveFleet,
    state,
    amount: 0,
  };
}

/**
 * Capacity-only lower bound on the vehicles of a day. Sw and So students use separate seat
 * pools, so a wave needs max(ceil(Sw / swCapacity), ceil(So / soCapacity)) vehicles at once
 * (all routes of a wave share one anchor time, so they run together). The day needs at least
 * the largest wave requirement. Ties go to the wave with more students, then the earlier one.
 * Null when there is no student or a needed seat pool has no capacity.
 */
export function computeCapacityFloor(
  waves: readonly Pick<PlanWave, "direction" | "anchorMinutes" | "anchorLabel" | "swCount" | "soCount">[],
  capacity: { readonly swCapacity: number; readonly soCapacity: number } | null | undefined,
): CapacityFloor | null {
  if (!capacity) return null;
  let best: (CapacityFloor & { anchorMinutes: number }) | null = null;
  for (const wave of waves) {
    const studentCount = wave.swCount + wave.soCount;
    if (studentCount === 0) continue;
    if ((wave.swCount > 0 && capacity.swCapacity <= 0) || (wave.soCount > 0 && capacity.soCapacity <= 0)) {
      return null;
    }
    const vehicles = Math.max(
      wave.swCount > 0 ? Math.ceil(wave.swCount / capacity.swCapacity) : 0,
      wave.soCount > 0 ? Math.ceil(wave.soCount / capacity.soCapacity) : 0,
    );
    const better = best === null
      || vehicles > best.vehicles
      || (vehicles === best.vehicles && (
        studentCount > best.studentCount
        || (studentCount === best.studentCount && wave.anchorMinutes < best.anchorMinutes)
      ));
    if (better) {
      best = {
        vehicles,
        direction: wave.direction,
        anchorLabel: wave.anchorLabel,
        anchorMinutes: wave.anchorMinutes,
        studentCount,
        swCount: wave.swCount,
        soCount: wave.soCount,
        swCapacity: capacity.swCapacity,
        soCapacity: capacity.soCapacity,
      };
    }
  }
  if (best === null) return null;
  const { vehicles, direction, anchorLabel, studentCount, swCount, soCount, swCapacity, soCapacity } = best;
  return { vehicles, direction, anchorLabel, studentCount, swCount, soCount, swCapacity, soCapacity };
}

/** Turns one preview response into everything the daily-plan page displays. */
export function buildDailyPlanView(response: DudulluPreviewResponse): DailyPlanView {
  const assumedAdmission = response.admissionMode === "assume_confirmed";
  const virtualFleet = response.fleetMode === "virtual";

  // Jobs with the same direction and anchor form one wave.
  const waveGroups = new Map<string, DudulluPreviewJobView[]>();
  for (const job of response.jobs) {
    const key = `${job.direction}:${job.anchorMinutes}`;
    waveGroups.set(key, [...(waveGroups.get(key) ?? []), job]);
  }

  const routeById = new Map<string, { route: PlanRoute; direction: PlanDirection; anchorLabel: string }>();
  const waves: PlanWave[] = [];
  const pendingRoutes: Mutable<PlanRoute>[] = [];
  for (const [key, jobs] of waveGroups) {
    const first = jobs[0];
    const anchorLabel = formatMinutesOfDay(first.anchorMinutes);
    const routes: Mutable<PlanRoute>[] = [];
    for (const job of jobs) {
      job.result.routes.forEach((raw, routeIndex) => {
        const interval = job.intervals.find((item) => item.routeIndex === routeIndex);
        const total = raw.route_details.reduce((sum, step) => sum + step.duration, 0);
        const startMinutes = interval?.startMinutes
          ?? (job.direction === "pickup" ? job.anchorMinutes - total : job.anchorMinutes);
        const endMinutes = interval?.endMinutes ?? startMinutes + total;
        const route: Mutable<PlanRoute> = {
          id: routeKey(job.id, routeIndex),
          number: routes.length + 1,
          startMinutes,
          endMinutes,
          startLabel: formatMinutesOfDay(startMinutes),
          endLabel: formatMinutesOfDay(endMinutes),
          totalMinutes: Math.round(total),
          maxRideMinutes: Math.round(longestStudentRideMinutes(raw.route_details, job.direction)),
          swCount: raw.sw_count,
          soCount: raw.so_count,
          studentCount: raw.sw_count + raw.so_count,
          stops: buildStops(raw.route_details, startMinutes),
          vehicleLabel: null,
        };
        routes.push(route);
        routeById.set(route.id, { route, direction: first.direction, anchorLabel });
      });
    }
    routes.sort((a, b) => a.startMinutes - b.startMinutes || a.endMinutes - b.endMinutes);
    // Number after sorting so "Rota 1" is the earliest departure of the wave.
    routes.forEach((route, index) => { route.number = index + 1; });
    pendingRoutes.push(...routes);
    waves.push({
      id: key,
      direction: first.direction,
      anchorMinutes: first.anchorMinutes,
      anchorLabel,
      routeCount: routes.length,
      studentCount: routes.reduce((sum, route) => sum + route.studentCount, 0),
      swCount: routes.reduce((sum, route) => sum + route.swCount, 0),
      soCount: routes.reduce((sum, route) => sum + route.soCount, 0),
      routes,
    });
  }

  const { rows: vehicles, labelByRouteId, timeline } = buildVehicles(response, routeById);
  for (const route of pendingRoutes) {
    route.vehicleLabel = labelByRouteId.get(route.id) ?? null;
  }

  const sections: PlanSection[] = (["pickup", "dropoff"] as const)
    .map((direction) => ({
      direction,
      waves: waves
        .filter((wave) => wave.direction === direction)
        .sort((a, b) => a.anchorMinutes - b.anchorMinutes),
    }))
    .filter((section) => section.waves.length > 0);

  const summaryFleet = response.vehicleSummary;
  const neededVehicles = summaryFleet?.minimumVehicles ?? null;
  const neededAtMost = neededVehicles !== null && summaryFleet !== null && !summaryFleet.minimumProven;
  const routeCount = waves.reduce((sum, wave) => sum + wave.routeCount, 0);
  const tripsFromJobs = waves.reduce((sum, wave) => sum + wave.studentCount, 0);
  const trips = summaryFleet
    ? summaryFleet.routesPerJob.reduce((sum, job) => sum + job.studentCount, 0)
    : tripsFromJobs;

  const reasons = response.reasonCodes.map((code) => describeReason(code, assumedAdmission));
  // An empty day is only the plain "nothing to plan" answer: any other real problem
  // (invalid schedule data, missing decision table, fleet, matrix ...) must stay visible.
  const isEmptyDay = response.reasonCodes.includes("NO_ADMITTED_DEMAND")
    && reasons.every((reason) => reason.code === "NO_ADMITTED_DEMAND" || reason.severity === "info");

  return {
    serviceDate: response.serviceDate,
    hypothetical: response.hypothetical,
    assumedAdmission,
    virtualFleet,
    virtualTemplate: response.fleet.template,
    limits: response.limits,
    summary: {
      status: response.status,
      tone: isEmptyDay ? "neutral" : statusTone(response.status),
      neededVehicles,
      neededAtMost,
      lowerBound: summaryFleet?.lowerBound ?? null,
      peakConcurrentRoutes: summaryFleet?.peakConcurrentRoutes ?? null,
      capacityFloor: computeCapacityFloor(waves, response.fleet.maxCapacity),
      students: response.candidateSummary.dudulluStudents,
      trips,
      routes: routeCount,
      invalidStudentRecords: response.candidateSummary.invalidStudentRecords,
      fleet: compareFleet(neededVehicles, neededAtMost, response),
      maxRideMinutes: pendingRoutes.length === 0
        ? null
        : Math.max(...pendingRoutes.map((route) => route.maxRideMinutes)),
    },
    reasons,
    isEmptyDay,
    sections,
    vehicles,
    timeline,
  };
}
