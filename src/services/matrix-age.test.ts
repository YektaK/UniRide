import { describe, expect, it } from "vitest";
import { buildMatrixAge } from "./matrix-age";

describe("buildMatrixAge (M4: data freshness, DECISION_LOG T09)", () => {
  it("carries the load time and age and the age of the travel-time data", () => {
    expect(
      buildMatrixAge({
        loaded_at: "2026-10-15T08:00:00+00:00",
        age_seconds: 0.4,
        data_updated_at: "2026-03-05T10:00:00+00:00",
        data_age_seconds: 19_000_000,
      }),
    ).toEqual({
      loadedAt: "2026-10-15T08:00:00+00:00",
      ageSeconds: 0.4,
      dataUpdatedAt: "2026-03-05T10:00:00+00:00",
      dataAgeSeconds: 19_000_000,
    });
  });

  it("has a null data age when the optimizer sends none (updated_at column not migrated yet)", () => {
    expect(buildMatrixAge({ loaded_at: "2026-10-15T08:00:00+00:00", age_seconds: 1 })).toEqual({
      loadedAt: "2026-10-15T08:00:00+00:00",
      ageSeconds: 1,
      dataUpdatedAt: null,
      dataAgeSeconds: null,
    });
    expect(buildMatrixAge({ data_updated_at: null, data_age_seconds: null })).toMatchObject({
      dataUpdatedAt: null,
      dataAgeSeconds: null,
    });
  });

  it("is null when the optimizer sent no provenance at all", () => {
    expect(buildMatrixAge(undefined)).toBeNull();
  });
});
