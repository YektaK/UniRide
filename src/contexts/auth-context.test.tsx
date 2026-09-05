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

function Probe() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("AuthProvider is required");

  return <button onClick={() => void auth.logout()}>logout</button>;
}

describe("AuthProvider", () => {
  afterEach(cleanup);

  beforeEach(() => {
    mocks.signIn.mockReset();
    mocks.signOut.mockReset().mockResolvedValue(undefined);
    mocks.onChange.mockReset().mockReturnValue(() => undefined);
    mocks.clearToken.mockReset();
  });

  it("clears the cache on every observed auth-state change", () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    const callback = mocks.onChange.mock.calls[0][0];

    act(() => callback(null));

    expect(mocks.clearToken).toHaveBeenCalledTimes(1);
  });

  it("clears the cache after explicit logout", async () => {
    render(<AuthProvider><Probe /></AuthProvider>);

    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => expect(mocks.signOut).toHaveBeenCalledTimes(1));
    expect(mocks.clearToken).toHaveBeenCalled();
  });
});
