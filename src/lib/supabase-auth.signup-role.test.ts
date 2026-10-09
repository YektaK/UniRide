import { beforeEach, describe, expect, it, vi } from "vitest";

// QW1 / audit C1: the browser must never decide the role of a new account.
const mocks = vi.hoisted(() => ({
  getSupabaseClient: vi.fn(),
  getUserByEmail: vi.fn(),
  getUserByStudentNumber: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  createSchedule: vi.fn(),
}));

vi.mock("./supabase", () => ({ getSupabaseClient: mocks.getSupabaseClient }));
vi.mock("./database", () => ({
  getUserByEmail: mocks.getUserByEmail,
  getUserByStudentNumber: mocks.getUserByStudentNumber,
  createUser: mocks.createUser,
  updateUser: mocks.updateUser,
  createSchedule: mocks.createSchedule,
}));

import { register, signUp } from "./supabase-auth";

describe("signUp / register never send a privileged role", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    for (const m of Object.values(mocks)) m.mockReset();
    mocks.getSupabaseClient.mockReturnValue({
      auth: {
        signUp: vi.fn().mockResolvedValue({
          data: { user: { id: "u-1", email: "s@example.com" } },
          error: null,
        }),
      },
    });
    mocks.createUser.mockResolvedValue({});
    mocks.createSchedule.mockResolvedValue({ id: "sched-1" });
    mocks.updateUser.mockResolvedValue(undefined);
  });

  it("signUp has no role parameter: arity is email, password, name, studentNumber, userData", () => {
    expect(signUp.length).toBe(5);
  });

  it("signUp passes userData as the 5th argument and always creates a student row", async () => {
    const user = await signUp("s@example.com", "pw123456", "Stu", "123", {
      homeAddress: "Somewhere",
      passwordHint: "hint",
    });
    expect(mocks.createUser).toHaveBeenCalledTimes(1);
    const row = mocks.createUser.mock.calls[0][0];
    expect(row.role).toBe("student");
    expect(row.homeAddress).toBe("Somewhere");
    expect(user?.role).toBe("student");
  });

  it.each(["admin", "driver"] as const)(
    "register ignores a caller-supplied role of %s",
    async (role) => {
      const user = await register("s@example.com", "pw123456", {
        name: "Mallory",
        role,
        homeAddress: "",
        accessibilityNeeds: [],
      } as Parameters<typeof register>[2]);
      const row = mocks.createUser.mock.calls[0][0];
      expect(row.role).toBe("student");
      expect(user.role).toBe("student");
    },
  );
});
