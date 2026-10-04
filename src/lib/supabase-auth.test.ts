import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

type RawListener = (event: string, session: { user: { email: string } } | null) => unknown;

const adminRow = { id: "admin-id", name: "Admin", email: "admin@example.com", role: "admin" as const };

function setup() {
  const unsubscribe = vi.fn();
  const onSupabaseAuthStateChange = vi.fn().mockReturnValue({
    data: { subscription: { unsubscribe } },
  });
  mocks.getSupabaseClient.mockReturnValue({
    auth: { onAuthStateChange: onSupabaseAuthStateChange },
  });
  const onUser = vi.fn();
  const onImmediateAuthEvent = vi.fn();
  const stop = onAuthStateChange(onUser, onImmediateAuthEvent);
  const rawListener = onSupabaseAuthStateChange.mock.calls[0][0] as RawListener;
  return { rawListener, onUser, onImmediateAuthEvent, unsubscribe, stop };
}

describe("onAuthStateChange", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.getUserByEmail.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns synchronously (not a promise) so auth-js never awaits it under its lock", () => {
    mocks.getUserByEmail.mockReturnValue(new Promise(() => {}));
    const { rawListener } = setup();

    expect(rawListener("SIGNED_IN", { user: { email: "admin@example.com" } })).toBeUndefined();
    expect(rawListener("SIGNED_OUT", null)).toBeUndefined();
  });

  it("does not query the database inside the listener call itself", async () => {
    mocks.getUserByEmail.mockResolvedValue(adminRow);
    const { rawListener, onImmediateAuthEvent } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });

    expect(onImmediateAuthEvent).toHaveBeenCalledTimes(1);
    expect(mocks.getUserByEmail).not.toHaveBeenCalled();
    await vi.runAllTimersAsync();
    expect(mocks.getUserByEmail).toHaveBeenCalledWith("admin@example.com");
  });

  it("still loads the profile on a normal SIGNED_IN", async () => {
    mocks.getUserByEmail.mockResolvedValue(adminRow);
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });
    expect(onUser).not.toHaveBeenCalled();
    await vi.runAllTimersAsync();

    expect(onUser).toHaveBeenCalledTimes(1);
    expect(onUser).toHaveBeenCalledWith(expect.objectContaining({
      id: "admin-id",
      email: "admin@example.com",
      role: "admin",
    }));
  });

  it("clears the user immediately on SIGNED_OUT", () => {
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_OUT", null);

    expect(onUser).toHaveBeenCalledWith(null);
  });

  it("ignores a late lookup that resolves after SIGNED_OUT", async () => {
    let resolveLookup!: (row: typeof adminRow) => void;
    mocks.getUserByEmail.mockReturnValue(new Promise((resolve) => { resolveLookup = resolve; }));
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });
    await vi.runAllTimersAsync(); // lookup now in flight
    rawListener("SIGNED_OUT", null);
    resolveLookup(adminRow);
    await vi.runAllTimersAsync();

    expect(onUser).toHaveBeenCalledTimes(1);
    expect(onUser).toHaveBeenLastCalledWith(null);
  });

  it("skips a deferred lookup that was superseded before it started", async () => {
    mocks.getUserByEmail.mockResolvedValue(adminRow);
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });
    rawListener("SIGNED_OUT", null);
    await vi.runAllTimersAsync();

    expect(mocks.getUserByEmail).not.toHaveBeenCalled();
    expect(onUser.mock.calls).toEqual([[null]]);
  });

  it("only applies the newest of two overlapping lookups", async () => {
    const first = deferred<typeof adminRow>();
    const second = deferred<typeof adminRow>();
    mocks.getUserByEmail
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });
    await vi.runAllTimersAsync();
    rawListener("TOKEN_REFRESHED", { user: { email: "admin@example.com" } });
    await vi.runAllTimersAsync();
    second.resolve({ ...adminRow, name: "Newest" });
    first.resolve({ ...adminRow, name: "Stale" });
    await vi.runAllTimersAsync();

    expect(onUser).toHaveBeenCalledTimes(1);
    expect(onUser).toHaveBeenCalledWith(expect.objectContaining({ name: "Newest" }));
  });

  it("drops pending lookups after unsubscribe", async () => {
    mocks.getUserByEmail.mockResolvedValue(adminRow);
    const { rawListener, onUser, stop, unsubscribe } = setup();

    rawListener("SIGNED_IN", { user: { email: "admin@example.com" } });
    stop();
    await vi.runAllTimersAsync();

    expect(unsubscribe).toHaveBeenCalledTimes(1);
    expect(onUser).not.toHaveBeenCalled();
  });

  it("maps lookup failures and missing rows to a null user", async () => {
    mocks.getUserByEmail.mockResolvedValueOnce(null).mockRejectedValueOnce({ code: "42501" });
    const { rawListener, onUser } = setup();

    rawListener("SIGNED_IN", { user: { email: "a@example.com" } });
    await vi.runAllTimersAsync();
    rawListener("SIGNED_IN", { user: { email: "b@example.com" } });
    await vi.runAllTimersAsync();

    expect(onUser.mock.calls).toEqual([[null], [null]]);
  });
});
