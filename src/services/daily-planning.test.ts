import { describe, expect, it } from "vitest";
import type { ScheduleEntry } from "@/types";

import {
  buildScheduleDemands,
  DEFAULT_DAILY_PLANNING_SETTINGS,
  groupServiceWaves,
  parseClockMinutes,
  serviceDayOfWeek,
} from "./daily-planning";

const WEDNESDAY_DUDULLU_ENTRIES: readonly ScheduleEntry[] = [
  { id: "dudullu-b", dayOfWeek: "wednesday", startTime: "14:15", endTime: "17:05", location: "  DUDULLU  " },
  { id: "cengel-1", dayOfWeek: "wednesday", startTime: "08:00", endTime: "09:00", location: "Çengelköy" },
  { id: "dudullu-a", dayOfWeek: "wednesday", startTime: "09:30", endTime: "11:00", location: "Dudullu" },
];

describe("daily planning contracts", () => {
  it("defines the Dudullu daily planning defaults", () => {
    expect(DEFAULT_DAILY_PLANNING_SETTINGS).toEqual({
      campusCode: "D.Kampus",
      timezone: "Europe/Istanbul",
      pickupArrivalBufferMinutes: 15,
      dropoffDepartureBufferMinutes: 15,
      confirmationCutoffHour: 22,
      exceptionLeadMinutes: 120,
    });
  });

  it("maps valid calendar dates to the existing schedule day enum", () => {
    expect(serviceDayOfWeek("2026-08-26")).toBe("wednesday");
    expect(() => serviceDayOfWeek("2026-02-30")).toThrow("Invalid service date");
  });

  it("parses valid clock times and rejects invalid ones", () => {
    expect(parseClockMinutes("09:30")).toBe(570);
    expect(() => parseClockMinutes("24:00")).toThrow("Invalid clock time");
  });

  it("builds independent Dudullu pickup and dropoff demands", () => {
    const result = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES });

    expect(result.demands).toMatchObject([
      { occurrenceId: "2026-08-26:pickup:S1", studentId: "S1", locationCode: "L1", campusCode: "D.Kampus", direction: "pickup", source: "schedule", admission: "pending_student_confirmation", classBoundaryMinutes: 570, anchorMinutes: 555, hardDeadlineMinutes: 555, waveKey: "PICKUP-09:00", anchorGroupKey: "PICKUP-09:00@555" },
      { occurrenceId: "2026-08-26:dropoff:S1", direction: "dropoff", classBoundaryMinutes: 1025, anchorMinutes: 1040, hardReadyMinutes: 1040, waveKey: "DROPOFF-17:00", anchorGroupKey: "DROPOFF-17:00@1040" },
    ]);
    expect(result.excludedEntries).toEqual([{ entryId: "cengel-1", reason: "other_campus", location: "Çengelköy" }]);
  });

  it("reports missing campuses and ignores days without Dudullu classes", () => {
    const missingCampus = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: [{ id: "missing-1", dayOfWeek: "wednesday", startTime: "09:00", endTime: "10:00" }] });
    const noDudullu = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES.filter((entry) => entry.location === "Çengelköy") });

    expect(missingCampus).toEqual({ demands: [], excludedEntries: [{ entryId: "missing-1", reason: "missing_campus" }] });
    expect(noDudullu.demands).toEqual([]);
  });

  it("selects daily boundaries without mutating the schedule input", () => {
    const entries = [...WEDNESDAY_DUDULLU_ENTRIES];
    const originalOrder = entries.map((entry) => entry.id);
    const result = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: entries });

    expect(result.demands.map((demand) => demand.classBoundaryMinutes)).toEqual([570, 1025]);
    expect(entries.map((entry) => entry.id)).toEqual(originalOrder);
  });

  it("changes exact anchors but not hourly waves when buffers change", () => {
    const baseInput = { studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES };
    const defaults = buildScheduleDemands(baseInput);
    const customized = buildScheduleDemands({ ...baseInput, settings: { ...DEFAULT_DAILY_PLANNING_SETTINGS, pickupArrivalBufferMinutes: 20, dropoffDepartureBufferMinutes: 25 } });

    expect(customized.demands.map((demand) => demand.anchorMinutes)).toEqual([550, 1050]);
    expect(customized.demands.map((demand) => demand.waveKey)).toEqual(defaults.demands.map((demand) => demand.waveKey));
    expect(customized.demands.map((demand) => demand.anchorGroupKey)).not.toEqual(defaults.demands.map((demand) => demand.anchorGroupKey));
  });

  it("keeps same-location students as distinct demand occurrences", () => {
    const first = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES });
    const second = buildScheduleDemands({ studentId: "S2", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES });

    expect(first.demands.map((demand) => demand.occurrenceId)).not.toEqual(second.demands.map((demand) => demand.occurrenceId));
  });

  it("keeps hourly waves separate from exact-anchor groups deterministically", () => {
    const nineOClock = buildScheduleDemands({ studentId: "S2", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: [{ id: "dudullu-nine", dayOfWeek: "wednesday", startTime: "09:00", endTime: "10:00", location: "D.Kampus" }] });
    const nineThirty = buildScheduleDemands({ studentId: "S1", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES });
    const pickups = [nineThirty.demands[0], nineOClock.demands[0]];
    const waves = groupServiceWaves(pickups);

    expect(waves).toMatchObject([{ key: "PICKUP-09:00", classBoundaryHour: 9, demands: [{ occurrenceId: "2026-08-26:pickup:S2" }, { occurrenceId: "2026-08-26:pickup:S1" }], anchorGroups: [{ key: "PICKUP-09:00@525", anchorMinutes: 525 }, { key: "PICKUP-09:00@555", anchorMinutes: 555 }] }]);
    expect(groupServiceWaves([...pickups].reverse())).toEqual(waves);
    expect(() => groupServiceWaves([pickups[0], pickups[0]])).toThrow("Duplicate occurrence ID");
  });
});