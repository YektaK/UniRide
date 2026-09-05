import { z } from "zod";
import type { DudulluReadinessReport } from "./dudullu-readiness";

export const DUDULLU_REASON_CODES = [
  "no_dudullu_students",
  "target_profile_incomplete",
  "schedule_classification_incomplete",
  "schedule_data_invalid",
  "no_configured_driver",
  "no_usable_active_vehicle",
  "matrix_unavailable",
  "matrix_stale",
  "matrix_incomplete",
  "matrix_location_mismatch",
] as const;

const count = z.number().int().nonnegative();

export const dudulluReadinessReportSchema = z.object({
  ready: z.boolean(),
  reasonCodes: z.array(z.enum(DUDULLU_REASON_CODES)),
  students: z.object({
    allAccounts: count,
    dudulluTarget: count,
    nonDudulluScheduled: count,
    unclassifiedSchedule: count,
    completeTargetProfiles: count,
    targetMissingLocation: count,
    targetMissingDisabilityType: count,
    scheduleLinkMismatch: count,
    distinctTargetLocations: count,
  }),
  schedules: z.object({
    total: count,
    empty: count,
    malformed: count,
    orphanedRows: count,
    duplicateRowsForStudent: count,
  }),
  fleet: z.object({
    configuredDrivers: count,
    vehicles: count,
    activeVehicles: count,
    usableActiveVehicles: count,
  }),
  matrix: z.object({
    source: z.enum(["supabase", "empty", "coordinates"]),
    loaded: z.boolean(),
    stale: z.boolean(),
    hasError: z.boolean(),
    matrixLocationCount: count,
    complete: z.boolean(),
    ready: z.boolean(),
    requiredLocationCount: count,
    expectedRequiredDirectedArcCount: count,
    validRequiredDirectedArcCount: count,
    missingRequiredLocationCount: count,
    invalidOrMissingRequiredDirectedArcCount: count,
    depotPresent: z.boolean(),
  }),
  historicalExpectation: z.object({
    studentCount: count,
    matrixNodeCount: count,
    matchesStudentCount: z.boolean(),
    matchesMatrixNodeCount: z.boolean(),
  }),
}) satisfies z.ZodType<DudulluReadinessReport>;

export function parseDudulluReadinessReport(input: unknown): DudulluReadinessReport {
  const parsed = dudulluReadinessReportSchema.safeParse(input);
  if (!parsed.success) {
    throw new Error("Invalid Dudullu readiness response");
  }
  return parsed.data;
}
