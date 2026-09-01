import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
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