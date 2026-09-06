import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getSupabaseClient: vi.fn(),
  getUserByEmail: vi.fn(),
  getUserByStudentNumber: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  createSchedule: vi.fn(),
}));

vi.mock("./supabase", () => ({
  getSupabaseClient: mocks.getSupabaseClient,
}));

vi.mock("./database", () => ({
  getUserByEmail: mocks.getUserByEmail,
  getUserByStudentNumber: mocks.getUserByStudentNumber,
  createUser: mocks.createUser,
  updateUser: mocks.updateUser,
  createSchedule: mocks.createSchedule,
}));

import { onAuthStateChange } from "./supabase-auth";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

describe("onAuthStateChange", () => {
  it("runs the optional immediate hook before awaiting mapped user data", async () => {
    const mappedUser = deferred<{
      id: string;
      name: string;
      email: string;
      role: "admin";
    }>();
    mocks.getUserByEmail.mockReturnValue(mappedUser.promise);
    const onSupabaseAuthStateChange = vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
    mocks.getSupabaseClient.mockReturnValue({
      auth: { onAuthStateChange: onSupabaseAuthStateChange },
    });
    const onUser = vi.fn();
    const onImmediateAuthEvent = vi.fn();

    onAuthStateChange(onUser, onImmediateAuthEvent);
    const rawListener = onSupabaseAuthStateChange.mock.calls[0][0];
    const mapping = rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });

    expect(onImmediateAuthEvent).toHaveBeenCalledTimes(1);
    expect(onUser).not.toHaveBeenCalled();

    mappedUser.resolve({
      id: "admin-id",
      name: "Admin",
      email: "admin@example.com",
      role: "admin",
    });
    await mapping;

    expect(onUser).toHaveBeenCalledWith(expect.objectContaining({
      id: "admin-id",
      email: "admin@example.com",
      role: "admin",
    }));
  });
});
