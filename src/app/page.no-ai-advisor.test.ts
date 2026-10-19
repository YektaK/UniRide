import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * Audit L2 (owner decision 2026-10-19: remove, do not build the route).
 * The landing page used to POST to /api/ai-advisor, which has no route under
 * src/app/api, so the advisor UI always showed an error.
 */
const srcDir = fileURLToPath(new URL("..", import.meta.url));
const pageSource = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");

function listSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return listSourceFiles(full);
    return /\.(ts|tsx)$/.test(name) && !name.endsWith(".no-ai-advisor.test.ts") ? [full] : [];
  });
}

describe("landing page AI advisor removal (audit L2)", () => {
  it("no /api/ai-advisor route exists, so no source file may call it", () => {
    expect(existsSync(join(srcDir, "app", "api", "ai-advisor"))).toBe(false);
    const offenders = listSourceFiles(srcDir).filter((file) =>
      readFileSync(file, "utf8").includes("/api/ai-advisor")
    );
    expect(offenders).toEqual([]);
  });

  it("the landing page carries no advisor state, handler or translation keys", () => {
    expect(pageSource).not.toMatch(/advisor/i);
    expect(pageSource).not.toContain("handleGetAdvice");
  });

  it.each(["en", "tr"])("messages/%s.json has no page.benchmark.advisor block", (locale) => {
    const messages = JSON.parse(
      readFileSync(new URL(`../../messages/${locale}.json`, import.meta.url), "utf8")
    ) as { page: { benchmark: Record<string, unknown> } };
    expect(messages.page.benchmark).not.toHaveProperty("advisor");
  });
});
