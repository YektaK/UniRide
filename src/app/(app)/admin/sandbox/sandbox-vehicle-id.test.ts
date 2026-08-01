import { describe, expect, it } from "vitest";

import { nextSandboxVehicleId } from "./sandbox-vehicle-id";

describe("nextSandboxVehicleId", () => {
  it("skips loaded IDs and each newly allocated sandbox ID", () => {
    const existingIds = new Set(["sb-1", "fleet-17"]);

    const firstId = nextSandboxVehicleId(existingIds);
    existingIds.add(firstId);
    const secondId = nextSandboxVehicleId(existingIds);
    existingIds.add(secondId);
    const thirdId = nextSandboxVehicleId(existingIds);

    expect([firstId, secondId, thirdId]).toEqual(["sb-2", "sb-3", "sb-4"]);
  });
});
