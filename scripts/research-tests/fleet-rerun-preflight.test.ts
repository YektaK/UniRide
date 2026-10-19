import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import {
  PINNED, PreflightRefusal, assertPreflight, evaluatePreflight, formatPreflightReport,
  type PreflightObservation, type PreflightPins, type PreflightReference,
} from "@/services/fleet-rerun-preflight";
import { loadFleetReference } from "@/services/fleet-rerun-reference";
import { collectLiveDays, readOnlyReader, runFleetRerunPreflight, type PreflightDeps } from "@/services/fleet-rerun-preflight-live";
import { parseFleetArgs, type FleetTypeSpec } from "@/services/fleet-scenario-args";
import { DATE, large, matrixOf, reader, rows, sedan, transport } from "@/services/fleet-scenario-fixtures";

const RESULTS = path.resolve(process.cwd(), "docs/paper/results");
const LARGE_SEDAN_MANIFEST = path.join(RESULTS, "week-2026-10-05-fleet/run_manifest.json");
const DOBLO_MANIFEST = path.join(RESULTS, "week-2026-10-05-fleet/extra/minivan-cap3/run_manifest.json");
const WAVES_DIR = path.join(RESULTS, "week-2026-10-05-4sw5so");

const GA = {
  population_size: 50, max_iterations: 100, crossover_rate: 0.85, mutation_rate: 0.2, elite_count: 3, tournament_size: 4,
  max_no_improvement: 25, seed: null, local_search_type: "hybrid", local_search_interval: 10, diversify_threshold: 30,
};
const SOLVER = {
  ga: { config: GA, seed: 42 }, hf: { config: GA, seed: 42 },
  cp: { version: "9.15.6755", seed: 20261008, workers: 1 },
};
const COMMIT = "f".repeat(40);

describe("preflight against the real historical archives (design WP-E10 (a)-(c))", () => {
  it("reads both fleet manifests and the 4sw5so wave composition as the reference", () => {
    const sedanRef = loadFleetReference({ manifestPath: LARGE_SEDAN_MANIFEST, wavesDir: WAVES_DIR });
    const dobloRef = loadFleetReference({ manifestPath: DOBLO_MANIFEST, wavesDir: WAVES_DIR });
    expect(PINNED.matrixSha256).toBe("bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5");
    for (const ref of [sedanRef, dobloRef]) {
      expect(ref.matrixSha256s).toEqual([PINNED.matrixSha256]);
      const dates = Object.keys(ref.waves);
      expect(dates).toEqual(["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"]);
      const waveCount = dates.reduce((n, d) => n + Object.keys(ref.waves[d]).length, 0);
      const legCount = dates.reduce((n, d) => n + Object.values(ref.waves[d]).reduce((m, ids) => m + ids.length, 0), 0);
      expect([waveCount, legCount]).toEqual([57, 226]);
      expect(ref.parameters.admission_mode).toBe("assume_confirmed");
      expect(ref.parameters).toMatchObject({ node_budget: 200000, selection_time_limit_seconds: 30, tour_limit: 150, max_cars: null });
      expect([ref.effective_seed, ref.hf_effective_seed]).toEqual([42, 42]);
      expect(ref.selection_solver).toMatchObject({ version: "9.15.6755", random_seed: 20261008, num_workers: 1 });
      expect(ref.ga_effective_configuration).toEqual(GA);
      expect(ref.hf_effective_configuration).toEqual(GA);
    }
    expect(sedanRef.fleet_types).toEqual([
      { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 },
      { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 },
    ]);
    expect(dobloRef.fleet_types).toEqual([
      { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 },
      { typeId: "minivan", swCapacity: 1, soCapacity: 3, totalCapacity: 3, cooldownMinutes: 10 },
    ]);
    expect(sedanRef.parameters.scenarios).toEqual(["A", "L1", "L2", "L3"]);
    expect(dobloRef.parameters.scenarios).toEqual(["L0", "L1", "L2"]);
  });

  it("passes when the observation equals the reference and refuses a deviation of each rule", () => {
    const ref = loadFleetReference({ manifestPath: LARGE_SEDAN_MANIFEST, wavesDir: WAVES_DIR });
    const obs = observationFrom(ref);
    expect(evaluatePreflight(ref, obs).ok).toBe(true);

    const failedIds = (o: PreflightObservation) => evaluatePreflight(ref, o).checks.filter((c) => !c.ok).map((c) => c.id);
    const clone = () => structuredClone(obs);
    // sha256
    const sha = clone(); sha.days[0].matrix!.sha256 = "0".repeat(64);
    expect(failedIds(sha)).toContain("matrix_sha256");
    // occurrence ids
    const occ = clone(); const wave = Object.keys(occ.days[0].waves)[0]; occ.days[0].waves[wave] = occ.days[0].waves[wave].slice(1);
    expect(failedIds(occ)).toContain("occurrence_ids");
    // rule (e): a one-day subset of the reference dates is accepted only when it is explicitly allowed
    const oneDay = clone(); oneDay.cli.dates = [ref.parameters.dates[1]]; oneDay.days = [oneDay.days[1]];
    expect(failedIds(oneDay)).toEqual(expect.arrayContaining(["grid", "occurrence_ids"]));
    oneDay.cli.allowSubsetDates = true;
    expect(evaluatePreflight(ref, oneDay).checks.find((c) => c.id === "grid")!.message).toMatch(/rule \(e\).*ordered subset/);
    expect(evaluatePreflight(ref, oneDay).checks.filter((c) => !c.ok)).toEqual([]);
    const foreign = clone(); foreign.cli.dates = ["2026-10-12"]; foreign.cli.allowSubsetDates = true;
    expect(failedIds(foreign)).toContain("grid");
    const reordered = clone(); reordered.cli.dates = [...ref.parameters.dates].reverse(); reordered.cli.allowSubsetDates = true;
    expect(failedIds(reordered)).toContain("grid");
    // N2: same ids, but a student of the wave changes class (Sw/So)
    const cls = clone(); const w2 = Object.keys(cls.days[0].classes)[0]; cls.days[0].classes[w2] = { sw: cls.days[0].classes[w2].sw + 1, so: cls.days[0].classes[w2].so - 1 };
    expect(failedIds(cls)).toContain("occurrence_ids");
    // fleet types
    const types = clone(); types.cli.fleetTypes = [types.cli.fleetTypes[0], { ...types.cli.fleetTypes[1], soCapacity: 3 }];
    expect(failedIds(types)).toContain("fleet_types");
    // dirty tree
    const dirty = clone(); dirty.git.dirty = true;
    expect(failedIds(dirty)).toContain("clean_tree");
    // configuration
    const cfg = clone(); cfg.solver.ga.config = { ...GA, population_size: 51 };
    expect(failedIds(cfg)).toContain("ga_configuration");
  });
});

describe("the documented re-run commands match the old manifests (design (a): fleet types, grid, limits)", () => {
  // Command lines of the two campaigns as documented in their READMEs (equivalent invocations), plus the WP-E10 flags.
  const common = ["--week-of", "2026-10-05", "--ride-limits", "50,60,70,90", "--tour-limit", "150", "--fixed-type", "large", "--pin-commit", "f7e014c", "--reference-manifest", "m"];
  const cases: Array<[string, string, string[]]> = [
    ["large+sedan", LARGE_SEDAN_MANIFEST, [...common, "--fleet-types", "large:4sw5so:cd10,sedan:0sw4so:cd10", "--minimize-type", "sedan", "--scenarios", "A,1,2,3"]],
    ["large+Doblo cap3", DOBLO_MANIFEST, [...common, "--fleet-types", "large:4sw5so:cd10,minivan:1sw3so:cap3:cd10", "--minimize-type", "minivan", "--scenarios", "0,1,2"]],
  ];
  it.each(cases)("%s: the parsed command line passes the fleet-type, grid, limit and admission checks", (_name, manifestPath, argv) => {
    const ref = loadFleetReference({ manifestPath, wavesDir: WAVES_DIR });
    const args = parseFleetArgs(argv);
    const obs = observationFrom(ref);
    obs.cli = {
      dates: args.dates, rideLimits: args.rideLimits, tourLimit: args.tourLimit, scenarios: args.scenarios.map((s) => (s === "A" ? "A" : `L${s}`)),
      maxCars: args.maxCars, nodeBudget: args.nodeBudget, selectionTimeLimitSeconds: args.selectionTimeLimitSeconds, admissionMode: "assume_confirmed",
      fleetTypes: args.fleetTypes, fixedType: args.fixedTypeId, minimizeType: args.minimizeTypeId,
    };
    expect(evaluatePreflight(ref, obs).checks.filter((c) => !c.ok)).toEqual([]);
  });
  it("a large+sedan command line is refused against the Doblo manifest (the minivan is not a sedan)", () => {
    const ref = loadFleetReference({ manifestPath: DOBLO_MANIFEST, wavesDir: WAVES_DIR });
    const args = parseFleetArgs(cases[0][2]);
    const obs = observationFrom(ref);
    obs.cli = { ...obs.cli, fleetTypes: args.fleetTypes, minimizeType: args.minimizeTypeId, scenarios: ["A", "L1", "L2", "L3"] };
    expect(evaluatePreflight(ref, obs).checks.filter((c) => !c.ok).map((c) => c.id)).toEqual(expect.arrayContaining(["fleet_types", "grid"]));
  });
});

function observationFrom(ref: PreflightReference): PreflightObservation {
  return {
    git: { head: COMMIT, dirty: false }, pinCommit: COMMIT.slice(0, 12),
    cli: {
      dates: ref.parameters.dates, rideLimits: ref.parameters.ride_limits, tourLimit: ref.parameters.tour_limit,
      scenarios: ref.parameters.scenarios, maxCars: ref.parameters.max_cars, nodeBudget: ref.parameters.node_budget,
      selectionTimeLimitSeconds: ref.parameters.selection_time_limit_seconds, admissionMode: "assume_confirmed",
      fleetTypes: ref.fleet_types, fixedType: ref.fixed_type, minimizeType: ref.minimize_type,
    },
    solver: structuredClone(SOLVER),
    days: Object.entries(ref.waves).map(([date, waves]) => ({
      date, status: "ready",
      matrix: { sha256: PINNED.matrixSha256, source: "supabase", id: `time_matrix:sha256:${PINNED.matrixSha256}`, version: PINNED.matrixSha256 },
      waves: structuredClone(waves), classes: structuredClone(ref.waveClasses[date]),
    })),
  };
}

// ---- the live collector and the refusal paths, on the small harness week -----------------------------------
const pins: PreflightPins = { ...PINNED, matrixSha256: "a".repeat(64), waveCount: 2, legCount: 6 };
const baseCli = (fleetTypes: FleetTypeSpec[] = [large, sedan]) => ({
  dates: [DATE], rideLimits: [60], tourLimit: 150, scenarios: ["A", "L1", "L2"], maxCars: null, nodeBudget: 200000,
  selectionTimeLimitSeconds: 30, admissionMode: "assume_confirmed", fleetTypes, fixedType: "large", minimizeType: "sedan",
});

async function liveReference(): Promise<PreflightReference> {
  const t = transport();
  const days = await collectLiveDays({ reader: reader(rows()).client, optimizerFetch: t.fetch }, [DATE]);
  const wavesByDate = Object.fromEntries(days.map((d) => [d.date, d.waves]));
  const base = loadFleetReference({ manifestPath: LARGE_SEDAN_MANIFEST, wavesDir: WAVES_DIR });
  return {
    ...base, parameters: { ...base.parameters, dates: [DATE], ride_limits: [60], scenarios: ["A", "L1", "L2"] },
    matrixSha256s: ["a".repeat(64)], waves: wavesByDate,
    waveClasses: Object.fromEntries(days.map((d) => [d.date, d.classes])),
  };
}

function deps(over: Partial<{ data: Record<string, unknown[]>; transport: ReturnType<typeof transport>["fetch"]; dirty: boolean; head: string; solver: typeof SOLVER }> = {}) {
  const db = reader(over.data ?? rows());
  const t = transport();
  const value: PreflightDeps & { db: typeof db; t: typeof t } = {
    reader: db.client, optimizerFetch: over.transport ?? t.fetch,
    git: () => ({ head: over.head ?? COMMIT, dirty: over.dirty ?? false }),
    captureSolver: () => over.solver ?? structuredClone(SOLVER),
    db, t,
  };
  return value;
}
const input = (cli = baseCli()) => ({ cli, pinCommit: COMMIT.slice(0, 10) });

describe("read-only preflight run (WP-E10 phase 1)", () => {
  it("passes on matching inputs, reads only the four demand tables and the matrix snapshot, and never solves or writes", async () => {
    const ref = await liveReference();
    const d = deps();
    const { report } = await runFleetRerunPreflight(d, input(), ref, pins);
    expect(report.ok).toBe(true);
    expect(d.db.writes).toEqual([]);
    expect([...new Set(d.db.tables)].sort()).toEqual(["ride_requests", "student_leg_decisions", "users", "weekly_schedules"]);
    expect([...new Set(d.t.calls.map((c) => c.path))]).toEqual(["/api/v1/internal/matrix-snapshot"]);
    // the printable report holds no raw student ids
    expect(formatPreflightReport(report)).not.toContain("s-sw");
  });

  it("the reader handed to the campaign cannot write", () => {
    const db = reader(rows());
    const guarded = readOnlyReader(db.client);
    expect(() => (guarded.from("users") as unknown as { insert: () => void }).insert()).toThrow();
    expect(() => (guarded.from("users") as unknown as { update: () => void }).update()).toThrow();
    expect(() => (guarded.from("users") as unknown as { upsert: () => void }).upsert()).toThrow();
    expect(() => (guarded.from("users") as unknown as { delete: () => void }).delete()).toThrow();
    expect(() => (guarded as unknown as { rpc: () => void }).rpc()).toThrow();
    expect(db.writes).toEqual([]);
    expect(() => guarded.from("users").select("id").eq("role", "student")).not.toThrow();
  });

  it("refuses a matrix whose sha256 differs from the archive", async () => {
    const ref = await liveReference();
    const other = "b".repeat(64);
    const d = deps({ transport: async (p, init) => (p === "/api/v1/internal/matrix-snapshot"
      ? Response.json({ ...matrixOf(5), id: `time_matrix:sha256:${other}`, version: other, sha256: other }) : transport().fetch(p, init)) });
    const { report } = await runFleetRerunPreflight(d, input(), ref, pins);
    expect(report.ok).toBe(false);
    expect(report.checks.filter((c) => !c.ok).map((c) => c.id)).toEqual(["matrix_sha256"]);
    expect(() => assertPreflight(report)).toThrow(PreflightRefusal);
  });

  it("refuses when the live occurrence ids differ from the archive", async () => {
    const ref = await liveReference();
    const data = rows();
    data.users = data.users.filter((u) => (u as { id: string }).id !== "s-so2");
    const { report } = await runFleetRerunPreflight(deps({ data }), input(), ref, pins);
    expect(report.checks.filter((c) => !c.ok).map((c) => c.id)).toContain("occurrence_ids");
    expect(report.ok).toBe(false);
  });

  it("refuses when a student moves to another location code (same count, other composition)", async () => {
    const ref = await liveReference();
    const data = rows();
    (data.users[2] as { location_code: string }).location_code = "So1";
    const { report } = await runFleetRerunPreflight(deps({ data }), input(), ref, pins);
    expect(report.checks.filter((c) => !c.ok).map((c) => c.id)).toContain("occurrence_ids");
  });

  it("refuses CLI fleet types that differ from the old manifest", async () => {
    const ref = await liveReference();
    const { report } = await runFleetRerunPreflight(deps(), input(baseCli([large, { ...sedan, swCapacity: 1 }])), ref, pins);
    expect(report.checks.filter((c) => !c.ok).map((c) => c.id)).toEqual(["fleet_types"]);
  });

  it("refuses a dirty working tree and a commit other than the pinned one", async () => {
    const ref = await liveReference();
    const dirty = await runFleetRerunPreflight(deps({ dirty: true }), input(), ref, pins);
    expect(dirty.report.checks.filter((c) => !c.ok).map((c) => c.id)).toEqual(["clean_tree"]);
    const moved = await runFleetRerunPreflight(deps({ head: "e".repeat(40) }), input(), ref, pins);
    expect(moved.report.checks.filter((c) => !c.ok).map((c) => c.id)).toEqual(["pinned_commit"]);
  });

  it("refuses a GA, HF, seed, CP-SAT or limit deviation", async () => {
    const ref = await liveReference();
    const failed = async (solver: typeof SOLVER, cli = baseCli()) =>
      (await runFleetRerunPreflight(deps({ solver }), input(cli), ref, pins)).report.checks.filter((c) => !c.ok).map((c) => c.id);
    expect(await failed({ ...SOLVER, ga: { ...SOLVER.ga, config: { ...GA, mutation_rate: 0.25 } } })).toEqual(["ga_configuration"]);
    expect(await failed({ ...SOLVER, hf: { ...SOLVER.hf, config: { ...GA, local_search_type: "none" } } })).toEqual(["hf_configuration"]);
    expect(await failed({ ...SOLVER, ga: { ...SOLVER.ga, seed: 43 } })).toEqual(["seeds"]);
    expect(await failed({ ...SOLVER, cp: { ...SOLVER.cp, version: "9.16.0" } })).toEqual(["selection_solver"]);
    expect(await failed({ ...SOLVER, cp: { ...SOLVER.cp, workers: 8 } })).toEqual(["selection_solver"]);
    expect(await failed(SOLVER, { ...baseCli(), nodeBudget: 100000 })).toEqual(["node_budget"]);
    expect(await failed(SOLVER, { ...baseCli(), selectionTimeLimitSeconds: 60 })).toEqual(["selection_time_limit"]);
    expect(await failed(SOLVER, { ...baseCli(), admissionMode: "confirmed_only" })).toEqual(["admission_mode"]);
  });

  it("fails closed when the matrix snapshot or the demand is unavailable", async () => {
    const ref = await liveReference();
    const down = await runFleetRerunPreflight(
      deps({ transport: async () => new Response("{}", { status: 503 }) }), input(), ref, pins);
    expect(down.report.ok).toBe(false);
    expect(down.report.checks.filter((c) => !c.ok).map((c) => c.id)).toContain("matrix_sha256");
    const empty = await runFleetRerunPreflight(deps({ data: { ...rows(), users: [] } }), input(), ref, pins);
    expect(empty.report.ok).toBe(false);
  });
});
