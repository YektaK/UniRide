/**
 * One-command local startup for the Dudullu runtime stack.
 * Node standard library only. Never prints or persists the shared internal key.
 */

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";

export const WEB_KEY_NAME = "OPTIMIZER_INTERNAL_API_KEY";
export const PYTHON_KEY_NAME = "INTERNAL_API_KEY";

const WEB_ENV_FILE = ".env.local";
const PYTHON_ENV_FILE = path.join("optimizer_api", ".env");
const WEB_URL = "http://127.0.0.1:9002";
const FASTAPI_URL = "http://127.0.0.1:8000";
const POLL_INTERVAL_MS = 500;
const PROBE_TIMEOUT_MS = 2_000;

export class KeyMismatchError extends Error {
  constructor() {
    super("Internal API key mismatch between web and FastAPI configuration");
    this.name = "KeyMismatchError";
    this.code = "mismatch";
  }
}

export function parseEnvFile(text) {
  const entries = new Map();
  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) {
      continue;
    }
    const eq = line.indexOf("=");
    if (eq === -1) {
      continue;
    }
    const key = line.slice(0, eq).trim();
    if (key === "") {
      continue;
    }
    entries.set(key, line.slice(eq + 1).trim());
  }
  return entries;
}

export function envFileNames(parsed) {
  return [...parsed.keys()].sort();
}

export function generateEphemeralKey() {
  return crypto.randomBytes(32).toString("hex");
}

export function resolveSharedKey({ web, python }) {
  const webKey =
    typeof web === "string" && web.trim() !== "" ? web.trim() : undefined;
  const pythonKey =
    typeof python === "string" && python.trim() !== "" ? python.trim() : undefined;

  if (webKey !== undefined && pythonKey !== undefined && webKey !== pythonKey) {
    throw new KeyMismatchError();
  }
  if (webKey !== undefined) {
    return { key: webKey, configured: true };
  }
  if (pythonKey !== undefined) {
    return { key: pythonKey, configured: true };
  }
  return { key: generateEphemeralKey(), configured: false };
}

export function buildChildEnv(parent, key) {
  const env = { ...(parent ?? {}) };
  env[WEB_KEY_NAME] = key;
  env[PYTHON_KEY_NAME] = key;
  return env;
}

export function pythonCommand(pythonBin) {
  return { command: pythonBin, args: ["main.py"], cwd: "optimizer_api" };
}

export function webCommand(platform = process.platform) {
  const isWin = platform === "win32";
  return {
    command: isWin ? "npm.cmd" : "npm",
    args: ["run", "dev"],
    cwd: ".",
    shell: isWin,
  };
}

export function probeWebRunner(web, args = ["--version"], timeoutMs = 15_000) {
  return new Promise((resolve) => {
    let child;
    try {
      const shell = Boolean(web.shell);
      const command = shell ? [web.command, ...args].join(" ") : web.command;
      child = spawn(command, shell ? [] : args, {
        stdio: "ignore",
        shell,
      });
    } catch {
      resolve(false);
      return;
    }
    let settled = false;
    let timer;
    const finish = (ok) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(ok);
      }
    };
    timer = setTimeout(() => {
      try {
        child.kill();
      } catch {
        // ignore
      }
      finish(false);
    }, timeoutMs);
    child.on("error", () => finish(false));
    child.on("exit", (code) => finish(code === 0));
  });
}

export function treeKillArgs(pid) {
  if (process.platform !== "win32") {
    return null;
  }
  return ["/pid", String(pid), "/T", "/F"];
}

export function findExecutableOnPath(pathVar, names) {
  if (typeof pathVar !== "string" || pathVar.trim() === "") {
    return null;
  }
  for (const dir of pathVar.split(path.delimiter)) {
    if (dir.trim() === "") {
      continue;
    }
    for (const name of names) {
      const candidate = path.join(dir, name);
      try {
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      } catch {
        // ignore unreadable directory
      }
    }
  }
  return null;
}

function readEnvFileOrEmpty(filePath) {
  try {
    return parseEnvFile(fs.readFileSync(filePath, "utf8"));
  } catch {
    return new Map();
  }
}

export function resolvePythonBin(env, rootDir) {
  const explicit = env.UNIRIDE_PYTHON;
  if (typeof explicit === "string" && explicit.trim() !== "") {
    const candidate = path.isAbsolute(explicit)
      ? explicit
      : path.join(rootDir, explicit);
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  const venvCandidates =
    process.platform === "win32"
      ? [
          path.join(rootDir, ".venv", "Scripts", "python.exe"),
          path.join(rootDir, ".venv", "bin", "python"),
        ]
      : [
          path.join(rootDir, ".venv", "bin", "python"),
          path.join(rootDir, ".venv", "Scripts", "python.exe"),
        ];
  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  const pathNames =
    process.platform === "win32" ? ["python.exe", "python"] : ["python"];
  return findExecutableOnPath(env.PATH, pathNames);
}

function collectConfiguredKeys(processEnv, rootDir) {
  const webFile = readEnvFileOrEmpty(path.join(rootDir, WEB_ENV_FILE));
  const pythonFile = readEnvFileOrEmpty(path.join(rootDir, PYTHON_ENV_FILE));
  return {
    web: processEnv[WEB_KEY_NAME] ?? webFile.get(WEB_KEY_NAME),
    python: processEnv[PYTHON_KEY_NAME] ?? pythonFile.get(PYTHON_KEY_NAME),
  };
}

export function allServicesReady(status) {
  return (
    status?.fastapiHealth === true &&
    status?.webListener === true &&
    status?.handshake === true
  );
}

export async function checkService(url, init, fetchFn = fetch) {
  const bounded = init?.signal ? init : { ...init, signal: AbortSignal.timeout(PROBE_TIMEOUT_MS) };
  try {
    const response = await fetchFn(url, bounded);
    return response.ok;
  } catch {
    return false;
  }
}

export async function checkHandshake(sharedKey, fetchFn = fetch) {
  try {
    const response = await fetchFn(
      `${FASTAPI_URL}/api/v1/internal/readiness`,
      {
        headers: { "X-Internal-API-Key": sharedKey },
        signal: AbortSignal.timeout(2_000),
      },
    );
    if (!response.ok) {
      return false;
    }
    const body = await response.json().catch(() => null);
    return body && body.service === "optimizer" && body.internal === "ok";
  } catch {
    return false;
  }
}

export async function waitForServices(sharedKey, deps = {}) {
  const check = deps.checkService ?? checkService;
  const handshake = deps.checkHandshake ?? checkHandshake;
  const write = deps.write ?? ((text) => process.stdout.write(text));
  const pollIntervalMs = deps.pollIntervalMs ?? POLL_INTERVAL_MS;
  const announced = {
    fastapiHealth: false,
    webListener: false,
    handshake: false,
  };

  while (true) {
    const [fastapiHealth, web, handshakeOk] = await Promise.all([
      check(`${FASTAPI_URL}/health`),
      check(WEB_URL, { signal: AbortSignal.timeout(2_000) }),
      handshake(sharedKey),
    ]);

    if (fastapiHealth && !announced.fastapiHealth) {
      announced.fastapiHealth = true;
      write("[uniride-local] optimizer /health: UP\n");
    }
    if (web && !announced.webListener) {
      announced.webListener = true;
      write("[uniride-local] next web listener: UP\n");
    }
    if (handshakeOk && !announced.handshake) {
      announced.handshake = true;
      write("[uniride-local] optimizer internal readiness handshake: UP\n");
    }
    if (allServicesReady({ fastapiHealth, webListener: web, handshake: handshakeOk })) {
      write("[uniride-local] both services running. Press Ctrl+C to stop.\n");
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }
}

function defaultKillEntry(entry, force) {
  const args = treeKillArgs(entry.proc.pid);
  if (args) {
    spawn("taskkill", args, { stdio: "ignore" });
    return;
  }
  try {
    entry.proc.kill(force ? "SIGKILL" : "SIGTERM");
  } catch {
    // ignore
  }
}

export function terminateChildren(children, force, killEntry = defaultKillEntry) {
  for (const entry of children) {
    if (entry.exited) {
      continue;
    }
    killEntry(entry, force);
  }
}

export function startStack(options, deps = {}) {
  const spawnFn = deps.spawnFn ?? spawn;
  const killEntry = deps.killEntry ?? defaultKillEntry;
  const children = [];

  const pythonProc = spawnFn(
    options.pythonBin,
    pythonCommand(options.pythonBin).args,
    {
      cwd: path.join(options.rootDir, "optimizer_api"),
      env: buildChildEnv(process.env, options.shared.key),
      stdio: "inherit",
    },
  );
  const python = { proc: pythonProc, exited: false };
  children.push(python);
  pythonProc.on("error", options.onError);
  pythonProc.on("exit", options.onUnexpectedExit("optimizer API", python));

  let webProc;
  try {
    webProc = spawnFn(
      options.web.shell
        ? [options.web.command, ...options.web.args].join(" ")
        : options.web.command,
      options.web.shell ? [] : options.web.args,
      {
        cwd: options.rootDir,
        env: buildChildEnv(process.env, options.shared.key),
        stdio: "inherit",
        shell: Boolean(options.web.shell),
      },
    );
  } catch (error) {
    terminateChildren(children, true, killEntry);
    throw error;
  }
  const webEntry = { proc: webProc, exited: false };
  children.push(webEntry);
  webEntry.proc.on("error", options.onError);
  webEntry.proc.on("exit", options.onUnexpectedExit("next web", webEntry));

  return children;
}

async function main() {
  const rootDir = process.cwd();
  const checkOnly = process.argv.includes("--check-only");

  const configured = collectConfiguredKeys(process.env, rootDir);
  let shared;
  try {
    shared = resolveSharedKey(configured);
  } catch (error) {
    if (error instanceof KeyMismatchError) {
      process.stderr.write(`[uniride-local] ${error.message}\n`);
      process.exitCode = 1;
      return;
    }
    throw error;
  }

  const pythonBin = resolvePythonBin(process.env, rootDir);
  const web = webCommand();

  if (checkOnly) {
    process.stdout.write(
      `[uniride-local] environment files: ${WEB_ENV_FILE}, ${PYTHON_ENV_FILE}\n`,
    );
    process.stdout.write(
      `[uniride-local] internal key: ${
        shared.configured ? "configured" : "ephemeral"
      } (value never printed)\n`,
    );
    process.stdout.write(
      `[uniride-local] python interpreter: ${
        pythonBin ?? "MISSING (set UNIRIDE_PYTHON or create .venv)"
      }\n`,
    );
    if (pythonBin === null) {
      process.stderr.write(
        "[uniride-local] check-only: python interpreter not found\n",
      );
      process.exitCode = 1;
      return;
    }
    process.stdout.write(
      `[uniride-local] web runner: ${web.command} (shell=${
        web.shell ? "on" : "off"
      }) probing --version...\n`,
    );
    const probeOk = await probeWebRunner(web);
    if (!probeOk) {
      process.stderr.write(
        `[uniride-local] check-only: web runner ${web.command} probe failed\n`,
      );
      process.exitCode = 1;
      return;
    }
    process.stdout.write("[uniride-local] web runner probe: PASS\n");
    return;
  }

  if (pythonBin === null) {
    process.stderr.write(
      "[uniride-local] python interpreter not found; set UNIRIDE_PYTHON or create .venv\n",
    );
    process.exitCode = 1;
    return;
  }

  let shuttingDown = false;

  function shutdown(code) {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    terminateChildren(children, false);
    setTimeout(() => {
      terminateChildren(children, true);
      process.exit(code);
    }, 3_000);
  }

  process.on("SIGINT", () => shutdown(130));
  process.on("SIGTERM", () => shutdown(143));

  function onUnexpectedExit(name, entry) {
    return (code, signal) => {
      entry.exited = true;
      if (shuttingDown) {
        return;
      }
      process.stderr.write(
        `[uniride-local] ${name} exited unexpectedly (code=${code ?? "none"}, signal=${signal ?? "none"})\n`,
      );
      shutdown(1);
    };
  }

  const children = startStack({
    pythonBin,
    web,
    rootDir,
    shared,
    onError: () => shutdown(1),
    onUnexpectedExit,
  });

  await waitForServices(shared.key);
}

const isMain =
  process.argv[1] &&
  pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;

if (isMain) {
  main().catch((error) => {
    process.stderr.write(
      `[uniride-local] startup failed: ${error?.message ?? "unknown error"}\n`,
    );
    process.exit(1);
  });
}