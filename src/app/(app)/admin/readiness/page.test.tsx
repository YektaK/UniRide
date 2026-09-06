// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    mocks.getDudullu.mockResolvedValue({
      ...report,
      historicalExpectation: { ...report.historicalExpectation, matchesMatrixNodeCount: false },
    });

    render(<ReadinessPage />);

    expect(await screen.findByText("status.passTitle")).toBeTruthy();
    expect(screen.getByText("labels.allAccounts: 30")).toBeTruthy();
    expect(screen.getByText("labels.dudulluTarget: 28")).toBeTruthy();
    expect(screen.getByText("labels.completeTargetProfiles: 28")).toBeTruthy();
    expect(screen.getByText("labels.unclassifiedSchedule: 0")).toBeTruthy();
    expect(screen.getByText("labels.scheduleTotal: 30")).toBeTruthy();
    expect(screen.getByText("labels.scheduleEmpty: 0")).toBeTruthy();
    expect(screen.getByText("labels.scheduleMalformed: 0")).toBeTruthy();
    expect(screen.getByText("labels.configuredDrivers: 2")).toBeTruthy();
    expect(screen.getByText("labels.activeVehicles: 2")).toBeTruthy();
    expect(screen.getByText("labels.usableActiveVehicles: 2")).toBeTruthy();
    expect(screen.getByText("labels.matrixSource: matrixSources.supabase")).toBeTruthy();
    expect(screen.getByText("labels.matrixLocationCount: 29")).toBeTruthy();
    expect(screen.getByText("labels.requiredLocationCount: 29")).toBeTruthy();
    expect(screen.getByText("labels.validArcCount: 812")).toBeTruthy();
    expect(screen.getByText("labels.expectedArcCount: 812")).toBeTruthy();
    expect(screen.getByText("labels.expectedStudents: 28")).toBeTruthy();
    expect(screen.getByText("labels.expectedMatrixNodes: 29")).toBeTruthy();
    expect(screen.getByText("labels.matchesStudents: boolean.yes")).toBeTruthy();
    expect(screen.getByText("labels.matchesMatrix: boolean.no")).toBeTruthy();
    expect(screen.queryByText("fields.allAccounts: 30")).toBeNull();
    expect(screen.queryByText("values.yes")).toBeNull();
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

    expect(await screen.findByText("status.blockedConfigTitle")).toBeTruthy();
    expect(screen.getByText("errors.authorization")).toBeTruthy();
  });

  it("renders a configuration error for an explicit configuration failure", async () => {
    mocks.getDudullu.mockRejectedValue(new DudulluReadinessRequestError("configuration"));

    render(<ReadinessPage />);

    expect(await screen.findByText("status.blockedConfigTitle")).toBeTruthy();
    expect(screen.getByText("errors.configuration")).toBeTruthy();
  });

  it("fails closed to a configuration error for an unknown failure", async () => {
    mocks.getDudullu.mockRejectedValue(new Error("unexpected"));

    render(<ReadinessPage />);

    expect(await screen.findByText("errors.configuration")).toBeTruthy();
  });

  it("fails closed and releases refresh when API invocation throws synchronously", async () => {
    mocks.getDudullu.mockImplementation(() => {
      throw new Error("unexpected");
    });

    render(<ReadinessPage />);

    expect(await screen.findByText("errors.configuration")).toBeTruthy();
    const refresh = screen.getByRole("button", { name: "refresh" });
    expect((refresh as HTMLButtonElement).disabled).toBe(false);

    mocks.getDudullu.mockResolvedValue(report);
    fireEvent.click(refresh);

    await waitFor(() => expect(mocks.getDudullu).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("status.passTitle")).toBeTruthy();
  });

  it("shows loading and disables refresh while a refresh request is unresolved", async () => {
    mocks.getDudullu
      .mockResolvedValueOnce(report)
      .mockReturnValueOnce(new Promise(() => undefined));

    render(<ReadinessPage />);

    await screen.findByText("status.passTitle");
    const refresh = screen.getByRole("button", { name: "refresh" });
    fireEvent.click(refresh);

    expect(screen.getByText("loading")).toBeTruthy();
    expect((refresh as HTMLButtonElement).disabled).toBe(true);
    await waitFor(() => expect(mocks.getDudullu).toHaveBeenCalledTimes(2));
  });

  it("keeps refresh disabled and avoids duplicate calls while the request is unresolved", async () => {
    mocks.getDudullu.mockReturnValue(new Promise(() => undefined));

    render(<ReadinessPage />);

    expect(screen.getByText("loading")).toBeTruthy();
    const refresh = screen.getByRole("button", { name: "refresh" });
    expect((refresh as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(refresh);
    await waitFor(() => expect(mocks.getDudullu).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("status.loading")).toBeNull();
    expect(screen.queryByRole("button", { name: "Yenile" })).toBeNull();
  });
});
