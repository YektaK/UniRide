import fs from "node:fs";
import path from "node:path";
import { fleetManifestSchema } from "./fleet-scenario-report";
import type { PreflightReference } from "./fleet-rerun-preflight";

// Reads the historical campaign a WP-E10 re-run is compared with. Read-only: it only opens files, never writes.
//   run manifest: parameters, fleet types, GA/HF configuration, seeds, selection solver, declared matrix sha256
//   wave composition: the 4sw5so archive, whose `routeIntervals` list the (anonymised) occurrence ids of every wave

const readJson = (file: string): unknown => JSON.parse(fs.readFileSync(file, "utf8"));
const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** Repo-relative POSIX form of a path; refuses a path outside the repository so no local directory reaches a published file. */
export function repoRelative(file: string, root: string): string {
  const relative = path.relative(path.resolve(root), path.resolve(file));
  if (relative === "" || relative.startsWith("..") || path.isAbsolute(relative)) throw new Error("Reference path lies outside the repository");
  return relative.split(path.sep).join("/");
}

export function loadFleetReference(input: { manifestPath: string; wavesDir: string; root?: string }): PreflightReference {
  const manifestPath = path.resolve(input.manifestPath);
  const wavesDir = path.resolve(input.wavesDir);
  const root = input.root ?? process.cwd();
  const manifestRelative = repoRelative(manifestPath, root);
  const wavesRelative = repoRelative(wavesDir, root);
  const manifest = fleetManifestSchema.parse(readJson(manifestPath));
  const manifestDir = path.dirname(manifestPath);

  // Every sha256 the old campaign declares: its matrix files and the provenance of each run.
  const shas = new Set<string>();
  for (const run of manifest.runs) {
    const provenance = run.matrix_provenance;
    if (record(provenance) && typeof provenance.sha256 === "string") shas.add(provenance.sha256);
    if (run.matrix_file) {
      const matrix = readJson(path.join(manifestDir, run.matrix_file));
      if (record(matrix) && typeof matrix.sha256 === "string") shas.add(matrix.sha256);
    }
  }

  // Wave composition per date from the 4sw5so responses; the four ride limits must agree.
  const waves: Record<string, Record<string, string[]>> = {};
  const waveClasses: Record<string, Record<string, { sw: number; so: number }>> = {};
  for (const date of manifest.parameters.dates) {
    let first: Record<string, string[]> | null = null;
    let firstClasses: Record<string, { sw: number; so: number }> | null = null;
    for (const ride of manifest.parameters.ride_limits) {
      const response = readJson(path.join(wavesDir, `${date}_R${ride}_repeat1.response.json`));
      if (!record(response) || !Array.isArray(response.routeIntervals) || response.serviceDate !== date) throw new Error(`Reference waves unreadable for ${date} R${ride}`);
      const byWave: Record<string, string[]> = {};
      const classes: Record<string, { sw: number; so: number }> = {};
      for (const interval of response.routeIntervals as Array<Record<string, unknown>>) {
        const jobId = String(interval.jobId);
        byWave[jobId] = [...(byWave[jobId] ?? []), ...(interval.occurrenceIds as string[])];
        const c = classes[jobId] ?? { sw: 0, so: 0 };
        classes[jobId] = { sw: c.sw + Number(interval.swCount), so: c.so + Number(interval.soCount) };
      }
      for (const ids of Object.values(byWave)) ids.sort();
      if (first === null) { first = byWave; firstClasses = classes; }
      else if (JSON.stringify(first) !== JSON.stringify(byWave) || JSON.stringify(firstClasses) !== JSON.stringify(classes)) throw new Error(`Reference waves differ between ride limits for ${date}`);
    }
    waves[date] = first ?? {};
    waveClasses[date] = firstClasses ?? {};
  }
  // The typed campaign must have built a menu for exactly these waves.
  for (const run of manifest.runs) {
    const menuWaves = run.menu_sizes.map((item) => item.wave_id).sort();
    if (JSON.stringify(menuWaves) !== JSON.stringify(Object.keys(waves[run.date] ?? {}).sort())) {
      throw new Error(`Reference menu waves differ from the wave archive for ${run.date} R${run.ride_limit}`);
    }
  }

  return {
    manifestPath: manifestRelative, gitCommit: manifest.git_commit, wavesArchive: wavesRelative,
    parameters: {
      dates: manifest.parameters.dates, ride_limits: manifest.parameters.ride_limits, tour_limit: manifest.parameters.tour_limit,
      scenarios: manifest.parameters.scenarios, max_cars: manifest.parameters.max_cars, node_budget: manifest.parameters.node_budget,
      selection_time_limit_seconds: manifest.parameters.selection_time_limit_seconds, admission_mode: manifest.parameters.admission_mode,
    },
    fleet_types: manifest.fleet_types, fixed_type: manifest.fixed_type, minimize_type: manifest.minimize_type,
    ga_effective_configuration: manifest.ga_effective_configuration, hf_effective_configuration: manifest.hf_effective_configuration,
    effective_seed: manifest.effective_seed, hf_effective_seed: manifest.hf_effective_seed,
    selection_solver: {
      version: manifest.selection_solver.version, random_seed: manifest.selection_solver.random_seed, num_workers: manifest.selection_solver.num_workers,
    },
    matrixSha256s: [...shas].sort(), waves, waveClasses,
  };
}
