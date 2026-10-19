import { z } from "zod";
import type { FleetScenarioDay, ScenarioResult } from "./fleet-scenario-run";
import { scenarioName, FLEET_ARCHIVE_FORMAT, extendedFleetManifestSchema } from "./fleet-scenario-report";

// Extended archive of the WP-E10 fleet re-run (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 9, rule (f)).
// Pure functions: the CLI writes what these return, after the usual anonymisation. Types only come from the run
// module, so this file has no `server-only` dependency.

export { FLEET_ARCHIVE_FORMAT, extendedFleetManifestSchema };

const stepSchema = z.object({ location1: z.string(), location2: z.string(), duration: z.number() });
const routeSchema = z.object({
  routeIndex: z.number().int().nonnegative(), vehicleId: z.string(), vehicleType: z.string().nullable(),
  steps: z.array(stepSchema).min(2), studentIds: z.array(z.string()),
  swCount: z.number().int().nonnegative(), soCount: z.number().int().nonnegative(), totalDurationMinutes: z.number(),
  minutes: z.number().nullable(), profileError: z.string().nullable(), rideMinutes: z.array(z.number()),
  interval: z.object({
    startMinutes: z.number(), endMinutes: z.number(), occurrenceIds: z.array(z.string()).min(1),
  }).nullable(),
});
const optionSchema = z.object({
  optionId: z.string().min(1), kind: z.enum(["baseline", "quota"]), quota: z.number().int().nullable(),
  status: z.enum(["included", "skipped_infeasible", "skipped_duplicate", "skipped_invalid", "skipped_http_error"]),
  reason: z.string().nullable(), routeCount: z.number().int().nullable(),
  success: z.boolean().nullable(), certificate: z.unknown(), error: z.string().nullable(),
  totalDurationMinutes: z.number().nullable(), routes: z.array(routeSchema),
}).superRefine((option, ctx) => {
  const fail = (message: string) => ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${option.optionId}: ${message}` });
  const answered = option.status === "included" || option.status === "skipped_duplicate" || option.status === "skipped_infeasible";
  // Every option the optimizer answered keeps the certificate of that answer, also a skipped one.
  if (answered && (option.certificate === null || option.certificate === undefined)) fail("certificate missing");
  if (option.status === "included" || option.status === "skipped_duplicate") {
    if (option.success !== true) fail("success must be true");
    if (option.routes.length === 0) fail("routes missing");
    if (option.routes.some((route) => route.interval === null)) fail("interval missing");
    if (option.routes.some((route) => route.minutes === null)) fail("minutes missing");
  }
  if (option.status === "skipped_infeasible" && (option.success !== false || option.routes.length > 0)) fail("infeasible option must carry no routes");
  if (option.status === "skipped_http_error" && option.error === null) fail("error missing");
});
const waveSchema = z.object({
  waveId: z.string().min(1), direction: z.enum(["pickup", "dropoff"]), anchorMinutes: z.number(), legs: z.number().int(),
  options: z.array(optionSchema).min(1),
});
const matrixSchema = z.object({ id: z.string(), version: z.string(), sha256: z.string(), source: z.string() });

/** One file per (date, R): every menu option of every wave. */
export const menuArchiveSchema = z.object({
  format: z.literal(FLEET_ARCHIVE_FORMAT), kind: z.literal("menu_options"),
  serviceDate: z.string(), rideLimit: z.number(),
  limits: z.object({ maxRideTimeMinutes: z.number(), maxTourMinutes: z.number() }),
  matrix: matrixSchema,
  /** Needed by the anonymiser; maps occurrence id to location code. */
  occurrenceLabels: z.record(z.string(), z.string()),
  waves: z.array(waveSchema).min(1),
});
export type MenuArchive = z.infer<typeof menuArchiveSchema>;

/** One file per (date, R, L): the exact /internal/fleet-selection request body and its response. */
export const selectionArchiveSchema = z.object({
  format: z.literal(FLEET_ARCHIVE_FORMAT), kind: z.literal("selection_exchange"),
  serviceDate: z.string(), rideLimit: z.number(), largeLimit: z.number().int().nonnegative(),
  occurrenceLabels: z.record(z.string(), z.string()),
  request: z.custom<unknown>((value) => value !== undefined && value !== null),
  httpStatus: z.number().int().nullable(),
  response: z.unknown(),
});
export type SelectionArchive = z.infer<typeof selectionArchiveSchema>;

export const menuArchiveName = (stem: string) => `${stem}.menu_options.json`;
export const selectionArchiveName = (stem: string, scenario: ScenarioResult["scenario"]) => `${stem}_${scenarioName(scenario)}.selection_exchange.json`;

export function menuArchive(day: FleetScenarioDay, ride: number): unknown {
  if (day.matrix === null) throw new Error("A menu archive needs the matrix snapshot of the day");
  return {
    format: FLEET_ARCHIVE_FORMAT, kind: "menu_options", serviceDate: day.serviceDate, rideLimit: ride, limits: day.limits,
    matrix: { id: day.matrix.id, version: day.matrix.version, sha256: day.matrix.sha256, source: day.matrix.source },
    occurrenceLabels: day.occurrenceLabels, waves: day.menuDetail,
  };
}

export function selectionArchive(day: FleetScenarioDay, ride: number, result: ScenarioResult): unknown {
  if (result.scenario === "A" || result.selectionExchange === null) throw new Error("No selection exchange for this scenario");
  return {
    format: FLEET_ARCHIVE_FORMAT, kind: "selection_exchange", serviceDate: day.serviceDate, rideLimit: ride, largeLimit: result.scenario,
    occurrenceLabels: day.occurrenceLabels, request: result.selectionExchange.request,
    httpStatus: result.selectionExchange.httpStatus, response: result.selectionExchange.response,
  };
}
