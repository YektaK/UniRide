import { describe, expect, it } from "vitest";

import { appendSandboxVehicle } from "./sandbox-vehicle-id";

describe("appendSandboxVehicle", () => {
  it("preserves loaded IDs and keeps both identity namespaces unique across consecutive additions", () => {
    const loaded = [
      { id: "sb-1", vehicleId: "fleet-17", name: "loaded-a" },
      { id: "fleet-18", vehicleId: "sb-2", name: "loaded-b" },
    ];

    const afterFirst = appendSandboxVehicle(loaded, (identity) => ({ ...identity, name: "new-a" }));
    const afterSecond = appendSandboxVehicle(afterFirst, (identity) => ({ ...identity, name: "new-b" }));

    expect(loaded).toEqual([
      { id: "sb-1", vehicleId: "fleet-17", name: "loaded-a" },
      { id: "fleet-18", vehicleId: "sb-2", name: "loaded-b" },
    ]);
    expect(afterSecond.slice(0, loaded.length)).toEqual(loaded);
    expect(afterSecond.slice(loaded.length).map(({ id, vehicleId }) => [id, vehicleId])).toEqual([
      ["sb-3", "sb-4"],
      ["sb-5", "sb-6"],
    ]);

    const combinedIds = afterSecond.flatMap(({ id, vehicleId }) => [id, vehicleId]);
    expect(new Set(combinedIds).size).toBe(combinedIds.length);
  });
});
