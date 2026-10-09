// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  checkHealth: vi.fn(),
  fetchProblems: vi.fn(),
}));

vi.mock("next-intl", () => ({ useTranslations: () => (key: string) => key }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));
vi.mock("@/hooks/use-auth", () => ({ useAuth: mocks.useAuth }));
vi.mock("@/services/benchmark-service", () => ({
  checkBenchmarkApiHealth: mocks.checkHealth,
  fetchProblems: mocks.fetchProblems,
  startBenchmark: vi.fn(),
  pollStatus: vi.fn(),
  stopBenchmark: vi.fn(),
  fetchResults: vi.fn(),
}));

import BenchmarkSuitePage from "./page";

describe("landing page admin gate", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    mocks.checkHealth.mockReset().mockResolvedValue(true);
    mocks.fetchProblems.mockReset().mockResolvedValue([]);
    class RO { observe() {} unobserve() {} disconnect() {} }
    vi.stubGlobal("ResizeObserver", RO);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it.each([
    ["anonymous", null],
    ["non-admin", { id: "s1", role: "student" }],
  ])("does not mount the suite or call anything for %s visitors", async (_label, user) => {
    mocks.useAuth.mockReturnValue({ user, isLoading: false });
    render(<BenchmarkSuitePage />);
    expect(screen.getByText("title")).toBeTruthy();
    expect(screen.getByText("signIn").closest("a")?.getAttribute("href")).toBe("/login");
    await new Promise((r) => setTimeout(r, 50));
    expect(mocks.checkHealth).not.toHaveBeenCalled();
    expect(mocks.fetchProblems).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows only a loading state while the session resolves", async () => {
    mocks.useAuth.mockReturnValue({ user: null, isLoading: true });
    render(<BenchmarkSuitePage />);
    expect(screen.getByText("checking")).toBeTruthy();
    expect(mocks.checkHealth).not.toHaveBeenCalled();
  });

  it("mounts for an admin and checks health through the service, never a bare fetch", async () => {
    mocks.useAuth.mockReturnValue({ user: { id: "a1", role: "admin" }, isLoading: false });
    render(<BenchmarkSuitePage />);
    await waitFor(() => expect(mocks.checkHealth).toHaveBeenCalled());
    await waitFor(() => expect(mocks.fetchProblems).toHaveBeenCalled());
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByText("signIn")).toBeNull();
  });
});
