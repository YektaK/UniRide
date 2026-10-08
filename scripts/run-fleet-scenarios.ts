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
  fleetManifestSchema, manifestRun, scenarioName, type FleetDailyRow, type FleetManifest,
} from "../src/services/fleet-scenario-report";
import type { FleetScenarioDay } from "../src/services/fleet-scenario-run";

const usage = "npm run experiments:fleet -- --week-of YYYY-MM-DD [--ride-limits 50,60,70,90] [--tour-limit 150] --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 [--fixed-type large] [--minimize-type sedan] [--scenarios A,1,2,3] [--max-cars N] [--node-budget 200000] [--selection-time-limit 30] [--out .temp/experiments/fleet-run]\n" +
  "Type grammar: <id>:<n>sw<m>so[:cd<min>][:r<R>][:t<T>]. Scenario A = minimum all-large; an integer is the fixed number of large vehicles L (0..4).\n" +
  "Use --dates YYYY-MM-DD,YYYY-MM-DD instead of --week-of for explicit dates. Fleet types come only from the command line; the vehicles table is never read. Optimizer must already be running with the same internal key.";
const SAFE_MESSAGES = [
  usage,
  "Configure the same internal key in the CLI and running optimizer; an unshared generated key cannot authenticate.",
  "Python runtime required for solver configuration provenance; set UNIRIDE_PYTHON.",
  "Could not capture local solver configuration; check the Python runtime locally.",
  "Output directory already exists; choose a fresh --out directory.",
  "Fleet experiment export failed; completed results are preserved. Check local services and input provenance.",
];

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length === 1 && argv[0] === "--help") { console.log(usage); return; }
  const startedAt = new Date();
  let args;
  try { args = parseFleetArgs(argv, startedAt); }
  catch { throw new Error(usage); }
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
  const [{ runFleetScenarioDay, scenarioResponse }, { getSupabaseAdmin }, { optimizerFetch }] = await Promise.all([
    import("../src/services/fleet-scenario-run"), import("../src/lib/supabase-admin"), import("../src/lib/optimizer-server"),
  ]);
  const python = resolvePythonBin(process.env, root);
  if (!python) throw new Error("Python runtime required for solver configuration provenance; set UNIRIDE_PYTHON.");
  let solver: {
    ga: { defaults: Record<string, unknown>; config: Record<string, unknown>; seed: number };
    hf: { config: Record<string, unknown>; seed: number };
    cp: { version: string | null; seed: number | null; workers: number | null };
  };
  try {
    const code = [
      "import sys,json; sys.path.insert(0,'optimizer_api')",
      "from strategies.ga_split_strategy import GASplitStrategy",
      "from strategies.ga_split_hf_strategy import GASplitHFStrategy",
      "from uniride_core.planning import typed_day_selection as d",
      "import ortools",
      "a=GASplitStrategy(); b=GASplitHFStrategy()",
      "print(json.dumps({'ga':{'defaults':a.DEFAULT_CONFIG,'config':a.config,'seed':a.seed},'hf':{'config':b.config,'seed':b.seed},'cp':{'version':getattr(ortools,'__version__',None),'seed':d.SOLVER_SEED,'workers':1}}))",
    ].join("\n");
    const text = execFileSync(python, ["-c", code], {
      cwd: root, env: process.env, windowsHide: true, timeout: 60_000, stdio: ["ignore", "pipe", "pipe"],
    }).toString();
    const parsed = JSON.parse(text);
    if (!parsed?.ga || !Number.isInteger(parsed.ga.seed) || !Number.isInteger(parsed.hf?.seed)) throw new Error();
    solver = parsed;
  } catch { throw new Error("Could not capture local solver configuration; check the Python runtime locally."); }
  const git = (...gitArgs: string[]) => execFileSync("git", gitArgs, { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
  const commit = git("rev-parse", "HEAD");
  const dirty = git("status", "--porcelain").length > 0;
  const out = path.resolve(root, args.out);
  // Refuse overwriting an existing campaign, including its provenance and results.
  if (fs.existsSync(out)) throw new Error("Output directory already exists; choose a fresh --out directory.");
  fs.mkdirSync(out, { recursive: true });

  const fixedType = args.fleetTypes.find((type) => type.typeId === args.fixedTypeId)!;
  const minimiseType = args.fleetTypes.find((type) => type.typeId === args.minimizeTypeId) ?? null;
  const reader = getSupabaseAdmin();
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
  };
  const checkpoint = () => {
    fleetManifestSchema.parse(manifest);
    writeJson("run_manifest.json", manifest);
    fs.writeFileSync(path.join(out, "scenario_daily.csv"), toCsv(dailyRows, FLEET_DAILY_COLUMNS));
    fs.writeFileSync(path.join(out, "scenario_weekly.csv"), toCsv(aggregateFleetWeeks(dailyRows), FLEET_WEEKLY_COLUMNS));
    fs.writeFileSync(path.join(out, "car_usage_windows.csv"), toCsv(windowRows, CAR_WINDOW_COLUMNS));
  };
  checkpoint();
  try {
    for (const date of args.dates) for (const ride of args.rideLimits) {
      let matrix: ExperimentMatrix | null = null;
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
          occurrenceLabels: {}, matrix: null, menu: [], scenarios: [],
        };
      }
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
      const rows = fleetDailyRows(day, args.scenarios, ride, args.tourLimit, fixedType, minimiseType);
      dailyRows.push(...rows);
      windowRows.push(...carWindowRows(day, ride));
      manifest.runs.push(manifestRun(
        day, ride, responseFiles, captured ? `${stem}.matrix.json` : null, captured?.provenance ?? null, rateLimitWaits, httpFailures,
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
  } catch {
    manifest.state = "failed";
    manifest.completed_at = new Date().toISOString();
    try { checkpoint(); } catch { /* keep the previous checkpoint */ }
    throw new Error("Fleet experiment export failed; completed results are preserved. Check local services and input provenance.");
  }
}

void main().catch((error) => {
  // Never print raw SDK, HTTP, Python or filesystem diagnostics that can contain secrets.
  const safe = error instanceof Error && SAFE_MESSAGES.includes(error.message)
    ? error.message : "Fleet experiment runner failed. Check local configuration; diagnostics are intentionally redacted.";
  console.error(safe);
  process.exitCode = 1;
});
