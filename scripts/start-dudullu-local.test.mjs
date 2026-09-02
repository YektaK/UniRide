import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  KeyMismatchError,
  WEB_KEY_NAME,
  PYTHON_KEY_NAME,
  parseEnvFile,
  envFileNames,
  generateEphemeralKey,
  resolveSharedKey,
  buildChildEnv,
  pythonCommand,
  webCommand,
  resolvePythonBin,
  probeWebRunner,
  treeKillArgs,
} from "./start-dudullu-local.mjs";

test("matching configured keys are accepted", () => {
  const result = resolveSharedKey({ web: "shared-secret", python: "shared-secret" });
  assert.equal(result.key, "shared-secret");
  assert.equal(result.configured, true);
});

test("mismatched configured keys fail without including either value", () => {
  let error;
  try {
    resolveSharedKey({ web: "secret-A", python: "secret-B" });
  } catch (caught) {
    error = caught;
  }
  assert.ok(error instanceof KeyMismatchError);
  assert.equal(error.code, "mismatch");
  assert.ok(!error.message.includes("secret-A"));
  assert.ok(!error.message.includes("secret-B"));
});

test("one configured side is copied only into the child-process environment", () => {
  const { key, configured } = resolveSharedKey({ web: "only-web-secret", python: undefined });
  assert.equal(configured, true);
  assert.equal(key, "only-web-secret");

  const env = buildChildEnv({ PATH: "/bin" }, key);
  assert.equal(Object.keys(env).length, 3);
  const valuesEqual = Object.values(env).filter((value) => value === key);
  assert.equal(valuesEqual.length, 2);
});

test("neither side configured produces an ephemeral cryptographically random shared key without writing a file", () => {
  const marker = path.join(process.cwd(), "uniride-dev-shared.key");
  assert.equal(fs.existsSync(marker), false);

  const first = resolveSharedKey({ web: undefined, python: undefined });
  const second = resolveSharedKey({ web: undefined, python: undefined });

  assert.equal(first.configured, false);
  assert.match(first.key, /^[0-9a-f]{64}$/);
  assert.notEqual(first.key, second.key);

  fs.rmSync(marker, { force: true });
  assert.equal(fs.existsSync(marker), false);
});

test("env parsing ignores comments and blanks and diagnostics never return values", () => {
  const parsed = parseEnvFile(
    [
      "# a comment",
      "",
      "   ",
      "INTERNAL_API_KEY=abc",
      "OPTIMIZER_INTERNAL_API_KEY=def",
      "OPTIMIZER_API_URL=http://127.0.0.1:8000 # trailing comment stays a value",
      "=",
      "UNIRIDE_PYTHON=x",
    ].join("\n"),
  );

  assert.equal(parsed.get("INTERNAL_API_KEY"), "abc");
  assert.equal(parsed.get("OPTIMIZER_INTERNAL_API_KEY"), "def");
  assert.equal(parsed.get("UNIRIDE_PYTHON"), "x");

  const names = envFileNames(parsed);
  assert.deepEqual(names, [
    "INTERNAL_API_KEY",
    "OPTIMIZER_API_URL",
    "OPTIMIZER_INTERNAL_API_KEY",
    "UNIRIDE_PYTHON",
  ]);
  const rendered = JSON.stringify(names);
  assert.ok(!rendered.includes("abc"));
  assert.ok(!rendered.includes("def"));
});

test("child environment contains both key names with the same value", () => {
  const { key } = resolveSharedKey({ web: undefined, python: undefined });
  const env = buildChildEnv({ NODE_ENV: "development" }, key);

  assert.equal(env[WEB_KEY_NAME], key);
  assert.equal(env[PYTHON_KEY_NAME], key);
  assert.equal(env.NODE_ENV, "development");
  assert.equal(Object.values(env).filter((value) => value === key).length, 2);
});

test("command and diagnostic rendering never contains the key", () => {
  const secret = "render-me-not-9f2a";
  const { key } = resolveSharedKey({ web: secret, python: secret });

  const python = pythonCommand("python");
  const web = webCommand();
  const diagnostic = JSON.stringify({ python, web });

  assert.equal(python.args.includes(secret), false);
  assert.equal(JSON.stringify(web).includes(secret), false);
  assert.ok(!diagnostic.includes(secret));
});

test("generateEphemeralKey returns distinct random hex values", () => {
  const first = generateEphemeralKey();
  const second = generateEphemeralKey();
  assert.match(first, /^[0-9a-f]{64}$/);
  assert.match(second, /^[0-9a-f]{64}$/);
  assert.notEqual(first, second);
});

test("pythonCommand pins main.py into the optimizer_api working directory", () => {
  const python = pythonCommand("/venv/python.exe");
  assert.deepEqual(python, {
    command: "/venv/python.exe",
    args: ["main.py"],
    cwd: "optimizer_api",
  });
});

test("webCommand selects npm.cmd with a Windows shell and plain npm elsewhere", () => {
  const win = webCommand("win32");
  assert.equal(win.command, "npm.cmd");
  assert.equal(win.shell, true);
  assert.deepEqual(win.args, ["run", "dev"]);
  assert.equal(win.cwd, ".");

  const posix = webCommand("linux");
  assert.equal(posix.command, "npm");
  assert.equal(posix.shell, false);
});

test("resolvePythonBin honors UNIRIDE_PYTHON then .venv then PATH python", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "uniride-python-"));
  try {
    const venv = path.join(root, ".venv", "Scripts", "python.exe");
    fs.mkdirSync(path.dirname(venv), { recursive: true });
    fs.writeFileSync(venv, "");
    assert.equal(
      resolvePythonBin({ PATH: process.env.PATH }, root),
      venv,
    );

    const explicit = path.join(root, "custom-python.exe");
    fs.writeFileSync(explicit, "");
    assert.equal(
      resolvePythonBin({ UNIRIDE_PYTHON: explicit, PATH: process.env.PATH }, root),
      explicit,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }

  const pathBin = resolvePythonBin({ PATH: process.env.PATH }, root);
  assert.ok(pathBin !== null && fs.existsSync(pathBin));
});

test("probeWebRunner succeeds for a real command and fails for a missing one", async () => {
  const ok = await probeWebRunner(
    { command: process.execPath, shell: false },
    ["--version"],
  );
  assert.equal(ok, true);

  const missing = await probeWebRunner(
    { command: "definitely-not-a-real-binary-9f2a", shell: false },
    ["--version"],
  );
  assert.equal(missing, false);
});

test("treeKillArgs emits a taskkill process-tree kill on win32 and null elsewhere", () => {
  const args = treeKillArgs(1234);
  if (process.platform === "win32") {
    assert.deepEqual(args, ["/pid", "1234", "/T", "/F"]);
  } else {
    assert.equal(args, null);
  }
});

// ── Readiness lifecycle: all-three gate, bounded probes, spawn cleanup ──

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

test("allServicesReady is true only when all three readiness checks pass", async () => {
  const { allServicesReady } = await import("./start-dudullu-local.mjs");
  assert.equal(
    allServicesReady({ fastapiHealth: true, webListener: true, handshake: true }),
    true,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: true, webListener: true, handshake: false }),
    false,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: true, webListener: false, handshake: true }),
    false,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: false, webListener: true, handshake: true }),
    false,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: true, webListener: true, handshake: undefined }),
    false,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: true, webListener: true }),
    false,
  );
  assert.equal(
    allServicesReady({ fastapiHealth: false, webListener: false, handshake: false }),
    false,
  );
});

test("waitForServices never announces both services on a handshake-only state and announces only after all three pass", async () => {
  const { waitForServices } = await import("./start-dudullu-local.mjs");
  const writes = [];
  const state = { fastapi: false, web: false, handshake: false };
  const pending = waitForServices("k", {
    checkService: async (url) =>
      url.includes("/health") ? state.fastapi : state.web,
    checkHandshake: async () => state.handshake,
    write: (text) => writes.push(text),
    pollIntervalMs: 2,
  });

  state.handshake = true;
  await sleep(30);
  assert.ok(
    !writes.some((line) => line.includes("both services running")),
    "handshake alone must never announce both services",
  );
  assert.ok(
    writes.some((line) => line.includes("optimizer internal readiness handshake: UP")),
  );

  state.fastapi = true;
  state.web = true;
  await pending;
  assert.ok(writes.some((line) => line.includes("both services running")));
  assert.ok(
    writes.indexOf("[uniride-local] optimizer /health: UP\n") <
      writes.indexOf("[uniride-local] both services running. Press Ctrl+C to stop.\n"),
  );
});

test("checkService imposes a bounded timeout on public /health and preserves the web probe signal", async () => {
  const { checkService } = await import("./start-dudullu-local.mjs");

  let healthInit;
  const ok = await checkService(
    "http://127.0.0.1:8000/health",
    undefined,
    (url, init) => {
      healthInit = init;
      return Promise.resolve(new Response(null, { status: 200 }));
    },
  );
  assert.equal(ok, true);
  assert.ok(healthInit.signal instanceof AbortSignal, "public /health must get a signal");

  const webSignal = AbortSignal.timeout(123);
  let webInit;
  const webOk = await checkService(
    "http://127.0.0.1:9002",
    { signal: webSignal },
    (url, init) => {
      webInit = init;
      return Promise.resolve(new Response(null, { status: 200 }));
    },
  );
  assert.equal(webOk, true);
  assert.equal(webInit.signal, webSignal);
});

test("checkHandshake stays bounded and rejects non-optimizer bodies", async () => {
  const { checkHandshake } = await import("./start-dudullu-local.mjs");
  let seenInit;
  const ok = await checkHandshake("secret", (url, init) => {
    seenInit = init;
    return Promise.resolve(
      new Response(JSON.stringify({ service: "optimizer", internal: "ok" }), {
        status: 200,
      }),
    );
  });
  assert.equal(ok, true);
  assert.ok(seenInit.signal instanceof AbortSignal, "handshake probe must stay bounded");

  const bad = await checkHandshake("secret", () =>
    Promise.resolve(new Response(JSON.stringify({ service: "other" }), { status: 200 })),
  );
  assert.equal(bad, false);
});

test("web spawn failure terminates the already-started python child and never reaches readiness", async () => {
  const { startStack } = await import("./start-dudullu-local.mjs");
  const pythonProc = { pid: 4242, exited: false, kill() {}, on() {} };
  const killed = [];
  const unexpected = [];
  let spawnCalls = 0;

  const spawnFn = (command, args, init) => {
    spawnCalls += 1;
    if (spawnCalls === 1) {
      return pythonProc;
    }
    throw new Error("simulated synchronous web spawn failure");
  };

  let caught;
  try {
    startStack(
      {
        pythonBin: "/venv/python.exe",
        web: { command: "npm.cmd", args: ["run", "dev"], cwd: ".", shell: true },
        rootDir: "C:/tmp",
        shared: { key: "not-printed" },
        onError: () => {},
        onUnexpectedExit: (name) => (code, signal) =>
          unexpected.push({ name, code, signal }),
      },
      { spawnFn, killEntry: (entry, force) => killed.push({ pid: entry.proc.pid, force }) },
    );
  } catch (error) {
    caught = error;
  }

  assert.ok(caught instanceof Error);
  assert.match(caught.message, /web spawn failure/);
  assert.equal(spawnCalls, 2, "web spawn was attempted after python started");
  assert.deepEqual(killed, [{ pid: 4242, force: true }]);
  assert.deepEqual(unexpected, [], "no exit/error callbacks may fire for a torn-down child");
});

test("failed web spawn prevents any both-services announcement in main ordering", async () => {
  const { startStack, waitForServices } = await import("./start-dudullu-local.mjs");
  const writes = [];
  let thrown;
  const spawnFn = (command, args, init) => {
    throw new Error("web unavailable at spawn time");
  };
  try {
    startStack(
      {
        pythonBin: "/venv/python.exe",
        web: { command: "npm.cmd", args: ["run", "dev"], cwd: ".", shell: true },
        rootDir: "C:/tmp",
        shared: { key: "k" },
        onError: () => {},
        onUnexpectedExit: () => () => {},
      },
      { spawnFn, killEntry: () => {} },
    );
    await waitForServices("k", {
      checkService: async () => false,
      checkHandshake: async () => false,
      write: (text) => writes.push(text),
      pollIntervalMs: 1,
    });
  } catch (error) {
    thrown = error;
  }
  assert.ok(thrown instanceof Error);
  assert.ok(
    !writes.some((line) => line.includes("both services running")),
    "failed spawn must never reach the readiness announcer",
  );
});

test("terminateChildren kills each live child exactly once and skips exited children", async () => {
  const { terminateChildren } = await import("./start-dudullu-local.mjs");
  const liveA = { proc: { pid: 1 }, exited: false };
  const liveB = { proc: { pid: 2 }, exited: false };
  const exitedC = { proc: { pid: 3 }, exited: true };

  const softCalls = [];
  terminateChildren([liveA, liveB, exitedC], false, (entry, force) =>
    softCalls.push({ pid: entry.proc.pid, force }),
  );
  assert.deepEqual(softCalls.sort((a, b) => a.pid - b.pid), [
    { pid: 1, force: false },
    { pid: 2, force: false },
  ]);

  const forceCalls = [];
  terminateChildren([liveA], true, (entry, force) =>
    forceCalls.push({ pid: entry.proc.pid, force }),
  );
  assert.deepEqual(forceCalls, [{ pid: 1, force: true }]);
});