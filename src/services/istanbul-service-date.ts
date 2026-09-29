const DAY_MILLISECONDS = 24 * 60 * 60 * 1_000;
const offsetFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "Europe/Istanbul",
  timeZoneName: "longOffset",
});

export function isRealServiceDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function offsetMinutesAt(instant: number): number {
  const zoneName = offsetFormatter
    .formatToParts(new Date(instant))
    .find((part) => part.type === "timeZoneName")?.value;
  if (zoneName === "GMT") return 0;
  const match = /^GMT([+-])(\d{2}):(\d{2})$/.exec(zoneName ?? "");
  if (!match) throw new Error("time zone offset unavailable");
  return (match[1] === "-" ? -1 : 1) * (Number(match[2]) * 60 + Number(match[3]));
}

export function serviceDateBounds(serviceDate: string): { start: string; end: string } {
  if (!isRealServiceDate(serviceDate)) throw new Error("Invalid service date");
  const wallStart = Date.parse(`${serviceDate}T00:00:00.000Z`);
  const toUtc = (wallClockAsUtc: number) => {
    const firstGuess = wallClockAsUtc - offsetMinutesAt(wallClockAsUtc) * 60_000;
    return new Date(wallClockAsUtc - offsetMinutesAt(firstGuess) * 60_000).toISOString();
  };
  return { start: toUtc(wallStart), end: toUtc(wallStart + DAY_MILLISECONDS) };
}
