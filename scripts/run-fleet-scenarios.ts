import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import dotenv from "dotenv";
import { resolveSharedKey, buildChildEnv, resolvePythonBin } from "./start-dudullu-local.mjs";
import { parseFleetArgs } from "../src/services/fleet-scenario-args";
import { loadFleetReference } from "../src/services/fleet-rerun-reference";
import type { RerunSolverCapture } from "../src/services/fleet-rerun-run";

const usage = "npm run experiments:fleet -- --week-of YYYY-MM-DD [--ride-limits 50,60,70,90] [--tour-limit 150] --fleet-types large:4sw5so:cd10,sedan:0sw4so:cd10 [--fixed-type large] [--minimize-type sedan] [--scenarios A,1,2,3] [--max-cars N] [--node-budget 200000] [--selection-time-limit 30] --pin-commit <hex commit> --reference-manifest <old run_manifest.json> [--reference-waves <4sw5so archive dir>] [--preflight-only] [--allow-subset-dates] [--out <new results directory>]\n" +
  "Type grammar: <id>:<n>sw<m>so[:cd<min>][:r<R>][:t<T>]. Scenario A = minimum all-large; an integer is the fixed number of large vehicles L (0..4).\n" +
  "Use --dates YYYY-MM-DD,YYYY-MM-DD instead of --week-of for explicit dates. Fleet types come only from the command line; the vehicles table is never read. Optimizer must already be running with the same internal key.\n" +
  "WP-E10: the run first compares the live inputs with the old campaign (read-only preflight) and refuses on any difference; --preflight-only stops after that check and writes nothing; --allow-subset-dates lets --dates be an ordered subset of the old campaign dates (rule (e): one day run again).";
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
  const [{ runFleetRerun, RerunAbort }, { getSupabaseAdmin }, { optimizerFetch }] = await Promise.all([
    import("../src/services/fleet-rerun-run"), import("../src/lib/supabase-admin"), import("../src/lib/optimizer-server"),
  ]);
  const python = resolvePythonBin(process.env, root);
  if (!python) throw new Error("Python runtime required for solver configuration provenance; set UNIRIDE_PYTHON.");
  const captureSolver = (): RerunSolverCapture => {
    try {
      const text = execFileSync(python, [path.join(root, "scripts", "capture_fleet_solver_config.py")], {
        cwd: root, env: process.env, windowsHide: true, timeout: 60_000, stdio: ["ignore", "pipe", "pipe"],
      }).toString();
      const parsed = JSON.parse(text.trim().split(/\r?\n/).at(-1)!);
      if (!parsed?.ga || !Number.isInteger(parsed.ga.seed) || !Number.isInteger(parsed.hf?.seed)) throw new Error();
      return parsed;
    } catch { throw new Error("Could not capture local solver configuration; check the Python runtime locally."); }
  };
  const git = (...gitArgs: string[]) => execFileSync("git", gitArgs, { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }).toString();
  let result;
  try {
    result = await runFleetRerun({
    root, reader: getSupabaseAdmin(), optimizerFetch, git: (gitArgs) => git(...gitArgs), captureSolver,
    loadReference: () => loadFleetReference({
      manifestPath: path.resolve(root, args.referenceManifest!), wavesDir: path.resolve(root, args.referenceWaves ?? DEFAULT_REFERENCE_WAVES), root,
    }),
    fs: {
      exists: (file) => fs.existsSync(file), mkdir: (dir) => { fs.mkdirSync(dir, { recursive: true }); },
      write: (file, text) => fs.writeFileSync(file, text),
    },
    log: (line) => console.log(line),
    }, args);
  } catch (error) {
    // An abort of the run itself carries a message built by the run (no secret, no student data).
    if (error instanceof RerunAbort) { console.error(error.message); process.exitCode = 1; return; }
    throw error;
  }
  if (result.message) console.error(result.message);
  process.exitCode = result.exitCode;
}

void main().catch((error) => {
  // Never print raw SDK, HTTP, Python or filesystem diagnostics that can contain secrets.
  const safe = error instanceof Error && SAFE_MESSAGES.includes(error.message)
    ? (error as Error).message : "Fleet experiment runner failed. Check local configuration; diagnostics are intentionally redacted.";
  console.error(safe);
  process.exitCode ||= 1;
});
