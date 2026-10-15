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

// Fixture mirrors the real GET /api/admin/users payload: raw `users` rows from
// select("*") (src/app/api/admin/users/route.ts), i.e. snake_case columns
// (src/types/db.ts). A camelCase fixture here hid audit finding H15.
const students = [
  { id: "student-1", name: "S1", role: "student", disability_type: "So" as const, location_code: "L1" },
];

const mixedStudents = [
  ...students,
  { id: "student-2", name: "S2", role: "student", disability_type: "Sw" as const, location_code: "L2" },
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

  it("counts a wheelchair user returned by the API as Sw, not So (H15)", async () => {
    mocks.getAllUsers.mockResolvedValue(mixedStudents);
    mocks.calculate.mockResolvedValue(resultPickup);

    render(<VehiclePlanningPage />);
    await screen.findByLabelText("student-2");

    // "Sw" quick-select must pick exactly the wheelchair student.
    fireEvent.click(screen.getByRole("button", { name: "Sw" }));
    expect(screen.getByLabelText("student-2")).toHaveProperty("checked", true);
    expect(screen.getByLabelText("student-1")).toHaveProperty("checked", false);
    expect(screen.getByText(/1 Sw,\s*0 So\)/)).toBeTruthy();

    // Select the rest: counts must split 1 Sw / 1 So, and the optimizer input
    // must carry the wheelchair flag.
    fireEvent.click(screen.getByRole("button", { name: "So" }));
    expect(screen.getByText(/1 Sw,\s*1 So\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /selectAll/ }));
    await waitFor(() => expect(mocks.calculate).toHaveBeenCalledTimes(1));
    const payload = mocks.calculate.mock.calls[0][0] as { students: Array<{ id: string; disabilityType?: string }> };
    expect(payload.students.find((s) => s.id === "student-2")?.disabilityType).toBe("Sw");
    expect(payload.students.find((s) => s.id === "student-1")?.disabilityType).toBe("So");
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

  it("saves a SOTA fallback plan as greedy_fallback, not as the selected strategy (M26)", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue({
      ...resultPickup,
      meta: {
        ...resultPickup.meta,
        algorithmUsed: "greedy_fallback",
        algorithmRequested: "genetic_algorithm",
        fallbackReason: "solver_error",
      },
    });

    await selectStudentAndCalculate("pickup");

    fireEvent.click(screen.getByRole("button", { name: /save/ }));
    await waitFor(() => expect(mocks.saveRoutePlan).toHaveBeenCalledTimes(1));
    expect(mocks.saveRoutePlan).toHaveBeenCalledWith(
      expect.objectContaining({ algorithmUsed: "greedy_fallback" }),
    );
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

describe("VehiclePlanningPage solver provenance", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.getAllUsers.mockReset();
    mocks.calculate.mockReset();
    mocks.saveRoutePlan.mockReset();
    mocks.toast.mockReset();
  });

  async function calculate() {
    render(<VehiclePlanningPage />);
    await screen.findByLabelText("student-1");
    fireEvent.click(screen.getByLabelText("student-1"));
    fireEvent.click(screen.getByRole("button", { name: /selectAll/ }));
    await waitFor(() => expect(mocks.calculate).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ title: "success" })));
  }

  it("shows the provenance line and saves the same provenance", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue({
      ...resultPickup,
      meta: { ...resultPickup.meta, algorithmUsed: "ga_split", algorithmRequested: "ga_split", effectiveConfigSource: "default", effectiveSeed: 42 },
    });

    await calculate();

    expect(await screen.findByTestId("solver-provenance")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /save/ }));
    await waitFor(() => expect(mocks.saveRoutePlan).toHaveBeenCalledTimes(1));
    expect(mocks.saveRoutePlan).toHaveBeenCalledWith(
      expect.objectContaining({
        solverProvenance: {
          algorithm_requested: "ga_split",
          algorithm_used: "genetic_algorithm",
          effective_config_source: "default",
          effective_seed: 42,
        },
      }),
    );
  });

  it("shows no provenance line and sends none for an older optimizer", async () => {
    mocks.getAllUsers.mockResolvedValue(students);
    mocks.calculate.mockResolvedValue(resultPickup);

    await calculate();

    expect(screen.queryByTestId("solver-provenance")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /save/ }));
    await waitFor(() => expect(mocks.saveRoutePlan).toHaveBeenCalledTimes(1));
    expect(mocks.saveRoutePlan.mock.calls[0]![0]).not.toHaveProperty("solverProvenance");
  });
});
