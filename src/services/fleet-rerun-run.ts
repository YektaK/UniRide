import "server-only";
import path from "node:path";
import { anonymizeResponse, captureMatrixSnapshot, fetchWithRateLimitRetry, toCsv, type ExperimentMatrix } from "@/services/plan-experiments";
import type { FleetArgs } from "@/services/fleet-scenario-args";
import {
  FLEET_DAILY_COLUMNS, FLEET_WEEKLY_COLUMNS, CAR_WINDOW_COLUMNS, aggregateFleetWeeks, carWindowRows, fleetDailyRows,
  manifestRun, scenarioName, type FleetDailyRow, type FleetManifest,
} from "@/services/fleet-scenario-report";
import { runFleetScenarioDay, scenarioResponse, type FleetScenarioDay } from "@/services/fleet-scenario-run";
import {
  FLEET_ARCHIVE_FORMAT, extendedFleetManifestSchema, menuArchive, menuArchiveName, menuArchiveSchema,
  selectionArchive, selectionArchiveName, selectionArchiveSchema,
} from "@/services/fleet-scenario-archive";
import { PINNED, compareWaves, formatPreflightReport, type PreflightPins, type PreflightReference, type SolverCapture } from "@/services/fleet-rerun-preflight";
import { anonymiseWaves, readOnlyReader, runFleetRerunPreflight } from "@/services/fleet-rerun-preflight-live";
import type { DailyPlanReader } from "@/services/daily-plan-run";

// Body of scripts/run-fleet-scenarios.ts after the environment is loaded: preflight, gates, the campaign loop and the
// archive. Every effect (git, files, DB reader, optimizer transport, solver capture) is injected so the gates can be
// tested without a database, an optimizer or a disk.

/** An abort whose message is built here and holds no secret or student data, so it may be printed. */
export class RerunAbort extends Error {}

export interface RerunFs {
  exists(file: string): boolean;
  mkdir(dir: string): void;
  write(file: string, text: string): void;
}
export interface RerunSolverCapture extends SolverCapture {
  ga: SolverCapture["ga"] & { defaults: Record<string, unknown> };
  /** Compute-policy values of the CLI environment (rate limit included); the session wrapper gives the optimizer the same. */
  compute_policy?: Record<string, unknown>;
  /** Repo-relative location of the project packages as the interpreter resolved them; the capture refuses any outside the repository. */
  python_provenance?: Record<string, string>;
}
export interface RerunDeps {
  root: string;
  reader: DailyPlanReader;
  optimizerFetch: (path: string, init?: RequestInit) => Promise<Response>;
  /** Runs `git <args>` in the repository and returns stdout. */
  git: (args: string[]) => string;
  captureSolver: () => RerunSolverCapture;
  loadReference: () => PreflightReference;
  /** Output-directory guard (the CLI injects the historical-archive refusal; this module names no result folder). Throws to refuse. */
  assertOutputAllowed: (out: string, root: string) => void;
  fs: RerunFs;
  log: (line: string) => void;
  now?: () => Date;
  pins?: PreflightPins;
}
export interface RerunResult { exitCode: number; manifest: FleetManifest | null; message: string | null }

/** Any line of `git status --porcelain` (tracked change or untracked file) makes the tree dirty. */
export const dirtyFromPorcelain = (porcelain: string): boolean => porcelain.trim().length > 0;
export function readGitState(exec: (args: string[]) => string): { head: string; dirty: boolean } {
  return {
    head: exec(["rev-parse", "HEAD"]).trim(),
    dirty: dirtyFromPorcelain(exec(["status", "--porcelain", "--untracked-files=all"])),
  };
}

const stable = (value: unknown): string => JSON.stringify(value, (_key, item) =>
  item && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item as Record<string, unknown>).sort(([a], [b]) => (a < b ? -1 : 1))) : item);

/** Parses the last line of the capture script's output; a capture without python_provenance (or without the seeds) fails at the start of the run, not at its end. */
export function parseSolverCapture(text: string): RerunSolverCapture {
  try {
    const parsed = JSON.parse(text.trim().split(/\r?\n/).at(-1)!);
    if (!parsed?.ga || !Number.isInteger(parsed.ga.seed) || !Number.isInteger(parsed.hf?.seed) || !parsed.python_provenance) throw new Error();
    return parsed;
  } catch { throw new Error("Could not capture local solver configuration; check the Python runtime locally."); }
}

export async function runFleetRerun(deps: RerunDeps, args: FleetArgs): Promise<RerunResult> {
  const { fs, log } = deps;
  const pins = deps.pins ?? PINNED;
  const now = deps.now ?? (() => new Date());
  const startedAt = now();
  if (args.pinCommit === null || args.referenceManifest === null) {
    throw new Error("--pin-commit and --reference-manifest are required: the run is refused without the input preflight.");
  }
  const solver = deps.captureSolver();
  let reference: PreflightReference;
  try { reference = deps.loadReference(); }
  catch { throw new Error("Could not read the reference campaign; check --reference-manifest and --reference-waves."); }
  const guardedReader = readOnlyReader(deps.reader);

  // ---- WP-E10 input preflight: read-only, before any solve and any write; refuses on any difference -------------------
  const preflight = await runFleetRerunPreflight({
    reader: guardedReader, optimizerFetch: deps.optimizerFetch, git: () => readGitState(deps.git), captureSolver: () => solver,
  }, {
    pinCommit: args.pinCommit,
    cli: {
      dates: args.dates, rideLimits: args.rideLimits, tourLimit: args.tourLimit, scenarios: args.scenarios.map(scenarioName),
      maxCars: args.maxCars, nodeBudget: args.nodeBudget, selectionTimeLimitSeconds: args.selectionTimeLimitSeconds,
      admissionMode: "assume_confirmed", fleetTypes: args.fleetTypes, fixedType: args.fixedTypeId, minimizeType: args.minimizeTypeId,
      allowSubsetDates: args.allowSubsetDates,
    },
  }, reference, pins);
  log(formatPreflightReport(preflight.report));
  if (!preflight.report.ok) {
    return { exitCode: 2, manifest: null, message: "Preflight refused: the live inputs or settings differ from the old campaign. Nothing was solved or written." };
  }
  if (args.preflightOnly) {
    log("Preflight only: nothing was solved or written.");
    return { exitCode: 0, manifest: null, message: null };
  }

  const git = readGitState(deps.git);
  const out = path.resolve(deps.root, args.out);
  deps.assertOutputAllowed(out, deps.root);
  // Refuse overwriting an existing campaign, including its provenance and results.
  if (fs.exists(out)) throw new Error("Output directory already exists; choose a fresh --out directory.");
  fs.mkdir(out);

  const fixedType = args.fleetTypes.find((type) => type.typeId === args.fixedTypeId)!;
  const minimiseType = args.fleetTypes.find((type) => type.typeId === args.minimizeTypeId) ?? null;
  const dailyRows: FleetDailyRow[] = [];
  const windowRows: ReturnType<typeof carWindowRows> = [];
  const writeJson = (file: string, value: unknown) => fs.write(path.join(out, file), JSON.stringify(value, null, 2) + "\n");
  const manifest: FleetManifest = {
    git_commit: git.head, dirty_working_tree: git.dirty, timestamp: startedAt.toISOString(),
    parameters: {
      dates: args.dates, ride_limits: args.rideLimits, tour_limit: args.tourLimit,
      scenarios: args.scenarios.map(scenarioName), max_cars: args.maxCars, node_budget: args.nodeBudget,
      selection_time_limit_seconds: args.selectionTimeLimitSeconds, admission_mode: "assume_confirmed",
      ...(args.allowSubsetDates ? { allow_subset_dates: true } : {}),
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
    archive_format: FLEET_ARCHIVE_FORMAT, run_kind: args.allowSubsetDates ? "rule_e_second_run" : "campaign", pinned_commit: args.pinCommit, preflight: preflight.record,
    ...(solver.compute_policy ? { compute_policy: solver.compute_policy } : {}),
    ...(solver.python_provenance ? { python_provenance: solver.python_provenance } : {}),
  };
  const checkpoint = () => {
    extendedFleetManifestSchema.parse(manifest);
    writeJson("run_manifest.json", manifest);
    fs.write(path.join(out, "scenario_daily.csv"), toCsv(dailyRows, FLEET_DAILY_COLUMNS));
    fs.write(path.join(out, "scenario_weekly.csv"), toCsv(aggregateFleetWeeks(dailyRows), FLEET_WEEKLY_COLUMNS));
    fs.write(path.join(out, "car_usage_windows.csv"), toCsv(windowRows, CAR_WINDOW_COLUMNS));
  };
  if (args.allowSubsetDates) {
    fs.write(path.join(out, "README.md"), `Rule (e) second run of ${args.dates.join(", ")} (determinism check of the fleet re-run); not a campaign archive, compare it with scripts/verify_fleet_rerun.py --double-run-dir.\n`);
  }
  checkpoint();

  // What the running optimizer reports as its applied policy; every /optimize answer must agree.
  const policy: { first: { profile_id: string; limits: Record<string, unknown> } | null; key: string; checked: number; identical: boolean } =
    { first: null, key: "", checked: 0, identical: true };
  const refreshPolicy = () => {
    if (policy.first) manifest.optimizer_policy = { ...policy.first, responses_checked: policy.checked, limits_identical: policy.identical };
  };

  try {
    for (const date of args.dates) for (const ride of args.rideLimits) {
      let matrix: ExperimentMatrix | null = null;
      let matrixDrift = false;
      let optimizerFailure: { path: string; status: number } | null = null;
      const rateLimitWaits: Array<{ path: string; status: number; wait_seconds: number; attempt: number }> = [];
      const httpFailures: Array<{ path: string; status: number }> = [];
      const fetchWithSnapshot = async (requestPath: string, init?: RequestInit) => {
        // N-d: after the first non-OK answer (its retries are exhausted) nothing more is sent; the cell is abandoned below.
        if (optimizerFailure) return new Response("{}", { status: 503 });
        // 429 handling identical to experiments:plan: up to two waits of at most 60 s each.
        const response = await fetchWithRateLimitRetry(deps.optimizerFetch, requestPath, init, {
          onRetry: (seconds, attempt) => {
            rateLimitWaits.push({ path: requestPath, status: 429, wait_seconds: seconds, attempt });
            log(`Optimizer rate limit: waiting ${seconds}s before retry ${attempt}.`);
          },
        });
        if (!response.ok) { httpFailures.push({ path: requestPath, status: response.status }); optimizerFailure ??= { path: requestPath, status: response.status }; }
        if (requestPath === "/api/v1/internal/matrix-snapshot" && response.ok) {
          let declared: unknown = null;
          try { const body = await response.clone().json(); declared = (body as { sha256?: unknown } | null)?.sha256; matrix = captureMatrixSnapshot(body); }
          catch { matrix = null; }
          // (a) every captured matrix must declare the archived sha256, also one the capture could not parse: a changed
          // snapshot stops the cell before any solve.
          if (declared !== pins.matrixSha256) { matrixDrift = true; matrix = null; return new Response("{}", { status: 503 }); }
        }
        if (requestPath.endsWith("/v1/optimize") && response.ok) {
          try {
            const applied = ((await response.clone().json()) as { applied_policy?: { profile_id?: string; limits?: Record<string, unknown> } }).applied_policy;
            if (applied && typeof applied.profile_id === "string") {
              const key = stable({ profile_id: applied.profile_id, limits: applied.limits ?? {} });
              policy.checked += 1;
              if (policy.first === null) { policy.first = { profile_id: applied.profile_id, limits: applied.limits ?? {} }; policy.key = key; }
              else if (key !== policy.key) policy.identical = false;
            }
          } catch { /* an unreadable answer is already reported by the run itself */ }
        }
        return response;
      };
      let day: FleetScenarioDay;
      try {
        day = await runFleetScenarioDay({ reader: guardedReader, optimizerFetch: fetchWithSnapshot, clock: () => new Date() }, {
          serviceDate: date, maxRideTimeMinutes: ride, maxTourMinutes: args.tourLimit,
          fixedType, minimiseType, scenarios: args.scenarios, maxCars: args.maxCars,
          nodeBudget: args.nodeBudget, selectionTimeLimitSeconds: args.selectionTimeLimitSeconds,
        });
      } catch {
        day = {
          serviceDate: date, status: "blocked_data", reasonCodes: ["SCENARIO_RUN_UNAVAILABLE"], dbVehiclesConsulted: false,
          limits: { maxRideTimeMinutes: ride, maxTourMinutes: args.tourLimit }, students: 0, legs: 0, waves: 0,
          occurrenceLabels: {}, matrix: null, menu: [], menuDetail: [], waveDemand: {}, scenarios: [],
        };
      }
      if (optimizerFailure && !matrixDrift) throw new RerunAbort(`Non-OK optimizer answer (HTTP ${(optimizerFailure as { status: number }).status}) for ${date} R${ride} after its retries; the run is stopped and the cell was not written.`);
      if (matrixDrift) throw new RerunAbort("Matrix snapshot sha256 changed during the run; stopped before any solve of this cell.");
      // (a) the wave composition must equal the archive at every capture, not only in the preflight.
      if (day.status !== "blocked_data") {
        const composition = anonymiseWaves(day.occurrenceLabels, day.waveDemand);
        const problems = compareWaves(reference.waves[date] ?? {}, reference.waveClasses[date] ?? {}, composition.waves, composition.classes);
        if (problems.length > 0) {
          throw new RerunAbort(`Live wave composition (occurrence ids or Sw/So counts) differs from the archive for ${date} R${ride} (${problems.length} waves); the cell was not written.`);
        }
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
      // WP-E10 extended archive (f): every menu option, and the selection exchange of every L. Validated before it is written;
      // a schema failure aborts the whole campaign (fail closed), the failed manifest is kept.
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
      refreshPolicy();
      checkpoint();
      for (const row of rows) {
        log(`${date} R${ride} ${row.scenario}: ${row.status}; cars=${row.cars ?? "n/a"}, large=${row.large_vehicles ?? "n/a"}, routes=${row.routes ?? "unknown"}, total_min=${row.total_vehicle_minutes ?? "unknown"}`);
      }
    }
    manifest.state = "completed";
    manifest.completed_at = now().toISOString();
    refreshPolicy();
    checkpoint();
    log(`Completed ${dailyRows.length} scenario rows. Results: ${args.out}`);
    return { exitCode: 0, manifest, message: null };
  } catch (error) {
    manifest.state = "failed";
    manifest.completed_at = now().toISOString();
    try { checkpoint(); } catch { /* keep the previous checkpoint */ }
    if (error instanceof RerunAbort) throw error;
    throw new Error("Fleet experiment export failed; completed results are preserved. Check local services and input provenance.");
  }
}
