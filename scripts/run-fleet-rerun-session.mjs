/**
 * One session of the WP-E10 fleet re-run: starts ONLY the optimizer API (from this checkout, on a spare port, with an
 * ephemeral shared key and the rate limit window lowered), runs scripts/run-fleet-scenarios.ts against it, and stops
 * exactly the optimizer process tree it started. Node standard library plus the repo launcher's building blocks.
 *
 * Environment (Supabase credentials) arrives through Node's own flag, by path, never copied and never printed:
 *   UNIRIDE_PYTHON=<python> node --env-file=<main>/optimizer_api/.env --env-file=<main>/.env.local \
 *     scripts/run-fleet-rerun-session.mjs --port 8011 --log <file outside the repo> -- <run-fleet-scenarios arguments>
 *
 * Rate limit (lead decision, DECISION_LOG E05): the optimizer's hard ceiling is 30 requests per window and cannot be
 * raised, so the window is lowered to 1 second (30 requests per second). The campaign is sequential and each GA call
 * takes seconds, so no request is ever rejected. No other compute-policy variable is touched. The run records the
 * effective values (manifest compute_policy and optimizer_policy).
 *
 * Every effect of `runSession` (spawn, port probe, health probe, log file, process-tree stop, signals, exit) is
 * injectable, so the tests never start a real interpreter and cannot hang.
 */
import { spawn as nodeSpawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { buildChildEnv, buildPythonEnv, generateEphemeralKey, pythonCommand } from "./start-dudullu-local.mjs";

export const RATE_LIMIT_WINDOW_ENV = "UNIRIDE_RATE_LIMIT_WINDOW_SECONDS";
export const RATE_LIMIT_WINDOW_SECONDS = "1";
export const HEALTH_TIMEOUT_MS = 90_000;

export function parseSessionArgs(argv) {
  const split = argv.indexOf("--");
  if (split === -1) throw new Error("Missing '--' before the run-fleet-scenarios arguments");
  const own = argv.slice(0, split);
  const cli = argv.slice(split + 1);
  const values = new Map();
  for (let i = 0; i < own.length; i += 2) {
    const key = own[i];
    const value = own[i + 1];
    if (!["--port", "--log"].includes(key) || values.has(key) || !value || value.startsWith("--")) throw new Error("Invalid session argument");
    values.set(key, value);
  }
  const port = Number(values.get("--port"));
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("--port must be an integer from 1024 to 65535");
  if (!values.has("--log")) throw new Error("--log is required");
  if (cli.length === 0) throw new Error("No run-fleet-scenarios arguments given");
  return { port, log: values.get("--log"), cli };
}

/** The log may contain request lines of the optimizer: keep it out of the repository so it cannot be committed. */
export function assertLogOutsideRepo(logPath, repoRoot) {
  const relative = path.relative(path.resolve(repoRoot), path.resolve(logPath));
  if (relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative))) throw new Error("The log file must lie outside the repository");
}

export function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => server.close(() => resolve(true)));
    server.listen(port, "127.0.0.1");
  });
}

/** /health counts only with HTTP 200 and the optimizer's own body; any other listener on the port is not accepted. */
export function healthOk(status, bodyText) {
  if (status !== 200) return false;
  try {
    const body = JSON.parse(bodyText);
    return body?.status === "ok" && typeof body.message === "string" && body.message.includes("UniRide Optimization Engine");
  } catch { return false; }
}

/**
 * One environment for both processes: the same UNIRIDE_PYTHON, the shared ephemeral key, the lowered rate-limit window,
 * and the run worktree FIRST on PYTHONPATH. The project venv carries an editable install that maps uniride_core,
 * optimizer_api and academic_benchmark to the main checkout; without this the optimizer (and the CLI's Python capture)
 * would execute the main checkout's code while the manifest names the pinned, clean worktree.
 */
export function buildSessionEnv(parent, key, port, python, repoRoot) {
  const env = buildPythonEnv(parent, key);
  env.PYTHONPATH = parent.PYTHONPATH ? [repoRoot, parent.PYTHONPATH].join(path.delimiter) : repoRoot;
  env.UNIRIDE_PYTHON = python;
  env.OPTIMIZER_PORT = String(port);
  env.OPTIMIZER_API_URL = `http://127.0.0.1:${port}`;
  env[RATE_LIMIT_WINDOW_ENV] = RATE_LIMIT_WINDOW_SECONDS;
  return env;
}

// One line (python -c): where do the three project packages resolve, without importing them.
export const PROVENANCE_MODULES = ["uniride_core", "optimizer_api", "academic_benchmark"];
export const PROVENANCE_ONE_LINER =
  "import json,importlib.util as u;print(json.dumps({n:(u.find_spec(n).origin or list(u.find_spec(n).submodule_search_locations)[0]) for n in "
  + JSON.stringify(PROVENANCE_MODULES).replace(/"/g, "'") + "}))";

/**
 * Refuses the run unless uniride_core, optimizer_api and academic_benchmark resolve inside `repoRoot`, as seen by the
 * optimizer's own interpreter, environment and working directory. Returns the repo-relative POSIX paths.
 */
export function checkPythonProvenance({ python, env, repoRoot, spawnSync: run = spawnSync }) {
  const answer = run(python, ["-c", PROVENANCE_ONE_LINER], {
    cwd: path.join(repoRoot, "optimizer_api"), env, encoding: "utf8", timeout: 60_000, windowsHide: true,
  });
  let found;
  try { found = JSON.parse(answer?.stdout ?? ""); } catch { found = null; }
  if (!answer || answer.status !== 0 || !found) throw new Error("Python provenance check failed: UNIRIDE_PYTHON could not resolve the project packages");
  const resolved = {};
  for (const name of PROVENANCE_MODULES) {
    if (typeof found[name] !== "string") throw new Error(`Python provenance check failed: ${name} was not reported`);
    const relative = path.relative(path.resolve(repoRoot), path.resolve(found[name]));
    if (relative === "" || relative.startsWith("..") || path.isAbsolute(relative)) {
      throw new Error(`Python provenance: ${name} resolves outside the run worktree (an editable install of another checkout?); the run would execute other code than the manifest names`);
    }
    resolved[name] = relative.split(path.sep).join("/");
  }
  return resolved;
}

/** Stops the process tree of a child this session started (never anything else). */
export function stopTree(child) {
  if (!child || child.exitCode !== null || child.killed) return;
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else child.kill("SIGTERM");
}

/**
 * SIGINT/SIGTERM: stop what the session started, then exit 130. `stop` is the session's own closure over its two children;
 * returns a function that removes the handlers again (the session does so when it ends).
 */
export function installSignalHandlers({ emitter = process, stop, exit = (code) => process.exit(code), log = console.log, signals = ["SIGINT", "SIGTERM"] }) {
  const handlers = signals.map((signal) => {
    const handler = () => { stop(); log(`${signal}: the processes of this session were stopped`); exit(130); };
    emitter.on(signal, handler);
    return [signal, handler];
  });
  return () => { for (const [signal, handler] of handlers) emitter.off(signal, handler); };
}

async function waitForHealth(port, d, isAlive) {
  const deadline = Date.now() + d.healthTimeoutMs;
  while (Date.now() < deadline && isAlive()) {
    try {
      const answer = await d.probeHealth(port);
      if (answer && healthOk(answer.status, answer.text)) return true;
    } catch { /* not up yet */ }
    await d.sleep(1000);
  }
  return false;
}

const defaultProbeHealth = async (port) => {
  const response = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(2000) });
  return { status: response.status, text: await response.text() };
};

export async function runSession(argv, parentEnv = process.env, repoRoot = process.cwd(), overrides = {}) {
  const d = {
    spawn: nodeSpawn, isPortFree, probeHealth: defaultProbeHealth, sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    healthTimeoutMs: HEALTH_TIMEOUT_MS, openLog: (file) => fs.openSync(file, "a"), closeLog: (fd) => fs.closeSync(fd), stopTree,
    emitter: process, exit: (code) => process.exit(code), log: console.log, spawnSync, writeLog: (fd, text) => fs.writeSync(fd, text), ...overrides,
  };
  const { port, log, cli } = parseSessionArgs(argv);
  assertLogOutsideRepo(log, repoRoot);
  const python = parentEnv.UNIRIDE_PYTHON;
  if (!python) throw new Error("Set UNIRIDE_PYTHON: one interpreter serves both the optimizer and the CLI");
  if (!(await d.isPortFree(port))) throw new Error(`Port ${port} is already in use; choose another --port`);

  const key = generateEphemeralKey();
  const optimizerEnv = buildSessionEnv(parentEnv, key, port, python, repoRoot);
  const command = pythonCommand(python);
  const logFd = d.openLog(log);
  // Provenance first, with the optimizer's interpreter, env and cwd, before anything is spawned.
  let provenance;
  try { provenance = checkPythonProvenance({ python, env: optimizerEnv, repoRoot, spawnSync: d.spawnSync }); }
  catch (error) { d.closeLog(logFd); throw error; }
  d.writeLog(logFd, `python provenance (repo-relative): ${JSON.stringify(provenance)}\n`);
  d.log(`python provenance: ${JSON.stringify(provenance)}`);
  const optimizer = d.spawn(command.command, command.args, {
    cwd: path.join(repoRoot, command.cwd), env: optimizerEnv, stdio: ["ignore", logFd, logFd], windowsHide: true,
  });
  let startError = null;
  // A wrong UNIRIDE_PYTHON (or any spawn failure) must fail now, not after the 90 s health wait.
  optimizer.on("error", (error) => { startError = error; });
  d.log(`optimizer started: PID ${optimizer.pid}, port ${port}, log ${path.basename(log)}`);
  let cliChild = null;
  const stopAll = () => { d.stopTree(cliChild); d.stopTree(optimizer); };
  const uninstall = installSignalHandlers({ emitter: d.emitter, stop: stopAll, exit: d.exit, log: d.log });
  let code = 1;
  try {
    const healthy = await waitForHealth(port, d, () => optimizer.exitCode === null && startError === null);
    if (startError) throw new Error("Could not start the optimizer; check UNIRIDE_PYTHON (the interpreter must exist and have the optimizer requirements)");
    if (!healthy) throw new Error("The optimizer did not report a healthy /health in time");
    d.log("optimizer healthy; starting the run");
    cliChild = d.spawn(process.execPath, ["--conditions=react-server", "--import", "tsx", "scripts/run-fleet-scenarios.ts", ...cli], {
      cwd: repoRoot, env: buildChildEnv(optimizerEnv, key), stdio: "inherit", windowsHide: true,
    });
    code = await new Promise((resolve) => { cliChild.on("exit", (exit) => resolve(exit ?? 1)); cliChild.on("error", () => resolve(1)); });
  } finally {
    uninstall();
    stopAll();
    d.log(`optimizer PID ${optimizer.pid} stopped`);
    d.closeLog(logFd);
  }
  return code;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  runSession(process.argv.slice(2)).then((code) => { process.exitCode = code; }, (error) => {
    console.error(`[fleet-rerun-session] ${error?.message ?? "failed"}`);
    process.exitCode = 1;
  });
}
