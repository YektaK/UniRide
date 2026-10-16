import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { runFleetScenarioDay } from "@/services/fleet-scenario-run";
import { fleetManifestSchema, manifestRun } from "@/services/fleet-scenario-report";
import {
  FLEET_ARCHIVE_FORMAT, HISTORICAL_ARCHIVE_DIRS, assertOutsideHistoricalArchives, menuArchive, menuArchiveSchema,
  selectionArchive, selectionArchiveSchema, extendedFleetManifestSchema,
} from "@/services/fleet-scenario-archive";
import { DATE, params, pickSelection, reader, rows, transport, type SelectionRequest } from "./fleet-scenario-fixtures";

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

describe("WP-E10 extended manifest (v2)", () => {
  const sha = "f".repeat(40);
  const preflight = {
    ok: true, checks: [{ id: "clean_tree", ok: true, message: "clean" }], reference_manifest: "m", reference_git_commit: "8ab88ca", reference_waves_archive: "w",
    live: { matrix_sha256: ["a".repeat(64)], waves: 2, legs: 6, waves_by_date: { [DATE]: 2 }, legs_by_date: { [DATE]: 6 } },
  };
  async function manifest(): Promise<Record<string, unknown>> {
    const { day } = await runDay();
    const run = manifestRun(day, RIDE, ["f.json"], "m.json", { sha256: "x" }, [], [], {
      menuOptionsFile: "2026-09-30_R60.menu_options.json",
      selectionExchangeFiles: [{ scenario: "L1", file: "a.json" }, { scenario: "L2", file: "b.json" }],
    });
    return {
      git_commit: sha, dirty_working_tree: false, timestamp: "2026-10-18T10:00:00.000Z",
      parameters: { dates: [DATE], ride_limits: [RIDE], tour_limit: 150, scenarios: ["A", "L1", "L2"], max_cars: null, node_budget: 200000, selection_time_limit_seconds: 30, admission_mode: "assume_confirmed" },
      fleet_types: [{ typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 }, { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 }],
      fleet_types_source: "cli", fixed_type: "large", minimize_type: "sedan", db_vehicles_consulted: false,
      algorithms: { baseline: "ga_split", menu: "ga_split_hf" }, termination_protocol: "native",
      ga_defaults: {}, ga_effective_configuration: {}, effective_seed: 42, hf_effective_configuration: {}, hf_effective_seed: 42,
      selection_solver: { name: "cp-sat", version: "9.15.6755", random_seed: 20261008, num_workers: 1, time_limit_seconds: 30 },
      vehicle_count_scope: "s", weekly_cars_definition: "d", runs: [run], state: "completed", completed_at: "2026-10-18T11:00:00.000Z",
      archive_format: FLEET_ARCHIVE_FORMAT, pinned_commit: sha.slice(0, 12), preflight,
    };
  }
  it("accepts a clean, pinned, preflighted manifest with the per-option and selection files", async () => {
    const value = await manifest();
    expect(() => extendedFleetManifestSchema.parse(value)).not.toThrow();
  });
  it.each<[string, (m: Record<string, unknown>) => void]>([
    ["dirty tree", (m) => { m.dirty_working_tree = true; }],
    ["commit other than the pinned one", (m) => { m.pinned_commit = "e".repeat(12); }],
    ["no pinned commit", (m) => { delete m.pinned_commit; }],
    ["no preflight", (m) => { delete m.preflight; }],
    ["failed preflight", (m) => { m.preflight = { ...preflight, ok: false }; }],
    ["no archive format", (m) => { delete m.archive_format; }],
    ["a run without the per-option file", (m) => { (m.runs as Array<Record<string, unknown>>)[0].menu_options_file = null; }],
    ["a run without the selection exchange list", (m) => { delete (m.runs as Array<Record<string, unknown>>)[0].selection_exchange_files; }],
    ["a completed run with an optimizer HTTP failure (an option was lost)", (m) => { (m.runs as Array<Record<string, unknown>>)[0].optimizer_http_failures = [{ path: "/api/v1/optimize", status: 429 }]; }],
    ["a completed run with a blocked day", (m) => { (m.runs as Array<Record<string, unknown>>)[0].day_status = "blocked_data"; }],
    ["a completed run that misses a grid cell", (m) => { (m.parameters as Record<string, unknown>).ride_limits = [RIDE, 70]; }],
  ])("rejects %s", async (_name, change) => {
    const value = await manifest();
    change(value);
    expect(() => extendedFleetManifestSchema.parse(value)).toThrow();
  });
});
