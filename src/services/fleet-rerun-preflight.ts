import type { FleetTypeSpec } from "./fleet-scenario-args";

// Input preflight of the WP-E10 fleet re-run (docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 9, "WP-E10 input rule
// and acceptance", (a)-(c)). Pure: it compares what the run would use with the historical campaign and refuses on any
// difference. The owner decides what happens next; there is no replay from archived inputs.

/** Values fixed by the design for the re-run (rules (a)-(c)). The reference manifest must agree with them. */
export interface PreflightPins {
  matrixSha256: string;
  waveCount: number;
  legCount: number;
  admissionMode: string;
  effectiveSeed: number;
  selectionTimeLimitSeconds: number;
  nodeBudget: number;
  selectionSolver: { version: string; randomSeed: number; numWorkers: number };
  gaConfiguration: Record<string, unknown>;
}
const GA_CONFIGURATION = {
  population_size: 50, max_iterations: 100, crossover_rate: 0.85, mutation_rate: 0.2, elite_count: 3, tournament_size: 4,
  max_no_improvement: 25, seed: null, local_search_type: "hybrid", local_search_interval: 10, diversify_threshold: 30,
};
export const PINNED: PreflightPins = {
  matrixSha256: "bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5",
  waveCount: 57, legCount: 226, admissionMode: "assume_confirmed", effectiveSeed: 42, selectionTimeLimitSeconds: 30, nodeBudget: 200000,
  selectionSolver: { version: "9.15.6755", randomSeed: 20261008, numWorkers: 1 },
  gaConfiguration: GA_CONFIGURATION,
};

/** What the historical campaign (old run manifest plus the wave composition of the 4sw5so archive) says. */
export interface PreflightReference {
  manifestPath: string;
  gitCommit: string;
  wavesArchive: string;
  parameters: {
    dates: string[]; ride_limits: number[]; tour_limit: number; scenarios: string[]; max_cars: number | null;
    node_budget: number; selection_time_limit_seconds: number; admission_mode: string;
  };
  fleet_types: FleetTypeSpec[];
  fixed_type: string;
  minimize_type: string | null;
  ga_effective_configuration: Record<string, unknown>;
  hf_effective_configuration: Record<string, unknown>;
  effective_seed: number;
  hf_effective_seed: number;
  selection_solver: { version: string | null; random_seed: number | null; num_workers: number | null };
  /** Every sha256 the old matrix files and manifest runs declare (one value expected). */
  matrixSha256s: string[];
  /** date -> wave id -> sorted anonymised occurrence ids. */
  waves: Record<string, Record<string, string[]>>;
  /** date -> wave id -> Sw and So passenger counts of the wave (sum over the routes of the 4sw5so archive). */
  waveClasses: Record<string, Record<string, WaveClasses>>;
}
export interface WaveClasses { sw: number; so: number }

export interface SolverCapture {
  ga: { config: Record<string, unknown>; seed: number };
  hf: { config: Record<string, unknown>; seed: number };
  cp: { version: string | null; seed: number | null; workers: number | null };
}
export interface LiveDay {
  date: string;
  status: string;
  matrix: { sha256: string; source: string; id: string; version: string } | null;
  /** wave id -> sorted occurrence ids in the anonymised form of the archives (never raw student ids). */
  waves: Record<string, string[]>;
  /** wave id -> Sw and So counts of the live demand. */
  classes: Record<string, WaveClasses>;
}
export interface PreflightObservation {
  git: { head: string; dirty: boolean };
  pinCommit: string;
  cli: {
    dates: string[]; rideLimits: number[]; tourLimit: number; scenarios: string[]; maxCars: number | null;
    nodeBudget: number; selectionTimeLimitSeconds: number; admissionMode: string;
    fleetTypes: FleetTypeSpec[]; fixedType: string; minimizeType: string | null;
    /** Rule (e): the dates may be a non-empty, ordered subset of the reference dates (one full day run twice). */
    allowSubsetDates?: boolean;
  };
  solver: SolverCapture;
  days: LiveDay[];
}

/**
 * Exact limit of the occurrence comparison (design rule (a)). The archives hold only anonymised ids, so the comparison
 * is made on that alias, not on student identity. Rule (d), the base routes equal to the 4sw5so routes, is the backstop.
 */
export const OCCURRENCE_CHECK_LIMIT =
  "The alias is <location_code>~<rank of the raw id among that day's occurrences at that location> (plan-experiments anonymizeResponse). " +
  "The check detects added or removed students, a change of location, direction or anchor, a rank shift, and a change of the Sw/So count of a wave. " +
  "It cannot detect a different student at the same location and rank; rule (d) (base routes equal to the 4sw5so routes) is the backstop.";

/** Differences between the archived and the live composition of one date (wave ids, ids, Sw/So counts). */
export function compareWaves(
  archived: Record<string, string[]>, archivedClasses: Record<string, WaveClasses>,
  live: Record<string, string[]>, liveClasses: Record<string, WaveClasses>,
): string[] {
  const problems: string[] = [];
  for (const waveId of new Set([...Object.keys(archived), ...Object.keys(live)])) {
    if (!same(archived[waveId], live[waveId])) problems.push(`${waveId}: occurrence ids differ (archive ${archived[waveId]?.length ?? "absent"}, live ${live[waveId]?.length ?? "absent"})`);
    else if (!same(archivedClasses[waveId], liveClasses[waveId])) problems.push(`${waveId}: Sw/So counts differ (archive ${stable(archivedClasses[waveId])}, live ${stable(liveClasses[waveId])})`);
  }
  return problems;
}

export interface PreflightCheck { id: string; ok: boolean; message: string }
export interface PreflightReport { ok: boolean; checks: PreflightCheck[] }

export class PreflightRefusal extends Error {
  constructor(readonly report: PreflightReport) {
    super(`Preflight refused: ${report.checks.filter((check) => !check.ok).map((check) => `${check.id} (${check.message})`).join("; ")}`);
    this.name = "PreflightRefusal";
  }
}

const stable = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>).filter(([, item]) => item !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([key, item]) => `${JSON.stringify(key)}:${stable(item)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
};
const same = (a: unknown, b: unknown) => stable(a) === stable(b);
const normalizeType = (type: FleetTypeSpec) => ({
  typeId: type.typeId, swCapacity: type.swCapacity, soCapacity: type.soCapacity, cooldownMinutes: type.cooldownMinutes,
  totalCapacity: type.totalCapacity, rideLimit: type.rideLimit, tourLimit: type.tourLimit,
});
const countWaves = (waves: Record<string, Record<string, string[]>>) => Object.values(waves).reduce((n, day) => n + Object.keys(day).length, 0);
const countLegs = (waves: Record<string, Record<string, string[]>>) =>
  Object.values(waves).reduce((n, day) => n + Object.values(day).reduce((m, ids) => m + ids.length, 0), 0);

/** Compares the live inputs and the run settings with the reference. Never throws; `ok` is false on any difference. */
export function evaluatePreflight(
  reference: PreflightReference, observed: PreflightObservation, pins: PreflightPins = PINNED,
): PreflightReport {
  const checks: PreflightCheck[] = [];
  const check = (id: string, ok: boolean, message: string) => checks.push({ id, ok, message });
  const { cli, solver } = observed;

  check("clean_tree", !observed.git.dirty, observed.git.dirty ? "the working tree has uncommitted or untracked changes" : "clean working tree");
  const pinned = /^[0-9a-f]{7,40}$/.test(observed.pinCommit) && /^[0-9a-f]{40}$/.test(observed.git.head) && observed.git.head.startsWith(observed.pinCommit);
  check("pinned_commit", pinned, pinned ? `HEAD ${observed.git.head.slice(0, 12)} is the pinned commit` : `HEAD ${observed.git.head.slice(0, 12)} is not the pinned commit ${observed.pinCommit}`);

  const typesOk = same(cli.fleetTypes.map(normalizeType), reference.fleet_types.map(normalizeType));
  check("fleet_types", typesOk, typesOk ? "CLI fleet types equal the reference manifest" : "CLI fleet types differ from the reference manifest");
  const datesOk = cli.allowSubsetDates
    ? cli.dates.length > 0 && cli.dates.every((date, k) => reference.parameters.dates.includes(date) && (k === 0 || reference.parameters.dates.indexOf(date) > reference.parameters.dates.indexOf(cli.dates[k - 1]!)))
    : same(cli.dates, reference.parameters.dates);
  const gridOk = datesOk && same(
    [cli.rideLimits, cli.tourLimit, cli.scenarios, cli.maxCars, cli.fixedType, cli.minimizeType],
    [reference.parameters.ride_limits, reference.parameters.tour_limit, reference.parameters.scenarios,
      reference.parameters.max_cars, reference.fixed_type, reference.minimize_type],
  );
  check("grid", gridOk, gridOk
    ? (cli.allowSubsetDates ? "rule (e) second run: the dates are an ordered subset of the reference dates; ride limits, tour limit, scenarios, cap and type roles equal the reference"
      : "dates, ride limits, tour limit, scenarios, cap and type roles equal the reference")
    : (cli.allowSubsetDates ? "the dates are not an ordered subset of the reference dates, or ride limits, tour limit, scenarios, cap or type roles differ from the reference"
      : "dates, ride limits, tour limit, scenarios, cap or type roles differ from the reference"));
  const admissionOk = cli.admissionMode === reference.parameters.admission_mode && cli.admissionMode === pins.admissionMode;
  check("admission_mode", admissionOk, admissionOk ? `admission_mode ${cli.admissionMode}` : `admission_mode ${cli.admissionMode} (expected ${pins.admissionMode})`);
  const nodeOk = cli.nodeBudget === reference.parameters.node_budget && cli.nodeBudget === pins.nodeBudget;
  check("node_budget", nodeOk, `node_budget ${cli.nodeBudget} (expected ${pins.nodeBudget})`);
  const limitOk = cli.selectionTimeLimitSeconds === reference.parameters.selection_time_limit_seconds && cli.selectionTimeLimitSeconds === pins.selectionTimeLimitSeconds;
  check("selection_time_limit", limitOk, `selection_time_limit_seconds ${cli.selectionTimeLimitSeconds} (expected ${pins.selectionTimeLimitSeconds})`);

  const gaOk = same(solver.ga.config, reference.ga_effective_configuration) && same(solver.ga.config, pins.gaConfiguration);
  check("ga_configuration", gaOk, gaOk ? "GA effective configuration equals the reference" : "GA effective configuration differs from the reference");
  const hfOk = same(solver.hf.config, reference.hf_effective_configuration) && same(solver.hf.config, pins.gaConfiguration);
  check("hf_configuration", hfOk, hfOk ? "HF effective configuration equals the reference" : "HF effective configuration differs from the reference");
  const seedsOk = solver.ga.seed === reference.effective_seed && solver.hf.seed === reference.hf_effective_seed &&
    solver.ga.seed === pins.effectiveSeed && solver.hf.seed === pins.effectiveSeed;
  check("seeds", seedsOk, `effective seeds ga ${solver.ga.seed}, hf ${solver.hf.seed} (expected ${pins.effectiveSeed})`);
  const cpOk = solver.cp.version === reference.selection_solver.version && solver.cp.version === pins.selectionSolver.version &&
    solver.cp.seed === reference.selection_solver.random_seed && solver.cp.seed === pins.selectionSolver.randomSeed &&
    solver.cp.workers === reference.selection_solver.num_workers && solver.cp.workers === pins.selectionSolver.numWorkers;
  check("selection_solver", cpOk, `CP-SAT ${solver.cp.version}, random_seed ${solver.cp.seed}, num_workers ${solver.cp.workers} (expected ${pins.selectionSolver.version}, ${pins.selectionSolver.randomSeed}, ${pins.selectionSolver.numWorkers})`);

  // (a) the live matrix of every date declares the archived sha256, and the demand reproduces the archived waves.
  const shaProblems: string[] = [];
  const observedShas = new Set<string>();
  for (const day of observed.days) {
    if (day.matrix === null) { shaProblems.push(`${day.date}: no matrix snapshot`); continue; }
    observedShas.add(day.matrix.sha256);
    if (day.matrix.source !== "supabase") shaProblems.push(`${day.date}: source ${day.matrix.source}`);
    if (day.matrix.id !== `time_matrix:sha256:${day.matrix.sha256}` || day.matrix.version !== day.matrix.sha256) shaProblems.push(`${day.date}: id/version do not match the sha256`);
    if (day.matrix.sha256 !== pins.matrixSha256) shaProblems.push(`${day.date}: sha256 ${day.matrix.sha256.slice(0, 8)}... differs from ${pins.matrixSha256.slice(0, 8)}...`);
    if (!reference.matrixSha256s.includes(day.matrix.sha256)) shaProblems.push(`${day.date}: sha256 is not declared by the reference archive`);
  }
  if (observed.days.length === 0) shaProblems.push("no day was inspected");
  check("matrix_sha256", shaProblems.length === 0, shaProblems.length === 0 ? `all ${observed.days.length} live matrices declare ${pins.matrixSha256.slice(0, 8)}...` : shaProblems.join("; "));

  const waveProblems: string[] = [];
  const liveWaves: Record<string, Record<string, string[]>> = {};
  for (const day of observed.days) {
    liveWaves[day.date] = day.waves;
    const archived = reference.waves[day.date];
    if (day.status !== "ready") waveProblems.push(`${day.date}: day status ${day.status}`);
    if (!archived) { waveProblems.push(`${day.date}: not in the reference archive`); continue; }
    waveProblems.push(...compareWaves(archived, reference.waveClasses[day.date] ?? {}, day.waves, day.classes));
  }
  const liveDates = new Set(observed.days.map((day) => day.date));
  if (!cli.allowSubsetDates) for (const date of Object.keys(reference.waves)) if (!liveDates.has(date)) waveProblems.push(`${date}: not inspected`);
  const waves = countWaves(liveWaves), legs = countLegs(liveWaves);
  // A full run must reproduce the totals named by the design; an allowed subset must reproduce the reference totals of its own dates.
  const expectedWaves = cli.allowSubsetDates ? countWaves(Object.fromEntries([...liveDates].map((date) => [date, reference.waves[date] ?? {}]))) : pins.waveCount;
  const expectedLegs = cli.allowSubsetDates ? countLegs(Object.fromEntries([...liveDates].map((date) => [date, reference.waves[date] ?? {}]))) : pins.legCount;
  if (waves !== expectedWaves || legs !== expectedLegs) waveProblems.push(`live totals ${waves} waves / ${legs} legs (expected ${expectedWaves} / ${expectedLegs})`);
  check("occurrence_ids", waveProblems.length === 0, waveProblems.length === 0 ? `${waves} waves and ${legs} legs equal the archive` : waveProblems.slice(0, 12).join("; ") + (waveProblems.length > 12 ? `; ... ${waveProblems.length} problems` : ""));

  // The reference itself must be the campaign the design names.
  const refProblems: string[] = [];
  if (reference.matrixSha256s.length !== 1 || reference.matrixSha256s[0] !== pins.matrixSha256) refProblems.push("reference matrix sha256");
  if (countWaves(reference.waves) !== pins.waveCount || countLegs(reference.waves) !== pins.legCount) refProblems.push("reference wave/leg totals");
  if (reference.parameters.admission_mode !== pins.admissionMode) refProblems.push("reference admission mode");
  if (reference.parameters.node_budget !== pins.nodeBudget || reference.parameters.selection_time_limit_seconds !== pins.selectionTimeLimitSeconds) refProblems.push("reference limits");
  if (reference.effective_seed !== pins.effectiveSeed || reference.hf_effective_seed !== pins.effectiveSeed) refProblems.push("reference seeds");
  if (!same(reference.ga_effective_configuration, pins.gaConfiguration) || !same(reference.hf_effective_configuration, pins.gaConfiguration)) refProblems.push("reference GA/HF configuration");
  if (reference.selection_solver.version !== pins.selectionSolver.version || reference.selection_solver.random_seed !== pins.selectionSolver.randomSeed ||
    reference.selection_solver.num_workers !== pins.selectionSolver.numWorkers) refProblems.push("reference selection solver");
  check("reference_matches_design", refProblems.length === 0, refProblems.length === 0 ? "reference archive equals the values named by the design" : `reference differs from the design: ${refProblems.join(", ")}`);

  return { ok: checks.every((item) => item.ok), checks };
}

export function assertPreflight(report: PreflightReport): void {
  if (!report.ok) throw new PreflightRefusal(report);
}

/** Printable report: ids, counts and sha prefixes only, never raw student ids or secrets. */
export function formatPreflightReport(report: PreflightReport): string {
  return [...report.checks.map((item) => `${item.ok ? "PASS" : "FAIL"} ${item.id}: ${item.message}`), report.ok ? "PREFLIGHT OK" : "PREFLIGHT REFUSED"].join("\n");
}
