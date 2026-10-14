// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getAll: vi.fn(),
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
  adminApi: { users: { getAll: mocks.getAll } },
  getAuthToken: mocks.getAuthToken,
}));

vi.mock("@/components/ui/select", () => ({
  Select: ({ children }: any) => <div>{children}</div>,
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ children }: any) => <div>{children}</div>,
  SelectTrigger: () => null,
  SelectValue: () => null,
}));

import AlgorithmComparisonPage from "./page";

const row = (algorithm: string, minutes: number, extra: Record<string, unknown> = {}) => ({
  algorithm,
  success: true,
  routes: [],
  total_vehicles: 1,
  total_duration_minutes: minutes,
  execution_time_seconds: 0.5,
  ...extra,
});

async function runComparison(results: unknown[], extra: Record<string, unknown> = {}) {
  mocks.getAll.mockResolvedValue([{ id: "s1", role: "student" }]);
  mocks.getAuthToken.mockResolvedValue("token");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      success: true,
      results,
      best_algorithm: "ga",
      fastest_algorithm: "ga",
      summary: {},
      ...extra,
    }),
  }));

  render(<AlgorithmComparisonPage />);
  const button = await screen.findByRole("button", { name: /selectAll/ });
  await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(button);
  await screen.findByText("BEST");
}

describe("AlgorithmComparisonPage fallback rows (M26)", () => {
  beforeEach(() => {
    mocks.getAll.mockReset();
    mocks.getAuthToken.mockReset();
    mocks.toast.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("labels a fallback row as greedy fallback with its reason code instead of a plain success", async () => {
    await runComparison([
      row("ga", 50),
      row("e2bso", 10, { algorithm_executed: "greedy_fallback", fallback_reason: "solver_error" }),
    ]);

    const fallbackRow = screen.getByText("e2bso").closest("tr") as HTMLElement;
    expect(within(fallbackRow).getByText(/greedyFallback/)).toBeTruthy();
    expect(within(fallbackRow).getByText(/solver_error/)).toBeTruthy();
    expect(within(fallbackRow).queryByText("success")).toBeNull();
  });

  it("keeps the plain success badge for a row that ran its own algorithm", async () => {
    await runComparison([row("ga", 50), row("e2bso", 10, { algorithm_executed: "greedy_fallback", fallback_reason: "solver_error" })]);

    const normalRow = screen.getByText("ga", { selector: "td" }).closest("tr") as HTMLElement;
    expect(within(normalRow).getByText("success")).toBeTruthy();
    expect(within(normalRow).queryByText(/greedyFallback/)).toBeNull();
  });
});
