import { describe, expect, it } from "vitest";

import { coordinatesToLocationCode } from "./location-mapper";

describe("coordinatesToLocationCode", () => {
  it("maps the canonical Dudullu depot coordinates to D.Kampus", () => {
    expect(coordinatesToLocationCode(41.001, 29.177)).toBe("D.Kampus");
  });
});
