
import type { WeeklySchedule, ScheduleEntry } from "@/types";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

// Manually created mock schedules adhering to constraints
const mockSchedules: Record<string, WeeklySchedule> = {
  "schedule001": { // Ayşe
    id: "schedule001",
    userId: "student001",
    entries: [
      { id: "s1m1", dayOfWeek: "monday", courseName: "MAT101", startTime: "09:00", endTime: "11:00", location: "Dudullu" },
      { id: "s1m2", dayOfWeek: "monday", courseName: "PHY202", startTime: "13:00", endTime: "15:00", location: "Çengelköy" },
      { id: "s1t1", dayOfWeek: "tuesday", courseName: "CS305", startTime: "10:00", endTime: "13:00", location: "Dudullu" },
      { id: "s1w1", dayOfWeek: "wednesday", courseName: "ENG111", startTime: "11:00", endTime: "14:00", location: "Çengelköy" },
      { id: "s1f1", dayOfWeek: "friday", courseName: "HIS210", startTime: "14:00", endTime: "17:00", location: "Dudullu" },
    ],
    lastUpdated: new Date().toISOString(),
  },
  "schedule002": { // Veli
    id: "schedule002",
    userId: "student002",
    entries: [
      { id: "s2m1", dayOfWeek: "monday", courseName: "ECO201", startTime: "10:00", endTime: "12:00", location: "Çengelköy" },
      { id: "s2t1", dayOfWeek: "tuesday", courseName: "SOC101", startTime: "09:00", endTime: "12:00", location: "Dudullu" },
      { id: "s2t2", dayOfWeek: "tuesday", courseName: "ART150", startTime: "14:00", endTime: "16:00", location: "Çengelköy" },
      { id: "s2r1", dayOfWeek: "thursday", courseName: "BUS330", startTime: "13:00", endTime: "17:00", location: "Dudullu" },
      { id: "s2f1", dayOfWeek: "friday", courseName: "LAW205", startTime: "11:00", endTime: "13:00", location: "Çengelköy" },
    ],
    lastUpdated: new Date().toISOString(),
  },
  "schedule003": { // Zeynep
    id: "schedule003",
    userId: "student003",
    entries: [
      { id: "s3m1", dayOfWeek: "monday", courseName: "PSY100", startTime: "08:00", endTime: "11:00", location: "Dudullu" },
      { id: "s3w1", dayOfWeek: "wednesday", courseName: "CHE220", startTime: "10:00", endTime: "14:00", location: "Çengelköy" },
      { id: "s3w2", dayOfWeek: "wednesday", courseName: "BIO110", startTime: "15:00", endTime: "17:00", location: "Dudullu" },
      { id: "s3r1", dayOfWeek: "thursday", courseName: "PHI400", startTime: "09:00", endTime: "11:00", location: "Çengelköy" },
      { id: "s3f1", dayOfWeek: "friday", courseName: "GEO202", startTime: "13:00", endTime: "16:00", location: "Dudullu" },
    ],
    lastUpdated: new Date().toISOString(),
  },
};

export function getStudentSchedule(scheduleId: string): WeeklySchedule | undefined {
  const schedule = mockSchedules[scheduleId];
  if (schedule) {
    // Return a deep copy to prevent direct mutation of the mockSchedules object
    return JSON.parse(JSON.stringify(schedule));
  }
  return undefined;
}

export function updateStudentScheduleEntries(scheduleId: string, entries: ScheduleEntry[]): boolean {
  if (mockSchedules[scheduleId]) {
    const sortedEntries = [...entries].sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));
    mockSchedules[scheduleId].entries = sortedEntries;
    mockSchedules[scheduleId].lastUpdated = new Date().toISOString();
    return true;
  }
  return false;
}

// Helper to create a new schedule if one doesn't exist for a user (e.g., a new student)
// In a real DB, this would be an INSERT operation.
export function createNewUserSchedule(userId: string, scheduleId: string): WeeklySchedule {
    if (mockSchedules[scheduleId]) {
        return getStudentSchedule(scheduleId)!; // Should not happen if ID is unique
    }
    const newSchedule: WeeklySchedule = {
        id: scheduleId,
        userId: userId,
        entries: [], // Start with an empty schedule
        lastUpdated: new Date().toISOString(),
    };
    mockSchedules[scheduleId] = newSchedule;
    return JSON.parse(JSON.stringify(newSchedule));
}
