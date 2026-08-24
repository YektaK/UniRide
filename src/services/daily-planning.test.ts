import { describe, expect, it } from "vitest";

import {
  DEFAULT_DAILY_PLANNING_SETTINGS,
  parseClockMinutes,
  serviceDayOfWeek,
} from "./daily-planning";

describe("daily planning contracts", () => {
  it("defines the Dudullu daily planning defaults", () => {
    expect(DEFAULT_DAILY_PLANNING_SETTINGS).toEqual({
      campusCode: "D.Kampus",
      timezone: "Europe/Istanbul",
      pickupArrivalBufferMinutes: 15,
      dropoffDepartureBufferMinutes: 15,
      confirmationCutoffHour: 22,
      exceptionLeadMinutes: 120,
    });
  });

  it("maps valid calendar dates to the existing schedule day enum", () => {
    expect(serviceDayOfWeek("2026-08-26")).toBe("wednesday");
    expect(() => serviceDayOfWeek("2026-02-30")).toThrow("Invalid service date");
  });

  it("parses valid clock times and rejects invalid ones", () => {
    expect(parseClockMinutes("09:30")).toBe(570);
    expect(() => parseClockMinutes("24:00")).toThrow("Invalid clock time");
  });
});
