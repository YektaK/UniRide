import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const read = (path: string) => readFileSync(join(root, path), "utf8");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("optimizer server boundary", () => {
  it("contains no public optimizer-key variable", () => {
    const forbidden = ["NEXT", "PUBLIC", "OPTIMIZER", "INTERNAL", "API", "KEY"].join("_");
    for (const file of sourceFiles(join(root, "src"))) {
      expect(readFileSync(file, "utf8"), file).not.toContain(forbidden);
    }
  });

  it("keeps the compare client on type-only browser-safe imports", () => {
    const page = read("src/app/(app)/admin/compare/page.tsx");
    expect(page).toContain("import type");
    expect(page).toContain("@/services/optimizer-types");
    expect(page).not.toContain("@/services/optimizer-service");
  });

  it("owns browser-safe route and comparison DTOs in optimizer-types", () => {
    const service = read("src/services/optimizer-service.ts");
    const types = read("src/services/optimizer-types.ts");

    expect(types).toContain("export interface RouteStep");
    expect(types).toContain("export interface VehicleRoute");
    expect(types).toContain("routes: VehicleRoute[]");
    expect(types).toContain("export interface AlgorithmCompareResult");
    expect(types).toContain("export interface CompareResult");
    expect(service).not.toMatch(/export interface (RouteStep|VehicleRoute|AlgorithmCompareResult|CompareResult)/);
    expect(service).toContain('export type { RouteStep, VehicleRoute, AlgorithmCompareResult, CompareResult } from "./optimizer-types"');
  });

  it("routes every heavy optimizer endpoint through the authenticated transport", () => {
    const endpointPattern = /\/api\/v1\/(optimize|compare|vehicle-calculator)/;
    const directFetchPattern = /\bfetch\s*\([\s\S]{0,180}\/api\/v1\/(optimize|compare|vehicle-calculator)/;
    const expectedModules = new Set([
      "src/services/optimizer-service.ts",
      "src/app/api/sandbox/route.ts",
      "src/services/doubus/multi-vehicle-routing.ts",
    ]);
    const observedModules = new Set<string>();

    for (const file of sourceFiles(join(root, "src"))) {
      const relative = file.slice(root.length + 1).replaceAll("\\", "/");
      const source = readFileSync(file, "utf8");
      if (/\.test\.(ts|tsx)$/.test(relative) || !endpointPattern.test(source)) continue;
      observedModules.add(relative);
      expect(source, relative).toContain("optimizerFetch");
      expect(source, relative).not.toMatch(directFetchPattern);
    }

    expect(observedModules).toEqual(expectedModules);
  });
  it("keeps server-only transport out of client components", () => {
    for (const file of sourceFiles(join(root, "src"))) {
      const source = readFileSync(file, "utf8");
      if (/^[\s\n]*["']use client["'];/m.test(source)) {
        expect(source, file).not.toContain("optimizer-server");
      }
    }
  });
});
