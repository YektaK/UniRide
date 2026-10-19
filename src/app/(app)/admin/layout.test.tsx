// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));
vi.mock("@/hooks/use-auth", () => ({ useAuth: mocks.useAuth }));

import AdminLayout from "./layout";

describe("AdminLayout redirect (L7)", () => {
  beforeEach(() => {
    mocks.replace.mockReset();
  });
  afterEach(() => cleanup());

  it("does not navigate during the render phase for a non-admin", () => {
    mocks.useAuth.mockReturnValue({ user: { id: "s1", role: "student" }, isLoading: false });
    // renderToString runs render but never effects, so any call here happened during render.
    renderToString(<AdminLayout>secret</AdminLayout>);
    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("redirects a non-admin to / from an effect, exactly once, without showing children", async () => {
    mocks.useAuth.mockReturnValue({ user: { id: "s1", role: "student" }, isLoading: false });
    render(<AdminLayout>secret</AdminLayout>);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/"));
    expect(mocks.replace).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("redirects an anonymous visitor once auth has loaded", async () => {
    mocks.useAuth.mockReturnValue({ user: null, isLoading: false });
    render(<AdminLayout>secret</AdminLayout>);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/"));
  });

  it("does not redirect while auth is loading and does not redirect an admin", () => {
    mocks.useAuth.mockReturnValue({ user: null, isLoading: true });
    const { unmount } = render(<AdminLayout>secret</AdminLayout>);
    expect(mocks.replace).not.toHaveBeenCalled();
    unmount();

    mocks.useAuth.mockReturnValue({ user: { id: "a1", role: "admin" }, isLoading: false });
    render(<AdminLayout>secret</AdminLayout>);
    expect(screen.getByText("secret")).toBeTruthy();
    expect(mocks.replace).not.toHaveBeenCalled();
  });
});
