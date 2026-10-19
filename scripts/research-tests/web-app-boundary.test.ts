import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// Boundary of the served web application (ACADEMIC_STUDY_UNIFICATION_DESIGN.md, production must not depend on academic
// result artifacts). This file lives under scripts/, outside src/, because it names the result folders it looks for.
// Research tooling that reads or writes `docs/paper/results/...` (the WP-E10 fleet re-run guards and their tests) lives in
// scripts/ and scripts/research-tests/; nothing under src/ may name those folders, and the import graph of the served
// app (src/app, src/components, src/proxy.ts) must not reach a file that does.

const ROOT = path.resolve(__dirname, "..", "..");
const SRC = path.join(ROOT, "src");

/** Literal path, path.join/resolve segment lists, and the folder names of academic result archives. */
export const RESULT_FOLDER_PATTERNS: readonly RegExp[] = [
  /docs[\\/]+paper/i,
  /["'`]docs["'`]\s*,\s*["'`]paper["'`]/i,
  /["'`]paper["'`]\s*,\s*["'`]results["'`]/i,
  /["'`]paper[\\/]+results/i,
  /week-2026-10-05/i,
  /tsplib-exact-reference/i,
  /exact_reference/i,
];

export function resultFolderReferences(text: string): string[] {
  return RESULT_FOLDER_PATTERNS.filter((pattern) => pattern.test(text)).map((pattern) => pattern.source);
}

function walk(dir: string): string[] {
  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) { if (entry.name !== "node_modules") files.push(...walk(full)); }
    else if (/\.(ts|tsx|js|jsx|mjs|json)$/.test(entry.name)) files.push(full);
  }
  return files;
}
const isTest = (file: string) => /\.test\.(ts|tsx)$/.test(file);
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");

const IMPORT = /(?:\bfrom\s+|\bimport\s*\(\s*|\bimport\s+|\brequire\s*\(\s*)["']([^"']+)["']/g;
function resolveModule(spec: string, from: string): string | null {
  const base = spec.startsWith("@/") ? path.join(SRC, spec.slice(2)) : spec.startsWith(".") ? path.resolve(path.dirname(from), spec) : null;
  if (base === null) return null;
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, `${base}.js`, `${base}.mjs`, `${base}.json`,
    path.join(base, "index.ts"), path.join(base, "index.tsx")]) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  }
  return null;
}

/** Every first-party file reachable from the roots through static imports, re-exports and dynamic import(). */
export function importClosure(roots: string[]): Set<string> {
  const seen = new Set<string>();
  const queue = [...roots];
  while (queue.length > 0) {
    const file = queue.pop()!;
    if (seen.has(file)) continue;
    seen.add(file);
    if (!/\.(ts|tsx|js|jsx|mjs)$/.test(file)) continue;
    const text = fs.readFileSync(file, "utf8");
    for (const match of text.matchAll(IMPORT)) {
      const target = resolveModule(match[1], file);
      if (target !== null) queue.push(target);
    }
  }
  return seen;
}

const srcFiles = walk(SRC);
const appRoots = srcFiles.filter((file) => !isTest(file) && (
  file.startsWith(path.join(SRC, "app") + path.sep) || file.startsWith(path.join(SRC, "components") + path.sep)
  || file === path.join(SRC, "proxy.ts")));

describe("served web application boundary", () => {
  it("the scan found the application entry points", () => {
    expect(appRoots.length).toBeGreaterThan(50);
    expect(appRoots.map(rel)).toContain("src/app/api/admin/dudullu-preview/route.ts");
  });

  it("no file reachable from the served app names or reads an academic result folder", () => {
    const closure = [...importClosure(appRoots)];
    expect(closure.length).toBeGreaterThan(appRoots.length);
    const offenders = closure.filter((file) => resultFolderReferences(fs.readFileSync(file, "utf8")).length > 0).map(rel);
    expect(offenders).toEqual([]);
  });

  it("no file under src/, tests included, names an academic result folder", () => {
    const offenders = srcFiles.filter((file) => resultFolderReferences(fs.readFileSync(file, "utf8")).length > 0).map(rel);
    expect(offenders).toEqual([]);
  });

  it("the detector catches literal, path.join and path.resolve spellings", () => {
    expect(resultFolderReferences('const a = "docs/paper/results/x";')).not.toEqual([]);
    expect(resultFolderReferences('const a = "docs\\\\paper\\\\results";')).not.toEqual([]);
    expect(resultFolderReferences('join(process.cwd(), "docs", "paper", "results", "w")')).not.toEqual([]);
    expect(resultFolderReferences('path.resolve(root, "paper", "results")')).not.toEqual([]);
    expect(resultFolderReferences('const n = "week-2026-10-05-fleet";')).not.toEqual([]);
    expect(resultFolderReferences('const n = "tsplib-exact-reference";')).not.toEqual([]);
    expect(resultFolderReferences('const results = await fetch("/api/benchmark/results/1");')).toEqual([]);
  });

  it("the import walker follows @/ aliases and relative imports", () => {
    const closure = importClosure([path.join(SRC, "app/api/admin/dudullu-preview/route.ts")]);
    expect([...closure].map(rel)).toContain("src/services/daily-plan-run.ts");
  });
});
