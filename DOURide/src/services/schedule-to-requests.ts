/**
 * Service to convert weekly schedules to ride requests
 * Creates RideRequest documents from WeeklySchedule entries for upcoming days
 */

import { getUsers, getScheduleByUserId, createRideRequest, getAllRideRequests } from "@/lib/database";
import type { ScheduleEntry, RideRequest } from "@/types";
import { addDays, format, getDay, startOfWeek, endOfWeek, addWeeks, parse } from "date-fns";
import { tr } from "date-fns/locale";

const daysOrder: ScheduleEntry["dayOfWeek"][] = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

/**
 * Convert day name to Date object for a specific week
 */
const getDateForDay = (dayName: ScheduleEntry["dayOfWeek"], weekStart: Date): Date => {
  const dayIndex = daysOrder.indexOf(dayName);
  return addDays(weekStart, dayIndex);
};

/**
 * Generate ride requests from a student's weekly schedule for a specific week
 */
export const generateRideRequestsFromSchedule = async (
  userId: string,
  scheduleId: string,
  targetWeekStart: Date,
  homeAddress: string,
  universityLocation: string = "Doğuş Üniversitesi, Dudullu Kampüsü"
): Promise<{ created: number; requests: RideRequest[] }> => {
  const schedule = await getScheduleByUserId(userId);
  if (!schedule || schedule.entries.length === 0) {
    return { created: 0, requests: [] };
  }

  const requests: RideRequest[] = [];
  const weekStart = startOfWeek(targetWeekStart, { weekStartsOn: 1, locale: tr });
  const weekEnd = endOfWeek(targetWeekStart, { weekStartsOn: 1, locale: tr });

  // Group entries by day
  const entriesByDay = new Map<ScheduleEntry["dayOfWeek"], ScheduleEntry[]>();
  schedule.entries.forEach((entry) => {
    if (!entriesByDay.has(entry.dayOfWeek)) {
      entriesByDay.set(entry.dayOfWeek, []);
    }
    entriesByDay.get(entry.dayOfWeek)!.push(entry);
  });

  // Create requests for each day with entries
  for (const [dayOfWeek, dayEntries] of entriesByDay) {
    if (dayEntries.length === 0) continue;

    // Sort entries by start time
    const sortedEntries = [...dayEntries].sort((a, b) =>
      a.startTime.localeCompare(b.startTime)
    );

    const firstEntry = sortedEntries[0];
    const lastEntry = sortedEntries[sortedEntries.length - 1];

    // Calculate dates and times
    const targetDate = getDateForDay(dayOfWeek, weekStart);

    // Pickup time: Before first class (subtract 30 minutes for travel time)
    const [pickupHour, pickupMinute] = firstEntry.startTime.split(":").map(Number);
    const pickupTime = new Date(targetDate);
    pickupTime.setHours(pickupHour, pickupMinute - 30, 0, 0); // 30 minutes before first class

    // Dropoff time: After last class (add 30 minutes for travel time)
    const [dropoffHour, dropoffMinute] = lastEntry.endTime.split(":").map(Number);
    const dropoffTime = new Date(targetDate);
    dropoffTime.setHours(dropoffHour, dropoffMinute + 30, 0, 0); // 30 minutes after last class

    // Create pickup request (home to university)
    const pickupRequest: Omit<RideRequest, "id" | "createdAt"> = {
      userId,
      type: "scheduled",
      requestedPickupTime: pickupTime.toISOString(),
      requestedDropoffTime: pickupTime.toISOString(), // Same as pickup for arrival
      pickupLocation: { address: homeAddress },
      dropoffLocation: { address: universityLocation },
      status: "pending_student_confirmation", // Will be confirmed by student
      notes: `Haftalık program - ${dayOfWeek} günü için otomatik oluşturuldu`,
    };

    // Create dropoff request (university to home)
    const dropoffRequest: Omit<RideRequest, "id" | "createdAt"> = {
      userId,
      type: "scheduled",
      requestedPickupTime: dropoffTime.toISOString(),
      requestedDropoffTime: dropoffTime.toISOString(), // Same as pickup for departure
      pickupLocation: { address: universityLocation },
      dropoffLocation: { address: homeAddress },
      status: "pending_student_confirmation", // Will be confirmed by student
      notes: `Haftalık program - ${dayOfWeek} günü için otomatik oluşturuldu`,
    };

    requests.push(pickupRequest as RideRequest, dropoffRequest as RideRequest);
  }

  // Create requests in database
  let createdCount = 0;
  const createdRequests: RideRequest[] = [];

  for (const request of requests) {
    try {
      const created = await createRideRequest(request);
      createdRequests.push(created);
      createdCount++;
    } catch (error) {
      console.error(`Error creating ride request for user ${userId}:`, error);
    }
  }

  return { created: createdCount, requests: createdRequests };
};

/**
 * Generate ride requests for all students for a specific week
 */
export const generateAllStudentRideRequests = async (
  targetWeekStart: Date
): Promise<{ totalCreated: number; errors: Array<{ userId: string; error: string }> }> => {
  const users = await getUsers();
  const students = users.filter((u) => u.role === "student" && u.weeklyScheduleId);

  let totalCreated = 0;
  const errors: Array<{ userId: string; error: string }> = [];

  for (const student of students) {
    if (!student.homeAddress || !student.weeklyScheduleId) {
      errors.push({
        userId: student.id,
        error: "Öğrencinin ev adresi veya haftalık programı eksik",
      });
      continue;
    }

    try {
      const result = await generateRideRequestsFromSchedule(
        student.id,
        student.weeklyScheduleId,
        targetWeekStart,
        student.homeAddress
      );
      totalCreated += result.created;
    } catch (error: any) {
      errors.push({
        userId: student.id,
        error: error.message || "Bilinmeyen hata",
      });
    }
  }

  return { totalCreated, errors };
};

/**
 * Check if ride requests already exist for a student for a specific week
 */
export const hasExistingRequestsForWeek = async (
  userId: string,
  weekStart: Date
): Promise<boolean> => {
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1, locale: tr });

  const requests = await getAllRideRequests({
    userId,
    dateFrom: weekStart.toISOString(),
    dateTo: weekEnd.toISOString(),
  });

  // Check if there are any scheduled requests for this week
  return requests.some(
    (req) =>
      req.type === "scheduled" &&
      new Date(req.requestedPickupTime) >= weekStart &&
      new Date(req.requestedPickupTime) <= weekEnd
  );
};

