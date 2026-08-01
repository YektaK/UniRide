// @vitest-environment jsdom

import { render } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SidebarMenuSkeleton } from "./sidebar";

describe("SidebarMenuSkeleton", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the same deterministic skeleton width on SSR and client mounts", () => {
    const randomSpy = vi.spyOn(Math, "random");

    const serverMarkup = renderToStaticMarkup(<SidebarMenuSkeleton />);
    const { container } = render(<SidebarMenuSkeleton />);

    const serverWidth = serverMarkup.match(/--skeleton-width:([^\"]+)/)?.[1];
    const clientWidth = container
      .querySelector<HTMLElement>('[data-sidebar="menu-skeleton-text"]')
      ?.style.getPropertyValue("--skeleton-width");

    expect(serverWidth).toBeTruthy();
    expect(clientWidth).toBe(serverWidth);
    expect(randomSpy).not.toHaveBeenCalled();
  });
});
