import { z } from "zod";
import { AppError, requireAdmin } from "@/lib/admin-auth";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import type { ScheduleEntry } from "@/types";
import {
  buildScheduleDemands,
  isDudulluCampus,
  serviceDayOfWeek,
  type DailyTripDemand,
} from "@/services/daily-planning";
import { buildDudulluPreview, type PreviewDemand } from "@/services/dudullu-preview";
import { isRealServiceDate, serviceDateBounds } from "@/services/istanbul-service-date";

const NO_STORE_HEADERS = { "cache-control": "private, no-store" };
const SERVICE_DATE_SCHEMA = z.object({
  serviceDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
}).strict();

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

type QueryResult = { data: unknown; error: unknown };
type DataRow = Record<string, unknown>;

function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: NO_STORE_HEADERS });
}

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

function nonBlankString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isCancelledRequest(row: DataRow): boolean {
  return row.status === "cancelled_by_student" || row.status === "cancelled_by_admin";
}

function withReasonCodes(
  result: ReturnType<typeof buildDudulluPreview>,
  extra: readonly (typeof result.reasonCodes)[number][],
) {
  return { ...result, reasonCodes: [...new Set([...result.reasonCodes, ...extra])] };
}

async function loadBlockedPreview(serviceDate: string) {
  const client = getSupabaseAdmin();
  const users = await selectRows(
    client.from("users")
      .select("id, role, location_code, disability_type, weekly_schedule_id")
      .eq("role", "student"),
  );

  const usersById = new Map<string, DataRow>();
  const scheduleIds = new Set<string>();
  let scheduleDataInvalid = false;
  for (const user of users) {
    if (!nonBlankString(user.id) || !nonBlankString(user.weekly_schedule_id)) {
      scheduleDataInvalid = true;
      continue;
    }
    usersById.set(user.id, user);
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

  const demands: PreviewDemand[] = [];
  const dudulluStudentIds = new Set<string>();
  const serviceDay = serviceDayOfWeek(serviceDate);
  for (const [studentId, user] of usersById) {
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
      scheduleDataInvalid = true;
      continue;
    }

    let scheduleDemands: readonly DailyTripDemand[];
    try {
      scheduleDemands = buildScheduleDemands({
        studentId,
        locationCode: user.location_code,
        serviceDate,
        scheduleEntries: entries.data as ScheduleEntry[],
      }).demands;
    } catch {
      scheduleDataInvalid = true;
      continue;
    }
    if (scheduleDemands.length === 0) continue;

    dudulluStudentIds.add(studentId);
    demands.push(...scheduleDemands.map((demand) => ({
      ...demand,
      disabilityType: user.disability_type as "Sw" | "So",
    })));
  }

  const extraReasons: Array<ReturnType<typeof buildDudulluPreview>["reasonCodes"][number]> = [];
  if (demands.length > 0) extraReasons.push("PENDING_STUDENT_CONFIRMATION");
  if (scheduleDataInvalid) extraReasons.push("SCHEDULE_DATA_INVALID");

  if (dudulluStudentIds.size > 0) {
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
    if (requests.some((request) => !isCancelledRequest(request))) {
      extraReasons.push("LEGACY_AMBIGUOUS_CONFIRMATION");
    }
  }

  const base = buildDudulluPreview({
    serviceDate,
    demands,
    vehicles: [],
    matrix: null,
    jobs: [],
  });
  return withReasonCodes(base, extraReasons);
}

export async function POST(request: Request): Promise<Response> {
  try {
    await requireAdmin(request);
  } catch (error) {
    if (error instanceof AppError && [401, 403].includes(error.statusCode)) {
      return json({ error: "ADMIN_REQUIRED" }, error.statusCode);
    }
    return json({ error: "PREVIEW_UNAVAILABLE" }, 503);
  }

  let parsedBody: unknown;
  try {
    parsedBody = await request.json();
  } catch {
    return json({ error: "INVALID_SERVICE_DATE" }, 400);
  }
  const parsed = SERVICE_DATE_SCHEMA.safeParse(parsedBody);
  if (!parsed.success || !isRealServiceDate(parsed.data.serviceDate)) {
    return json({ error: "INVALID_SERVICE_DATE" }, 400);
  }

  try {
    return json(await loadBlockedPreview(parsed.data.serviceDate), 200);
  } catch {
    return json({ error: "PREVIEW_UNAVAILABLE" }, 503);
  }
}
