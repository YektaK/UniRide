// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getAllRouteAssignments: vi.fn(),
  getAllVehicles: vi.fn(),
  getAllUsers: vi.fn(),
}));

vi.mock("next-intl", () => ({ useTranslations: () => (key: string) => key }));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock("@/lib/database", () => ({
  getAllRouteAssignments: mocks.getAllRouteAssignments,
  getAllVehicles: mocks.getAllVehicles,
  getAllUsers: mocks.getAllUsers,
}));
vi.mock("@/services/excel/driver-export", () => ({
  exportDriverAssignmentsToExcel: vi.fn(),
  exportDriverAssignmentsToPDF: vi.fn(),
}));

import DriverAssignmentsPage from "./page";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function assignment(id: string, vehicleId: string) {
  return {
    id,
    date: "2026-10-01",
    vehicleId,
    driverId: undefined,
    routeId: "r",
    studentIds: [],
    pickupTime: "2026-10-01T07:00:00.000Z",
    estimatedDropoffTime: "2026-10-01T08:00:00.000Z",
    status: "scheduled",
  };
}

describe("admin drivers page stale responses (M7)", () => {
  beforeEach(() => {
    mocks.getAllRouteAssignments.mockReset();
    mocks.getAllVehicles.mockReset().mockResolvedValue([
      { id: "vA", name: "Vehicle-A" },
      { id: "vB", name: "Vehicle-B" },
    ]);
    mocks.getAllUsers.mockReset().mockResolvedValue([]);
  });
  afterEach(() => cleanup());

  it("keeps the newest date's data when an older request resolves last", async () => {
    const first = deferred<unknown[]>();
    const second = deferred<unknown[]>();
    mocks.getAllRouteAssignments
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const { container } = render(<DriverAssignmentsPage />);
    const dateInput = container.querySelector('input[type="date"]') as HTMLInputElement;
    const initialDate = dateInput.value;
    const newDate = initialDate === "2030-01-02" ? "2030-01-03" : "2030-01-02";
    fireEvent.change(dateInput, { target: { value: newDate } });

    await waitFor(() => expect(mocks.getAllRouteAssignments).toHaveBeenCalledTimes(2));
    expect(mocks.getAllRouteAssignments).toHaveBeenNthCalledWith(1, { date: initialDate });
    expect(mocks.getAllRouteAssignments).toHaveBeenNthCalledWith(2, { date: newDate });

    // The newer request (date B) answers first, then the stale one (date A) arrives late.
    second.resolve([assignment("b1", "vB")]);
    await waitFor(() => expect(screen.getAllByText("Vehicle-B").length).toBeGreaterThan(0));
    first.resolve([assignment("a1", "vA")]);
    await new Promise((r) => setTimeout(r, 20));

    expect(screen.queryAllByText("Vehicle-A")).toHaveLength(0);
    expect(screen.getAllByText("Vehicle-B").length).toBeGreaterThan(0);
  });
});
