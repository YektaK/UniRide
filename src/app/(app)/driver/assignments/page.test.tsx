// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { format } from "date-fns";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  getVehicles: vi.fn(),
  getSession: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));
vi.mock("@/hooks/use-auth", () => ({ useAuth: mocks.useAuth }));
// toast is a module-level, referentially stable function in the real hook.
const toastFn = vi.fn();
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: toastFn }) }));
vi.mock("@/lib/admin-api", () => ({
  adminApi: { vehicles: { getAll: mocks.getVehicles } },
}));
vi.mock("@/lib/supabase", () => ({
  getSupabaseClient: () => ({ auth: { getSession: mocks.getSession } }),
}));

import Page from "./page";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

const today = format(new Date(), "yyyy-MM-dd");

function assignment(id: string, driverId: string, vehicleId: string) {
  return {
    id,
    date: today,
    vehicleId,
    driverId,
    routeId: "r",
    studentIds: ["s1"],
    pickupTime: today + "T07:00:00",
    estimatedDropoffTime: today + "T08:00:00",
    status: "scheduled",
  };
}

describe("driver assignments page cancels on user change (L15)", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    mocks.getSession.mockReset().mockResolvedValue({ data: { session: { access_token: "t" } } });
    mocks.getVehicles.mockReset().mockResolvedValue([
      { id: "v1", name: "Vehicle-U1" },
      { id: "v2", name: "Vehicle-U2" },
    ]);
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("ignores a late response that belongs to the previous user", async () => {
    const first = deferred<unknown[]>();
    const second = deferred<unknown[]>();
    fetchMock
      .mockReturnValueOnce(first.promise.then((d) => ({ json: async () => d })))
      .mockReturnValueOnce(second.promise.then((d) => ({ json: async () => d })));

    mocks.useAuth.mockReturnValue({ user: { id: "u1", role: "driver" } });
    const { rerender } = render(<Page />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    mocks.useAuth.mockReturnValue({ user: { id: "u2", role: "driver" } });
    rerender(<Page />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    second.resolve([assignment("a2", "u2", "v2")]);
    await waitFor(() => expect(screen.getAllByText(/Vehicle-U2/).length).toBeGreaterThan(0));
    first.resolve([assignment("a1", "u1", "v1")]);
    await new Promise((r) => setTimeout(r, 20));

    expect(screen.queryAllByText(/Vehicle-U1/)).toHaveLength(0);
    expect(screen.getAllByText(/Vehicle-U2/).length).toBeGreaterThan(0);
  });
});
