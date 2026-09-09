import { describe, expect, it } from "vitest";

import { normalizeScheduleLocationForEditing } from "./schedule-form-dialog";

describe("normalizeScheduleLocationForEditing", () => {
  it("normalizes only the Dudullu machine alias and leaves another campus distinct", () => {
    expect(normalizeScheduleLocationForEditing("D.Kampus")).toBe("Dudullu");
    expect(normalizeScheduleLocationForEditing("Çengelköy")).toBe("Çengelköy");
    expect(normalizeScheduleLocationForEditing("Other Campus")).toBe("Other Campus");
  });
});
