export function nextSandboxVehicleId(existingIds: Iterable<string>): string {
  const usedIds = new Set(existingIds);
  let sequence = 1;

  while (usedIds.has(`sb-${sequence}`)) {
    sequence += 1;
  }

  return `sb-${sequence}`;
}
