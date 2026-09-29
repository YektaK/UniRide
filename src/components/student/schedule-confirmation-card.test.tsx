// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ toast: vi.fn(), getSession: vi.fn() }));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) =>
    values?.direction ? `${key} ${values.direction}` : key,
}));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: mocks.toast }) }));
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => ({ user: { id: "student-1" } }) }));
vi.mock("@/lib/supabase", () => ({ getSupabaseClient: () => ({ auth: { getSession: mocks.getSession } }) }));

import ScheduleConfirmationCard from "./schedule-confirmation-card";

type Decision = "pending" | "confirmed" | "cancelled";
const props = {
  studentName: "Student",
  pickupTime: "08:30",
  dropoffTime: "17:15",
  notificationMessage: "Service available",
  relevantDate: "Wednesday",
  rideDate: "2026-09-30",
};

describe("ScheduleConfirmationCard", () => {
  let decisions: Record<"pickup" | "dropoff", Decision>;
  let admissions: Record<"pickup" | "dropoff", string>;
  let legacyBlocker: boolean;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    decisions = { pickup: "pending", dropoff: "pending" };
    admissions = { pickup: "pending_student_confirmation", dropoff: "pending_student_confirmation" };
    legacyBlocker = false;
    mocks.toast.mockReset();
    mocks.getSession.mockResolvedValue({ data: { session: { access_token: "token" } } });
    fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/ride-confirmation" && init?.method === "POST") {
        const body = JSON.parse(init.body as string);
        if (body.action !== "change") {
          decisions[body.direction as "pickup" | "dropoff"] = body.action === "confirm" ? "confirmed" : "cancelled";
          admissions[body.direction as "pickup" | "dropoff"] = body.action === "confirm" ? "admitted" : "cancelled";
        }
        return { ok: true, json: async () => ({ success: true }) };
      }
      return { ok: true, json: async () => ({
        legs: {
          pickup: { decision: decisions.pickup, admission: admissions.pickup },
          dropoff: { decision: decisions.dropoff, admission: admissions.dropoff },
        },
        legacyBlocker,
      }) };
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("confirms pickup alone with the exact directional payload and refreshes both legs", async () => {
    render(<ScheduleConfirmationCard {...props} />);
    const pickup = await screen.findByRole("group", { name: "pickup" });
    const dropoff = screen.getByRole("group", { name: "dropoff" });
    fireEvent.click(within(pickup).getByRole("button", { name: "confirmLeg pickup" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/ride-confirmation", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ action: "confirm", rideDate: "2026-09-30", direction: "pickup" }),
    })));
    await waitFor(() => expect(within(pickup).getByText("confirmed")).toBeTruthy());
    expect(within(dropoff).getByText("pending")).toBeTruthy();
  });

  it("cancels dropoff without changing confirmed pickup", async () => {
    decisions.pickup = "confirmed";
    admissions.pickup = "admitted";
    render(<ScheduleConfirmationCard {...props} />);
    const pickup = await screen.findByRole("group", { name: "pickup" });
    const dropoff = screen.getByRole("group", { name: "dropoff" });
    fireEvent.click(within(dropoff).getByRole("button", { name: "cancelLeg dropoff" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/ride-confirmation", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ action: "cancel", rideDate: "2026-09-30", direction: "dropoff" }),
    })));
    await waitFor(() => expect(within(dropoff).getByText("cancelled")).toBeTruthy());
    expect(within(pickup).getByText("confirmed")).toBeTruthy();
  });

  it("shows late admission and legacy blocker, keeping change on its legacy payload", async () => {
    decisions.pickup = "confirmed";
    admissions.pickup = "pending_admin_approval";
    legacyBlocker = true;
    render(<ScheduleConfirmationCard {...props} />);
    const pickup = await screen.findByRole("group", { name: "pickup" });
    expect(await within(pickup).findByText("pendingAdminReview")).toBeTruthy();
    expect(screen.getByText("legacyBlocker")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "changeButton" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/ride-confirmation", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ action: "change", rideDate: "2026-09-30", pickupTime: "08:30", dropoffTime: "17:15" }),
    })));
  });

  it("does not display unknown leg state as pending when the GET fails", async () => {
    fetchMock.mockImplementationOnce(async () => ({ ok: false, json: async () => ({ error: "unavailable" }) }) as Response);
    render(<ScheduleConfirmationCard {...props} />);

    expect((await screen.findByRole("alert")).textContent).toBe("stateUnavailable");
    const pickup = screen.getByRole("group", { name: "pickup" });
    expect(within(pickup).queryByText("pending")).toBeNull();
    expect(within(pickup).getByRole("button", { name: "confirmLeg pickup" })).toHaveProperty("disabled", true);
  });
});
