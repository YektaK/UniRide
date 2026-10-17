import { z } from "zod";
import type { FleetTypeSpec, ScenarioKey } from "./fleet-scenario-args";
import type { FleetScenarioDay, ScenarioResult } from "./fleet-scenario-run";

// Tables and manifest of the heterogeneous-fleet experiment (design section 8). Pure functions,
// no I/O: the CLI writes what these return.

const weekdayNames = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const dateObject = (date: string) => new Date(`${date}T00:00:00Z`);
const addDays = (date: string, days: number) => {
  const value = dateObject(date);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
};
const round6 = (value: number) => Math.round(value * 1_000_000) / 1_000_000;
export const scenarioName = (scenario: ScenarioKey) => (scenario === "A" ? "A" : `L${scenario}`);

export function clock(minutes: number | null): string | null {
  if (minutes === null) return null;
  const whole = Math.floor(minutes);
  const seconds = Math.round((minutes - whole) * 60);
  const base = `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
  return seconds ? `${base}:${String(seconds).padStart(2, "0")}` : base;
}

export interface FleetDailyRow {
  date: string; weekday: string; ride_limit: number; tour_limit: number;
  scenario: string; large_limit: number | null;
  cars: number | null; cars_status: string | null; large_vehicles: number | null; large_vehicles_proven: boolean | null;
  large_routes: number | null; car_routes: number | null; routes: number | null;
  waves: number | null; students: number | null; legs: number | null;
  large_vehicle_minutes: number | null; car_vehicle_minutes: number | null; total_vehicle_minutes: number | null;
  ride_passengers: number | null; ride_mean: number | null; ride_median: number | null; ride_p90: number | null; ride_max: number | null;
  car_first_start: string | null; car_last_end: string | null; car_busy_minutes: number | null;
  status: string; selection_status: string | null; assignment_status: string | null; reason_codes: string[];
}
export const FLEET_DAILY_COLUMNS = [
  "date", "weekday", "ride_limit", "tour_limit", "scenario", "large_limit", "cars", "cars_status", "large_vehicles",
  "large_vehicles_proven", "large_routes", "car_routes", "routes", "waves", "students", "legs",
  "large_vehicle_minutes", "car_vehicle_minutes", "total_vehicle_minutes", "ride_passengers", "ride_mean", "ride_median",
  "ride_p90", "ride_max", "car_first_start", "car_last_end", "car_busy_minutes", "status", "selection_status",
  "assignment_status", "reason_codes",
] as const;

export function fleetDailyRows(
  day: FleetScenarioDay, requested: readonly ScenarioKey[], ride: number, tour: number,
  fixedType: Pick<FleetTypeSpec, "typeId">, minimiseType: Pick<FleetTypeSpec, "typeId"> | null,
): FleetDailyRow[] {
  const base = { date: day.serviceDate, weekday: weekdayNames[dateObject(day.serviceDate).getUTCDay()], ride_limit: ride, tour_limit: tour };
  return requested.map((key): FleetDailyRow => {
    const result: ScenarioResult | undefined = day.scenarios.find((item) => item.scenario === key);
    const empty = {
      ...base, scenario: scenarioName(key), large_limit: key === "A" ? null : key, cars: null, cars_status: null,
      large_vehicles: null, large_vehicles_proven: null, large_routes: null, car_routes: null, routes: null,
      waves: day.status === "blocked_data" ? null : day.waves, students: day.status === "blocked_data" ? null : day.students,
      legs: day.status === "blocked_data" ? null : day.legs,
      large_vehicle_minutes: null, car_vehicle_minutes: null, total_vehicle_minutes: null, ride_passengers: null, ride_mean: null,
      ride_median: null, ride_p90: null, ride_max: null, car_first_start: null, car_last_end: null, car_busy_minutes: null,
      status: day.status === "ready" ? "missing" : day.status, selection_status: null, assignment_status: null,
      reason_codes: [...day.reasonCodes],
    };
    if (!result) return empty;
    const windows = result.carUsageWindows;
    return {
      ...empty,
      large_limit: result.largeLimit, cars: result.cars, cars_status: result.carsStatus,
      large_vehicles: result.largeVehicles, large_vehicles_proven: result.largeVehiclesProven,
      large_routes: result.largeRoutes, car_routes: result.carRoutes, routes: result.routes.length,
      large_vehicle_minutes: result.minutesByType[fixedType.typeId] ?? 0,
      car_vehicle_minutes: minimiseType ? result.minutesByType[minimiseType.typeId] ?? 0 : 0,
      total_vehicle_minutes: result.totalVehicleMinutes,
      ride_passengers: result.ride?.passengers ?? null, ride_mean: result.ride?.mean ?? null,
      ride_median: result.ride?.median ?? null, ride_p90: result.ride?.p90 ?? null, ride_max: result.ride?.max ?? null,
      car_first_start: windows.length ? clock(Math.min(...windows.map((w) => w.windowStartMinutes))) : null,
      car_last_end: windows.length ? clock(Math.max(...windows.map((w) => w.windowEndMinutes))) : null,
      car_busy_minutes: windows.length ? round6(windows.reduce((sum, w) => sum + w.busyMinutes, 0)) : null,
      status: day.status === "empty_day" ? "empty_day" : result.status,
      selection_status: result.selection?.status ?? null, assignment_status: result.assignment?.status ?? null,
      reason_codes: [...result.reasonCodes],
    };
  });
}

export const CAR_WINDOW_COLUMNS = ["date", "ride_limit", "scenario", "car_id", "window_start", "window_end", "busy_minutes", "routes", "waves"] as const;
export function carWindowRows(day: FleetScenarioDay, ride: number) {
  return day.scenarios.flatMap((result) => result.carUsageWindows.map((window) => ({
    date: day.serviceDate, ride_limit: ride, scenario: scenarioName(result.scenario), car_id: window.carId,
    window_start: clock(window.windowStartMinutes), window_end: clock(window.windowEndMinutes),
    busy_minutes: window.busyMinutes, routes: window.routeCount, waves: window.waves,
  })));
}

export const FLEET_WEEKLY_COLUMNS = [
  "week_of", "ride_limit", "scenario", "large_limit", "weekly_cars", "weekly_large_vehicles",
  "monday_cars", "tuesday_cars", "wednesday_cars", "thursday_cars", "friday_cars", "cars_day_sum",
  "complete_week", "all_proven", "infeasible_days", "large_vehicle_minutes", "car_vehicle_minutes", "total_vehicle_minutes",
  "ride_passengers", "ride_mean", "ride_max",
] as const;

/**
 * Weekly rows per (week, R, scenario). Q5: weekly cars is the maximum over the days (the same
 * cars every day); `cars_day_sum` and the per-weekday columns carry the per-day need (borrow per day).
 * Weekly figures are null unless all five weekdays are accounted for.
 */
export function aggregateFleetWeeks(rows: readonly FleetDailyRow[]) {
  const groups = new Map<string, FleetDailyRow[]>();
  for (const row of rows) {
    const monday = addDays(row.date, -((dateObject(row.date).getUTCDay() + 6) % 7));
    const key = JSON.stringify([monday, row.ride_limit, row.scenario]);
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return [...groups.entries()].map(([key, group]) => {
    const [monday, ride, scenario] = JSON.parse(key) as [string, number, string];
    const daily = Array.from({ length: 5 }, (_, i) => group.find((row) => row.date === addDays(monday, i)));
    const accounted = (row: FleetDailyRow | undefined): row is FleetDailyRow =>
      row !== undefined && (row.status === "ok" || row.status === "empty_day");
    const complete = daily.every(accounted);
    const days = daily.filter(accounted);
    const carsOf = (row: FleetDailyRow | undefined) => accounted(row) ? row.cars ?? 0 : null;
    const sum = (pick: (row: FleetDailyRow) => number | null) =>
      complete && days.every((row) => pick(row) !== null) ? round6(days.reduce((s, row) => s + (pick(row) ?? 0), 0)) : null;
    const passengers = days.reduce((s, row) => s + (row.ride_passengers ?? 0), 0);
    const weighted = days.reduce((s, row) => s + (row.ride_mean ?? 0) * (row.ride_passengers ?? 0), 0);
    const carDays = daily.map(carsOf);
    return {
      week_of: monday, ride_limit: ride, scenario, large_limit: group[0].large_limit,
      weekly_cars: complete && scenario !== "A" ? Math.max(...carDays.map((v) => v!)) : null,
      weekly_large_vehicles: complete ? Math.max(...days.map((row) => row.large_vehicles ?? 0)) : null,
      monday_cars: carDays[0], tuesday_cars: carDays[1], wednesday_cars: carDays[2], thursday_cars: carDays[3], friday_cars: carDays[4],
      cars_day_sum: complete && scenario !== "A" ? carDays.reduce<number>((s, v) => s + (v ?? 0), 0) : null,
      complete_week: complete,
      all_proven: complete && days.every((row) => row.status === "empty_day" ||
        (scenario === "A" ? row.large_vehicles_proven === true : row.cars_status === "proven_over_menu")),
      infeasible_days: group.filter((row) => row.status === "infeasible_for_L").length,
      large_vehicle_minutes: sum((row) => row.large_vehicle_minutes),
      car_vehicle_minutes: sum((row) => row.car_vehicle_minutes),
      total_vehicle_minutes: sum((row) => row.total_vehicle_minutes),
      ride_passengers: complete ? passengers : null,
      ride_mean: complete && passengers ? round6(weighted / passengers) : null,
      ride_max: complete ? Math.max(0, ...days.map((row) => row.ride_max ?? 0)) : null,
    };
  });
}

// ---- manifest ------------------------------------------------------------------------------
const fleetTypeSchema = z.object({
  typeId: z.string().min(1), swCapacity: z.number().int().nonnegative(), soCapacity: z.number().int().nonnegative(),
  totalCapacity: z.number().int().min(1).optional(),
  cooldownMinutes: z.number().int().nonnegative(),
  rideLimit: z.number().optional(), tourLimit: z.number().optional(),
});
const runSchema = z.object({
  date: z.string(), ride_limit: z.number(), day_status: z.string(),
  response_files: z.array(z.string()), matrix_file: z.string().nullable(),
  matrix_provenance: z.unknown().nullable(),
  rate_limit_waits: z.array(z.object({ path: z.string(), status: z.number(), wait_seconds: z.number(), attempt: z.number() })),
  optimizer_http_failures: z.array(z.object({ path: z.string(), status: z.number() })),
  menu_sizes: z.array(z.object({ wave_id: z.string(), options: z.number(), skipped: z.number() })),
  scenarios: z.array(z.object({
    scenario: z.string(), status: z.string(), cars: z.number().nullable(), cars_status: z.string().nullable(),
    selection_status: z.string().nullable(), assignment_status: z.string().nullable(),
  })),
  // WP-E10 (archive format v2). Absent in the historical manifests, which stay readable.
  menu_options_file: z.string().nullable().optional(),
  selection_exchange_files: z.array(z.object({ scenario: z.string(), file: z.string() })).optional(),
});
/** Archive format of the WP-E10 re-run: per-option menu files and per-(date, R, L) selection exchanges. */
export const FLEET_ARCHIVE_FORMAT = "fleet_archive_v2";
const preflightCheckSchema = z.object({ id: z.string(), ok: z.boolean(), message: z.string() });
/** Repo-relative POSIX path: no drive letter, no leading slash, no backslash, no parent step. A published file must not name a local directory. */
export const repoRelativePathSchema = z.string().min(1).refine(
  (value) => !/^[A-Za-z]:/.test(value) && !value.startsWith("/") && !value.includes("\\") && !value.split("/").includes(".."),
  "must be a repo-relative POSIX path",
);
const preflightRecordSchema = z.object({
  ok: z.boolean(), checks: z.array(preflightCheckSchema),
  /** Exact limit of the occurrence comparison (anonymised alias), see OCCURRENCE_CHECK_LIMIT. */
  occurrence_check_limit: z.string().min(1),
  reference_manifest: repoRelativePathSchema, reference_git_commit: z.string(), reference_waves_archive: repoRelativePathSchema,
  live: z.object({
    matrix_sha256: z.array(z.string()), waves: z.number().int(), legs: z.number().int(),
    waves_by_date: z.record(z.string(), z.number().int()), legs_by_date: z.record(z.string(), z.number().int()),
  }),
});
export const fleetManifestSchema = z.object({
  git_commit: z.string().min(7), dirty_working_tree: z.boolean(), timestamp: z.string(),
  parameters: z.object({
    dates: z.array(z.string()), ride_limits: z.array(z.number()), tour_limit: z.number(),
    scenarios: z.array(z.string()), max_cars: z.number().nullable(), node_budget: z.number(),
    selection_time_limit_seconds: z.number(), admission_mode: z.literal("assume_confirmed"),
    /** Rule (e): this run covers a subset of the campaign dates (one day run again). Absent in a campaign. */
    allow_subset_dates: z.boolean().optional(),
  }),
  fleet_types: z.array(fleetTypeSchema).min(1), fleet_types_source: z.literal("cli"),
  fixed_type: z.string(), minimize_type: z.string().nullable(), db_vehicles_consulted: z.literal(false),
  algorithms: z.object({ baseline: z.literal("ga_split"), menu: z.literal("ga_split_hf") }),
  termination_protocol: z.literal("native"),
  ga_defaults: z.record(z.string(), z.unknown()), ga_effective_configuration: z.record(z.string(), z.unknown()),
  effective_seed: z.number().int(),
  hf_effective_configuration: z.record(z.string(), z.unknown()), hf_effective_seed: z.number().int(),
  selection_solver: z.object({
    name: z.literal("cp-sat"), version: z.string().nullable(), random_seed: z.number().int().nullable(),
    num_workers: z.number().int().nullable(), time_limit_seconds: z.number(),
  }),
  vehicle_count_scope: z.string(), weekly_cars_definition: z.string(),
  runs: z.array(runSchema), state: z.enum(["running", "completed", "failed"]), completed_at: z.string().nullable(),
  // WP-E10 (archive format v2). Absent in the historical manifests, which stay readable.
  archive_format: z.literal(FLEET_ARCHIVE_FORMAT).optional(),
  /** Repo-relative location of uniride_core, optimizer_api and academic_benchmark as the run's interpreter resolved them (all inside the run worktree). */
  python_provenance: z.record(z.string(), repoRelativePathSchema).optional(),
  /** `campaign` (the archive WP-E4 reads) or `rule_e_second_run` (one day run again to prove determinism; never an archive). */
  run_kind: z.enum(["campaign", "rule_e_second_run"]).optional(),
  pinned_commit: z.string().regex(/^[0-9a-f]{7,40}$/).optional(),
  preflight: preflightRecordSchema.optional(),
  /** Compute-policy values the CLI environment (and, through the session wrapper, the optimizer) runs with, rate limit included. */
  compute_policy: z.record(z.string(), z.unknown()).optional(),
  /** `applied_policy` the running optimizer reported in its /optimize answers (profile and effective limits). */
  optimizer_policy: z.object({
    profile_id: z.string(), limits: z.record(z.string(), z.unknown()), responses_checked: z.number().int(), limits_identical: z.boolean(),
  }).optional(),
});
export type FleetManifest = z.infer<typeof fleetManifestSchema>;
export type FleetPreflightRecord = z.infer<typeof preflightRecordSchema>;
/**
 * Manifest of a WP-E10 re-run: everything optional in the historical format is mandatory here (design
 * section 9, rules (a), (b), (f), (g)): clean tree at the pinned commit, the passed preflight, and the
 * per-option and selection-exchange files of every run that built a menu.
 */
export const extendedFleetManifestSchema = fleetManifestSchema.superRefine((manifest, ctx) => {
  const fail = (message: string) => ctx.addIssue({ code: z.ZodIssueCode.custom, message });
  if (manifest.archive_format !== FLEET_ARCHIVE_FORMAT) fail("archive_format must be fleet_archive_v2");
  if (manifest.dirty_working_tree) fail("a re-run archive requires a clean working tree");
  if (!manifest.pinned_commit || !manifest.git_commit.startsWith(manifest.pinned_commit)) fail("git_commit must equal the pinned commit");
  if (!manifest.preflight?.ok) fail("a passed preflight is required");
  if (!manifest.run_kind) fail("run_kind must be campaign or rule_e_second_run");
  if ((manifest.parameters.allow_subset_dates === true) !== (manifest.run_kind === "rule_e_second_run")) {
    fail("allow_subset_dates and run_kind rule_e_second_run must go together");
  }
  if (manifest.state === "completed") {
    if (!manifest.compute_policy) fail("compute_policy must be recorded");
    if (!manifest.python_provenance || !["uniride_core", "optimizer_api", "academic_benchmark"].every((name) => name in manifest.python_provenance!)) {
      fail("python_provenance must be recorded for uniride_core, optimizer_api and academic_benchmark");
    }
    if (!manifest.optimizer_policy || manifest.optimizer_policy.responses_checked < 1 || !manifest.optimizer_policy.limits_identical) fail("optimizer_policy must be recorded and identical over all answers");
    // Acceptance of the re-run grid: every (date, R) cell present exactly once and ready.
    const expected = manifest.parameters.dates.length * manifest.parameters.ride_limits.length;
    const cells = new Set(manifest.runs.map((run) => `${run.date}|${run.ride_limit}`));
    if (manifest.runs.length !== expected || cells.size !== expected) fail("a completed re-run needs every (date, R) cell exactly once");
    if (manifest.runs.some((run) => run.day_status !== "ready")) fail("a completed re-run needs every day ready");
    // A non-OK optimizer answer (also a 429 that survived the retries) drops a menu option: the archive would not hold every option.
    if (manifest.runs.some((run) => run.optimizer_http_failures.length > 0)) fail("a completed re-run must have no optimizer HTTP failure");
  }
  for (const run of manifest.runs) {
    const wantsMenu = run.day_status === "ready" && run.menu_sizes.length > 0;
    if (wantsMenu && !run.menu_options_file) fail(`run ${run.date} R${run.ride_limit} lacks menu_options_file`);
    // A scenario whose request could not be built (SELECTION_INTERVAL_PRECISION) has no exchange file; the list itself must exist.
    if (wantsMenu && run.selection_exchange_files === undefined) fail(`run ${run.date} R${run.ride_limit} lacks selection_exchange_files`);
  }
});
export type FleetManifestRun = z.infer<typeof runSchema>;

export function manifestRun(
  day: FleetScenarioDay, ride: number, responseFiles: readonly string[], matrixFile: string | null,
  matrixProvenance: unknown, rateLimitWaits: FleetManifestRun["rate_limit_waits"], httpFailures: FleetManifestRun["optimizer_http_failures"],
  archive?: { menuOptionsFile: string | null; selectionExchangeFiles: ReadonlyArray<{ scenario: string; file: string }> },
): FleetManifestRun {
  return {
    date: day.serviceDate, ride_limit: ride, day_status: day.status, response_files: [...responseFiles],
    matrix_file: matrixFile, matrix_provenance: matrixProvenance ?? null,
    rate_limit_waits: rateLimitWaits, optimizer_http_failures: httpFailures,
    menu_sizes: day.menu.map((wave) => ({
      wave_id: wave.waveId, options: wave.options.filter((o) => o.status === "included").length,
      skipped: wave.options.filter((o) => o.status !== "included").length,
    })),
    scenarios: day.scenarios.map((result) => ({
      scenario: scenarioName(result.scenario), status: result.status, cars: result.cars, cars_status: result.carsStatus,
      selection_status: result.selection?.status ?? null, assignment_status: result.assignment?.status ?? null,
    })),
    ...(archive ? { menu_options_file: archive.menuOptionsFile, selection_exchange_files: [...archive.selectionExchangeFiles] } : {}),
  };
}
