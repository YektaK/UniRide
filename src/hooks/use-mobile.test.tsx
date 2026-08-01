// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useIsMobile } from "./use-mobile";

describe("useIsMobile", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true });
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: () => ({
        matches: false,
        media: "",
        onchange: null,
        addEventListener: (_type: string, callback: () => void) => window.addEventListener("resize", callback),
        removeEventListener: (_type: string, callback: () => void) => window.removeEventListener("resize", callback),
        dispatchEvent: () => true,
      }),
    });
  });

  it("uses React's external-store contract", () => {
    expect(useIsMobile.toString()).toContain("useSyncExternalStore");
  });

  it("updates from the external viewport store without effect-driven state", () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
    act(() => {
      window.innerWidth = 640;
      window.dispatchEvent(new Event("resize"));
    });
    expect(result.current).toBe(true);
  });
});
