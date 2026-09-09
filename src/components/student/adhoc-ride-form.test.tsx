// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  addRideRequest: vi.fn(),
  toast: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => ({
    defaultDropoff: "Doğuş University, Dudullu Campus",
    successTitle: "success",
    successDesc: "saved",
    errorTitle: "error",
    errorDesc: "failed",
    dateLabel: "date",
    datePlaceholder: "date",
    pickupTimeLabel: "pickup time",
    pickupAddressLabel: "pickup address",
    pickupPlaceholder: "pickup address",
    pickupAddressDesc: "pickup description",
    dropoffAddressLabel: "dropoff address",
    dropoffPlaceholder: "dropoff address",
    dropoffAddressDesc: "dropoff description",
    notesLabel: "notes",
    notesPlaceholder: "notes",
    submitButton: "submit",
  }[key] ?? key),
}));

vi.mock("@/lib/database", () => ({
  addRideRequest: mocks.addRideRequest,
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: mocks.toast }),
}));

vi.mock("@/components/ui/popover", () => ({
  Popover: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/ui/calendar", () => ({
  Calendar: ({ onSelect }: { onSelect: (date: Date) => void }) => (
    <button type="button" onClick={() => onSelect(new Date("2099-01-01T12:00:00"))}>choose date</button>
  ),
}));

import AdhocRideForm from "./adhoc-ride-form";

describe("AdhocRideForm", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.addRideRequest.mockReset();
    mocks.addRideRequest.mockResolvedValue({ id: "ride-1" });
    mocks.toast.mockReset();
  });

  it("submits the Dudullu default dropoff unchanged", async () => {
    const { container } = render(<AdhocRideForm userId="student-1" defaultPickupAddress="Student home" />);
    fireEvent.click(screen.getByRole("button", { name: "choose date" }));
    fireEvent.change(container.querySelector('input[type="time"]')!, { target: { value: "09:00" } });
    fireEvent.click(screen.getByRole("button", { name: "submit" }));

    await waitFor(() => expect(mocks.addRideRequest).toHaveBeenCalledWith(expect.objectContaining({
      dropoffLocation: { address: "Doğuş University, Dudullu Campus" },
    })));
  });
});
