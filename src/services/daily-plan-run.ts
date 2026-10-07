import "server-only";
import type { getSupabaseAdmin } from "@/lib/supabase-admin";
import { z } from "zod";
import type { ScheduleEntry } from "@/types";
import {
  buildScheduleDemands,
  isBlockingLegacyRequestStatus,
  isDudulluCampus,
  serviceDayOfWeek,
  type DemandAdmission,
  type StudentLegDecision,
  type TripDirection,
} from "@/services/daily-planning";
import {
  assumeScheduledLegsConfirmed,
  buildDudulluPreview,
  buildVirtualFleet,
  selectVirtualFleetTemplate,
  type PreviewDemand,
  type VirtualFleetTemplate,
} from "@/services/dudullu-preview";
import type { MatrixSnapshot, PreviewJobInput, PreviewOptimizationResult, PreviewVehicle, PreviewReasonCode } from "@/services/dudullu-preview";
import { serviceDateBounds } from "@/services/istanbul-service-date";
import { DUDULLU_DEPOT } from "@/services/dudullu-campus";

type AdmissionMode = "recorded" | "assume_confirmed";
type FleetMode = "live" | "virtual";

export type DailyPlanReader = Pick<ReturnType<typeof getSupabaseAdmin>, "from">;
export interface DailyPlanDeps {
  readonly reader: DailyPlanReader;
  readonly optimizerFetch: (path: string, init?: RequestInit) => Promise<Response>;
  // Current preview has no wall-clock-dependent output; callers own run timestamps.
  readonly clock: () => Date;
}

/**
 * Largest vehicle list sent to one /optimize call. Mirrors the optimizer policy cap
 * (`UNIRIDE_COMPUTE_MAX_VEHICLES`, default 50: optimizer_api/compute_policy.py and
 * optimizer_api/models/schemas.py). The full virtual fleet is only given to the physical
 * assignment search, never to /optimize.
 */
const OPTIMIZER_MAX_VEHICLES = 50;

// Postgres "undefined_table" and PostgREST "table not found in the schema cache".
const MISSING_RELATION_CODES = new Set(["42P01", "PGRST205"]);

const scheduleEntrySchema = z.object({
  id: z.string().min(1),
  dayOfWeek: z.enum([
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
  ]),
  startTime: z.string(),
  endTime: z.string(),
  location: z.string().optional(),
  courseName: z.string().optional(),
}).passthrough();
const decisionRowSchema = z.object({
  user_id: z.string().min(1),
  service_date: z.string(),
  direction: z.enum(["pickup", "dropoff"]),
  decision: z.enum(["confirmed", "cancelled"]),
  decided_at: z.string().datetime({ offset: true }),
  flexibility_minutes: z.number().int().min(0).max(1439),
}).passthrough();
const snapshotSchema = z.object({
  id: z.string(), version: z.string(), sha256: z.string().regex(/^[0-9a-f]{64}$/),
  source: z.literal("supabase"),
  arcs: z.array(z.object({ origin_code: z.string(), destination_code: z.string(), duration_minutes: z.number() })),
});
const optimizerResultSchema = z.object({
  success: z.boolean(),
  routes: z.array(z.object({
    vehicle_id: z.string(),
    route_details: z.array(z.object({ location1: z.string(), location2: z.string(), duration: z.number(), distance: z.number() })),
    total_duration_minutes: z.number(), total_distance_km: z.number().optional(),
    sw_count: z.number(), so_count: z.number(), student_ids: z.array(z.string()),
  })),
  total_duration_minutes: z.number().optional(), feasibility_certificate: z.unknown().optional(),
});

type QueryResult = { data: unknown; error: unknown };
type DataRow = Record<string, unknown>;

function isRow(value: unknown): value is DataRow {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function selectRows(query: PromiseLike<QueryResult>): Promise<DataRow[]> {
  const { data, error } = await query;
  if (error || !Array.isArray(data) || !data.every(isRow)) {
    throw new Error("preview read failed");
  }
  return data;
}

/** Like `selectRows`, but reports a missing relation (not any other failure) as `null`. */
async function selectRowsOrMissingRelation(query: PromiseLike<QueryResult>): Promise<DataRow[] | null> {
  const { data, error } = await query;
  if (isRow(error) && typeof error.code === "string" && MISSING_RELATION_CODES.has(error.code)) return null;
  if (error || !Array.isArray(data) || !data.every(isRow)) {
    throw new Error("preview read failed");
  }
  return data;
}

function violatesFleetSize(certificate: unknown): boolean {
  if (!isRow(certificate) || !Array.isArray(certificate.violations)) return false;
  return certificate.violations.some((violation) => isRow(violation) && violation.type === "fleet_size_violation");
}

function violatesRideTime(certificate: unknown): boolean {
  if (!isRow(certificate) || !Array.isArray(certificate.violations)) return false;
  return certificate.violations.some((violation) => isRow(violation) && violation.type === "ride_time_violation");
}

function nonBlankString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function withReasonCodes(
  result: ReturnType<typeof buildDudulluPreview>,
  extra: readonly (typeof result.reasonCodes)[number][],
) {
  return { ...result, reasonCodes: [...new Set([...result.reasonCodes, ...extra])] };
}

function blockedPreview(
  serviceDate: string,
  demands: readonly PreviewDemand[],
  matrix: MatrixSnapshot | null,
  reason: PreviewReasonCode,
) {
  const base = buildDudulluPreview({ serviceDate, demands, vehicles: [], matrix, jobs: [] });
  return { ...base, status: "blocked_data" as const, jobs: [], reasonCodes: [reason] };
}

function exactClock(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function nodeMaps(demands: readonly PreviewDemand[]) {
  const counts = new Map<string, number>();
  for (const demand of demands) counts.set(demand.locationCode, (counts.get(demand.locationCode) ?? 0) + 1);
  const nodeToLocation = new Map<string, string>([[DUDULLU_DEPOT.id, DUDULLU_DEPOT.id]]);
  const nodeToOccurrence = new Map<string, string>();
  const reserved = new Set(demands.map((demand) => demand.locationCode));
  for (const demand of demands) {
    if (counts.get(demand.locationCode) !== 1) continue;
    nodeToLocation.set(demand.locationCode, demand.locationCode);
    nodeToOccurrence.set(demand.locationCode, demand.occurrenceId);
  }
  for (const demand of demands) {
    if (counts.get(demand.locationCode) === 1) continue;
    const base = `${demand.locationCode}#${demand.occurrenceId}`;
    let node = base;
    for (let suffix = 1; reserved.has(node) || nodeToLocation.has(node); suffix += 1) node = `${base}#${suffix}`;
    nodeToLocation.set(node, demand.locationCode);
    nodeToOccurrence.set(node, demand.occurrenceId);
  }
  return { nodeToLocation, nodeToOccurrence };
}

const ADMISSION_KEYS: readonly DemandAdmission[] = [
  "confirmed", "approved", "pending_student_confirmation", "pending_admin_approval", "cancelled",
];

export interface DailyPlanParams {
  readonly serviceDate: string;
  readonly admissionMode: AdmissionMode;
  readonly fleetMode: FleetMode;
  readonly maxRideTimeMinutes: number;
  readonly maxTourMinutes: number;
}

export async function runDailyPlan(deps: DailyPlanDeps, params: DailyPlanParams) {
  const { serviceDate, admissionMode, fleetMode, maxRideTimeMinutes, maxTourMinutes } = params;
  const { reader: client, optimizerFetch } = deps;
  // K1 (owner decision, 2026-10-04): a deliberate, owner-approved exception to
  // ACTIVE_ROADMAP.md's "do not infer consent". It is preview-only: nothing is written,
  // the response is labelled hypothetical and publishable stays false.
  const assumeConfirmed = admissionMode === "assume_confirmed";
  const hypothetical = assumeConfirmed || fleetMode !== "live";
  const candidateSummary = {
    dudulluStudents: 0,
    legsByAdmission: Object.fromEntries(ADMISSION_KEYS.map((key) => [key, 0])) as Record<DemandAdmission, number>,
    invalidStudentRecords: 0,
  };
  const occurrenceLabels: Record<string, string> = {};
  const fleetInfo: {
    mode: FleetMode;
    assignmentFleetSize: number | null;
    liveActiveFleetSize: number | null;
    activeVehicleIds?: string[];
    template: VirtualFleetTemplate | null;
    maxCapacity: { swCapacity: number; soCapacity: number } | null;
  } = { mode: fleetMode, assignmentFleetSize: null, liveActiveFleetSize: null, template: null, maxCapacity: null };
  // The optimizer limits are echoed; no global minimum ride limit is proven.
  const limits: {
    maxRideTimeMinutes: number;
    maxTourMinutes: number;
    minimumFeasibleRideMinutes: number | null;
  } = { maxRideTimeMinutes, maxTourMinutes, minimumFeasibleRideMinutes: null };
  const extraReasons: PreviewReasonCode[] = [];
  if (assumeConfirmed) extraReasons.push("ADMISSION_ASSUMED");

  // Every response, including blocked ones, carries the same labelling. Display labels are
  // location codes only; no user names are read or returned (K4).
  const finish = <T extends ReturnType<typeof buildDudulluPreview>>(result: T) => ({
    ...withReasonCodes(result, extraReasons),
    admissionMode,
    fleetMode,
    hypothetical,
    candidateSummary,
    fleet: fleetInfo,
    limits,
    occurrenceLabels,
  });

  const users = await selectRows(
    client.from("users")
      .select("id, role, location_code, disability_type, weekly_schedule_id")
      .eq("role", "student"),
  );

  const usersById = new Map<string, DataRow>();
  const scheduleIds = new Set<string>();
  let scheduleDataInvalid = false;
  for (const user of users) {
    if (
      !nonBlankString(user.id) ||
      user.role !== "student" ||
      usersById.has(user.id)
    ) {
      scheduleDataInvalid = true;
      continue;
    }
    usersById.set(user.id, user);
    if (user.weekly_schedule_id === null) continue;
    if (!nonBlankString(user.weekly_schedule_id)) {
      scheduleDataInvalid = true;
      continue;
    }
    scheduleIds.add(user.weekly_schedule_id);
  }

  const schedules = scheduleIds.size === 0
    ? []
    : await selectRows(
      client.from("weekly_schedules")
        .select("id, user_id, entries")
        .in("id", [...scheduleIds]),
    );
  const schedulesById = new Map<string, DataRow>();
  for (const schedule of schedules) {
    if (!nonBlankString(schedule.id) || schedulesById.has(schedule.id)) {
      scheduleDataInvalid = true;
      continue;
    }
    schedulesById.set(schedule.id, schedule);
  }
  if (schedulesById.size !== scheduleIds.size) scheduleDataInvalid = true;

  const candidates: Array<{
    studentId: string;
    locationCode: string;
    disabilityType: "Sw" | "So";
    entries: ScheduleEntry[];
  }> = [];
  const dudulluStudentIds = new Set<string>();
  const serviceDay = serviceDayOfWeek(serviceDate);
  for (const [studentId, user] of usersById) {
    if (user.weekly_schedule_id === null) continue;
    const scheduleId = user.weekly_schedule_id as string;
    const schedule = schedulesById.get(scheduleId);
    if (!schedule || schedule.user_id !== studentId) {
      scheduleDataInvalid = true;
      continue;
    }
    const entries = z.array(scheduleEntrySchema).safeParse(schedule.entries);
    if (!entries.success) {
      scheduleDataInvalid = true;
      continue;
    }
    const hasDudulluEntry = entries.data.some(
      (entry) => entry.dayOfWeek === serviceDay && isDudulluCampus(entry.location ?? ""),
    );
    if (!hasDudulluEntry) continue;
    if (
      !nonBlankString(user.location_code) ||
      (user.disability_type !== "Sw" && user.disability_type !== "So")
    ) {
      // Profile-level defect: the demo mode drops this student and counts it; otherwise the
      // whole day stays blocked. Integrity errors (duplicates, dangling schedules) always block.
      if (assumeConfirmed) candidateSummary.invalidStudentRecords += 1;
      else scheduleDataInvalid = true;
      continue;
    }

    dudulluStudentIds.add(studentId);
    candidates.push({
      studentId,
      locationCode: user.location_code,
      disabilityType: user.disability_type,
      entries: entries.data as ScheduleEntry[],
    });
  }

  candidateSummary.dudulluStudents = candidates.length;
  const decisionsByStudent = new Map<string, Partial<Record<TripDirection, StudentLegDecision>>>();
  const blockedStudents = new Set<string>();
  if (dudulluStudentIds.size > 0) {
    const decisionRows = await selectRowsOrMissingRelation(
      client.from("student_leg_decisions")
        .select("user_id, service_date, direction, decision, decided_at, flexibility_minutes")
        .in("user_id", [...dudulluStudentIds])
        .eq("service_date", serviceDate),
    );
    if (decisionRows === null) {
      // The table does not exist (true on the live DB today). Recorded admission cannot be
      // evaluated at all; the demo mode proceeds without recorded decisions.
      extraReasons.push("LEG_DECISIONS_UNAVAILABLE");
      if (!assumeConfirmed) {
        if (scheduleDataInvalid) extraReasons.push("SCHEDULE_DATA_INVALID");
        return finish(blockedPreview(serviceDate, [], null, "LEG_DECISIONS_UNAVAILABLE"));
      }
    }
    for (const raw of decisionRows ?? []) {
      const parsed = decisionRowSchema.safeParse(raw);
      if (!parsed.success || !dudulluStudentIds.has(parsed.data.user_id) || parsed.data.service_date !== serviceDate) {
        scheduleDataInvalid = true;
        continue;
      }
      const row = parsed.data;
      const decisions = decisionsByStudent.get(row.user_id) ?? {};
      if (decisions[row.direction]) {
        scheduleDataInvalid = true;
        continue;
      }
      decisions[row.direction] = row.decision === "confirmed"
        ? { status: "confirmed", confirmedAt: row.decided_at, flexibilityMinutes: row.flexibility_minutes }
        : { status: "cancelled", decidedAt: row.decided_at };
      decisionsByStudent.set(row.user_id, decisions);
    }

    const { start, end } = serviceDateBounds(serviceDate);
    const requests = await selectRows(
      client.from("ride_requests")
        .select("id, user_id, requested_pickup_time, requested_dropoff_time, status")
        .in("user_id", [...dudulluStudentIds])
        .or(
          `and(requested_pickup_time.gte.${start},requested_pickup_time.lt.${end}),` +
          `and(requested_dropoff_time.gte.${start},requested_dropoff_time.lt.${end})`,
        ),
    );
    for (const request of requests) {
      const status = String(request.status);
      if (!nonBlankString(request.user_id) || !dudulluStudentIds.has(request.user_id)) {
        scheduleDataInvalid = true;
      } else if (isBlockingLegacyRequestStatus(status)) {
        blockedStudents.add(request.user_id);
      }
    }
  }

  const demands: PreviewDemand[] = [];
  for (const candidate of candidates) {
    try {
      const scheduleDemands = buildScheduleDemands({
        studentId: candidate.studentId,
        locationCode: candidate.locationCode,
        serviceDate,
        scheduleEntries: candidate.entries,
        decisions: decisionsByStudent.get(candidate.studentId),
      }).demands;
      const typed = scheduleDemands.map((demand) => ({
        ...demand,
        // In the demo mode the downgrade is undone by assumeScheduledLegsConfirmed below, so
        // legacy blockers only leave the info code.
        admission: blockedStudents.has(candidate.studentId) && demand.admission === "confirmed"
          ? "pending_admin_approval" as const
          : demand.admission,
        disabilityType: candidate.disabilityType,
      }));
      demands.push(...(assumeConfirmed ? assumeScheduledLegsConfirmed(typed) : typed));
    } catch {
      scheduleDataInvalid = true;
    }
  }
  for (const demand of demands) candidateSummary.legsByAdmission[demand.admission] += 1;
  if (demands.some((demand) => demand.admission === "pending_student_confirmation")) {
    extraReasons.push("PENDING_STUDENT_CONFIRMATION");
  }
  if (blockedStudents.size > 0) extraReasons.push("LEGACY_AMBIGUOUS_CONFIRMATION");
  if (scheduleDataInvalid) extraReasons.push("SCHEDULE_DATA_INVALID");

  const admitted = scheduleDataInvalid ? [] : demands.filter((demand) => demand.admission === "confirmed" || demand.admission === "approved");
  if (admitted.length === 0) {
    return finish(buildDudulluPreview({ serviceDate, demands: [], vehicles: [], matrix: null, jobs: [] }));
  }
  for (const demand of admitted) occurrenceLabels[demand.occurrenceId] = demand.locationCode;

  const vehicleRows = await selectRows(
    client.from("vehicles")
      .select("id, wheelchair_capacity, seating_capacity, cooldown_minutes, status")
      .eq("status", "active"),
  );
  const liveVehicles: PreviewVehicle[] = [];
  const vehicleIds = new Set<string>();
  for (const row of vehicleRows) {
    if (
      !nonBlankString(row.id) || vehicleIds.has(row.id) || row.status !== "active" ||
      !Number.isInteger(row.wheelchair_capacity) || (row.wheelchair_capacity as number) < 0 ||
      !Number.isInteger(row.seating_capacity) || (row.seating_capacity as number) < 0 ||
      !Number.isInteger(row.cooldown_minutes) || (row.cooldown_minutes as number) < 0
    ) return finish(blockedPreview(serviceDate, admitted, null, "FLEET_INVALID"));
    vehicleIds.add(row.id);
    liveVehicles.push({
      vehicleId: row.id,
      swCapacity: row.wheelchair_capacity as number,
      soCapacity: row.seating_capacity as number,
      cooldownMinutes: row.cooldown_minutes as number,
    });
  }
  fleetInfo.liveActiveFleetSize = liveVehicles.length;
  fleetInfo.activeVehicleIds = liveVehicles.map((vehicle) => vehicle.vehicleId);
  if (fleetMode === "live" && liveVehicles.length === 0) {
    return finish(blockedPreview(serviceDate, admitted, null, "FLEET_SHORTAGE"));
  }
  // K2 (owner decision, 2026-10-04): the virtual fleet is N identical copies of one template
  // vehicle, N = admitted legs of the day. Identical copies keep the assignment search provable.
  // `vehicles` is the fleet used for the physical assignment; /optimize gets a capped slice.
  let vehicles = liveVehicles;
  if (fleetMode === "virtual") {
    fleetInfo.template = selectVirtualFleetTemplate(liveVehicles);
    vehicles = buildVirtualFleet(fleetInfo.template, admitted.length);
  }
  fleetInfo.assignmentFleetSize = vehicles.length;
  // Largest seat counts of the fleet the plan used: lets the page explain the capacity-only
  // vehicle floor ("why N vehicles?"). Sw and So seats are separate pools.
  if (vehicles.length > 0) {
    fleetInfo.maxCapacity = {
      swCapacity: Math.max(...vehicles.map((vehicle) => vehicle.swCapacity)),
      soCapacity: Math.max(...vehicles.map((vehicle) => vehicle.soCapacity)),
    };
  }

  let matrix: MatrixSnapshot;
  try {
    const response = await optimizerFetch("/api/v1/internal/matrix-snapshot", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ student_location_codes: [...new Set(admitted.map((demand) => demand.locationCode))] }),
    });
    if (!response.ok) throw new Error("matrix unavailable");
    const parsed = snapshotSchema.safeParse(await response.json());
    if (!parsed.success || parsed.data.id !== `time_matrix:sha256:${parsed.data.sha256}` || parsed.data.version !== parsed.data.sha256) {
      throw new Error("matrix invalid");
    }
    matrix = parsed.data;
  } catch {
    return finish(blockedPreview(serviceDate, admitted, null, "MATRIX_UNAVAILABLE"));
  }

  const groups = new Map<string, PreviewDemand[]>();
  for (const demand of admitted) {
    const key = `${demand.direction}:${demand.anchorMinutes}`;
    const group = groups.get(key) ?? [];
    group.push(demand);
    groups.set(key, group);
  }
  const jobs: PreviewJobInput[] = [];
  for (const group of groups.values()) {
    const first = group[0]!;
    // Virtual: at most min(legs in the wave, policy cap) identical vehicles per call.
    const waveVehicles = fleetMode === "virtual"
      ? vehicles.slice(0, Math.min(group.length, OPTIMIZER_MAX_VEHICLES))
      : vehicles;
    let result: PreviewOptimizationResult;
    try {
      const response = await optimizerFetch("/api/v1/optimize", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({
          algorithm: "ga_split", mode: "sandbox", service_date: serviceDate,
          direction: first.direction, target_time: exactClock(first.anchorMinutes),
          expected_matrix_sha256: matrix.sha256, use_time_windows: false,
          is_asymmetric: true,
          max_travel_time: maxTourMinutes, max_ride_time: maxRideTimeMinutes,
          sw_capacity: Math.max(0, ...waveVehicles.map((vehicle) => vehicle.swCapacity)),
          so_capacity: Math.max(0, ...waveVehicles.map((vehicle) => vehicle.soCapacity)),
          depot: DUDULLU_DEPOT,
          students: group.map((demand) => ({
            id: demand.occurrenceId, occurrence_id: demand.occurrenceId,
            name: demand.studentId, location_code: demand.locationCode,
            disability_type: demand.disabilityType,
          })),
          vehicles: waveVehicles.map((vehicle) => ({
            vehicle_id: vehicle.vehicleId, sw_capacity: vehicle.swCapacity,
            so_capacity: vehicle.soCapacity, cooldown_minutes: vehicle.cooldownMinutes,
          })),
        }),
      });
      if (!response.ok) throw new Error("optimizer unavailable");
      const parsed = optimizerResultSchema.safeParse(await response.json());
      if (!parsed.success) throw new Error("optimizer result invalid");
      result = parsed.data;
    } catch {
      return finish(blockedPreview(serviceDate, admitted, matrix, "OPTIMIZATION_NOT_SUCCESSFUL"));
    }
    if (fleetMode === "live" && !result.success && violatesFleetSize(result.feasibility_certificate)) {
      // The solver needs more routes than the real fleet has vehicles: report the shortage
      // instead of a generic optimization failure. Not applied to the virtual fleet, where
      // the vehicle list is capped by the optimizer policy and not by the real fleet.
      return finish({ ...blockedPreview(serviceDate, admitted, matrix, "FLEET_SHORTAGE"), status: "shortage" as const });
    }
    if (!result.success && violatesRideTime(result.feasibility_certificate)) {
      // No suitable route was computed within the ride limit.
      return finish(blockedPreview(serviceDate, admitted, matrix, "RIDE_TIME_LIMIT_INFEASIBLE"));
    }
    jobs.push({
      id: `${serviceDate}:${first.direction}:${first.anchorMinutes}`,
      serviceDate, direction: first.direction, anchorMinutes: first.anchorMinutes,
      demands: group, ...nodeMaps(group), result,
    });
  }
  return finish(buildDudulluPreview({ serviceDate, demands: admitted, vehicles, matrix, jobs }));
}

