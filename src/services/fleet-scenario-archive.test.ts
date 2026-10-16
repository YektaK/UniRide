import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { runFleetScenarioDay } from "@/services/fleet-scenario-run";
import { fleetManifestSchema } from "@/services/fleet-scenario-report";
import {
  FLEET_ARCHIVE_FORMAT, HISTORICAL_ARCHIVE_DIRS, assertOutsideHistoricalArchives, menuArchive, menuArchiveSchema,
  selectionArchive, selectionArchiveSchema, extendedFleetManifestSchema,
} from "@/services/fleet-scenario-archive";
import { params, pickSelection, reader, rows, transport, type SelectionRequest } from "./fleet-scenario-fixtures";

const clock = () => new Date("2026-09-30T00:00:00Z");
const RIDE = 60;

async function runDay(
  scenarios: Array<"A" | number> = ["A", 1, 2],
  selection: (request: SelectionRequest) => { status: number; body: unknown } = pickSelection("q1", () => ["large", "car"]),
) {
  const t = transport({ selection });
  const day = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: t.fetch, clock }, params({ scenarios }));
  return { day, t };
}

describe("WP-E10 extended archive: every menu option", () => {
  it("archives base and q0..qQ of every wave with routes, stop order, student ids, minutes, intervals and the certificate", async () => {
    const { day } = await runDay();
    const archive = menuArchiveSchema.parse(menuArchive(day, RIDE));
    expect(archive.format).toBe(FLEET_ARCHIVE_FORMAT);
    expect(archive.waves).toHaveLength(day.menu.length);
    for (const [index, wave] of archive.waves.entries()) {
      // same option ids and statuses as the summary menu: nothing is dropped, duplicates and infeasible options included
      expect(wave.options.map((o) => [o.optionId, o.status])).toEqual(day.menu[index].options.map((o) => [o.optionId, o.status]));
      for (const option of wave.options) {
        expect(option.certificate).not.toBeNull();
        if (option.status === "included" || option.status === "skipped_duplicate") {
          expect(option.success).toBe(true);
          expect(option.routes.length).toBeGreaterThan(0);
          for (const route of option.routes) {
            expect(route.steps.length).toBeGreaterThanOrEqual(2);
            expect(route.studentIds.length).toBe(route.steps.length - 1);
            expect(route.minutes).toBeGreaterThan(0);
            expect(route.interval).not.toBeNull();
            expect(route.interval!.endMinutes).toBeGreaterThan(route.interval!.startMinutes);
            expect(route.interval!.occurrenceIds.length).toBeGreaterThan(0);
            expect(route.rideMinutes.length).toBe(route.studentIds.length);
          }
        } else {
          // q0: a Sw student cannot ride the sedan, the optimizer answers success=false with its certificate
          expect(option).toMatchObject({ status: "skipped_infeasible", success: false, routes: [] });
        }
      }
    }
    // a duplicate option keeps its own routes (the GA stop order may differ from the earlier option)
    const dup = archive.waves[0].options.find((o) => o.optionId === "q2")!;
    expect(dup.status).toBe("skipped_duplicate");
    expect(dup.routes.length).toBeGreaterThan(0);
  });

  it("rejects an archive in which an included option lacks its certificate, minutes, intervals or routes", async () => {
    const { day } = await runDay();
    const good = JSON.parse(JSON.stringify(menuArchive(day, RIDE)));
    expect(() => menuArchiveSchema.parse(good)).not.toThrow();
    const included = (value: typeof good) => value.waves[0].options.find((o: { status: string }) => o.status === "included");
    const mutate = (change: (option: ReturnType<typeof included>) => void) => {
      const copy = JSON.parse(JSON.stringify(good));
      change(included(copy));
      return copy;
    };
    expect(() => menuArchiveSchema.parse(mutate((o) => { o.certificate = null; }))).toThrow();
    expect(() => menuArchiveSchema.parse(mutate((o) => { delete o.certificate; }))).toThrow();
    expect(() => menuArchiveSchema.parse(mutate((o) => { o.routes = []; }))).toThrow();
    expect(() => menuArchiveSchema.parse(mutate((o) => { o.routes[0].minutes = null; }))).toThrow();
    expect(() => menuArchiveSchema.parse(mutate((o) => { o.routes[0].interval = null; }))).toThrow();
    expect(() => menuArchiveSchema.parse(mutate((o) => { delete o.routes[0].steps; }))).toThrow();
  });

  it("records the optimizer error of an option that has no routes (HTTP error) instead of dropping it", async () => {
    const t = transport({ selection: pickSelection("base", (n) => Array(n).fill("large")) });
    const failing = async (path: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      if (path === "/api/v1/optimize" && body?.algorithm === "ga_split_hf" && body.vehicle_types[0].max_routes === 1) {
        return new Response("{}", { status: 500 });
      }
      return t.fetch(path, init);
    };
    const day = await runFleetScenarioDay({ reader: reader(rows()).client, optimizerFetch: failing, clock }, params({ scenarios: [1] }));
    const archive = menuArchiveSchema.parse(menuArchive(day, RIDE));
    const q1 = archive.waves[0].options.find((o) => o.optionId === "q1")!;
    expect(q1).toMatchObject({ status: "skipped_http_error", success: null, certificate: null, error: "http_500", routes: [] });
  });
});

describe("WP-E10 extended archive: the day-selection exchange per (date, R, L)", () => {
  it("archives the exact /internal/fleet-selection request body and its response", async () => {
    const { day, t } = await runDay();
    const posted = t.calls.filter((c) => c.path === "/api/v1/internal/fleet-selection");
    expect(posted).toHaveLength(2); // L1 and L2
    for (const [index, result] of day.scenarios.filter((s) => s.scenario !== "A").entries()) {
      const archive = selectionArchiveSchema.parse(selectionArchive(day, RIDE, result));
      expect(archive.largeLimit).toBe(result.scenario);
      expect(archive.request).toEqual(posted[index].body);
      expect((archive.request as SelectionRequest).max_large).toBe(result.scenario);
      expect(archive.httpStatus).toBe(200);
      expect(archive.response).toMatchObject({ status: "optimal", cars: 1, stats: { random_seed: 20261008, num_workers: 1 } });
    }
  });

  it("archives the exchange of an infeasible_for_L answer too, and nothing for scenario A", async () => {
    const { day } = await runDay(["A", 0], () => ({
      status: 200,
      body: { status: "infeasible_for_L", cars: null, large_peak: null, car_minutes: null, total_minutes: null, selection: {}, diagnostics: { reason: "X" }, stats: {} },
    }));
    const [a, l0] = day.scenarios;
    expect(a.selectionExchange).toBeNull();
    expect(selectionArchiveSchema.parse(selectionArchive(day, RIDE, l0)).response).toMatchObject({ status: "infeasible_for_L" });
    expect(() => selectionArchive(day, RIDE, a)).toThrow();
  });

  it("keeps the status of an unavailable selection endpoint and refuses an archive without a request", async () => {
    const { day } = await runDay([1], () => ({ status: 503, body: {} }));
    const archive = selectionArchiveSchema.parse(selectionArchive(day, RIDE, day.scenarios[0]));
    expect(archive).toMatchObject({ httpStatus: 503, response: null });
    expect(() => selectionArchiveSchema.parse({ ...archive, request: undefined })).toThrow();
  });
});

describe("WP-E10 manifest: old format stays readable, new format is strict", () => {
  const results = path.resolve(process.cwd(), "docs/paper/results");
  const oldManifests = [
    "week-2026-10-05-fleet/run_manifest.json",
    "week-2026-10-05-fleet/extra/minivan-cap3/run_manifest.json",
    "week-2026-10-05-4sw5so/run_manifest.json",
  ];
  it.each(oldManifests.slice(0, 2))("the historical manifest %s still parses with the base schema but not as a v2 archive", (file) => {
    const value = JSON.parse(fs.readFileSync(path.join(results, file), "utf8"));
    expect(() => fleetManifestSchema.parse(value)).not.toThrow();
    expect(() => extendedFleetManifestSchema.parse(value)).toThrow();
  });
  it("the historical archive directories are refused as an output location (g)", () => {
    expect(HISTORICAL_ARCHIVE_DIRS.length).toBeGreaterThanOrEqual(3);
    for (const dir of HISTORICAL_ARCHIVE_DIRS) {
      expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), dir))).toThrow();
      expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), dir, "rerun"))).toThrow();
    }
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), "docs/paper/results/week-2026-10-05-fleet-rerun"))).not.toThrow();
    expect(() => assertOutsideHistoricalArchives(path.resolve(process.cwd(), ".temp/experiments/x"))).not.toThrow();
  });
});
