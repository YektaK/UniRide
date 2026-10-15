import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CLUSTERING_ALGORITHM_NAMES } from "./clustering-algorithms";

describe("CLUSTERING_ALGORITHM_NAMES", () => {
  it("matches the optimizer's SUPPORTED_CLUSTERING_ALGORITHMS (the factory dict keys)", () => {
    const source = readFileSync(
      join(process.cwd(), "uniride_core/algorithms/clustering_strategies/__init__.py"),
      "utf8"
    );
    const block = source.match(/_CLUSTERING_STRATEGIES\s*=\s*\{([\s\S]*?)\n\}/);
    expect(block).not.toBeNull();
    const pythonNames = [...block![1].matchAll(/^\s*"([a-z_]+)"\s*:/gm)].map((m) => m[1]);

    expect(pythonNames.length).toBe(7);
    expect([...CLUSTERING_ALGORITHM_NAMES].sort()).toEqual([...pythonNames].sort());
  });
});
