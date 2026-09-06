// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useContext } from "react";

const mocks = vi.hoisted(() => ({
  signIn: vi.fn(),
  signOut: vi.fn(),
  onChange: vi.fn(),
  clearToken: vi.fn(),
}));

vi.mock("@/lib/supabase-auth", () => ({
  signIn: mocks.signIn,
  signOutUser: mocks.signOut,
  onAuthStateChange: mocks.onChange,
}));

vi.mock("@/lib/admin-api", () => ({
  clearAuthTokenCache: mocks.clearToken,
}));

import { AuthContext, AuthProvider } from "./auth-context";

function Probe({ onLogout }: { onLogout?: (promise: Promise<void>) => void }) {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("AuthProvider is required");

  return (
    <button onClick={() => {
      const promise = auth.logout();
      onLogout?.(promise);
    }}>
      logout
    </button>
  );
}

function deferred() {
  let resolve!: () => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<void>((next, fail) => {
    resolve = next;
    reject = fail;
  });
  return { promise, reject, resolve };
}

describe("AuthProvider", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    mocks.signIn.mockReset();
    mocks.signOut.mockReset().mockResolvedValue(undefined);
    mocks.onChange.mockReset().mockReturnValue(() => undefined);
    mocks.clearToken.mockReset();
  });

  it("passes cache invalidation as the immediate auth-state hook", () => {
    render(<AuthProvider><Probe /></AuthProvider>);

    expect(mocks.onChange).toHaveBeenCalledWith(expect.any(Function), mocks.clearToken);
  });

  it("clears before sign-out settles and again after successful logout", async () => {
    const signOut = deferred();
    mocks.signOut.mockReturnValue(signOut.promise);
    render(<AuthProvider><Probe /></AuthProvider>);

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "logout" }));
    });

    expect(mocks.signOut).toHaveBeenCalledTimes(1);
    expect(mocks.clearToken).toHaveBeenCalledTimes(1);

    signOut.resolve();
    await waitFor(() => expect(mocks.clearToken).toHaveBeenCalledTimes(2));
  });

  it("clears immediately but not a second time when deferred logout fails", async () => {
    const signOut = deferred();
    const failure = new Error("sign-out failed");
    mocks.signOut.mockReturnValue(signOut.promise);
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    let logout: Promise<void> | undefined;
    render(
      <AuthProvider>
        <Probe onLogout={(promise) => { logout = promise; }} />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    expect(mocks.signOut).toHaveBeenCalledTimes(1);
    expect(mocks.clearToken).toHaveBeenCalledTimes(1);

    signOut.reject(failure);
    await expect(logout).rejects.toBe(failure);
    expect(mocks.clearToken).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith("Logout error:", failure);
  });
});
