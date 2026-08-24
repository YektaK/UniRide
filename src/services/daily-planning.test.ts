import { describe, expect, it } from "vitest";
import type { ScheduleEntry } from "@/types";
import type { DailyPlanningSettings } from "./daily-planning";

import {
  buildExceptionDemand,
  buildScheduleDemands,
  DEFAULT_DAILY_PLANNING_SETTINGS,
  groupServiceWaves,
  assessShiftEligibility,
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
  it("rejects noncanonical campus and timezone settings", () => {
    for (const settings of [
      { ...DEFAULT_DAILY_PLANNING_SETTINGS, campusCode: "Other" },
      { ...DEFAULT_DAILY_PLANNING_SETTINGS, timezone: "UTC" },
    ]) {
      expect(() =>
        buildScheduleDemands({
          studentId: "S1",
          locationCode: "L1",
          serviceDate: "2026-08-26",
          scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
          settings: settings as DailyPlanningSettings,
        }),
      ).toThrow("Invalid daily planning settings");
    }
  });

  it("rejects invalid pickup and dropoff buffers", () => {
    for (const key of [
      "pickupArrivalBufferMinutes",
      "dropoffDepartureBufferMinutes",
    ] as const) {
      for (const value of [-1, 1.5, Infinity]) {
        expect(() =>
          buildScheduleDemands({
            studentId: "S1",
            locationCode: "L1",
            serviceDate: "2026-08-26",
            scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
            settings: {
              ...DEFAULT_DAILY_PLANNING_SETTINGS,
              [key]: value,
            } as DailyPlanningSettings,
          }),
        ).toThrow("Invalid daily planning settings");
      }
    }
  });

  it("rejects invalid confirmation cutoff hours", () => {
    for (const confirmationCutoffHour of [-1, 24, 12.5]) {
      expect(() =>
        buildScheduleDemands({
          studentId: "S1",
          locationCode: "L1",
          serviceDate: "2026-08-26",
          scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
          settings: {
            ...DEFAULT_DAILY_PLANNING_SETTINGS,
            confirmationCutoffHour,
          } as DailyPlanningSettings,
        }),
      ).toThrow("Invalid daily planning settings");
    }
  });

  it("rejects invalid exception lead minutes", () => {
    for (const exceptionLeadMinutes of [-1, 1.5, Infinity]) {
      expect(() =>
        buildScheduleDemands({
          studentId: "S1",
          locationCode: "L1",
          serviceDate: "2026-08-26",
          scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
          settings: {
            ...DEFAULT_DAILY_PLANNING_SETTINGS,
            exceptionLeadMinutes,
          } as DailyPlanningSettings,
        }),
      ).toThrow("Invalid daily planning settings");
    }
  });
});

describe("schedule decision admission", () => {
  it("applies the Istanbul confirmation cutoff independently per leg", () => {
    const result = buildScheduleDemands({
      studentId: "S1",
      locationCode: "L1",
      serviceDate: "2026-08-26",
      scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
      decisions: {
        pickup: {
          status: "confirmed",
          confirmedAt: "2026-08-25T18:59:00Z",
          flexibilityMinutes: 10,
        },
        dropoff: {
          status: "confirmed",
          confirmedAt: "2026-08-25T19:01:00Z",
        },
      },
    });

    expect(result.demands).toMatchObject([
      { direction: "pickup", admission: "confirmed", flexibilityMinutes: 10 },
      { direction: "dropoff", admission: "pending_admin_approval", flexibilityMinutes: 0 },
    ]);
    expect(
      buildScheduleDemands({
        studentId: "S1",
        locationCode: "L1",
        serviceDate: "2026-08-26",
        scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
        decisions: { pickup: { status: "cancelled", decidedAt: "2026-08-25T18:00:00Z" } },
      }).demands,
    ).toMatchObject([
      { direction: "pickup", admission: "cancelled" },
      { direction: "dropoff", admission: "pending_student_confirmation" },
    ]);
  });


  it("accepts exactly the Istanbul cutoff but not the instant after it", () => {
    const baseInput = {
      studentId: "S1",
      locationCode: "L1",
      serviceDate: "2026-08-26",
      scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
    };

    expect(
      buildScheduleDemands({
        ...baseInput,
        decisions: {
          pickup: { status: "confirmed", confirmedAt: "2026-08-25T19:00:00.000Z" },
        },
      }).demands[0]!.admission,
    ).toBe("confirmed");
    expect(
      buildScheduleDemands({
        ...baseInput,
        decisions: {
          pickup: { status: "confirmed", confirmedAt: "2026-08-25T19:00:00.001Z" },
        },
      }).demands[0]!.admission,
    ).toBe("pending_admin_approval");
  });
  it("rejects malformed confirmed decisions and negative flexibility", () => {
    expect(() =>
      buildScheduleDemands({
        studentId: "S1",
        locationCode: "L1",
        serviceDate: "2026-08-26",
        scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
        decisions: { pickup: { status: "confirmed", confirmedAt: "not-a-timestamp" } },
      }),
    ).toThrow("Invalid ISO timestamp");
    expect(() =>
      buildScheduleDemands({
        studentId: "S1",
        locationCode: "L1",
        serviceDate: "2026-08-26",
        scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
        decisions: { pickup: { status: "cancelled", decidedAt: "not-a-timestamp" } },
      }),
    ).toThrow("Invalid ISO timestamp");
    expect(() =>
      buildScheduleDemands({
        studentId: "S1",
        locationCode: "L1",
        serviceDate: "2026-08-26",
        scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
        decisions: { dropoff: { status: "pending", flexibilityMinutes: -1 } },
      }),
    ).toThrow("Invalid flexibility minutes");
  });
});
describe("exception demand admission", () => {
  const ordinaryException = {
    requestId: "request-1",
    studentId: "S1",
    locationCode: "L1",
    serviceDate: "2026-08-26",
    direction: "pickup" as const,
    requestedAnchorTime: "10:00",
    requestedAt: "2026-08-26T04:30:00Z",
  };

  it("builds a no-class exception demand with ordinary pending admission", () => {
    const demand = buildExceptionDemand(ordinaryException);

    expect(demand).toMatchObject({
      occurrenceId: "2026-08-26:pickup:exception:request-1",
      studentId: "S1",
      locationCode: "L1",
      source: "student_exception",
      direction: "pickup",
      admission: "pending_admin_approval",
      anchorMinutes: 600,
      waveKey: "PICKUP-10:00",
      emergencyException: false,
    });
  });

  it("requires a reason to approve an emergency exception", () => {
    const emergency = {
      ...ordinaryException,
      requestedAt: "2026-08-26T05:30:00Z",
      adminApproval: { approved: true, reason: "   " },
    };

    expect(buildExceptionDemand(emergency)).toMatchObject({
      admission: "pending_admin_approval",
      emergencyException: true,
    });
    expect(
      buildExceptionDemand({
        ...emergency,
        adminApproval: { approved: true, reason: "Medical need" },
      }),
    ).toMatchObject({ admission: "approved", emergencyException: true });
    expect(
      buildExceptionDemand({
        ...ordinaryException,
        adminApproval: { approved: true },
      }),
    ).toMatchObject({ admission: "approved", emergencyException: false });
  });


  it("preserves seconds at the exception lead-time boundary", () => {
    expect(
      buildExceptionDemand({
        ...ordinaryException,
        requestedAt: "2026-08-26T05:00:00.000Z",
      }).emergencyException,
    ).toBe(false);
    expect(
      buildExceptionDemand({
        ...ordinaryException,
        requestedAt: "2026-08-26T05:00:30.000Z",
      }).emergencyException,
    ).toBe(true);
  });
  it("keeps pickup and dropoff exception anchors independent", () => {
    const pickup = buildExceptionDemand(ordinaryException);
    const dropoff = buildExceptionDemand({
      ...ordinaryException,
      requestId: "request-2",
      direction: "dropoff",
      requestedAnchorTime: "17:10",
    });

    expect([pickup, dropoff]).toMatchObject([
      { direction: "pickup", anchorMinutes: 600, waveKey: "PICKUP-10:00" },
      { direction: "dropoff", anchorMinutes: 1030, waveKey: "DROPOFF-17:00" },
    ]);
  });

  it("rejects invalid exception inputs", () => {
    for (const input of [
      { ...ordinaryException, requestedAt: "not-a-timestamp" },
      { ...ordinaryException, requestedAt: "2026-02-30T00:00:00Z" },
      { ...ordinaryException, requestedAnchorTime: "25:00" },
      { ...ordinaryException, requestId: " " },
      { ...ordinaryException, flexibilityMinutes: -1 },
    ]) {
      expect(() => buildExceptionDemand(input)).toThrow();
    }
  });
});

describe("service-wave shift eligibility", () => {
  const baseDemand = buildScheduleDemands({
    studentId: "S1",
    locationCode: "L1",
    serviceDate: "2026-08-26",
    scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES,
    decisions: {
      pickup: { status: "confirmed", confirmedAt: "2026-08-25T18:00:00Z", flexibilityMinutes: 60 },
      dropoff: { status: "confirmed", confirmedAt: "2026-08-25T18:00:00Z", flexibilityMinutes: 60 },
    },
  }).demands;
  const pickup = baseDemand[0]!;
  const dropoff = baseDemand[1]!;

  it("previews direction-safe pickup-earlier and dropoff-later shifts within confirmed flexibility", () => {
    expect(assessShiftEligibility(pickup, { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: pickup.anchorMinutes - 60 })).toEqual({ canPreview: true, requiresStudentReconfirmation: false, deltaMinutes: -60 });
    expect(assessShiftEligibility(dropoff, { serviceDate: dropoff.serviceDate, direction: "dropoff", anchorMinutes: dropoff.anchorMinutes + 60 })).toEqual({ canPreview: true, requiresStudentReconfirmation: false, deltaMinutes: 60 });
  });

  it("rejects unsafe directions unless the student requested an alternative time", () => {
    for (const [demand, anchorMinutes] of [[pickup, pickup.anchorMinutes + 1], [dropoff, dropoff.anchorMinutes - 1]] as const) {
      expect(assessShiftEligibility(demand, { serviceDate: demand.serviceDate, direction: demand.direction, anchorMinutes })).toEqual({ canPreview: false, requiresStudentReconfirmation: false, deltaMinutes: anchorMinutes - demand.anchorMinutes, rejectionReason: "unsafe_direction" });
      expect(assessShiftEligibility(demand, { serviceDate: demand.serviceDate, direction: demand.direction, anchorMinutes, alternativeTimeRequested: true })).toEqual({ canPreview: true, requiresStudentReconfirmation: true, deltaMinutes: anchorMinutes - demand.anchorMinutes });
    }
  });

  it("requires reconfirmation beyond flexibility and for nonzero shifts with default zero flexibility", () => {
    expect(assessShiftEligibility(pickup, { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: pickup.anchorMinutes - 61 })).toMatchObject({ canPreview: true, requiresStudentReconfirmation: true, deltaMinutes: -61 });
    const zeroFlexibility = buildScheduleDemands({ studentId: "S2", locationCode: "L1", serviceDate: "2026-08-26", scheduleEntries: WEDNESDAY_DUDULLU_ENTRIES }).demands[0]!;
    expect(assessShiftEligibility(zeroFlexibility, { serviceDate: zeroFlexibility.serviceDate, direction: "pickup", anchorMinutes: zeroFlexibility.anchorMinutes - 1 })).toMatchObject({ canPreview: true, requiresStudentReconfirmation: true, deltaMinutes: -1 });
  });

  // This policy precheck must never claim vehicle savings; Package 5 needs certified source/destination re-solves.
  it("keeps same anchors non-reconfirming, rejects cross-boundary targets, and does not mutate demand", () => {
    const before = structuredClone(pickup);
    expect(assessShiftEligibility(pickup, { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: pickup.anchorMinutes })).toEqual({ canPreview: true, requiresStudentReconfirmation: false, deltaMinutes: 0 });
    expect(assessShiftEligibility(pickup, { serviceDate: "2026-08-27", direction: "pickup", anchorMinutes: pickup.anchorMinutes })).toMatchObject({ canPreview: false, rejectionReason: "different_service_date" });
    expect(assessShiftEligibility(pickup, { serviceDate: pickup.serviceDate, direction: "dropoff", anchorMinutes: pickup.anchorMinutes })).toMatchObject({ canPreview: false, rejectionReason: "different_direction" });
    expect(pickup).toEqual(before);
  });

  it("rejects malformed runtime targets fail-closed", () => {
    for (const target of [
      { serviceDate: "2026-02-30", direction: "pickup", anchorMinutes: pickup.anchorMinutes },
      { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: Infinity },
      { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: 1.5 },
      { serviceDate: pickup.serviceDate, direction: "pickup", anchorMinutes: 1440 },
    ] as const) {
      expect(() => assessShiftEligibility(pickup, target)).toThrow("Invalid shift target");
    }
  });
  it("rejects truthy non-boolean alternative-time intent fail-closed", () => {
    expect(() =>
      assessShiftEligibility(pickup, {
        serviceDate: pickup.serviceDate,
        direction: "pickup",
        anchorMinutes: pickup.anchorMinutes + 1,
        alternativeTimeRequested: "false" as unknown as boolean,
      }),
    ).toThrow("Invalid shift target");
  });
});
