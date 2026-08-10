import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

type RootPackage = {
  dependencies?: Record<string, string>;
};

type Lockfile = {
  packages: {
    "": RootPackage;
  };
};

const projectRoot = resolve(__dirname, "../..");
const manifest = JSON.parse(
  readFileSync(resolve(projectRoot, "package.json"), "utf8"),
) as RootPackage;
const lockfile = JSON.parse(
  readFileSync(resolve(projectRoot, "package-lock.json"), "utf8"),
) as Lockfile;

describe("dependency manifest contract", () => {
  it("removes unused direct dependency edges while retaining required roots", () => {
    const roots = [manifest.dependencies ?? {}, lockfile.packages[""].dependencies ?? {}];
    const removedDirectDependencies = [
      "@genkit-ai/ai",
      "@genkit-ai/firebase",
      "@genkit-ai/google-genai",
      "@genkit-ai/next",
      "@typespec/compiler",
    ];
    const retainedDirectDependencies = ["genkit", "@genkit-ai/googleai", "xlsx"];

    for (const dependency of removedDirectDependencies) {
      for (const root of roots) {
        expect(root).not.toHaveProperty(dependency);
      }
    }

    for (const dependency of retainedDirectDependencies) {
      for (const root of roots) {
        expect(root).toHaveProperty(dependency);
      }
    }
  });
});
