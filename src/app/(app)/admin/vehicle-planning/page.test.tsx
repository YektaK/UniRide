// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getAllUsers: vi.fn(),
  calculate: vi.fn(),
  saveRoutePlan: vi.fn(),
  getAuthToken: vi.fn(),
  toast: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: mocks.toast }),
}));

vi.mock("@/lib/admin-api", () => ({
  adminApi: {
    users: { getAll: mocks.getAllUsers },
    vehicles: { calculate: mocks.calculate },
  },
  getAuthToken: mocks.getAuthToken,
}));

// Only the network save seam is replaced; formatRoutePlanForSave stays real so
// the production direction guard is the code under test.
vi.mock("@/services/route-plans", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/services/route-plans")>();
  return { ...actual, saveRoutePlan: mocks.saveRoutePlan };
});

vi.mock("@/components/ui/select", () => ({
  Select: ({ value, onValueChange, children }: any) => {
    const isDirection = value === "pickup" || value === "dropoff";
    return (
      <select
        data-testid={isDirection ? "direction-control" : "param-control"}
        value={value}
        onChange={(event) => onValueChange?.(event.target.value)}
      >
        {children}
      </select>
    );
  },
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ value, children }: any) => <option value={value}>{children ?? value}</option>,
  SelectTrigger: () => null,
  SelectValue: () => null,
}));

vi.mock("@/components/ui/checkbox", () => ({
  Checkbox: ({ id, checked, onCheckedChange }: any) => (
    <input
      type="checkbox"
      aria-label={id}
      checked={Boolean(checked)}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
    />
  ),
}));

import VehiclePlanningPage from "./page";

const students = [
  { id: "student-1", name: "S1", role: "student", disabilityType: "So" as const, locationCode: "L1" },
];

// Realistic successful DUD-01 payload: direction, requiredVehicles, assignments,
// totalDuration and meta, mirroring the BFF success response.
const resultOk = {
  success: true,
  requiredVehicles: 1,
  totalDuration: 10,
  meta: { validStudentCount: 1 },
  assignments: [
    {
      vehicleIndex: 1,
      students: [{ id: "student-1", locationCode: "L1", disabilityType: "So" }],
      route: [],
      totalDuration: 10,
      swCount: 0,
      soCount: 1,
    },
  ],
  message: "ok",
};

const resultPickup = { ...resultOk, direction: "pickup" as const };

describe("VehiclePlanningPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.getAllUsers.mockReset();
    mocks.calculate.mockReset();
    mocks.saveRoutePlan.mockReset();
    mocks.getAuthToken.mockReset();
    mocks.toast.mockReset();
  });

  async function selectStudentAndCalculate(directionOverride: "pickup" | "dropoff" = "pickup") {
    render(<VehiclePlanningPage />);
    await screen.findByLabelText("student-1");
    fireEvent.click(screen.getByLabelText("student-1"));

    const directionControl = screen.getByTestId("direction-control");
    if (directionOverride !== "pickup") {
      fireEvent.change(directionControl, { target: { value: directionOverride } });
    }

    fireEvent.click(screen.getByRole("button", { name: /selectAll/ }));
    await waitFor(() => expect(mocks.calculate).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ title: "success" })));
  }

  it("calculates through the authenticated helper with the selected direction", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue(resultPickup);

    await selectStudentAndCalculate("pickup");

    expect(mocks.calculate).toHaveBeenCalledWith(
      expect.objectContaining({
        direction: "pickup",
        strategy: "genetic_algorithm",
        clusteringAlgorithm: "sweep",
      })
    );
  });

  it("calculates and saves dropoff even after the selector changes to pickup", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue({ ...resultOk, direction: "dropoff" });

    await selectStudentAndCalculate("dropoff");

    expect(mocks.calculate).toHaveBeenCalledWith(expect.objectContaining({ direction: "dropoff" }));
    fireEvent.change(screen.getByTestId("direction-control"), { target: { value: "pickup" } });
    fireEvent.click(screen.getByRole("button", { name: /save/ }));
    await waitFor(() => expect(mocks.saveRoutePlan).toHaveBeenCalledTimes(1));
    expect(mocks.saveRoutePlan).toHaveBeenCalledWith(expect.objectContaining({ direction: "dropoff" }));
  });

  it("persists the calculation-time direction even after the selector changes", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue(resultPickup);

    await selectStudentAndCalculate("pickup");

    fireEvent.change(screen.getByTestId("direction-control"), { target: { value: "dropoff" } });
    fireEvent.click(screen.getByRole("button", { name: /save/ }));

    await waitFor(() => expect(mocks.saveRoutePlan).toHaveBeenCalledTimes(1));
    expect(mocks.saveRoutePlan).toHaveBeenCalledWith(expect.objectContaining({ direction: "pickup" }));
  });

  it.each([
    ["that omits the result direction", { ...resultOk }],
    ["with an invalid result direction", { ...resultOk, direction: "sideways" }],
    ["with a direction conflicting with the request", { ...resultOk, direction: "dropoff" }],
  ])("blocks saving a result %s", async (_label, fixture) => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue(fixture as typeof resultOk & { direction?: string });

    await selectStudentAndCalculate("pickup");

    fireEvent.click(screen.getByRole("button", { name: /save/ }));

    await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ variant: "destructive" })));
    expect(mocks.saveRoutePlan).not.toHaveBeenCalled();
  });
});
