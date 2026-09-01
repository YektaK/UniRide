/**
 * Admin Dudullu Readiness BFF
 * Aggregates redacted operational readiness for the Dudullu service.
 */

import { z } from "zod";
import { AppError, requireAdmin } from "@/lib/admin-auth";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { optimizerFetch } from "@/lib/optimizer-server";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "@/lib/supabase";
import {
  analyzeDudulluReadiness,
  requiredDudulluStudentLocations,
} from "@/services/dudullu-readiness";
import type {
  ReadinessMatrixSummary,
  ReadinessScheduleInput,
  ReadinessStudentInput,
  ReadinessVehicleInput,
} from "@/services/dudullu-readiness";

const UNAVAILABLE_BODY = {
  ready: false,
  reasonCodes: ["dependency_unavailable"],
} as const;

const NO_STORE_HEADERS = { "cache-control": "private, no-store" };

const EMPTY_MATRIX: ReadinessMatrixSummary = {
  source: "empty",
  loaded: false,
  stale: false,
  hasError: true,
  matrixLocationCount: 0,
  requiredLocationCount: 0,
  missingRequiredLocationCount: 0,
  expectedRequiredDirectedArcCount: 0,
  validRequiredDirectedArcCount: 0,
  invalidOrMissingRequiredDirectedArcCount: 0,
  depotPresent: false,
  complete: false,
  ready: false,
};

const TIMEOUT_MILLIS = 10_000;

const summarySchema = z
  .object({
    source: z.enum(["supabase", "empty", "coordinates"]),
    loaded: z.boolean(),
    stale: z.boolean(),
    hasError: z.boolean(),
    matrixLocationCount: z.number().int().nonnegative(),
    requiredLocationCount: z.number().int().nonnegative(),
    missingRequiredLocationCount: z.number().int().nonnegative(),
    expectedRequiredDirectedArcCount: z.number().int().nonnegative(),
    validRequiredDirectedArcCount: z.number().int().nonnegative(),
    invalidOrMissingRequiredDirectedArcCount: z.number().int().nonnegative(),
    depotPresent: z.boolean(),
    complete: z.boolean(),
    ready: z.boolean(),
  })
  .strict();

type AdminClient = ReturnType<typeof getSupabaseAdmin>;

async function selectAll(
  client: AdminClient,
  table: string,
  columns: string,
): Promise<Record<string, unknown>[]> {
  const { data, error } = await client.from(table).select(columns);
  if (error) {
    throw new Error("readiness query failed");
  }
  return Array.isArray(data) ? (data as Record<string, unknown>[]) : [];
}

function toStudent(row: Record<string, unknown>): ReadinessStudentInput {
  return {
    id: String(row.id ?? ""),
    role: String(row.role ?? ""),
    locationCode:
      typeof row.location_code === "string" ? row.location_code : undefined,
    disabilityType:
      typeof row.disability_type === "string" ? row.disability_type : undefined,
    weeklyScheduleId:
      typeof row.weekly_schedule_id === "string"
        ? row.weekly_schedule_id
        : undefined,
  };
}

function toSchedule(row: Record<string, unknown>): ReadinessScheduleInput {
  return {
    id: String(row.id ?? ""),
    userId: String(row.user_id ?? ""),
    entries: row.entries,
  };
}

function toVehicle(row: Record<string, unknown>): ReadinessVehicleInput {
  return {
    status: String(row.status ?? ""),
    wheelchairCapacity:
      typeof row.wheelchair_capacity === "number" ? row.wheelchair_capacity : 0,
    seatingCapacity:
      typeof row.seating_capacity === "number" ? row.seating_capacity : 0,
  };
}

function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: NO_STORE_HEADERS });
}

export async function GET(request: Request) {
  try {
    await requireAdmin(request);
  } catch (error) {
    if (error instanceof AppError) {
      return json({ error: error.message }, error.statusCode);
    }
    return json(UNAVAILABLE_BODY, 503);
  }

  let users: Record<string, unknown>[];
  let schedules: Record<string, unknown>[];
  let vehicles: Record<string, unknown>[];
  try {
    const client: SupabaseClient<Database> = getSupabaseAdmin();
    users = await selectAll(client, "users", "id, role, location_code, disability_type, weekly_schedule_id");
    schedules = await selectAll(client, "weekly_schedules", "id, user_id, entries");
    vehicles = await selectAll(client, "vehicles", "status, wheelchair_capacity, seating_capacity");
  } catch {
    return json(UNAVAILABLE_BODY, 503);
  }

  const studentInputs = users.map(toStudent);
  const scheduleInputs = schedules.map(toSchedule);
  const vehicleInputs = vehicles.map(toVehicle);

  const locationCodes = requiredDudulluStudentLocations(studentInputs, scheduleInputs);

  let matrix: ReadinessMatrixSummary;
  if (locationCodes.length === 0) {
    matrix = EMPTY_MATRIX;
  } else {
    try {
      const response = await optimizerFetch("/api/v1/internal/readiness/time-matrix", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ student_location_codes: locationCodes }),
        signal: AbortSignal.timeout(TIMEOUT_MILLIS),
      });
      if (!response.ok) {
        throw new Error("readiness upstream failed");
      }
      const raw: unknown = await response.json();
      const parsed = summarySchema.safeParse(raw);
      if (!parsed.success) {
        throw new Error("readiness upstream failed");
      }
      matrix = parsed.data;
    } catch {
      return json(UNAVAILABLE_BODY, 503);
    }
  }

  const report = analyzeDudulluReadiness(
    studentInputs,
    scheduleInputs,
    vehicleInputs,
    matrix,
  );

  return json(report, 200);
}