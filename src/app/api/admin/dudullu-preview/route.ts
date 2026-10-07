import { z } from "zod";
import { AppError, requireAdmin } from "@/lib/admin-auth";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { optimizerFetch } from "@/lib/optimizer-server";
import { isRealServiceDate } from "@/services/istanbul-service-date";
import { runDailyPlan } from "@/services/daily-plan-run";

const NO_STORE_HEADERS = { "cache-control": "private, no-store" };
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const ADMISSION_MODES = ["recorded", "assume_confirmed"] as const;
const FLEET_MODES = ["live", "virtual"] as const;
/**
 * Owner decision (2026-10-04): "maximum travel time" is the time a STUDENT stays in the
 * vehicle (`max_ride_time`, demo default 90 min). The vehicle tour (depot -> stops -> depot,
 * `max_travel_time`) only gets an upper bound (default 150 min). Both are adjustable.
 */
const DEFAULT_MAX_RIDE_MINUTES = 90;
const DEFAULT_MAX_TOUR_MINUTES = 150;
const RIDE_LIMIT_RANGE = { min: 15, max: 240 } as const;
const TOUR_LIMIT_RANGE = { min: 30, max: 300 } as const;
const LIMIT_KEYS: ReadonlySet<unknown> = new Set(["maxRideTimeMinutes", "maxTourMinutes"]);
const MODE_KEYS: ReadonlySet<unknown> = new Set(["admissionMode", "fleetMode"]);
const SERVICE_DATE_SCHEMA = z.object({
  serviceDate: z.string().regex(DATE_PATTERN),
  admissionMode: z.enum(ADMISSION_MODES).optional(),
  fleetMode: z.enum(FLEET_MODES).optional(),
  maxRideTimeMinutes: z.number().int().min(RIDE_LIMIT_RANGE.min).max(RIDE_LIMIT_RANGE.max).optional(),
  maxTourMinutes: z.number().int().min(TOUR_LIMIT_RANGE.min).max(TOUR_LIMIT_RANGE.max).optional(),
}).strict();

function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: NO_STORE_HEADERS });
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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
  if (!parsed.success) {
    // A valid body with only a bad mode or limit value gets its own code; everything else keeps
    // the original contract (including rejection of unknown fields).
    const issues = parsed.error.issues;
    const onlyKnownFieldIssues = issues.every(
      (issue) => MODE_KEYS.has(issue.path[0]) || LIMIT_KEYS.has(issue.path[0]),
    );
    const dateOk = isRecord(parsedBody) && typeof parsedBody.serviceDate === "string" &&
      DATE_PATTERN.test(parsedBody.serviceDate) && isRealServiceDate(parsedBody.serviceDate);
    if (!onlyKnownFieldIssues || !dateOk) return json({ error: "INVALID_SERVICE_DATE" }, 400);
    const modeIssue = issues.some((issue) => MODE_KEYS.has(issue.path[0]));
    return json({ error: modeIssue ? "INVALID_MODE" : "INVALID_LIMIT" }, 400);
  }
  if (!isRealServiceDate(parsed.data.serviceDate)) {
    return json({ error: "INVALID_SERVICE_DATE" }, 400);
  }

  try {
    return json(await runDailyPlan({ reader: getSupabaseAdmin(), optimizerFetch, clock: () => new Date() }, {
      serviceDate: parsed.data.serviceDate,
      admissionMode: parsed.data.admissionMode ?? "recorded",
      fleetMode: parsed.data.fleetMode ?? "live",
      maxRideTimeMinutes: parsed.data.maxRideTimeMinutes ?? DEFAULT_MAX_RIDE_MINUTES,
      maxTourMinutes: parsed.data.maxTourMinutes ?? DEFAULT_MAX_TOUR_MINUTES,
    }), 200);
  } catch {
    return json({ error: "PREVIEW_UNAVAILABLE" }, 503);
  }
}
