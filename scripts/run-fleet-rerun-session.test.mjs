import test from "node:test";
import assert from "node:assert/strict";
import net from "node:net";
import path from "node:path";
import {
  RATE_LIMIT_WINDOW_ENV, assertLogOutsideRepo, buildSessionEnv, healthOk, isPortFree, parseSessionArgs, runSession,
} from "./run-fleet-rerun-session.mjs";

test("session arguments: port, log and everything after -- go to the run", () => {
  assert.deepEqual(parseSessionArgs(["--port", "8011", "--log", "x.log", "--", "--preflight-only", "--week-of", "2026-10-05"]),
    { port: 8011, log: "x.log", cli: ["--preflight-only", "--week-of", "2026-10-05"] });
  for (const bad of [[], ["--port", "8011", "--log", "x"], ["--port", "80", "--log", "x", "--", "a"], ["--port", "8011", "--", "a"],
    ["--port", "8011", "--port", "8012", "--log", "x", "--", "a"], ["--port", "8011", "--log", "--", "a"], ["--port", "8011", "--log", "x", "--"]]) {
    assert.throws(() => parseSessionArgs(bad), undefined, JSON.stringify(bad));
  }
});

test("a log path inside the repository is refused, one outside is accepted", () => {
  const root = path.resolve("repo-root-fixture");
  assert.throws(() => assertLogOutsideRepo(path.join(root, "optimizer.log"), root));
  assert.throws(() => assertLogOutsideRepo(path.join(root, ".temp", "x", "optimizer.log"), root));
  assert.throws(() => assertLogOutsideRepo(root, root));
  assert.doesNotThrow(() => assertLogOutsideRepo(path.join(path.dirname(root), "elsewhere", "optimizer.log"), root));
  assert.doesNotThrow(() => assertLogOutsideRepo(path.join(path.dirname(root), "repo-root-fixture-2", "optimizer.log"), root));
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

test("a port that is already in use is detected", async () => {
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  assert.equal(await isPortFree(port), false);
  await new Promise((resolve) => server.close(resolve));
  assert.equal(await isPortFree(port), true);
});

test("runSession refuses before starting anything: a log inside the repo, a missing interpreter, a busy port", async () => {
  const root = path.resolve("repo-root-fixture");
  const args = (log, port = 18011) => ["--port", String(port), "--log", log, "--", "--preflight-only"];
  await assert.rejects(() => runSession(args(path.join(root, "x.log")), { UNIRIDE_PYTHON: "py" }, root), /outside the repository/);
  await assert.rejects(() => runSession(args(path.join(path.dirname(root), "x.log")), {}, root), /UNIRIDE_PYTHON/);
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  await assert.rejects(() => runSession(args(path.join(path.dirname(root), "x.log"), port), { UNIRIDE_PYTHON: "py" }, root), /already in use/);
  await new Promise((resolve) => server.close(resolve));
});

test("one environment for both processes: same interpreter, shared key, lowered window, nothing else touched", () => {
  const parent = { PATH: "p", SUPABASE_SERVICE_ROLE_KEY: "secret-value", UNIRIDE_COMPUTE_MAX_ITERATIONS: "700" };
  const env = buildSessionEnv(parent, "k".repeat(64), 8011, "C:/py/python.exe");
  assert.equal(env.UNIRIDE_PYTHON, "C:/py/python.exe");
  assert.equal(env.OPTIMIZER_PORT, "8011");
  assert.equal(env.OPTIMIZER_API_URL, "http://127.0.0.1:8011");
  assert.equal(env.OPTIMIZER_INTERNAL_API_KEY, env.INTERNAL_API_KEY);
  assert.equal(env[RATE_LIMIT_WINDOW_ENV], "1");
  assert.equal(env.UNIRIDE_RATE_LIMIT_REQUESTS, undefined); // the requests ceiling (30) cannot be raised, so it is left alone
  assert.equal(env.UNIRIDE_COMPUTE_MAX_ITERATIONS, "700"); // no other compute-policy variable is changed
  assert.equal(env.SUPABASE_SERVICE_ROLE_KEY, "secret-value"); // passed on, never printed
  assert.deepEqual(Object.keys(parent).sort(), ["PATH", "SUPABASE_SERVICE_ROLE_KEY", "UNIRIDE_COMPUTE_MAX_ITERATIONS"]); // parent untouched
});
