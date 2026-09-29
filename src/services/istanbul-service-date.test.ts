import { describe, expect, it } from "vitest";
import { isRealServiceDate, serviceDateBounds } from "./istanbul-service-date";

describe("Istanbul service dates", () => {
  it("rejects impossible and noncanonical calendar dates", () => {
    expect(isRealServiceDate("2026-02-30")).toBe(false);
    expect(isRealServiceDate("2026-9-30")).toBe(false);
    expect(isRealServiceDate("2026-09-30")).toBe(true);
  });

  it("uses an inclusive Istanbul midnight and exclusive next midnight", () => {
    expect(serviceDateBounds("2026-09-30")).toEqual({
      start: "2026-09-29T21:00:00.000Z",
      end: "2026-09-30T21:00:00.000Z",
    });
  });
});
