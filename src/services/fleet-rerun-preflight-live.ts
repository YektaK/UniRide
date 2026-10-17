import "server-only";
import {
  createDailyPlanDemandState, fetchMatrixSnapshot, groupWaves, loadDailyPlanDemand,
  type DailyPlanDeps, type DailyPlanReader,
} from "@/services/daily-plan-run";
import { anonymizeResponse } from "@/services/plan-experiments";
import {
  assertPreflight, evaluatePreflight, OCCURRENCE_CHECK_LIMIT, PINNED,
  type LiveDay, type WaveClasses, type PreflightObservation, type PreflightPins, type PreflightReference, type PreflightReport, type SolverCapture,
} from "@/services/fleet-rerun-preflight";
import type { FleetPreflightRecord } from "@/services/fleet-scenario-report";

// Live half of the WP-E10 preflight. It performs the same reads as the campaign before its first solve (the demand
// tables and the matrix snapshot) and nothing else: no /optimize call, no selection call, no write.

/**
 * A Supabase reader that can only select. Every other member of the client (insert, update, upsert, delete, rpc,
 * auth, storage, ...) and every other member of a table handle throws, so a code path that tried to write would fail
 * loudly instead of changing live data.
 */
export function readOnlyReader(client: DailyPlanReader): DailyPlanReader {
  const refuse = (what: string): never => { throw new Error(`Read-only reader: ${what} is not allowed`); };
  const table = (name: string) => new Proxy({}, {
    get: (_target, property) => property === "select"
      ? (...args: unknown[]) => (client.from(name) as unknown as { select: (...a: unknown[]) => unknown }).select(...args)
      : refuse(`table ${String(property)}`),
  });
  return new Proxy({}, {
    get: (_target, property) => property === "from" ? (name: string) => table(name) : refuse(`client ${String(property)}`),
  }) as unknown as DailyPlanReader;
}

/**
 * Anonymised, sorted occurrence ids per wave (the alias of the archives), from the demand of a day. The raw ids never
 * leave this function. `labels` is the day's occurrence-label map, which drives the anonymiser.
 */
export function anonymiseWaves(
  labels: Readonly<Record<string, string>>, demand: Readonly<Record<string, { readonly occurrenceIds: readonly string[]; readonly sw: number; readonly so: number }>>,
): { waves: Record<string, string[]>; classes: Record<string, WaveClasses> } {
  const raw = Object.fromEntries(Object.entries(demand).map(([id, wave]) => [id, [...wave.occurrenceIds]]));
  const anonymous = anonymizeResponse({ occurrenceLabels: labels, waves: raw }) as { waves: Record<string, string[]> };
  return {
    waves: Object.fromEntries(Object.entries(anonymous.waves).map(([id, ids]) => [id, [...ids].sort()])),
    classes: Object.fromEntries(Object.entries(demand).map(([id, wave]) => [id, { sw: wave.sw, so: wave.so }])),
  };
}

/** Waves and matrix of each date, loaded exactly as `runFleetScenarioDay` loads them (`assume_confirmed`). */
export async function collectLiveDays(
  deps: Pick<DailyPlanDeps, "reader" | "optimizerFetch">, dates: readonly string[],
): Promise<LiveDay[]> {
  const days: LiveDay[] = [];
  for (const date of dates) {
    const state = createDailyPlanDemandState(true);
    const loaded = await loadDailyPlanDemand(deps.reader, date, true, state);
    if (loaded.kind === "blocked") { days.push({ date, status: "blocked_data", matrix: null, waves: {}, classes: {} }); continue; }
    if (loaded.kind === "empty") { days.push({ date, status: "empty_day", matrix: null, waves: {}, classes: {} }); continue; }
    const matrix = await fetchMatrixSnapshot(deps.optimizerFetch, loaded.admitted);
    const demand: Record<string, { occurrenceIds: string[]; sw: number; so: number }> = {};
    for (const group of groupWaves(loaded.admitted)) {
      const first = group[0]!;
      demand[`${date}:${first.direction}:${first.anchorMinutes}`] = {
        occurrenceIds: group.map((item) => item.occurrenceId),
        sw: group.filter((item) => item.disabilityType === "Sw").length, so: group.filter((item) => item.disabilityType === "So").length,
      };
    }
    // Same anonymiser as the archive files, so ids are comparable and no raw student id leaves this function.
    const { waves, classes } = anonymiseWaves(state.occurrenceLabels, demand);
    days.push({
      date, status: "ready", waves, classes,
      matrix: matrix === null ? null : { sha256: matrix.sha256, source: matrix.source, id: matrix.id, version: matrix.version },
    });
  }
  return days;
}

export interface PreflightDeps extends Pick<DailyPlanDeps, "reader" | "optimizerFetch"> {
  git: () => { head: string; dirty: boolean };
  captureSolver: () => SolverCapture;
}
export interface PreflightInput {
  cli: PreflightObservation["cli"];
  pinCommit: string;
}

/** One preflight: reads git, the solver configuration and the live demand/matrix, then evaluates. Writes nothing. */
export async function runFleetRerunPreflight(
  deps: PreflightDeps, input: PreflightInput, reference: PreflightReference, pins: PreflightPins = PINNED,
): Promise<{ report: PreflightReport; observation: PreflightObservation; record: FleetPreflightRecord }> {
  const git = deps.git();
  const solver = deps.captureSolver();
  const days = await collectLiveDays({ reader: readOnlyReader(deps.reader), optimizerFetch: deps.optimizerFetch }, input.cli.dates);
  const observation: PreflightObservation = { git, pinCommit: input.pinCommit, cli: input.cli, solver, days };
  const report = evaluatePreflight(reference, observation, pins);
  const wavesByDate = Object.fromEntries(days.map((day) => [day.date, Object.keys(day.waves).length]));
  const legsByDate = Object.fromEntries(days.map((day) => [day.date, Object.values(day.waves).reduce((n, ids) => n + ids.length, 0)]));
  const record: FleetPreflightRecord = {
    ok: report.ok, checks: report.checks, occurrence_check_limit: OCCURRENCE_CHECK_LIMIT,
    reference_manifest: reference.manifestPath, reference_git_commit: reference.gitCommit, reference_waves_archive: reference.wavesArchive,
    live: {
      matrix_sha256: [...new Set(days.flatMap((day) => (day.matrix ? [day.matrix.sha256] : [])))].sort(),
      waves: Object.values(wavesByDate).reduce((a, b) => a + b, 0), legs: Object.values(legsByDate).reduce((a, b) => a + b, 0),
      waves_by_date: wavesByDate, legs_by_date: legsByDate,
    },
  };
  return { report, observation, record };
}

export { assertPreflight };
