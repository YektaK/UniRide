import type { DudulluPreviewResponse } from "./dudullu-preview-response";

type Response = DudulluPreviewResponse;
type Job = Response["jobs"][number];

const step = (location1: string, location2: string, duration: number) => ({
  location1,
  location2,
  duration,
  distance: duration / 2,
});

/**
 * Test fixtures for the daily-plan view model and page. Shaped like a real
 * /api/admin/dudullu-preview response: location codes only, no student names.
 * Morning wave 08:45 has two routes, the evening wave 17:00 one.
 */
export const PICKUP_ANCHOR = 8 * 60 + 45;
export const DROPOFF_ANCHOR = 17 * 60;

export function makeJobs(): Job[] {
  const pickup: Job = {
    id: "2026-10-05:pickup:525",
    serviceDate: "2026-10-05",
    direction: "pickup",
    anchorMinutes: PICKUP_ANCHOR,
    result: {
      success: true,
      routes: [
        {
          vehicle_id: "virtual:4-10-10:1",
          route_details: [
            step("D.Kampus", "So1", 10),
            step("So1", "Sw2", 5),
            step("Sw2", "D.Kampus", 12),
          ],
          total_duration_minutes: 27,
          sw_count: 1,
          so_count: 1,
          student_ids: ["occ-a", "occ-b"],
        },
        {
          vehicle_id: "virtual:4-10-10:2",
          route_details: [
            step("D.Kampus", "So3#occ-c", 10),
            step("So3#occ-c", "D.Kampus", 10),
          ],
          total_duration_minutes: 20,
          sw_count: 0,
          so_count: 1,
          student_ids: ["occ-c"],
        },
      ],
    },
    intervals: [
      {
        jobId: "2026-10-05:pickup:525", routeIndex: 0, vehicleId: "virtual:4-10-10:1", direction: "pickup",
        startMinutes: 498, endMinutes: 525, occurrenceIds: ["occ-a", "occ-b"], swCount: 1, soCount: 1,
      },
      {
        jobId: "2026-10-05:pickup:525", routeIndex: 1, vehicleId: "virtual:4-10-10:2", direction: "pickup",
        startMinutes: 505, endMinutes: 525, occurrenceIds: ["occ-c"], swCount: 0, soCount: 1,
      },
    ],
  };
  const dropoff: Job = {
    id: "2026-10-05:dropoff:1020",
    serviceDate: "2026-10-05",
    direction: "dropoff",
    anchorMinutes: DROPOFF_ANCHOR,
    result: {
      success: true,
      routes: [
        {
          vehicle_id: "virtual:4-10-10:1",
          route_details: [step("D.Kampus", "Sw4", 8), step("Sw4", "D.Kampus", 8)],
          total_duration_minutes: 16,
          sw_count: 1,
          so_count: 0,
          student_ids: ["occ-d"],
        },
      ],
    },
    intervals: [
      {
        jobId: "2026-10-05:dropoff:1020", routeIndex: 0, vehicleId: "virtual:4-10-10:1", direction: "dropoff",
        startMinutes: 1020, endMinutes: 1036, occurrenceIds: ["occ-d"], swCount: 1, soCount: 0,
      },
    ],
  };
  return [pickup, dropoff];
}

const baseResponse = (): Response => ({
  status: "preview_ready",
  publishable: false,
  hypothetical: true,
  serviceDate: "2026-10-05",
  admissionMode: "assume_confirmed",
  fleetMode: "virtual",
  reasonCodes: ["ADMISSION_ASSUMED"],
  candidateSummary: {
    dudulluStudents: 4,
    legsByAdmission: {
      confirmed: 4, approved: 0, pending_student_confirmation: 0, pending_admin_approval: 0, cancelled: 0,
    },
    invalidStudentRecords: 0,
  },
  fleet: {
    mode: "virtual",
    assignmentFleetSize: 4,
    liveActiveFleetSize: 1,
    template: { swCapacity: 4, soCapacity: 10, cooldownMinutes: 10 },
    maxCapacity: { swCapacity: 4, soCapacity: 10 },
  },
  limits: { maxRideTimeMinutes: 90, maxTourMinutes: 150, minimumFeasibleRideMinutes: null },
  vehicleSummary: {
    minimumVehicles: 2,
    minimumProven: true,
    lowerBound: 2,
    peakConcurrentRoutes: 2,
    activeFleetSize: 4,
    routesPerJob: [
      { jobId: "2026-10-05:pickup:525", direction: "pickup", anchorMinutes: PICKUP_ANCHOR, routeCount: 2, studentCount: 3 },
      { jobId: "2026-10-05:dropoff:1020", direction: "dropoff", anchorMinutes: DROPOFF_ANCHOR, routeCount: 1, studentCount: 1 },
    ],
  },
  jobs: makeJobs(),
  routeIntervals: makeJobs().flatMap((job) => job.intervals),
  assignments: [
    {
      jobId: "2026-10-05:pickup:525", routeIndex: 0, vehicleId: "virtual:4-10-10:1", direction: "pickup",
      startMinutes: 498, endMinutes: 525, occurrenceIds: ["occ-a", "occ-b"], swCount: 1, soCount: 1,
      physicalVehicleId: "virtual:4-10-10:2",
    },
    {
      jobId: "2026-10-05:pickup:525", routeIndex: 1, vehicleId: "virtual:4-10-10:2", direction: "pickup",
      startMinutes: 505, endMinutes: 525, occurrenceIds: ["occ-c"], swCount: 0, soCount: 1,
      physicalVehicleId: "virtual:4-10-10:1",
    },
    {
      jobId: "2026-10-05:dropoff:1020", routeIndex: 0, vehicleId: "virtual:4-10-10:1", direction: "dropoff",
      startMinutes: 1020, endMinutes: 1036, occurrenceIds: ["occ-d"], swCount: 1, soCount: 0,
      physicalVehicleId: "virtual:4-10-10:2",
    },
  ],
  hourlyOccupiedVehicles: { "08:00": 2, "17:00": 1 },
  occurrenceLabels: { "occ-a": "So1", "occ-b": "Sw2", "occ-c": "So3", "occ-d": "Sw4" },
});

/** preview_ready: 2 vehicles for 3 routes, one live vehicle. */
export function readyResponse(): Response {
  return baseResponse();
}

/**
 * Shaped like the 2026-10-05 live run: the 08:45 wave carries 20 students (5 Sw, 15 So), so seat
 * capacity (Sw 4 / So 10) alone needs 2 vehicles. `neededVehicles` is what the assignment proved.
 */
export function peakWaveResponse(neededVehicles = 3): Response {
  const response = baseResponse();
  const counts = [[2, 5], [2, 5], [1, 5]] as const;
  const [pickup, dropoff] = response.jobs;
  const routes = counts.map(([sw, so], index) => ({
    vehicle_id: `virtual:4-10-10:${index + 1}`,
    route_details: [step("D.Kampus", "So1", 10), step("So1", "D.Kampus", 10)],
    total_duration_minutes: 20,
    sw_count: sw,
    so_count: so,
    student_ids: [],
  }));
  return {
    ...response,
    jobs: [{ ...pickup, result: { ...pickup.result, routes }, intervals: [] }, dropoff],
    assignments: [],
    vehicleSummary: { ...response.vehicleSummary!, minimumVehicles: neededVehicles, lowerBound: 2 },
  };
}

/** Assignment search did not finish: the vehicle count is only an upper bound. */
export function indeterminateResponse(): Response {
  const response = baseResponse();
  return {
    ...response,
    status: "indeterminate",
    reasonCodes: ["ADMISSION_ASSUMED", "ASSIGNMENT_SEARCH_INDETERMINATE"],
    vehicleSummary: { ...response.vehicleSummary!, minimumVehicles: 3, minimumProven: false },
  };
}

/** Live fleet cannot cover the routes: no assignment, jobs kept. */
export function shortageResponse(): Response {
  const response = baseResponse();
  return {
    ...response,
    status: "shortage",
    admissionMode: "recorded",
    fleetMode: "live",
    hypothetical: false,
    reasonCodes: ["FLEET_SHORTAGE"],
    fleet: { mode: "live", assignmentFleetSize: 1, liveActiveFleetSize: 1, template: null },
    assignments: [],
    hourlyOccupiedVehicles: {},
    vehicleSummary: { ...response.vehicleSummary!, minimumVehicles: null, minimumProven: false, lowerBound: 2, activeFleetSize: 1 },
  };
}

/** Blocked before any plan exists (for example the travel-time matrix is missing). */
export function blockedResponse(reasonCodes: string[] = ["MATRIX_UNAVAILABLE"]): Response {
  const response = baseResponse();
  return {
    ...response,
    status: "blocked_data",
    reasonCodes,
    jobs: [],
    routeIntervals: [],
    assignments: [],
    hourlyOccupiedVehicles: {},
    vehicleSummary: null,
    fleet: { mode: "virtual", assignmentFleetSize: null, liveActiveFleetSize: 2, template: null },
  };
}

/** The solver did not compute a suitable route within the ride limit. */
export function rideLimitInfeasibleResponse(): Response {
  const response = blockedResponse(["ADMISSION_ASSUMED", "RIDE_TIME_LIMIT_INFEASIBLE"]);
  return { ...response, limits: { maxRideTimeMinutes: 15, maxTourMinutes: 150, minimumFeasibleRideMinutes: null } };
}

/** A day with no admitted trip. */
export function emptyDayResponse(): Response {
  const response = baseResponse();
  return {
    ...response,
    status: "blocked_data",
    reasonCodes: ["ADMISSION_ASSUMED", "NO_ADMITTED_DEMAND"],
    candidateSummary: {
      dudulluStudents: 0,
      legsByAdmission: {
        confirmed: 0, approved: 0, pending_student_confirmation: 0, pending_admin_approval: 0, cancelled: 0,
      },
      invalidStudentRecords: 0,
    },
    jobs: [],
    routeIntervals: [],
    assignments: [],
    hourlyOccupiedVehicles: {},
    vehicleSummary: null,
    occurrenceLabels: {},
    fleet: { mode: "virtual", assignmentFleetSize: null, liveActiveFleetSize: null, template: null },
  };
}
