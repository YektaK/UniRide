/**
 * Excel/CSV Import Service
 * Handles importing student schedules from Excel/CSV files
 */

import * as XLSX from "xlsx";
import type { ScheduleEntry } from "@/types";
import { getUsers, getScheduleByUserId, createSchedule, updateScheduleEntries, updateUser } from "@/lib/database";
import { DUDULLU_CAMPUS } from "@/services/dudullu-campus";

export interface ExcelImportRow {
  studentNumber: string;
  day: string;
  courseCode?: string;
  startTime: string;
  endTime: string;
  location: string;
}

export interface ImportResult {
  success: boolean;
  processed: number;
  created: number;
  updated: number;
  errors: Array<{ row: number; message: string }>;
}

const DAY_MAP: Record<string, ScheduleEntry["dayOfWeek"]> = {
  monday: "monday",
  tuesday: "tuesday",
  wednesday: "wednesday",
  thursday: "thursday",
  friday: "friday",
  saturday: "saturday",
  sunday: "sunday",
  pazartesi: "monday",
  salı: "tuesday",
  çarşamba: "wednesday",
  perşembe: "thursday",
  cuma: "friday",
  cumartesi: "saturday",
  pazar: "sunday",
  mon: "monday",
  tue: "tuesday",
  wed: "wednesday",
  thu: "thursday",
  fri: "friday",
  sat: "saturday",
  sun: "sunday",
};

const LOCATION_MAP: Record<string, string> = {
  dudullu: DUDULLU_CAMPUS.scheduleLabel,
  "d.kampus": DUDULLU_CAMPUS.scheduleLabel,
  çengelköy: "Çengelköy",
  cengelkoy: "Çengelköy",
  cengelköy: "Çengelköy",
};

/**
 * Parse time string (HH:mm or H:mm format)
 */
const parseTime = (timeStr: string): string | null => {
  if (!timeStr) return null;

  // Remove whitespace
  const cleaned = timeStr.trim();

  // Check if it's already in HH:mm format
  if (/^([01]\d|2[0-3]):([0-5]\d)$/.test(cleaned)) {
    return cleaned;
  }

  // Try to parse Excel time format (decimal number)
  const num = parseFloat(cleaned);
  if (!isNaN(num) && num >= 0 && num < 1) {
    // Excel time is stored as a fraction of a day
    const totalSeconds = Math.floor(num * 24 * 60 * 60);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
  }

  return null;
};

/**
 * Validate and normalize a row
 */
const normalizeRow = (row: any, rowIndex: number): ExcelImportRow | null => {
  const studentNumber = String(row["Öğrenci No"] || row["studentNumber"] || row["ÖğrenciNo"] || "").trim();
  const day = String(row["Gün"] || row["day"] || row["Day"] || "").trim().toLowerCase();
  const courseCode = String(row["Ders Kodu"] || row["courseCode"] || row["DersKodu"] || row["CourseCode"] || "").trim();
  const startTime = String(row["Başlangıç Saati"] || row["startTime"] || row["BaşlangıçSaati"] || row["StartTime"] || "").trim();
  const endTime = String(row["Bitiş Saati"] || row["endTime"] || row["BitişSaati"] || row["EndTime"] || "").trim();
  const location = String(row["Konum"] || row["location"] || row["Location"] || "").trim().toLowerCase();

  if (!studentNumber || !day || !startTime || !endTime) {
    return null;
  }

  const normalizedDay = DAY_MAP[day];
  if (!normalizedDay) {
    return null;
  }

  const normalizedStartTime = parseTime(startTime);
  const normalizedEndTime = parseTime(endTime);
  if (!normalizedStartTime || !normalizedEndTime) {
    return null;
  }

  const normalizedLocation = LOCATION_MAP[location] || location;
  if (normalizedLocation !== "Dudullu" && normalizedLocation !== "Çengelköy") {
    return null;
  }

  return {
    studentNumber,
    day: normalizedDay,
    courseCode: courseCode || undefined,
    startTime: normalizedStartTime,
    endTime: normalizedEndTime,
    location: normalizedLocation,
  };
};

/**
 * Parse Excel/CSV file
 */
export const parseExcelFile = async (file: File): Promise<ExcelImportRow[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: "array" });

        // Get first sheet
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];

        // Convert to JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

        if (jsonData.length < 2) {
          reject(new Error("Excel dosyası en az bir başlık satırı ve bir veri satırı içermelidir."));
          return;
        }

        // First row is headers
        const headers = (jsonData[0] as unknown[]).map((h) => String(h ?? "").trim());

        // Create object rows
        const rows: ExcelImportRow[] = [];
        for (let i = 1; i < jsonData.length; i++) {
          const rowData: Record<string, unknown> = {};
          const row = jsonData[i] as unknown[];

          headers.forEach((header, index) => {
            rowData[header] = row[index];
          });

          const normalized = normalizeRow(rowData, i + 1);
          if (normalized) {
            rows.push(normalized);
          }
        }

        resolve(rows);
      } catch (error) {
        reject(error);
      }
    };

    reader.onerror = () => {
      reject(new Error("Dosya okunurken bir hata oluştu."));
    };

    reader.readAsArrayBuffer(file);
  });
};

/**
 * Import schedules from parsed rows
 */
export const importSchedules = async (rows: ExcelImportRow[]): Promise<ImportResult> => {
  const result: ImportResult = {
    success: true,
    processed: 0,
    created: 0,
    updated: 0,
    errors: [],
  };

  try {
    // Get all users
    const allUsers = await getUsers();
    const userMap = new Map<string, any>();
    allUsers.forEach((user) => {
      if (user.studentNumber) {
        userMap.set(user.studentNumber, user);
      }
    });

    // Group rows by student number
    const studentRows = new Map<string, ExcelImportRow[]>();
    rows.forEach((row, index) => {
      if (!studentRows.has(row.studentNumber)) {
        studentRows.set(row.studentNumber, []);
      }
      studentRows.get(row.studentNumber)!.push(row);
    });

    // Process each student
    for (const [studentNumber, studentRowList] of studentRows) {
      const user = userMap.get(studentNumber);
      if (!user) {
        result.errors.push({
          row: rows.findIndex((r) => r.studentNumber === studentNumber) + 1,
          message: `Öğrenci numarası ${studentNumber} bulunamadı.`,
        });
        result.success = false;
        continue;
      }

      if (user.role !== "student") {
        result.errors.push({
          row: rows.findIndex((r) => r.studentNumber === studentNumber) + 1,
          message: `Kullanıcı ${studentNumber} bir öğrenci değil.`,
        });
        result.success = false;
        continue;
      }

      try {
        // Convert rows to schedule entries
        const entries: ScheduleEntry[] = studentRowList.map((row, index) => ({
          id: `se_import_${Date.now()}_${index}`,
          dayOfWeek: row.day as ScheduleEntry["dayOfWeek"],
          courseName: row.courseCode,
          startTime: row.startTime,
          endTime: row.endTime,
          location: row.location,
        }));

        // Get or create schedule
        let schedule;
        if (user.weeklyScheduleId) {
          schedule = await getScheduleByUserId(user.id);
          if (schedule) {
            // Update existing schedule - merge with existing entries
            const existingEntries = schedule.entries || [];
            // Remove entries for days that have new data
            const daysToReplace = new Set(entries.map((e) => e.dayOfWeek));
            const filteredExisting = existingEntries.filter(
              (e) => !daysToReplace.has(e.dayOfWeek)
            );
            const mergedEntries = [...filteredExisting, ...entries];

            await updateScheduleEntries(schedule.id, mergedEntries);
            result.updated++;
          } else {
            // Create new schedule with existing ID
            schedule = await createSchedule(
              {
                userId: user.id,
                entries,
                lastUpdated: new Date().toISOString(),
              },
              user.weeklyScheduleId
            );
            result.created++;
          }
        } else {
          // Create new schedule
          const scheduleId = `schedule_${user.id}`;
          schedule = await createSchedule(
            {
              userId: user.id,
              entries,
              lastUpdated: new Date().toISOString(),
            },
            scheduleId
          );

          // Update user with schedule ID
          await updateUser(user.id, { weeklyScheduleId: scheduleId });
          result.created++;
        }

        result.processed += studentRowList.length;
      } catch (error: any) {
        result.errors.push({
          row: rows.findIndex((r) => r.studentNumber === studentNumber) + 1,
          message: `Öğrenci ${studentNumber} için hata: ${error.message}`,
        });
        result.success = false;
      }
    }
  } catch (error: any) {
    result.success = false;
    result.errors.push({
      row: 0,
      message: `Genel hata: ${error.message}`,
    });
  }

  return result;
};

