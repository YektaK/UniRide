import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import dotenv from "dotenv";
import { resolveSharedKey, buildChildEnv, resolvePythonBin } from "./start-dudullu-local.mjs";
import {
  parseExperimentArgs, captureMatrixSnapshot, summarizePlan, anonymizeResponse,
  aggregateWeeks, summariesMatch, toCsv, SUMMARY_COLUMNS,
  type ExperimentMatrix, type ExperimentSummary,
} from "../src/services/plan-experiments";

const usage = "npm run experiments:plan -- --week-of YYYY-MM-DD [--ride-limits 50,60,70,90] [--tour-limit 150] [--fleet virtual|live] [--repeat 2] [--out .temp/experiments/run]\nUse --dates YYYY-MM-DD,YYYY-MM-DD instead of --week-of for explicit dates. Optimizer must already be running with the same internal key.";

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length === 1 && argv[0] === "--help") { console.log(usage); return; }
  const startedAt = new Date();
  let args;
  try { args = parseExperimentArgs(argv, startedAt); }
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
  const [{ runDailyPlan }, { getSupabaseAdmin }, { optimizerFetch }] = await Promise.all([
    import("../src/services/daily-plan-run"), import("../src/lib/supabase-admin"), import("../src/lib/optimizer-server"),
  ]);
  const python = resolvePythonBin(process.env, root);
  if (!python) throw new Error("Python runtime required for GA configuration provenance; set UNIRIDE_PYTHON.");
  let ga: { defaults: Record<string, unknown>; config: Record<string, unknown>; seed: number };
  try {
    const text = execFileSync(python, ["-c", "import sys,json; sys.path.insert(0,'optimizer_api'); from strategies.ga_split_strategy import GASplitStrategy; s=GASplitStrategy(); print(json.dumps({'defaults':s.DEFAULT_CONFIG,'config':s.config,'seed':s.seed}))"], {
      cwd: root, env: process.env, windowsHide: true, timeout: 60_000, stdio: ["ignore", "pipe", "pipe"],
    }).toString();
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed.defaults !== "object" || typeof parsed.config !== "object" || !Number.isInteger(parsed.seed)) throw new Error();
    ga = parsed;
  } catch { throw new Error("Could not capture local GA configuration; check the Python runtime locally."); }
  const commit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
  const dirty = execFileSync("git", ["status", "--porcelain"], { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }).toString().trim().length > 0;
  const out = path.resolve(root, args.out);
  // Refuse overwriting an existing campaign, including its provenance and repeat results.
  if (fs.existsSync(out)) throw new Error("Output directory already exists; choose a fresh --out directory.");
  fs.mkdirSync(out, { recursive: true });
  const reader = getSupabaseAdmin();
  const summaries: ExperimentSummary[] = [];
  const runs: Array<Record<string, unknown>> = [];
  const divergences: Array<Record<string, unknown>> = [];
  const primary = new Map<string, { summary: ExperimentSummary; hash: string | null }>();
  const writeJson = (file: string, value: unknown) => fs.writeFileSync(path.join(out, file), JSON.stringify(value, null, 2) + "\n");
  const manifest = {
    git_commit: commit, dirty_working_tree: dirty, timestamp: startedAt.toISOString(),
    parameters: { dates: args.dates, ride_limits: args.rideLimits, tour_limit: args.tourLimit, fleet: args.fleet, admission_mode: "assume_confirmed", repeat: args.repeat },
    algorithm: "ga_split", termination_protocol: "native", ga_defaults: ga.defaults,
    ga_effective_configuration: ga.config, effective_seed: ga.seed,
    ga_configuration_source: "local production constructor; optimizer must use the same checkout and environment",
    vehicle_count_scope: "conditional on the solver's fixed routes; not global route optimality",
    metric_precision: "additional mean/vehicle minutes rounded to 6 decimals; max ride/counts use daily-plan view",
    runs, divergences, state: "running", completed_at: null as string | null,
  };
  const checkpoint = () => {
    writeJson("run_manifest.json", manifest);
    fs.writeFileSync(path.join(out, "summary.csv"), toCsv(summaries, SUMMARY_COLUMNS));
    const weekly = aggregateWeeks(summaries);
    const weeklyColumns = ["week_of", "ride_limit", "tour_limit", "weekly_fleet_need", "max_observed_vehicles", "vehicle_count_proven", "complete_week", "monday_vehicles", "tuesday_vehicles", "wednesday_vehicles", "thursday_vehicles", "friday_vehicles", "total_vehicle_minutes", "observed_vehicle_minutes", "per_day"];
    fs.writeFileSync(path.join(out, "weekly.csv"), toCsv(weekly, weeklyColumns));
  };
  checkpoint();
  try {
    for (const date of args.dates) for (const ride of args.rideLimits) for (let repeat = 1; repeat <= args.repeat; repeat++) {
      let matrix: ExperimentMatrix | null = null;
      const fetchWithSnapshot = async (requestPath: string, init?: RequestInit) => {
        const response = await optimizerFetch(requestPath, init);
        if (requestPath === "/api/v1/internal/matrix-snapshot" && response.ok) {
          try { matrix = captureMatrixSnapshot(await response.clone().json()); }
          catch { matrix = null; }
        }
        return response;
      };
      let response: unknown;
      try {
        response = await runDailyPlan({ reader, optimizerFetch: fetchWithSnapshot, clock: () => new Date() }, {
          serviceDate: date, admissionMode: "assume_confirmed", fleetMode: args.fleet,
          maxRideTimeMinutes: ride, maxTourMinutes: args.tourLimit,
        });
      } catch { response = { error: "PREVIEW_UNAVAILABLE" }; }
      const summary = summarizePlan(response, matrix, date, ride, args.tourLimit, repeat);
      const stem = `${date}_R${ride}_repeat${repeat}`;
      const responseFile = `${stem}.response.json`;
      writeJson(responseFile, anonymizeResponse(response));
      // Snapshot provenance is captured before the route schema drops it. No inference from a subset of arcs.
      const captured = matrix as ExperimentMatrix | null;
      if (captured) writeJson(`${stem}.matrix.json`, captured);
      summaries.push(summary);
      runs.push({ date, ride_limit: ride, repeat_index: repeat, response_file: responseFile,
        matrix_file: captured ? `${stem}.matrix.json` : null, matrix_provenance: captured?.provenance ?? null,
        virtual_template: typeof response === "object" && response !== null && "fleet" in response
          ? (response.fleet as { template?: unknown }).template ?? null : null,
      });
      const key = `${date}:${ride}`;
      const hash = captured?.sha256 ?? null;
      if (repeat === 1) primary.set(key, { summary, hash });
      else {
        const first = primary.get(key)!;
        if (!summariesMatch(first.summary, summary) || first.hash !== hash) divergences.push({ date, ride_limit: ride, repeat_index: repeat, summaries_match: summariesMatch(first.summary, summary), matrix_hash_match: first.hash === hash });
      }
      checkpoint();
      console.log(`${date} R${ride} repeat ${repeat}: ${summary.status}; students=${summary.students ?? "unknown"}, vehicles=${summary.vehicles_required ?? "unknown"}, routes=${summary.routes ?? "unknown"}, waves=${summary.waves ?? "unknown"}, max_ride=${summary.max_ride_min ?? "unknown"}`);
    }
    manifest.state = divergences.length ? "divergent" : "completed";
    manifest.completed_at = new Date().toISOString();
    checkpoint();
    if (divergences.length) { console.error("Repeat summaries or matrix hashes diverged; see run_manifest.json."); process.exitCode = 2; }
    else console.log(`Completed ${summaries.length} runs. Results: ${args.out}`);
  } catch {
    manifest.state = "failed";
    manifest.completed_at = new Date().toISOString();
    checkpoint();
    throw new Error("Experiment export failed; completed results are preserved. Check local services and input provenance.");
  }
}

void main().catch(error => {
  // Never print raw SDK, HTTP, Python or filesystem diagnostics that can contain secrets.
  const safe = error instanceof Error && [usage,
    "Configure the same internal key in the CLI and running optimizer; an unshared generated key cannot authenticate.",
    "Python runtime required for GA configuration provenance; set UNIRIDE_PYTHON.",
    "Could not capture local GA configuration; check the Python runtime locally.",
    "Output directory already exists; choose a fresh --out directory.",
    "Experiment export failed; completed results are preserved. Check local services and input provenance.",
  ].includes(error.message) ? error.message : "Experiment runner failed. Check local configuration; diagnostics are intentionally redacted.";
  console.error(safe);
  process.exitCode = 1;
});
