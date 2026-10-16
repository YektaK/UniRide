import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import dotenv from "dotenv";
import { resolveSharedKey, buildChildEnv, resolvePythonBin } from "./start-dudullu-local.mjs";
import {
  captureMatrixSnapshot, anonymizeResponse, toCsv, fetchWithRateLimitRetry, type ExperimentMatrix,
} from "../src/services/plan-experiments";
import { parseFleetArgs } from "../src/services/fleet-scenario-args";
import {
  FLEET_DAILY_COLUMNS, FLEET_WEEKLY_COLUMNS, CAR_WINDOW_COLUMNS, aggregateFleetWeeks, carWindowRows, fleetDailyRows,
  manifestRun, scenarioName, type FleetDailyRow, type FleetManifest,
} from "../src/services/fleet-scenario-report";
import type { FleetScenarioDay } from "../src/services/fleet-scenario-run";
import {
  FLEET_ARCHIVE_FORMAT, assertOutsideHistoricalArchives, extendedFleetManifestSchema, menuArchive, menuArchiveName, menuArchiveSchema,
  selectionArchive, selectionArchiveName, selectionArchiveSchema,
} from "../src/services/fleet-scenario-archive";
import { PINNED, formatPreflightReport } from "../src/services/fleet-rerun-preflight";
import { loadFleetReference } from "../src/services/fleet-rerun-reference";

const usage = "npm run experiments:fleet -- --week-of YYYY-MM-DD [--ride-limits 50,60,70,90] [--tour-limit 150] --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 [--fixed-type large] [--minimize-type sedan] [--scenarios A,1,2,3] [--max-cars N] [--node-budget 200000] [--selection-time-limit 30] --pin-commit <hex commit> --reference-manifest <old run_manifest.json> [--reference-waves <4sw5so archive dir>] [--preflight-only] [--out <new results directory>]\n" +
  "Type grammar: <id>:<n>sw<m>so[:cd<min>][:r<R>][:t<T>]. Scenario A = minimum all-large; an integer is the fixed number of large vehicles L (0..4).\n" +
  "Use --dates YYYY-MM-DD,YYYY-MM-DD instead of --week-of for explicit dates. Fleet types come only from the command line; the vehicles table is never read. Optimizer must already be running with the same internal key.\n" +
  "WP-E10: the run first compares the live inputs with the old campaign (read-only preflight) and refuses on any difference; --preflight-only stops after that check and writes nothing.";
const SAFE_MESSAGES = [
  usage,
  "Configure the same internal key in the CLI and running optimizer; an unshared generated key cannot authenticate.",
  "Python runtime required for solver configuration provenance; set UNIRIDE_PYTHON.",
  "Could not capture local solver configuration; check the Python runtime locally.",
  "Output directory already exists; choose a fresh --out directory.",
  "Fleet experiment export failed; completed results are preserved. Check local services and input provenance.",
  "--pin-commit and --reference-manifest are required: the run is refused without the input preflight.",
  "Could not read the reference campaign; check --reference-manifest and --reference-waves.",
  "Output directory lies inside a historical archive; choose a new directory.",
  "Preflight refused: the live inputs or settings differ from the old campaign. Nothing was solved or written.",
];
const DEFAULT_REFERENCE_WAVES = "docs/paper/results/week-2026-10-05-4sw5so";

/** An abort whose message is built here and holds no secret or student data, so it may be printed. */
class RerunAbort extends Error {}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length === 1 && argv[0] === "--help") { console.log(usage); return; }
  const startedAt = new Date();
  let args;
  try { args = parseFleetArgs(argv, startedAt); }
  catch { throw new Error(usage); }
  if (args.pinCommit === null || args.referenceManifest === null) {
    throw new Error("--pin-commit and --reference-manifest are required: the run is refused without the input preflight.");
  }
  const root = process.cwd();
  for (const file of [".env.local", "optimizer_api/.env"]) {
    const filename = path.join(root, file);
    if (!fs.existsSync(filename)) continue;
    for (const [name, value] of Object.entries(dotenv.parse(fs.readFileSync(filename)))) {
      if (process.env[name] === undefined) process.env[name] = value;
    }
  }
  const shared = resolveSharedKey({ web: process.env.OPTIMIZER_INTERNAL_API_KEY, python: process.env.INTERNAL_API_KEY });
  if (!shared.configured) throw new Error("Configure the same internal key in the CLI and running optimizer; an unshared generated key cannot authenticate.");
  Object.assign(process.env, buildChildEnv(process.env, shared.key));

  // Import only after loading environment: these modules capture configuration at import time.
  const [{ runFleetScenarioDay, scenarioResponse }, { getSupabaseAdmin }, { optimizerFetch }, { readOnlyReader, runFleetRerunPreflight }] = await Promise.all([
    import("../src/services/fleet-scenario-run"), import("../src/lib/supabase-admin"), import("../src/lib/optimizer-server"),
    import("../src/services/fleet-rerun-preflight-live"),
  ]);
  const python = resolvePythonBin(process.env, root);
  if (!python) throw new Error("Python runtime required for solver configuration provenance; set UNIRIDE_PYTHON.");
  type Capture = {
    ga: { defaults: Record<string, unknown>; config: Record<string, unknown>; seed: number };
    hf: { config: Record<string, unknown>; seed: number };
    cp: { version: string | null; seed: number | null; workers: number | null };
  };
  const captureSolver = (): Capture => {
    try {
      const text = execFileSync(python, [path.join(root, "scripts", "capture_fleet_solver_config.py")], {
        cwd: root, env: process.env, windowsHide: true, timeout: 60_000, stdio: ["ignore", "pipe", "pipe"],
      }).toString();
      const parsed = JSON.parse(text.trim().split(/\r?\n/).at(-1)!);
      if (!parsed?.ga || !Number.isInteger(parsed.ga.seed) || !Number.isInteger(parsed.hf?.seed)) throw new Error();
      return parsed;
    } catch { throw new Error("Could not capture local solver configuration; check the Python runtime locally."); }
  };
  const git = (...gitArgs: string[]) => execFileSync("git", gitArgs, { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
  const solver = captureSolver();

  // ---- WP-E10 input preflight: read-only, before any solve; refuses on any difference ----------------------------
  let reference;
  try {
    reference = loadFleetReference({
      manifestPath: path.resolve(root, args.referenceManifest), wavesDir: path.resolve(root, args.referenceWaves ?? DEFAULT_REFERENCE_WAVES),
    });
  } catch { throw new Error("Could not read the reference campaign; check --reference-manifest and --reference-waves."); }
  const guardedReader = readOnlyReader(getSupabaseAdmin());
  const preflight = await runFleetRerunPreflight({
    reader: guardedReader, optimizerFetch,
    git: () => ({ head: git("rev-parse", "HEAD"), dirty: git("status", "--porcelain").length > 0 }),
    captureSolver: () => solver,
  }, {
    pinCommit: args.pinCommit,
    cli: {
      dates: args.dates, rideLimits: args.rideLimits, tourLimit: args.tourLimit, scenarios: args.scenarios.map(scenarioName),
      maxCars: args.maxCars, nodeBudget: args.nodeBudget, selectionTimeLimitSeconds: args.selectionTimeLimitSeconds,
      admissionMode: "assume_confirmed", fleetTypes: args.fleetTypes, fixedType: args.fixedTypeId, minimizeType: args.minimizeTypeId,
    },
  }, reference);
  console.log(formatPreflightReport(preflight.report));
  if (!preflight.report.ok) {
    process.exitCode = 2;
    throw new Error("Preflight refused: the live inputs or settings differ from the old campaign. Nothing was solved or written.");
  }
  if (args.preflightOnly) { console.log("Preflight only: nothing was solved or written."); return; }

  const commit = git("rev-parse", "HEAD");
  const dirty = git("status", "--porcelain").length > 0;
  const out = path.resolve(root, args.out);
  assertOutsideHistoricalArchives(out, root);
  // Refuse overwriting an existing campaign, including its provenance and results.
  if (fs.existsSync(out)) throw new Error("Output directory already exists; choose a fresh --out directory.");
  fs.mkdirSync(out, { recursive: true });

  const fixedType = args.fleetTypes.find((type) => type.typeId === args.fixedTypeId)!;
  const minimiseType = args.fleetTypes.find((type) => type.typeId === args.minimizeTypeId) ?? null;
  const reader = guardedReader;
  const dailyRows: FleetDailyRow[] = [];
  const windowRows: ReturnType<typeof carWindowRows> = [];
  const writeJson = (file: string, value: unknown) => fs.writeFileSync(path.join(out, file), JSON.stringify(value, null, 2) + "\n");
  const manifest: FleetManifest = {
    git_commit: commit, dirty_working_tree: dirty, timestamp: startedAt.toISOString(),
    parameters: {
      dates: args.dates, ride_limits: args.rideLimits, tour_limit: args.tourLimit,
      scenarios: args.scenarios.map(scenarioName), max_cars: args.maxCars, node_budget: args.nodeBudget,
      selection_time_limit_seconds: args.selectionTimeLimitSeconds, admission_mode: "assume_confirmed",
    },
    fleet_types: args.fleetTypes, fleet_types_source: "cli", fixed_type: args.fixedTypeId, minimize_type: args.minimizeTypeId,
    db_vehicles_consulted: false,
    algorithms: { baseline: "ga_split", menu: "ga_split_hf" }, termination_protocol: "native",
    ga_defaults: solver.ga.defaults, ga_effective_configuration: solver.ga.config, effective_seed: solver.ga.seed,
    hf_effective_configuration: solver.hf.config, hf_effective_seed: solver.hf.seed,
    selection_solver: {
      name: "cp-sat", version: solver.cp.version, random_seed: solver.cp.seed, num_workers: solver.cp.workers,
      time_limit_seconds: args.selectionTimeLimitSeconds,
    },
    vehicle_count_scope: "cars are the minimum over the per-wave option menus (heuristic GA routes) and exact for the chosen fixed routes when proven; not a global minimum",
    weekly_cars_definition: "weekly_cars = maximum over weekdays (same cars every day); cars_day_sum and monday_cars..friday_cars give the per-day need (borrow per day)",
    runs: [], state: "running", completed_at: null,
    archive_format: FLEET_ARCHIVE_FORMAT, pinned_commit: args.pinCommit, preflight: preflight.record,
  };
  const checkpoint = () => {
    extendedFleetManifestSchema.parse(manifest);
    writeJson("run_manifest.json", manifest);
    fs.writeFileSync(path.join(out, "scenario_daily.csv"), toCsv(dailyRows, FLEET_DAILY_COLUMNS));
    fs.writeFileSync(path.join(out, "scenario_weekly.csv"), toCsv(aggregateFleetWeeks(dailyRows), FLEET_WEEKLY_COLUMNS));
    fs.writeFileSync(path.join(out, "car_usage_windows.csv"), toCsv(windowRows, CAR_WINDOW_COLUMNS));
  };
  checkpoint();
  try {
    for (const date of args.dates) for (const ride of args.rideLimits) {
      let matrix: ExperimentMatrix | null = null;
      let matrixDrift = false;
      const rateLimitWaits: Array<{ path: string; status: number; wait_seconds: number; attempt: number }> = [];
      const httpFailures: Array<{ path: string; status: number }> = [];
      const fetchWithSnapshot = async (requestPath: string, init?: RequestInit) => {
        // 429 handling identical to experiments:plan: up to two waits of at most 60 s each.
        const response = await fetchWithRateLimitRetry(optimizerFetch, requestPath, init, {
          onRetry: (seconds, attempt) => {
            rateLimitWaits.push({ path: requestPath, status: 429, wait_seconds: seconds, attempt });
            console.log(`Optimizer rate limit: waiting ${seconds}s before retry ${attempt}.`);
          },
        });
        if (!response.ok) httpFailures.push({ path: requestPath, status: response.status });
        if (requestPath === "/api/v1/internal/matrix-snapshot" && response.ok) {
          try { matrix = captureMatrixSnapshot(await response.clone().json()); }
          catch { matrix = null; }
          // (a) every captured matrix must declare the archived sha256: a changed snapshot stops the day before any solve.
          if (matrix && matrix.sha256 !== PINNED.matrixSha256) { matrixDrift = true; matrix = null; return new Response("{}", { status: 503 }); }
        }
        return response;
      };
      let day: FleetScenarioDay;
      try {
        day = await runFleetScenarioDay({ reader, optimizerFetch: fetchWithSnapshot, clock: () => new Date() }, {
          serviceDate: date, maxRideTimeMinutes: ride, maxTourMinutes: args.tourLimit,
          fixedType, minimiseType, scenarios: args.scenarios, maxCars: args.maxCars,
          nodeBudget: args.nodeBudget, selectionTimeLimitSeconds: args.selectionTimeLimitSeconds,
        });
      } catch {
        day = {
          serviceDate: date, status: "blocked_data", reasonCodes: ["SCENARIO_RUN_UNAVAILABLE"], dbVehiclesConsulted: false,
          limits: { maxRideTimeMinutes: ride, maxTourMinutes: args.tourLimit }, students: 0, legs: 0, waves: 0,
          occurrenceLabels: {}, matrix: null, menu: [], menuDetail: [], scenarios: [],
        };
      }
      if (matrixDrift) throw new RerunAbort("Matrix snapshot sha256 changed during the run; stopped before any solve of this day.");
      const captured = matrix as ExperimentMatrix | null;
      const stem = `${date}_R${ride}`;
      const responseFiles: string[] = [];
      const files = day.scenarios.length ? day.scenarios : [];
      for (const result of files) {
        const file = `${stem}_${scenarioName(result.scenario)}.response.json`;
        writeJson(file, anonymizeResponse(scenarioResponse(day, result)));
        responseFiles.push(file);
      }
      if (files.length === 0) {
        const file = `${stem}.response.json`;
        writeJson(file, anonymizeResponse({ serviceDate: date, dayStatus: day.status, reasonCodes: day.reasonCodes, occurrenceLabels: day.occurrenceLabels }));
        responseFiles.push(file);
      }
      if (captured) writeJson(`${stem}.matrix.json`, captured);
      // WP-E10 extended archive (f): every menu option, and the selection exchange of every L. Validated before it is written.
      let menuFile: string | null = null;
      const exchangeFiles: Array<{ scenario: string; file: string }> = [];
      if (day.menuDetail.length > 0) {
        const written = anonymizeResponse(menuArchive(day, ride));
        menuArchiveSchema.parse(written);
        menuFile = menuArchiveName(stem);
        writeJson(menuFile, written);
      }
      for (const result of day.scenarios) {
        if (result.scenario === "A" || result.selectionExchange === null) continue;
        const written = anonymizeResponse(selectionArchive(day, ride, result));
        selectionArchiveSchema.parse(written);
        const file = selectionArchiveName(stem, result.scenario);
        writeJson(file, written);
        exchangeFiles.push({ scenario: scenarioName(result.scenario), file });
      }
      const rows = fleetDailyRows(day, args.scenarios, ride, args.tourLimit, fixedType, minimiseType);
      dailyRows.push(...rows);
      windowRows.push(...carWindowRows(day, ride));
      manifest.runs.push(manifestRun(
        day, ride, responseFiles, captured ? `${stem}.matrix.json` : null, captured?.provenance ?? null, rateLimitWaits, httpFailures,
        { menuOptionsFile: menuFile, selectionExchangeFiles: exchangeFiles },
      ));
      checkpoint();
      for (const row of rows) {
        console.log(`${date} R${ride} ${row.scenario}: ${row.status}; cars=${row.cars ?? "n/a"}, large=${row.large_vehicles ?? "n/a"}, routes=${row.routes ?? "unknown"}, total_min=${row.total_vehicle_minutes ?? "unknown"}`);
      }
    }
    manifest.state = "completed";
    manifest.completed_at = new Date().toISOString();
    checkpoint();
    console.log(`Completed ${dailyRows.length} scenario rows. Results: ${args.out}`);
  } catch (error) {
    manifest.state = "failed";
    manifest.completed_at = new Date().toISOString();
    try { checkpoint(); } catch { /* keep the previous checkpoint */ }
    if (error instanceof RerunAbort) throw error;
    throw new Error("Fleet experiment export failed; completed results are preserved. Check local services and input provenance.");
  }
}

void main().catch((error) => {
  // Never print raw SDK, HTTP, Python or filesystem diagnostics that can contain secrets.
  const safe = error instanceof RerunAbort || (error instanceof Error && SAFE_MESSAGES.includes(error.message))
    ? (error as Error).message : "Fleet experiment runner failed. Check local configuration; diagnostics are intentionally redacted.";
  console.error(safe);
  process.exitCode ||= 1;
});
