// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";

const mocks = vi.hoisted(() => ({
  getDudullu: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/admin-api", () => ({
  adminApi: {
    readiness: {
      getDudullu: mocks.getDudullu,
    },
  },
  DudulluReadinessRequestError: class DudulluReadinessRequestError extends Error {
    constructor(public readonly kind: "authorization" | "configuration") {
      super("Dudullu readiness request failed");
    }
  },
}));

import ReadinessPage from "./page";
import { DudulluReadinessRequestError } from "@/lib/admin-api";

const report: DudulluReadinessReport = {
  ready: true,
  reasonCodes: [],
  students: {
    allAccounts: 30,
    dudulluTarget: 28,
    nonDudulluScheduled: 2,
    unclassifiedSchedule: 0,
    completeTargetProfiles: 28,
    targetMissingLocation: 0,
    targetMissingDisabilityType: 0,
    scheduleLinkMismatch: 0,
    distinctTargetLocations: 28,
  },
  schedules: { total: 30, empty: 0, malformed: 0, orphanedRows: 0, duplicateRowsForStudent: 0 },
  fleet: { configuredDrivers: 2, vehicles: 2, activeVehicles: 2, usableActiveVehicles: 2 },
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

describe("ReadinessPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.getDudullu.mockReset();
  });

  it("renders a passing aggregate readiness report", async () => {
    mocks.getDudullu.mockResolvedValue(report);

    render(<ReadinessPage />);

    expect(await screen.findByText("status.passTitle")).toBeTruthy();
    expect(screen.getByText("fields.allAccounts: 30")).toBeTruthy();
  });

  it("renders blocked-data reasons from a failing aggregate readiness report", async () => {
    mocks.getDudullu.mockResolvedValue({ ...report, ready: false, reasonCodes: ["matrix_incomplete"] });

    render(<ReadinessPage />);

    expect(await screen.findByText("status.blockedDataTitle")).toBeTruthy();
    expect(screen.getByText("reasons.matrix_incomplete")).toBeTruthy();
  });

  it("renders an authorization error", async () => {
    mocks.getDudullu.mockRejectedValue(new DudulluReadinessRequestError("authorization"));

    render(<ReadinessPage />);

    expect(await screen.findByText("errors.authorization")).toBeTruthy();
  });

  it("renders a configuration error for an explicit configuration failure", async () => {
    mocks.getDudullu.mockRejectedValue(new DudulluReadinessRequestError("configuration"));

    render(<ReadinessPage />);

    expect(await screen.findByText("errors.configuration")).toBeTruthy();
  });

  it("fails closed to a configuration error for an unknown failure", async () => {
    mocks.getDudullu.mockRejectedValue(new Error("unexpected"));

    render(<ReadinessPage />);

    expect(await screen.findByText("errors.configuration")).toBeTruthy();
  });

  it("keeps refresh disabled and avoids duplicate calls while the request is unresolved", () => {
    mocks.getDudullu.mockReturnValue(new Promise(() => undefined));

    render(<ReadinessPage />);

    const refresh = screen.getByRole("button", { name: "Yenile" });
    expect((refresh as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(refresh);
    expect(mocks.getDudullu).toHaveBeenCalledTimes(1);
  });
});
