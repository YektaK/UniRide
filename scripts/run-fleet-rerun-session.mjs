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
 */
import { spawn, spawnSync } from "node:child_process";
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

/** One environment for both processes: the same UNIRIDE_PYTHON, the shared ephemeral key, the lowered rate-limit window. */
export function buildSessionEnv(parent, key, port, python) {
  const env = buildPythonEnv(parent, key);
  env.UNIRIDE_PYTHON = python;
  env.OPTIMIZER_PORT = String(port);
  env.OPTIMIZER_API_URL = `http://127.0.0.1:${port}`;
  env[RATE_LIMIT_WINDOW_ENV] = RATE_LIMIT_WINDOW_SECONDS;
  return env;
}

function stopTree(child) {
  if (!child || child.exitCode !== null || child.killed) return;
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else child.kill("SIGTERM");
}

async function waitForHealth(port, isAlive) {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS;
  while (Date.now() < deadline && isAlive()) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(2000) });
      if (healthOk(response.status, await response.text())) return true;
    } catch { /* not up yet */ }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return false;
}

export async function runSession(argv, parentEnv = process.env, repoRoot = process.cwd()) {
  const { port, log, cli } = parseSessionArgs(argv);
  assertLogOutsideRepo(log, repoRoot);
  const python = parentEnv.UNIRIDE_PYTHON;
  if (!python) throw new Error("Set UNIRIDE_PYTHON: one interpreter serves both the optimizer and the CLI");
  if (!(await isPortFree(port))) throw new Error(`Port ${port} is already in use; choose another --port`);

  const key = generateEphemeralKey();
  const optimizerEnv = buildSessionEnv(parentEnv, key, port, python);
  const command = pythonCommand(python);
  const logFd = fs.openSync(log, "a");
  const optimizer = spawn(command.command, command.args, {
    cwd: path.join(repoRoot, command.cwd), env: optimizerEnv, stdio: ["ignore", logFd, logFd], windowsHide: true,
  });
  console.log(`optimizer started: PID ${optimizer.pid}, port ${port}, log ${path.basename(log)}`);
  let cliChild = null;
  const stopAll = () => { stopTree(cliChild); stopTree(optimizer); };
  for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { stopAll(); console.log(`${signal}: optimizer PID ${optimizer.pid} stopped`); process.exit(130); });
  let code = 1;
  try {
    if (!(await waitForHealth(port, () => optimizer.exitCode === null))) throw new Error("The optimizer did not report a healthy /health in time");
    console.log("optimizer healthy; starting the run");
    cliChild = spawn(process.execPath, ["--conditions=react-server", "--import", "tsx", "scripts/run-fleet-scenarios.ts", ...cli], {
      cwd: repoRoot, env: buildChildEnv(optimizerEnv, key), stdio: "inherit", windowsHide: true,
    });
    code = await new Promise((resolve) => { cliChild.on("exit", (exit) => resolve(exit ?? 1)); cliChild.on("error", () => resolve(1)); });
  } finally {
    stopAll();
    console.log(`optimizer PID ${optimizer.pid} stopped`);
    fs.closeSync(logFd);
  }
  return code;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  runSession(process.argv.slice(2)).then((code) => { process.exitCode = code; }, (error) => {
    console.error(`[fleet-rerun-session] ${error?.message ?? "failed"}`);
    process.exitCode = 1;
  });
}
