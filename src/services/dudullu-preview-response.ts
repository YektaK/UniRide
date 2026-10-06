import { z } from "zod";

/**
 * Client-side contract for the POST /api/admin/dudullu-preview response.
 * It mirrors the fields the daily-plan page reads from `DudulluPreviewResult` plus the
 * route's own envelope (modes, labelling, fleet info). Unknown extra keys are dropped.
 * The response carries no student names: display labels are location codes only (K4).
 */
const finite = z.number().finite();
const count = z.number().int().nonnegative();
const direction = z.enum(["pickup", "dropoff"]);

const routeIntervalSchema = z.object({
  jobId: z.string(),
  routeIndex: count,
  vehicleId: z.string(),
  direction,
  startMinutes: finite,
  endMinutes: finite,
  occurrenceIds: z.array(z.string()),
  swCount: count,
  soCount: count,
});

const assignmentSchema = routeIntervalSchema.extend({
  physicalVehicleId: z.string(),
});

const routeStepSchema = z.object({
  location1: z.string(),
  location2: z.string(),
  duration: finite,
  distance: finite,
});

const routeSchema = z.object({
  vehicle_id: z.string(),
  route_details: z.array(routeStepSchema),
  total_duration_minutes: finite,
  sw_count: count,
  so_count: count,
  student_ids: z.array(z.string()),
});

const jobSchema = z.object({
  id: z.string(),
  serviceDate: z.string(),
  direction,
  anchorMinutes: finite,
  result: z.object({
    success: z.boolean(),
    routes: z.array(routeSchema),
  }),
  intervals: z.array(routeIntervalSchema),
});

const vehicleSummarySchema = z.object({
  minimumVehicles: count.nullable(),
  minimumProven: z.boolean(),
  lowerBound: count,
  peakConcurrentRoutes: count,
  activeFleetSize: count,
  routesPerJob: z.array(z.object({
    jobId: z.string(),
    direction,
    anchorMinutes: finite,
    routeCount: count,
    studentCount: count,
  })),
});

export const DUDULLU_PREVIEW_STATUSES = ["preview_ready", "shortage", "blocked_data", "indeterminate"] as const;

export const dudulluPreviewResponseSchema = z.object({
  status: z.enum(DUDULLU_PREVIEW_STATUSES),
  publishable: z.literal(false),
  hypothetical: z.boolean(),
  serviceDate: z.string(),
  admissionMode: z.enum(["recorded", "assume_confirmed"]),
  fleetMode: z.enum(["live", "virtual"]),
  reasonCodes: z.array(z.string()),
  candidateSummary: z.object({
    dudulluStudents: count,
    legsByAdmission: z.record(z.string(), count),
    invalidStudentRecords: count,
  }),
  fleet: z.object({
    mode: z.enum(["live", "virtual"]),
    assignmentFleetSize: count.nullable(),
    liveActiveFleetSize: count.nullable(),
    /** Optional on older responses; identifies the live fleet used by the producer. */
    activeVehicleIds: z.array(z.string()).optional(),
    template: z.object({
      swCapacity: count,
      soCapacity: count,
      cooldownMinutes: count,
    }).nullable(),
    /** Largest Sw / So capacity of the fleet the plan used; absent on older responses. */
    maxCapacity: z.object({
      swCapacity: count,
      soCapacity: count,
    }).nullable().optional(),
  }),
  /** The limits the optimizer was given (minutes); the minimum is set only for an infeasible ride limit. */
  limits: z.object({
    maxRideTimeMinutes: count,
    maxTourMinutes: count,
    minimumFeasibleRideMinutes: count.nullable(),
  }),
  vehicleSummary: vehicleSummarySchema.nullable(),
  jobs: z.array(jobSchema),
  routeIntervals: z.array(routeIntervalSchema),
  assignments: z.array(assignmentSchema),
  hourlyOccupiedVehicles: z.record(z.string(), count),
  occurrenceLabels: z.record(z.string(), z.string()),
});

export type DudulluPreviewResponse = z.infer<typeof dudulluPreviewResponseSchema>;
export type DudulluPreviewJobView = DudulluPreviewResponse["jobs"][number];

/** Throws a ZodError when the payload is not a usable preview response. */
export function parseDudulluPreviewResponse(value: unknown): DudulluPreviewResponse {
  return dudulluPreviewResponseSchema.parse(value);
}
