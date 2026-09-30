/**
 * API Route: Student Ride Confirmation
 * POST /api/ride-confirmation
 * GET  /api/ride-confirmation?date=YYYY-MM-DD
 * 
 * Handles student confirmation/cancellation for next-day rides.
 * Requires JWT authentication — userId is extracted from the token.
 */

import { z } from "zod";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { getCurrentUserFromRequest } from "@/lib/admin-auth";
import { classifyScheduleDecision, isBlockingLegacyRequestStatus, isDudulluCampus, serviceDayOfWeek, type StudentLegDecision, type TripDirection } from "@/services/daily-planning";
import { isRealServiceDate, serviceDateBounds } from "@/services/istanbul-service-date";
import type { DbStudentLegDecision } from "@/types/db";

const dateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const directionalSchema = z.object({
  action: z.enum(["confirm", "cancel"]),
  rideDate: dateSchema,
  direction: z.enum(["pickup", "dropoff"]),
  flexibilityMinutes: z.number().int().min(0).max(1439).default(0),
}).strict();
const changeSchema = z.object({
  action: z.literal("change"),
  rideDate: dateSchema,
  pickupTime: z.string().optional(),
  dropoffTime: z.string().optional(),
  notes: z.string().optional(),
}).strict();
const postSchema = z.union([directionalSchema, changeSchema]);
const headers = { "cache-control": "private, no-store" };

function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers });
}

function pendingLeg() {
  return { decision: "pending", admission: "pending_student_confirmation" } as const;
}

function legView(row: DbStudentLegDecision | undefined, serviceDate: string) {
  if (!row) return pendingLeg();
  const decision: StudentLegDecision = row.decision === "confirmed"
    ? { status: "confirmed", confirmedAt: row.decided_at, flexibilityMinutes: row.flexibility_minutes }
    : { status: "cancelled", decidedAt: row.decided_at };
  return { decision: row.decision, admission: classifyScheduleDecision(decision, serviceDate).admission };
}

export async function POST(request: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return json({ error: "INVALID_REQUEST" }, 400);
  }
  const parsed = postSchema.safeParse(body);
  if (!parsed.success || !isRealServiceDate(parsed.data.rideDate)) {
    return json({ error: "INVALID_REQUEST" }, 400);
  }

  try {
    const authUser = await getCurrentUserFromRequest(request);
    if (!authUser) return json({ error: "AUTH_REQUIRED" }, 401);
    if (authUser.role !== "student") return json({ error: "STUDENT_REQUIRED" }, 403);

    const { rideDate, action } = parsed.data;
    const client = getSupabaseAdmin();
    const { data: userRaw, error: userError } = await client.from("users")
      .select("weekly_schedule_id").eq("id", authUser.id).maybeSingle();
    if (userError) throw userError;
    const user = userRaw as { weekly_schedule_id: string | null } | null;
    if (!user?.weekly_schedule_id) return json({ error: "NO_DUDULLU_SERVICE" }, 409);

    const { data: scheduleRaw, error: scheduleError } = await client.from("weekly_schedules")
      .select("user_id, entries").eq("id", user.weekly_schedule_id).maybeSingle();
    if (scheduleError) throw scheduleError;
    const schedule = scheduleRaw as { user_id: string; entries: unknown } | null;
    const entries = schedule?.entries;
    const eligible = schedule?.user_id === authUser.id && Array.isArray(entries) && entries.some((entry) =>
      entry && typeof entry === "object" && entry.dayOfWeek === serviceDayOfWeek(rideDate) &&
      typeof entry.location === "string" && isDudulluCampus(entry.location));
    if (!eligible) return json({ error: "NO_DUDULLU_SERVICE" }, 409);

    if (action === "change") {
      const { start, end } = serviceDateBounds(rideDate);
      const { data: rideRaw, error: readError } = await client.from("ride_requests")
        .select("id, notes").eq("user_id", authUser.id)
        .gte("requested_pickup_time", start).lt("requested_pickup_time", end).maybeSingle();
      if (readError) throw readError;
      const ride = rideRaw as { id: string; notes: string | null } | null;
      if (!ride) return json({ error: "RIDE_NOT_FOUND" }, 404);
      const { data: updated, error: updateError } = await client.from("ride_requests")
        .update({ status: "pending_admin_approval", notes: parsed.data.notes ?? ride.notes, updated_at: new Date().toISOString() } as never)
        .eq("id", ride.id).eq("user_id", authUser.id).select().single();
      if (updateError) throw updateError;
      return json({ success: true, action, status: "pending_admin_approval", ride: updated,
        message: "Değişiklik talebiniz yönetici onayına gönderildi." }, 200);
    }

    const { direction, flexibilityMinutes } = parsed.data;
    const decision = action === "confirm" ? "confirmed" : "cancelled";
    const flexibility = action === "confirm" ? flexibilityMinutes : 0;
    const { data: existingRaw, error: readError } = await client.from("student_leg_decisions")
      .select("decision, flexibility_minutes").eq("user_id", authUser.id)
      .eq("service_date", rideDate).eq("direction", direction).maybeSingle();
    if (readError) throw readError;
    const existing = existingRaw as Pick<DbStudentLegDecision, "decision" | "flexibility_minutes"> | null;
    if (existing?.decision !== decision || existing.flexibility_minutes !== flexibility) {
      const { error: writeError } = await client.from("student_leg_decisions").upsert({
        user_id: authUser.id,
        service_date: rideDate,
        direction,
        decision,
        flexibility_minutes: flexibility,
      } as never, { onConflict: "user_id,service_date,direction" });
      if (writeError) throw writeError;
    }
    return json({ success: true, direction, decision }, 200);
  } catch {
    return json({ error: "CONFIRMATION_UNAVAILABLE" }, 503);
  }
}

export async function GET(request: Request): Promise<Response> {
  const date = new URL(request.url).searchParams.get("date");
  if (!date || !isRealServiceDate(date)) return json({ error: "INVALID_SERVICE_DATE" }, 400);

  try {
    const authUser = await getCurrentUserFromRequest(request);
    if (!authUser) return json({ error: "AUTH_REQUIRED" }, 401);
    if (authUser.role !== "student") return json({ error: "STUDENT_REQUIRED" }, 403);

    const client = getSupabaseAdmin();
    const { data: decisions, error: decisionError } = await client.from("student_leg_decisions")
      .select("direction, decision, decided_at, flexibility_minutes")
      .eq("user_id", authUser.id).eq("service_date", date);
    if (decisionError || !Array.isArray(decisions)) throw new Error("decision read failed");

    const { start, end } = serviceDateBounds(date);
    const { data: legacy, error: legacyError } = await client.from("ride_requests")
      .select("status").eq("user_id", authUser.id)
      .or(`and(requested_pickup_time.gte.${start},requested_pickup_time.lt.${end}),` +
        `and(requested_dropoff_time.gte.${start},requested_dropoff_time.lt.${end})`);
    if (legacyError || !Array.isArray(legacy)) throw new Error("legacy read failed");

    const rows = decisions as DbStudentLegDecision[];
    const byDirection = (direction: TripDirection) => rows.find((row) => row.direction === direction);
    return json({
      legs: {
        pickup: legView(byDirection("pickup"), date),
        dropoff: legView(byDirection("dropoff"), date),
      },
      legacyBlocker: (legacy as Array<{ status: string }>).some((row) => isBlockingLegacyRequestStatus(row.status)),
    }, 200);
  } catch {
    return json({ error: "CONFIRMATION_UNAVAILABLE" }, 503);
  }
}
