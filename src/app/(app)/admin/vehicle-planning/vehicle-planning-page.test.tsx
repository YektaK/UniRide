// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ toast: vi.fn() }));

// The mocked translator returns the key, so the assertions pin which i18n key
// the page uses (the same common.* keys as the compare and sandbox pages).
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: mocks.toast }),
}));

vi.mock("@/components/ui/select", () => ({
  Select: ({ children }: any) => <>{children}</>,
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ children }: any) => <>{children}</>,
  SelectTrigger: ({ children }: any) => <>{children}</>,
  SelectValue: () => null,
}));

vi.mock("@/components/ui/checkbox", () => ({
  Checkbox: ({ id, checked, onCheckedChange }: any) => (
    <input
      type="checkbox"
      aria-label={id}
      checked={!!checked}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
    />
  ),
}));

import VehiclePlanningPage from "./vehicle-planning-page";

function respondWith(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

async function calculate() {
  render(<VehiclePlanningPage />);
  fireEvent.click(screen.getByText("Tümü", { selector: "button" }));
  fireEvent.click(screen.getByText("Hesapla", { selector: "button" }));
  await waitFor(() => expect(mocks.toast).toHaveBeenCalled());
  return mocks.toast.mock.calls.at(-1)![0];
}

describe("vehicle planning matrix errors", () => {
  beforeEach(() => mocks.toast.mockReset());
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the common.matrixUnavailable message for a matrix outage", async () => {
    respondWith(503, { error: "travel-time matrix unavailable", code: "travel_time_matrix_unavailable" });
    const toast = await calculate();
    expect(toast.description).toBe("matrixUnavailable");
  });

  it("shows the common.matrixLocationsMissing message for unknown locations", async () => {
    respondWith(422, { error: "locations missing", code: "travel_time_matrix_locations_missing" });
    const toast = await calculate();
    expect(toast.description).toBe("matrixLocationsMissing");
  });

  it("keeps the generic message for other failures", async () => {
    respondWith(500, { error: "boom" });
    const toast = await calculate();
    expect(toast.description).toBe("Hesaplama başarısız");
  });
});
