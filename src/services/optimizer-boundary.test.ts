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

  it.each([
    ["src/services/optimizer-service.ts", ["/api/v1/optimize", "/api/v1/compare"]],
    ["src/app/api/sandbox/route.ts", ["/api/v1/optimize"]],
    ["src/services/doubus/multi-vehicle-routing.ts", ["/api/v1/optimize"]],
  ])("routes heavy calls in %s through optimizerFetch", (path, endpoints) => {
    const source = read(path);
    expect(source).toContain("optimizerFetch");
    for (const endpoint of endpoints) expect(source).toContain(endpoint);
    expect(source).not.toMatch(/fetch\s*\(\s*[`'"][^`'"]*\/api\/v1\/(optimize|compare|vehicle-calculator)/);
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
