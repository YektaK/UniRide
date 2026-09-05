import { describe, expect, it } from "vitest";
import type { DudulluReadinessReport } from "./dudullu-readiness";
import { parseDudulluReadinessReport } from "./dudullu-readiness-response";

const validReport: DudulluReadinessReport = {
  ready: true,
  reasonCodes: [],
  students: {
    allAccounts: 28,
    dudulluTarget: 28,
    nonDudulluScheduled: 0,
    unclassifiedSchedule: 0,
    completeTargetProfiles: 28,
    targetMissingLocation: 0,
    targetMissingDisabilityType: 0,
    scheduleLinkMismatch: 0,
    distinctTargetLocations: 28,
  },
  schedules: {
    total: 28,
    empty: 0,
    malformed: 0,
    orphanedRows: 0,
    duplicateRowsForStudent: 0,
  },
  fleet: {
    configuredDrivers: 1,
    vehicles: 1,
    activeVehicles: 1,
    usableActiveVehicles: 1,
  },
  matrix: {
    source: "supabase",
    loaded: true,
    stale: false,
    hasError: false,
    matrixLocationCount: 29,
    complete: true,
    ready: true,
    requiredLocationCount: 29,
    expectedRequiredDirectedArcCount: 812,
    validRequiredDirectedArcCount: 812,
    missingRequiredLocationCount: 0,
    invalidOrMissingRequiredDirectedArcCount: 0,
    depotPresent: true,
  },
  historicalExpectation: {
    studentCount: 28,
    matrixNodeCount: 29,
    matchesStudentCount: true,
    matchesMatrixNodeCount: true,
  },
};

describe("parseDudulluReadinessReport", () => {
  it("parses the complete report and strips unexpected fields", () => {
    const parsed = parseDudulluReadinessReport({
      ...validReport,
      studentNames: ["must-not-cross-boundary"],
      students: { ...validReport.students, homeAddresses: ["secret"] },
    });

    expect(parsed).toEqual(validReport);
    expect(parsed).not.toHaveProperty("studentNames");
    expect(parsed.students).not.toHaveProperty("homeAddresses");
  });

  it.each([
    { ...validReport, reasonCodes: ["unrecognized_reason"] },
    { ...validReport, students: { ...validReport.students, allAccounts: -1 } },
    { ...validReport, students: { ...validReport.students, allAccounts: 1.5 } },
    { ...validReport, matrix: { ...validReport.matrix, source: "unknown" } },
    { ...validReport, fleet: undefined },
    { ...validReport, matrix: { ...validReport.matrix, depotPresent: undefined } },
  ])("rejects malformed response", (input) => {
    expect(() => parseDudulluReadinessReport(input)).toThrow(
      "Invalid Dudullu readiness response",
    );
  });
});
