import { describe, expect, it } from "vitest";
import { parseFleetArgs, parseFleetType, rideStatistics, routeRideProfile } from "./fleet-scenario-args";

const base = ["--week-of", "2026-10-05", "--fleet-types", "large:4sw5so:cd10,sedan:0sw4so:cd10", "--fixed-type", "large", "--minimize-type", "sedan"];

describe("parseFleetType", () => {
  it("parses capacities and the optional cooldown, ride and tour parts", () => {
    expect(parseFleetType("large:4sw5so")).toEqual({ typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 });
    expect(parseFleetType("sedan:1sw3so:cd15:r50:t120")).toEqual({
      typeId: "sedan", swCapacity: 1, soCapacity: 3, cooldownMinutes: 15, rideLimit: 50, tourLimit: 120,
    });
  });
  it("parses the optional :capN shared seat limit in any position", () => {
    expect(parseFleetType("minivan:1sw3so:cap3:cd10")).toEqual({
      typeId: "minivan", swCapacity: 1, soCapacity: 3, totalCapacity: 3, cooldownMinutes: 10,
    });
    expect(parseFleetType("minivan:1sw3so:cd5:cap3:r50").totalCapacity).toBe(3);
    expect(parseFleetType("large:4sw5so")).not.toHaveProperty("totalCapacity");
  });
  it.each(["minivan:1sw3so:cap0", "minivan:1sw3so:cap5", "minivan:1sw3so:cap3:cap3", "minivan:1sw3so:cap", "minivan:1sw3so:capx"])(
    "rejects invalid cap %j", (text) => { expect(() => parseFleetType(text)).toThrow(); });
  it.each(["", "large", "Large:4sw5so", "large:4sw", "large:0sw0so", "large:4sw5so:cd", "large:4sw5so:cd10:cd10",
    "large:4sw5so:x5", "large:4sw5so:r5", "1x:4sw5so", "large:4sw5so:cd999"])("rejects %j", (text) => {
    expect(() => parseFleetType(text)).toThrow();
  });
});

describe("parseFleetArgs", () => {
  it("parses the documented command line", () => {
    const args = parseFleetArgs([...base, "--ride-limits", "50,60,70,90", "--tour-limit", "150", "--scenarios", "A,1,2,3", "--out", ".temp/x"]);
    expect(args).toMatchObject({
      dates: ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"], rideLimits: [50, 60, 70, 90], tourLimit: 150,
      fixedTypeId: "large", minimizeTypeId: "sedan", scenarios: ["A", 1, 2, 3], maxCars: null, nodeBudget: 200000,
      selectionTimeLimitSeconds: 30, out: ".temp/x",
    });
    expect(args.fleetTypes.map((t) => [t.typeId, t.swCapacity, t.soCapacity, t.cooldownMinutes])).toEqual([["large", 4, 5, 10], ["sedan", 0, 4, 10]]);
  });
  it("defaults the scenarios and accepts the optional limits", () => {
    expect(parseFleetArgs(base).scenarios).toEqual(["A", 1, 2, 3]);
    expect(parseFleetArgs([...base, "--max-cars", "3", "--node-budget", "5000", "--selection-time-limit", "10"]))
      .toMatchObject({ maxCars: 3, nodeBudget: 5000, selectionTimeLimitSeconds: 10 });
  });
  it("allows a single type for scenario A without a minimise type", () => {
    expect(parseFleetArgs(["--week-of", "2026-10-05", "--fleet-types", "large:4sw5so", "--scenarios", "A"]))
      .toMatchObject({ fixedTypeId: "large", minimizeTypeId: null, scenarios: ["A"] });
  });
  const without = (flag: string) => {
    const copy = [...base];
    copy.splice(copy.indexOf(flag), 2);
    return copy;
  };
  it.each<[string, string[]]>([
    ["missing fleet types", ["--week-of", "2026-10-05"]],
    ["missing minimise type", without("--minimize-type")],
    ["missing fixed type with two types", without("--fixed-type")],
    ["unknown fixed type", [...without("--fixed-type"), "--fixed-type", "truck"]],
    ["same fixed and minimise type", [...without("--minimize-type"), "--minimize-type", "large"]],
    ["duplicate type id", ["--week-of", "2026-10-05", "--fleet-types", "a:4sw5so,a:0sw4so", "--fixed-type", "a", "--minimize-type", "a"]],
    ["three types", ["--week-of", "2026-10-05", "--fleet-types", "a:4sw5so,b:0sw4so,c:0sw2so", "--fixed-type", "a", "--minimize-type", "b"]],
    ["fixed L with one type", ["--week-of", "2026-10-05", "--fleet-types", "large:4sw5so", "--scenarios", "A,1"]],
    ["L above the menu limit", [...base, "--scenarios", "5"]],
    ["duplicate scenario", [...base, "--scenarios", "1,1"]],
    ["unknown scenario", [...base, "--scenarios", "B"]],
    ["unknown flag", [...base, "--fleet", "live"]],
    ["duplicate flag", [...base, "--fixed-type", "large"]],
    ["per-type ride limit above the experiment limit", ["--week-of", "2026-10-05", "--ride-limits", "50", "--fleet-types", "a:4sw5so:r60,b:0sw4so", "--fixed-type", "a", "--minimize-type", "b"]],
    ["bad node budget", [...base, "--node-budget", "5"]],
    ["bad max cars", [...base, "--max-cars", "-1"]],
    ["bad week", ["--week-of", "2026-10-06", "--fleet-types", "large:4sw5so", "--scenarios", "A"]],
  ])("rejects %s", (_name, argv) => {
    expect(() => parseFleetArgs(argv)).toThrow();
  });
});

describe("ride statistics", () => {
  const step = (location1: string, location2: string) => ({ location1, location2, duration: 999, distance: 0 });
  const arcs = [
    { origin_code: "D", destination_code: "A", duration_minutes: 10 },
    { origin_code: "A", destination_code: "B", duration_minutes: 20 },
    { origin_code: "B", destination_code: "D", duration_minutes: 30 },
    { origin_code: "D", destination_code: "C", duration_minutes: 5 },
    { origin_code: "C", destination_code: "D", duration_minutes: 100 },
  ];
  const jobs = [
    { direction: "pickup" as const, result: { routes: [{ student_ids: ["a", "b"], sw_count: 2, so_count: 0, route_details: [step("D", "A"), step("A", "B"), step("B", "D")] }] } },
    { direction: "dropoff" as const, result: { routes: [{ student_ids: ["c"], sw_count: 0, so_count: 1, route_details: [step("D", "C"), step("C", "D")] }] } },
  ];
  it("measures pure travel on the authoritative arcs per route and passenger", () => {
    expect(routeRideProfile(jobs, arcs)).toEqual([
      { routeMinutes: 60, rides: [50, 30] },
      { routeMinutes: 105, rides: [5] },
    ]);
  });
  it("fails closed on a missing arc or a coverage mismatch", () => {
    expect(() => routeRideProfile(jobs, [])).toThrow();
    expect(() => routeRideProfile([{ ...jobs[0], result: { routes: [{ ...jobs[0].result.routes[0], student_ids: ["a"] }] } }], arcs)).toThrow();
  });
  it("computes mean, median, nearest-rank p90 and max", () => {
    expect(rideStatistics([])).toBeNull();
    expect(rideStatistics([50, 30, 5])).toEqual({ passengers: 3, mean: 28.333333, median: 30, p90: 50, max: 50 });
    expect(rideStatistics([1, 2, 3, 4])).toMatchObject({ median: 2.5, p90: 4 });
    expect(rideStatistics(Array.from({ length: 10 }, (_, i) => i + 1))).toMatchObject({ p90: 9, max: 10 });
  });
});
