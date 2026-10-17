import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import net from "node:net";
import path from "node:path";
import {
  RATE_LIMIT_WINDOW_ENV, assertLogOutsideRepo, buildSessionEnv, healthOk, installSignalHandlers, isPortFree, parseSessionArgs, runSession,
} from "./run-fleet-rerun-session.mjs";

const ROOT = path.resolve("repo-root-fixture");
const OUTSIDE_LOG = path.join(path.dirname(ROOT), "elsewhere", "optimizer.log");
const INSIDE = JSON.stringify({
  uniride_core: path.join(ROOT, "uniride_core", "__init__.py"), optimizer_api: path.join(ROOT, "optimizer_api", "__init__.py"),
  academic_benchmark: path.join(ROOT, "academic_benchmark", "__init__.py"),
});
const HEALTHY = async () => ({ status: 200, text: JSON.stringify({ status: "ok", message: "UniRide Optimization Engine is running." }) });
const args = (log = OUTSIDE_LOG, port = 18011) => ["--port", String(port), "--log", log, "--", "--preflight-only", "--week-of", "2026-10-05"];

/** A fake spawn: nothing real is ever started. The first call is the optimizer, the second the run. */
function fakeSpawn({ errorOnOptimizer = false, cliHangs = false, cliExit = 0 } = {}) {
  const calls = [];
  const spawn = (command, spawnArgs, options) => {
    const child = new EventEmitter();
    child.pid = 5000 + calls.length;
    child.exitCode = null;
    child.killed = false;
    calls.push({ command, args: spawnArgs, options, child });
    if (calls.length === 1 && errorOnOptimizer) setImmediate(() => child.emit("error", new Error("spawn ENOENT")));
    if (calls.length === 2 && !cliHangs) setImmediate(() => { child.exitCode = cliExit; child.emit("exit", cliExit); });
    return child;
  };
  spawn.calls = calls;
  return spawn;
}
function deps(over = {}) {
  const stopped = [];
  const synced = [];
  const logged = [];
  const exits = [];
  const emitter = new EventEmitter();
  return {
    stopped, emitter, exits, synced, logged,
    spawnSync: (command, spawnArgs, options) => { synced.push({ command, args: spawnArgs, options }); return { status: 0, stdout: over.provenance ?? INSIDE }; },
    writeLog: (fd, text) => { logged.push(text); },
    spawn: over.spawn ?? fakeSpawn(), isPortFree: async () => true, probeHealth: HEALTHY, sleep: () => new Promise((resolve) => setImmediate(resolve)),
    healthTimeoutMs: 50, openLog: () => 99, closeLog: () => {}, stopTree: (child) => { if (child) stopped.push(child.pid); },
    exit: (code) => { exits.push(code); }, log: () => {}, ...over,
  };
}

test("session arguments: port, log and everything after -- go to the run", () => {
  assert.deepEqual(parseSessionArgs(["--port", "8011", "--log", "x.log", "--", "--preflight-only", "--week-of", "2026-10-05"]),
    { port: 8011, log: "x.log", cli: ["--preflight-only", "--week-of", "2026-10-05"] });
  for (const bad of [[], ["--port", "8011", "--log", "x"], ["--port", "80", "--log", "x", "--", "a"], ["--port", "8011", "--", "a"],
    ["--port", "8011", "--port", "8012", "--log", "x", "--", "a"], ["--port", "8011", "--log", "--", "a"], ["--port", "8011", "--log", "x", "--"]]) {
    assert.throws(() => parseSessionArgs(bad), undefined, JSON.stringify(bad));
  }
});

test("a log path inside the repository is refused, one outside is accepted", () => {
  assert.throws(() => assertLogOutsideRepo(path.join(ROOT, "optimizer.log"), ROOT));
  assert.throws(() => assertLogOutsideRepo(path.join(ROOT, ".temp", "x", "optimizer.log"), ROOT));
  assert.throws(() => assertLogOutsideRepo(ROOT, ROOT));
  assert.doesNotThrow(() => assertLogOutsideRepo(OUTSIDE_LOG, ROOT));
  assert.doesNotThrow(() => assertLogOutsideRepo(path.join(path.dirname(ROOT), "repo-root-fixture-2", "optimizer.log"), ROOT));
});

test("/health is accepted only with HTTP 200 and the optimizer's own body", () => {
  const body = JSON.stringify({ status: "ok", message: "UniRide Optimization Engine is running.", version: "3.1.0" });
  assert.equal(healthOk(200, body), true);
  assert.equal(healthOk(204, body), false);
  assert.equal(healthOk(503, body), false);
  assert.equal(healthOk(200, "<html>another app</html>"), false);
  assert.equal(healthOk(200, JSON.stringify({ status: "ok" })), false);
  assert.equal(healthOk(200, JSON.stringify({ status: "ok", message: "something else" })), false);
});

test("a port that is already in use is detected (real socket on a spare port)", async () => {
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  assert.equal(await isPortFree(port), false);
  await new Promise((resolve) => server.close(resolve));
  assert.equal(await isPortFree(port), true);
});

test("runSession refuses before it spawns anything: a log inside the repo, a missing interpreter, a busy port", async () => {
  for (const [argv, env, over, pattern] of [
    [args(path.join(ROOT, "x.log")), { UNIRIDE_PYTHON: "py" }, {}, /outside the repository/],
    [args(), {}, {}, /UNIRIDE_PYTHON/],
    [args(), { UNIRIDE_PYTHON: "py" }, { isPortFree: async () => false }, /already in use/],
  ]) {
    const d = deps(over);
    await assert.rejects(() => runSession(argv, env, ROOT, d), pattern);
    assert.equal(d.spawn.calls.length, 0, "nothing may be spawned");
  }
});

test("a wrong interpreter fails fast with a clear message and does not wait for the health timeout", async () => {
  // a short health timeout: a regression (no 'error' handler) fails after 2 s with another message, not after the 60 s node test timeout
  const d = deps({ spawn: fakeSpawn({ errorOnOptimizer: true }), probeHealth: async () => null, healthTimeoutMs: 2_000 });
  const started = Date.now();
  await assert.rejects(() => runSession(args(), { UNIRIDE_PYTHON: "no-such-python" }, ROOT, d), /could not start the optimizer.*UNIRIDE_PYTHON/i);
  assert.ok(Date.now() - started < 2000, "must not wait for the 60 s timeout");
  assert.equal(d.spawn.calls.length, 1, "the run is never started");
  assert.deepEqual(d.stopped, [5000]); // only the process the session itself tried to start
});

test("an unhealthy optimizer (another app answers /health) stops the session without starting the run", async () => {
  const d = deps({ probeHealth: async () => ({ status: 200, text: "<html>another app</html>" }), healthTimeoutMs: 20 });
  await assert.rejects(() => runSession(args(), { UNIRIDE_PYTHON: "py" }, ROOT, d), /healthy/);
  assert.equal(d.spawn.calls.length, 1);
  assert.deepEqual(d.stopped, [5000]);
});

test("a full session starts the optimizer, then the run with the same key, port and interpreter, and stops only its own processes", async () => {
  const d = deps({ spawn: fakeSpawn({ cliExit: 7 }) });
  const code = await runSession(args(), { UNIRIDE_PYTHON: "py", PATH: "p" }, ROOT, d);
  assert.equal(code, 7);
  const [optimizer, cli] = d.spawn.calls;
  assert.equal(optimizer.command, "py");
  assert.equal(optimizer.options.env.OPTIMIZER_PORT, "18011");
  assert.equal(optimizer.options.env.UNIRIDE_RATE_LIMIT_WINDOW_SECONDS, "1");
  assert.deepEqual(cli.args.slice(-3), ["--preflight-only", "--week-of", "2026-10-05"]);
  assert.ok(cli.args.includes("scripts/run-fleet-scenarios.ts"));
  assert.equal(cli.options.env.OPTIMIZER_INTERNAL_API_KEY, optimizer.options.env.INTERNAL_API_KEY);
  assert.equal(cli.options.env.UNIRIDE_PYTHON, "py");
  assert.deepEqual([...d.stopped].sort(), [optimizer.child.pid, cli.child.pid].sort()); // exactly the two it started, nothing else
});

test("SIGINT during the run stops the optimizer and the run it started, exits 130 and leaves no handler behind", async () => {
  const d = deps({ spawn: fakeSpawn({ cliHangs: true }) });
  const session = runSession(args(), { UNIRIDE_PYTHON: "py" }, ROOT, d);
  await new Promise((resolve) => setTimeout(resolve, 30)); // the run child exists and hangs
  assert.equal(d.spawn.calls.length, 2);
  assert.equal(d.emitter.listenerCount("SIGINT"), 1);
  d.emitter.emit("SIGINT");
  assert.deepEqual([...d.stopped].sort(), [5000, 5001]);
  assert.deepEqual(d.exits, [130]);
  d.spawn.calls[1].child.emit("exit", 130);
  await session;
  assert.equal(d.emitter.listenerCount("SIGINT"), 0);
  assert.equal(d.emitter.listenerCount("SIGTERM"), 0);
});

test("installSignalHandlers: both signals call stop once with its own targets and then exit 130; uninstall removes them", () => {
  const emitter = new EventEmitter();
  const stopped = [];
  const exits = [];
  const uninstall = installSignalHandlers({ emitter, stop: () => stopped.push("stop"), exit: (code) => exits.push(code), log: () => {} });
  assert.equal(emitter.listenerCount("SIGINT"), 1);
  assert.equal(emitter.listenerCount("SIGTERM"), 1);
  emitter.emit("SIGTERM");
  assert.deepEqual([stopped, exits], [["stop"], [130]]);
  uninstall();
  assert.equal(emitter.listenerCount("SIGINT") + emitter.listenerCount("SIGTERM"), 0);
});

test("P-provenance: the Python modules must resolve inside the run worktree, checked with the optimizer's interpreter, env and cwd before anything is spawned", async () => {
  const d = deps();
  await runSession(args(), { UNIRIDE_PYTHON: "py", PYTHONPATH: "other" }, ROOT, d);
  assert.equal(d.synced.length, 1);
  const [check] = d.synced;
  assert.equal(check.command, "py");
  assert.equal(check.args[0], "-c");
  assert.ok(!check.args[1].includes("\n"), "python -c must be one line");
  for (const name of ["uniride_core", "optimizer_api", "academic_benchmark"]) assert.ok(check.args[1].includes(name));
  assert.equal(check.options.cwd, path.join(ROOT, "optimizer_api"));
  assert.equal(check.options.env.PYTHONPATH, [ROOT, "other"].join(path.delimiter));
  assert.equal(d.spawn.calls[0].options.env.PYTHONPATH, check.options.env.PYTHONPATH); // the optimizer gets the very same env
  assert.equal(d.spawn.calls[1].options.env.PYTHONPATH, check.options.env.PYTHONPATH); // and so does the run (its Python capture)
  // the resolved, repo-relative result goes to the log; no absolute path
  const line = d.logged.join("");
  assert.ok(line.includes('"uniride_core":"uniride_core/__init__.py"'), line);
  assert.ok(!line.includes(ROOT));
});

test("a module that resolves outside the run worktree (editable install of another checkout) refuses the run before any spawn", async () => {
  const outside = JSON.stringify({ uniride_core: path.join(path.dirname(ROOT), "main-checkout", "uniride_core", "__init__.py"),
    optimizer_api: path.join(ROOT, "optimizer_api", "__init__.py"), academic_benchmark: path.join(ROOT, "academic_benchmark", "__init__.py") });
  const d = deps({ provenance: outside });
  await assert.rejects(() => runSession(args(), { UNIRIDE_PYTHON: "py" }, ROOT, d), /uniride_core.*outside the run worktree/);
  assert.equal(d.spawn.calls.length, 0);
  assert.equal(d.synced.length, 1);
});

test("a failing or unreadable provenance check refuses the run before any spawn", async () => {
  for (const answer of [{ status: 1, stdout: "" }, { status: 0, stdout: "not json" }, { status: 0, stdout: JSON.stringify({ uniride_core: "x" }) }]) {
    const d = deps({ spawnSync: () => answer });
    await assert.rejects(() => runSession(args(), { UNIRIDE_PYTHON: "py" }, ROOT, d), /provenance/i);
    assert.equal(d.spawn.calls.length, 0);
  }
});

test("one environment for both processes: same interpreter, shared key, lowered window, nothing else touched", () => {
  const parent = { PATH: "p", SUPABASE_SERVICE_ROLE_KEY: "secret-value", UNIRIDE_COMPUTE_MAX_ITERATIONS: "700" };
  const env = buildSessionEnv(parent, "k".repeat(64), 8011, "C:/py/python.exe", ROOT);
  assert.equal(env.PYTHONPATH, ROOT); // the run worktree first: the editable install of another checkout must not win
  assert.equal(buildSessionEnv({ PYTHONPATH: "a" }, "k", 8011, "py", ROOT).PYTHONPATH, [ROOT, "a"].join(path.delimiter));
  assert.equal(env.UNIRIDE_PYTHON, "C:/py/python.exe");
  assert.equal(env.OPTIMIZER_PORT, "8011");
  assert.equal(env.OPTIMIZER_API_URL, "http://127.0.0.1:8011");
  assert.equal(env.OPTIMIZER_INTERNAL_API_KEY, env.INTERNAL_API_KEY);
  assert.equal(env[RATE_LIMIT_WINDOW_ENV], "1");
  assert.equal(env.UNIRIDE_RATE_LIMIT_REQUESTS, undefined);
  assert.equal(env.UNIRIDE_COMPUTE_MAX_ITERATIONS, "700");
  assert.equal(env.SUPABASE_SERVICE_ROLE_KEY, "secret-value");
  assert.deepEqual(Object.keys(parent).sort(), ["PATH", "SUPABASE_SERVICE_ROLE_KEY", "UNIRIDE_COMPUTE_MAX_ITERATIONS"]); // parent untouched
});
