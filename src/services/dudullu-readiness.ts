import { isDudulluCampus } from "./daily-planning";

export interface ReadinessStudentInput {
  id: string;
  role: string;
  locationCode?: string;
  disabilityType?: string;
  weeklyScheduleId?: string;
}

export interface ReadinessScheduleInput {
  id: string;
  userId: string;
  entries: unknown;
}

export interface ReadinessVehicleInput {
  status: string;
  wheelchairCapacity: number;
  seatingCapacity: number;
}

export interface ReadinessMatrixSummary {
  source: "supabase" | "empty" | "coordinates";
  loaded: boolean;
  stale: boolean;
  hasError: boolean;
  matrixLocationCount: number;
  requiredLocationCount: number;
  missingRequiredLocationCount: number;
  expectedRequiredDirectedArcCount: number;
  validRequiredDirectedArcCount: number;
  invalidOrMissingRequiredDirectedArcCount: number;
  depotPresent: boolean;
  complete: boolean;
  ready: boolean;
}

export interface DudulluReadinessReport {
  ready: boolean;
  reasonCodes: readonly string[];
  students: {
    allAccounts: number;
    dudulluTarget: number;
    nonDudulluScheduled: number;
    unclassifiedSchedule: number;
    completeTargetProfiles: number;
    targetMissingLocation: number;
    targetMissingDisabilityType: number;
    scheduleLinkMismatch: number;
    distinctTargetLocations: number;
  };
  schedules: {
    total: number;
    empty: number;
    malformed: number;
    orphanedRows: number;
    duplicateRowsForStudent: number;
  };
  fleet: {
    configuredDrivers: number;
    vehicles: number;
    activeVehicles: number;
    usableActiveVehicles: number;
  };
  matrix: {
    source: "supabase" | "empty" | "coordinates";
    loaded: boolean;
    stale: boolean;
    hasError: boolean;
    matrixLocationCount: number;
    complete: boolean;
    ready: boolean;
    requiredLocationCount: number;
    expectedRequiredDirectedArcCount: number;
    validRequiredDirectedArcCount: number;
    missingRequiredLocationCount: number;
    invalidOrMissingRequiredDirectedArcCount: number;
    depotPresent: boolean;
  };
  historicalExpectation: {
    studentCount: number;
    matrixNodeCount: number;
    matchesStudentCount: boolean;
    matchesMatrixNodeCount: boolean;
  };
}

const DUDULLU_HISTORICAL_STUDENT_EXPECTATION = 28;
const DUDULLU_HISTORICAL_MATRIX_NODE_EXPECTATION = 29;

function roleOf(user: ReadinessStudentInput): "student" | "driver" | "unknown" {
  switch (user.role.trim().toLocaleLowerCase("tr-TR")) {
    case "student":
      return "student";
    case "driver":
      return "driver";
    default:
      return "unknown";
  }
}

function isFiniteNonNegative(value: unknown): boolean {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function vehicleTotalCapacity(vehicle: ReadinessVehicleInput): number {
  if (!isFiniteNonNegative(vehicle.wheelchairCapacity)) {
    return 0;
  }
  if (!isFiniteNonNegative(vehicle.seatingCapacity)) {
    return 0;
  }
  return vehicle.wheelchairCapacity + vehicle.seatingCapacity;
}

interface StudentRecord {
  id: string;
  role: "student" | "driver" | "unknown";
  homeCode?: string;
  disabilityEnumerated: boolean;
  schedule?: ReadinessScheduleInput;
  linkMismatch: boolean;
  entriesMalformed: boolean;
  target: boolean;
}

function normalizedDisability(value: unknown): "Sw" | "So" | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  if (trimmed === "Sw" || trimmed === "So") {
    return trimmed;
  }
  return undefined;
}

function buildStudentRecords(
  users: readonly ReadinessStudentInput[],
  schedulesById: ReadonlyMap<string, ReadinessScheduleInput>,
): StudentRecord[] {
  const records: StudentRecord[] = [];

  for (const user of users) {
    const role = roleOf(user);
    if (role !== "student") {
      continue;
    }

    const location =
      typeof user.locationCode === "string" && user.locationCode.trim() !== ""
        ? user.locationCode!.trim()
        : undefined;

    const scheduleId =
      typeof user.weeklyScheduleId === "string" && user.weeklyScheduleId.trim() !== ""
        ? user.weeklyScheduleId.trim()
        : undefined;
    const schedule = scheduleId ? schedulesById.get(scheduleId) : undefined;

    const entriesValidArray =
      schedule !== undefined && flattenEntriesTrimmed(schedule) !== undefined;

    const record: StudentRecord = {
      id: user.id,
      role,
      homeCode: location,
      disabilityEnumerated: normalizedDisability(user.disabilityType) !== undefined,
      schedule,
      linkMismatch: schedule !== undefined && schedule.userId !== user.id,
      entriesMalformed: schedule !== undefined && !entriesValidArray,
      target: false,
    };
    record.target =
      record.schedule !== undefined &&
      !record.linkMismatch &&
      !record.entriesMalformed &&
      hasDudulluEntry(record);

    records.push(record);
  }

  return records;
}

function hasDudulluEntry(record: StudentRecord): boolean {
  const schedule = record.schedule;
  if (!schedule) {
    return false;
  }
  const entries = flattenEntriesTrimmed(schedule);
  if (!entries) {
    return false;
  }
  return entries.some((entry) => isDudulluCampus(entry));
}

function flattenEntriesTrimmed(
  schedule: ReadinessScheduleInput,
): readonly string[] | undefined {
  if (!Array.isArray(schedule.entries)) {
    return undefined;
  }
  const locations: string[] = [];
  for (const entry of schedule.entries) {
    if (typeof entry !== "object" || entry === null) {
      return undefined;
    }
    const location = (entry as { location?: unknown }).location;
    if (typeof location !== "string" || location.trim() === "") {
      return undefined;
    }
    locations.push(location.trim());
  }
  return locations;
}

export function requiredDudulluStudentLocations(
  users: readonly ReadinessStudentInput[],
  schedules: readonly ReadinessScheduleInput[],
): readonly string[] {
  const schedulesById = indexSchedules(schedules);
  const records = buildStudentRecords(users, schedulesById);
  const homeCodes = new Set<string>();

  for (const record of records) {
    if (record.target && record.homeCode !== undefined) {
      homeCodes.add(record.homeCode);
    }
  }

  return [...homeCodes];
}

function indexSchedules(
  schedules: readonly ReadinessScheduleInput[],
): Map<string, ReadinessScheduleInput> {
  const byId = new Map<string, ReadinessScheduleInput>();
  for (const schedule of schedules) {
    if (typeof schedule.id === "string" && schedule.id.trim() !== "") {
      const id = schedule.id.trim();
      if (!byId.has(id)) {
        byId.set(id, schedule);
      }
    }
  }
  return byId;
}

export function analyzeDudulluReadiness(
  users: readonly ReadinessStudentInput[],
  schedules: readonly ReadinessScheduleInput[],
  vehicles: readonly ReadinessVehicleInput[],
  matrix: ReadinessMatrixSummary,
): DudulluReadinessReport {
  const schedulesById = indexSchedules(schedules);
  const records = buildStudentRecords(users, schedulesById);

  const report: DudulluReadinessReport = {
    ready: true,
    reasonCodes: [],
    students: {
      allAccounts: 0,
      dudulluTarget: 0,
      nonDudulluScheduled: 0,
      unclassifiedSchedule: 0,
      completeTargetProfiles: 0,
      targetMissingLocation: 0,
      targetMissingDisabilityType: 0,
      scheduleLinkMismatch: 0,
      distinctTargetLocations: 0,
    },
    schedules: {
      total: schedules.length,
      empty: 0,
      malformed: 0,
      orphanedRows: 0,
      duplicateRowsForStudent: 0,
    },
    fleet: {
      configuredDrivers: 0,
      vehicles: vehicles.length,
      activeVehicles: 0,
      usableActiveVehicles: 0,
    },
    matrix: {
      source: matrix.source,
      loaded: matrix.loaded,
      stale: matrix.stale,
      hasError: matrix.hasError,
      matrixLocationCount: matrix.matrixLocationCount,
      complete: matrix.complete,
      ready: matrix.ready,
      requiredLocationCount: matrix.requiredLocationCount,
      expectedRequiredDirectedArcCount: matrix.expectedRequiredDirectedArcCount,
      validRequiredDirectedArcCount: matrix.validRequiredDirectedArcCount,
      missingRequiredLocationCount: matrix.missingRequiredLocationCount,
      invalidOrMissingRequiredDirectedArcCount:
        matrix.invalidOrMissingRequiredDirectedArcCount,
      depotPresent: matrix.depotPresent,
    },
    historicalExpectation: {
      studentCount: DUDULLU_HISTORICAL_STUDENT_EXPECTATION,
      matrixNodeCount: DUDULLU_HISTORICAL_MATRIX_NODE_EXPECTATION,
      matchesStudentCount: false,
      matchesMatrixNodeCount: false,
    },
  };

  const targetLocations = new Set<string>();
  const studentIds = new Set<string>();
  for (const user of users) {
    if (roleOf(user) === "driver") {
      report.fleet.configuredDrivers += 1;
    }
    if (roleOf(user) === "student") {
      studentIds.add(user.id);
      report.students.allAccounts += 1;
    }
  }

  for (const record of records) {
    if (record.target) {
      report.students.dudulluTarget += 1;
      if (record.homeCode !== undefined) {
        targetLocations.add(record.homeCode);
      }
      if (record.homeCode === undefined) {
        report.students.targetMissingLocation += 1;
      }
      if (!record.disabilityEnumerated) {
        report.students.targetMissingDisabilityType += 1;
      }
      if (record.homeCode !== undefined && record.disabilityEnumerated) {
        report.students.completeTargetProfiles += 1;
      }
    }

    if (record.linkMismatch) {
      report.students.scheduleLinkMismatch += 1;
      report.students.unclassifiedSchedule += 1;
    } else if (record.entriesMalformed) {
      report.schedules.malformed += 1;
      report.students.unclassifiedSchedule += 1;
    } else if (record.schedule === undefined) {
      report.students.unclassifiedSchedule += 1;
    } else {
      const entries = flattenEntriesTrimmed(record.schedule);
      if (entries === undefined) {
        report.schedules.malformed += 1;
        report.students.unclassifiedSchedule += 1;
      } else if (entries.length === 0) {
        report.schedules.empty += 1;
        report.students.nonDudulluScheduled += 1;
      } else if (!record.target) {
        report.students.nonDudulluScheduled += 1;
      }
    }
  }

  report.students.distinctTargetLocations = targetLocations.size;

  const seenStudentRows = new Set<string>();
  for (const schedule of schedules) {
    if (!studentIds.has(schedule.userId)) {
      report.schedules.orphanedRows += 1;
      continue;
    }
    if (seenStudentRows.has(schedule.userId)) {
      report.schedules.duplicateRowsForStudent += 1;
    } else {
      seenStudentRows.add(schedule.userId);
    }
  }

  for (const vehicle of vehicles) {
    if (vehicle.status.trim().toLocaleLowerCase("tr-TR") === "active") {
      report.fleet.activeVehicles += 1;
      if (vehicleTotalCapacity(vehicle) > 0) {
        report.fleet.usableActiveVehicles += 1;
      }
    }
  }

  const studentComparison = report.students.dudulluTarget;
  report.historicalExpectation.matchesStudentCount =
    studentComparison === DUDULLU_HISTORICAL_STUDENT_EXPECTATION;
  report.historicalExpectation.matchesMatrixNodeCount =
    matrix.matrixLocationCount === DUDULLU_HISTORICAL_MATRIX_NODE_EXPECTATION;

  const reasons: string[] = [];

  if (report.students.dudulluTarget === 0) {
    reasons.push("no_dudullu_students");
  }
  if (
    report.students.dudulluTarget > 0 &&
    report.students.completeTargetProfiles !== report.students.dudulluTarget
  ) {
    reasons.push("target_profile_incomplete");
  }
  if (report.students.unclassifiedSchedule > 0) {
    reasons.push("schedule_classification_incomplete");
  }
  if (
    report.schedules.malformed > 0 ||
    report.schedules.orphanedRows > 0 ||
    report.schedules.duplicateRowsForStudent > 0
  ) {
    reasons.push("schedule_data_invalid");
  }
  if (report.fleet.configuredDrivers === 0) {
    reasons.push("no_configured_driver");
  }
  if (report.fleet.usableActiveVehicles === 0) {
    reasons.push("no_usable_active_vehicle");
  }

  const matrixAvailable = matrix.source === "supabase" && matrix.loaded && !matrix.hasError;
  if (!matrixAvailable) {
    reasons.push("matrix_unavailable");
  } else {
    if (matrix.stale) {
      reasons.push("matrix_stale");
    }
    if (!matrix.complete || !matrix.ready) {
      reasons.push("matrix_incomplete");
    }
  }
  if (
    matrix.requiredLocationCount !== targetLocations.size + 1 ||
    matrix.missingRequiredLocationCount !== 0 ||
    matrix.invalidOrMissingRequiredDirectedArcCount !== 0
  ) {
    reasons.push("matrix_location_mismatch");
  }

  report.ready = reasons.length === 0;
  report.reasonCodes = reasons;

  return report;
}