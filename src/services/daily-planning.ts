import type { ScheduleEntry } from "@/types";

export type TripDirection = "pickup" | "dropoff";
export type DemandSource = "schedule" | "student_exception" | "admin_override";
export type DemandAdmission =
  | "pending_student_confirmation"
  | "confirmed"
  | "pending_admin_approval"
  | "approved"
  | "cancelled";

export interface DailyPlanningSettings {
  readonly campusCode: "D.Kampus";
  readonly timezone: "Europe/Istanbul";
  readonly pickupArrivalBufferMinutes: number;
  readonly dropoffDepartureBufferMinutes: number;
  readonly confirmationCutoffHour: number;
  readonly exceptionLeadMinutes: number;
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
