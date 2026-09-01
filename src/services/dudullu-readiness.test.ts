import { describe, expect, it } from "vitest";
import type {
  ReadinessMatrixSummary,
  ReadinessScheduleInput,
  ReadinessStudentInput,
  ReadinessVehicleInput,
} from "./dudullu-readiness";
import {
  analyzeDudulluReadiness,
  requiredDudulluStudentLocations,
} from "./dudullu-readiness";

const DRIVER_ID = "drv-9f2a-driver";
const OBSERVER_STUDENT = "stu-9f2a-observer";
const UNKNOWN_SCHEDULE_ID = "sch-9f2a-nowhere";

function targetStudent(
  id: string,
  locationCode: string,
  extra: Partial<ReadinessStudentInput> = {},
): ReadinessStudentInput {
  return {
    id,
    role: "student",
    locationCode,
    disabilityType: "Sw",
    weeklyScheduleId: id,
    ...extra,
  };
}

function nonDudulluStudent(
  id: string,
  extra: Partial<ReadinessStudentInput> = {},
): ReadinessStudentInput {
  return { id, role: "student", locationCode: "Çengelköy", disabilityType: "So", weeklyScheduleId: id, ...extra };
}

function dudulluSchedule(
  id: string,
  entries: unknown = [
    {
      id: "cl-9f2a",
      dayOfWeek: "wednesday",
      startTime: "09:00",
      endTime: "10:00",
      location: "Dudullu",
    },
  ],
): ReadinessScheduleInput {
  return { id, userId: id, entries };
}

function readyMatrix(
  requiredLocationCount: number,
  matrixLocationCount = 29,
): ReadinessMatrixSummary {
  const arcs = requiredLocationCount * (requiredLocationCount - 1);
  return {
    source: "supabase",
    loaded: true,
    stale: false,
    hasError: false,
    matrixLocationCount,
    requiredLocationCount,
    missingRequiredLocationCount: 0,
    expectedRequiredDirectedArcCount: arcs,
    validRequiredDirectedArcCount: arcs,
    invalidOrMissingRequiredDirectedArcCount: 0,
    depotPresent: true,
    complete: true,
    ready: true,
  };
}

function readyVehicles(): readonly ReadinessVehicleInput[] {
  return [{ status: "active", wheelchairCapacity: 1, seatingCapacity: 7 }];
}

const READY_DRIVERS = [{ id: DRIVER_ID, role: "driver" as const }];

describe("analyzeDudulluReadiness", () => {
  it("compares but never requires the historical 28-student count", () => {
    const students = Array.from({ length: 30 }, (_, i) =>
      targetStudent(`stu-${i}`, `Sw${i + 1}`),
    );
    const schedules = students.map((s) => dudulluSchedule(s.id));
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, ...students],
      schedules,
      readyVehicles(),
      readyMatrix(31, 31),
    );

    expect(report.historicalExpectation.studentCount).toBe(28);
    expect(report.historicalExpectation.matchesStudentCount).toBe(false);
    expect(report.ready).toBe(true);

    const twentyEight = Array.from({ length: 28 }, (_, i) =>
      targetStudent(`stu-${i}`, `Sw${i + 1}`),
    );
    const exact = analyzeDudulluReadiness(
      [...READY_DRIVERS, ...twentyEight],
      twentyEight.map((s) => dudulluSchedule(s.id)),
      readyVehicles(),
      readyMatrix(29, 29),
    );
    expect(exact.historicalExpectation.matchesStudentCount).toBe(true);
    expect(exact.historicalExpectation.matchesMatrixNodeCount).toBe(true);
    expect(exact.ready).toBe(true);
  });

  it("counts a consistent weekly_schedule_id <-> schedule id/user_id mapping", () => {
    const student = targetStudent("stu-A-9f2a", "Sw1");
    const schedule = { id: "sch-A-9f2a", userId: student.id, entries: dudulluSchedule("x").entries };
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [{ ...schedule, id: student.weeklyScheduleId! }],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.students.dudulluTarget).toBe(1);
    expect(report.schedules.total).toBe(1);
    expect(report.students.unclassifiedSchedule).toBe(0);
    expect(report.ready).toBe(true);
  });

  it("reports valid non-Dudullu scheduled accounts without blocking readiness", () => {
    const target = targetStudent("stu-T-9f2a", "Sw1");
    const other = nonDudulluStudent("stu-N-9f2a");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target, other],
      [
        dudulluSchedule(target.id),
        {
          id: other.id,
          userId: other.id,
          entries: [{ id: "c-9f2a", dayOfWeek: "wednesday", startTime: "10:00", endTime: "11:00", location: "Çengelköy" }],
        },
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.students.dudulluTarget).toBe(1);
    expect(report.students.nonDudulluScheduled).toBe(1);
    expect(report.ready).toBe(true);
  });

  it("classifies a missing schedule link as unclassified and blocks readiness", () => {
    const student = targetStudent("stu-M-9f2a", "Sw1", { weeklyScheduleId: undefined });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("schedule_classification_incomplete");
  });

  it("classifies an unknown schedule reference as unclassified and blocks readiness", () => {
    const student = targetStudent("stu-U-9f2a", "Sw1", { weeklyScheduleId: UNKNOWN_SCHEDULE_ID });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(report.ready).toBe(false);
  });

  it("counts a schedule user_id mismatch on the linked student and blocks", () => {
    const student = targetStudent("stu-W-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [{ id: student.weeklyScheduleId!, userId: OBSERVER_STUDENT, entries: dudulluSchedule("x").entries }],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.scheduleLinkMismatch).toBe(1);
    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(report.ready).toBe(false);
  });

  it("treats malformed non-array schedule entries as malformed and blocks", () => {
    const student = targetStudent("stu-E-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [{ id: student.weeklyScheduleId!, userId: student.id, entries: { bad: true } }],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.schedules.malformed).toBe(1);
    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("schedule_data_invalid");
  });

  it("treats a non-object schedule entry as malformed and blocks", () => {
    const student = targetStudent("stu-F-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [{ id: student.weeklyScheduleId!, userId: student.id, entries: [42] }],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.schedules.malformed).toBe(1);
    expect(report.ready).toBe(false);
  });

  it("yields ready false with no_dudullu_students when zero targets exist", () => {
    const student = nonDudulluStudent("stu-Z-9f2a");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [{ id: student.id, userId: student.id, entries: [] }],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.dudulluTarget).toBe(0);
    expect(report.students.nonDudulluScheduled).toBe(1);
    expect(report.schedules.empty).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("no_dudullu_students");
  });

  it("treats an empty schedule as a valid non-Dudullu account", () => {
    const target = targetStudent("stu-T2-9f2a", "Sw1");
    const emptyStudent = nonDudulluStudent("stu-E2-9f2a");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target, emptyStudent],
      [
        dudulluSchedule(target.id),
        { id: emptyStudent.id, userId: emptyStudent.id, entries: [] },
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.schedules.empty).toBe(1);
    expect(report.schedules.malformed).toBe(0);
    expect(report.students.nonDudulluScheduled).toBe(1);
    expect(report.ready).toBe(true);
  });

  it("counts orphaned schedule rows and blocks readiness", () => {
    const target = targetStudent("stu-O-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [
        dudulluSchedule(target.id),
        { id: "sch-orphan-9f2a", userId: DRIVER_ID, entries: [] },
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.schedules.orphanedRows).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("schedule_data_invalid");
  });

  it("counts duplicate schedule rows beyond the first per student", () => {
    const target = targetStudent("stu-D-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [
        dudulluSchedule(target.id),
        { id: "sch-D2-9f2a", userId: target.id, entries: [] },
        { id: "sch-D3-9f2a", userId: target.id, entries: [] },
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.schedules.duplicateRowsForStudent).toBe(2);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("schedule_data_invalid");
  });

  it("blocks a target missing its location code with target_profile_incomplete", () => {
    const student = targetStudent("stu-L-9f2a", "Sw1", { locationCode: undefined });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [dudulluSchedule(student.id)],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.targetMissingLocation).toBe(1);
    expect(report.students.completeTargetProfiles).toBe(0);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("target_profile_incomplete");
  });

  it("blocks a target missing its disability type with target_profile_incomplete", () => {
    const student = targetStudent("stu-DIS-9f2a", "Sw1", { disabilityType: undefined });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [dudulluSchedule(student.id)],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.targetMissingDisabilityType).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("target_profile_incomplete");
  });

  it("counts duplicate physical locations as students but one distinct location", () => {
    const first = targetStudent("stu-P1-9f2a", "Sw1");
    const second = targetStudent("stu-P2-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, first, second],
      [
        dudulluSchedule(first.id),
        dudulluSchedule(second.id),
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.students.dudulluTarget).toBe(2);
    expect(report.students.distinctTargetLocations).toBe(1);
    expect(report.matrix.requiredLocationCount).toBe(2);
    expect(report.ready).toBe(true);
  });

  it("reports driver accounts as configuredDrivers without inventing availability", () => {
    const target = targetStudent("stu-G-9f2a", "Sw1");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.fleet.configuredDrivers).toBe(1);
  });

  it("treats an active vehicle with zero total capacity as unusable", () => {
    const target = targetStudent("stu-V0-9f2a", "Sw1");
    const blocked = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      [{ status: "active", wheelchairCapacity: 0, seatingCapacity: 0 }],
      readyMatrix(2),
    );

    expect(blocked.fleet.vehicles).toBe(1);
    expect(blocked.fleet.activeVehicles).toBe(1);
    expect(blocked.fleet.usableActiveVehicles).toBe(0);
    expect(blocked.ready).toBe(false);
    expect(blocked.reasonCodes).toContain("no_usable_active_vehicle");

    const allowed = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      [
        { status: "active", wheelchairCapacity: 0, seatingCapacity: 0 },
        { status: "active", wheelchairCapacity: 0, seatingCapacity: 5 },
      ],
      readyMatrix(2),
    );
    expect(allowed.fleet.usableActiveVehicles).toBe(1);
    expect(allowed.ready).toBe(true);
  });

  it("never mutates its input objects", () => {
    const student = Object.freeze(targetStudent("stu-FZ-9f2a", "Sw1"));
    const schedule = Object.freeze({
      id: Object.freeze(student.weeklyScheduleId! as unknown as string),
      userId: Object.freeze(student.id as unknown as string),
      entries: Object.freeze([
        Object.freeze({
          id: "cl-9f2a",
          dayOfWeek: "wednesday",
          startTime: "09:00",
          endTime: "10:00",
          location: "Dudullu",
        }),
      ]),
    });
    const vehicle = Object.freeze({ status: "active", wheelchairCapacity: 1, seatingCapacity: 7 });
    const matrix = Object.freeze(readyMatrix(2));

    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [schedule],
      [vehicle],
      matrix,
    );

    expect(report.ready).toBe(true);
    expect(requiredDudulluStudentLocations([...READY_DRIVERS, student], [schedule])).toEqual(["Sw1"]);
  });

  it("serializes none of the sentinel identities or location codes", () => {
    const target = targetStudent("stu-SENTINEL-9f2a", "SwSECRET-9f2a");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      readyVehicles(),
      readyMatrix(2),
    );
    const serialized = JSON.stringify(report);

    for (const forbidden of [
      "stu-SENTINEL-9f2a",
      "drv-9f2a-driver",
      "SwSECRET-9f2a",
      "sch-9f2a-nowhere",
      "cl-9f2a",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });

  it("emits reason codes in the approved order from the fixed allowlist", () => {
    const student = nonDudulluStudent("stu-R-9f2a", { weeklyScheduleId: undefined });
    const report = analyzeDudulluReadiness(
      [student],
      [],
      [{ status: "inactive", wheelchairCapacity: 1, seatingCapacity: 7 }],
      {
        source: "empty",
        loaded: false,
        stale: false,
        hasError: true,
        matrixLocationCount: 0,
        requiredLocationCount: 0,
        missingRequiredLocationCount: 0,
        expectedRequiredDirectedArcCount: 0,
        validRequiredDirectedArcCount: 0,
        invalidOrMissingRequiredDirectedArcCount: 0,
        depotPresent: false,
        complete: false,
        ready: false,
      },
    );

    expect(report.reasonCodes).toEqual([
      "no_dudullu_students",
      "schedule_classification_incomplete",
      "no_configured_driver",
      "no_usable_active_vehicle",
      "matrix_unavailable",
      "matrix_location_mismatch",
    ]);
  });

  it("never classifies a Dudullu home location as a target without a qualifying schedule", () => {
    const homeOnly = targetStudent("stu-HOME-9f2a", "Dudullu", {
      weeklyScheduleId: undefined,
    });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, homeOnly],
      [],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.dudulluTarget).toBe(0);
    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(report.students.distinctTargetLocations).toBe(0);
    expect(
      requiredDudulluStudentLocations([homeOnly], []),
    ).toEqual([]);
    expect(report.reasonCodes).toContain("no_dudullu_students");
  });

  it("does not count a mismatched Dudullu schedule as a target or matrix requirement", () => {
    const student = targetStudent("stu-MM-9f2a", "Sw1");
    const mismatched = {
      id: student.weeklyScheduleId!,
      userId: OBSERVER_STUDENT,
      entries: dudulluSchedule("x").entries,
    };
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [mismatched],
      readyVehicles(),
      readyMatrix(1),
    );

    expect(report.students.dudulluTarget).toBe(0);
    expect(report.students.scheduleLinkMismatch).toBe(1);
    expect(report.students.unclassifiedSchedule).toBe(1);
    expect(
      requiredDudulluStudentLocations([student], [mismatched]),
    ).toEqual([]);
  });

  it("treats entries with a missing or non-string or blank location as malformed", () => {
    const malformedCases: unknown[][] = [
      [{}],
      [{ id: "c-9f2a" }],
      [{ id: "c-9f2a", location: "" }],
      [{ id: "c-9f2a", location: "   " }],
      [{ id: "c-9f2a", location: 42 }],
    ];
    for (const entries of malformedCases) {
      const student = targetStudent("stu-MF-9f2a", "Sw1");
      const report = analyzeDudulluReadiness(
        [...READY_DRIVERS, student],
        [{ id: student.weeklyScheduleId!, userId: student.id, entries }],
        readyVehicles(),
        readyMatrix(1),
      );

      expect(report.schedules.malformed).toBe(1);
      expect(report.students.unclassifiedSchedule).toBe(1);
      expect(report.students.dudulluTarget).toBe(0);
      expect(report.reasonCodes).toContain("schedule_data_invalid");
    }
  });

  it("rejects an invalid nonblank disability type on a target profile", () => {
    const student = targetStudent("stu-DINV-9f2a", "Sw1", {
      disabilityType: "unknown",
    });
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, student],
      [dudulluSchedule(student.id)],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.students.dudulluTarget).toBe(1);
    expect(report.students.completeTargetProfiles).toBe(0);
    expect(report.students.targetMissingDisabilityType).toBe(1);
    expect(report.ready).toBe(false);
    expect(report.reasonCodes).toContain("target_profile_incomplete");
  });

  it("reports allAccounts and the full approved report DTO", () => {
    const target = targetStudent("stu-DTO-9f2a", "Sw1");
    const plain = nonDudulluStudent("stu-DTO2-9f2a");
    const report = analyzeDudulluReadiness(
      [...READY_DRIVERS, target, plain],
      [
        dudulluSchedule(target.id),
        { id: plain.id, userId: plain.id, entries: [] },
      ],
      readyVehicles(),
      readyMatrix(2),
    );

    expect(report.students.allAccounts).toBe(2);
    expect(report.students.dudulluTarget).toBe(1);
    expect(report.students.nonDudulluScheduled).toBe(1);
    expect(Object.keys(report.schedules)).toEqual([
      "total",
      "empty",
      "malformed",
      "orphanedRows",
      "duplicateRowsForStudent",
    ]);
    expect("dudulluTargetRows" in report.schedules).toBe(false);
    expect("nonDudulluScheduledRows" in report.schedules).toBe(false);
    expect("isWithinDeviation" in report.historicalExpectation).toBe(false);
    expect(report.matrix.expectedRequiredDirectedArcCount).toBe(2);
    expect(report.matrix.validRequiredDirectedArcCount).toBe(2);
    expect(report.matrix.depotPresent).toBe(true);
    expect(report.matrix.ready).toBe(true);
  });

  it("derives matchesMatrixNodeCount from matrixLocationCount === 29", () => {
    const target = targetStudent("stu-29-9f2a", "Sw1");

    const exact = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      readyVehicles(),
      readyMatrix(2, 29),
    );
    expect(exact.historicalExpectation.matchesMatrixNodeCount).toBe(true);

    const shifted = analyzeDudulluReadiness(
      [...READY_DRIVERS, target],
      [dudulluSchedule(target.id)],
      readyVehicles(),
      readyMatrix(2, 30),
    );
    expect(shifted.historicalExpectation.matchesMatrixNodeCount).toBe(false);
  });
});

describe("requiredDudulluStudentLocations", () => {
  it("returns deduplicated trimmed home codes for Dudullu targets only", () => {
    const first = targetStudent("stu-H1-9f2a", "Sw1");
    const second = targetStudent("stu-H2-9f2a", " Sw1 ");
    const third = targetStudent("stu-H3-9f2a", "So1");
    const other = nonDudulluStudent("stu-H4-9f2a");
    const unclassified = targetStudent("stu-H5-9f2a", "So2", { weeklyScheduleId: undefined });

    const codes = requiredDudulluStudentLocations(
      [first, second, third, other, unclassified],
      [
        dudulluSchedule(first.id),
        dudulluSchedule(second.id),
        dudulluSchedule(third.id),
        { id: other.id, userId: other.id, entries: [] },
      ],
    );

    expect(codes).toEqual(["Sw1", "So1"]);
  });

  it("returns an empty list when no Dudullu targets have a location", () => {
    const missing = targetStudent("stu-H6-9f2a", "Sw1", { locationCode: undefined });
    const other = nonDudulluStudent("stu-H7-9f2a");

    expect(
      requiredDudulluStudentLocations([missing, other], [dudulluSchedule(missing.id)]),
    ).toEqual([]);
  });
});