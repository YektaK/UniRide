export interface SandboxVehicleIdentity {
  id: string;
  vehicleId: string;
}

export function nextSandboxVehicleId(existingIds: Iterable<string>): string {
  const usedIds = new Set(existingIds);
  let sequence = 1;

  while (usedIds.has(`sb-${sequence}`)) {
    sequence += 1;
  }

  return `sb-${sequence}`;
}

export function appendSandboxVehicle<T extends SandboxVehicleIdentity>(
  currentVehicles: readonly T[],
  createVehicle: (identity: SandboxVehicleIdentity) => T,
): T[] {
  const usedIds = new Set(currentVehicles.flatMap((vehicle) => [vehicle.id, vehicle.vehicleId]));
  const id = nextSandboxVehicleId(usedIds);
  usedIds.add(id);
  const vehicleId = nextSandboxVehicleId(usedIds);

  return [...currentVehicles, createVehicle({ id, vehicleId })];
}
