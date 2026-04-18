const RUN_ID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

function secureRandomHex(byteLength = 6): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID().replace(/-/g, "").slice(0, byteLength * 2);
  }

  if (typeof globalThis.crypto?.getRandomValues === "function") {
    const bytes = new Uint8Array(byteLength);
    globalThis.crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  throw new Error("Secure random source is not available");
}

export function generateBenchmarkRunId(date = new Date()): string {
  const timestamp = date.toISOString().replace(/[-:T.]/g, "").substring(0, 14);
  const randomSuffix = secureRandomHex(6);
  return `benchmark_${timestamp}_${randomSuffix}`;
}

export function isValidBenchmarkRunId(runId: string): boolean {
  return RUN_ID_PATTERN.test(runId);
}
