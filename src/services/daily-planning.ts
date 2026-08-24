import type { ScheduleEntry } from "@/types";

export type TripDirection = "pickup" | "dropoff";
export type DemandSource = "schedule" | "student_exception" | "admin_override";
export type DemandAdmission =
  | "pending_student_confirmation"
  | "confirmed"
  | "pending_admin_approval"
  | "approved"
  | "cancelled";

export type StudentLegDecision =
  | { readonly status: "pending"; readonly flexibilityMinutes?: number }
  | {
      readonly status: "confirmed";
      readonly confirmedAt: string;
      readonly flexibilityMinutes?: number;
    }
  | { readonly status: "cancelled"; readonly decidedAt: string };

export interface DailyPlanningSettings {
  readonly campusCode: "D.Kampus";
  readonly timezone: "Europe/Istanbul";
  readonly pickupArrivalBufferMinutes: number;
  readonly dropoffDepartureBufferMinutes: number;
  readonly confirmationCutoffHour: number;
  readonly exceptionLeadMinutes: number;
}


export interface DailyTripDemand {
  readonly occurrenceId: string;
  readonly studentId: string;
  readonly locationCode: string;
  readonly campusCode: "D.Kampus";
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly source: DemandSource;
  readonly admission: DemandAdmission;
  readonly classBoundaryMinutes: number;
  readonly waveKey: string;
  readonly anchorGroupKey: string;
  readonly anchorMinutes: number;
  readonly hardReadyMinutes?: number;
  readonly hardDeadlineMinutes?: number;
  readonly flexibilityMinutes: number;
  readonly emergencyException: boolean;
}

export interface ExcludedScheduleEntry {
  readonly entryId: string;
  readonly location?: string;
  readonly reason: "other_campus" | "missing_campus";
}

export interface BuildScheduleDemandsInput {
  readonly studentId: string;
  readonly locationCode: string;
  readonly serviceDate: string;
  readonly scheduleEntries: readonly ScheduleEntry[];
  readonly settings?: DailyPlanningSettings;
  readonly decisions?: Partial<Record<TripDirection, StudentLegDecision>>;
}


export interface ExceptionAdmissionInput {
  readonly requestId: string;
  readonly studentId: string;
  readonly locationCode: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly requestedAnchorTime: string;
  readonly requestedAt: string;
  readonly flexibilityMinutes?: number;
  readonly adminApproval?: {
    readonly approved: boolean;
    readonly reason?: string;
  };
}
export interface ServiceAnchorGroup {
  readonly key: string;
  readonly anchorMinutes: number;
  readonly demands: readonly DailyTripDemand[];
}

export interface ServiceWave {
  readonly key: string;
  readonly serviceDate: string;
  readonly direction: TripDirection;
  readonly classBoundaryHour: number;
  readonly demands: readonly DailyTripDemand[];
  readonly anchorGroups: readonly ServiceAnchorGroup[];
}
export const DEFAULT_DAILY_PLANNING_SETTINGS: Readonly<DailyPlanningSettings> =
  Object.freeze({
    campusCode: "D.Kampus",
    timezone: "Europe/Istanbul",
    pickupArrivalBufferMinutes: 15,
    dropoffDepartureBufferMinutes: 15,
    confirmationCutoffHour: 22,
    exceptionLeadMinutes: 120,
  });

const ISTANBUL_WALL_CLOCK_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Europe/Istanbul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

const ISO_TIMESTAMP =
  /^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?(?:Z|[+-]\d{2}:\d{2})$/;
const DAYS_OF_WEEK: ScheduleEntry["dayOfWeek"][] = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
];

export function parseClockMinutes(value: string): number {
  const match = /^(?:[01]\d|2[0-3]):[0-5]\d$/.exec(value);

  if (!match) {
    throw new Error("Invalid clock time");
  }

  return Number(value.slice(0, 2)) * 60 + Number(value.slice(3, 5));
}

export function serviceDayOfWeek(
  serviceDate: string,
): ScheduleEntry["dayOfWeek"] {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(serviceDate);

  if (!match) {
    throw new Error("Invalid service date");
  }

  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const date = new Date(Date.UTC(year, month - 1, day));

  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    throw new Error("Invalid service date");
  }

  return DAYS_OF_WEEK[date.getUTCDay()];
}

function isDudullu(location: string): boolean {
  const normalized = location.trim().toLocaleLowerCase("tr-TR");

  return normalized === "dudullu" || normalized === "d.kampus";
}

function waveKey(direction: TripDirection, classBoundaryMinutes: number): string {
  const hour = String(Math.floor(classBoundaryMinutes / 60)).padStart(2, "0");

  return direction.toUpperCase() + "-" + hour + ":00";
}

function demandOrder(left: DailyTripDemand, right: DailyTripDemand): number {
  return (
    left.anchorMinutes - right.anchorMinutes ||
    left.occurrenceId.localeCompare(right.occurrenceId)
  );
}

function validateDailyPlanningSettings(
  settings: DailyPlanningSettings,
): void {
  if (
    settings.campusCode !== "D.Kampus" ||
    settings.timezone !== "Europe/Istanbul" ||
    !Number.isFinite(settings.pickupArrivalBufferMinutes) ||
    !Number.isInteger(settings.pickupArrivalBufferMinutes) ||
    settings.pickupArrivalBufferMinutes < 0 ||
    !Number.isFinite(settings.dropoffDepartureBufferMinutes) ||
    !Number.isInteger(settings.dropoffDepartureBufferMinutes) ||
    settings.dropoffDepartureBufferMinutes < 0 ||
    !Number.isInteger(settings.confirmationCutoffHour) ||
    settings.confirmationCutoffHour < 0 ||
    settings.confirmationCutoffHour > 23 ||
    !Number.isFinite(settings.exceptionLeadMinutes) ||
    !Number.isInteger(settings.exceptionLeadMinutes) ||
    settings.exceptionLeadMinutes < 0
  ) {
    throw new Error("Invalid daily planning settings");
  }
}
function validateFlexibilityMinutes(value: number | undefined): number {
  const flexibilityMinutes = value ?? 0;

  if (!Number.isFinite(flexibilityMinutes) || !Number.isInteger(flexibilityMinutes) || flexibilityMinutes < 0) {
    throw new Error("Invalid flexibility minutes");
  }

  return flexibilityMinutes;
}

function parseIsoTimestamp(value: string): Date {
  const match = ISO_TIMESTAMP.exec(value);

  if (!match) {
    throw new Error("Invalid ISO timestamp");
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const calendarDate = new Date(Date.UTC(year, month - 1, day));
  const timestamp = new Date(value);

  if (
    Number.isNaN(timestamp.getTime()) ||
    calendarDate.getUTCFullYear() !== year ||
    calendarDate.getUTCMonth() !== month - 1 ||
    calendarDate.getUTCDate() !== day
  ) {
    throw new Error("Invalid ISO timestamp");
  }

  return timestamp;
}
function istanbulWallClock(timestamp: Date): {
  readonly year: number;
  readonly month: number;
  readonly day: number;
  readonly minutes: number;
  readonly millisecondsSinceDay: number;
} {
  const values: Record<string, number> = {};

  for (const part of ISTANBUL_WALL_CLOCK_FORMATTER.formatToParts(timestamp)) {
    if (part.type !== "literal") {
      values[part.type] = Number(part.value);
    }
  }

  return {
    year: values.year!,
    month: values.month!,
    day: values.day!,
    minutes: values.hour! * 60 + values.minute!,
    millisecondsSinceDay:
      (values.hour! * 60 * 60 + values.minute! * 60 + values.second!) * 1_000 +
      timestamp.getUTCMilliseconds(),
  };
}

function previousServiceDate(serviceDate: string): {
  readonly year: number;
  readonly month: number;
  readonly day: number;
} {
  serviceDayOfWeek(serviceDate);
  const [year, month, day] = serviceDate.split("-").map(Number);
  const previous = new Date(Date.UTC(year!, month! - 1, day! - 1));

  return {
    year: previous.getUTCFullYear(),
    month: previous.getUTCMonth() + 1,
    day: previous.getUTCDate(),
  };
}

function compareWallDate(
  left: { readonly year: number; readonly month: number; readonly day: number },
  right: { readonly year: number; readonly month: number; readonly day: number },
): number {
  return (
    (left.year - right.year) ||
    (left.month - right.month) ||
    (left.day - right.day)
  );
}

export function classifyScheduleDecision(
  decision: StudentLegDecision | undefined,
  serviceDate: string,
  settings?: DailyPlanningSettings,
): { readonly admission: DemandAdmission; readonly flexibilityMinutes: number } {
  const effectiveSettings = settings ?? DEFAULT_DAILY_PLANNING_SETTINGS;
  validateDailyPlanningSettings(effectiveSettings);
  const flexibilityMinutes = validateFlexibilityMinutes(
    decision && decision.status !== "cancelled"
      ? decision.flexibilityMinutes
      : undefined,
  );

  if (!decision || decision.status === "pending") {
    return { admission: "pending_student_confirmation", flexibilityMinutes };
  }

  if (decision.status === "cancelled") {
    parseIsoTimestamp(decision.decidedAt);
    return { admission: "cancelled", flexibilityMinutes };
  }

  const confirmation = istanbulWallClock(parseIsoTimestamp(decision.confirmedAt));
  const cutoffDate = previousServiceDate(serviceDate);
  const cutoffMilliseconds =
    effectiveSettings.confirmationCutoffHour * 60 * 60 * 1_000;
  const isAtOrBeforeCutoff =
    compareWallDate(confirmation, cutoffDate) < 0 ||
    (compareWallDate(confirmation, cutoffDate) === 0 &&
      confirmation.millisecondsSinceDay <= cutoffMilliseconds);
  return {
    admission: isAtOrBeforeCutoff ? "confirmed" : "pending_admin_approval",
    flexibilityMinutes,
  };
}
export function buildScheduleDemands(
  input: BuildScheduleDemandsInput,
): {
  readonly demands: readonly DailyTripDemand[];
  readonly excludedEntries: readonly ExcludedScheduleEntry[];
} {
  const settings = input.settings ?? DEFAULT_DAILY_PLANNING_SETTINGS;
  validateDailyPlanningSettings(settings);
  const dayOfWeek = serviceDayOfWeek(input.serviceDate);
  const excludedEntries: ExcludedScheduleEntry[] = [];
  const dudulluEntries: ScheduleEntry[] = [];

  for (const entry of input.scheduleEntries) {
    if (entry.dayOfWeek !== dayOfWeek) {
      continue;
    }

    if (!entry.location?.trim()) {
      excludedEntries.push({ entryId: entry.id, reason: "missing_campus" });
    } else if (isDudullu(entry.location)) {
      dudulluEntries.push(entry);
    } else {
      excludedEntries.push({
        entryId: entry.id,
        location: entry.location,
        reason: "other_campus",
      });
    }
  }

  if (dudulluEntries.length === 0) {
    return { demands: [], excludedEntries };
  }

  const firstEntry = [...dudulluEntries].sort(
    (left, right) =>
      parseClockMinutes(left.startTime) - parseClockMinutes(right.startTime) ||
      left.id.localeCompare(right.id),
  )[0]!;
  const lastEntry = [...dudulluEntries].sort(
    (left, right) =>
      parseClockMinutes(right.endTime) - parseClockMinutes(left.endTime) ||
      left.id.localeCompare(right.id),
  )[0]!;
  const pickupBoundary = parseClockMinutes(firstEntry.startTime);
  const dropoffBoundary = parseClockMinutes(lastEntry.endTime);
  const pickupAnchor = pickupBoundary - settings.pickupArrivalBufferMinutes;
  const dropoffAnchor = dropoffBoundary + settings.dropoffDepartureBufferMinutes;
  const pickupWaveKey = waveKey("pickup", pickupBoundary);
  const dropoffWaveKey = waveKey("dropoff", dropoffBoundary);
  const pickupDecision = classifyScheduleDecision(
    input.decisions?.pickup,
    input.serviceDate,
    settings,
  );
  const dropoffDecision = classifyScheduleDecision(
    input.decisions?.dropoff,
    input.serviceDate,
    settings,
  );

  return {
    demands: [
      {
        occurrenceId: input.serviceDate + ":pickup:" + input.studentId,
        studentId: input.studentId,
        locationCode: input.locationCode,
        campusCode: settings.campusCode,
        serviceDate: input.serviceDate,
        direction: "pickup",
        source: "schedule",
        admission: pickupDecision.admission,
        classBoundaryMinutes: pickupBoundary,
        waveKey: pickupWaveKey,
        anchorGroupKey: pickupWaveKey + "@" + pickupAnchor,
        anchorMinutes: pickupAnchor,
        hardDeadlineMinutes: pickupAnchor,
        flexibilityMinutes: pickupDecision.flexibilityMinutes,
        emergencyException: false,
      },
      {
        occurrenceId: input.serviceDate + ":dropoff:" + input.studentId,
        studentId: input.studentId,
        locationCode: input.locationCode,
        campusCode: settings.campusCode,
        serviceDate: input.serviceDate,
        direction: "dropoff",
        source: "schedule",
        admission: dropoffDecision.admission,
        classBoundaryMinutes: dropoffBoundary,
        waveKey: dropoffWaveKey,
        anchorGroupKey: dropoffWaveKey + "@" + dropoffAnchor,
        anchorMinutes: dropoffAnchor,
        hardReadyMinutes: dropoffAnchor,
        flexibilityMinutes: dropoffDecision.flexibilityMinutes,
        emergencyException: false,
      },
    ],
    excludedEntries,
  };
}

function requireNonBlank(value: string): void {
  if (!value.trim()) {
    throw new Error("Invalid exception input");
  }
}

function wallTimestampMilliseconds(
  date: { readonly year: number; readonly month: number; readonly day: number },
  millisecondsSinceDay: number,
): number {
  return Date.UTC(date.year, date.month - 1, date.day) + millisecondsSinceDay;
}
export function buildExceptionDemand(
  input: ExceptionAdmissionInput,
  settings?: DailyPlanningSettings,
): DailyTripDemand {
  const effectiveSettings = settings ?? DEFAULT_DAILY_PLANNING_SETTINGS;
  validateDailyPlanningSettings(effectiveSettings);
  requireNonBlank(input.requestId);
  requireNonBlank(input.studentId);
  requireNonBlank(input.locationCode);
  serviceDayOfWeek(input.serviceDate);
  const anchorMinutes = parseClockMinutes(input.requestedAnchorTime);
  const requested = istanbulWallClock(parseIsoTimestamp(input.requestedAt));
  const [year, month, day] = input.serviceDate.split("-").map(Number);
  const leadMilliseconds =
    wallTimestampMilliseconds(
      { year: year!, month: month!, day: day! },
      anchorMinutes * 60_000,
    ) -
    wallTimestampMilliseconds(requested, requested.millisecondsSinceDay);
  const emergencyException =
    leadMilliseconds < effectiveSettings.exceptionLeadMinutes * 60_000;
  const approved =
    input.adminApproval?.approved === true &&
    (!emergencyException || Boolean(input.adminApproval.reason?.trim()));
  const key = waveKey(input.direction, anchorMinutes);

  return {
    occurrenceId:
      input.serviceDate + ":" + input.direction + ":exception:" + input.requestId,
    studentId: input.studentId,
    locationCode: input.locationCode,
    campusCode: effectiveSettings.campusCode,
    serviceDate: input.serviceDate,
    direction: input.direction,
    source: "student_exception",
    admission: approved ? "approved" : "pending_admin_approval",
    classBoundaryMinutes: anchorMinutes,
    waveKey: key,
    anchorGroupKey: key + "@" + anchorMinutes,
    anchorMinutes,
    ...(input.direction === "pickup"
      ? { hardDeadlineMinutes: anchorMinutes }
      : { hardReadyMinutes: anchorMinutes }),
    flexibilityMinutes: validateFlexibilityMinutes(input.flexibilityMinutes),
    emergencyException,
  };
}
export function groupServiceWaves(
  demands: readonly DailyTripDemand[],
): readonly ServiceWave[] {
  const occurrenceIds = new Set<string>();
  const waves = new Map<string, DailyTripDemand[]>();

  for (const demand of demands) {
    if (occurrenceIds.has(demand.occurrenceId)) {
      throw new Error("Duplicate occurrence ID");
    }

    occurrenceIds.add(demand.occurrenceId);
    const partitionKey =
      demand.serviceDate + "|" + demand.direction + "|" + demand.waveKey;
    const grouped = waves.get(partitionKey);

    if (grouped) {
      grouped.push(demand);
    } else {
      waves.set(partitionKey, [demand]);
    }
  }

  return [...waves.values()]
    .map((waveDemands) => {
      const orderedDemands = [...waveDemands].sort(demandOrder);
      const firstDemand = orderedDemands[0]!;
      const anchorGroups = new Map<string, DailyTripDemand[]>();

      for (const demand of orderedDemands) {
        const grouped = anchorGroups.get(demand.anchorGroupKey);

        if (grouped) {
          grouped.push(demand);
        } else {
          anchorGroups.set(demand.anchorGroupKey, [demand]);
        }
      }

      return {
        key: firstDemand.waveKey,
        serviceDate: firstDemand.serviceDate,
        direction: firstDemand.direction,
        classBoundaryHour: Math.floor(firstDemand.classBoundaryMinutes / 60),
        demands: orderedDemands,
        anchorGroups: [...anchorGroups.entries()]
          .map(([key, groupedDemands]) => ({
            key,
            anchorMinutes: groupedDemands[0]!.anchorMinutes,
            demands: [...groupedDemands].sort(demandOrder),
          }))
          .sort(
            (left, right) =>
              left.anchorMinutes - right.anchorMinutes ||
              left.key.localeCompare(right.key),
          ),
      };
    })
    .sort(
      (left, right) =>
        left.serviceDate.localeCompare(right.serviceDate) ||
        left.direction.localeCompare(right.direction) ||
        left.key.localeCompare(right.key),
    );
}
