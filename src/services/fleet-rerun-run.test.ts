import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { RerunAbort, dirtyFromPorcelain, readGitState, runFleetRerun, type RerunDeps, type RerunFs } from "@/services/fleet-rerun-run";
import { PINNED, OCCURRENCE_CHECK_LIMIT, type PreflightPins, type PreflightReference } from "@/services/fleet-rerun-preflight";
import { collectLiveDays } from "@/services/fleet-rerun-preflight-live";
import { loadFleetReference } from "@/services/fleet-rerun-reference";
import { extendedFleetManifestSchema } from "@/services/fleet-scenario-archive";
import { parseFleetArgs } from "@/services/fleet-scenario-args";
import { DATE, matrixOf, pickSelection, reader, rows, transport } from "./fleet-scenario-fixtures";

const RESULTS = path.resolve(process.cwd(), "docs/paper/results");
const LARGE_SEDAN_MANIFEST = path.join(RESULTS, "week-2026-10-05-fleet/run_manifest.json");
const WAVES_DIR = path.join(RESULTS, "week-2026-10-05-4sw5so");
const HEAD = "f".repeat(40);
const GA = {
  population_size: 50, max_iterations: 100, crossover_rate: 0.85, mutation_rate: 0.2, elite_count: 3, tournament_size: 4,
  max_no_improvement: 25, seed: null, local_search_type: "hybrid", local_search_interval: 10, diversify_threshold: 30,
};
const SOLVER = {
  ga: { defaults: GA, config: GA, seed: 42 }, hf: { config: GA, seed: 42 },
  cp: { version: "9.15.6755", seed: 20261008, workers: 1 },
  compute_policy: { profile_id: "production-conservative-v1", rate_limit_requests: 30, rate_limit_window_seconds: 1 },
};
const pins: PreflightPins = { ...PINNED, matrixSha256: "a".repeat(64), waveCount: 2, legCount: 6 };
const OUT = "docs/paper/results/week-2026-10-05-fleet-rerun-test";

const argv = (rides = "60", extra: string[] = []) => [
  "--dates", DATE, "--ride-limits", rides, "--tour-limit", "150", "--fleet-types", "large:4sw5so:cd10,sedan:0sw4so:cd10",
  "--fixed-type", "large", "--minimize-type", "sedan", "--scenarios", "A,1,2", "--pin-commit", HEAD.slice(0, 12),
  "--reference-manifest", "docs/paper/results/week-2026-10-05-fleet/run_manifest.json", "--out", OUT, ...extra,
];

async function harnessReference(rideLimits: number[]): Promise<PreflightReference> {
  const days = await collectLiveDays({ reader: reader(rows()).client, optimizerFetch: transport().fetch }, [DATE]);
  const base = loadFleetReference({ manifestPath: LARGE_SEDAN_MANIFEST, wavesDir: WAVES_DIR });
  return {
    ...base, parameters: { ...base.parameters, dates: [DATE], ride_limits: rideLimits, scenarios: ["A", "L1", "L2"] },
    matrixSha256s: ["a".repeat(64)], waves: { [DATE]: days[0].waves }, waveClasses: { [DATE]: days[0].classes },
  };
}

function fakeFs(existing: string[] = []) {
  const files = new Map<string, string>();
  const dirs = new Set<string>(existing);
  const fsApi: RerunFs = {
    exists: (p) => dirs.has(p) || files.has(p), mkdir: (p) => { dirs.add(p); }, write: (p, text) => { files.set(p, text); },
  };
  return { fsApi, files, dirs };
}

interface Setup {
  status?: string; head?: string; data?: Record<string, unknown[]>;
  fetchWrap?: (inner: ReturnType<typeof transport>["fetch"], state: { snapshots: number }) => (p: string, i?: RequestInit) => Promise<Response>;
  afterFirstSnapshot?: () => void;
}
async function setup(rides: number[], opts: Setup = {}) {
  const data = opts.data ?? rows();
  const db = reader(data);
  const t = transport({ selection: pickSelection("q1", () => ["large", "car"]) });
  const fsx = fakeFs();
  const state = { snapshots: 0 };
  const inner = async (p: string, i?: RequestInit) => {
    if (p === "/api/v1/internal/matrix-snapshot") { state.snapshots += 1; if (state.snapshots === 1) opts.afterFirstSnapshot?.(); }
    return t.fetch(p, i);
  };
  const gitCalls: string[][] = [];
  const log: string[] = [];
  const deps: RerunDeps = {
    root: process.cwd(), reader: db.client, optimizerFetch: opts.fetchWrap ? opts.fetchWrap(inner, state) : inner,
    git: (args) => { gitCalls.push(args); return args[0] === "rev-parse" ? `${opts.head ?? HEAD}\n` : opts.status ?? ""; },
    captureSolver: () => structuredClone(SOLVER), loadReference: () => reference, fs: fsx.fsApi, log: (l) => log.push(l),
    now: () => new Date("2026-10-18T10:00:00Z"), pins,
  };
  const reference = await harnessReference(rides);
  return { deps, db, t, fsx, gitCalls, log, data };
}
const manifestOf = (fsx: { files: Map<string, string> }) => JSON.parse([...fsx.files.entries()].find(([p]) => p.endsWith("run_manifest.json"))![1]);
const solves = (calls: Array<{ path: string }>) => calls.filter((c) => c.path.endsWith("/v1/optimize") || c.path.endsWith("fleet-selection")).length;

describe("B1: the run gates of runFleetRerun", () => {
  it("a full run on matching inputs completes, writes the v2 archive and a valid extended manifest", async () => {
    const s = await setup([60]);
    const result = await runFleetRerun(s.deps, parseFleetArgs(argv()));
    expect(result.exitCode).toBe(0);
    const names = [...s.fsx.files.keys()].map((p) => path.basename(p));
    expect(names).toEqual(expect.arrayContaining(["run_manifest.json", `${DATE}_R60.menu_options.json`, `${DATE}_R60_L1.selection_exchange.json`, `${DATE}_R60_L2.selection_exchange.json`]));
    const manifest = manifestOf(s.fsx);
    expect(manifest.state).toBe("completed");
    expect(() => extendedFleetManifestSchema.parse(manifest)).not.toThrow();
    expect(s.db.writes).toEqual([]);
  });

  it("a refused preflight (dirty tree) makes 0 solve calls, creates no output directory and returns exit code 2", async () => {
    const s = await setup([60], { status: "?? stray.txt\n" });
    const result = await runFleetRerun(s.deps, parseFleetArgs(argv()));
    expect(result.exitCode).toBe(2);
    expect(solves(s.t.calls)).toBe(0);
    expect(s.fsx.dirs.size).toBe(0);
    expect(s.fsx.files.size).toBe(0);
  });

  it("a refused preflight on the live inputs (other occurrence ids) also stops before any solve", async () => {
    const s = await setup([60]);
    s.data.users = (s.data.users as Array<{ id: string }>).filter((u) => u.id !== "s-so2");
    const result = await runFleetRerun(s.deps, parseFleetArgs(argv()));
    expect(result.exitCode).toBe(2);
    expect(solves(s.t.calls)).toBe(0);
    expect(s.fsx.files.size).toBe(0);
  });

  it("--preflight-only reads and checks but solves nothing and writes nothing", async () => {
    const s = await setup([60]);
    const result = await runFleetRerun(s.deps, parseFleetArgs(argv("60", ["--preflight-only"])));
    expect(result.exitCode).toBe(0);
    expect(solves(s.t.calls)).toBe(0);
    expect(s.fsx.dirs.size).toBe(0);
    expect(s.fsx.files.size).toBe(0);
    expect(s.log.join("\n")).toContain("PREFLIGHT OK");
  });

  it("an untracked file alone counts as a dirty tree, and git is asked for untracked files explicitly", async () => {
    expect(dirtyFromPorcelain("?? x\n")).toBe(true);
    expect(dirtyFromPorcelain(" M a.ts\n")).toBe(true);
    expect(dirtyFromPorcelain("")).toBe(false);
    expect(dirtyFromPorcelain("\n")).toBe(false);
    const asked: string[][] = [];
    const state = readGitState((args) => { asked.push(args); return args[0] === "rev-parse" ? "abc\n" : "?? x\n"; });
    expect(state).toEqual({ head: "abc", dirty: true });
    expect(asked).toContainEqual(["status", "--porcelain", "--untracked-files=all"]);
  });

  it("a matrix sha256 that changes on the second cell aborts it before any solve and keeps a failed manifest", async () => {
    const other = "b".repeat(64);
    const s = await setup([60, 70], {
      fetchWrap: (inner, state) => async (p, i) => (p === "/api/v1/internal/matrix-snapshot" && state.snapshots >= 2
        ? (await inner(p, i), Response.json({ ...matrixOf(5), id: `time_matrix:sha256:${other}`, version: other, sha256: other }))
        : inner(p, i)),
    });
    const before = () => solves(s.t.calls);
    let atAbort = -1;
    await expect(runFleetRerun(s.deps, parseFleetArgs(argv("60,70"))).catch((e) => { atAbort = before(); throw e; })).rejects.toBeInstanceOf(RerunAbort);
    const solvesFirstCell = atAbort;
    expect(solvesFirstCell).toBeGreaterThan(0);
    // nothing was solved for the second cell: the call count did not move after the first cell
    const manifest = manifestOf(s.fsx);
    expect(manifest.state).toBe("failed");
    expect(manifest.runs).toHaveLength(1);
    expect(manifest.runs[0].ride_limit).toBe(60);
    const cell2 = s.t.calls.map((c) => c.path);
    expect(cell2.filter((p) => p === "/api/v1/internal/matrix-snapshot")).toHaveLength(3); // preflight, cell 1, cell 2
    expect(s.t.calls.slice(s.t.calls.map((c) => c.path).lastIndexOf("/api/v1/internal/matrix-snapshot") + 1)).toEqual([]);
  });
});

describe("N-d: the first non-OK optimizer answer stops the run", () => {
  it("aborts after the retries are exhausted, writes no further network call, keeps a failed manifest and does not write the cell", async () => {
    let atFailure = -1;
    const s = await setup([60, 70], {
      fetchWrap: (inner) => async (p, i) => {
        const body = i?.body ? JSON.parse(String(i.body)) : null;
        if (atFailure >= 0 && p.endsWith("/v1/optimize")) throw new Error("a call was made after the failure");
        if (p.endsWith("/v1/optimize") && body?.algorithm === "ga_split_hf" && body.vehicle_types?.[0]?.max_routes === 1) {
          atFailure = s.t.calls.length;
          return new Response("{}", { status: 500 });
        }
        return inner(p, i);
      },
    });
    await expect(runFleetRerun(s.deps, parseFleetArgs(argv("60,70")))).rejects.toThrow(/non-OK optimizer answer/i);
    expect(atFailure).toBeGreaterThan(0);
    expect(s.t.calls.length).toBe(atFailure); // nothing reached the optimizer after the failure, in this or the next cell
    const manifest = manifestOf(s.fsx);
    expect(manifest.state).toBe("failed");
    expect(manifest.runs).toEqual([]);
  });
});

describe("V-2: a rule (e) second run is labelled", () => {
  it("a campaign is labelled run_kind campaign and has no README; a subset run records the flag, run_kind and a one-line README", async () => {
    const full = await setup([60]);
    await runFleetRerun(full.deps, parseFleetArgs(argv()));
    expect(manifestOf(full.fsx)).toMatchObject({ run_kind: "campaign" });
    expect(manifestOf(full.fsx).parameters).not.toHaveProperty("allow_subset_dates");
    expect([...full.fsx.files.keys()].some((p) => p.endsWith("README.md"))).toBe(false);

    const second = await setup([60]);
    await runFleetRerun(second.deps, parseFleetArgs(argv("60", ["--allow-subset-dates"])));
    const manifest = manifestOf(second.fsx);
    expect(manifest.run_kind).toBe("rule_e_second_run");
    expect(manifest.parameters.allow_subset_dates).toBe(true);
    expect(manifest.state).toBe("completed");
    const readme = [...second.fsx.files.entries()].find(([p]) => p.endsWith("README.md"))![1];
    expect(readme.trim().split("\n")).toHaveLength(1);
    expect(readme).toMatch(/rule \(e\) second run/i);
  });
});

describe("B2: the wave composition is re-checked on every cell", () => {
  it("aborts before writing the cell when the live demand differs from the archive at capture time", async () => {
    const data = rows();
    const s = await setup([60], {
      // same students, same locations and ids (the alias is unchanged), but one is now a wheelchair user: only the Sw/So count of the wave tells
      data, afterFirstSnapshot: () => { (data.users as Array<{ id: string; disability_type: string }>).find((u) => u.id === "s-so2")!.disability_type = "Sw"; },
    });
    await expect(runFleetRerun(s.deps, parseFleetArgs(argv()))).rejects.toThrow(/differs from the archive/i);
    const names = [...s.fsx.files.keys()].map((p) => path.basename(p));
    expect(names.filter((n) => n.startsWith(DATE))).toEqual([]); // the cell was not written
    const manifest = manifestOf(s.fsx);
    expect(manifest.state).toBe("failed");
    expect(manifest.runs).toEqual([]);
  });
});

describe("B3 and N1/N2: the published manifest", () => {
  it("holds only repo-relative POSIX paths, no drive letter and no user directory", async () => {
    const s = await setup([60]);
    await runFleetRerun(s.deps, parseFleetArgs(argv()));
    const text = [...s.fsx.files.entries()].find(([p]) => p.endsWith("run_manifest.json"))![1];
    expect(text).not.toMatch(/[A-Za-z]:[\\/]/);
    expect(text).not.toMatch(/\\\\|\/Users\/|yektakayman/i);
    const manifest = JSON.parse(text);
    expect(manifest.preflight.reference_manifest).toBe("docs/paper/results/week-2026-10-05-fleet/run_manifest.json");
    expect(manifest.preflight.reference_waves_archive).toBe("docs/paper/results/week-2026-10-05-4sw5so");
  });
  it("records the optimizer policy, the compute-policy values and the exact limit of the occurrence check", async () => {
    const s = await setup([60]);
    await runFleetRerun(s.deps, parseFleetArgs(argv()));
    const manifest = manifestOf(s.fsx);
    expect(manifest.compute_policy).toMatchObject({ rate_limit_requests: 30, rate_limit_window_seconds: 1 });
    expect(manifest.optimizer_policy).toMatchObject({ profile_id: "production-conservative-v1", limits_identical: true });
    expect(manifest.optimizer_policy.responses_checked).toBeGreaterThan(5);
    expect(manifest.preflight.occurrence_check_limit).toBe(OCCURRENCE_CHECK_LIMIT);
    expect(OCCURRENCE_CHECK_LIMIT).toMatch(/different student at the same location and rank/);
  });
  it("refuses a reference path outside the repository", () => {
    expect(() => loadFleetReference({ manifestPath: path.resolve("C:/elsewhere/run_manifest.json"), wavesDir: WAVES_DIR, root: process.cwd() })).toThrow();
  });
});

describe("N2/N3: the run README template", () => {
  const template = fs.readFileSync(path.resolve(process.cwd(), "docs/designs/WP_E10_RUN_README_TEMPLATE.md"), "utf8");
  it("repeats the exact limit of the occurrence check that the manifest records", () => {
    expect(template).toContain(OCCURRENCE_CHECK_LIMIT);
  });
  it("P-1: prescribes one fresh detached worktree per run, the pinned merged commit, and never relaxes the dirty check", () => {
    expect(template).toMatch(/each run .* gets its own fresh detached worktree at the pinned commit/);
    expect(template).toContain("git worktree add <run-worktree> <pin> --detach");
    expect(template).toMatch(/never relaxed and the output directory is never excluded/);
    expect(template).toContain("rule_e_second_run_<date>/");
  });
  it("says that a write-time archive schema failure aborts the whole campaign", () => {
    expect(template).toMatch(/schema failure aborts the whole campaign/);
    expect(template).toMatch(/fail closed/);
  });
});
